"""Tipos de datos compartidos del núcleo de AI Engineering.

Estos tipos son el "idioma común" entre componentes: VectorStore los produce,
Retriever los consume y enriquece, PromptManager los consume para construir el
contexto. Vivir en un módulo aparte (en vez de dentro de cada Protocol) evita
imports circulares entre `vectorstore`, `retrieval` y `prompts`.

Inmutables (frozen=True) a propósito: una vez recuperado un chunk con su score,
ningún componente debería mutarlo en el camino — si algo necesita transformarlo,
debe crear una instancia nueva. Esto hace el flujo de datos trazable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ChunkMetadata:
    """Metadata de procedencia de un chunk, para trazabilidad y citación.

    Attributes:
        source_document: Nombre o identificador del documento de origen
            (ej. "guia_tramite_residencia.pdf").
        page: Número de página de origen (1-indexed), si aplica.
            None si el documento no tiene paginación (ej. un .txt).
        section: Título de sección o encabezado más cercano, si se pudo
            inferir durante el chunking. None si no aplica o no se detectó.
        chunk_index: Posición ordinal del chunk dentro del documento
            (0-indexed). Útil para depuración y para reconstruir el orden
            original si se necesita contexto adicional.
        extra: Espacio de extensión para metadata específica de dominio
            (ej. tipo de trámite, fecha de vigencia del documento) sin
            romper el contrato de esta clase. El núcleo reutilizable nunca
            lee de aquí; solo la capa de dominio puede depender de su
            contenido.
    """

    source_document: str
    page: int | None = None
    section: str | None = None
    chunk_index: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Chunk:
    """Un fragmento de texto listo para ser embebido o indexado.

    Es la unidad que produce la Text Processing Layer y que consume la
    Embeddings Layer / VectorStore. No lleva score todavía: el score solo
    existe después de una búsqueda (ver ScoredChunk).

    Attributes:
        id: Identificador único y estable del chunk (ej. hash de
            source_document + chunk_index). Se usa como clave en el
            VectorStore y para trazabilidad en logs de observabilidad.
        text: El texto del fragmento, ya limpio/normalizado.
        metadata: Procedencia del fragmento (ver ChunkMetadata).
    """

    id: str
    text: str
    metadata: ChunkMetadata


@dataclass(frozen=True)
class ScoredChunk:
    """Un chunk recuperado de una búsqueda, con su score de similitud.

    Attributes:
        chunk: El fragmento recuperado.
        score: Score de similitud, normalizado a [0.0, 1.0] donde 1.0 es
            coincidencia perfecta. Los providers concretos (Chroma, etc.)
            son responsables de normalizar a esta escala aunque su métrica
            nativa sea distinta (distancia coseno, L2, etc.) — el resto del
            sistema asume siempre "más alto es mejor".
    """

    chunk: Chunk
    score: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(
                f"score debe estar normalizado en [0.0, 1.0], recibido: {self.score}"
            )


@dataclass(frozen=True)
class RetrievalResult:
    """Resultado de una operación de retrieval sobre una query.

    Encapsula no solo los chunks recuperados, sino también si el resultado
    se considera "suficiente" para generar una respuesta — la decisión de
    refusal se basa en este campo, no en que el llamador reinterprete scores.

    Attributes:
        query: La consulta original (ya validada/saneada) que originó
            esta búsqueda.
        chunks: Chunks recuperados, ordenados de mayor a menor score.
            Lista vacía si no se encontró nada por encima del umbral.
        has_sufficient_context: True si al menos un chunk superó el
            min_score configurado. El Retriever decide esto, no el
            llamador, para que el criterio de "suficiente" viva en un
            solo lugar.
    """

    query: str
    chunks: list[ScoredChunk]
    has_sufficient_context: bool
