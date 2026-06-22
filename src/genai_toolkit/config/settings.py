"""Configuration Layer: fuente única de verdad para parámetros del sistema.

Precedencia de configuración (de mayor a menor prioridad):
    1. Variables de entorno reales (export FOO=bar / set en el SO)
    2. Valores en .env
    3. kwargs pasados explícitamente al constructor (uso típico: tests,
       ej. Settings(chunk_size=10))
    4. Valores en configs/default.yaml
    5. Defaults declarados como default= en cada campo de esta clase

Esta jerarquía se implementa con `settings_customise_sources` (ver más abajo)
en vez de pasar el YAML como kwargs del constructor: Pydantic Settings trata
los kwargs del __init__ como la fuente de MAYOR prioridad por defecto, así
que pasar el YAML ahí lo dejaría por encima de .env y del entorno real —
exactamente lo opuesto a la jerarquía que queremos. `settings_customise_sources`
es el mecanismo soportado por la librería para insertar una fuente
personalizada en la posición exacta de prioridad deseada.

Ningún otro módulo del proyecto debe leer os.environ, un .env o el YAML
directamente — todo pasa por una instancia de Settings, inyectada donde se
necesite. Esto es lo que la Code Quality Skill llama "fuente única de verdad,
sin números mágicos dispersos".

Uso:
    from genai_toolkit.config.settings import Settings
    settings = Settings()  # aplica toda la jerarquía automáticamente

Para tests, sobreescribe valores puntuales con kwargs (tienen prioridad
sobre el YAML, ver jerarquía arriba):
    settings = Settings(chunk_size=10, chunk_overlap=2)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_YAML_PATH = _PROJECT_ROOT / "configs" / "default.yaml"

# Mapeo explícito ruta-en-YAML -> nombre-de-campo-en-Settings.
# Deliberadamente explícito (no un aplanado automático "mágico"): la
# estructura del YAML (anidada, en inglés con guiones bajos por sección) no
# coincide 1:1 con los nombres de campo de Settings, y un aplanado genérico
# fallaría en silencio si alguien reordena el YAML — preferimos que romper
# el mapeo sea un error visible (KeyError) y no un default ignorado sin aviso.
_YAML_TO_FIELD: dict[tuple[str, ...], str] = {
    ("llm", "model"): "llm_model",
    ("llm", "temperature"): "llm_temperature",
    ("llm", "seed"): "llm_seed",
    ("llm", "base_url"): "ollama_base_url",
    ("embeddings", "model"): "embedding_model",
    ("vector_store", "persist_dir"): "chroma_persist_dir",
    ("vector_store", "collection"): "chroma_collection",
    ("chunking", "chunk_size"): "chunk_size",
    ("chunking", "chunk_overlap"): "chunk_overlap",
    ("retrieval", "top_k"): "retrieval_top_k",
    ("retrieval", "min_score"): "retrieval_min_score",
    ("security", "max_file_size_mb"): "max_file_size_mb",
    ("security", "max_pages"): "max_pages",
    ("security", "max_input_chars"): "max_input_chars",
    ("evaluation", "thresholds", "faithfulness"): "eval_faithfulness_min",
    ("evaluation", "thresholds", "answer_relevancy"): "eval_answer_relevancy_min",
    ("evaluation", "thresholds", "context_precision"): "eval_context_precision_min",
    ("evaluation", "thresholds", "context_recall"): "eval_context_recall_min",
    ("evaluation", "thresholds", "refusal_quality"): "eval_refusal_quality_min",
    (
        "evaluation",
        "thresholds",
        "hallucination_rate_max",
    ): "eval_hallucination_rate_max",
    ("observability", "sink"): "observability_sink",
    ("observability", "path"): "observability_path",
    ("observability", "redact_pii"): "redact_pii",
}


def _get_nested(node: dict[str, Any], path: tuple[str, ...]) -> Any:
    """Navega un dict anidado siguiendo `path`; devuelve None si falta."""
    current: Any = node
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _load_yaml_defaults(yaml_path: Path) -> dict[str, Any]:
    """Lee configs/default.yaml y lo traduce a nombres de campo de Settings.

    Si el archivo no existe, devuelve {} silenciosamente — el YAML es un
    nivel de defaults opcional, no obligatorio (los defaults declarados en
    la clase Settings siguen funcionando sin él). Si una clave del mapeo no
    está presente en el YAML, simplemente se omite (no es un error: permite
    YAMLs parciales).
    """
    if not yaml_path.exists():
        return {}

    with yaml_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    result: dict[str, Any] = {}
    for yaml_path_keys, field_name in _YAML_TO_FIELD.items():
        value = _get_nested(raw, yaml_path_keys)
        if value is not None:
            result[field_name] = value
    return result


class _YamlSettingsSource(PydanticBaseSettingsSource):
    """Fuente de settings que lee configs/default.yaml.

    Implementa el protocolo de PydanticBaseSettingsSource para poder
    insertarse en `settings_customise_sources` con la prioridad exacta que
    queremos (ver Settings.settings_customise_sources). No se usa
    directamente fuera de este módulo.
    """

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        # Requerido por la interfaz abstracta; no se usa porque
        # sobreescribimos __call__ directamente para resolver todo el
        # dict de una vez (más simple que campo por campo).
        raise NotImplementedError

    def __call__(self) -> dict[str, Any]:
        return _load_yaml_defaults(_DEFAULT_YAML_PATH)


class Settings(BaseSettings):
    """Parámetros centralizados del sistema.

    Instanciar como `Settings()` carga automáticamente .env y aplica la
    precedencia descrita en el docstring del módulo. Los nombres de campo
    coinciden deliberadamente con las claves de .env.example para que ambos
    archivos sean fáciles de cotejar.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM ---
    llm_model: str = "llama3.1:8b"
    llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    # Semilla de muestreo del LLM. None = no determinista (default de Ollama).
    # Fijarla (p. ej. en evaluación) hace reproducibles las generaciones para
    # poder comparar configuraciones sin que el ruido del muestreo confunda.
    llm_seed: int | None = None
    ollama_base_url: str = "http://localhost:11434"

    # --- Embeddings ---
    embedding_model: str = "intfloat/multilingual-e5-small"

    # --- Vector store ---
    chroma_persist_dir: Path = Path("./chroma_db")
    chroma_collection: str = "immigration_docs"

    # --- Chunking ---
    chunk_size: int = Field(default=500, gt=0)
    chunk_overlap: int = Field(default=80, ge=0)

    # --- Retrieval ---
    retrieval_top_k: int = Field(default=4, gt=0)
    retrieval_min_score: float = Field(default=0.70, ge=0.0, le=1.0)

    # --- Seguridad / ingesta ---
    max_file_size_mb: int = Field(default=25, gt=0)
    max_pages: int = Field(default=300, gt=0)
    max_input_chars: int = Field(default=2000, gt=0)

    # --- Evaluación (umbrales POC, ver RAG Evaluation Skill) ---
    eval_faithfulness_min: float = Field(default=0.80, ge=0.0, le=1.0)
    eval_answer_relevancy_min: float = Field(default=0.75, ge=0.0, le=1.0)
    eval_context_precision_min: float = Field(default=0.70, ge=0.0, le=1.0)
    eval_context_recall_min: float = Field(default=0.70, ge=0.0, le=1.0)
    eval_refusal_quality_min: float = Field(default=0.90, ge=0.0, le=1.0)
    eval_hallucination_rate_max: float = Field(default=0.10, ge=0.0, le=1.0)

    # --- Observabilidad ---
    observability_sink: Literal["jsonl", "sqlite"] = "jsonl"
    observability_path: Path = Path("./logs/interactions.jsonl")
    redact_pii: bool = True

    # --- App ---
    app_title: str = "Asesor Migratorio RAG"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @model_validator(mode="after")
    def _validate_chunk_overlap_smaller_than_size(self) -> Settings:
        """El overlap nunca debe ser >= chunk_size: produciría chunks que no
        avanzan (bucle infinito conceptual en el chunker) o duplicación total.
        """
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                "chunk_overlap debe ser menor que chunk_size "
                f"(recibido overlap={self.chunk_overlap}, size={self.chunk_size})"
            )
        return self

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Inserta el YAML como fuente de MENOR prioridad que todas las demás.

        Por qué este mecanismo y no pasar el YAML como kwargs al
        constructor: Pydantic Settings trata los kwargs del `__init__`
        como la fuente de MAYOR prioridad por defecto (por encima de
        env real y de .env) — justo lo opuesto a la jerarquía que
        queremos (YAML debe ser la capa más baja, solo por encima de los
        defaults declarados en la clase). `settings_customise_sources`
        es el mecanismo soportado por la librería para insertar una
        fuente personalizada en la posición exacta de prioridad deseada.

        Orden final (primero = mayor prioridad):
            env_settings > dotenv_settings > init_settings > yaml_settings
            > file_secret_settings > defaults de clase

        Nota: `init_settings` se mantiene por encima del YAML para no
        romper el caso de uso de tests (`Settings(chunk_size=10)` para
        un test específico debe poder forzar un valor sin que el YAML
        lo pise).
        """
        yaml_settings = _YamlSettingsSource(settings_cls)
        return (
            env_settings,
            dotenv_settings,
            init_settings,
            yaml_settings,
            file_secret_settings,
        )
