"""Capa de ingesta: loaders de documentos para la pipeline RAG."""

from genai_toolkit.ingestion.base import DocumentLoader
from genai_toolkit.ingestion.pdf_loader import PdfLoader
from genai_toolkit.ingestion.types import (
    FileTooLargeError,
    IngestError,
    LoadedDocument,
    PdfParseError,
    RawPage,
    TooManyPagesError,
)

__all__ = [
    "DocumentLoader",
    "FileTooLargeError",
    "IngestError",
    "LoadedDocument",
    "PdfLoader",
    "PdfParseError",
    "RawPage",
    "TooManyPagesError",
]
