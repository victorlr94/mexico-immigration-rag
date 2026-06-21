"""Security tests — validación de documentos de entrada.

Verifica que PdfLoader rechaza de forma controlada archivos peligrosos,
corruptos o que exceden los límites de seguridad antes de procesarlos.
El contrato de seguridad: siempre una excepción tipada, nunca un crash
del proceso ni un traceback sin manejar expuesto al usuario.

Riesgos mitigados:
  - Documentos maliciosos con magic bytes incorrectos (spoofing de extensión).
  - Archivos sobredimensionados que agotarían memoria (DoS).
  - PDFs con demasiadas páginas (DoS de parseo).
  - PDFs corruptos que podrían crashear el parser (LLM03 corpus poisoning).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from genai_toolkit.config.settings import Settings
from genai_toolkit.ingestion.pdf_loader import PdfLoader
from genai_toolkit.ingestion.types import (
    FileTooLargeError,
    PdfParseError,
    TooManyPagesError,
)

_TIGHT_SETTINGS = Settings(max_file_size_mb=5, max_pages=10)


@pytest.mark.security
class TestMagicBytesGuard:
    """Archivos que no son PDF se rechazan ANTES de llamar a pypdf."""

    def test_zip_file_disguised_as_pdf_is_rejected(self, tmp_path: Path) -> None:
        """ZIP con extensión .pdf → rechazado por magic bytes, no por pypdf."""
        fake = tmp_path / "malicioso.pdf"
        fake.write_bytes(b"PK\x03\x04")  # magic bytes de ZIP
        with pytest.raises(PdfParseError, match="magic bytes"):
            PdfLoader(_TIGHT_SETTINGS).load(fake)

    def test_docx_disguised_as_pdf_is_rejected(self, tmp_path: Path) -> None:
        """Office XML (DOCX/XLSX) con extensión .pdf → rechazado."""
        fake = tmp_path / "ofimática.pdf"
        fake.write_bytes(b"PK\x03\x04\x14\x00")  # DOCX/XLSX también son ZIP
        with pytest.raises(PdfParseError, match="magic bytes"):
            PdfLoader(_TIGHT_SETTINGS).load(fake)

    def test_html_disguised_as_pdf_is_rejected(self, tmp_path: Path) -> None:
        fake = tmp_path / "pagina.pdf"
        fake.write_bytes(b"<!DOCTYPE html><html>")
        with pytest.raises(PdfParseError, match="magic bytes"):
            PdfLoader(_TIGHT_SETTINGS).load(fake)

    def test_empty_file_is_rejected(self, tmp_path: Path) -> None:
        fake = tmp_path / "vacío.pdf"
        fake.write_bytes(b"")
        with pytest.raises(PdfParseError, match="magic bytes"):
            PdfLoader(_TIGHT_SETTINGS).load(fake)

    def test_valid_pdf_magic_bytes_pass_check(self, tmp_path: Path) -> None:
        """Archivo con magic bytes válidos (%PDF-) supera la comprobación."""
        valid = tmp_path / "valido.pdf"
        valid.write_bytes(b"%PDF-1.4 stub")
        with patch(
            "genai_toolkit.ingestion.pdf_loader.pypdf.PdfReader",
            return_value=_mock_reader(pages=["texto"]),
        ):
            doc = PdfLoader(_TIGHT_SETTINGS).load(valid)
        assert doc.total_pages == 1


@pytest.mark.security
class TestFileSizeGuard:
    """Archivos que exceden el límite de tamaño se rechazan sin procesarlos."""

    def test_oversized_file_is_rejected_before_parsing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Un PDF de 10 MB rechazado por límite de 5 MB — pypdf nunca se llama."""
        pdf = tmp_path / "enorme.pdf"
        pdf.write_bytes(b"%PDF-1.4 stub")
        original_stat = Path.stat

        def fake_stat(self_path: Path, *args: object, **kwargs: object) -> object:
            if self_path == pdf:
                stat = MagicMock()
                stat.st_size = 10 * 1024 * 1024  # 10 MB
                return stat
            return original_stat(self_path, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "stat", fake_stat)
        with pytest.raises(FileTooLargeError, match="10.0 MB"):
            PdfLoader(_TIGHT_SETTINGS).load(pdf)

    def test_file_at_exact_limit_is_not_rejected_by_size(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Archivo exactamente en el límite no es rechazado por tamaño."""
        pdf = tmp_path / "exacto.pdf"
        pdf.write_bytes(b"%PDF-1.4 stub")
        original_stat = Path.stat

        def fake_stat(self_path: Path, *args: object, **kwargs: object) -> object:
            if self_path == pdf:
                stat = MagicMock()
                stat.st_size = 5 * 1024 * 1024  # exactamente 5 MB
                return stat
            return original_stat(self_path, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "stat", fake_stat)
        with patch(
            "genai_toolkit.ingestion.pdf_loader.pypdf.PdfReader",
            return_value=_mock_reader(pages=["ok"]),
        ):
            doc = PdfLoader(_TIGHT_SETTINGS).load(pdf)
        assert doc.total_pages == 1


@pytest.mark.security
class TestPageCountGuard:
    """Documentos con demasiadas páginas se rechazan antes de extraer texto."""

    def test_too_many_pages_is_rejected(self, tmp_path: Path) -> None:
        pdf = tmp_path / "libro.pdf"
        pdf.write_bytes(b"%PDF-1.4 stub")
        with (
            patch(
                "genai_toolkit.ingestion.pdf_loader.pypdf.PdfReader",
                return_value=_mock_reader(n=50),
            ),
            pytest.raises(TooManyPagesError, match="50 páginas"),
        ):
            PdfLoader(_TIGHT_SETTINGS).load(pdf)

    def test_document_at_page_limit_is_accepted(self, tmp_path: Path) -> None:
        pdf = tmp_path / "límite.pdf"
        pdf.write_bytes(b"%PDF-1.4 stub")
        with patch(
            "genai_toolkit.ingestion.pdf_loader.pypdf.PdfReader",
            return_value=_mock_reader(n=10),
        ):
            doc = PdfLoader(_TIGHT_SETTINGS).load(pdf)
        assert doc.total_pages == 10


@pytest.mark.security
class TestCorruptedDocumentGuard:
    """PDFs corruptos producen error controlado, nunca un crash del proceso."""

    def test_corrupted_body_raises_pdf_parse_error(self, tmp_path: Path) -> None:
        pdf = tmp_path / "corrupto.pdf"
        pdf.write_bytes(b"%PDF-1.4 cuerpo_corrupto")
        with (
            patch(
                "genai_toolkit.ingestion.pdf_loader.pypdf.PdfReader",
                side_effect=Exception("invalid xref table"),
            ),
            pytest.raises(PdfParseError, match="corrupto.pdf"),
        ):
            PdfLoader(_TIGHT_SETTINGS).load(pdf)

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            PdfLoader(_TIGHT_SETTINGS).load(tmp_path / "no_existe.pdf")

    def test_pdf_parse_error_is_not_bare_exception(self, tmp_path: Path) -> None:
        """PdfParseError es subclase de IngestError — el sistema puede atraparlo."""
        from genai_toolkit.ingestion.types import IngestError

        pdf = tmp_path / "corrupto2.pdf"
        pdf.write_bytes(b"%PDF-1.4 stub")
        with (
            patch(
                "genai_toolkit.ingestion.pdf_loader.pypdf.PdfReader",
                side_effect=Exception("fallo"),
            ),
            pytest.raises(IngestError),
        ):
            PdfLoader(_TIGHT_SETTINGS).load(pdf)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_reader(pages: list[str] | None = None, n: int | None = None) -> MagicMock:
    """Crea un PdfReader mock con N páginas (con texto si `pages` se proporciona)."""
    count = n if n is not None else (len(pages) if pages else 1)
    mock_pages = []
    for i in range(count):
        p = MagicMock()
        p.extract_text.return_value = pages[i] if pages and i < len(pages) else f"p{i}"
        mock_pages.append(p)
    reader = MagicMock()
    reader.pages = mock_pages
    return reader
