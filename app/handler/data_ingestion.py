from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.document_loaders import SQLDatabaseLoader
import os
import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Callable, Awaitable

from aio_pika.abc import AbstractIncomingMessage
from langchain_community.document_loaders import (
    DirectoryLoader,
    PyMuPDFLoader,
    WebBaseLoader,
)
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.handler.embedding import execute_embedding
from config.qdrant import create_collection_for_ingestion, upsert_chunk_embeddings

logger = logging.getLogger(__name__)

# ── Source loader type ────────────────────────────────────────────────────────
# Each loader receives the raw payload dict and returns a list of Documents.
# Raise ValueError to signal a bad/missing field — the dispatcher will log it.
SourceLoader = Callable[[dict], Awaitable[list[Document]] | list[Document]]


# ── Loader implementations ────────────────────────────────────────────────────

def _load_pdf(payload: dict) -> list[Document]:
    path = Path(payload["stored_path"])
    if not path.exists():
        raise ValueError(f"pdf path missing: {path}")
    if path.is_file():
        return PyMuPDFLoader(str(path)).load()
    if path.is_dir():
        return DirectoryLoader(str(path), loader_cls=PyMuPDFLoader).load()
    raise ValueError(f"path is neither file nor directory: {path}")


def _load_text(payload: dict) -> list[Document]:
    text = payload.get("text")
    if not text:
        raise ValueError("'text' field is missing or empty")
    return [Document(page_content=text)]


def _load_url(payload: dict) -> list[Document]:
    url = payload.get("url")
    if not url:
        raise ValueError("'url' field is missing or empty")
    return WebBaseLoader(url).load()

SUPPORTED_DIALECTS = ("sqlite", "postgresql", "mysql", "mariadb", "mssql", "oracle")

def _load_db(payload: dict) -> list[Document]:
    db_uri = payload.get("db")
    if not db_uri:
        raise ValueError("'db' field is missing or empty")

    dialect = db_uri.split("://")[0].split("+")[0].lower()
    if dialect not in SUPPORTED_DIALECTS:
        raise ValueError(f"Unsupported dialect '{dialect}'. Supported: {SUPPORTED_DIALECTS}")

    db = SQLDatabase.from_uri(db_uri)
    tables = db.get_usable_table_names()

    if not tables:
        raise ValueError(f"No usable tables found in database: {db_uri}")

    logger.info("_load_db found %d tables: %s", len(tables), tables)

    all_docs = []

    for table in tables:
        loader = SQLDatabaseLoader(
            query=f'SELECT * FROM "{table}"',
            db=db,
            page_content_mapper=lambda row, t=table: str(row),
            metadata_mapper=lambda row, t=table, uri=db_uri, d=dialect: {
                "table": t,
                "source": uri,
                "dialect": d,
            },
        )
        docs = loader.load()
        logger.info("_load_db table=%s loaded %d docs", table, len(docs))
        all_docs.extend(docs)

    logger.info("_load_db total=%d documents", len(all_docs))
    return all_docs

# ── Registry ──────────────────────────────────────────────────────────────────
# To add a new source: implement a loader above, then add one line here.

SOURCE_HANDLERS: dict[str, SourceLoader] = {
    "pdf": _load_pdf,
    "text": _load_text,
    "url": _load_url,
    "db": _load_db,
}


# ── Shared pipeline ───────────────────────────────────────────────────────────

def split_into_chunks(
    documents: list[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    logger.info("split %d documents into %d chunks", len(documents), len(chunks))
    return chunks


async def _index_chunks(chunks: list[Document]) -> None:
    """Embed chunks and upsert them into a new Qdrant collection."""
    embeddings = await execute_embedding(chunks)
    logger.debug("embeddings shape %s", getattr(embeddings, "shape", None))

    if embeddings is None or len(embeddings) == 0:
        logger.warning("no embeddings produced — skipping upsert")
        return

    collection_name = str(uuid.uuid4())
    vector_size = int(embeddings.shape[1])

    await asyncio.to_thread(create_collection_for_ingestion, collection_name, vector_size)
    await asyncio.to_thread(upsert_chunk_embeddings, collection_name, embeddings, chunks)

    logger.info("qdrant indexed %d vectors in collection %s", len(embeddings), collection_name)


# ── Message handler ───────────────────────────────────────────────────────────

async def handle_ingestion_message(message: AbstractIncomingMessage) -> None:
    async with message.process():
        raw = message.body.decode("utf-8", errors="replace")

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.info("ingestion rk=%s non_json_body=%s", message.routing_key, raw[:500])
            return

        logger.info("ingestion rk=%s payload=%s", message.routing_key, payload)

        source = payload.get("source")
        loader = SOURCE_HANDLERS.get(source)

        if loader is None:
            logger.error("ingestion unknown source: %r (registered: %s)", source, list(SOURCE_HANDLERS))
            return

        try:
            # Loaders may be sync or async — handle both transparently
            result = loader(payload)
            documents: list[Document] = await result if asyncio.iscoroutine(result) else result
        except (ValueError, KeyError) as exc:
            logger.error("ingestion loader error [source=%s]: %s", source, exc)
            return

        logger.info("ingestion [source=%s] loaded %d documents", source, len(documents))

        chunks = split_into_chunks(documents)
        if not chunks:
            logger.warning("no chunks produced — skipping embedding")
            return

        logger.debug("first chunk preview: %s", chunks[0].page_content[:200])
        await _index_chunks(chunks)