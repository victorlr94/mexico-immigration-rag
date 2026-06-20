"""Unit tests para SimpleRetriever.

EmbeddingProvider y VectorStore se mockean con MagicMock: la lógica a
verificar es la orquestación (orden de llamadas, filtrado por min_score,
construcción de RetrievalResult) — no el comportamiento de los proveedores
subyacentes, que tienen sus propios tests.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from genai_toolkit.config.settings import Settings
from genai_toolkit.embeddings.base import EmbeddingError
from genai_toolkit.retrieval.base import RetrievalError
from genai_toolkit.retrieval.simple_retriever import SimpleRetriever
from genai_toolkit.retrieval.types import (
    Chunk,
    ChunkMetadata,
    RetrievalResult,
    ScoredChunk,
)
from genai_toolkit.vectorstore.base import VectorStoreError

_DIM = 4
_QUERY_VEC = [0.25, 0.25, 0.25, 0.25]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scored_chunk(chunk_id: str = "c0", score: float = 0.90) -> ScoredChunk:
    meta = ChunkMetadata(source_document="doc.pdf", page=1, chunk_index=0)
    chunk = Chunk(id=chunk_id, text="texto", metadata=meta)
    return ScoredChunk(chunk=chunk, score=score)


def _make_embedder(vec: list[float] = _QUERY_VEC) -> MagicMock:
    embedder = MagicMock()
    embedder.embed_query.return_value = vec
    return embedder


def _make_store(results: list[ScoredChunk] | None = None) -> MagicMock:
    store = MagicMock()
    store.search.return_value = results or []
    return store


def _make_settings(top_k: int = 4, min_score: float = 0.70) -> Settings:
    return Settings(retrieval_top_k=top_k, retrieval_min_score=min_score)


# ---------------------------------------------------------------------------
# Construcción
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_uses_top_k_from_settings(self) -> None:
        store = _make_store()
        retriever = SimpleRetriever(_make_embedder(), store, _make_settings(top_k=7))
        retriever.retrieve("consulta")
        store.search.assert_called_once_with(_QUERY_VEC, 7)

    def test_uses_min_score_from_settings(self) -> None:
        chunk_high = _make_scored_chunk("high", score=0.80)
        chunk_low = _make_scored_chunk("low", score=0.50)
        store = _make_store([chunk_high, chunk_low])
        retriever = SimpleRetriever(
            _make_embedder(), store, _make_settings(min_score=0.75)
        )
        result = retriever.retrieve("consulta")
        assert len(result.chunks) == 1
        assert result.chunks[0].chunk.id == "high"

    def test_uses_default_settings_when_none_passed(self) -> None:
        retriever = SimpleRetriever(_make_embedder(), _make_store())
        result = retriever.retrieve("consulta")
        assert isinstance(result, RetrievalResult)


# ---------------------------------------------------------------------------
# Flujo de llamadas
# ---------------------------------------------------------------------------


class TestCallFlow:
    def test_embeds_query_before_searching(self) -> None:
        embedder = _make_embedder()
        store = _make_store()
        retriever = SimpleRetriever(embedder, store, _make_settings())
        retriever.retrieve("¿Qué documentos necesito?")
        embedder.embed_query.assert_called_once_with("¿Qué documentos necesito?")

    def test_passes_query_vector_to_store(self) -> None:
        custom_vec = [0.1, 0.2, 0.3, 0.4]
        embedder = _make_embedder(vec=custom_vec)
        store = _make_store()
        retriever = SimpleRetriever(embedder, store, _make_settings(top_k=3))
        retriever.retrieve("query")
        store.search.assert_called_once_with(custom_vec, 3)

    def test_query_preserved_in_result(self) -> None:
        retriever = SimpleRetriever(_make_embedder(), _make_store(), _make_settings())
        result = retriever.retrieve("mi consulta exacta")
        assert result.query == "mi consulta exacta"


# ---------------------------------------------------------------------------
# Filtrado por min_score
# ---------------------------------------------------------------------------


class TestScoreFiltering:
    def test_chunks_above_threshold_included(self) -> None:
        chunks = [
            _make_scored_chunk("a", score=0.85),
            _make_scored_chunk("b", score=0.70),
            _make_scored_chunk("c", score=0.69),
        ]
        store = _make_store(chunks)
        retriever = SimpleRetriever(
            _make_embedder(), store, _make_settings(min_score=0.70)
        )
        result = retriever.retrieve("consulta")
        ids = [sc.chunk.id for sc in result.chunks]
        assert "a" in ids
        assert "b" in ids
        assert "c" not in ids

    def test_chunk_exactly_at_threshold_included(self) -> None:
        store = _make_store([_make_scored_chunk(score=0.70)])
        retriever = SimpleRetriever(
            _make_embedder(), store, _make_settings(min_score=0.70)
        )
        result = retriever.retrieve("consulta")
        assert len(result.chunks) == 1

    def test_all_below_threshold_yields_empty_chunks(self) -> None:
        chunks = [_make_scored_chunk("x", score=0.50)]
        store = _make_store(chunks)
        retriever = SimpleRetriever(
            _make_embedder(), store, _make_settings(min_score=0.70)
        )
        result = retriever.retrieve("consulta")
        assert result.chunks == []

    def test_empty_store_yields_empty_chunks(self) -> None:
        retriever = SimpleRetriever(_make_embedder(), _make_store([]), _make_settings())
        result = retriever.retrieve("consulta")
        assert result.chunks == []


# ---------------------------------------------------------------------------
# has_sufficient_context
# ---------------------------------------------------------------------------


class TestSufficientContext:
    def test_true_when_at_least_one_chunk_above_threshold(self) -> None:
        store = _make_store([_make_scored_chunk(score=0.80)])
        retriever = SimpleRetriever(
            _make_embedder(), store, _make_settings(min_score=0.70)
        )
        result = retriever.retrieve("consulta")
        assert result.has_sufficient_context is True

    def test_false_when_no_chunks_above_threshold(self) -> None:
        store = _make_store([_make_scored_chunk(score=0.50)])
        retriever = SimpleRetriever(
            _make_embedder(), store, _make_settings(min_score=0.70)
        )
        result = retriever.retrieve("consulta")
        assert result.has_sufficient_context is False

    def test_false_when_store_is_empty(self) -> None:
        retriever = SimpleRetriever(_make_embedder(), _make_store([]), _make_settings())
        result = retriever.retrieve("consulta")
        assert result.has_sufficient_context is False


# ---------------------------------------------------------------------------
# Propagación de errores
# ---------------------------------------------------------------------------


class TestErrorPropagation:
    def test_embedding_error_raises_retrieval_error(self) -> None:
        embedder = _make_embedder()
        embedder.embed_query.side_effect = EmbeddingError("modelo caído")
        retriever = SimpleRetriever(embedder, _make_store(), _make_settings())
        with pytest.raises(RetrievalError, match="Error al embeber"):
            retriever.retrieve("consulta")

    def test_vectorstore_error_raises_retrieval_error(self) -> None:
        store = _make_store()
        store.search.side_effect = VectorStoreError("ChromaDB caído")
        retriever = SimpleRetriever(_make_embedder(), store, _make_settings())
        with pytest.raises(RetrievalError, match="Error al buscar"):
            retriever.retrieve("consulta")

    def test_embedding_error_does_not_call_store(self) -> None:
        embedder = _make_embedder()
        embedder.embed_query.side_effect = EmbeddingError("fallo")
        store = _make_store()
        retriever = SimpleRetriever(embedder, store, _make_settings())
        with pytest.raises(RetrievalError):
            retriever.retrieve("consulta")
        store.search.assert_not_called()
