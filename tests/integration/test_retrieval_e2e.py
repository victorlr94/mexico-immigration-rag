"""Tests de integración para SimpleRetriever con embedder y store reales.

El fixture `real_embedder` (session-scoped) carga el modelo una sola vez para
toda la sesión. Los stores se crean en tmp_path separados por test para evitar
contaminación entre casos.
"""

from __future__ import annotations

import pytest

from genai_toolkit.config.settings import Settings
from genai_toolkit.retrieval.simple_retriever import SimpleRetriever
from genai_toolkit.retrieval.types import Chunk, ChunkMetadata
from genai_toolkit.vectorstore.chroma import ChromaVectorStore

_MIGRATION_TEXTS = [
    (
        "Para solicitar una visa de estudiante en México se necesitan: "
        "comprobante de inscripción expedido por la institución educativa, "
        "pasaporte vigente y carta de aceptación oficial."
    ),
    (
        "Los requisitos para la residencia temporal incluyen pasaporte vigente, "
        "comprobante de domicilio en México y demostración de solvencia económica."
    ),
    (
        "El trámite de naturalización requiere haber mantenido residencia legal "
        "continua en México durante al menos cinco años."
    ),
]


def _populated_retriever(
    real_embedder,
    tmp_path,
    *,
    min_score: float = 0.1,
    top_k: int = 3,
) -> SimpleRetriever:
    settings = Settings(
        chroma_persist_dir=tmp_path / "chroma",
        retrieval_min_score=min_score,
        retrieval_top_k=top_k,
    )
    store = ChromaVectorStore(settings=settings)
    chunks = [
        Chunk(
            id=f"c{i}",
            text=text,
            metadata=ChunkMetadata(
                source_document="guia.pdf", chunk_index=i, page=i + 1
            ),
        )
        for i, text in enumerate(_MIGRATION_TEXTS)
    ]
    embeddings = real_embedder.embed_documents([c.text for c in chunks])
    store.add(chunks, embeddings)
    return SimpleRetriever(real_embedder, store, settings)


@pytest.mark.integration
class TestRetrieverE2E:
    def test_embedder_produces_384_dim_vectors(self, real_embedder) -> None:
        """Sanity check: multilingual-e5-small produce vectores de 384 dimensiones."""
        vecs = real_embedder.embed_documents(["texto de prueba"])
        assert len(vecs) == 1
        assert len(vecs[0]) == 384

    def test_embed_query_produces_384_dim_vector(self, real_embedder) -> None:
        vec = real_embedder.embed_query("consulta de prueba")
        assert len(vec) == 384

    def test_retrieves_relevant_chunk_for_student_visa_query(
        self, real_embedder, tmp_path
    ) -> None:
        """Una consulta sobre visa de estudiante recupera el chunk más relevante."""
        retriever = _populated_retriever(real_embedder, tmp_path)
        result = retriever.retrieve(
            "¿Qué documentos necesito para tramitar visa de estudiante?"
        )

        assert result.has_sufficient_context
        assert len(result.chunks) >= 1
        top_text = result.chunks[0].chunk.text.lower()
        assert any(kw in top_text for kw in ("estudiante", "inscripción", "aceptación"))

    def test_retrieves_relevant_chunk_for_naturalization_query(
        self, real_embedder, tmp_path
    ) -> None:
        retriever = _populated_retriever(real_embedder, tmp_path)
        result = retriever.retrieve(
            "¿Cuántos años necesito vivir en México para naturalizarme?"
        )

        assert result.has_sufficient_context
        top_text = result.chunks[0].chunk.text.lower()
        assert "naturalización" in top_text or "residencia" in top_text

    def test_empty_store_always_returns_no_context(
        self, real_embedder, tmp_path
    ) -> None:
        settings = Settings(
            chroma_persist_dir=tmp_path / "chroma_empty",
            retrieval_min_score=0.0,
            retrieval_top_k=3,
        )
        store = ChromaVectorStore(settings=settings)
        retriever = SimpleRetriever(real_embedder, store, settings)
        result = retriever.retrieve("visa de estudiante")
        assert not result.has_sufficient_context
        assert result.chunks == []

    def test_very_high_threshold_produces_no_context(
        self, real_embedder, tmp_path
    ) -> None:
        """Con threshold=0.99 ningún chunk supera el umbral — se activa el refusal."""
        retriever = _populated_retriever(
            real_embedder, tmp_path, min_score=0.99, top_k=3
        )
        result = retriever.retrieve("visa de estudiante en México")
        assert not result.has_sufficient_context

    def test_chunks_are_ordered_by_score_descending(
        self, real_embedder, tmp_path
    ) -> None:
        """Los chunks recuperados deben venir ordenados de mayor a menor score."""
        retriever = _populated_retriever(real_embedder, tmp_path)
        result = retriever.retrieve("trámites migratorios en México")
        scores = [sc.score for sc in result.chunks]
        assert scores == sorted(scores, reverse=True)
