"""Unit tests de la Configuration Layer.

Cubre: defaults de clase, carga desde configs/default.yaml, validación
cruzada (chunk_overlap < chunk_size), y la jerarquía de precedencia
(env real > .env > kwargs init > YAML > defaults de clase).
"""

import os

import pytest

from genai_toolkit.config.settings import Settings


def test_defaults_sin_yaml_ni_env(tmp_path, monkeypatch):
    """Sin YAML disponible, Settings debe construirse con los defaults
    declarados en la clase (no debe fallar ni quedar en None)."""
    monkeypatch.chdir(tmp_path)  # cwd sin configs/default.yaml ni .env
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.llm_model == "llama3.1:8b"
    assert settings.chunk_size == 500
    assert settings.chunk_overlap == 80
    assert settings.retrieval_min_score == 0.70


def test_carga_valores_reales_desde_default_yaml():
    """Contra el configs/default.yaml real del proyecto: los valores deben
    coincidir con lo declarado ahí, no con los defaults de clase, para
    confirmar que el mapeo _YAML_TO_FIELD está bien direccionado."""
    settings = Settings()
    assert settings.llm_model == "llama3.1:8b"
    assert settings.embedding_model == "intfloat/multilingual-e5-small"
    assert settings.chroma_collection == "immigration_docs"
    assert settings.chunk_size == 500
    assert settings.chunk_overlap == 80
    assert settings.retrieval_top_k == 4
    assert settings.retrieval_min_score == 0.70
    assert settings.eval_faithfulness_min == 0.80
    assert settings.eval_refusal_quality_min == 0.90
    assert settings.observability_sink == "jsonl"
    assert settings.redact_pii is True


def test_kwargs_init_tienen_prioridad_sobre_yaml():
    """Un valor pasado explícitamente al constructor debe ganarle al YAML
    (ver jerarquía documentada en settings.py)."""
    settings = Settings(chunk_size=999)
    assert settings.chunk_size == 999


def test_env_real_tiene_prioridad_sobre_kwargs_init(monkeypatch):
    """Una variable de entorno real debe ganarle incluso a un kwarg
    explícito del constructor (máxima prioridad en la jerarquía)."""
    monkeypatch.setenv("CHUNK_SIZE", "777")
    settings = Settings(chunk_size=999)
    assert settings.chunk_size == 777


def test_chunk_overlap_mayor_o_igual_a_chunk_size_falla():
    """La validación cruzada debe rechazar overlap >= chunk_size."""
    with pytest.raises(ValueError, match="chunk_overlap debe ser menor"):
        Settings(chunk_size=100, chunk_overlap=100)


def test_chunk_overlap_valido_no_falla():
    settings = Settings(chunk_size=500, chunk_overlap=80)
    assert settings.chunk_overlap < settings.chunk_size
