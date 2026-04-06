import logging

from aio_pika.abc import AbstractIncomingMessage

logger = logging.getLogger(__name__)


async def default_incoming_handler(message: AbstractIncomingMessage) -> None:
    async with message.process():
        body = message.body.decode("utf-8", errors="replace")
        logger.info("message rk=%s body=%s", message.routing_key, body)
