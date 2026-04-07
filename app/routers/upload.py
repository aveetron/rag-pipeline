import json

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.deps import get_rabbitmq_producer
from app.messaging.producer import RabbitMQProducer
from app.models.common import ApiResponse
from app.models.upload import build_ingest_payload, ensure_at_least_one_source
from config.settings import get_settings

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("", summary="Upload PDF and/or text metadata to the pipeline (multipart/form-data)")
async def upload(
    producer: RabbitMQProducer = Depends(get_rabbitmq_producer),
    file: UploadFile | None = File(default=None, description="PDF file to ingest"),
    website_url: str | None = Form(default=None),
    text: str | None = Form(default=None),
    database_url: str | None = Form(default=None),
) -> ApiResponse:
    ensure_at_least_one_source(
        file=file,
        website_url=website_url,
        text=text,
        database_url=database_url,
    )
    settings = get_settings()
    payload = await build_ingest_payload(
        file=file,
        website_url=website_url,
        text=text,
        database_url=database_url,
        upload_dir=settings.upload_dir,
        max_bytes=settings.max_upload_bytes,
    )
    await producer.publish(json.dumps(payload).encode("utf-8"), routing_key="upload")
    return ApiResponse.success("Data uploaded successfully")
