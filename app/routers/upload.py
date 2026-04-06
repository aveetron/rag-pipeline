from fastapi import APIRouter
from app.models.common import ApiResponse

from app.models.upload import UploadRequest

router = APIRouter(prefix="/upload", tags=["upload"])

@router.post("", summary="upload data to the pipeline")
async def upload(request: UploadRequest) -> ApiResponse:
    return ApiResponse.success("Data uploaded successfully")