"""Unit tests para RecursiveTextChunker (ver ADR-007).

Cubre el contrato del Protocol TextChunker y el diferenciador frente al
SlidingWindowChunker: respeta límites naturales del texto (no corta palabras
a la mitad) y preserva las garantías de seguridad (sanitización de control
chars) y de citación (número de página en la metadata).
"""

from __future__ import annotations

import pytest

from genai_toolkit.config.settings import Settings
from genai_toolkit.ingestion.types import LoadedDocument, RawPage
from genai_toolkit.processing.recursive_text_chunker import RecursiveTextChunker

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def small_settings() -> Settings:
    """Settings con chunk_size pequeño para forzar múltiples chunks."""
    return Settings(chunk_size=30, chunk_overlap=5)


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
# Casos vacíos
# ---------------------------------------------------------------------------


class TestEmptyInputs:
    def test_empty_page_produces_no_chunks(self, small_settings: Settings) -> None:
        doc = _make_doc([("", 1)])
        assert RecursiveTextChunker(small_settings).chunk(doc) == []

    def test_whitespace_page_produces_no_chunks(self, small_settings: Settings) -> None:
        doc = _make_doc([("   \n  ", 1)])
        assert RecursiveTextChunker(small_settings).chunk(doc) == []

    def test_all_empty_pages_returns_empty_list(self, small_settings: Settings) -> None:
        doc = _make_doc([("", 1), ("", 2), ("", 3)])
        assert RecursiveTextChunker(small_settings).chunk(doc) == []


# ---------------------------------------------------------------------------
# División
# ---------------------------------------------------------------------------


class TestSplitting:
    def test_short_text_produces_one_chunk(self, small_settings: Settings) -> None:
        doc = _make_doc([("texto corto", 1)])
        chunks = RecursiveTextChunker(small_settings).chunk(doc)
        assert len(chunks) == 1
        assert chunks[0].text.strip() == "texto corto"

    def test_long_text_produces_multiple_chunks(self, small_settings: Settings) -> None:
        doc = _make_doc([("palabra " * 50, 1)])
        chunks = RecursiveTextChunker(small_settings).chunk(doc)
        assert len(chunks) > 1

    def test_respeta_limites_de_palabra(self, small_settings: Settings) -> None:
        """Diferenciador clave vs. ventana de caracteres: con separador de espacio,
        ningún chunk debe partir una palabra a la mitad."""
        doc = _make_doc([("palabra " * 50, 1)])
        chunks = RecursiveTextChunker(small_settings).chunk(doc)
        for c in chunks:
            for token in c.text.split():
                assert token == "palabra", f"palabra fragmentada: {token!r}"

    def test_prefiere_frontera_de_parrafo(self) -> None:
        """Con dos párrafos separados por doble salto y chunk_size que cabe en uno,
        el splitter divide en el párrafo, no a media frase."""
        settings = Settings(chunk_size=40, chunk_overlap=0)
        p1 = "Primer parrafo breve."
        p2 = "Segundo parrafo igualmente breve."
        doc = _make_doc([(f"{p1}\n\n{p2}", 1)])
        chunks = RecursiveTextChunker(settings).chunk(doc)
        texts = [c.text.strip() for c in chunks]
        assert p1 in texts
        assert p2 in texts


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_chunk_index_sequential_from_zero(self, small_settings: Settings) -> None:
        doc = _make_doc([("palabra " * 30, 1)])
        chunks = RecursiveTextChunker(small_settings).chunk(doc)
        indices = [c.metadata.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_chunk_index_continues_across_pages(self, small_settings: Settings) -> None:
        doc = _make_doc([("palabra " * 20, 1), ("termino " * 20, 2)])
        chunks = RecursiveTextChunker(small_settings).chunk(doc)
        indices = [c.metadata.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_page_number_preserved(self, small_settings: Settings) -> None:
        doc = _make_doc([("uno " * 10, 1), ("dos " * 10, 7)])
        chunks = RecursiveTextChunker(small_settings).chunk(doc)
        pages = {c.metadata.page for c in chunks}
        assert pages == {1, 7}

    def test_chunks_carry_correct_page_number(self, small_settings: Settings) -> None:
        doc = _make_doc([("palabra " * 30, 5)])
        chunks = RecursiveTextChunker(small_settings).chunk(doc)
        assert all(c.metadata.page == 5 for c in chunks)

    def test_source_document_in_metadata(self, small_settings: Settings) -> None:
        doc = _make_doc([("texto de prueba", 1)], source="documento.pdf")
        chunks = RecursiveTextChunker(small_settings).chunk(doc)
        assert all(c.metadata.source_document == "documento.pdf" for c in chunks)

    def test_section_is_none(self, small_settings: Settings) -> None:
        doc = _make_doc([("texto", 1)])
        chunks = RecursiveTextChunker(small_settings).chunk(doc)
        assert all(c.metadata.section is None for c in chunks)


# ---------------------------------------------------------------------------
# IDs estables
# ---------------------------------------------------------------------------


class TestChunkIds:
    def test_chunk_id_is_stable(self, small_settings: Settings) -> None:
        doc = _make_doc([("texto estable", 1)])
        a = RecursiveTextChunker(small_settings).chunk(doc)
        b = RecursiveTextChunker(small_settings).chunk(doc)
        assert [c.id for c in a] == [c.id for c in b]

    def test_chunk_ids_are_unique(self, small_settings: Settings) -> None:
        doc = _make_doc([("palabra " * 40, 1)])
        chunks = RecursiveTextChunker(small_settings).chunk(doc)
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Seguridad
# ---------------------------------------------------------------------------


class TestSanitization:
    def test_control_chars_sanitized_before_indexing(
        self, small_settings: Settings
    ) -> None:
        doc = _make_doc([("texto\x00con\x01control", 1)])
        chunks = RecursiveTextChunker(small_settings).chunk(doc)
        combined = "".join(c.text for c in chunks)
        assert "\x00" not in combined
        assert "\x01" not in combined


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


class TestDefaults:
    def test_default_settings_used_when_not_provided(self) -> None:
        """RecursiveTextChunker() sin argumentos carga Settings() por defecto."""
        doc = _make_doc([("texto breve", 1)])
        chunks = RecursiveTextChunker().chunk(doc)
        assert len(chunks) == 1
