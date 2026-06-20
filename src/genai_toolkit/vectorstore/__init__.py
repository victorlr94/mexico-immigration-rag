"""Almacén vectorial: contrato e implementación concreta con ChromaDB."""

from genai_toolkit.vectorstore.base import VectorStore, VectorStoreError
from genai_toolkit.vectorstore.chroma import ChromaVectorStore

__all__ = ["ChromaVectorStore", "VectorStore", "VectorStoreError"]
