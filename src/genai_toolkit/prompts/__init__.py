"""Gestión de prompts: contrato de PromptManager."""

from genai_toolkit.prompts.base import (
    PromptInputs,
    PromptManager,
    PromptTemplateNotFoundError,
)

__all__ = ["PromptInputs", "PromptManager", "PromptTemplateNotFoundError"]
