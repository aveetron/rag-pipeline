import json
import logging
from pathlib import Path
import uuid

from aio_pika.abc import AbstractIncomingMessage
from langchain_community.document_loaders import DirectoryLoader, PyMuPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.handler.embedding import execute_embedding

logger = logging.getLogger(__name__)


async def handle_ingestion_message(message: AbstractIncomingMessage) -> None:
    async with message.process():
        raw = message.body.decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.info(
                "ingestion rk=%s non_json_body=%s",
                message.routing_key,
                raw[:500],
            )
            return

        logger.info(
            "ingestion rk=%s payload=%s",
            message.routing_key,
            payload,
        )
        embeddings = None
        if payload.get("source") == "pdf":
            path = Path(payload["stored_path"])
            if not path.exists():
                logger.error("ingestion pdf path missing: %s", path)
                return
            if path.is_file():
                documents = PyMuPDFLoader(str(path)).load()
            elif path.is_dir():
                documents = DirectoryLoader(
                    str(path),
                    loader_cls=PyMuPDFLoader,
                ).load()
            else:
                logger.error("ingestion path is not a file or directory: %s", path)
                return
            chunks = split_into_chunks(documents)
            logger.info(
                "ingestion pdf split into %s chunks (from %s docs)",
                len(chunks),
                len(documents),
            )
            if chunks:
                logger.debug("first chunk preview: %s", chunks[0].page_content[:200])

        if chunks: 
            embeddings = await execute_embedding(chunks)
            print(embeddings)
            logger.debug("embeddings shape %s", getattr(embeddings, "shape", None))
        else:
            logger.warning("no chunks to embed")
        """
            store into qdrant database as collection
        """
        if embeddings:
            # colleciton name would be a uuid
            pass

        # TODO: enqueue RAG pipeline (chunk, embed, index) from payload


def split_into_chunks(
    documents: list[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[Document]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = text_splitter.split_documents(documents)
    logger.info(
        "split %s documents into %s chunks",
        len(documents),
        len(chunks),
    )
    return chunks
