"""Unit tests para PdfLoader.

Todos los tests usan mocks de pypdf para no depender de archivos PDF reales
ni de la instalación del paquete en CI (los mocks ejercen la lógica del loader,
no la de pypdf). Un test de integración con un PDF real puede añadirse en
tests/integration/ cuando exista esa capa.
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

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tight_settings() -> Settings:
    """Settings con límites pequeños para facilitar los tests de validación."""
    return Settings(max_file_size_mb=5, max_pages=10)


def _mock_reader(
    num_pages: int, page_texts: list[str] | None = None
) -> MagicMock:
    """PdfReader mock con `num_pages` páginas y textos opcionales."""
    pages = []
    for i in range(num_pages):
        page = MagicMock()
        text = (
            page_texts[i]
            if page_texts and i < len(page_texts)
            else f"Página {i + 1}"
        )
        page.extract_text.return_value = text
        pages.append(page)

    reader = MagicMock()
    reader.pages = pages
    return reader


# ---------------------------------------------------------------------------
# Validaciones de seguridad
# ---------------------------------------------------------------------------


class TestValidation:
    def test_raises_file_not_found(
        self, tmp_path: Path, tight_settings: Settings
    ) -> None:
        loader = PdfLoader(tight_settings)
        with pytest.raises(FileNotFoundError):
            loader.load(tmp_path / "no_existe.pdf")

    def test_raises_file_too_large(
        self,
        tmp_path: Path,
        tight_settings: Settings,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        pdf = tmp_path / "grande.pdf"
        pdf.write_bytes(b"%PDF-1.4 stub")

        original_stat = Path.stat

        def fake_stat(
            self_path: Path, *args: object, **kwargs: object
        ) -> object:
            if self_path == pdf:
                stat = MagicMock()
                stat.st_size = 10 * 1024 * 1024  # 10 MB > límite de 5 MB
                return stat
            return original_stat(self_path, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "stat", fake_stat)

        loader = PdfLoader(tight_settings)
        with pytest.raises(FileTooLargeError, match="10.0 MB"):
            loader.load(pdf)

    def test_raises_too_many_pages(
        self, tmp_path: Path, tight_settings: Settings
    ) -> None:
        pdf = tmp_path / "largo.pdf"
        pdf.write_bytes(b"%PDF-1.4 stub")

        with patch(
            "genai_toolkit.ingestion.pdf_loader.pypdf.PdfReader",
            return_value=_mock_reader(num_pages=50),  # > límite de 10
        ):
            loader = PdfLoader(tight_settings)
            with pytest.raises(TooManyPagesError, match="50 páginas"):
                loader.load(pdf)

    def test_raises_pdf_parse_error_on_corrupt(
        self, tmp_path: Path, tight_settings: Settings
    ) -> None:
        pdf = tmp_path / "corrupto.pdf"
        pdf.write_bytes(b"esto no es un PDF")

        with patch(
            "genai_toolkit.ingestion.pdf_loader.pypdf.PdfReader",
            side_effect=Exception("invalid PDF header"),
        ):
            loader = PdfLoader(tight_settings)
            with pytest.raises(PdfParseError, match="corrupto.pdf"):
                loader.load(pdf)


# ---------------------------------------------------------------------------
# Caso de éxito
# ---------------------------------------------------------------------------


class TestSuccessPath:
    def test_returns_correct_document_structure(
        self, tmp_path: Path, tight_settings: Settings
    ) -> None:
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-1.4 stub")
        texts = ["Primera página", "Segunda página", "Tercera página"]

        with patch(
            "genai_toolkit.ingestion.pdf_loader.pypdf.PdfReader",
            return_value=_mock_reader(num_pages=3, page_texts=texts),
        ):
            doc = PdfLoader(tight_settings).load(pdf)

        assert doc.source == "doc.pdf"
        assert doc.total_pages == 3
        assert len(doc.pages) == 3

    def test_pages_have_correct_numbering_and_source(
        self, tmp_path: Path, tight_settings: Settings
    ) -> None:
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-1.4 stub")
        texts = ["Uno", "Dos"]

        with patch(
            "genai_toolkit.ingestion.pdf_loader.pypdf.PdfReader",
            return_value=_mock_reader(num_pages=2, page_texts=texts),
        ):
            doc = PdfLoader(tight_settings).load(pdf)

        assert doc.pages[0].page_number == 1
        assert doc.pages[0].text == "Uno"
        assert doc.pages[1].page_number == 2
        assert doc.pages[1].text == "Dos"
        assert all(p.source_document == "doc.pdf" for p in doc.pages)

    def test_page_extraction_error_yields_empty_text(
        self, tmp_path: Path, tight_settings: Settings
    ) -> None:
        """Una página que pypdf no puede extraer produce text='' sin abortar."""
        pdf = tmp_path / "parcial.pdf"
        pdf.write_bytes(b"%PDF-1.4 stub")

        failing_page = MagicMock()
        failing_page.extract_text.side_effect = Exception("encoding error")
        ok_page = MagicMock()
        ok_page.extract_text.return_value = "Texto válido"

        reader = MagicMock()
        reader.pages = [failing_page, ok_page]

        with patch(
            "genai_toolkit.ingestion.pdf_loader.pypdf.PdfReader",
            return_value=reader,
        ):
            doc = PdfLoader(tight_settings).load(pdf)

        assert len(doc.pages) == 2
        assert doc.pages[0].text == ""
        assert doc.pages[1].text == "Texto válido"

    def test_none_text_from_pypdf_becomes_empty_string(
        self, tmp_path: Path, tight_settings: Settings
    ) -> None:
        """extract_text() devuelve None en páginas imagen; se convierte a ''."""
        pdf = tmp_path / "imagen.pdf"
        pdf.write_bytes(b"%PDF-1.4 stub")

        image_page = MagicMock()
        image_page.extract_text.return_value = None
        reader = MagicMock()
        reader.pages = [image_page]

        with patch(
            "genai_toolkit.ingestion.pdf_loader.pypdf.PdfReader",
            return_value=reader,
        ):
            doc = PdfLoader(tight_settings).load(pdf)

        assert doc.pages[0].text == ""

    def test_default_settings_used_when_not_provided(self, tmp_path: Path) -> None:
        """PdfLoader() sin argumentos carga Settings() por defecto."""
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-1.4 stub")

        with patch(
            "genai_toolkit.ingestion.pdf_loader.pypdf.PdfReader",
            return_value=_mock_reader(num_pages=1, page_texts=["Hola"]),
        ):
            doc = PdfLoader().load(pdf)

        assert doc.total_pages == 1
        assert doc.pages[0].text == "Hola"
