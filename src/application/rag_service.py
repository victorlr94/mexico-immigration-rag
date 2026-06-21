"""RAGService: orquesta el pipeline completo de consulta RAG.

Esta clase es la única que combina todos los componentes del genai_toolkit
con las decisiones de dominio migratorio (templates, instrucciones, refusal).
La capa de presentación (Streamlit) solo llama a ask() — no sabe nada de
retrieval, embeddings ni prompts.

Separación de responsabilidades:
  - genai_toolkit/*: componentes reutilizables sin dominio.
  - domain/prompt_templates: templates y disclaimers migratorios.
  - application/rag_service.py (aquí): orquestación + timing + logging.
  - app/streamlit_app.py: presentación únicamente.
"""

from __future__ import annotations

import logging
import time

from application.types import RAGResponse, SourceCitation
from domain.prompt_templates import DISCLAIMER_ES
from genai_toolkit.config.settings import Settings
from genai_toolkit.llm.base import LLMProvider
from genai_toolkit.observability.logger import RAGInteractionLogger
from genai_toolkit.prompts.base import PromptInputs, PromptManager
from genai_toolkit.retrieval.base import Retriever
from genai_toolkit.retrieval.types import RetrievalResult, ScoredChunk

logger = logging.getLogger(__name__)

_TEMPLATE_ID = "rag_grounding_v1"

_REFUSAL_ANSWER = (
    "No encontré información suficiente en la documentación disponible "
    "para responder esta pregunta con certeza. "
    "Considera consultar directamente al INM o a un asesor migratorio certificado."
)


class RAGService:
    """Consulta completa: validación → retrieval → generación → logging."""

    def __init__(
        self,
        retriever: Retriever,
        llm: LLMProvider,
        prompt_manager: PromptManager,
        *,
        interaction_logger: RAGInteractionLogger | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._retriever = retriever
        self._llm = llm
        self._prompt_manager = prompt_manager
        self._logger = interaction_logger
        self._settings = settings or Settings()

    def ask(self, question: str) -> RAGResponse:
        """Procesa una consulta del usuario de extremo a extremo.

        Args:
            question: Texto de la pregunta. Se aplica strip() antes de
                cualquier validación.

        Returns:
            RAGResponse con la respuesta, fuentes y métricas de la
            interacción.

        Raises:
            ValueError: Si la pregunta está vacía o supera max_input_chars.
            RetrievalError: Si el retriever falla irrecuperablemente.
            LLMGenerationError: Si el LLM falla al generar la respuesta.
        """
        question = question.strip()
        if not question:
            raise ValueError("La pregunta no puede estar vacía.")
        if len(question) > self._settings.max_input_chars:
            raise ValueError(
                f"La pregunta supera el límite de "
                f"{self._settings.max_input_chars} caracteres."
            )

        t_start = time.perf_counter()
        stage_latencies: dict[str, float] = {}

        try:
            retrieval_result, stage_latencies = self._retrieve(
                question, stage_latencies
            )

            if not retrieval_result.has_sufficient_context:
                return self._build_refusal(
                    question, retrieval_result, t_start, stage_latencies
                )

            answer, stage_latencies = self._generate(
                question, retrieval_result, stage_latencies
            )
        except Exception as exc:
            self._log(
                question=question,
                question_type="error",
                retrieval_result=RetrievalResult(
                    query=question, chunks=[], has_sufficient_context=False
                ),
                response_time_ms=_elapsed_ms(t_start),
                stage_latencies=stage_latencies,
                error=str(exc),
            )
            raise

        response_time_ms = _elapsed_ms(t_start)
        self._log(
            question=question,
            question_type="in_scope",
            retrieval_result=retrieval_result,
            response_time_ms=response_time_ms,
            stage_latencies=stage_latencies,
            answer=answer,
        )

        return RAGResponse(
            answer=answer,
            sources=_extract_sources(retrieval_result.chunks),
            has_sufficient_context=True,
            response_time_ms=response_time_ms,
            question_type="in_scope",
        )

    # ------------------------------------------------------------------
    # Métodos privados
    # ------------------------------------------------------------------

    def _retrieve(
        self, question: str, stage_latencies: dict[str, float]
    ) -> tuple[RetrievalResult, dict[str, float]]:
        t0 = time.perf_counter()
        result = self._retriever.retrieve(question)
        stage_latencies = {**stage_latencies, "retrieval_ms": _elapsed_ms(t0)}
        return result, stage_latencies

    def _generate(
        self,
        question: str,
        retrieval_result: RetrievalResult,
        stage_latencies: dict[str, float],
    ) -> tuple[str, dict[str, float]]:
        inputs = PromptInputs(
            question=question,
            retrieval_result=retrieval_result,
            domain_instructions=DISCLAIMER_ES,
        )
        prompt = self._prompt_manager.render(_TEMPLATE_ID, inputs)
        t0 = time.perf_counter()
        answer = self._llm.generate(prompt)
        stage_latencies = {**stage_latencies, "generation_ms": _elapsed_ms(t0)}
        return answer, stage_latencies

    def _build_refusal(
        self,
        question: str,
        retrieval_result: RetrievalResult,
        t_start: float,
        stage_latencies: dict[str, float],
    ) -> RAGResponse:
        response_time_ms = _elapsed_ms(t_start)
        self._log(
            question=question,
            question_type="refused",
            retrieval_result=retrieval_result,
            response_time_ms=response_time_ms,
            stage_latencies=stage_latencies,
            answer=None,
        )
        return RAGResponse(
            answer=_REFUSAL_ANSWER,
            sources=[],
            has_sufficient_context=False,
            response_time_ms=response_time_ms,
            question_type="refused",
        )

    def _log(self, **kwargs: object) -> None:
        if self._logger is None:
            return
        try:
            self._logger.log_interaction(**kwargs)  # type: ignore[arg-type]
        except Exception:
            logger.exception("ObservabilityStore falló — la interacción continúa.")


def _elapsed_ms(t_start: float) -> float:
    return round((time.perf_counter() - t_start) * 1000, 2)


def _extract_sources(chunks: list[ScoredChunk]) -> list[SourceCitation]:
    seen: set[tuple[str, int | None]] = set()
    sources: list[SourceCitation] = []
    for sc in chunks:
        key = (sc.chunk.metadata.source_document, sc.chunk.metadata.page)
        if key not in seen:
            seen.add(key)
            sources.append(
                SourceCitation(
                    document=sc.chunk.metadata.source_document,
                    page=sc.chunk.metadata.page,
                )
            )
    return sources
