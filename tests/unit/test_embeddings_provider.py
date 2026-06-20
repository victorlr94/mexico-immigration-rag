"""Unit tests para SentenceTransformerProvider.

El modelo de embeddings real (multilingual-e5-small) NO se carga en estos
tests: es pesado (~117 MB), requiere descarga y haría el suite lento e
impredecible en CI. SentenceTransformer se mockea completamente; lo que se
verifica es la lógica del provider (prefijos, conversión de tipos, manejo de
errores) sin depender del modelo subyacente.

Un test de integración con el modelo real puede añadirse en tests/integration/
cuando exista esa capa (Fase 3).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from genai_toolkit.config.settings import Settings
from genai_toolkit.embeddings.base import EmbeddingError
from genai_toolkit.embeddings.sentence_transformer_provider import (
    SentenceTransformerProvider,
)

_MODEL_PATH = (
    "genai_toolkit.embeddings.sentence_transformer_provider.SentenceTransformer"
)
_DIM = 384


def _make_mock_model(dimension: int = _DIM) -> MagicMock:
    """Crea un mock de SentenceTransformer con comportamiento realista."""
    model = MagicMock()
    model.get_sentence_embedding_dimension.return_value = dimension

    def fake_encode(
        texts: list[str] | str, normalize_embeddings: bool = False
    ) -> np.ndarray:  # type: ignore[type-arg]
        if isinstance(texts, str):
            return np.zeros(dimension, dtype=np.float32)
        return np.zeros((len(texts), dimension), dtype=np.float32)

    model.encode.side_effect = fake_encode
    return model


@pytest.fixture()
def provider() -> SentenceTransformerProvider:
    """Provider con modelo mockeado; Settings por defecto."""
    with patch(_MODEL_PATH, return_value=_make_mock_model()):
        return SentenceTransformerProvider()


@pytest.fixture()
def small_settings() -> Settings:
    return Settings(embedding_model="intfloat/multilingual-e5-small")


# ---------------------------------------------------------------------------
# Construcción
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_dimension_reported_correctly(
        self, provider: SentenceTransformerProvider
    ) -> None:
        assert provider.dimension == _DIM

    def test_raises_embedding_error_if_model_has_no_dimension(self) -> None:
        mock = _make_mock_model()
        mock.get_sentence_embedding_dimension.return_value = None
        with (
            patch(_MODEL_PATH, return_value=mock),
            pytest.raises(EmbeddingError, match="dimensión"),
        ):
            SentenceTransformerProvider()

    def test_uses_embedding_model_from_settings(self, small_settings: Settings) -> None:
        with patch(_MODEL_PATH) as mock_cls:
            mock_cls.return_value = _make_mock_model()
            SentenceTransformerProvider(small_settings)
        mock_cls.assert_called_once_with("intfloat/multilingual-e5-small")


# ---------------------------------------------------------------------------
# embed_documents
# ---------------------------------------------------------------------------


class TestEmbedDocuments:
    def test_returns_one_vector_per_text(
        self, provider: SentenceTransformerProvider
    ) -> None:
        result = provider.embed_documents(["texto uno", "texto dos", "texto tres"])
        assert len(result) == 3

    def test_vector_has_correct_dimension(
        self, provider: SentenceTransformerProvider
    ) -> None:
        result = provider.embed_documents(["texto"])
        assert len(result[0]) == _DIM

    def test_returns_list_of_float_not_numpy(
        self, provider: SentenceTransformerProvider
    ) -> None:
        result = provider.embed_documents(["texto"])
        assert isinstance(result, list)
        assert isinstance(result[0], list)
        assert isinstance(result[0][0], float)

    def test_adds_passage_prefix(self, provider: SentenceTransformerProvider) -> None:
        provider.embed_documents(["mi texto"])
        call_args = provider._model.encode.call_args
        texts_passed = call_args[0][0]
        assert texts_passed == ["passage: mi texto"]

    def test_uses_normalize_embeddings(
        self, provider: SentenceTransformerProvider
    ) -> None:
        provider.embed_documents(["texto"])
        call_kwargs = provider._model.encode.call_args[1]
        assert call_kwargs.get("normalize_embeddings") is True

    def test_empty_list_raises_value_error(
        self, provider: SentenceTransformerProvider
    ) -> None:
        with pytest.raises(ValueError, match="vacía"):
            provider.embed_documents([])

    def test_model_error_raises_embedding_error(
        self, provider: SentenceTransformerProvider
    ) -> None:
        provider._model.encode.side_effect = RuntimeError("CUDA out of memory")
        with pytest.raises(EmbeddingError, match="Error al embeber documentos"):
            provider.embed_documents(["texto"])


# ---------------------------------------------------------------------------
# embed_query
# ---------------------------------------------------------------------------


class TestEmbedQuery:
    def test_returns_single_vector(self, provider: SentenceTransformerProvider) -> None:
        result = provider.embed_query("¿Qué documentos necesito?")
        assert isinstance(result, list)
        assert len(result) == _DIM

    def test_returns_list_of_float_not_numpy(
        self, provider: SentenceTransformerProvider
    ) -> None:
        result = provider.embed_query("consulta")
        assert isinstance(result[0], float)

    def test_adds_query_prefix(self, provider: SentenceTransformerProvider) -> None:
        provider.embed_query("mi consulta")
        call_args = provider._model.encode.call_args
        text_passed = call_args[0][0]
        assert text_passed == "query: mi consulta"

    def test_uses_normalize_embeddings(
        self, provider: SentenceTransformerProvider
    ) -> None:
        provider.embed_query("consulta")
        call_kwargs = provider._model.encode.call_args[1]
        assert call_kwargs.get("normalize_embeddings") is True

    def test_model_error_raises_embedding_error(
        self, provider: SentenceTransformerProvider
    ) -> None:
        provider._model.encode.side_effect = RuntimeError("tokenizer error")
        with pytest.raises(EmbeddingError, match="Error al embeber consulta"):
            provider.embed_query("consulta")


# ---------------------------------------------------------------------------
# Prefijos query vs passage son distintos
# ---------------------------------------------------------------------------


class TestQueryVsDocumentPrefixes:
    def test_query_and_document_use_different_prefixes(
        self, provider: SentenceTransformerProvider
    ) -> None:
        """e5 requiere prefijos distintos para query y passage."""
        provider.embed_query("consulta")
        query_text = provider._model.encode.call_args[0][0]

        provider.embed_documents(["documento"])
        doc_text = provider._model.encode.call_args[0][0][0]

        assert query_text.startswith("query: ")
        assert doc_text.startswith("passage: ")
