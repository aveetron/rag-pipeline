from collections.abc import Awaitable, Callable

import aio_pika
from aio_pika.abc import (
    AbstractIncomingMessage,
    AbstractQueue,
    AbstractRobustChannel,
    AbstractRobustConnection,
)


class RabbitMQConsumer:
    def __init__(
        self,
        connection: AbstractRobustConnection,
        exchange_name: str,
        queue_name: str,
        handler: Callable[[AbstractIncomingMessage], Awaitable[None]],
    ) -> None:
        self._connection = connection
        self._exchange_name = exchange_name
        self._queue_name = queue_name
        self._handler = handler
        self._channel: AbstractRobustChannel | None = None
        self._queue: AbstractQueue | None = None
        self._consumer_tag: str | None = None

    async def setup(self) -> None:
        self._channel = await self._connection.channel()
        exchange = await self._channel.declare_exchange(
            self._exchange_name,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        self._queue = await self._channel.declare_queue(self._queue_name, durable=True)
        await self._queue.bind(exchange, routing_key="#")

    async def start(self) -> None:
        if self._queue is None:
            raise RuntimeError("RabbitMQConsumer.setup() must be called before start")
        self._consumer_tag = await self._queue.consume(self._handler)

    async def stop(self) -> None:
        if self._consumer_tag is not None and self._queue is not None:
            await self._queue.cancel(self._consumer_tag)
            self._consumer_tag = None
        if self._channel is not None:
            await self._channel.close()
            self._channel = None
            self._queue = None
