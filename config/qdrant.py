"""Qdrant client singleton and helpers for vector ingestion."""

import json
import logging
from typing import Any

import numpy as np
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from config.settings import get_settings

logger = logging.getLogger(__name__)

_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        s = get_settings()
        kwargs: dict[str, Any] = {
            "host": s.qdrant_host,
            "port": s.qdrant_port,
            "https": s.qdrant_https,
            "prefer_grpc": s.qdrant_prefer_grpc,
        }
        if s.qdrant_api_key:
            kwargs["api_key"] = s.qdrant_api_key
        _client = QdrantClient(**kwargs)
        logger.info(
            "Qdrant client ready host=%s port=%s https=%s",
            s.qdrant_host,
            s.qdrant_port,
            s.qdrant_https,
        )
    return _client


def create_collection_for_ingestion(collection_name: str, vector_size: int) -> None:
    client = get_qdrant_client()
    if client.collection_exists(collection_name):
        logger.warning(
            "Qdrant collection %s already exists; skipping create",
            collection_name,
        )
        return
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )
    logger.info(
        "created Qdrant collection %s vector_size=%s distance=COSINE",
        collection_name,
        vector_size,
    )


def _json_safe_value(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


def _payload_for_chunk(chunk: Document) -> dict[str, Any]:
    payload: dict[str, Any] = {"text": chunk.page_content}
    for k, v in chunk.metadata.items():
        payload[str(k)] = _json_safe_value(v)
    return payload


def upsert_chunk_embeddings(
    collection_name: str,
    embeddings: np.ndarray,
    chunks: list[Document],
) -> None:
    if len(chunks) != len(embeddings):
        msg = (
            f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) length mismatch"
        )
        raise ValueError(msg)
    client = get_qdrant_client()
    points: list[PointStruct] = []
    for i, chunk in enumerate(chunks):
        row = embeddings[i]
        vector = row.tolist() if hasattr(row, "tolist") else list(row)
        points.append(
            PointStruct(
                id=i,
                vector=vector,
                payload=_payload_for_chunk(chunk),
            )
        )
    client.upsert(collection_name=collection_name, points=points)
    logger.info("upserted %s points to collection %s", len(points), collection_name)


def search_similar(
    collection_name: str,
    query_vector: list[float],
    limit: int,
) -> list[dict[str, Any]]:
    """Nearest-neighbor search; collection must use COSINE (see create_collection_for_ingestion)."""
    client = get_qdrant_client()
    response = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=limit,
        with_payload=True,
    )
    out: list[dict[str, Any]] = []
    for hit in response.points:
        raw = hit.payload
        payload: dict[str, Any] = dict(raw) if isinstance(raw, dict) else {}
        raw_text = payload.get("text", "")
        text = raw_text if isinstance(raw_text, str) else str(raw_text)
        out.append(
            {
                "score": hit.score,
                "text": text,
                "payload": payload,
            }
        )
    return out
