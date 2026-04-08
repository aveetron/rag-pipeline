import asyncio
import logging
import shutil
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.handler import handle_ingestion_message
from app.messaging import RabbitMQConsumer, RabbitMQProducer
from app.routers import ask
from app.routers import health
from app.routers import upload
from app.handler.embedding import get_embeddings
from config.rabbitmq import close_connection, create_connection
from config.settings import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    connection = await create_connection(settings)
    app.state.rabbitmq_connection = connection

    producer = RabbitMQProducer(connection, settings.exchange_name)
    await producer.setup()
    app.state.rabbitmq_producer = producer

    consumer = RabbitMQConsumer(
        connection,
        settings.exchange_name,
        settings.rabbitmq_queue_name,
        handle_ingestion_message,
    )
    await consumer.setup()
    await consumer.start()
    app.state.rabbitmq_consumer = consumer

    def _warm_embeddings() -> None:
        get_embeddings().get_embedding_dimension()

    try:
        await asyncio.to_thread(_warm_embeddings)
        logger.info("Embedding model warmed up for /query")
    except Exception:
        logger.exception("Embedding warmup failed; first /query may be slow")
    await ask.warmup_llm()

    yield

    await consumer.stop()
    await producer.close()
    await close_connection(connection)
    upload_dir = get_settings().upload_dir
    if upload_dir.exists():
        shutil.rmtree(upload_dir)


app = FastAPI(lifespan=lifespan)
app.include_router(health.router)
app.include_router(upload.router)
app.include_router(ask.router)

if __name__ == "__main__":
  uvicorn.run(app, host="0.0.0.0", port=8000)
