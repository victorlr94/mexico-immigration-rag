"""Contrato para la capa de recuperación (retrieval).

El Retriever es el componente que orquesta EmbeddingProvider + VectorStore
para responder "dada esta pregunta, ¿qué chunks son relevantes?". Es la
primera capa que decide si hay "contexto suficiente" — esa decisión vive aquí
(en has_sufficient_context, ver RetrievalResult) para que el resto del
pipeline no reinterprete scores por su cuenta.

Nota: a diferencia de EmbeddingProvider/VectorStore/LLMProvider, no se espera
más de una implementación intercambiable a corto plazo (no hay "otro tipo de
retriever" en el roadmap actual, como sí lo hay para vector stores o LLMs).
Aun así se define como Protocol por consistencia con el resto del toolkit y
para permitir mockear en tests sin esfuerzo.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from genai_toolkit.retrieval.types import RetrievalResult


@runtime_checkable
class Retriever(Protocol):
    """Recupera los chunks más relevantes para una consulta en lenguaje natural."""

    def retrieve(self, query: str) -> RetrievalResult:
        """Busca los chunks relevantes para `query`.

        Internamente: embebe la query (vía EmbeddingProvider.embed_query),
        busca en el VectorStore (vía VectorStore.search) y filtra por el
        score mínimo configurado para decidir has_sufficient_context.

        Args:
            query: La pregunta del usuario, ya validada por el
                Security Layer (longitud, sin patrones de injection).
                Este método asume que `query` es segura de procesar.

        Returns:
            RetrievalResult con los chunks encontrados (puede ser una
            lista vacía) y el flag de suficiencia de contexto.

        Raises:
            RetrievalError: Si el VectorStore o el EmbeddingProvider
                subyacentes fallan.
        """
        ...


class RetrievalError(Exception):
    """Fallo en la capa de recuperación."""
