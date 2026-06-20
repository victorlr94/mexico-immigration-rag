"""Capa de embeddings: contrato e implementación concreta."""

from genai_toolkit.embeddings.base import EmbeddingError, EmbeddingProvider
from genai_toolkit.embeddings.sentence_transformer_provider import (
    SentenceTransformerProvider,
)

__all__ = ["EmbeddingError", "EmbeddingProvider", "SentenceTransformerProvider"]
