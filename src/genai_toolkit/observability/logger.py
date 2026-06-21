"""RAGInteractionLogger: construye y persiste InteractionLog por interacción RAG.

Responsabilidades:
- Redacción de PII antes de loggear (06_observability.md: "redactar antes de
  loggear, no omitir ni registrar en bruto").
- Construcción del InteractionLog a partir de los artefactos del pipeline.
- Delegación al ObservabilityStore para la persistencia.

El llamador (RAGService) solo pasa los artefactos que ya tiene; este módulo
se encarga de la redacción, el hashing y el formateo.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime

from genai_toolkit.config.settings import Settings
from genai_toolkit.observability.store import (
    InteractionLog,
    ObservabilityStore,
    SourceReference,
)
from genai_toolkit.retrieval.types import RetrievalResult

# Patrones de PII del dominio migratorio mexicano.
# Orden: más específico primero (CURP antes que RFC, que comparte prefijo alfanum).
_PII_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # CURP: 4L + 6D fecha + H/M + 2L estado + 3L + 1AN + 1D
    (re.compile(r"\b[A-Z]{4}\d{6}[HM][A-Z]{2}[A-Z]{3}[A-Z0-9]\d\b"), "[CURP]"),
    # RFC persona física (4L+6D+3AN) o moral (3L+6D+3AN)
    (re.compile(r"\b[A-Z]{3,4}\d{6}[A-Z0-9]{3}\b"), "[RFC]"),
    # Correo electrónico
    (re.compile(r"\b[\w.+\-]+@[\w\-]+\.[\w.]{2,}\b", re.ASCII), "[EMAIL]"),
    # Teléfono con prefijo +52 compacto, sin separador (ej. +525512345678)
    (re.compile(r"\+52\d{10}(?!\d)"), "[TEL]"),
    # Teléfono 10 dígitos sin prefijo compacto (no rodeado de más dígitos)
    (re.compile(r"(?<!\d)\d{10}(?!\d)"), "[TEL]"),
    # Número de pasaporte: 1-2 letras seguidas de 7-9 dígitos
    (re.compile(r"\b[A-Z]{1,2}\d{7,9}\b"), "[PASAPORTE]"),
]


def redact_pii(text: str) -> str:
    """Aplica redacción de PII al texto usando los patrones del dominio.

    No garantiza detección perfecta de todos los PII posibles —
    cubre los tipos más comunes en consultas de trámites migratorios MX.
    """
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class RAGInteractionLogger:
    """Crea y persiste InteractionLog a partir de los artefactos del pipeline."""

    def __init__(
        self,
        settings: Settings | None = None,
        store: ObservabilityStore | None = None,
    ) -> None:
        self._settings = settings or Settings()
        self._store = store or ObservabilityStore(self._settings)

    def log_interaction(
        self,
        *,
        question: str,
        question_type: str,
        retrieval_result: RetrievalResult,
        response_time_ms: float,
        stage_latencies: dict[str, float] | None = None,
        answer: str | None = None,
        error: str | None = None,
    ) -> None:
        """Construye y persiste un InteractionLog.

        Args:
            question: Texto original de la pregunta del usuario.
            question_type: "in_scope" | "refused" | "error".
            retrieval_result: Resultado completo del retriever.
            response_time_ms: Latencia total de la interacción en ms.
            stage_latencies: Latencias por etapa (retrieval_ms, generation_ms, …).
            answer: Respuesta generada (None en refusal o error).
            error: Mensaje de la excepción si la interacción falló.
        """
        question_hash = hashlib.sha256(question.encode("utf-8")).hexdigest()[:16]
        question_text = redact_pii(question) if self._settings.redact_pii else question

        record = InteractionLog(
            timestamp=datetime.now(UTC).isoformat(),
            question_hash=question_hash,
            question_type=question_type,
            model=self._settings.llm_model,
            embedding_model=self._settings.embedding_model,
            retrieved_context_ids=[sc.chunk.id for sc in retrieval_result.chunks],
            source_documents=[
                SourceReference(
                    doc=sc.chunk.metadata.source_document,
                    page=sc.chunk.metadata.page,
                )
                for sc in retrieval_result.chunks
            ],
            retrieval_scores=[sc.score for sc in retrieval_result.chunks],
            has_sufficient_context=retrieval_result.has_sufficient_context,
            response_time_ms=round(response_time_ms, 2),
            stage_latencies={
                k: round(v, 2) for k, v in (stage_latencies or {}).items()
            },
            answer=answer,
            error=error,
            question_text=question_text,
        )
        self._store.log(record)
