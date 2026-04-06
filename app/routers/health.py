from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="Liveness / readiness probe")
async def health() -> dict[str, str]:
  return {"status": "ok"}
