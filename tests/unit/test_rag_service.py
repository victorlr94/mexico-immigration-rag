"""Unit tests para RAGService.

Retriever, LLMProvider y PromptManager se mockean: lo que se verifica aquí
es la orquestación (flujo in_scope vs. refused vs. error), la validación de
entrada, la extracción de fuentes sin duplicados y la integración con el
logger de observabilidad.

Ningún modelo real se carga en estos tests.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from application.rag_service import _REFUSAL_ANSWER, RAGService, _extract_sources
from application.types import RAGResponse, SourceCitation
from genai_toolkit.config.settings import Settings
from genai_toolkit.retrieval.base import RetrievalError
from genai_toolkit.retrieval.types import (
    Chunk,
    ChunkMetadata,
    RetrievalResult,
    ScoredChunk,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(
    chunk_id: str = "c1",
    source: str = "guia.pdf",
    page: int | None = 3,
) -> Chunk:
    return Chunk(
        id=chunk_id,
        text="Texto de ejemplo.",
        metadata=ChunkMetadata(source_document=source, page=page, chunk_index=0),
    )


def _make_retrieval_result(
    sufficient: bool = True,
    n_chunks: int = 2,
    source: str = "guia.pdf",
) -> RetrievalResult:
    chunks = [
        ScoredChunk(
            chunk=_make_chunk(f"c{i}", source=source, page=i + 1),
            score=0.85 - i * 0.05,
        )
        for i in range(n_chunks)
    ]
    return RetrievalResult(
        query="¿Cuáles son los requisitos?",
        chunks=chunks,
        has_sufficient_context=sufficient,
    )


def _build_service(
    *,
    retrieval_result: RetrievalResult | None = None,
    llm_answer: str = "Esta es la respuesta generada.",
    with_logger: bool = True,
    max_input_chars: int = 2000,
) -> tuple[RAGService, MagicMock, MagicMock, MagicMock, MagicMock]:
    """Construye un RAGService completamente mockeado."""
    if retrieval_result is None:
        retrieval_result = _make_retrieval_result()

    retriever = MagicMock()
    retriever.retrieve.return_value = retrieval_result

    llm = MagicMock()
    llm.generate.return_value = llm_answer

    prompt_manager = MagicMock()
    prompt_manager.render.return_value = "prompt ensamblado"

    interaction_logger = MagicMock() if with_logger else None

    settings = Settings(max_input_chars=max_input_chars)
    service = RAGService(
        retriever,
        llm,
        prompt_manager,
        interaction_logger=interaction_logger,
        settings=settings,
    )
    return service, retriever, llm, prompt_manager, interaction_logger


# ---------------------------------------------------------------------------
# Flujo in_scope (camino feliz)
# ---------------------------------------------------------------------------


class TestAskInScope:
    def test_retorna_rag_response(self) -> None:
        service, *_ = _build_service()
        response = service.ask("¿Cuáles son los requisitos?")
        assert isinstance(response, RAGResponse)

    def test_question_type_in_scope(self) -> None:
        service, *_ = _build_service()
        response = service.ask("¿Cuáles son los requisitos?")
        assert response.question_type == "in_scope"

    def test_has_sufficient_context_true(self) -> None:
        service, *_ = _build_service()
        response = service.ask("pregunta")
        assert response.has_sufficient_context is True

    def test_answer_viene_del_llm(self) -> None:
        service, *_ = _build_service(llm_answer="Respuesta del LLM.")
        response = service.ask("pregunta")
        assert response.answer == "Respuesta del LLM."

    def test_fuentes_extraidas_de_chunks(self) -> None:
        service, *_ = _build_service()
        response = service.ask("pregunta")
        assert len(response.sources) > 0
        assert all(isinstance(s, SourceCitation) for s in response.sources)

    def test_response_time_ms_positivo(self) -> None:
        service, *_ = _build_service()
        response = service.ask("pregunta")
        assert response.response_time_ms > 0

    def test_retriever_llamado_con_pregunta(self) -> None:
        service, retriever, *_ = _build_service()
        service.ask("¿qué necesito?")
        retriever.retrieve.assert_called_once_with("¿qué necesito?")

    def test_llm_generate_llamado(self) -> None:
        service, _, llm, *_ = _build_service()
        service.ask("pregunta")
        llm.generate.assert_called_once()

    def test_prompt_manager_render_llamado(self) -> None:
        service, _, _, prompt_manager, _ = _build_service()
        service.ask("pregunta")
        prompt_manager.render.assert_called_once()

    def test_strip_whitespace_en_pregunta(self) -> None:
        service, retriever, *_ = _build_service()
        service.ask("  ¿qué necesito?  ")
        retriever.retrieve.assert_called_once_with("¿qué necesito?")

    def test_logger_llamado_con_question_type_in_scope(self) -> None:
        service, _, _, _, interaction_logger = _build_service()
        service.ask("pregunta")
        interaction_logger.log_interaction.assert_called_once()
        call_kwargs = interaction_logger.log_interaction.call_args.kwargs
        assert call_kwargs["question_type"] == "in_scope"

    def test_logger_recibe_answer(self) -> None:
        service, _, _, _, interaction_logger = _build_service(
            llm_answer="Respuesta exacta."
        )
        service.ask("pregunta")
        call_kwargs = interaction_logger.log_interaction.call_args.kwargs
        assert call_kwargs["answer"] == "Respuesta exacta."

    def test_logger_recibe_stage_latencies(self) -> None:
        service, _, _, _, interaction_logger = _build_service()
        service.ask("pregunta")
        call_kwargs = interaction_logger.log_interaction.call_args.kwargs
        latencies = call_kwargs["stage_latencies"]
        assert "retrieval_ms" in latencies
        assert "generation_ms" in latencies


# ---------------------------------------------------------------------------
# Flujo refused (contexto insuficiente)
# ---------------------------------------------------------------------------


class TestAskRefused:
    def test_question_type_refused(self) -> None:
        result = _make_retrieval_result(sufficient=False, n_chunks=0)
        service, *_ = _build_service(retrieval_result=result)
        response = service.ask("¿Qué es la CURP?")
        assert response.question_type == "refused"

    def test_has_sufficient_context_false(self) -> None:
        result = _make_retrieval_result(sufficient=False, n_chunks=0)
        service, *_ = _build_service(retrieval_result=result)
        response = service.ask("pregunta")
        assert response.has_sufficient_context is False

    def test_respuesta_es_refusal_answer(self) -> None:
        result = _make_retrieval_result(sufficient=False, n_chunks=0)
        service, *_ = _build_service(retrieval_result=result)
        response = service.ask("pregunta")
        assert response.answer == _REFUSAL_ANSWER

    def test_sources_vacias_en_refusal(self) -> None:
        result = _make_retrieval_result(sufficient=False, n_chunks=0)
        service, *_ = _build_service(retrieval_result=result)
        response = service.ask("pregunta")
        assert response.sources == []

    def test_llm_no_se_llama_en_refusal(self) -> None:
        result = _make_retrieval_result(sufficient=False, n_chunks=0)
        service, _, llm, *_ = _build_service(retrieval_result=result)
        service.ask("pregunta")
        llm.generate.assert_not_called()

    def test_logger_llamado_con_refused(self) -> None:
        result = _make_retrieval_result(sufficient=False, n_chunks=0)
        service, _, _, _, interaction_logger = _build_service(retrieval_result=result)
        service.ask("pregunta")
        call_kwargs = interaction_logger.log_interaction.call_args.kwargs
        assert call_kwargs["question_type"] == "refused"


# ---------------------------------------------------------------------------
# Validación de entrada
# ---------------------------------------------------------------------------


class TestInputValidation:
    def test_pregunta_vacia_lanza_value_error(self) -> None:
        service, *_ = _build_service()
        with pytest.raises(ValueError, match="vacía"):
            service.ask("")

    def test_pregunta_solo_espacios_lanza_value_error(self) -> None:
        service, *_ = _build_service()
        with pytest.raises(ValueError, match="vacía"):
            service.ask("   ")

    def test_pregunta_demasiado_larga_lanza_value_error(self) -> None:
        service, *_ = _build_service(max_input_chars=10)
        with pytest.raises(ValueError, match="límite"):
            service.ask("x" * 11)

    def test_pregunta_en_el_limite_no_lanza(self) -> None:
        service, *_ = _build_service(max_input_chars=10)
        response = service.ask("x" * 10)
        assert isinstance(response, RAGResponse)


# ---------------------------------------------------------------------------
# Manejo de errores del pipeline
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_retriever_error_se_propaga(self) -> None:
        service, retriever, *_ = _build_service()
        retriever.retrieve.side_effect = RetrievalError("timeout")
        with pytest.raises(RetrievalError):
            service.ask("pregunta")

    def test_retriever_error_se_loggea(self) -> None:
        service, retriever, _, _, interaction_logger = _build_service()
        retriever.retrieve.side_effect = RetrievalError("timeout")
        with pytest.raises(RetrievalError):
            service.ask("pregunta")
        call_kwargs = interaction_logger.log_interaction.call_args.kwargs
        assert call_kwargs["question_type"] == "error"
        assert "timeout" in call_kwargs["error"]

    def test_logger_falla_silenciosamente(self) -> None:
        service, _, _, _, interaction_logger = _build_service()
        interaction_logger.log_interaction.side_effect = Exception("store down")
        response = service.ask("pregunta")
        assert response.question_type == "in_scope"

    def test_sin_logger_no_falla(self) -> None:
        service, *_ = _build_service(with_logger=False)
        response = service.ask("pregunta")
        assert isinstance(response, RAGResponse)


# ---------------------------------------------------------------------------
# Extracción de fuentes (deduplica por doc+página)
# ---------------------------------------------------------------------------


class TestExtractSources:
    def test_fuentes_unicas(self) -> None:
        chunks = [
            ScoredChunk(chunk=_make_chunk("c1", "doc.pdf", 1), score=0.9),
            ScoredChunk(chunk=_make_chunk("c2", "doc.pdf", 1), score=0.85),
            ScoredChunk(chunk=_make_chunk("c3", "doc.pdf", 2), score=0.80),
        ]
        sources = _extract_sources(chunks)
        assert len(sources) == 2

    def test_orden_preservado(self) -> None:
        chunks = [
            ScoredChunk(chunk=_make_chunk("c1", "a.pdf", 1), score=0.9),
            ScoredChunk(chunk=_make_chunk("c2", "b.pdf", 2), score=0.85),
        ]
        sources = _extract_sources(chunks)
        assert sources[0].document == "a.pdf"
        assert sources[1].document == "b.pdf"

    def test_chunks_vacios_devuelven_lista_vacia(self) -> None:
        assert _extract_sources([]) == []

    def test_pagina_none_en_source(self) -> None:
        chunks = [ScoredChunk(chunk=_make_chunk("c1", "doc.pdf", None), score=0.9)]
        [source] = _extract_sources(chunks)
        assert source.page is None
