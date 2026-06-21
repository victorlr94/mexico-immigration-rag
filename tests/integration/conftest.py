"""Fixtures de sesión compartidos por los tests de integración.

Los fixtures de sesión son críticos aquí: SentenceTransformerProvider carga
un modelo de ~117 MB — cargarlo una vez por sesión (no por test) hace que la
suite de integración sea práctica de ejecutar.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from genai_toolkit.config.settings import Settings
from genai_toolkit.embeddings.sentence_transformer_provider import (
    SentenceTransformerProvider,
)


@pytest.fixture(scope="session")
def integration_settings(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    """Settings con directorios temporales para aislamiento total entre sesiones."""
    chroma_dir = tmp_path_factory.mktemp("chroma_integration")
    log_dir = tmp_path_factory.mktemp("logs_integration")
    return Settings(
        chroma_persist_dir=chroma_dir,
        observability_path=str(log_dir / "interactions.jsonl"),
        retrieval_min_score=0.1,
        retrieval_top_k=3,
    )


@pytest.fixture(scope="session")
def real_embedder(integration_settings: Settings) -> SentenceTransformerProvider:
    """SentenceTransformerProvider real — el modelo se carga una sola vez."""
    return SentenceTransformerProvider(integration_settings)


@pytest.fixture(scope="session")
def blank_pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """PDF mínimo válido generado por pypdf (página en blanco, sin texto).

    Verifica la ruta de 'documento sin texto' del IngestionPipeline —
    pages_loaded=1, chunks_indexed=0 — sin necesitar un PDF con contenido real.
    """
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)

    tmp = tmp_path_factory.mktemp("fixtures_integration")
    path = tmp / "blank.pdf"
    path.write_bytes(buf.getvalue())
    return path
