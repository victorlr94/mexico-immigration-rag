#!/usr/bin/env python
"""CLI de ingesta: indexa uno o varios PDFs en ChromaDB.

Uso:
    python scripts/ingest.py ruta/documento.pdf [otro.pdf ...]

El script carga cada PDF, lo parte en chunks, calcula embeddings y los
almacena en ChromaDB usando la configuración de configs/default.yaml y
las variables de entorno (Settings con precedencia estándar del proyecto).

Errores por archivo se reportan en stderr y el script sale con código 1
si al menos un archivo falló — los demás archivos del lote se procesan
igualmente (no se aborta en el primer error).

Re-ingesta: el ChromaVectorStore usa upsert por chunk_id (hash de
source_document:chunk_index). Si el documento no cambia, re-indexar es
idempotente. Si el documento cambia de contenido o longitud, el lote
anterior puede dejar chunks huérfanos — borrar manualmente el directorio
chroma_db y re-ingestar para limpiar (mejora planificada para Fase 2).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from genai_toolkit.config.settings import Settings
from genai_toolkit.embeddings.sentence_transformer_provider import (
    SentenceTransformerProvider,
)
from genai_toolkit.ingestion.pdf_loader import PdfLoader
from genai_toolkit.pipeline.ingest import IngestionPipeline
from genai_toolkit.processing.sliding_window_chunker import SlidingWindowChunker
from genai_toolkit.vectorstore.chroma import ChromaVectorStore

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def _build_pipeline(settings: Settings) -> IngestionPipeline:
    return IngestionPipeline(
        loader=PdfLoader(settings),
        chunker=SlidingWindowChunker(settings),
        embedder=SentenceTransformerProvider(settings),
        store=ChromaVectorStore(settings),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Indexa PDFs en ChromaDB para el asistente migratorio RAG."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        metavar="PDF",
        help="Uno o varios archivos PDF a indexar.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Activa logging INFO en todos los módulos.",
    )
    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)

    settings = Settings()
    pipeline = _build_pipeline(settings)

    total = len(args.paths)
    errors: list[tuple[Path, Exception]] = []

    for path in args.paths:
        try:
            result = pipeline.run(path)
            print(
                f"[OK] {result.source}: "
                f"{result.chunks_indexed} chunks de {result.pages_loaded} paginas"
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] {path}: {exc}", file=sys.stderr)
            logger.exception("Fallo al ingestar %s", path)
            errors.append((path, exc))

    print(f"\n{total - len(errors)}/{total} archivos indexados correctamente.")
    if errors:
        print(f"{len(errors)} archivo(s) con error — ver stderr.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
