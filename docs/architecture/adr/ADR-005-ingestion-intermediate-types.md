# ADR-005: Tipos intermedios en la capa de ingesta (RawPage / LoadedDocument)

## Estado

Aceptado · Fase 1

## Contexto

CONTEXT.md dejaba abierta la decisión: el loader debía producir `Chunk` /
`ChunkMetadata` (los tipos ya definidos en `retrieval/types.py`) o un tipo
intermedio "documento crudo" antes del chunking. Ambas opciones cumplen con
ADR-001 (capas desacopladas); la diferencia está en dónde vive la
responsabilidad de asignar los campos que dependen del chunking.

Los campos de `Chunk`/`ChunkMetadata` que el loader **no puede conocer**:

| Campo | Razón |
|---|---|
| `Chunk.id` | Requiere hash de `(source_document, chunk_index)` — el índice lo asigna el chunker |
| `ChunkMetadata.chunk_index` | Ordinal dentro del documento; solo existe tras dividir |
| `ChunkMetadata.section` | Encabezado de sección más cercano, inferido durante el chunking |
| `Chunk.text` | El loader extrae texto de página; el chunker lo divide en fragmentos |

Forzar al loader a producir `Chunk` requeriría que él también troceara el
texto (mezcla de dos responsabilidades) o que el chunker recibiera un `Chunk`
a medio llenar con valores placeholder (viola el invariante `frozen=True` y
confunde al lector sobre qué está completo).

## Decisión

Se introducen dos tipos propios de la capa de ingesta en
`src/genai_toolkit/ingestion/types.py`:

- **`RawPage`** — una página extraída tal cual: `text`, `page_number`
  (1-indexed, para coincidir con `ChunkMetadata.page`), `source_document`.
- **`LoadedDocument`** — el documento completo: `source`, `pages: list[RawPage]`,
  `total_pages`.

El loader devuelve un `LoadedDocument`. El chunker (Fase 1, siguiente pieza)
recibe ese `LoadedDocument` y produce `list[Chunk]`, asignando en ese momento
`chunk_index`, `section` y `id`.

## Alternativa considerada: loader produce Chunk directamente

El loader haría también el chunking inicial (una página = un chunk). Descartada:

- Funde dos responsabilidades en una clase (extracción + división), dificultando
  la sustitución independiente de cada estrategia de chunking.
- `frozen=True` en `Chunk` no permite rellenar campos a posteriori; el único
  workaround habría sido introducir un `Chunk` "mutable de construcción" aparte,
  que es exactamente el problema que `RawPage` resuelve de forma más limpia.
- Los tests del loader habrían tenido que conocer la lógica de chunking, acoplando
  ambas suites.

## Consecuencias

- (+) Cada capa tiene una sola responsabilidad; el chunker puede sustituirse
  sin tocar el loader (p. ej. cambiar tamaño de chunk, estrategia de solapamiento
  o detección de secciones).
- (+) `RawPage` es la unidad natural de inspección en tests del loader: verificar
  que se extrae texto página a página es independiente de cómo luego se divide.
- (+) `LoadedDocument.total_pages` permite detectar que max_pages truncó la
  carga (si en el futuro se quiere truncar en lugar de rechazar).
- (−) Un nivel de indirección más: el consumidor (chunker) recibe
  `LoadedDocument`, no `Chunk` directamente. Aceptable dado el desacoplamiento
  que ofrece.
