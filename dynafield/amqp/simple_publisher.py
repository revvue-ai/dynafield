import asyncio
import json
from typing import Any, Dict, Optional, Set, Tuple

from aio_pika import ExchangeType, Message, connect
from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractExchange, AbstractQueue
from aio_pika.pool import Pool
from pika.exceptions import AMQPError

from dynafield.logger.logger_config import get_logger

log = get_logger(__name__)

_default_connection_params = {
    "host": "localhost",
    "port": 5672,
    "virtualhost": "/",
    "login": "guest",
    "password": "guest",
}


class AMQPSimplePublisher:
    def __init__(self, connection_params: Optional[Dict[str, Any]] = None) -> None:
        self._connection_pool: Optional[Pool[AbstractConnection]] = None
        self._channel_pool: Optional[Pool[AbstractChannel]] = None
        self._is_initialized = False
        self._declared_exchanges: Set[str] = set()

        if connection_params is not None:
            self._connection_params = connection_params
        else:
            self._connection_params = _default_connection_params

    async def initialize(self) -> None:
        """Initialize connection pools - call this once at app startup"""
        if self._is_initialized:
            return

        self._connection_pool = Pool(self._create_connection, max_size=10, loop=asyncio.get_event_loop())

        self._channel_pool = Pool(self._create_channel, max_size=50, loop=asyncio.get_event_loop())

        self._is_initialized = True
        log.info("✅ RabbitMQ pools initialized")

    async def _create_connection(self) -> AbstractConnection:
        host: str | None = self._connection_params.get("host")
        port: int | None = self._connection_params.get("port")
        virtualhost: str = self._connection_params.get("virtualhost", "/")
        login: str = self._connection_params.get("login", "guest")
        password: str = self._connection_params.get("password", "guest")
        log.info(f"Creating RabbitMQ connection to {host}:{port}")
        if host is None or port is None:
            raise ValueError("Invalid connection parameters for RabbitMQ")

        return await connect(
            host=host,
            port=port,
            virtualhost=virtualhost,
            login=login,
            password=password,
        )

    async def _create_channel(self) -> AbstractChannel:
        if self._connection_pool is None:
            raise RuntimeError("Connection pool not initialized")
        async with self._connection_pool.acquire() as connection:
            return await connection.channel(publisher_confirms=True)

    async def _get_exchange(self, channel: AbstractChannel, exchange: str, exchange_type: str = "topic") -> AbstractExchange:
        """Get or declare exchange object"""
        try:
            # Try to get existing exchange first
            exchange_obj = await channel.get_exchange(exchange)
            log.debug(f"Using existing exchange: {exchange}")
            return exchange_obj
        except Exception:
            # If exchange doesn't exist, declare it
            try:
                exchange_obj = await channel.declare_exchange(exchange, type=ExchangeType(exchange_type), durable=True)
                self._declared_exchanges.add(exchange)
                log.info(f"Declared new exchange: {exchange} ({exchange_type})")
                return exchange_obj
            except Exception as e:
                log.error(f"Failed to declare exchange {exchange}: {e}")
                raise

    async def publish(
        self,
        data: Dict[str, Any],
        exchange: str,
        routing_key: str,
        require_confirm: bool = True,
        msg_type: Optional[str] = None,
        exchange_type: str = "topic",
    ) -> bool:
        """
        Simple publishing using exchange name as string
        """
        if not self._is_initialized:
            raise RuntimeError("Publisher not initialized. Call initialize() first.")

        if self._channel_pool is None:
            raise RuntimeError("Channel pool not initialized")

        try:
            async with self._channel_pool.acquire() as channel:
                # Create message
                message = Message(
                    body=json.dumps(data).encode(),
                    content_type="application/json",
                    delivery_mode=2,  # Persistent
                    type=msg_type,
                )

                # Get exchange object
                exchange_obj = await self._get_exchange(channel, exchange, exchange_type)

                # Publish using the exchange object
                if require_confirm:
                    confirm = await exchange_obj.publish(
                        message,
                        routing_key=routing_key,
                        timeout=5.0,  # 5 second timeout for confirmation
                    )
                    if confirm:
                        log.info(f"CONFIRMED: {exchange}::{routing_key}")
                        return True
                    else:
                        log.error(f"NOT CONFIRMED: {exchange}::{routing_key}")
                        return False
                else:
                    await exchange_obj.publish(message, routing_key=routing_key)
                    log.info(f"📤 SENT: {exchange}::{routing_key}")
                    return True

        except asyncio.TimeoutError:
            log.error(f"CONFIRM TIMEOUT: {exchange}::{routing_key}")
            return False
        except Exception as e:
            log.error(f"PUBLISH FAILED: {exchange}::{routing_key} - {str(e)}")
            return False

    async def _get_queue(
        self,
        channel: AbstractChannel,
        queue: str,
        durable: bool = True,
        exclusive: bool = False,
        auto_delete: bool = False,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> AbstractQueue:
        """
        Get or declare queue object with passive declaration first.
        This is safe for queues that may already exist with different properties.
        """
        try:
            # First try to get the queue passively (won't change properties if it exists)
            try:
                queue_obj = await channel.get_queue(queue, ensure=False)
                log.debug(f"Using existing queue: {queue}")
                return queue_obj
            except AMQPError:
                # If queue doesn't exist, declare it with specified properties
                log.debug(f"Queue {queue} doesn't exist, declaring with durable={durable}")
                queue_obj = await channel.declare_queue(name=queue, durable=durable, exclusive=exclusive, auto_delete=auto_delete, arguments=arguments)
                log.info(f"Declared new queue: {queue} (durable={durable})")
                return queue_obj
        except Exception as e:
            log.error(f"Failed to handle queue {queue}: {e}")
            raise

    async def declare_exchange(
        self, exchange: str, exchange_type: str = "topic", durable: bool = True, auto_delete: bool = False, passive: bool = False
    ) -> bool:
        """
        Safely declare an exchange.
        If passive=True, will only check if exchange exists.
        Returns True if exchange exists or was successfully declared.
        """
        if not self._is_initialized:
            raise RuntimeError("Publisher not initialized. Call initialize() first.")

        if self._channel_pool is None:
            raise RuntimeError("Channel pool not initialized")

        try:
            async with self._channel_pool.acquire() as channel:
                if passive:
                    # Just check if exchange exists
                    _exchange_obj = await channel.get_exchange(exchange)
                    log.debug(f"Exchange exists: {exchange}")
                    return True
                else:
                    # Try to declare with specified properties
                    _exchange_obj = await channel.declare_exchange(name=exchange, type=ExchangeType(exchange_type), durable=durable, auto_delete=auto_delete)
                    self._declared_exchanges.add(exchange)
                    log.info(f"Exchange declared: {exchange} ({exchange_type}, durable={durable})")
                    return True
        except Exception as e:
            if "PRECONDITION_FAILED" in str(e):
                log.warning(f"Exchange '{exchange}' exists with different properties: {e}")
                # Exchange exists but with different properties - we can still use it
                return True
            log.error(f"Failed to handle exchange {exchange}: {e}")
            return False

    async def declare_queue(
        self,
        queue: str,
        durable: bool = True,
        exclusive: bool = False,
        auto_delete: bool = False,
        arguments: Optional[Dict[str, Any]] = None,
        passive: bool = False,
    ) -> Optional[AbstractQueue]:
        """
        Safely declare a queue.
        If passive=True, will only check if queue exists.
        Returns the queue object or None if failed.
        """
        if not self._is_initialized:
            raise RuntimeError("Publisher not initialized. Call initialize() first.")

        if self._channel_pool is None:
            raise RuntimeError("Channel pool not initialized")

        try:
            async with self._channel_pool.acquire() as channel:
                if passive:
                    # Just check if queue exists
                    queue_obj = await channel.get_queue(queue, ensure=False)
                    log.debug(f"Queue exists: {queue}")
                    return queue_obj
                else:
                    # Try to declare with specified properties
                    queue_obj = await channel.declare_queue(name=queue, durable=durable, exclusive=exclusive, auto_delete=auto_delete, arguments=arguments)
                    log.info(f"Queue declared: {queue} (durable={durable}, exclusive={exclusive})")
                    return queue_obj
        except Exception as e:
            if "PRECONDITION_FAILED" in str(e):
                log.warning(f"Queue '{queue}' exists with different properties: {e}")
                # Try to get the existing queue
                try:
                    queue_obj = await channel.get_queue(queue, ensure=False)
                    log.info(f"Using existing queue '{queue}' (properties differ from requested)")
                    return queue_obj
                except Exception as get_error:
                    log.error(f"Could not retrieve existing queue {queue}: {get_error}")
                    return None
            log.error(f"Failed to handle queue {queue}: {e}")
            return None

    async def bind_queue_to_exchange(
        self,
        queue: str,
        exchange: str,
        routing_key: str,
        arguments: Optional[Dict[str, Any]] = None,
        queue_durable: bool = True,
        queue_exclusive: bool = False,
        queue_auto_delete: bool = False,
        queue_arguments: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Safely bind a queue to an exchange.
        This handles the case where the queue may already exist with different properties.
        """
        if not self._is_initialized:
            raise RuntimeError("Publisher not initialized. Call initialize() first.")

        if self._channel_pool is None:
            raise RuntimeError("Channel pool not initialized")

        try:
            async with self._channel_pool.acquire() as channel:
                # Get or declare the exchange
                exchange_obj = await self._get_exchange(channel, exchange)

                # Get or declare the queue (using safe method)
                try:
                    queue_obj = await self._get_queue(
                        channel, queue, durable=queue_durable, exclusive=queue_exclusive, auto_delete=queue_auto_delete, arguments=queue_arguments
                    )
                except Exception as e:
                    log.error(f"Failed to get queue {queue}: {e}")
                    return False

                # Bind queue to exchange
                await queue_obj.bind(exchange_obj, routing_key, arguments=arguments)

                log.info(f"Bound queue '{queue}' to exchange '{exchange}' with routing key '{routing_key}'")
                return True
        except Exception as e:
            if "PRECONDITION_FAILED" in str(e):
                log.warning(f"⚠Binding failed for queue '{queue}' to exchange '{exchange}': {e}")
                # The binding might already exist or there's a property mismatch
                # We'll try to verify if the binding exists
                try:
                    # Check if queue and exchange exist and try to get the binding
                    async with self._channel_pool.acquire() as channel:
                        _exchange_obj = await channel.get_exchange(exchange)
                        _queue_obj = await channel.get_queue(queue, ensure=False)
                        # If we got here, queue and exchange exist
                        log.info(f"✅ Queue '{queue}' and exchange '{exchange}' exist (may already be bound)")
                        return True
                except Exception as e:
                    log.error(f"Cannot verify binding for queue '{queue}' to exchange '{exchange}' {e}")
                    return False
            log.error(f"Failed to bind queue {queue} to exchange {exchange}")
            return False

    async def setup_exchange_and_queue(
        self,
        exchange: str,
        queue: str,
        routing_key: str,
        exchange_type: str = "topic",
        exchange_durable: bool = True,
        exchange_auto_delete: bool = False,
        queue_durable: bool = True,
        queue_exclusive: bool = False,
        queue_auto_delete: bool = False,
        bind_arguments: Optional[Dict[str, Any]] = None,
        queue_arguments: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, bool, bool]:
        """
        Complete setup: declare exchange, declare queue, and bind them.
        Returns tuple of (exchange_handled, queue_handled, binding_handled)
        """
        try:
            # Handle exchange (declared or already exists)
            exchange_result = await self.declare_exchange(
                exchange=exchange, exchange_type=exchange_type, durable=exchange_durable, auto_delete=exchange_auto_delete
            )

            # Handle queue (declared or already exists)
            queue_obj = await self.declare_queue(
                queue=queue, durable=queue_durable, exclusive=queue_exclusive, auto_delete=queue_auto_delete, arguments=queue_arguments
            )
            queue_result = queue_obj is not None

            # Bind queue to exchange (handles existing bindings)
            binding_result = False
            if queue_result:
                binding_result = await self.bind_queue_to_exchange(
                    queue=queue,
                    exchange=exchange,
                    routing_key=routing_key,
                    arguments=bind_arguments,
                    queue_durable=queue_durable,
                    queue_exclusive=queue_exclusive,
                    queue_auto_delete=queue_auto_delete,
                    queue_arguments=queue_arguments,
                )

            return exchange_result, queue_result, binding_result

        except Exception as e:
            log.error(f"Failed to setup exchange '{exchange}' and queue '{queue}': {e}")
            return False, False, False

    async def close(self) -> None:
        """Close all pools - call this at app shutdown"""
        if self._channel_pool:
            await self._channel_pool.close()
        if self._connection_pool:
            await self._connection_pool.close()
        self._is_initialized = False
        self._declared_exchanges.clear()
        log.info("✅ RabbitMQ pools closed")

    async def readiness_ping(self, timeout: float = 0.5, probe_exchange: str = "amq.topic") -> bool:
        if not self._is_initialized or self._channel_pool is None:
            return False

        async def _probe() -> bool:
            async with self._channel_pool.acquire() as channel:  # type: ignore # already checking self._channel_pool for None above, mypy can't resolve it
                await channel.declare_exchange(
                    probe_exchange,
                    type=ExchangeType.TOPIC,
                    passive=True,
                    durable=True,
                )
                return True

        try:
            return await asyncio.wait_for(_probe(), timeout=timeout)
        except Exception as e:
            log.exception(f"RabbitMQ readiness ping failed with error {e}")
            return False
