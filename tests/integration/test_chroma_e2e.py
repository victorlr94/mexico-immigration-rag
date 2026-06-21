"""Tests de integración para ChromaVectorStore.

Usan ChromaDB real con un directorio temporal. Los vectores son valores fijos
(no se necesita el modelo de embeddings) — el objetivo es verificar que el
almacenamiento, la búsqueda, el upsert y la serialización de metadata funcionan
con la dependencia real, no con mocks.
"""

from __future__ import annotations

import math

import pytest

from genai_toolkit.retrieval.types import Chunk, ChunkMetadata
from genai_toolkit.vectorstore.chroma import ChromaVectorStore


def _unit_vec(dim: int = 384) -> list[float]:
    """Vector unitario de `dim` dimensiones — similar coseno consigo mismo = 1.0."""
    val = 1.0 / math.sqrt(dim)
    return [val] * dim


def _make_chunk(idx: int, text: str, page: int | None = None) -> Chunk:
    return Chunk(
        id=f"chunk_{idx}",
        text=text,
        metadata=ChunkMetadata(
            source_document="test.pdf",
            chunk_index=idx,
            page=page if page is not None else idx + 1,
        ),
    )


@pytest.mark.integration
class TestChromaStorageAndRetrieval:
    def _store(self, tmp_path) -> ChromaVectorStore:
        return ChromaVectorStore(persist_directory=tmp_path / "chroma")

    def test_empty_store_count_is_zero(self, tmp_path) -> None:
        assert self._store(tmp_path).count() == 0

    def test_add_increases_count(self, tmp_path) -> None:
        store = self._store(tmp_path)
        chunks = [_make_chunk(i, f"texto {i}") for i in range(3)]
        store.add(chunks, [_unit_vec() for _ in chunks])
        assert store.count() == 3

    def test_search_empty_store_returns_empty_list(self, tmp_path) -> None:
        results = self._store(tmp_path).search(_unit_vec(), top_k=5)
        assert results == []

    def test_search_returns_scored_chunk_in_range(self, tmp_path) -> None:
        store = self._store(tmp_path)
        chunk = _make_chunk(0, "trámite de visa de estudiante")
        store.add([chunk], [_unit_vec()])
        results = store.search(_unit_vec(), top_k=3)
        assert len(results) == 1
        assert results[0].chunk.id == "chunk_0"
        assert 0.0 <= results[0].score <= 1.0

    def test_upsert_does_not_duplicate_on_same_id(self, tmp_path) -> None:
        store = self._store(tmp_path)
        chunk = _make_chunk(0, "texto original")
        store.add([chunk], [_unit_vec()])
        store.add([chunk], [_unit_vec()])
        assert store.count() == 1

    def test_delete_removes_chunk(self, tmp_path) -> None:
        store = self._store(tmp_path)
        chunk = _make_chunk(0, "borrar esto")
        store.add([chunk], [_unit_vec()])
        store.delete(["chunk_0"])
        assert store.count() == 0

    def test_delete_nonexistent_id_is_noop(self, tmp_path) -> None:
        store = self._store(tmp_path)
        store.delete(["no_existe"])  # no debe lanzar
        assert store.count() == 0

    def test_top_k_limits_returned_results(self, tmp_path) -> None:
        store = self._store(tmp_path)
        chunks = [_make_chunk(i, f"texto {i}") for i in range(5)]
        store.add(chunks, [_unit_vec() for _ in chunks])
        results = store.search(_unit_vec(), top_k=2)
        assert len(results) <= 2

    def test_metadata_roundtrip_page_none(self, tmp_path) -> None:
        """page=None serializado como -1 se deserializa de vuelta a None."""
        store = self._store(tmp_path)
        chunk = Chunk(
            id="sin_pagina",
            text="sin paginación",
            metadata=ChunkMetadata(source_document="doc.pdf", chunk_index=0, page=None),
        )
        store.add([chunk], [_unit_vec()])
        results = store.search(_unit_vec(), top_k=1)
        assert results[0].chunk.metadata.page is None

    def test_score_for_identical_vector_is_near_one(self, tmp_path) -> None:
        """Un vector exactamente igual al indexado debe tener score próximo a 1.0."""
        store = self._store(tmp_path)
        vec = _unit_vec()
        store.add([_make_chunk(0, "igual")], [vec])
        results = store.search(vec, top_k=1)
        assert results[0].score >= 0.99
