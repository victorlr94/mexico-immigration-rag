"""Capa de recuperación: tipos compartidos y contrato del Retriever."""

from genai_toolkit.retrieval.base import RetrievalError, Retriever
from genai_toolkit.retrieval.types import (
    Chunk,
    ChunkMetadata,
    RetrievalResult,
    ScoredChunk,
)

__all__ = [
    "Chunk",
    "ChunkMetadata",
    "RetrievalError",
    "RetrievalResult",
    "Retriever",
    "ScoredChunk",
]
