"""Tests de integración para IngestionPipeline.

Combinan componentes reales: PdfLoader, SlidingWindowChunker,
SentenceTransformerProvider y ChromaVectorStore. El objetivo es verificar
que la interfaz entre todos ellos es compatible y que el pipeline orquesta
correctamente las distintas rutas (blank PDF → 0 chunks; documento con texto
→ N chunks indexados y recuperables).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from genai_toolkit.config.settings import Settings
from genai_toolkit.embeddings.sentence_transformer_provider import (
    SentenceTransformerProvider,
)
from genai_toolkit.ingestion.pdf_loader import PdfLoader
from genai_toolkit.ingestion.types import LoadedDocument, RawPage
from genai_toolkit.pipeline.ingest import IngestionPipeline, IngestResult
from genai_toolkit.processing.sliding_window_chunker import SlidingWindowChunker
from genai_toolkit.retrieval.types import Chunk, ChunkMetadata
from genai_toolkit.vectorstore.chroma import ChromaVectorStore


def _build_pipeline(
    settings: Settings,
    embedder: SentenceTransformerProvider,
) -> IngestionPipeline:
    return IngestionPipeline(
        loader=PdfLoader(settings),
        chunker=SlidingWindowChunker(settings),
        embedder=embedder,
        store=ChromaVectorStore(settings=settings),
    )


@pytest.mark.integration
class TestIngestionPipelineE2E:
    def test_blank_pdf_produces_zero_chunks(
        self,
        blank_pdf: Path,
        real_embedder: SentenceTransformerProvider,
        tmp_path: Path,
    ) -> None:
        """Página en blanco → pipeline completa sin error, chunks_indexed=0."""
        settings = Settings(chroma_persist_dir=tmp_path / "chroma")
        pipeline = _build_pipeline(settings, real_embedder)

        result = pipeline.run(blank_pdf)

        assert isinstance(result, IngestResult)
        assert result.pages_loaded >= 1
        assert result.chunks_indexed == 0

    def test_blank_pdf_result_source_matches_filename(
        self,
        blank_pdf: Path,
        real_embedder: SentenceTransformerProvider,
        tmp_path: Path,
    ) -> None:
        """IngestResult.source debe coincidir con el nombre del archivo procesado."""
        settings = Settings(chroma_persist_dir=tmp_path / "chroma")
        pipeline = _build_pipeline(settings, real_embedder)

        result = pipeline.run(blank_pdf)

        assert result.source == blank_pdf.name

    def test_document_with_text_produces_indexed_chunks(
        self, real_embedder: SentenceTransformerProvider, tmp_path: Path
    ) -> None:
        """LoadedDocument con texto real → N chunks en ChromaDB, recuperables."""
        settings = Settings(
            chroma_persist_dir=tmp_path / "chroma_text",
            chunking_chunk_size=200,
            chunking_overlap=20,
        )
        chunker = SlidingWindowChunker(settings)
        store = ChromaVectorStore(settings=settings)

        text = (
            "Para solicitar una visa de estudiante en México se requieren: "
            "comprobante de inscripción expedido por la institución educativa, "
            "pasaporte vigente con al menos seis meses de vigencia, carta de "
            "aceptación oficial, comprobante de solvencia económica y seguro médico."
        )
        doc = LoadedDocument(
            source="guia_visa.pdf",
            total_pages=1,
            pages=[RawPage(source_document="guia_visa.pdf", page_number=1, text=text)],
        )

        chunks = chunker.chunk(doc)
        assert len(chunks) >= 1

        embeddings = real_embedder.embed_documents([c.text for c in chunks])
        store.add(chunks, embeddings)

        assert store.count() == len(chunks)

    def test_embeddings_dimension_matches_store_expectation(
        self, real_embedder: SentenceTransformerProvider, tmp_path: Path
    ) -> None:
        """Los embeddings del proveedor real son compatibles con ChromaDB cosine."""
        settings = Settings(chroma_persist_dir=tmp_path / "chroma_dim")
        store = ChromaVectorStore(settings=settings)

        chunk = Chunk(
            id="dim_test",
            text="compatibilidad de dimensiones",
            metadata=ChunkMetadata(source_document="test.pdf", chunk_index=0),
        )
        embeddings = real_embedder.embed_documents([chunk.text])
        assert len(embeddings[0]) == real_embedder.dimension

        store.add([chunk], embeddings)
        assert store.count() == 1
