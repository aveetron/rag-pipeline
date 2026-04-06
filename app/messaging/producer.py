import aio_pika
from aio_pika import Message
from aio_pika.abc import AbstractExchange, AbstractRobustChannel, AbstractRobustConnection


class RabbitMQProducer:
    def __init__(self, connection: AbstractRobustConnection, exchange_name: str) -> None:
        self._connection = connection
        self._exchange_name = exchange_name
        self._channel: AbstractRobustChannel | None = None
        self._exchange: AbstractExchange | None = None

    async def setup(self) -> None:
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            self._exchange_name,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

    async def publish(self, body: bytes | str, routing_key: str = "default") -> None:
        if self._exchange is None:
            raise RuntimeError("RabbitMQProducer.setup() must be called before publish")
        payload = body.encode() if isinstance(body, str) else body
        await self._exchange.publish(Message(payload), routing_key=routing_key)

    async def close(self) -> None:
        if self._channel is not None:
            await self._channel.close()
            self._channel = None
            self._exchange = None
