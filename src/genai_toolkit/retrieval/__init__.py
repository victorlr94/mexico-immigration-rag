"""Capa de recuperación: tipos compartidos, contrato e implementación."""

from genai_toolkit.retrieval.base import RetrievalError, Retriever
from genai_toolkit.retrieval.simple_retriever import SimpleRetriever
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
    "SimpleRetriever",
]
