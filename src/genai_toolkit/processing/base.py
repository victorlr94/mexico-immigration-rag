"""Protocol para chunkers de texto."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from genai_toolkit.ingestion.types import LoadedDocument
from genai_toolkit.retrieval.types import Chunk


@runtime_checkable
class TextChunker(Protocol):
    """Divide un LoadedDocument en Chunks listos para embedder y vectorstore.

    El chunker es el puente entre la capa de ingesta (texto crudo por página)
    y la capa de embeddings (fragmentos normalizados con metadata completa).
    Asigna chunk_index, genera el id estable y sanitiza el texto antes de
    indexar (mitigación de injection indirecto desde documentos — ver Security Skill).

    Implementaciones concretas: SlidingWindowChunker; futura: SemanticChunker.
    """

    def chunk(self, document: LoadedDocument) -> list[Chunk]:
        """Divide `document` en Chunks con metadata completa.

        Args:
            document: Documento cargado por un DocumentLoader.

        Returns:
            Lista de Chunks en orden, con chunk_index secuencial global
            (0-indexed, continuo a través de todas las páginas). Lista
            vacía si todas las páginas tienen texto vacío.
        """
        ...
