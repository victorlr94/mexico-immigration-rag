"""Unit tests para OllamaProvider.

El cliente de Ollama se mockea completamente: no se requiere un servidor
Ollama activo. Lo que se verifica es la lógica de orquestación del provider
(construcción de options, conversión de errores, validación de respuesta vacía)
sin depender de la red ni del modelo subyacente.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from genai_toolkit.config.settings import Settings
from genai_toolkit.llm.base import LLMGenerationError
from genai_toolkit.llm.ollama import OllamaProvider

_CLIENT_PATH = "genai_toolkit.llm.ollama.Client"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(text: str = "Respuesta generada.") -> MagicMock:
    resp = MagicMock()
    resp.response = text
    return resp


def _make_settings(
    model: str = "llama3.1:8b",
    base_url: str = "http://localhost:11434",
    temperature: float = 0.1,
    seed: int | None = None,
) -> Settings:
    return Settings(
        llm_model=model,
        ollama_base_url=base_url,
        llm_temperature=temperature,
        llm_seed=seed,
    )


@pytest.fixture()
def mock_client() -> MagicMock:
    client = MagicMock()
    client.generate.return_value = _make_response()
    return client


@pytest.fixture()
def provider(mock_client: MagicMock) -> OllamaProvider:
    with patch(_CLIENT_PATH, return_value=mock_client):
        return OllamaProvider(_make_settings())


# ---------------------------------------------------------------------------
# Construcción
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_model_name_from_settings(self, mock_client: MagicMock) -> None:
        with patch(_CLIENT_PATH, return_value=mock_client):
            p = OllamaProvider(_make_settings(model="mistral:7b"))
        assert p.model_name == "mistral:7b"

    def test_client_created_with_base_url(self) -> None:
        with patch(_CLIENT_PATH) as mock_cls:
            mock_cls.return_value = MagicMock()
            OllamaProvider(_make_settings(base_url="http://mi-ollama:11434"))
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["host"] == "http://mi-ollama:11434"

    def test_client_created_with_timeout(self) -> None:
        with patch(_CLIENT_PATH) as mock_cls:
            mock_cls.return_value = MagicMock()
            OllamaProvider(_make_settings(), timeout=30.0)
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["timeout"] == 30.0

    def test_uses_default_settings_when_none_passed(self) -> None:
        with patch(_CLIENT_PATH, return_value=MagicMock()):
            p = OllamaProvider()
        assert p.model_name == "llama3.1:8b"


# ---------------------------------------------------------------------------
# generate — retorno correcto
# ---------------------------------------------------------------------------


class TestGenerate:
    def test_returns_response_text(self, provider: OllamaProvider) -> None:
        provider._client.generate.return_value = _make_response("Texto de respuesta.")
        result = provider.generate("mi prompt")
        assert result == "Texto de respuesta."

    def test_strips_whitespace_from_response(self, provider: OllamaProvider) -> None:
        provider._client.generate.return_value = _make_response("  Texto  \n")
        result = provider.generate("prompt")
        assert result == "Texto"

    def test_passes_prompt_to_client(self, provider: OllamaProvider) -> None:
        provider.generate("prompt exacto de prueba")
        call_args = provider._client.generate.call_args
        assert call_args[1]["prompt"] == "prompt exacto de prueba"

    def test_passes_model_to_client(self, provider: OllamaProvider) -> None:
        provider.generate("prompt")
        call_args = provider._client.generate.call_args
        assert call_args[1]["model"] == "llama3.1:8b"

    def test_passes_temperature_in_options(self, provider: OllamaProvider) -> None:
        provider.generate("prompt", temperature=0.5)
        options = provider._client.generate.call_args[1]["options"]
        assert options["temperature"] == 0.5

    def test_default_temperature_is_low(self, provider: OllamaProvider) -> None:
        provider.generate("prompt")
        options = provider._client.generate.call_args[1]["options"]
        assert options["temperature"] == pytest.approx(0.1)

    def test_default_temperature_comes_from_settings(
        self, mock_client: MagicMock
    ) -> None:
        """Sin temperature explícita, usa la configurada en Settings (no un
        0.1 hardcodeado). Bloquea el bug de que el pipeline ignorara la
        temperatura configurada."""
        with patch(_CLIENT_PATH, return_value=mock_client):
            p = OllamaProvider(_make_settings(temperature=0.7))
        p.generate("prompt")
        options = p._client.generate.call_args[1]["options"]
        assert options["temperature"] == pytest.approx(0.7)

    def test_max_tokens_maps_to_num_predict(self, provider: OllamaProvider) -> None:
        provider.generate("prompt", max_tokens=256)
        options = provider._client.generate.call_args[1]["options"]
        assert options["num_predict"] == 256

    def test_num_predict_absent_when_max_tokens_is_none(
        self, provider: OllamaProvider
    ) -> None:
        provider.generate("prompt", max_tokens=None)
        options = provider._client.generate.call_args[1]["options"]
        assert "num_predict" not in options


# ---------------------------------------------------------------------------
# generate — seed (reproducibilidad)
# ---------------------------------------------------------------------------


class TestSeed:
    def test_seed_absent_when_unset(self, provider: OllamaProvider) -> None:
        """Sin seed configurada ni explícita, options no incluye 'seed'
        (comportamiento no determinista por defecto de Ollama)."""
        provider.generate("prompt")
        options = provider._client.generate.call_args[1]["options"]
        assert "seed" not in options

    def test_seed_from_settings_included_in_options(
        self, mock_client: MagicMock
    ) -> None:
        with patch(_CLIENT_PATH, return_value=mock_client):
            p = OllamaProvider(_make_settings(seed=42))
        p.generate("prompt")
        options = p._client.generate.call_args[1]["options"]
        assert options["seed"] == 42

    def test_explicit_seed_overrides_settings(self, mock_client: MagicMock) -> None:
        with patch(_CLIENT_PATH, return_value=mock_client):
            p = OllamaProvider(_make_settings(seed=42))
        p.generate("prompt", seed=123)
        options = p._client.generate.call_args[1]["options"]
        assert options["seed"] == 123


# ---------------------------------------------------------------------------
# generate — errores
# ---------------------------------------------------------------------------


class TestGenerateErrors:
    def test_none_response_raises_llm_generation_error(
        self, provider: OllamaProvider
    ) -> None:
        resp = MagicMock()
        resp.response = None
        provider._client.generate.return_value = resp
        with pytest.raises(LLMGenerationError, match="None"):
            provider.generate("prompt")

    def test_empty_response_raises_llm_generation_error(
        self, provider: OllamaProvider
    ) -> None:
        provider._client.generate.return_value = _make_response("")
        with pytest.raises(LLMGenerationError, match="vacía"):
            provider.generate("prompt")

    def test_whitespace_only_response_raises_llm_generation_error(
        self, provider: OllamaProvider
    ) -> None:
        provider._client.generate.return_value = _make_response("   \n\t  ")
        with pytest.raises(LLMGenerationError, match="vacía"):
            provider.generate("prompt")

    def test_connection_error_raises_llm_generation_error(
        self, provider: OllamaProvider
    ) -> None:
        provider._client.generate.side_effect = ConnectionError("refused")
        with pytest.raises(LLMGenerationError, match="no pudo generar"):
            provider.generate("prompt")

    def test_timeout_raises_llm_generation_error(
        self, provider: OllamaProvider
    ) -> None:
        provider._client.generate.side_effect = TimeoutError("timed out")
        with pytest.raises(LLMGenerationError, match="no pudo generar"):
            provider.generate("prompt")

    def test_generic_exception_raises_llm_generation_error(
        self, provider: OllamaProvider
    ) -> None:
        provider._client.generate.side_effect = RuntimeError("crash inesperado")
        with pytest.raises(LLMGenerationError):
            provider.generate("prompt")


# ---------------------------------------------------------------------------
# model_name property
# ---------------------------------------------------------------------------


class TestModelName:
    def test_returns_configured_model(self, mock_client: MagicMock) -> None:
        with patch(_CLIENT_PATH, return_value=mock_client):
            p = OllamaProvider(_make_settings(model="codellama:13b"))
        assert p.model_name == "codellama:13b"
