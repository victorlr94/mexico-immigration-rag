"""Unit tests para ChromaVectorStore.

ChromaDB se instancia con un directorio temporal real (pytest tmp_path) en
lugar de mocks: la lógica de persistencia, upsert e indexado de ChromaDB no
puede verificarse significativamente sin tocar el motor real. Esto es
consistente con la pirámide de tests del proyecto (ver 03_testing.md):
los tests de componentes de infraestructura que no tienen lógica propia
ejecutable sin el motor se clasifican aquí en la capa de unit, pero usan
el backend real en modo efímero vía tmp_path.

Cada test recibe un store aislado — tmp_path es único por test en pytest.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from genai_toolkit.retrieval.types import Chunk, ChunkMetadata
from genai_toolkit.vectorstore.base import VectorStoreError
from genai_toolkit.vectorstore.chroma import ChromaVectorStore

_DIM = 4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unit_vec(*components: float) -> list[float]:
    """Devuelve un vector normalizado de los componentes dados."""
    norm = math.sqrt(sum(c * c for c in components))
    return [c / norm for c in components]


def _make_chunk(
    chunk_id: str = "id-0",
    text: str = "texto de prueba",
    source_document: str = "doc.pdf",
    page: int | None = 1,
    section: str | None = None,
    chunk_index: int = 0,
) -> Chunk:
    meta = ChunkMetadata(
        source_document=source_document,
        page=page,
        section=section,
        chunk_index=chunk_index,
    )
    return Chunk(id=chunk_id, text=text, metadata=meta)


def _emb(a: float = 1.0, b: float = 0.0, c: float = 0.0, d: float = 0.0) -> list[float]:
    return _unit_vec(a, b, c, d)


@pytest.fixture()
def store(tmp_path: Path) -> ChromaVectorStore:
    return ChromaVectorStore(
        persist_directory=tmp_path / "chroma",
        collection_name="test_col",
    )


# ---------------------------------------------------------------------------
# Construcción
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_new_store_starts_empty(self, store: ChromaVectorStore) -> None:
        assert store.count() == 0

    def test_persist_directory_kwarg_overrides_settings(self, tmp_path: Path) -> None:
        s1 = ChromaVectorStore(
            persist_directory=tmp_path / "store1", collection_name="col"
        )
        s1.add([_make_chunk("a")], [_emb(1)])
        s2 = ChromaVectorStore(
            persist_directory=tmp_path / "store2", collection_name="col"
        )
        assert s2.count() == 0

    def test_same_directory_reloads_persisted_data(self, tmp_path: Path) -> None:
        path = tmp_path / "shared"
        s1 = ChromaVectorStore(persist_directory=path, collection_name="col")
        s1.add([_make_chunk("a")], [_emb(1)])
        s2 = ChromaVectorStore(persist_directory=path, collection_name="col")
        assert s2.count() == 1


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------


class TestAdd:
    def test_single_chunk_increases_count(self, store: ChromaVectorStore) -> None:
        store.add([_make_chunk()], [_emb(1)])
        assert store.count() == 1

    def test_multiple_chunks_increase_count(self, store: ChromaVectorStore) -> None:
        chunks = [_make_chunk(f"id-{i}", chunk_index=i) for i in range(5)]
        embeddings = [_emb(float(i + 1)) for i in range(5)]
        store.add(chunks, embeddings)
        assert store.count() == 5

    def test_upsert_same_id_does_not_duplicate(self, store: ChromaVectorStore) -> None:
        chunk = _make_chunk("dup")
        store.add([chunk], [_emb(1)])
        store.add([chunk], [_emb(0, 1)])
        assert store.count() == 1

    def test_mismatched_lengths_raises_vectorstore_error(
        self, store: ChromaVectorStore
    ) -> None:
        with pytest.raises(VectorStoreError, match="misma longitud"):
            store.add([_make_chunk()], [])

    def test_empty_input_is_noop(self, store: ChromaVectorStore) -> None:
        store.add([], [])
        assert store.count() == 0


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestSearch:
    def test_empty_store_returns_empty_list(self, store: ChromaVectorStore) -> None:
        result = store.search(_emb(1), top_k=5)
        assert result == []

    def test_returns_scored_chunks(self, store: ChromaVectorStore) -> None:
        store.add([_make_chunk()], [_emb(1)])
        result = store.search(_emb(1), top_k=5)
        assert len(result) == 1

    def test_top_k_limits_results(self, store: ChromaVectorStore) -> None:
        chunks = [_make_chunk(f"id-{i}", chunk_index=i) for i in range(10)]
        store.add(chunks, [_emb(float(i + 1)) for i in range(10)])
        result = store.search(_emb(1), top_k=3)
        assert len(result) == 3

    def test_top_k_larger_than_collection_returns_all(
        self, store: ChromaVectorStore
    ) -> None:
        chunks = [_make_chunk(f"id-{i}", chunk_index=i) for i in range(3)]
        store.add(chunks, [_emb(float(i + 1)) for i in range(3)])
        result = store.search(_emb(1), top_k=100)
        assert len(result) == 3

    def test_score_is_in_0_1_range(self, store: ChromaVectorStore) -> None:
        store.add([_make_chunk()], [_emb(1)])
        result = store.search(_emb(1), top_k=1)
        assert 0.0 <= result[0].score <= 1.0

    def test_identical_vector_has_max_score(self, store: ChromaVectorStore) -> None:
        vec = _emb(1, 0, 0, 0)
        store.add([_make_chunk()], [vec])
        result = store.search(vec, top_k=1)
        assert result[0].score == pytest.approx(1.0, abs=1e-5)

    def test_results_sorted_by_score_descending(self, store: ChromaVectorStore) -> None:
        query = _emb(1, 0, 0, 0)
        close = _make_chunk("close", chunk_index=0)
        far = _make_chunk("far", chunk_index=1)
        store.add([close, far], [_emb(1, 0, 0, 0), _emb(0, 0, 0, 1)])
        result = store.search(query, top_k=2)
        assert result[0].score >= result[1].score

    def test_text_round_trip(self, store: ChromaVectorStore) -> None:
        original_text = "Texto de prueba específico para round trip."
        store.add([_make_chunk(text=original_text)], [_emb(1)])
        result = store.search(_emb(1), top_k=1)
        assert result[0].chunk.text == original_text

    def test_metadata_source_document_round_trip(
        self, store: ChromaVectorStore
    ) -> None:
        store.add(
            [_make_chunk(source_document="tramites_migratorios.pdf")],
            [_emb(1)],
        )
        result = store.search(_emb(1), top_k=1)
        assert result[0].chunk.metadata.source_document == "tramites_migratorios.pdf"

    def test_metadata_page_number_round_trip(self, store: ChromaVectorStore) -> None:
        store.add([_make_chunk(page=42)], [_emb(1)])
        result = store.search(_emb(1), top_k=1)
        assert result[0].chunk.metadata.page == 42

    def test_metadata_none_page_round_trip(self, store: ChromaVectorStore) -> None:
        store.add([_make_chunk(page=None)], [_emb(1)])
        result = store.search(_emb(1), top_k=1)
        assert result[0].chunk.metadata.page is None

    def test_metadata_section_round_trip(self, store: ChromaVectorStore) -> None:
        store.add([_make_chunk(section="Requisitos generales")], [_emb(1)])
        result = store.search(_emb(1), top_k=1)
        assert result[0].chunk.metadata.section == "Requisitos generales"

    def test_metadata_none_section_round_trip(self, store: ChromaVectorStore) -> None:
        store.add([_make_chunk(section=None)], [_emb(1)])
        result = store.search(_emb(1), top_k=1)
        assert result[0].chunk.metadata.section is None

    def test_metadata_chunk_index_round_trip(self, store: ChromaVectorStore) -> None:
        store.add([_make_chunk(chunk_index=17)], [_emb(1)])
        result = store.search(_emb(1), top_k=1)
        assert result[0].chunk.metadata.chunk_index == 17


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDelete:
    def test_delete_removes_chunk(self, store: ChromaVectorStore) -> None:
        store.add([_make_chunk("to-del")], [_emb(1)])
        store.delete(["to-del"])
        assert store.count() == 0

    def test_delete_only_specified_chunks(self, store: ChromaVectorStore) -> None:
        store.add(
            [_make_chunk("keep", chunk_index=0), _make_chunk("gone", chunk_index=1)],
            [_emb(1), _emb(0, 1)],
        )
        store.delete(["gone"])
        assert store.count() == 1

    def test_delete_nonexistent_id_is_silent(self, store: ChromaVectorStore) -> None:
        store.delete(["no-existe"])

    def test_delete_empty_list_is_noop(self, store: ChromaVectorStore) -> None:
        store.add([_make_chunk()], [_emb(1)])
        store.delete([])
        assert store.count() == 1

    def test_delete_allows_reinsertion(self, store: ChromaVectorStore) -> None:
        chunk = _make_chunk("reingested")
        store.add([chunk], [_emb(1)])
        store.delete(["reingested"])
        store.add([chunk], [_emb(0, 1)])
        assert store.count() == 1
