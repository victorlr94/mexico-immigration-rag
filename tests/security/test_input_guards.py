"""Security tests — validación de entrada (LLM01, LLM04).

Verifica que RAGService rechaza de forma controlada payloads adversariales
antes de que lleguen al pipeline RAG. El comportamiento esperado es siempre
un ValueError tipado, nunca un crash ni una fuga de información.

Riesgos mitigados:
  - LLM04 (DoS por inputs masivos): límite de longitud bloqueante.
  - LLM01 (prompt injection directo): la validación actúa como primera barrera
    antes de que el input toque el retriever, el LLM o los prompts.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from application.rag_service import RAGService
from genai_toolkit.config.settings import Settings
from genai_toolkit.retrieval.types import RetrievalResult


def _build_service(*, max_input_chars: int = 500) -> RAGService:
    """RAGService con dependencias mockeadas para tests de validación de entrada."""
    retriever = MagicMock()
    retriever.retrieve.return_value = RetrievalResult(
        query="",
        chunks=[],
        has_sufficient_context=False,
    )
    llm = MagicMock()
    llm.generate.return_value = "respuesta"
    prompt_manager = MagicMock()
    prompt_manager.render.return_value = "prompt"

    settings = Settings(max_input_chars=max_input_chars)
    return RAGService(retriever, llm, prompt_manager, settings=settings)


@pytest.mark.security
class TestInputLengthGuard:
    """Límite de longitud — mitiga DoS y prompts gigantes (LLM04)."""

    def test_empty_string_is_rejected(self) -> None:
        service = _build_service()
        with pytest.raises(ValueError, match="vacía"):
            service.ask("")

    def test_whitespace_only_is_rejected(self) -> None:
        service = _build_service()
        with pytest.raises(ValueError, match="vacía"):
            service.ask("   \t\n   ")

    def test_newline_only_is_rejected(self) -> None:
        service = _build_service()
        with pytest.raises(ValueError, match="vacía"):
            service.ask("\n\n\n")

    def test_input_at_exact_limit_is_accepted(self) -> None:
        service = _build_service(max_input_chars=50)
        response = service.ask("a" * 50)
        assert response is not None

    def test_input_one_over_limit_is_rejected(self) -> None:
        service = _build_service(max_input_chars=50)
        with pytest.raises(ValueError, match="50"):
            service.ask("a" * 51)

    def test_massive_input_is_rejected(self) -> None:
        """Un payload de 100 000 chars no llega al pipeline (DoS mitigation)."""
        service = _build_service(max_input_chars=2000)
        with pytest.raises(ValueError, match="2000"):
            service.ask("A" * 100_000)


@pytest.mark.security
class TestInputSanitizationBoundary:
    """Verifica que la validación actúa ANTES de cualquier llamada al pipeline."""

    def test_retriever_never_called_on_empty_input(self) -> None:
        retriever = MagicMock()
        llm = MagicMock()
        prompt_manager = MagicMock()
        service = RAGService(
            retriever, llm, prompt_manager, settings=Settings(max_input_chars=200)
        )
        with pytest.raises(ValueError):
            service.ask("")
        retriever.retrieve.assert_not_called()
        llm.generate.assert_not_called()

    def test_retriever_never_called_on_oversized_input(self) -> None:
        retriever = MagicMock()
        llm = MagicMock()
        prompt_manager = MagicMock()
        service = RAGService(
            retriever, llm, prompt_manager, settings=Settings(max_input_chars=10)
        )
        with pytest.raises(ValueError):
            service.ask("A" * 100)
        retriever.retrieve.assert_not_called()

    def test_strip_whitespace_before_validation(self) -> None:
        """El strip() de whitespace ocurre antes de pasarlo al retriever."""
        retriever = MagicMock()
        retriever.retrieve.return_value = RetrievalResult(
            query="", chunks=[], has_sufficient_context=False
        )
        llm = MagicMock()
        prompt_manager = MagicMock()
        service = RAGService(
            retriever, llm, prompt_manager, settings=Settings(max_input_chars=200)
        )
        service.ask("  pregunta válida  ")
        retriever.retrieve.assert_called_once_with("pregunta válida")
