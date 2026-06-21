"""Unit tests para el Observability Layer.

Cubre tres áreas:
1. ObservabilityStore — escritura JSONL, lectura y creación de directorio.
2. redact_pii — patrones de PII del dominio migratorio mexicano.
3. RAGInteractionLogger — construcción correcta del InteractionLog,
   respeto de la política de redacción, campo question_hash.

ObservabilityStore se parametriza con un directorio temporal para no
contaminar el sistema de archivos. El modelo de embeddings y el LLM
no se instancian — se pasan artefactos mínimos directamente.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from genai_toolkit.config.settings import Settings
from genai_toolkit.observability.logger import RAGInteractionLogger, redact_pii
from genai_toolkit.observability.store import (
    InteractionLog,
    ObservabilityStore,
    SourceReference,
)
from genai_toolkit.retrieval.types import (
    Chunk,
    ChunkMetadata,
    RetrievalResult,
    ScoredChunk,
)

# ---------------------------------------------------------------------------
# Helpers compartidos
# ---------------------------------------------------------------------------


def _make_settings(tmp_path: Path) -> Settings:
    return Settings(
        observability_path=tmp_path / "logs" / "interactions.jsonl",
        redact_pii=True,
    )


def _make_chunk(
    chunk_id: str = "abc123", source: str = "guia.pdf", page: int = 1
) -> Chunk:
    return Chunk(
        id=chunk_id,
        text="Texto de ejemplo del chunk.",
        metadata=ChunkMetadata(source_document=source, page=page, chunk_index=0),
    )


def _make_retrieval_result(
    sufficient: bool = True, n_chunks: int = 2
) -> RetrievalResult:
    chunks = [
        ScoredChunk(chunk=_make_chunk(f"chunk{i}", page=i + 1), score=0.85 - i * 0.05)
        for i in range(n_chunks)
    ]
    return RetrievalResult(
        query="¿Qué documentos necesito?",
        chunks=chunks,
        has_sufficient_context=sufficient,
    )


# ---------------------------------------------------------------------------
# ObservabilityStore
# ---------------------------------------------------------------------------


class TestObservabilityStore:
    def test_crea_directorio_si_no_existe(self, tmp_path: Path) -> None:
        deep = tmp_path / "a" / "b" / "interactions.jsonl"
        ObservabilityStore(Settings(observability_path=deep))
        assert deep.parent.exists()

    def test_log_crea_archivo_jsonl(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path)
        store = ObservabilityStore(settings)
        record = _minimal_log()
        store.log(record)
        assert store.path.exists()
        lines = store.path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1

    def test_log_multiple_appends(self, tmp_path: Path) -> None:
        store = ObservabilityStore(_make_settings(tmp_path))
        for _ in range(3):
            store.log(_minimal_log())
        assert len(store.read_all()) == 3

    def test_read_all_vacio_si_no_existe_archivo(self, tmp_path: Path) -> None:
        store = ObservabilityStore(_make_settings(tmp_path))
        assert store.read_all() == []

    def test_log_serializa_campos_obligatorios(self, tmp_path: Path) -> None:
        store = ObservabilityStore(_make_settings(tmp_path))
        store.log(_minimal_log())
        [entry] = store.read_all()
        assert entry["timestamp"] != ""
        assert entry["question_hash"] == "deadbeef12345678"
        assert entry["question_type"] == "in_scope"
        assert entry["model"] == "test-model"

    def test_log_serializa_source_documents_como_dicts(self, tmp_path: Path) -> None:
        store = ObservabilityStore(_make_settings(tmp_path))
        record = _minimal_log()
        record.source_documents.append(SourceReference(doc="guia.pdf", page=3))
        store.log(record)
        [entry] = store.read_all()
        assert entry["source_documents"][0] == {"doc": "guia.pdf", "page": 3}

    def test_log_jsonl_linea_valida(self, tmp_path: Path) -> None:
        store = ObservabilityStore(_make_settings(tmp_path))
        store.log(_minimal_log())
        line = store.path.read_text(encoding="utf-8").strip()
        parsed = json.loads(line)
        assert isinstance(parsed, dict)

    def test_path_property(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path)
        store = ObservabilityStore(settings)
        assert store.path == Path(settings.observability_path)


def _minimal_log() -> InteractionLog:
    return InteractionLog(
        timestamp="2026-06-20T00:00:00+00:00",
        question_hash="deadbeef12345678",
        question_type="in_scope",
        model="test-model",
        embedding_model="test-embedder",
        retrieved_context_ids=["abc"],
        source_documents=[],
        retrieval_scores=[0.85],
        has_sufficient_context=True,
        response_time_ms=100.0,
    )


# ---------------------------------------------------------------------------
# redact_pii
# ---------------------------------------------------------------------------


class TestRedactPii:
    @pytest.mark.parametrize(
        "text, expected_tag",
        [
            # CURP
            ("Mi CURP es ROML850315HDFLPS09", "[CURP]"),
            # RFC persona física
            ("RFC: ROML850315AB1", "[RFC]"),
            # RFC persona moral
            ("RFC empresa: SEM850315AB1", "[RFC]"),
            # Email
            ("Escríbeme a usuario@ejemplo.com por favor", "[EMAIL]"),
            # Teléfono 10 dígitos
            ("Mi celular es 5512345678", "[TEL]"),
            # Teléfono con prefijo +52
            ("+525512345678 es mi número", "[TEL]"),
        ],
    )
    def test_patron_detectado(self, text: str, expected_tag: str) -> None:
        result = redact_pii(text)
        assert expected_tag in result
        # El patrón original no debe estar en el resultado
        # (chequeamos que se reemplazó, no qué queda exactamente)

    def test_texto_sin_pii_queda_igual(self) -> None:
        text = "¿Cuáles son los requisitos para visa de estudiante?"
        assert redact_pii(text) == text

    def test_multiples_pii_en_mismo_texto(self) -> None:
        text = "Email: vic@test.com y CURP: ROML850315HDFLPS09"
        result = redact_pii(text)
        assert "[EMAIL]" in result
        assert "[CURP]" in result
        assert "vic@test.com" not in result
        assert "ROML850315HDFLPS09" not in result

    def test_texto_vacio(self) -> None:
        assert redact_pii("") == ""

    def test_no_falso_positivo_numeros_cortos(self) -> None:
        text = "El artículo 30 de la Ley de Migración"
        result = redact_pii(text)
        assert result == text


# ---------------------------------------------------------------------------
# RAGInteractionLogger
# ---------------------------------------------------------------------------


class TestRAGInteractionLogger:
    def test_crea_registro_en_store(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path)
        store = ObservabilityStore(settings)
        logger = RAGInteractionLogger(settings, store)
        result = _make_retrieval_result()
        logger.log_interaction(
            question="¿Qué visa necesito?",
            question_type="in_scope",
            retrieval_result=result,
            response_time_ms=350.0,
            answer="Necesitas una visa de turista.",
        )
        [entry] = store.read_all()
        assert entry["question_type"] == "in_scope"
        assert entry["has_sufficient_context"] is True
        assert entry["response_time_ms"] == 350.0

    def test_question_hash_sha256_16chars(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path)
        store = ObservabilityStore(settings)
        logger = RAGInteractionLogger(settings, store)
        logger.log_interaction(
            question="hola",
            question_type="in_scope",
            retrieval_result=_make_retrieval_result(),
            response_time_ms=100.0,
        )
        [entry] = store.read_all()
        assert len(entry["question_hash"]) == 16
        assert re.fullmatch(r"[0-9a-f]{16}", entry["question_hash"])

    def test_redact_pii_true_aplica_redaccion(self, tmp_path: Path) -> None:
        settings = Settings(
            observability_path=tmp_path / "logs" / "i.jsonl",
            redact_pii=True,
        )
        store = ObservabilityStore(settings)
        logger = RAGInteractionLogger(settings, store)
        logger.log_interaction(
            question="Mi email es test@example.com",
            question_type="in_scope",
            retrieval_result=_make_retrieval_result(),
            response_time_ms=100.0,
        )
        [entry] = store.read_all()
        assert "test@example.com" not in (entry["question_text"] or "")
        assert "[EMAIL]" in (entry["question_text"] or "")

    def test_redact_pii_false_guarda_texto_original(self, tmp_path: Path) -> None:
        settings = Settings(
            observability_path=tmp_path / "logs" / "i.jsonl",
            redact_pii=False,
        )
        store = ObservabilityStore(settings)
        logger = RAGInteractionLogger(settings, store)
        question = "¿Cuál es el plazo para renovar?"
        logger.log_interaction(
            question=question,
            question_type="in_scope",
            retrieval_result=_make_retrieval_result(),
            response_time_ms=100.0,
        )
        [entry] = store.read_all()
        assert entry["question_text"] == question

    def test_stage_latencies_redondeadas(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path)
        store = ObservabilityStore(settings)
        logger = RAGInteractionLogger(settings, store)
        logger.log_interaction(
            question="test",
            question_type="in_scope",
            retrieval_result=_make_retrieval_result(),
            response_time_ms=123.456789,
            stage_latencies={"retrieval_ms": 50.123456, "generation_ms": 73.333333},
        )
        [entry] = store.read_all()
        assert entry["stage_latencies"]["retrieval_ms"] == 50.12
        assert entry["stage_latencies"]["generation_ms"] == 73.33

    def test_retrieval_ids_y_scores_en_log(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path)
        store = ObservabilityStore(settings)
        logger = RAGInteractionLogger(settings, store)
        result = _make_retrieval_result(n_chunks=2)
        logger.log_interaction(
            question="test",
            question_type="in_scope",
            retrieval_result=result,
            response_time_ms=100.0,
        )
        [entry] = store.read_all()
        assert len(entry["retrieved_context_ids"]) == 2
        assert len(entry["retrieval_scores"]) == 2
        assert all(0.0 <= s <= 1.0 for s in entry["retrieval_scores"])

    def test_refused_flujo(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path)
        store = ObservabilityStore(settings)
        logger = RAGInteractionLogger(settings, store)
        result = _make_retrieval_result(sufficient=False, n_chunks=0)
        logger.log_interaction(
            question="pregunta fuera de tema",
            question_type="refused",
            retrieval_result=result,
            response_time_ms=50.0,
            answer=None,
        )
        [entry] = store.read_all()
        assert entry["question_type"] == "refused"
        assert entry["has_sufficient_context"] is False
        assert entry["answer"] is None

    def test_error_flujo(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path)
        store = ObservabilityStore(settings)
        logger = RAGInteractionLogger(settings, store)
        logger.log_interaction(
            question="test",
            question_type="error",
            retrieval_result=_make_retrieval_result(sufficient=False, n_chunks=0),
            response_time_ms=10.0,
            error="Connection refused",
        )
        [entry] = store.read_all()
        assert entry["error"] == "Connection refused"

    def test_store_default_se_crea_con_settings(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path)
        logger = RAGInteractionLogger(settings)
        logger.log_interaction(
            question="q",
            question_type="in_scope",
            retrieval_result=_make_retrieval_result(n_chunks=0, sufficient=False),
            response_time_ms=1.0,
        )
        assert Path(settings.observability_path).exists()
