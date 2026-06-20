"""Tipos de datos y excepciones de la capa de ingesta de documentos."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RawPage:
    """Una página extraída de un documento, antes del chunking.

    Attributes:
        text: Texto extraído (vacío si la página es imagen-only o falla la extracción).
        page_number: Número de página, 1-indexed, para coincidir con ChunkMetadata.page.
        source_document: Nombre del archivo de origen (solo nombre, sin ruta completa).
    """

    text: str
    page_number: int
    source_document: str


@dataclass(frozen=True)
class LoadedDocument:
    """Documento cargado, listo para pasar al chunker.

    Attributes:
        source: Nombre del archivo de origen.
        pages: Páginas extraídas en orden.
        total_pages: Total de páginas del documento original.
    """

    source: str
    pages: list[RawPage]
    total_pages: int


class IngestError(Exception):
    """Error base de la capa de ingesta."""


class FileTooLargeError(IngestError):
    """El archivo excede el límite de tamaño configurado (max_file_size_mb)."""


class TooManyPagesError(IngestError):
    """El documento excede el límite de páginas configurado (max_pages)."""


class PdfParseError(IngestError):
    """pypdf no pudo leer o procesar el archivo."""
