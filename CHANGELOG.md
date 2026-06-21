# Changelog

Todos los cambios notables de este proyecto se documentan aquí.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es/) y el
proyecto se adhiere a [Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

---

## [0.2.0] - 2026-06-20

Segunda release de portfolio: sistema RAG completamente interactivo —
observable, con UI funcional y logging estructurado de todas las interacciones.

### Added — Fase 2: UI Streamlit + Observability Layer

- `ObservabilityStore`: sink JSONL append-only, un registro por interacción;
  `read_all()` para analítica offline (jq, pandas, DuckDB)
- `RAGInteractionLogger`: construye `InteractionLog` desde artefactos del
  pipeline; aplica redacción de PII antes de persistir cuando `redact_pii=True`
- `redact_pii()`: patrones regex para CURP, RFC, email, teléfono (+52 compacto
  y separado) y pasaporte mexicano
- `RAGService` (`src/application/`): orquesta retriever → prompt → LLM → logger;
  expone `ask(question)` limpio para la UI; tres flujos: `in_scope`, `refused`,
  `error`; logger falla silenciosamente sin interrumpir la respuesta
- `_extract_sources()`: deduplica `(doc, page)` preservando orden de score
- `RAGResponse` + `SourceCitation`: tipos inmutables para el contrato UI↔service
- `app/streamlit_app.py`: interfaz de consulta con badge de confianza
  (in_scope / refused), panel de fuentes expandible con doc + página, manejo
  diferenciado de errores, sidebar con disclaimer legal y `@st.cache_resource`
  para no recargar el modelo de embeddings en cada interacción

### Security

- `question_hash` = SHA-256[:16] — trazabilidad sin almacenar texto crudo
- Pregunta loggeada en forma redactada (no omitida): conserva utilidad
  analítica sin exposición de PII
- Logging de aplicación (`logging` module) estrictamente separado del logging
  de interacciones (JSONL) — no se mezclan

### Stats

- 221 tests unitarios; 97.85% de cobertura
- 3 PRs de feature integrados a develop (#12, #13, #14)

---

## [0.1.0] - 2026-06-20

Primera release de portfolio: MVP RAG local completo, sin APIs de pago ni
infraestructura en la nube. Cubre las Fases 0 y 1 del roadmap del proyecto.

### Added — Fase 0: Arquitectura y configuración

- Estructura de repositorio con layout `src/` (`genai_toolkit/` + `domain/` + `application/`)
- `Settings` (Pydantic) con jerarquía de precedencia explícita: env > `.env` > kwargs > YAML > defaults
- Interfaces del núcleo como `typing.Protocol` con `@runtime_checkable`: `EmbeddingProvider`, `VectorStore`, `LLMProvider`, `Retriever`, `PromptManager`, `DocumentLoader`, `TextChunker`
- Tipos compartidos: `Chunk`, `ChunkMetadata`, `ScoredChunk`, `RetrievalResult`, `RawPage`, `LoadedDocument`
- 5 ADRs en `docs/architecture/adr/` (separación de dominio, pypdf vs PyMuPDF, gate de seguridad, umbrales de cobertura, tipos intermedios de ingesta)
- 7 engineering skills en `docs/engineering_skills/` (version control, calidad de código, testing, seguridad, evaluación RAG, observabilidad, documentación)
- CI/CD: lint (Ruff), type check (mypy strict en `genai_toolkit.*`), test + coverage (pytest), gate de seguridad (pip-audit con allowlist)

### Added — Fase 1: MVP RAG local

- `PdfLoader`: ingesta de PDFs con validación de magic bytes `%PDF-`, límites de tamaño/páginas (Settings) y timeout de 60 s vía `ThreadPoolExecutor` (pypdf~=6.0)
- `SlidingWindowChunker`: chunking por ventana deslizante (chunk_size=500, overlap=80) con sanitización de caracteres de control e IDs estables por SHA-256
- `SentenceTransformerProvider`: embeddings multilingües con `intfloat/multilingual-e5-small`; prefijos de rol `passage:`/`query:` requeridos por la arquitectura e5; `normalize_embeddings=True` para similitud coseno
- `ChromaVectorStore`: almacén vectorial persistente local con ChromaDB (espacio coseno, semántica upsert para re-ingesta sin duplicados)
- `SimpleRetriever`: orquesta embedder + vectorstore, filtra candidatos por `min_score` (0.70) y decide `has_sufficient_context` en un único lugar
- `OllamaProvider`: generación local vía Ollama (`llama3.1:8b`), timeout 120 s, temperatura 0.1 por defecto (fidelidad sobre creatividad)
- `RagPromptManager`: renderizador de templates RAG agnóstico de dominio; templates de dominio en `src/domain/prompt_templates/` (ADR-001); refusal instruction incorporada
- `IngestionPipeline`: pipeline load → chunk → embed → store con resultado estructurado `IngestResult`
- `scripts/ingest.py`: CLI para indexar uno o varios PDFs con manejo de errores por archivo y código de salida apropiado

### Security

- Validación de magic bytes en `PdfLoader` (evita spoofing por extensión)
- Sanitización de caracteres de control en `SlidingWindowChunker` (mitiga prompt injection indirecto desde PDFs maliciosos)
- Delimitadores explícitos `<context>…</context>` en el template RAG (el contenido recuperado es tratado como dato, nunca como instrucción)
- Gate `pip-audit` con `security/accepted-vulnerabilities.txt` (próxima revisión: 2026-09-01)

### Changed

- Umbral de cobertura: 30% → 50% (ADR-004, cierre Fase 1)

### Stats

- 163 tests unitarios; 97% de cobertura total
- 10 PRs cerrados desde el scaffold inicial

---

*Para versiones anteriores al scaffold inicial, ver el historial de commits.*
