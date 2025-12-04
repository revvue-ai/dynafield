import asyncio
import json
from typing import Any, Dict, List, Optional

from aio_pika import ExchangeType, Message, connect
from aio_pika.abc import AbstractChannel, AbstractConnection
from aio_pika.pool import Pool
from faststream.rabbit import RabbitExchange

from ..logger.logger_config import get_logger

log = get_logger(__name__)

_default_connection_params = {
    "host": "localhost",
    "port": 5672,
    "virtualhost": "/",
    "login": "guest",
    "password": "guest",
}


class AMQPublisher:
    def __init__(self, exchanges: List[RabbitExchange], connection_params: Optional[Dict[str, Any]] = None) -> None:
        self._connection_pool: Optional[Pool[AbstractConnection]] = None
        self._channel_pool: Optional[Pool[AbstractChannel]] = None
        self._is_initialized = False
        self.exchanges: List[RabbitExchange] = exchanges

        if connection_params is not None:
            self._connection_params = connection_params
        else:
            self._connection_params = _default_connection_params

    async def initialize(self) -> None:
        """Initialize connection pools - call this once at app startup"""
        if self._is_initialized:
            return

        # Connection pool - manages physical TCP connections to RabbitMQ
        self._connection_pool = Pool(self._create_connection, max_size=10, loop=asyncio.get_event_loop())

        self._channel_pool = Pool(
            self._create_channel,
            max_size=50,  # Max 50 channels
            loop=asyncio.get_event_loop(),
        )

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

    async def publish(
        self,
        data: Dict[str, Any],
        exchange: str,
        routing_key: str,
        require_confirm: bool = True,
        msg_type: Optional[str] = None,
    ) -> bool:
        if not self._is_initialized:
            raise RuntimeError("Publisher not initialized. Call initialize() first.")

        if self._channel_pool is None:
            raise RuntimeError("Channel pool not initialized")

        try:
            async with self._channel_pool.acquire() as channel:
                # Idempotent
                message = Message(
                    body=json.dumps(data).encode(),
                    content_type="application/json",
                    delivery_mode=2,  # Persistent,
                    type=msg_type,
                )

                exchange_obj = next((e for e in self.exchanges if e.name == exchange), None)
                if exchange_obj is None:
                    raise ValueError(f"Exchange '{exchange}' not found in configured exchanges.")

                exchange_obj_declared = await channel.declare_exchange(
                    exchange_obj.name, type=ExchangeType(exchange_obj.type.value), durable=exchange_obj.durable
                )

                if require_confirm:
                    confirm = await exchange_obj_declared.publish(message, routing_key, timeout=5.0)
                    if confirm:
                        log.info(f"✅ CONFIRMED: {exchange}::{routing_key}")
                        return True
                    else:
                        log.error(f"❌ NOT CONFIRMED: {exchange}::{routing_key}")
                        return False
                else:
                    await exchange_obj_declared.publish(message, routing_key)
                    log.info(f"📤 SENT: {exchange}::{routing_key}")
                    return True

        except asyncio.TimeoutError:
            log.info(f"CONFIRM TIMEOUT: {exchange}::{routing_key}")
            raise ValueError("Publish confirm timeout")
        except Exception as e:
            log.error(f"Failed to publish: {e}")
            raise e

    async def close(self) -> None:
        """Close all pools - call this at app shutdown"""
        if self._channel_pool:
            await self._channel_pool.close()
        if self._connection_pool:
            await self._connection_pool.close()
        self._is_initialized = False
        log.info("✅ RabbitMQ pools closed")
