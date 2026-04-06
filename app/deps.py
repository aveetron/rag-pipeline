from fastapi import Request

from app.messaging.producer import RabbitMQProducer


def get_rabbitmq_producer(request: Request) -> RabbitMQProducer:
    return request.app.state.rabbitmq_producer
