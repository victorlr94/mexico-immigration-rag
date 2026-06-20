"""Gestión de prompts: contrato e implementación concreta RAG."""

from genai_toolkit.prompts.base import (
    PromptInputs,
    PromptManager,
    PromptTemplateNotFoundError,
)
from genai_toolkit.prompts.rag_prompt_manager import RagPromptManager

__all__ = [
    "PromptInputs",
    "PromptManager",
    "PromptTemplateNotFoundError",
    "RagPromptManager",
]
