"""Implementación concreta de PromptManager para pipelines RAG.

Recibe templates como dict[str, str] inyectado en el constructor, lo que
mantiene este módulo agnóstico de dominio (no sabe nada de migración, banca,
etc.). El contenido de los templates vive en la capa de dominio
(src/domain/prompt_templates/).

Formato de variables en templates: sintaxis de str.format_map(), es decir,
{variable_name}. Los templates deben definir exactamente estas tres variables:
  {context_block}        — chunks recuperados, uno por bloque con fuente/página
  {question}             — pregunta del usuario (ya validada)
  {domain_instructions}  — instrucciones específicas de dominio (disclaimer, scope)

Seguridad: _build_context_block() etiqueta cada chunk con su fuente y página
para que el template pueda rodearlos con marcadores explícitos (<context>…
</context>). El llamador pasa RetrievalResult como tipo estructurado; nunca
puede concatenar strings a mano y "olvidar" delimitarlos (ver base.py).
"""

from __future__ import annotations

import logging

from genai_toolkit.prompts.base import PromptInputs, PromptTemplateNotFoundError
from genai_toolkit.retrieval.types import RetrievalResult

logger = logging.getLogger(__name__)

_NO_CONTEXT = "(sin contexto disponible)"


class RagPromptManager:
    """PromptManager que renderiza templates RAG con variables estructuradas.

    Args:
        templates: Mapeo de template_id → string de template con
            placeholders {context_block}, {question} y {domain_instructions}.
    """

    def __init__(self, templates: dict[str, str]) -> None:
        self._templates = templates

    def render(self, template_id: str, inputs: PromptInputs) -> str:
        """Renderiza el template indicado con las variables de PromptInputs.

        Raises:
            PromptTemplateNotFoundError: Si template_id no está registrado.
        """
        template = self._templates.get(template_id)
        if template is None:
            raise PromptTemplateNotFoundError(
                f"Template '{template_id}' no encontrado. "
                f"Disponibles: {sorted(self._templates)}"
            )

        context_block = _build_context_block(inputs.retrieval_result)

        prompt = template.format_map(
            {
                "context_block": context_block,
                "question": inputs.question,
                "domain_instructions": inputs.domain_instructions,
            }
        )
        logger.debug(
            "render: template=%r chunks=%d prompt_chars=%d",
            template_id,
            len(inputs.retrieval_result.chunks),
            len(prompt),
        )
        return prompt


def _build_context_block(result: RetrievalResult) -> str:
    """Serializa los chunks de un RetrievalResult para insertarlos en el prompt.

    Cada chunk lleva su etiqueta de fuente/página para que el LLM pueda
    citar correctamente. El template es responsable de rodear este bloque
    con los marcadores explícitos que lo delimitan como dato (no instrucción).
    """
    if not result.chunks:
        return _NO_CONTEXT

    parts: list[str] = []
    for sc in result.chunks:
        m = sc.chunk.metadata
        label = f"[Fuente: {m.source_document}"
        if m.page is not None:
            label += f", Página {m.page}"
        label += "]"
        parts.append(f"{label}\n{sc.chunk.text}")

    return "\n\n".join(parts)
