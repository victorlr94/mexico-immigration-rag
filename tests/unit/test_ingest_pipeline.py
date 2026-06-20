"""Unit tests para IngestionPipeline.

Los cuatro componentes (loader, chunker, embedder, store) se mockean para
verificar la lógica de orquestación del pipeline de forma aislada.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from genai_toolkit.ingestion.types import LoadedDocument, RawPage
from genai_toolkit.pipeline.ingest import IngestionPipeline, IngestResult
from genai_toolkit.retrieval.types import Chunk, ChunkMetadata

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raw_page(text: str = "texto", page: int = 1) -> RawPage:
    return RawPage(text=text, page_number=page, source_document="doc.pdf")


def _loaded_doc(pages: list[RawPage] | None = None) -> LoadedDocument:
    _pages = pages or [_raw_page()]
    return LoadedDocument(source="doc.pdf", pages=_pages, total_pages=len(_pages))


def _chunk(chunk_id: str = "c0", text: str = "texto", chunk_index: int = 0) -> Chunk:
    meta = ChunkMetadata(source_document="doc.pdf", page=1, chunk_index=chunk_index)
    return Chunk(id=chunk_id, text=text, metadata=meta)


def _make_components(
    doc: LoadedDocument | None = None,
    chunks: list[Chunk] | None = None,
    embeddings: list[list[float]] | None = None,
) -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    """Devuelve (loader, chunker, embedder, store) con retornos configurados."""
    _doc = doc or _loaded_doc()
    _chunks = chunks if chunks is not None else [_chunk()]
    _embs = embeddings if embeddings is not None else [[0.1, 0.2]]

    loader = MagicMock()
    loader.load.return_value = _doc

    chunker = MagicMock()
    chunker.chunk.return_value = _chunks

    embedder = MagicMock()
    embedder.embed_documents.return_value = _embs

    store = MagicMock()

    return loader, chunker, embedder, store


@pytest.fixture()
def pipeline() -> IngestionPipeline:
    loader, chunker, embedder, store = _make_components()
    return IngestionPipeline(loader, chunker, embedder, store)


# ---------------------------------------------------------------------------
# Flujo de llamadas
# ---------------------------------------------------------------------------


class TestCallFlow:
    def test_loader_called_with_path(self) -> None:
        loader, chunker, embedder, store = _make_components()
        p = IngestionPipeline(loader, chunker, embedder, store)
        path = Path("tramite.pdf")
        p.run(path)
        loader.load.assert_called_once_with(path)

    def test_chunker_receives_loaded_document(self) -> None:
        doc = _loaded_doc()
        loader, chunker, embedder, store = _make_components(doc=doc)
        IngestionPipeline(loader, chunker, embedder, store).run(Path("x.pdf"))
        chunker.chunk.assert_called_once_with(doc)

    def test_embedder_receives_chunk_texts(self) -> None:
        chunks = [_chunk("c0", "primer texto"), _chunk("c1", "segundo texto", 1)]
        loader, chunker, embedder, store = _make_components(
            chunks=chunks, embeddings=[[0.1], [0.2]]
        )
        IngestionPipeline(loader, chunker, embedder, store).run(Path("x.pdf"))
        embedder.embed_documents.assert_called_once_with(
            ["primer texto", "segundo texto"]
        )

    def test_store_add_called_with_chunks_and_embeddings(self) -> None:
        chunks = [_chunk("c0")]
        embs = [[0.5, 0.5]]
        loader, chunker, embedder, store = _make_components(
            chunks=chunks, embeddings=embs
        )
        IngestionPipeline(loader, chunker, embedder, store).run(Path("x.pdf"))
        store.add.assert_called_once_with(chunks, embs)

    def test_pipeline_order_load_then_chunk_then_embed_then_store(self) -> None:
        parent = MagicMock()
        loader, chunker, embedder, store = _make_components()
        parent.attach_mock(loader, "loader")
        parent.attach_mock(chunker, "chunker")
        parent.attach_mock(embedder, "embedder")
        parent.attach_mock(store, "store")

        IngestionPipeline(loader, chunker, embedder, store).run(Path("x.pdf"))

        method_calls = [str(c) for c in parent.mock_calls]
        load_idx = next(i for i, c in enumerate(method_calls) if "loader.load" in c)
        chunk_idx = next(i for i, c in enumerate(method_calls) if "chunker.chunk" in c)
        embed_idx = next(
            i for i, c in enumerate(method_calls) if "embedder.embed_documents" in c
        )
        store_idx = next(i for i, c in enumerate(method_calls) if "store.add" in c)
        assert load_idx < chunk_idx < embed_idx < store_idx


# ---------------------------------------------------------------------------
# Resultado devuelto
# ---------------------------------------------------------------------------


class TestIngestResult:
    def test_result_is_ingest_result(self, pipeline: IngestionPipeline) -> None:
        result = pipeline.run(Path("x.pdf"))
        assert isinstance(result, IngestResult)

    def test_source_matches_document_source(self) -> None:
        doc = LoadedDocument(source="tramites.pdf", pages=[_raw_page()], total_pages=1)
        loader, chunker, embedder, store = _make_components(doc=doc)
        result = IngestionPipeline(loader, chunker, embedder, store).run(Path("x.pdf"))
        assert result.source == "tramites.pdf"

    def test_pages_loaded_matches_document_total_pages(self) -> None:
        pages = [_raw_page(page=i) for i in range(1, 6)]
        doc = _loaded_doc(pages=pages)
        loader, chunker, embedder, store = _make_components(doc=doc)
        result = IngestionPipeline(loader, chunker, embedder, store).run(Path("x.pdf"))
        assert result.pages_loaded == 5

    def test_chunks_indexed_matches_chunk_count(self) -> None:
        chunks = [_chunk(f"c{i}", chunk_index=i) for i in range(7)]
        embs = [[0.1]] * 7
        loader, chunker, embedder, store = _make_components(
            chunks=chunks, embeddings=embs
        )
        result = IngestionPipeline(loader, chunker, embedder, store).run(Path("x.pdf"))
        assert result.chunks_indexed == 7


# ---------------------------------------------------------------------------
# Documento sin chunks (páginas vacías)
# ---------------------------------------------------------------------------


class TestEmptyDocument:
    def test_empty_chunks_returns_zero_indexed(self) -> None:
        loader, chunker, embedder, store = _make_components(chunks=[])
        result = IngestionPipeline(loader, chunker, embedder, store).run(Path("x.pdf"))
        assert result.chunks_indexed == 0

    def test_empty_chunks_does_not_call_embedder(self) -> None:
        loader, chunker, embedder, store = _make_components(chunks=[])
        IngestionPipeline(loader, chunker, embedder, store).run(Path("x.pdf"))
        embedder.embed_documents.assert_not_called()

    def test_empty_chunks_does_not_call_store(self) -> None:
        loader, chunker, embedder, store = _make_components(chunks=[])
        IngestionPipeline(loader, chunker, embedder, store).run(Path("x.pdf"))
        store.add.assert_not_called()


# ---------------------------------------------------------------------------
# Propagación de errores
# ---------------------------------------------------------------------------


class TestErrorPropagation:
    def test_loader_error_propagates(self) -> None:
        loader, chunker, embedder, store = _make_components()
        loader.load.side_effect = FileNotFoundError("no existe")
        with pytest.raises(FileNotFoundError):
            IngestionPipeline(loader, chunker, embedder, store).run(Path("x.pdf"))

    def test_loader_error_does_not_call_subsequent_components(self) -> None:
        loader, chunker, embedder, store = _make_components()
        loader.load.side_effect = RuntimeError("fallo loader")
        with pytest.raises(RuntimeError):
            IngestionPipeline(loader, chunker, embedder, store).run(Path("x.pdf"))
        chunker.chunk.assert_not_called()
        embedder.embed_documents.assert_not_called()
        store.add.assert_not_called()

    def test_embedder_error_propagates(self) -> None:
        loader, chunker, embedder, store = _make_components()
        embedder.embed_documents.side_effect = RuntimeError("fallo embedder")
        with pytest.raises(RuntimeError):
            IngestionPipeline(loader, chunker, embedder, store).run(Path("x.pdf"))

    def test_embedder_error_does_not_call_store(self) -> None:
        loader, chunker, embedder, store = _make_components()
        embedder.embed_documents.side_effect = RuntimeError("fallo embedder")
        with pytest.raises(RuntimeError):
            IngestionPipeline(loader, chunker, embedder, store).run(Path("x.pdf"))
        store.add.assert_not_called()
