"""Implementación de LLMProvider con Ollama (backend local, sin API de pago).

Usa el cliente oficial de Python `ollama~=0.3`. El timeout de 120 s cubre
la generación de llama3.1:8b en CPU — ajustar vía constructor si el hardware
es más lento.

El parámetro `temperature` del Protocol (default 0.1) refleja la preferencia
del proyecto por fidelidad sobre creatividad en un dominio regulado: el pipeline
lo pasa explícitamente desde Settings.llm_temperature para que el llamador
siempre controle la temperatura final.
"""

from __future__ import annotations

import logging

from ollama import Client

from genai_toolkit.config.settings import Settings
from genai_toolkit.llm.base import LLMGenerationError

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT_SECS = 120.0


class OllamaProvider:
    """LLMProvider que delega la generación a un servidor Ollama local.

    El cliente se crea en el constructor (operación ligera) y se reutiliza
    en todas las llamadas a generate().
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        timeout: float = _REQUEST_TIMEOUT_SECS,
    ) -> None:
        _s = settings or Settings()
        self._model: str = _s.llm_model
        self._temperature: float = _s.llm_temperature
        self._seed: int | None = _s.llm_seed
        self._client: Client = Client(host=_s.ollama_base_url, timeout=timeout)
        logger.info(
            "OllamaProvider listo: model=%r, base_url=%r, temperature=%.2f, seed=%r",
            self._model,
            _s.ollama_base_url,
            self._temperature,
            self._seed,
        )

    def generate(
        self,
        prompt: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        seed: int | None = None,
    ) -> str:
        """Genera texto a partir de un prompt ensamblado por el PromptManager.

        Args:
            prompt: Prompt completo (system + contexto + query).
            temperature: Aleatoriedad (0.0 = determinista). None usa la
                temperatura configurada en Settings (default del proyecto:
                0.1, baja porque en RAG sobre dominio regulado se prioriza
                fidelidad).
            max_tokens: Límite de tokens de salida. None deja el default
                de Ollama (depende del modelo).
            seed: Semilla de muestreo. None usa la configurada en Settings
                (None por defecto = no determinista). Fijarla hace
                reproducible la generación con la misma temperatura/modelo.

        Returns:
            Texto generado, sin espacios de cabeza/cola.

        Raises:
            LLMGenerationError: Si Ollama no responde, falla la conexión,
                o devuelve una respuesta vacía.
        """
        effective_temperature = (
            temperature if temperature is not None else self._temperature
        )
        effective_seed = seed if seed is not None else self._seed
        options: dict[str, object] = {"temperature": effective_temperature}
        if effective_seed is not None:
            options["seed"] = effective_seed
        if max_tokens is not None:
            options["num_predict"] = max_tokens

        try:
            response = self._client.generate(
                model=self._model,
                prompt=prompt,
                options=options,
            )
        except Exception as exc:
            raise LLMGenerationError(
                f"Ollama ({self._model}) no pudo generar respuesta: {exc}"
            ) from exc

        raw = response.response
        if raw is None:
            raise LLMGenerationError(
                f"Ollama ({self._model}) devolvió una respuesta None."
            )
        text: str = raw.strip()
        if not text:
            raise LLMGenerationError(
                f"Ollama ({self._model}) devolvió una respuesta vacía."
            )

        logger.debug("generate: model=%r chars_out=%d", self._model, len(text))
        return text

    @property
    def model_name(self) -> str:
        """Identificador del modelo activo (ej. 'llama3.1:8b')."""
        return self._model
