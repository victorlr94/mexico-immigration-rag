"""Chunker de ventana deslizante con sanitización de texto (ver Security Skill).

Responsabilidades de este módulo:
  1. Sanitizar texto extraído (eliminar caracteres de control) antes de indexar.
     Mitigación de prompt injection indirecto desde documentos — Security Skill.
  2. Dividir texto de cada página en ventanas de tamaño fijo con solapamiento,
     usando chunk_size y chunk_overlap de Settings (sin números mágicos).
  3. Asignar metadata completa a cada Chunk: id estable, chunk_index global,
     número de página, source_document. section=None hasta que se implemente
     detección de encabezados (Fase futura).
"""

from __future__ import annotations

import hashlib
import logging

from genai_toolkit.config.settings import Settings
from genai_toolkit.ingestion.types import LoadedDocument
from genai_toolkit.processing._sanitize import sanitize_text as _sanitize_text
from genai_toolkit.retrieval.types import Chunk, ChunkMetadata

logger = logging.getLogger(__name__)


def _split_into_windows(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Divide `text` en ventanas de `chunk_size` chars con solapamiento.

    Garantiza que no se pierde contenido: la unión de todas las ventanas cubre
    el texto completo (con repetición en las zonas de solapamiento). Ventanas
    vacías o de solo espacios se descartan.
    """
    if not text.strip():
        return []

    step = chunk_size - chunk_overlap
    windows: list[str] = []
    start = 0

    while start < len(text):
        window = text[start : start + chunk_size]
        if window.strip():
            windows.append(window)
        if start + chunk_size >= len(text):
            break
        start += step

    return windows


def _make_chunk_id(source_document: str, chunk_index: int) -> str:
    """Genera un id estable y único para el chunk a partir de su procedencia."""
    key = f"{source_document}:{chunk_index}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


class SlidingWindowChunker:
    """Divide un LoadedDocument en Chunks usando una ventana deslizante.

    Aplica sanitización de texto en cada página antes de dividir, conforme
    a la Security Skill (eliminar caracteres de control antes de indexar).
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()

    def chunk(self, document: LoadedDocument) -> list[Chunk]:
        """Divide `document` en Chunks con metadata completa.

        Args:
            document: Documento cargado por un DocumentLoader.

        Returns:
            Lista de Chunks en orden de aparición; chunk_index es secuencial
            y global a través de todas las páginas del documento. Vacía si
            todas las páginas tienen texto vacío o solo espacios.
        """
        result: list[Chunk] = []
        chunk_index = 0

        for raw_page in document.pages:
            sanitized = _sanitize_text(raw_page.text)
            windows = _split_into_windows(
                sanitized,
                self._settings.chunk_size,
                self._settings.chunk_overlap,
            )

            for window_text in windows:
                result.append(
                    Chunk(
                        id=_make_chunk_id(document.source, chunk_index),
                        text=window_text,
                        metadata=ChunkMetadata(
                            source_document=document.source,
                            page=raw_page.page_number,
                            section=None,
                            chunk_index=chunk_index,
                        ),
                    )
                )
                chunk_index += 1

        logger.info(
            "Chunkeado '%s': %d páginas → %d chunks",
            document.source,
            len(document.pages),
            len(result),
        )
        return result
