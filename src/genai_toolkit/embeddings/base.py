"""Contrato para proveedores de embeddings.

Cualquier modelo de embeddings (Sentence Transformers, OpenAI, Cohere, etc.)
puede implementar este Protocol y ser intercambiado sin tocar el resto del
pipeline. La implementación concreta (ej. SentenceTransformerProvider) vive en
un módulo aparte y se inyecta donde se necesite — nunca se importa
directamente fuera de la capa de composición del pipeline.

Por qué Protocol y no ABC: Protocol da "structural typing" — cualquier clase
que tenga estos métodos con estas firmas cumple el contrato automáticamente,
sin necesidad de herencia explícita. Esto es valioso para wrappers de
librerías externas (ej. envolver un cliente de OpenAI) sin forzar una
jerarquía de clases artificial.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Convierte texto en vectores de embedding.

    Implementaciones esperadas: SentenceTransformerProvider (local, por
    defecto), y opcionalmente wrappers de APIs externas si en el futuro se
    justifica (ver nota de costo en el README del proyecto).
    """

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embebe un lote de textos (uso: indexar documentos).

        Args:
            texts: Lista de textos a embeber. No debe estar vacía;
                el llamador es responsable de filtrar textos vacíos
                antes de invocar este método.

        Returns:
            Lista de vectores, en el mismo orden que `texts`. Cada vector
            es una lista de floats de dimensión fija (depende del modelo
            subyacente, ej. 384 para all-MiniLM-L6-v2).

        Raises:
            EmbeddingError: Si el modelo subyacente falla al procesar el
                lote (ej. texto demasiado largo para la ventana del modelo).
        """
        ...

    def embed_query(self, text: str) -> list[float]:
        """Embebe un único texto de consulta (uso: búsqueda en tiempo real).

        Separado de `embed_documents` porque algunos modelos (ej. e5,
        BGE) usan prefijos o normalización distinta para "query" vs
        "passage" — el Protocol expone esa distinción aunque una
        implementación simple pueda delegar ambos métodos al mismo código.

        Args:
            text: El texto de la consulta del usuario, ya validado.

        Returns:
            Vector de embedding de la misma dimensión que
            `embed_documents`.

        Raises:
            EmbeddingError: Si el modelo subyacente falla.
        """
        ...

    @property
    def dimension(self) -> int:
        """Dimensión de los vectores que produce este provider.

        Necesario para validar compatibilidad con el VectorStore al
        inicializar la colección (ej. Chroma necesita saber la dimensión
        de antemano en algunos backends).
        """
        ...


class EmbeddingError(Exception):
    """Fallo al generar embeddings."""
