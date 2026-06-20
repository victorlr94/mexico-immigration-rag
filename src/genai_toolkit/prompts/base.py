"""Contrato para la gestión de prompts.

Separa la carga/versionado/renderizado de templates (genérico, reutilizable)
del contenido de los templates en sí (específico de dominio, vive en
`src/domain/prompt_templates/` y en `prompts/`). El PromptManager no sabe nada
de migración: solo sabe cargar un template por id y rellenarlo con variables.

Decisión de diseño clave para seguridad: `render` exige que el contexto
recuperado (RetrievalResult) se pase como campo estructurado, no como string
libre concatenado por el llamador. Esto fuerza a que la implementación
concreta sea la única responsable de delimitar el contexto con marcadores
explícitos en el prompt final (ver Security Skill: "el contenido recuperado es
dato, nunca instrucción") — un llamador no puede "olvidar" delimitarlo porque
no tiene la oportunidad de ensamblar ese string a mano.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from genai_toolkit.retrieval.types import RetrievalResult


@dataclass(frozen=True)
class PromptInputs:
    """Variables que un template de RAG necesita para renderizarse.

    Mantener esto como un tipo explícito (en vez de **kwargs) hace que el
    contrato de PromptManager.render sea verificable por mypy: si un template
    nuevo necesita una variable más, se extiende este dataclass y el type
    checker señala todos los call sites que faltan actualizar.

    Attributes:
        question: La pregunta del usuario, ya validada.
        retrieval_result: Resultado de la capa de retrieval. La
            implementación de PromptManager es responsable de serializar
            `retrieval_result.chunks` dentro de marcadores explícitos de
            contexto (ej. <context>...</context>) al renderizar.
        domain_instructions: Instrucciones específicas de dominio a
            inyectar (ej. el disclaimer migratorio, las reglas de scope).
            El PromptManager las trata como texto opaco — no las
            interpreta, solo las coloca en la posición que el template
            defina.
    """

    question: str
    retrieval_result: RetrievalResult
    domain_instructions: str


@runtime_checkable
class PromptManager(Protocol):
    """Carga templates versionados y los renderiza con variables de entrada."""

    def render(self, template_id: str, inputs: PromptInputs) -> str:
        """Renderiza un template con las variables dadas.

        Args:
            template_id: Identificador del template a usar (ej.
                "rag_grounding_v1"). Permite versionar templates sin
                romper código que ya los referencia por id anterior.
            inputs: Variables a inyectar en el template.

        Returns:
            El prompt final, listo para enviarse a un LLMProvider.
            Debe incluir el contexto delimitado explícitamente (ver
            Security Skill) y las instrucciones de grounding/refusal.

        Raises:
            PromptTemplateNotFoundError: Si `template_id` no existe.
        """
        ...


class PromptTemplateNotFoundError(Exception):
    """El template solicitado no existe o no pudo cargarse."""
