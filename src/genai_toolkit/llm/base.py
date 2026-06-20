"""Contrato para proveedores de modelos de lenguaje.

Permite sustituir Ollama por otro backend local o por una API externa sin
tocar el RAG Pipeline ni el Prompt Management. La implementación concreta
(OllamaProvider) vive en `llm/ollama.py`.

Decisión de diseño: el método se llama `generate`, no `chat`, y recibe un
prompt ya ensamblado (string), no una lista de mensajes. Esto mantiene el
contrato simple para la POC; si en el futuro se necesita soporte multi-turno
real (historial de conversación), se extiende el Protocol entonces — no se
sobrearquitectura ahora para un caso que no existe todavía (la app es de
preguntas independientes, no un chat con memoria).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Genera texto a partir de un prompt usando un modelo de lenguaje."""

    def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> str:
        """Genera una respuesta de texto a partir de un prompt completo.

        Args:
            prompt: Prompt ya ensamblado por el PromptManager (incluye
                system instructions, contexto delimitado y la pregunta).
                Este método no construye prompts, solo los ejecuta.
            temperature: Aleatoriedad de la generación. Por defecto baja
                (0.1) porque en un RAG sobre dominio regulado se prioriza
                fidelidad al contexto sobre creatividad — ver Security
                Skill, sección de alucinaciones.
            max_tokens: Límite de tokens de salida. None delega el límite
                por defecto al backend subyacente.

        Returns:
            El texto generado, sin procesar (el OutputGuard se encarga de
            validar grounding y extraer estructura después, fuera de este
            Protocol).

        Raises:
            LLMGenerationError: Si el backend falla, no responde dentro de
                un timeout razonable, o devuelve una respuesta vacía.
        """
        ...

    @property
    def model_name(self) -> str:
        """Identificador del modelo en uso (ej. "llama3.1:8b").

        Se registra en cada interacción vía Observability Layer, para
        poder comparar calidad/latencia entre modelos.
        """
        ...


class LLMGenerationError(Exception):
    """Fallo al generar texto con el modelo de lenguaje."""
