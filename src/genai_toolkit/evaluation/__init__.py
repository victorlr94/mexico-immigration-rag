"""Evaluación de calidad RAG: evaluadores propios deterministas.

Las métricas que requieren un LLM juez (faithfulness, answer relevancy, context
precision/recall) se calculan con RAGAS desde la capa de aplicación
(``scripts/evaluate.py``). Este paquete contiene solo los evaluadores propios y
deterministas, agnósticos de dominio.
"""

from genai_toolkit.evaluation.custom_metrics import (
    CitationOutcome,
    RefusalOutcome,
    citation_accuracy,
    hallucination_rate,
    refusal_quality,
)

__all__ = [
    "CitationOutcome",
    "RefusalOutcome",
    "citation_accuracy",
    "hallucination_rate",
    "refusal_quality",
]
