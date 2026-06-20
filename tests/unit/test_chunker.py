"""Unit tests para SlidingWindowChunker y funciones auxiliares.

Objetivo de cobertura: ≥90% en el módulo sliding_window_chunker
(ver Testing Skill — chunking es crítico, mismo umbral que security guards).

Estructura:
  - TestSanitizeText: función _sanitize_text (seguridad: eliminar control chars)
  - TestSplitIntoWindows: función _split_into_windows (algoritmo de chunking)
  - TestSlidingWindowChunker: integración completa LoadedDocument → list[Chunk]
"""

from __future__ import annotations

import pytest

from genai_toolkit.config.settings import Settings
from genai_toolkit.ingestion.types import LoadedDocument, RawPage
from genai_toolkit.processing.sliding_window_chunker import (
    SlidingWindowChunker,
    _sanitize_text,
    _split_into_windows,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def small_settings() -> Settings:
    """Settings con chunk_size pequeño para facilitar la verificación."""
    return Settings(chunk_size=20, chunk_overlap=5)


def _make_doc(
    pages: list[tuple[str, int]],
    source: str = "test.pdf",
) -> LoadedDocument:
    """Crea un LoadedDocument con las páginas indicadas como (text, page_number)."""
    raw_pages = [
        RawPage(text=text, page_number=pnum, source_document=source)
        for text, pnum in pages
    ]
    return LoadedDocument(source=source, pages=raw_pages, total_pages=len(raw_pages))


# ---------------------------------------------------------------------------
# _sanitize_text
# ---------------------------------------------------------------------------


class TestSanitizeText:
    def test_normal_text_unchanged(self) -> None:
        text = "Hola mundo\nSegunda línea"
        assert _sanitize_text(text) == text

    def test_tab_preserved(self) -> None:
        assert _sanitize_text("col1\tcol2") == "col1\tcol2"

    def test_null_byte_removed(self) -> None:
        assert _sanitize_text("texto\x00con nulo") == "textocon nulo"

    def test_control_chars_removed(self) -> None:
        # \x01–\x08 y \x0e–\x1f son caracteres de control
        dirty = "".join(chr(i) for i in range(1, 9)) + "texto"
        result = _sanitize_text(dirty)
        assert result == "texto"

    def test_del_char_removed(self) -> None:
        assert _sanitize_text("texto\x7ffin") == "textofin"

    def test_empty_string_unchanged(self) -> None:
        assert _sanitize_text("") == ""

    def test_newline_and_carriage_return_preserved(self) -> None:
        # \r (0x0d) no está en el rango excluido — se preserva
        assert _sanitize_text("línea1\r\nlínea2") == "línea1\r\nlínea2"


# ---------------------------------------------------------------------------
# _split_into_windows
# ---------------------------------------------------------------------------


class TestSplitIntoWindows:
    def test_empty_string_returns_empty(self) -> None:
        assert _split_into_windows("", 20, 5) == []

    def test_whitespace_only_returns_empty(self) -> None:
        assert _split_into_windows("   \n  ", 20, 5) == []

    def test_short_text_single_window(self) -> None:
        windows = _split_into_windows("corto", 20, 5)
        assert len(windows) == 1
        assert windows[0] == "corto"

    def test_exact_chunk_size_single_window(self) -> None:
        text = "a" * 20
        windows = _split_into_windows(text, 20, 5)
        assert len(windows) == 1

    def test_long_text_multiple_windows(self) -> None:
        # 35 chars, chunk_size=20, overlap=5 → step=15 → 2 windows
        text = "a" * 35
        windows = _split_into_windows(text, 20, 5)
        assert len(windows) == 2

    def test_overlap_produces_shared_content(self) -> None:
        text = "abcdefghijklmnopqrstuvwxyz"  # 26 chars
        windows = _split_into_windows(text, 15, 5)
        # window[0] ends at index 15; window[1] starts at 15-5=10
        # so chars [10:15] appear in both
        assert windows[0][10:15] == windows[1][:5]

    def test_no_content_lost(self) -> None:
        text = "x" * 100
        windows = _split_into_windows(text, 20, 5)
        reconstructed = "".join(windows)
        # Con overlap la reconstrucción tiene más chars que el original
        assert len(reconstructed) >= len(text)
        # El primer y último carácter del original están cubiertos
        assert windows[0][0] == text[0]
        assert windows[-1][-1] == text[-1]

    def test_window_with_only_spaces_discarded(self) -> None:
        # Ventana de solo espacios debe descartarse
        text = "texto" + " " * 20 + "fin"
        windows = _split_into_windows(text, 5, 0)
        non_empty = [w for w in windows if w.strip()]
        assert len(non_empty) == len(windows)

    def test_zero_overlap_sequential_no_repeat(self) -> None:
        text = "abcdefghij"  # 10 chars
        windows = _split_into_windows(text, 5, 0)
        assert windows == ["abcde", "fghij"]


# ---------------------------------------------------------------------------
# SlidingWindowChunker — integración
# ---------------------------------------------------------------------------


class TestSlidingWindowChunker:
    def test_empty_page_produces_no_chunks(self, small_settings: Settings) -> None:
        doc = _make_doc([("", 1)])
        chunks = SlidingWindowChunker(small_settings).chunk(doc)
        assert chunks == []

    def test_whitespace_page_produces_no_chunks(self, small_settings: Settings) -> None:
        doc = _make_doc([("   \n  ", 1)])
        chunks = SlidingWindowChunker(small_settings).chunk(doc)
        assert chunks == []

    def test_all_empty_pages_returns_empty_list(self, small_settings: Settings) -> None:
        doc = _make_doc([("", 1), ("", 2), ("", 3)])
        assert SlidingWindowChunker(small_settings).chunk(doc) == []

    def test_short_text_produces_one_chunk(self, small_settings: Settings) -> None:
        doc = _make_doc([("texto corto", 1)])
        chunks = SlidingWindowChunker(small_settings).chunk(doc)
        assert len(chunks) == 1
        assert chunks[0].text == "texto corto"

    def test_long_text_produces_multiple_chunks(self, small_settings: Settings) -> None:
        doc = _make_doc([("a" * 50, 1)])
        chunks = SlidingWindowChunker(small_settings).chunk(doc)
        assert len(chunks) > 1

    def test_chunk_index_is_sequential_from_zero(
        self, small_settings: Settings
    ) -> None:
        doc = _make_doc([("a" * 50, 1)])
        chunks = SlidingWindowChunker(small_settings).chunk(doc)
        indices = [c.metadata.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_chunk_index_continues_across_pages(self, small_settings: Settings) -> None:
        doc = _make_doc([("a" * 30, 1), ("b" * 30, 2)])
        chunks = SlidingWindowChunker(small_settings).chunk(doc)
        indices = [c.metadata.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_page_number_in_metadata(self, small_settings: Settings) -> None:
        doc = _make_doc([("página uno " * 3, 1), ("página dos " * 3, 2)])
        chunks = SlidingWindowChunker(small_settings).chunk(doc)
        page_nums = {c.metadata.page for c in chunks}
        assert 1 in page_nums
        assert 2 in page_nums

    def test_chunks_from_page_carry_correct_page_number(
        self, small_settings: Settings
    ) -> None:
        doc = _make_doc([("a" * 30, 5)])
        chunks = SlidingWindowChunker(small_settings).chunk(doc)
        assert all(c.metadata.page == 5 for c in chunks)

    def test_source_document_in_metadata(self, small_settings: Settings) -> None:
        doc = _make_doc([("texto de prueba", 1)], source="documento.pdf")
        chunks = SlidingWindowChunker(small_settings).chunk(doc)
        assert all(c.metadata.source_document == "documento.pdf" for c in chunks)

    def test_section_is_none(self, small_settings: Settings) -> None:
        doc = _make_doc([("texto", 1)])
        chunks = SlidingWindowChunker(small_settings).chunk(doc)
        assert all(c.metadata.section is None for c in chunks)

    def test_chunk_id_is_stable(self, small_settings: Settings) -> None:
        doc = _make_doc([("texto estable", 1)])
        chunks_a = SlidingWindowChunker(small_settings).chunk(doc)
        chunks_b = SlidingWindowChunker(small_settings).chunk(doc)
        assert [c.id for c in chunks_a] == [c.id for c in chunks_b]

    def test_chunk_ids_are_unique(self, small_settings: Settings) -> None:
        doc = _make_doc([("a" * 60, 1)])
        chunks = SlidingWindowChunker(small_settings).chunk(doc)
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_control_chars_sanitized_before_indexing(
        self, small_settings: Settings
    ) -> None:
        doc = _make_doc([("texto\x00con\x01control", 1)])
        chunks = SlidingWindowChunker(small_settings).chunk(doc)
        combined = "".join(c.text for c in chunks)
        assert "\x00" not in combined
        assert "\x01" not in combined

    def test_content_not_lost_in_chunking(self, small_settings: Settings) -> None:
        text = "z" * 100
        doc = _make_doc([(text, 1)])
        chunks = SlidingWindowChunker(small_settings).chunk(doc)
        reconstructed = "".join(c.text for c in chunks)
        # Con solapamiento la reconstrucción tiene al menos tantos chars
        assert len(reconstructed) >= len(text)

    def test_default_settings_used_when_not_provided(self) -> None:
        """SlidingWindowChunker() sin argumentos carga Settings() por defecto."""
        doc = _make_doc([("texto breve", 1)])
        chunks = SlidingWindowChunker().chunk(doc)
        assert len(chunks) == 1

    def test_chunk_text_matches_source_window(self, small_settings: Settings) -> None:
        text = "abcdefghijklmnopqrstuvwxyz0123456789"
        doc = _make_doc([(text, 1)])
        chunks = SlidingWindowChunker(small_settings).chunk(doc)
        # El primer chunk debe comenzar con los primeros chars del texto
        assert chunks[0].text.startswith(text[:5])
