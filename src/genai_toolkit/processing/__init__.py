"""Capa de procesamiento de texto: chunking y sanitización."""

from genai_toolkit.processing.base import TextChunker
from genai_toolkit.processing.sliding_window_chunker import SlidingWindowChunker

__all__ = [
    "SlidingWindowChunker",
    "TextChunker",
]
