"""Proveedor de embeddings con Sentence Transformers (intfloat/multilingual-e5-small).

Por qué multilingual-e5:
  - Multilingüe: soporta español e inglés en el mismo espacio vectorial.
  - Ligero: ~117 MB, corre en CPU sin GPU requerida.
  - Requiere prefijos de rol: "passage: " para documentos, "query: " para
    consultas — razón directa por la que EmbeddingProvider tiene embed_documents
    y embed_query separados, en lugar de un único método genérico.

Normalización:
  normalize_embeddings=True produce vectores unitarios, lo que hace que la
  similitud coseno sea equivalente al producto punto — necesario para que
  Chroma opere correctamente con la métrica cosine.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from sentence_transformers import SentenceTransformer

from genai_toolkit.config.settings import Settings
from genai_toolkit.embeddings.base import EmbeddingError

logger = logging.getLogger(__name__)


class SentenceTransformerProvider:
    """Implementación concreta de EmbeddingProvider usando Sentence Transformers.

    Carga el modelo en el constructor (operación costosa, ~segundos la primera
    vez con descarga incluida). Diseñado para instanciarse una sola vez y
    reutilizarse durante toda la sesión.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        model_name = self._settings.embedding_model
        logger.info("Cargando modelo de embeddings: %s", model_name)
        self._model: SentenceTransformer = SentenceTransformer(model_name)
        raw_dim = self._model.get_sentence_embedding_dimension()
        if raw_dim is None:
            raise EmbeddingError(
                f"El modelo '{model_name}' no reporta dimensión de embedding."
            )
        self._dimension: int = raw_dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embebe un lote de textos de documento con el prefijo 'passage:'.

        Args:
            texts: Lista de textos a embeber. No debe estar vacía.

        Returns:
            Lista de vectores normalizados, uno por texto, en el mismo orden.

        Raises:
            ValueError: Si `texts` está vacía.
            EmbeddingError: Si el modelo falla al procesar el lote.
        """
        if not texts:
            raise ValueError("texts no debe estar vacía.")
        prefixed = [f"passage: {t}" for t in texts]
        try:
            raw: Any = self._model.encode(prefixed, normalize_embeddings=True)
            return cast(list[list[float]], [v.tolist() for v in raw])
        except Exception as exc:
            model = self._settings.embedding_model
            raise EmbeddingError(
                f"Error al embeber documentos con '{model}': {exc}"
            ) from exc

    def embed_query(self, text: str) -> list[float]:
        """Embebe una consulta con el prefijo 'query:'.

        Args:
            text: Texto de la consulta, ya validado.

        Returns:
            Vector normalizado de la misma dimensión que embed_documents.

        Raises:
            EmbeddingError: Si el modelo falla.
        """
        try:
            raw: Any = self._model.encode(f"query: {text}", normalize_embeddings=True)
            return cast(list[float], raw.tolist())
        except Exception as exc:
            model = self._settings.embedding_model
            raise EmbeddingError(
                f"Error al embeber consulta con '{model}': {exc}"
            ) from exc

    @property
    def dimension(self) -> int:
        """Dimensión de los vectores (384 para multilingual-e5-small)."""
        return self._dimension
