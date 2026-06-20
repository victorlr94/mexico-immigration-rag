"""Capa LLM: contrato e implementación con Ollama."""

from genai_toolkit.llm.base import LLMGenerationError, LLMProvider
from genai_toolkit.llm.ollama import OllamaProvider

__all__ = ["LLMGenerationError", "LLMProvider", "OllamaProvider"]
