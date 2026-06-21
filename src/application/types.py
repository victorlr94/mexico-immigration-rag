"""Tipos de respuesta de la capa de aplicación.

Estos tipos son el contrato entre RAGService (lógica) y la capa de
presentación (Streamlit). No dependen de ningún detalle de implementación
del genai_toolkit — solo de los conceptos de "respuesta" y "fuente".
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceCitation:
    """Referencia a un fragmento de documento que sustenta la respuesta.

    Attributes:
        document: Nombre del archivo fuente (ej. "guia_residencia.pdf").
        page: Número de página, si el documento tiene paginación. None para
            fuentes sin paginación (ej. texto plano).
    """

    document: str
    page: int | None = None


@dataclass(frozen=True)
class RAGResponse:
    """Resultado de una consulta al pipeline RAG.

    Attributes:
        answer: Respuesta generada o mensaje de refusal.
        sources: Fragmentos de documentos que sustentaron la respuesta.
            Lista vacía cuando question_type == "refused".
        has_sufficient_context: True si se encontraron chunks por encima del
            umbral de confianza y se generó una respuesta real.
        response_time_ms: Latencia total de la interacción en ms.
        question_type: "in_scope" si el LLM respondió con contexto;
            "refused" si no hubo contexto suficiente.
    """

    answer: str
    sources: list[SourceCitation]
    has_sufficient_context: bool
    response_time_ms: float
    question_type: str
