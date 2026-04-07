import asyncio
import logging
from collections.abc import Sequence
from typing import TypeAlias

import numpy as np
from langchain_core.documents import Document
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

TextsOrDocs: TypeAlias = Sequence[str] | Sequence[Document]


def _to_strings(texts: TextsOrDocs) -> list[str]:
    if not texts:
        return []
    first = next(iter(texts))
    if isinstance(first, Document):
        return [d.page_content for d in texts]  # type: ignore[arg-type, misc]
    return list(texts)  # type: ignore[arg-type]


class Embeddings:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self.model = self._load_model_sync()

    def _load_model_sync(self) -> SentenceTransformer:
        logger.info("Loading model %s...", self.model_name)
        model = SentenceTransformer(self.model_name)
        dim = model.get_sentence_embedding_dimension()
        logger.info(
            "Model %s loaded successfully, embedding dimension %s",
            self.model_name,
            dim,
        )
        return model

    async def generate_embeddings(self, texts: TextsOrDocs) -> np.ndarray:
        strings = _to_strings(texts)
        if not strings:
            raise ValueError("No text to embed")
        # SentenceTransformer.encode is synchronous; avoid blocking the event loop.
        embeddings = await asyncio.to_thread(
            self.model.encode,
            strings,
            show_progress_bar=False,
        )
        logger.info("Generated embeddings shape %s", embeddings.shape)
        return embeddings

    def get_embedding_dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()


_embeddings: Embeddings | None = None


def get_embeddings() -> Embeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = Embeddings()
    return _embeddings


async def execute_embedding(texts: TextsOrDocs) -> np.ndarray:
    return await get_embeddings().generate_embeddings(texts)
