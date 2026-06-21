#!/usr/bin/env python
"""CLI de evaluación RAG: corre el dataset y reporta métricas contra umbrales.

Flujo (ver RAG Evaluation Skill, docs/engineering_skills/05_rag_evaluation.md):
    dataset → ejecutar RAG por pregunta → métricas → comparar con umbrales → pass/fail

Métricas en dos capas:
  - Propias (deterministas, sin LLM): refusal_quality, citation_accuracy,
    hallucination_rate. Siempre se calculan.
  - RAGAS (requieren LLM juez local, Ollama): faithfulness, answer_relevancy,
    context_precision, context_recall. Best-effort: si la integración local no
    está disponible, se omiten con un aviso y la evaluación continúa con las
    propias (ver ADR sobre degradación de RAGAS con juez local).

Uso:
    python scripts/evaluate.py                 # evaluación completa
    python scripts/evaluate.py --no-ragas      # solo métricas deterministas
    python scripts/evaluate.py --update-baseline
    python scripts/evaluate.py --dry-run       # valida el dataset sin LLM

Requiere: corpus indexado (scripts/ingest.py) y Ollama activo con el modelo
configurado para la evaluación completa.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from application.rag_service import RAGService
from domain.prompt_templates import TEMPLATES
from genai_toolkit.config.settings import Settings
from genai_toolkit.embeddings.sentence_transformer_provider import (
    SentenceTransformerProvider,
)
from genai_toolkit.evaluation import (
    CitationOutcome,
    RefusalOutcome,
    citation_accuracy,
    hallucination_rate,
    refusal_quality,
)
from genai_toolkit.llm.ollama import OllamaProvider
from genai_toolkit.prompts.rag_prompt_manager import RagPromptManager
from genai_toolkit.retrieval.simple_retriever import SimpleRetriever
from genai_toolkit.vectorstore.chroma import ChromaVectorStore

logging.basicConfig(
    level=logging.WARNING, format="%(levelname)s %(name)s — %(message)s"
)
logger = logging.getLogger(__name__)

DATASET_PATH = Path("evaluations/test_questions.jsonl")
RESULTS_DIR = Path("evaluations/results")
BASELINE_PATH = RESULTS_DIR / "baseline.json"

_REFUSAL_CATEGORIES = {"out_of_scope", "no_answer"}
_REFUSAL_MARKERS = (
    "no encontré información",
    "no encontre informacion",
    "no cuento con información",
    "no dispongo de información",
    "no puedo proporcionar asistencia",
    "lo siento, pero no puedo",
    "no tengo información sobre",
    "fuera del alcance",
)


@dataclass(frozen=True)
class MetricCheck:
    """Una métrica con su umbral y veredicto."""

    name: str
    value: float
    threshold: float
    higher_is_better: bool
    passed: bool


def _looks_like_refusal(answer: str) -> bool:
    low = answer.lower()
    return any(marker in low for marker in _REFUSAL_MARKERS)


def _did_refuse(question_type: str, answer: str) -> bool:
    """Un caso cuenta como rechazo si el retriever no tuvo contexto suficiente
    (question_type == 'refused') o si el LLM emitió la frase de rechazo."""
    return question_type == "refused" or _looks_like_refusal(answer)


def _load_dataset(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el dataset de evaluación: {path}")
    cases: list[dict[str, Any]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            cases.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Línea {i} del dataset no es JSON válido: {exc}") from exc
    return cases


def _build_service(settings: Settings) -> tuple[RAGService, SimpleRetriever]:
    embedder = SentenceTransformerProvider(settings)
    store = ChromaVectorStore(settings)
    retriever = SimpleRetriever(embedder, store, settings)
    llm = OllamaProvider(settings)
    prompt_manager = RagPromptManager(TEMPLATES)
    service = RAGService(retriever, llm, prompt_manager, settings=settings)
    return service, retriever


def _thresholds(settings: Settings, metrics: dict[str, float]) -> list[MetricCheck]:
    """Construye los veredictos comparando cada métrica con su umbral de Settings."""
    spec: list[tuple[str, float, bool]] = [
        ("refusal_quality", settings.eval_refusal_quality_min, True),
        ("hallucination_rate", settings.eval_hallucination_rate_max, False),
        ("faithfulness", settings.eval_faithfulness_min, True),
        ("answer_relevancy", settings.eval_answer_relevancy_min, True),
        ("context_precision", settings.eval_context_precision_min, True),
        ("context_recall", settings.eval_context_recall_min, True),
    ]
    checks: list[MetricCheck] = []
    for name, threshold, higher_is_better in spec:
        if name not in metrics:
            continue
        value = metrics[name]
        passed = value >= threshold if higher_is_better else value <= threshold
        checks.append(MetricCheck(name, value, threshold, higher_is_better, passed))
    # citation_accuracy no tiene umbral en Settings; se reporta sin gate.
    return checks


def _run_ragas(samples: list[dict[str, Any]], settings: Settings) -> dict[str, float]:
    """Calcula métricas RAGAS con juez/embeddings locales. Best-effort.

    Lanza una excepción si la integración local no está disponible; el llamador
    la captura y continúa solo con las métricas deterministas.
    """
    from datasets import Dataset
    from langchain_community.chat_models import ChatOllama
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from ragas import evaluate as ragas_evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )

    judge = LangchainLLMWrapper(
        ChatOllama(
            model=settings.llm_model,
            base_url=settings.ollama_base_url,
            temperature=0.0,
        )
    )
    embeddings = LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(model_name=settings.embedding_model)
    )

    dataset = Dataset.from_list(
        [
            {
                "question": s["question"],
                "answer": s["answer"],
                "contexts": s["contexts"],
                "ground_truth": s["ground_truth"],
            }
            for s in samples
        ]
    )
    result = ragas_evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=judge,
        embeddings=embeddings,
    )
    scores = result.to_pandas().mean(numeric_only=True).to_dict()
    return {str(k): float(v) for k, v in scores.items()}


def _print_report(
    metrics: dict[str, float], checks: list[MetricCheck], n_cases: int
) -> None:
    print("\n" + "=" * 60)
    print(f"  EVALUACIÓN RAG — {n_cases} preguntas")
    print("=" * 60)
    gated = {c.name for c in checks}
    for c in checks:
        symbol = "✓" if c.passed else "✗"
        op = "≥" if c.higher_is_better else "≤"
        print(
            f"  [{symbol}] {c.name:<20} {c.value:.3f}  (umbral {op} {c.threshold:.2f})"
        )
    for name, value in metrics.items():
        if name not in gated:
            print(f"  [·] {name:<20} {value:.3f}  (informativo)")
    print("=" * 60)


def _write_results(
    records: list[dict[str, Any]],
    metrics: dict[str, float],
    checks: list[MetricCheck],
    update_baseline: bool,
) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "n_cases": len(records),
        "metrics": metrics,
        "checks": [
            {
                "name": c.name,
                "value": c.value,
                "threshold": c.threshold,
                "passed": c.passed,
            }
            for c in checks
        ],
        "records": records,
    }
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = RESULTS_DIR / f"eval_{stamp}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if update_baseline:
        BASELINE_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return out


def main(argv: list[str] | None = None) -> int:
    # Windows consoles default to cp1252; force UTF-8 so the report symbols render.
    for _stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError):
            _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

    parser = argparse.ArgumentParser(description="Evaluación RAG del asistente.")
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument(
        "--no-ragas", action="store_true", help="Solo métricas deterministas."
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Guarda el resultado como baseline.json.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valida el dataset sin ejecutar el RAG (no requiere Ollama).",
    )
    args = parser.parse_args(argv)

    cases = _load_dataset(args.dataset)
    print(f"Dataset: {len(cases)} preguntas cargadas desde {args.dataset}")

    if args.dry_run:
        by_cat: dict[str, int] = {}
        for c in cases:
            by_cat[c["category"]] = by_cat.get(c["category"], 0) + 1
        print("Distribución por categoría:", by_cat)
        print("Dry-run OK: dataset bien formado.")
        return 0

    settings = Settings()
    service, retriever = _build_service(settings)

    refusal_outcomes: list[RefusalOutcome] = []
    citation_outcomes: list[CitationOutcome] = []
    ragas_samples: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []

    for case in cases:
        question = case["question"]
        category = case["category"]
        should_refuse = category in _REFUSAL_CATEGORIES

        retrieval = retriever.retrieve(question)
        contexts = [sc.chunk.text for sc in retrieval.chunks]
        response = service.ask(question)
        did_refuse = _did_refuse(response.question_type, response.answer)

        refusal_outcomes.append(RefusalOutcome(should_refuse, did_refuse))
        if category == "in_scope":
            cited = tuple(s.document for s in response.sources)
            citation_outcomes.append(
                CitationOutcome(case.get("expected_source", ""), cited)
            )
            if contexts:
                ragas_samples.append(
                    {
                        "question": question,
                        "answer": response.answer,
                        "contexts": contexts,
                        "ground_truth": case.get("ground_truth", ""),
                    }
                )

        records.append(
            {
                "question": question,
                "category": category,
                "should_refuse": should_refuse,
                "did_refuse": did_refuse,
                "answer": response.answer,
                "sources": [s.document for s in response.sources],
            }
        )
        print(f"  · {category:<13} refuse={did_refuse!s:<5} {question[:50]}")

    metrics: dict[str, float] = {
        "refusal_quality": refusal_quality(refusal_outcomes),
        "citation_accuracy": citation_accuracy(citation_outcomes),
        "hallucination_rate": hallucination_rate(refusal_outcomes),
    }

    if not args.no_ragas and ragas_samples:
        try:
            print("\nEjecutando RAGAS con juez local (puede tardar)…")
            metrics.update(_run_ragas(ragas_samples, settings))
        except Exception as exc:  # noqa: BLE001 — degradación documentada
            print(
                f"\n[AVISO] RAGAS no disponible con juez local ({exc}). "
                "Continuando solo con métricas deterministas.",
                file=sys.stderr,
            )

    checks = _thresholds(settings, metrics)
    _print_report(metrics, checks, len(cases))
    out = _write_results(records, metrics, checks, args.update_baseline)
    print(f"\nResultados escritos en: {out}")

    failed = [c.name for c in checks if not c.passed]
    if failed:
        print(f"\nUmbrales no alcanzados: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("\nTodos los umbrales con gate se alcanzaron.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
