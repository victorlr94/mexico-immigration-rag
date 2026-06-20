"""Pipeline de ingesta: orquesta loader → chunker → embedder → vectorstore."""

from genai_toolkit.pipeline.ingest import IngestionPipeline, IngestResult

__all__ = ["IngestResult", "IngestionPipeline"]
