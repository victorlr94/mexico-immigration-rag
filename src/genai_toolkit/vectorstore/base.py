"""Contrato para almacenes vectoriales.

Permite sustituir ChromaDB por otro backend (Qdrant, FAISS+metadata propia,
pgvector) sin tocar el Retriever ni el pipeline de ingesta. La implementación
concreta (ChromaVectorStore) vive en `vectorstore/chroma.py`.

Decisión de diseño: el VectorStore recibe y devuelve `Chunk`/`ScoredChunk`
(tipos del dominio del toolkit), nunca vectores crudos directamente en su
interfaz pública. Quien calcula los vectores es el EmbeddingProvider, inyectado
en capas superiores (Retriever) — el VectorStore solo persiste y busca.
Algunas implementaciones podrían embeber internamente (ej. Chroma con su
función de embedding nativa), pero el contrato no lo exige.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from genai_toolkit.retrieval.types import Chunk, ScoredChunk


@runtime_checkable
class VectorStore(Protocol):
    """Persiste chunks con sus vectores y permite búsqueda por similitud."""

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """Inserta chunks junto con sus vectores ya calculados.

        Args:
            chunks: Chunks a persistir. Cada uno debe tener un `id` único
                y estable (ver Chunk.id) — reinsertar el mismo id debe
                actualizar (upsert), no duplicar.
            embeddings: Vectores correspondientes, en el mismo orden y
                misma longitud que `chunks`. El llamador (no el
                VectorStore) es responsable de haberlos calculado con un
                EmbeddingProvider compatible.

        Raises:
            VectorStoreError: Si `chunks` y `embeddings` no tienen la
                misma longitud, o si el backend falla al escribir.
        """
        ...

    def search(self, query_embedding: list[float], top_k: int) -> list[ScoredChunk]:
        """Busca los `top_k` chunks más similares a un vector de consulta.

        Args:
            query_embedding: Vector de la consulta, ya calculado por un
                EmbeddingProvider compatible con la dimensión de la
                colección.
            top_k: Número máximo de resultados a devolver. Implementaciones
                deben devolver menos si la colección tiene menos elementos
                que `top_k`, nunca rellenar con resultados inventados.

        Returns:
            Lista de ScoredChunk ordenada de mayor a menor score
            (score normalizado a [0.0, 1.0], ver ScoredChunk). Lista vacía
            si la colección está vacía.

        Raises:
            VectorStoreError: Si el backend falla al consultar, o si
                `query_embedding` no coincide con la dimensión esperada
                por la colección.
        """
        ...

    def delete(self, chunk_ids: list[str]) -> None:
        """Elimina chunks por id.

        Necesario para re-ingestar un documento sin duplicar sus chunks
        anteriores (borrar por `source_document` antes de re-indexar).

        Args:
            chunk_ids: IDs a eliminar. IDs inexistentes se ignoran
                silenciosamente (no es un error borrar lo que no existe).

        Raises:
            VectorStoreError: Si el backend falla al eliminar.
        """
        ...

    def count(self) -> int:
        """Número total de chunks actualmente almacenados.

        Útil para health checks y para que la app pueda mostrar
        "base de conocimiento vacía" en vez de fallar silenciosamente.
        """
        ...


class VectorStoreError(Exception):
    """Fallo en una operación del almacén vectorial."""
