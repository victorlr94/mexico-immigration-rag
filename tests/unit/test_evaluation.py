"""Unit tests para los evaluadores propios deterministas.

No requieren LLM ni modelos: validan la lógica pura de las métricas que
complementan a RAGAS (refusal quality, citation accuracy, hallucination rate).
"""

from __future__ import annotations

import pytest

from genai_toolkit.evaluation import (
    CitationOutcome,
    RefusalOutcome,
    citation_accuracy,
    hallucination_rate,
    refusal_quality,
)


@pytest.mark.unit
class TestRefusalQuality:
    def test_all_correct_is_one(self) -> None:
        outcomes = [
            RefusalOutcome(should_refuse=False, did_refuse=False),
            RefusalOutcome(should_refuse=True, did_refuse=True),
        ]
        assert refusal_quality(outcomes) == 1.0

    def test_all_wrong_is_zero(self) -> None:
        outcomes = [
            RefusalOutcome(should_refuse=False, did_refuse=True),
            RefusalOutcome(should_refuse=True, did_refuse=False),
        ]
        assert refusal_quality(outcomes) == 0.0

    def test_half_correct(self) -> None:
        outcomes = [
            RefusalOutcome(should_refuse=True, did_refuse=True),
            RefusalOutcome(should_refuse=True, did_refuse=False),
        ]
        assert refusal_quality(outcomes) == 0.5

    def test_empty_is_one(self) -> None:
        assert refusal_quality([]) == 1.0


@pytest.mark.unit
class TestCitationAccuracy:
    def test_exact_match_is_one(self) -> None:
        outcomes = [
            CitationOutcome("guia.pdf", ("guia.pdf", "otra.pdf")),
        ]
        assert citation_accuracy(outcomes) == 1.0

    def test_missing_citation_is_zero(self) -> None:
        outcomes = [CitationOutcome("guia.pdf", ("otra.pdf",))]
        assert citation_accuracy(outcomes) == 0.0

    def test_case_insensitive_match(self) -> None:
        outcomes = [CitationOutcome("Guia.PDF", ("guia.pdf",))]
        assert citation_accuracy(outcomes) == 1.0

    def test_basename_match_ignores_path(self) -> None:
        outcomes = [CitationOutcome("data/samples/guia.pdf", ("guia.pdf",))]
        assert citation_accuracy(outcomes) == 1.0

    def test_empty_expected_source_is_ignored(self) -> None:
        """Preguntas sin fuente esperada no cuentan; aquí no hay relevantes → 1.0."""
        outcomes = [CitationOutcome("", ("cualquiera.pdf",))]
        assert citation_accuracy(outcomes) == 1.0

    def test_mixed_relevant_and_ignored(self) -> None:
        outcomes = [
            CitationOutcome("a.pdf", ("a.pdf",)),  # hit
            CitationOutcome("b.pdf", ("z.pdf",)),  # miss
            CitationOutcome("", ("x.pdf",)),  # ignorada
        ]
        assert citation_accuracy(outcomes) == 0.5

    def test_no_outcomes_is_one(self) -> None:
        assert citation_accuracy([]) == 1.0


@pytest.mark.unit
class TestHallucinationRate:
    def test_no_cases_to_refuse_is_zero(self) -> None:
        outcomes = [RefusalOutcome(should_refuse=False, did_refuse=False)]
        assert hallucination_rate(outcomes) == 0.0

    def test_answered_when_should_refuse_counts(self) -> None:
        outcomes = [
            RefusalOutcome(should_refuse=True, did_refuse=False),  # alucinó
            RefusalOutcome(should_refuse=True, did_refuse=True),  # bien
        ]
        assert hallucination_rate(outcomes) == 0.5

    def test_all_refused_correctly_is_zero(self) -> None:
        outcomes = [
            RefusalOutcome(should_refuse=True, did_refuse=True),
            RefusalOutcome(should_refuse=True, did_refuse=True),
        ]
        assert hallucination_rate(outcomes) == 0.0

    def test_in_scope_questions_are_ignored(self) -> None:
        """Solo cuentan los casos que debían rechazarse."""
        outcomes = [
            RefusalOutcome(should_refuse=False, did_refuse=False),
            RefusalOutcome(should_refuse=True, did_refuse=False),  # único relevante
        ]
        assert hallucination_rate(outcomes) == 1.0

    def test_empty_is_zero(self) -> None:
        assert hallucination_rate([]) == 0.0
