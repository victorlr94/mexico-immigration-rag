"""Implementación concreta del Retriever.

Orquesta EmbeddingProvider + VectorStore en un único método retrieve():
  1. Embebe la query con EmbeddingProvider.embed_query().
  2. Busca los top_k chunks más cercanos en VectorStore.search().
  3. Filtra los resultados por el umbral min_score.
  4. Decide has_sufficient_context: True si al menos un chunk superó min_score.

La decisión de "suficiente contexto" vive aquí (no en el pipeline que llama)
para que el criterio sea único y testeable de forma aislada.
"""

from __future__ import annotations

import logging

from genai_toolkit.config.settings import Settings
from genai_toolkit.embeddings.base import EmbeddingError, EmbeddingProvider
from genai_toolkit.retrieval.base import RetrievalError
from genai_toolkit.retrieval.types import RetrievalResult, ScoredChunk
from genai_toolkit.vectorstore.base import VectorStore, VectorStoreError

logger = logging.getLogger(__name__)


class SimpleRetriever:
    """Retriever que delega embeddings y búsqueda a proveedores inyectados.

    Los proveedores se inyectan en el constructor (no se crean internamente)
    para que el llamador controle el ciclo de vida de modelos y conexiones.
    """

    def __init__(
        self,
        embedder: EmbeddingProvider,
        store: VectorStore,
        settings: Settings | None = None,
    ) -> None:
        self._embedder = embedder
        self._store = store
        _s = settings or Settings()
        self._top_k: int = _s.retrieval_top_k
        self._min_score: float = _s.retrieval_min_score

    def retrieve(self, query: str) -> RetrievalResult:
        """Embebe la query, busca en el store y filtra por min_score."""
        try:
            query_vec = self._embedder.embed_query(query)
        except EmbeddingError as exc:
            raise RetrievalError(f"Error al embeber la consulta: {exc}") from exc

        try:
            candidates: list[ScoredChunk] = self._store.search(query_vec, self._top_k)
        except VectorStoreError as exc:
            raise RetrievalError(f"Error al buscar en el vector store: {exc}") from exc

        above_threshold = [c for c in candidates if c.score >= self._min_score]

        logger.debug(
            "retrieve: query=%r candidates=%d above_threshold=%d min_score=%.2f",
            query[:50],
            len(candidates),
            len(above_threshold),
            self._min_score,
        )

        return RetrievalResult(
            query=query,
            chunks=above_threshold,
            has_sufficient_context=len(above_threshold) > 0,
        )
