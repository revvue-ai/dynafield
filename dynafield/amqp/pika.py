import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pika
from faststream.rabbit import RabbitQueue
from pika.adapters.blocking_connection import BlockingChannel

from ..models.error_msg import ErrorMessage

log = logging.getLogger(__name__)


class RabbitMQPeeker:
    def __init__(
        self, error_queue: RabbitQueue, host: str, port: int = 5672, virtual_host: str = "/", username: str = "guest", password: str = "guest"
    ) -> None:
        self.error_queue = error_queue
        self.connection_params = pika.ConnectionParameters(
            host=host,
            port=port,
            virtual_host=virtual_host,
            credentials=pika.PlainCredentials(username, password),
            heartbeat=600,
            blocked_connection_timeout=300,
        )

    def get_channel(self) -> BlockingChannel:
        """Get a fresh channel for each operation"""
        connection = pika.BlockingConnection(self.connection_params)
        return connection.channel()

    @staticmethod
    def parse_error_message(
        body: bytes,
        method_frame: Optional[pika.spec.Basic.GetOk] = None,
        header_frame: Optional[pika.spec.BasicProperties] = None,
        total_message_count: int = 0,
        current_index: int = 0,
    ) -> ErrorMessage:
        """
        Parse a raw RabbitMQ message into ErrorMessage model and extract metadata.
        """
        try:
            error_wrapper = json.loads(body.decode("utf-8"))
            # Extract original payload from wrapper
            original_payload = error_wrapper.pop("payload", {})
            error_info = error_wrapper.get("error_info", {})
            source_queue = error_wrapper.get("source_queue", "")
            source_exchange = error_wrapper.get("source_exchange", "")
            service_name = error_wrapper.get("service_name", None)
            metadata = error_wrapper.get("_metadata", {})

            # Get timestamp from error info or use current time
            timestamp_str = error_info.get("timestamp")
            timestamp = None
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except Exception as e:
                    log.debug(f"Failed to parse timestamp {e}")
                    timestamp = datetime.now(timezone.utc)

            # Extract tenant ID from various sources
            tenant_id = None
            if original_payload and isinstance(original_payload, dict):
                tenant_id = original_payload.get("tenant_id")
            if header_frame and header_frame.headers is not None:
                header_dict: Dict[str, Any] = dict(header_frame.headers)
            else:
                header_dict = {}
            # Create ErrorMessage model
            error_message = ErrorMessage(
                message_id=error_info.get("message_id") or getattr(header_frame, "message_id", None),
                body=error_wrapper,  # Store original payload, not wrapper
                service_name=service_name,
                routing_key=source_queue,
                exchange=source_exchange,
                headers=header_dict,
                timestamp=timestamp,
                redelivered=getattr(method_frame, "redelivered", False) if method_frame else False,
                message_index=total_message_count - current_index - 1,
                tenant_id=tenant_id,
                payload=original_payload,
                metadata=metadata,
            )

            return error_message

        except Exception as e:
            # Catch-all for errors
            error_message = ErrorMessage(
                body={"error": str(e)},
                timestamp=datetime.now(timezone.utc),
                message_count=total_message_count - current_index - 1,
            )

            return error_message

    def peek_messages(self, service_filter: Optional[List[str]] = None, max_messages: int = 50) -> List[ErrorMessage]:
        """
        Peek at messages in error queue without consuming them.
        """
        channel = self.get_channel()
        messages = []

        try:
            # Get queue info
            queue_declare = channel.queue_declare(queue=self.error_queue.name, passive=True)
            message_count = queue_declare.method.message_count

            if message_count == 0:
                log.info(f"No messages in error queue '{self.error_queue.name}'")
                return []

            # Peek at messages
            for i in range(min(max_messages, message_count)):
                method_frame, header_frame, body = channel.basic_get(queue=self.error_queue.name, auto_ack=False)

                if not method_frame:
                    break
                error_message = self.parse_error_message(
                    body=body, method_frame=method_frame, header_frame=header_frame, total_message_count=message_count, current_index=i
                )

                if service_filter is not None and error_message.service_name not in service_filter:
                    continue

                messages.append(error_message)
                channel.basic_reject(method_frame.delivery_tag, requeue=True)

        except Exception as e:
            log.error(f"Error peeking messages: {e}")
            raise
        finally:
            if channel and channel.is_open:
                channel.connection.close()

        log.info(f"Peeked {len(messages)} messages from error queue")
        return messages

    def resend_messages(self, service_filter: Optional[List[str]] = None, limit: Optional[int] = None, remove_from_queue: bool = True) -> Dict[str, Any]:
        """
        Resend messages from error queue to their original destinations.
        """
        channel = self.get_channel()
        results = {
            "total_processed": 0,
            "successfully_resent": 0,
            "failed": 0,
            "skipped": 0,
        }

        try:
            processed = 0

            while True:
                if limit and processed >= limit:
                    break

                method_frame, header_frame, body = channel.basic_get(queue=self.error_queue.name, auto_ack=False)

                if not method_frame:
                    break

                results["total_processed"] += 1
                processed += 1
                delivery_tag = method_frame.delivery_tag

                try:
                    # Parse the message
                    error_message = self.parse_error_message(body=body, method_frame=method_frame, header_frame=header_frame)

                    original_payload = error_message.payload
                    source_exchange = error_message.exchange
                    source_queue = error_message.routing_key
                    service_name = error_message.service_name

                    # Validate
                    if not original_payload or not source_exchange or not source_queue:
                        log.error(f"Missing required info in message {delivery_tag}")
                        channel.basic_reject(delivery_tag, requeue=True)
                        results["failed"] += 1
                        continue

                    # Apply service filter
                    if service_filter and service_name not in service_filter:
                        channel.basic_reject(delivery_tag, requeue=True)
                        results["skipped"] += 1
                        continue

                    # Resend the original payload
                    success = self._resend_single_message(
                        channel=channel,
                        delivery_tag=delivery_tag,
                        payload=original_payload,
                        content_type=header_frame.content_type,
                        source_exchange=source_exchange,
                        source_queue=source_queue,
                        error_message=error_message,
                        remove_from_queue=remove_from_queue,
                    )

                    if success:
                        results["successfully_resent"] += 1
                        log.info(f"Resent message {delivery_tag} from {service_name}")
                    else:
                        results["failed"] += 1
                        channel.basic_reject(delivery_tag, requeue=True)

                except Exception as e:
                    log.error(f"Error processing message {delivery_tag}: {e}")
                    results["failed"] += 1
                    channel.basic_reject(delivery_tag, requeue=True)

        except Exception as e:
            log.error(f"Error in resend_messages: {e}")
        finally:
            if channel and channel.is_open:
                channel.connection.close()

        log.info(f"Resend operation completed: {results}")
        return results

    def discard_messages(self, service_filter: Optional[List[str]] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Discard messages from error queue.
        """
        channel = self.get_channel()
        results = {
            "total_processed": 0,
            "discarded": 0,
            "skipped": 0,
        }

        try:
            processed = 0

            while True:
                if limit and processed >= limit:
                    break

                method_frame, header_frame, body = channel.basic_get(queue=self.error_queue.name, auto_ack=False)

                if not method_frame:
                    break

                results["total_processed"] += 1
                processed += 1
                delivery_tag = method_frame.delivery_tag

                try:
                    # Parse the message (for logging/record keeping)
                    error_message = self.parse_error_message(body=body, method_frame=method_frame, header_frame=header_frame)

                    if service_filter is not None and error_message.service_name not in service_filter:
                        channel.basic_reject(delivery_tag, requeue=True)
                        results["skipped"] += 1
                        continue

                    channel.basic_ack(delivery_tag)
                    results["discarded"] += 1
                    log.info(f"Discarded message {delivery_tag}")

                except Exception as e:
                    log.error(f"Error processing message {delivery_tag}: {e}")
                    channel.basic_reject(delivery_tag, requeue=True)

        except Exception as e:
            log.error(f"Error in discard_messages: {e}")
        finally:
            if channel and channel.is_open:
                channel.connection.close()

        log.info(f"Discard operation completed: {results}")
        return results

    @staticmethod
    def _resend_single_message(
        channel: BlockingChannel,
        delivery_tag: int,
        payload: Dict[str, Any],
        content_type: str,
        source_exchange: str,
        source_queue: str,
        error_message: Optional[ErrorMessage] = None,
        remove_from_queue: bool = True,
    ) -> bool:
        """
        Resend a single original payload to its original destination.
        """
        try:
            log.info(f"Resending to {source_exchange}::{source_queue}")
            body = json.dumps(payload).encode("utf-8")

            headers = {
                "x-resent": True,
                "x-resent-timestamp": str(time.time()),
            }

            if error_message and error_message.tenant_id:
                headers["x-tenant-id"] = error_message.tenant_id

            properties = pika.BasicProperties(
                content_type=content_type or "application/json",
                delivery_mode=2,  # Persistent
                headers=headers,
                message_id=error_message.message_id if error_message else None,
                timestamp=int(time.time()),
            )

            channel.basic_publish(exchange=source_exchange, routing_key=source_queue, body=body, properties=properties)

            if remove_from_queue:
                channel.basic_ack(delivery_tag)
            log.info(f"Successfully resent to {source_exchange}::{source_queue}")
            return True

        except Exception as e:
            log.error(f"Failed to resend message {delivery_tag} to {source_exchange}::{source_queue}: {e}")
            return False
