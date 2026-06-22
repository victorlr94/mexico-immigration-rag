"""Chunker recursivo basado en límites naturales del texto (ver ADR-007).

A diferencia de SlidingWindowChunker —que corta por número fijo de caracteres y
parte frases (y artículos legales) a la mitad— este chunker usa
RecursiveCharacterTextSplitter de langchain-text-splitters: intenta dividir en la
frontera natural más grande disponible (párrafo → línea → frase → cláusula →
palabra) antes de recurrir a un corte forzado. Combinado con un chunk_size mayor,
mantiene unidades semánticas completas (p. ej. "delito + su pena" en el mismo
chunk), lo que mejora la recuperación.

Responsabilidades (idénticas al Protocol TextChunker):
  1. Sanitizar el texto extraído (caracteres de control) antes de indexar
     —mitigación de prompt injection indirecto, Security Skill.
  2. Dividir el texto de cada página con el splitter recursivo, usando
     chunk_size y chunk_overlap de Settings (sin números mágicos).
  3. Asignar metadata completa: id estable, chunk_index global, número de
     página y source_document. section=None hasta que exista detección de
     encabezados (fase futura).

Se chunkea por página (no a través de páginas) para conservar el número de
página en la cita —un diferenciador del producto.
"""

from __future__ import annotations

import hashlib
import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter

from genai_toolkit.config.settings import Settings
from genai_toolkit.ingestion.types import LoadedDocument
from genai_toolkit.processing._sanitize import sanitize_text
from genai_toolkit.retrieval.types import Chunk, ChunkMetadata

logger = logging.getLogger(__name__)

# Separadores en orden de preferencia para prosa legal en español: primero
# fronteras de párrafo, luego de frase y cláusula, y solo al final palabra/char.
_SEPARATORS = ["\n\n", "\n", ". ", "; ", ", ", " ", ""]


def _make_chunk_id(source_document: str, chunk_index: int) -> str:
    """Genera un id estable y único para el chunk a partir de su procedencia."""
    key = f"{source_document}:{chunk_index}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


class RecursiveTextChunker:
    """Divide un LoadedDocument en Chunks respetando límites naturales del texto.

    Implementa el Protocol TextChunker. Aplica sanitización por página antes de
    dividir (Security Skill) y delega la división en
    RecursiveCharacterTextSplitter, parametrizado desde Settings.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self._settings.chunk_size,
            chunk_overlap=self._settings.chunk_overlap,
            separators=_SEPARATORS,
            keep_separator=True,
            length_function=len,
        )

    def chunk(self, document: LoadedDocument) -> list[Chunk]:
        """Divide `document` en Chunks con metadata completa.

        Args:
            document: Documento cargado por un DocumentLoader.

        Returns:
            Lista de Chunks en orden de aparición; chunk_index es secuencial y
            global a través de todas las páginas. Vacía si todas las páginas
            tienen texto vacío o solo espacios.
        """
        result: list[Chunk] = []
        chunk_index = 0

        for raw_page in document.pages:
            sanitized = sanitize_text(raw_page.text)
            if not sanitized.strip():
                continue

            for piece in self._splitter.split_text(sanitized):
                if not piece.strip():
                    continue
                result.append(
                    Chunk(
                        id=_make_chunk_id(document.source, chunk_index),
                        text=piece,
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
            "Chunkeado '%s' (recursivo): %d páginas → %d chunks",
            document.source,
            len(document.pages),
            len(result),
        )
        return result
