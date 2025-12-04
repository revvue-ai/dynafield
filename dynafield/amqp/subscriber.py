import asyncio
from datetime import datetime
from typing import Any, Callable, List, Optional

from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitMessage, RabbitQueue

from ..logger.logger_config import get_logger
from ..utils.formating import parse_structured_traceback

log = get_logger(__name__)


class AmqpSubscriber:
    def __init__(self, exchanges: Optional[List[RabbitExchange]] = None, queues: Optional[List[RabbitQueue]] = None) -> None:
        """Initialize AMQP handler registry with exchanges and queues from config"""
        self.broker: Optional[RabbitBroker] = None
        self.exchanges: List[RabbitExchange] = exchanges or []
        self.queues: List[RabbitQueue] = queues or []

    async def setup_infrastructure(self) -> None:
        """Robust infrastructure setup with retry logic"""
        try:
            await self._try_setup()
            log.debug("✅ AMQP infrastructure setup completed")
            return

        except Exception as e:
            raise e

    async def _try_setup(self) -> None:
        """Attempt to setup AMQP infrastructure"""
        if self.broker is None:
            raise RuntimeError("Broker not initialized")

        for exchange in self.exchanges:
            await self.broker.declare_exchange(exchange)
        for queue in self.queues:
            await self.broker.declare_queue(queue)

    async def register_subscriber(
        self,
        func: Callable[..., Any],
        queue: RabbitQueue,
        exchange: RabbitExchange,
    ) -> None:
        """Manually register a subscriber function"""
        if self.broker is None:
            raise RuntimeError("Broker not initialized")

        self.broker.subscriber(queue=queue, exchange=exchange)(func)
        log.debug(f"✅ Subscriber registered for queue: {queue.name}")

    async def register_subscriber_with_retry(
        self,
        func: Callable[..., Any],
        queue: RabbitQueue,
        exchange: RabbitExchange,
        max_retries: int = 3,
        backoff_factor: int = 1,
        error_routing_key: Optional[str] = None,
        error_exchange: Optional[str] = None,
    ) -> None:
        """Register a subscriber with retry logic built into the handler"""
        if self.broker is None:
            raise RuntimeError("Broker not initialized")

        async def handler_with_retry(
            data: dict[str, Any],
            message: RabbitMessage,
        ) -> Any | None:
            headers = message.headers or {}
            retry_count = headers.get("x-retry-count", 0)
            log.debug(f"🎯 Processing - Retry count: {retry_count}")
            try:
                result = await func(data)
                await message.ack()
                log.debug("✅ Success")
                return result

            except Exception as e:
                log.error(f"❌ Failed: {e}")
                if retry_count < max_retries:
                    backoff_seconds = (retry_count + 1) * backoff_factor
                    log.debug(f"⏰ Waiting {backoff_seconds}s before retry...")
                    await asyncio.sleep(backoff_seconds)

                    new_headers = {**headers, "x-retry-count": retry_count + 1}
                    if self.broker is None:
                        raise RuntimeError("Broker not initialized for retry publishing")
                    routing_key = message.raw_message.routing_key
                    if routing_key is None:
                        raise ValueError("Routing key is None in the original message")
                    await self.broker.publish(data, exchange=message.raw_message.exchange, routing_key=routing_key, headers=new_headers)

                    await message.ack()
                    log.debug(f"🔄 Retry {retry_count + 1} scheduled")

                else:
                    # Capture detailed error information
                    structured_tb = parse_structured_traceback(e, repository="revvue-ai/error-handler")
                    log.error("🚨 Max retries reached - sending to error queue")

                    error_data = {
                        "payload": data,
                        "error_info": structured_tb,
                        "source_queue": queue.name,
                        "source_exchange": exchange.name,
                        "_metadata": {
                            "final_failure": True,
                            "retries": retry_count + 1,
                            "error": str(e),
                            "failed_at": datetime.utcnow().isoformat(),
                        },
                    }

                    if error_exchange and error_routing_key and self.broker:
                        await self.broker.publish(error_data, exchange=error_exchange, routing_key=error_routing_key)

                    await message.ack()
            return None

        self.broker.subscriber(queue=queue, exchange=exchange)(handler_with_retry)
        log.info(f"✅ Subscriber with retry registered for queue: {queue.name}")
