"""Implementación concreta de VectorStore con ChromaDB.

ChromaDB actúa como almacén local persistente (sin servidor). La colección
usa espacio coseno; ChromaDB devuelve distancias en [0, 2], que se convierten
a score en [0, 1] con la fórmula min(1, max(0, 1 - distancia)).

Metadata de ChromaDB no acepta valores None: page=None se serializa como -1,
section=None como "" — los mismos centinelas se revierten al reconstruir Chunk.

Inicialización:
- persist_directory dado (incluido tmp_path en tests): PersistentClient.
- persist_directory no dado: usa settings.chroma_persist_dir (./chroma_db).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.types import IncludeEnum

from genai_toolkit.config.settings import Settings
from genai_toolkit.retrieval.types import Chunk, ChunkMetadata, ScoredChunk
from genai_toolkit.vectorstore.base import VectorStoreError

logger = logging.getLogger(__name__)

_HNSW_SPACE = "cosine"
_NO_PAGE: int = -1
_NO_SECTION: str = ""


class ChromaVectorStore:
    """VectorStore respaldado por ChromaDB con similitud coseno.

    Usa upsert en add() para que re-ingestar el mismo documento no duplique
    chunks — basta con borrar los IDs anteriores y volver a insertar.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        persist_directory: Path | str | None = None,
        collection_name: str | None = None,
    ) -> None:
        _settings = settings or Settings()
        _dir = (
            persist_directory
            if persist_directory is not None
            else _settings.chroma_persist_dir
        )
        _name = collection_name or _settings.chroma_collection

        client = chromadb.PersistentClient(path=str(_dir))
        self._collection: chromadb.Collection = client.get_or_create_collection(
            name=_name,
            metadata={"hnsw:space": _HNSW_SPACE},
        )
        logger.info(
            "ChromaVectorStore listo: colección=%r, persist=%r", _name, str(_dir)
        )

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """Inserta o actualiza chunks junto con sus vectores (upsert por id)."""
        if len(chunks) != len(embeddings):
            raise VectorStoreError(
                f"chunks ({len(chunks)}) y embeddings ({len(embeddings)}) "
                "deben tener la misma longitud."
            )
        if not chunks:
            return
        try:
            self._collection.upsert(
                ids=[c.id for c in chunks],
                documents=[c.text for c in chunks],
                embeddings=embeddings,  # type: ignore[arg-type]
                metadatas=[_serialize_metadata(c.metadata) for c in chunks],
            )
        except Exception as exc:
            raise VectorStoreError(f"Error al insertar en ChromaDB: {exc}") from exc
        logger.debug("Upserted %d chunks.", len(chunks))

    def search(self, query_embedding: list[float], top_k: int) -> list[ScoredChunk]:
        """Devuelve hasta top_k chunks ordenados de mayor a menor score."""
        if self._collection.count() == 0:
            return []
        n = min(top_k, self._collection.count())
        try:
            _include: list[IncludeEnum] = [
                IncludeEnum.documents,
                IncludeEnum.metadatas,
                IncludeEnum.distances,
            ]
            raw: Any = self._collection.query(
                query_embeddings=[query_embedding],  # type: ignore[arg-type]
                n_results=n,
                include=_include,
            )
        except Exception as exc:
            raise VectorStoreError(f"Error al consultar ChromaDB: {exc}") from exc

        ids: list[str] = (raw.get("ids") or [[]])[0]
        documents: list[str | None] = (raw.get("documents") or [[]])[0]
        metadatas: list[dict[str, Any]] = (raw.get("metadatas") or [[]])[0]
        distances: list[float] = (raw.get("distances") or [[]])[0]

        scored: list[ScoredChunk] = []
        for chunk_id, text, meta, dist in zip(
            ids, documents, metadatas, distances, strict=True
        ):
            score = min(1.0, max(0.0, 1.0 - float(dist)))
            chunk = Chunk(
                id=chunk_id,
                text=text or "",
                metadata=_deserialize_metadata(meta),
            )
            scored.append(ScoredChunk(chunk=chunk, score=score))
        return scored

    def delete(self, chunk_ids: list[str]) -> None:
        """Elimina chunks por id. IDs inexistentes se ignoran."""
        if not chunk_ids:
            return
        try:
            self._collection.delete(ids=chunk_ids)
        except Exception as exc:
            raise VectorStoreError(f"Error al eliminar de ChromaDB: {exc}") from exc

    def count(self) -> int:
        """Número total de chunks almacenados."""
        return self._collection.count()


def _serialize_metadata(meta: ChunkMetadata) -> dict[str, Any]:
    return {
        "source_document": meta.source_document,
        "chunk_index": meta.chunk_index,
        "page": meta.page if meta.page is not None else _NO_PAGE,
        "section": meta.section if meta.section is not None else _NO_SECTION,
    }


def _deserialize_metadata(raw: dict[str, Any]) -> ChunkMetadata:
    raw_page = raw.get("page", _NO_PAGE)
    page = None if raw_page == _NO_PAGE else int(raw_page)
    raw_section = raw.get("section", _NO_SECTION)
    section = None if raw_section == _NO_SECTION else str(raw_section)
    return ChunkMetadata(
        source_document=str(raw.get("source_document", "")),
        page=page,
        section=section,
        chunk_index=int(raw.get("chunk_index", 0)),
    )
