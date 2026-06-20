"""Pipeline de ingesta: carga → chunking → embeddings → vectorstore.

Orquesta los cuatro componentes ya implementados en la capa genai_toolkit.
Esta clase es agnóstica de dominio y de formato de entrada — solo combina
las interfaces definidas por sus protocolos (DocumentLoader, TextChunker,
EmbeddingProvider, VectorStore).

Diseño deliberadamente simple para la POC: procesa un documento a la vez.
Para producción con muchos documentos, extender con concurrencia en este
módulo sin tocar el script CLI ni los componentes individuales.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from genai_toolkit.embeddings.base import EmbeddingProvider
from genai_toolkit.ingestion.base import DocumentLoader
from genai_toolkit.processing.base import TextChunker
from genai_toolkit.vectorstore.base import VectorStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestResult:
    """Resumen de una operación de ingesta completada.

    Attributes:
        source: Nombre del documento procesado.
        pages_loaded: Total de páginas leídas del documento.
        chunks_indexed: Número de chunks almacenados en el vector store.
            Puede ser 0 si todas las páginas tenían texto vacío.
    """

    source: str
    pages_loaded: int
    chunks_indexed: int


class IngestionPipeline:
    """Pipeline load → chunk → embed → store para un solo documento.

    Los cuatro proveedores se inyectan en el constructor para que el llamador
    controle su ciclo de vida (el modelo de embeddings es costoso de cargar).
    """

    def __init__(
        self,
        loader: DocumentLoader,
        chunker: TextChunker,
        embedder: EmbeddingProvider,
        store: VectorStore,
    ) -> None:
        self._loader = loader
        self._chunker = chunker
        self._embedder = embedder
        self._store = store

    def run(self, path: Path) -> IngestResult:
        """Indexa un documento completo en el vector store.

        Args:
            path: Ruta al archivo a procesar.

        Returns:
            IngestResult con el resumen de la operación.

        Raises:
            Cualquier excepción de los componentes subyacentes (FileTooLargeError,
            PdfParseError, EmbeddingError, VectorStoreError, etc.) se propaga
            sin envolver para que el llamador decida cómo manejarla.
        """
        logger.info("Iniciando ingesta: %s", path.name)

        document = self._loader.load(path)
        chunks = self._chunker.chunk(document)

        if not chunks:
            logger.warning("Documento sin chunks: %s — omitiendo indexado.", path.name)
            return IngestResult(
                source=document.source,
                pages_loaded=document.total_pages,
                chunks_indexed=0,
            )

        texts = [c.text for c in chunks]
        embeddings = self._embedder.embed_documents(texts)
        self._store.add(chunks, embeddings)

        logger.info(
            "Ingesta completa: %s — %d páginas, %d chunks indexados.",
            path.name,
            document.total_pages,
            len(chunks),
        )
        return IngestResult(
            source=document.source,
            pages_loaded=document.total_pages,
            chunks_indexed=len(chunks),
        )
