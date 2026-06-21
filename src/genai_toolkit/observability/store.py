"""ObservabilityStore: sink JSONL para registros estructurados de interacción RAG.

Implementa el primer nivel de la progresión de observabilidad definida en
docs/engineering_skills/06_observability.md: JSONL desde el día 1, con
interfaz que permite migrar a SQLite sin cambiar el código llamador.

Un registro por línea; compatible con jq, pandas, DuckDB y cualquier
herramienta que acepte JSONL.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from genai_toolkit.config.settings import Settings


@dataclass
class SourceReference:
    """Referencia de procedencia de un chunk en el log de interacción."""

    doc: str
    page: int | None = None


@dataclass
class InteractionLog:
    """Registro estructurado de una interacción completa con el pipeline RAG.

    Sigue el schema de 06_observability.md. Campos obligatorios siempre
    presentes; opcionales en None o colección vacía en flujo normal.
    """

    timestamp: str
    question_hash: str
    question_type: str
    model: str
    embedding_model: str
    retrieved_context_ids: list[str]
    source_documents: list[SourceReference]
    retrieval_scores: list[float]
    has_sufficient_context: bool
    response_time_ms: float
    stage_latencies: dict[str, float] = field(default_factory=dict)
    answer: str | None = None
    error: str | None = None
    question_text: str | None = None


class ObservabilityStore:
    """Persiste InteractionLog en un archivo JSONL local (append-only)."""

    def __init__(self, settings: Settings | None = None) -> None:
        _s = settings or Settings()
        self._path = Path(_s.observability_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def log(self, record: InteractionLog) -> None:
        """Añade un registro al archivo JSONL. Thread-safe en CPython (GIL + write)."""
        entry = _to_dict(record)
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        """Lee todos los registros del archivo. Para tests y analítica offline."""
        if not self._path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self._path.open(encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    records.append(json.loads(stripped))
        return records


def _to_dict(record: InteractionLog) -> dict[str, Any]:
    """Serializa InteractionLog a dict JSON-compatible."""
    return asdict(record)
