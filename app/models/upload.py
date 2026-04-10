import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile


def ensure_at_least_one_source(
    *,
    file: UploadFile | None,
    url: str | None,
    text: str | None,
    db: str | None,
) -> None:
    has_file = file is not None and bool(file.filename)
    if not any([has_file, url, text, db]):
        raise HTTPException(
            status_code=400,
            detail="Provide a PDF file, url, text, or db.",
        )


def ensure_pdf(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")
    name = file.filename.lower()
    if not name.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    ct = (file.content_type or "").lower()
    if ct and "pdf" not in ct and ct not in ("application/octet-stream", "binary/octet-stream"):
        raise HTTPException(
            status_code=400,
            detail="File must be a PDF (wrong content type).",
        )


async def build_ingest_payload(
    *,
    file: UploadFile | None,
    url: str | None,
    text: str | None,
    db: str | None,
    upload_dir: Path,
    max_bytes: int,
) -> dict[str, Any]:
    # Normalize — treat blank, whitespace-only, or placeholder strings as None
    url = url.strip() if url else None
    text = text.strip() if text else None
    db = db.strip() if db else None

    # Discard Swagger placeholder default values
    url = None if url in (None, "string", "null") else url
    text = None if text in (None, "string", "null") else text
    db = None if db in (None, "string", "null") else db

    payload: dict[str, Any] = {}

    if file is not None and file.filename:
        ensure_pdf(file)
        data = await file.read()
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum size of {max_bytes} bytes.",
            )
        upload_dir.mkdir(parents=True, exist_ok=True)
        dest = upload_dir / f"{uuid.uuid4().hex}.pdf"
        dest.write_bytes(data)
        payload["source"] = "pdf"
        payload["stored_path"] = str(dest.resolve())
        payload["original_filename"] = file.filename
        payload["size_bytes"] = len(data)
    elif db:
        payload["source"] = "db"
        payload["db"] = db
    elif url:
        payload["source"] = "url"
        payload["url"] = url
    elif text:
        payload["source"] = "text"
        payload["text"] = text
    else:
        raise HTTPException(status_code=400, detail="Provide a PDF file, url, text, or db.")

    return payload