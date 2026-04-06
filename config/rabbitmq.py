import aio_pika
from aio_pika.abc import AbstractRobustConnection

from config.settings import Settings


async def create_connection(settings: Settings) -> AbstractRobustConnection:
    return await aio_pika.connect_robust(
        host=settings.rabbitmq_host,
        port=settings.rabbitmq_port,
        login=settings.rabbitmq_user,
        password=settings.rabbitmq_password,
        virtualhost=settings.rabbitmq_vhost,
    )


async def close_connection(connection: AbstractRobustConnection) -> None:
    await connection.close()
