"""Protocol para cargadores de documentos."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from genai_toolkit.ingestion.types import LoadedDocument


@runtime_checkable
class DocumentLoader(Protocol):
    """Transforma un archivo en un LoadedDocument.

    El loader solo extrae texto y metadata de procedencia — no chunking,
    no embeddings, no limpieza avanzada (responsabilidades de capas posteriores).

    Implementaciones concretas: PdfLoader; futuras: TxtLoader, HtmlLoader, etc.
    """

    def load(self, path: Path) -> LoadedDocument:
        """Carga un documento y devuelve sus páginas con metadata.

        Args:
            path: Ruta al archivo a cargar.

        Returns:
            LoadedDocument con las páginas extraídas.

        Raises:
            FileNotFoundError: Si el archivo no existe.
            FileTooLargeError: Si el archivo supera max_file_size_mb.
            TooManyPagesError: Si el documento supera max_pages.
            PdfParseError: Si el archivo está corrupto o no puede procesarse.
        """
        ...
