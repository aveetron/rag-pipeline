import asyncio
import json
import logging
import time
from typing import Any, AsyncIterator

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.handler.embedding import execute_embedding
from app.models.ask import AskRequest, AskResponse
from config.llm import resolve_openai_chat_completions_url
from config.qdrant import get_qdrant_client, search_similar
from config.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query", tags=["query"])

RAG_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer ONLY from context. "
    "If not found, say you don't know."
)


def _llm_headers() -> dict[str, str]:
    settings = get_settings()
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"
    return headers


def _llm_http_timeout() -> httpx.Timeout:
    settings = get_settings()
    return httpx.Timeout(
        connect=15.0,
        read=settings.llm_timeout_seconds,
        write=120.0,
        pool=10.0,
    )


def _llm_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=_llm_http_timeout(),
        trust_env=False,
        limits=httpx.Limits(max_keepalive_connections=5, max_connections=20),
    )


def _sse(data: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(data)}\n\n".encode()


def _truncate_context(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    logger.info(
        "RAG context truncated from %s to %s chars",
        len(text),
        max_chars,
    )
    return text[: max_chars - 3] + "..."


def _source_texts(hits: list[dict[str, Any]]) -> list[str]:
    return [h["text"] for h in hits if h.get("text")]


async def _retrieve(body: AskRequest):
    t = time.perf_counter()
    settings = get_settings()

    qdrant = get_qdrant_client()
    exists = await asyncio.to_thread(qdrant.collection_exists, body.collection_name)
    if not exists:
        raise HTTPException(404, "Collection not found")

    embeddings = await execute_embedding([body.question])
    vector = embeddings[0].tolist()

    hits = await asyncio.to_thread(
        search_similar,
        body.collection_name,
        vector,
        body.top_k,
    )

    logger.info("RAG retrieve done in %.2fs", time.perf_counter() - t)

    if not hits:
        raise HTTPException(404, "No results found")

    context = "\n---\n".join(h["text"] for h in hits if h.get("text"))
    context = _truncate_context(context, settings.max_rag_context_chars)

    messages = [
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {body.question}",
        },
    ]

    return messages, hits


async def _stream_llm(messages: list[dict[str, Any]]) -> AsyncIterator[bytes]:
    settings = get_settings()
    url = resolve_openai_chat_completions_url(settings.llm_base_url)

    payload = {
        "model": settings.llm_model,
        "messages": messages,
        "stream": True,
        "temperature": 0.2,
    }

    async with _llm_client() as client:
        async with client.stream(
            "POST",
            url,
            json=payload,
            headers=_llm_headers(),
        ) as r:
            r.raise_for_status()

            async for raw in r.aiter_lines():
                line = raw.strip()
                if not line or not line.startswith("data: "):
                    continue

                data = line[6:].strip()
                if data == "[DONE]":
                    yield b"data: [DONE]\n\n"
                    break

                try:
                    obj = json.loads(data)
                    delta = (obj.get("choices") or [{}])[0].get("delta") or {}
                    content = delta.get("content")
                    if content:
                        yield _sse({"delta": content})
                except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                    continue


def _http_exception_detail(exc: HTTPException) -> str:
    d = exc.detail
    if isinstance(d, str):
        return d
    return str(d)


@router.post("/ask/stream")
async def ask_stream(body: AskRequest):
    async def generator() -> AsyncIterator[bytes]:
        try:
            messages, hits = await _retrieve(body)
        except HTTPException as e:
            yield _sse({"error": _http_exception_detail(e)})
            return
        except Exception as e:
            logger.exception("RAG retrieve failed")
            yield _sse({"error": str(e)})
            return

        async for chunk in _stream_llm(messages):
            yield chunk

    return StreamingResponse(
        generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _chat(messages: list[dict[str, Any]]) -> str:
    settings = get_settings()
    url = resolve_openai_chat_completions_url(settings.llm_base_url)

    async with _llm_client() as client:
        r = await client.post(
            url,
            json={
                "model": settings.llm_model,
                "messages": messages,
                "temperature": 0.2,
            },
            headers=_llm_headers(),
        )
        r.raise_for_status()
        data = r.json()
        return str(data["choices"][0]["message"]["content"]).strip()


@router.post("/ask", response_model=AskResponse)
async def ask(body: AskRequest):
    messages, hits = await _retrieve(body)
    answer = await _chat(messages)
    return AskResponse(answer=answer, sources=_source_texts(hits))


async def warmup_llm() -> None:
    logger.info("Warming up LLM...")
    try:
        await _chat([{"role": "user", "content": "hello"}])
        logger.info("LLM warmup done")
    except Exception:
        logger.warning("LLM warmup failed", exc_info=True)
