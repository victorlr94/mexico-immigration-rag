"""Evaluadores propios, deterministas y agnósticos de dominio.

Complementan las métricas de RAGAS (faithfulness, answer_relevancy, etc.), que
requieren un LLM juez, con métricas que se calculan sin modelo y son por tanto
reproducibles bit a bit y baratas de correr en CI:

- ``refusal_quality``: ¿el sistema decide correctamente cuándo responder y cuándo
  rechazar? En un dominio regulado, rechazar mal (responder algo sin sustento) es
  peor que callar — de ahí que sea una métrica de primer orden.
- ``citation_accuracy``: ¿las fuentes citadas corresponden al documento esperado?
  Una cita incorrecta destruye la confianza del usuario.
- ``hallucination_rate``: proxy determinista del riesgo principal — fracción de
  preguntas que debían rechazarse pero recibieron una respuesta sustantiva. La
  medición a nivel de afirmación (claim) la cubre RAGAS faithfulness.

Estas funciones operan sobre tipos genéricos (booleanos y nombres de fuente), no
sobre tipos del dominio migratorio: viven en ``genai_toolkit`` y se reutilizan en
cualquier dominio (ver ADR-001).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PurePath


@dataclass(frozen=True)
class RefusalOutcome:
    """Resultado esperado vs. real de la decisión de rechazo para una pregunta.

    Attributes:
        should_refuse: True si la pregunta debía rechazarse (fuera de dominio o
            sin respuesta en el corpus).
        did_refuse: True si el sistema efectivamente rechazó.
    """

    should_refuse: bool
    did_refuse: bool


@dataclass(frozen=True)
class CitationOutcome:
    """Fuente esperada vs. fuentes realmente citadas para una pregunta.

    Attributes:
        expected_source: Nombre del documento que debería sustentar la respuesta.
            Cadena vacía si la pregunta no tiene fuente esperada (se ignora).
        cited_sources: Nombres de los documentos efectivamente citados.
    """

    expected_source: str
    cited_sources: tuple[str, ...]


def _normalize_source(name: str) -> str:
    """Normaliza un nombre de fuente a su basename en minúsculas para comparar."""
    return PurePath(name.strip()).name.lower()


def refusal_quality(outcomes: Sequence[RefusalOutcome]) -> float:
    """Fracción de decisiones de rechazo correctas (en ambas direcciones).

    Una decisión es correcta cuando ``should_refuse == did_refuse``: rechazar lo
    que debía rechazarse y responder lo que debía responderse.

    Returns:
        Valor en [0.0, 1.0]. 1.0 si la secuencia está vacía (no hay errores).
    """
    if not outcomes:
        return 1.0
    correct = sum(1 for o in outcomes if o.should_refuse == o.did_refuse)
    return correct / len(outcomes)


def citation_accuracy(outcomes: Sequence[CitationOutcome]) -> float:
    """Fracción de respuestas que citan el documento esperado.

    Solo cuentan las preguntas con ``expected_source`` no vacío; las demás se
    ignoran (no penalizan ni premian).

    Returns:
        Valor en [0.0, 1.0]. 1.0 si no hay preguntas con fuente esperada.
    """
    relevant = [o for o in outcomes if o.expected_source.strip()]
    if not relevant:
        return 1.0
    hits = 0
    for o in relevant:
        expected = _normalize_source(o.expected_source)
        cited = {_normalize_source(c) for c in o.cited_sources}
        if expected in cited:
            hits += 1
    return hits / len(relevant)


def hallucination_rate(outcomes: Sequence[RefusalOutcome]) -> float:
    """Proxy determinista: fracción de casos que debían rechazarse pero no.

    Mide específicamente la dirección peligrosa del error (responder cuando no
    hay sustento). Es un proxy: la detección de alucinación a nivel de afirmación
    requiere un LLM juez (RAGAS faithfulness).

    Returns:
        Valor en [0.0, 1.0]. 0.0 si no había casos que debieran rechazarse.
    """
    should = [o for o in outcomes if o.should_refuse]
    if not should:
        return 0.0
    answered_anyway = sum(1 for o in should if not o.did_refuse)
    return answered_anyway / len(should)
