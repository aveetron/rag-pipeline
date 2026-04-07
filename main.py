from contextlib import asynccontextmanager
import shutil

import uvicorn
from fastapi import FastAPI

from app.handler import handle_ingestion_message
from app.messaging import RabbitMQConsumer, RabbitMQProducer
from app.routers import health
from app.routers import upload
from config.rabbitmq import close_connection, create_connection
from config.settings import get_settings


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

    yield

    await consumer.stop()
    await producer.close()
    await close_connection(connection)
    # delete upload directory
    shutil.rmtree(get_settings().upload_dir)


app = FastAPI(lifespan=lifespan)
app.include_router(health.router)
app.include_router(upload.router)

if __name__ == "__main__":
  uvicorn.run(app, host="0.0.0.0", port=8000)