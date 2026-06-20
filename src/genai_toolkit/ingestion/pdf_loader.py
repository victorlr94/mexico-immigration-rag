"""Cargador de PDF usando pypdf~=6.0 (ver ADR-002).

Seguridad aplicada antes de abrir el archivo:
  - Tamaño máximo: Settings.max_file_size_mb
  - Páginas máximas: Settings.max_pages
  - Timeout de extracción: _EXTRACTION_TIMEOUT_SECS (protege contra PDFs que
    bloquean pypdf indefinidamente — p. ej. con streams corruptos o muy grandes)
  - try/except por página: una página que falla produce text='' en vez de abortar
    el documento entero.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from pathlib import Path

import pypdf

from genai_toolkit.config.settings import Settings
from genai_toolkit.ingestion.types import (
    FileTooLargeError,
    LoadedDocument,
    PdfParseError,
    RawPage,
    TooManyPagesError,
)

logger = logging.getLogger(__name__)

_EXTRACTION_TIMEOUT_SECS = 60


class PdfLoader:
    """Carga un PDF y devuelve sus páginas como RawPage.

    Aplica límites de seguridad (tamaño y páginas) antes de llamar a pypdf.
    Si pypdf se bloquea en un archivo corrupto, un timeout de
    _EXTRACTION_TIMEOUT_SECS devuelve el control al llamador con PdfParseError.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()

    def load(self, path: Path) -> LoadedDocument:
        """Carga el PDF en `path` y devuelve sus páginas con metadata.

        Args:
            path: Ruta al archivo PDF.

        Returns:
            LoadedDocument con una RawPage por página del documento.

        Raises:
            FileNotFoundError: Si el archivo no existe.
            FileTooLargeError: Si el archivo supera max_file_size_mb.
            TooManyPagesError: Si el documento supera max_pages.
            PdfParseError: Si el archivo está corrupto o pypdf no puede abrirlo,
                o si la extracción supera _EXTRACTION_TIMEOUT_SECS.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        self._check_file_size(path)

        try:
            reader = pypdf.PdfReader(str(path))
        except Exception as exc:
            raise PdfParseError(
                f"No se pudo abrir el PDF '{path.name}': {exc}"
            ) from exc

        total_pages = len(reader.pages)
        self._check_page_count(total_pages, path.name)

        pages = self._extract_with_timeout(reader, path.name, total_pages)

        logger.info(
            "PDF cargado: %s — %d páginas, %d chars totales",
            path.name,
            len(pages),
            sum(len(p.text) for p in pages),
        )
        return LoadedDocument(source=path.name, pages=pages, total_pages=total_pages)

    def _check_file_size(self, path: Path) -> None:
        size_mb = path.stat().st_size / (1024 * 1024)
        limit_mb = self._settings.max_file_size_mb
        if size_mb > limit_mb:
            raise FileTooLargeError(
                f"'{path.name}' pesa {size_mb:.1f} MB, límite: {limit_mb} MB"
            )

    def _check_page_count(self, total_pages: int, name: str) -> None:
        limit = self._settings.max_pages
        if total_pages > limit:
            raise TooManyPagesError(
                f"'{name}' tiene {total_pages} páginas, límite: {limit}"
            )

    def _extract_with_timeout(
        self, reader: pypdf.PdfReader, source_name: str, count: int
    ) -> list[RawPage]:
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pdf-extract")
        future = executor.submit(self._extract_pages, reader, source_name, count)
        try:
            pages = future.result(timeout=_EXTRACTION_TIMEOUT_SECS)
            executor.shutdown(wait=False)
            return pages
        except FuturesTimeoutError:
            executor.shutdown(wait=False)
            raise PdfParseError(
                f"Timeout extrayendo '{source_name}' tras {_EXTRACTION_TIMEOUT_SECS}s"
                " — el archivo puede estar corrupto."
            ) from None

    @staticmethod
    def _extract_pages(
        reader: pypdf.PdfReader, source_name: str, count: int
    ) -> list[RawPage]:
        pages: list[RawPage] = []
        for i in range(count):
            try:
                text = reader.pages[i].extract_text() or ""
            except Exception as exc:
                logger.warning(
                    "No se pudo extraer texto de página %d de '%s': %s — se omite.",
                    i + 1,
                    source_name,
                    exc,
                )
                text = ""
            pages.append(
                RawPage(text=text, page_number=i + 1, source_document=source_name)
            )
        return pages
