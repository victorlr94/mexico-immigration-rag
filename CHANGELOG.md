# Changelog

Todos los cambios notables de este proyecto se documentan aquí.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es/) y el
proyecto se adhiere a [Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

---

## [0.4.0] - 2026-06-21

Cuarta release de portfolio: MVP demostrable localmente — corpus oficial indexado,
evaluación RAG con métricas reales, UI pulida y README como vitrina.

### Added — MVP Vitrina + Evaluación RAG

- **Corpus de muestra** (`data/samples/`, PR #21): 4 PDFs públicos oficiales
  (Ley de Migración, Reglamento Ley de Nacionalidad, Lineamientos de visas
  25-jul-2025, Lineamientos de trámites). Total: 212 páginas, 1 704 chunks.
  Excepción `.gitignore` + `data/samples/README.md` con tabla de procedencia.
- **UI demo polish** (`app/streamlit_app.py`, PR #22): 4 preguntas sugeridas como
  botones; aviso accionable cuando el índice está vacío; panel de estado del sistema
  (n.º de fragmentos + estado de Ollama con 3 estados); `@st.cache_resource` para
  conteo del índice; `_ollama_status()` compatible con `ListResponse` del SDK.
- **Makefile** (PR #23): targets `install`, `pull-model`, `ingest`, `run`, `eval`,
  `test`, `test-all`, `lint`, `format`, `clean`, `demo` (instala + descarga modelo
  + indexa en un solo comando).
- **Evaluación RAG en dos capas** (PR #24, ver ADR-006):
  - `src/genai_toolkit/evaluation/` — evaluadores deterministas sin LLM:
    `refusal_quality`, `citation_accuracy`, `hallucination_rate`; 16 tests unitarios.
  - `evaluations/test_questions.jsonl` — 13 preguntas con `ground_truth`,
    `expected_source`, `category` (in_scope × 9, out_of_scope × 2, no_answer × 2).
    Fuentes verificadas empíricamente contra el corpus real.
  - `scripts/evaluate.py` — CLI completo: `--no-ragas`, `--update-baseline`,
    `--dry-run`; RAGAS con juez Ollama local en bloque lazy + `try/except`
    para degradación documentada.
  - `ADR-006`: evaluación en dos capas; RAGAS best-effort con juez local.
- **Calibración de evaluación** (PR #25): `top_k` 4→6 (el LLM encuentra respuesta
  en 3 preguntas que antes quedaban sin contexto); `_REFUSAL_MARKERS` ampliados con
  patrones reales del LLM; fix de encoding UTF-8 en terminal Windows (SIM105).
- **README como vitrina** (PR #26): diagrama Mermaid de arquitectura, quickstart
  funcional, tabla de corpus, métricas reales, mapa OWASP, tabla de ADRs, roadmap
  actualizado. Reemplaza el placeholder de Fase 0.
- **`evaluations/results/baseline.json`** — primera baseline versionada con métricas
  reales: `refusal_quality=0.923`, `hallucination_rate=0.000`,
  `citation_accuracy=1.000`, `answer_relevancy=0.901` (RAGAS).

### Changed

- `retrieval.top_k`: 4 → **6** (mejora cobertura de contexto sin impacto en latencia
  perceptible en entorno local)
- `README.md`: reescritura completa — de placeholder de Fase 0 a vitrina de portafolio

### Stats

- **276 tests** (unit + security); **97.96% de cobertura**
- 6 PRs de feature integrados a develop (#21–#26)
- Métricas de evaluación con corpus real de 1 704 chunks

---

## [0.3.0] - 2026-06-20

Tercera release de portfolio: suite de testing completa con enfoque en
seguridad — 260 tests, pre-commit hooks endurecidos y umbral de cobertura
en 70% (meta de ADR-004 alcanzada).

### Added — Fase 3: Testing Suite + Pre-commit

- `.pre-commit-config.yaml` actualizado a versiones actuales: Black 26.5.1,
  ruff-pre-commit v0.15.18, mirrors-mypy v2.1.0; scope de mypy ajustado a
  `^src/genai_toolkit/` (solo el núcleo reutilizable en modo estricto);
  hooks `check-toml`, `detect-private-key` añadidos
- **Suite de integración** (`tests/integration/`, 20 tests, `@pytest.mark.integration`):
  - `test_chroma_e2e.py` — ChromaVectorStore real: add, count, search, delete,
    upsert semántico, metadata roundtrip `page=None↔-1`
  - `test_retrieval_e2e.py` — SimpleRetriever + SentenceTransformerProvider real:
    dimensión 384, relevancia semántica, threshold, orden por score descendente
  - `test_ingestion_e2e.py` — IngestionPipeline: blank PDF → 0 chunks, LoadedDocument
    con texto → chunks indexados, compatibilidad de dimensiones embedder↔ChromaDB
  - Fixture `blank_pdf` (session-scoped): PDF mínimo válido generado por pypdf
  - CI actualizado: `pytest -m "not integration and not e2e"` en el job rápido
- **Suite de seguridad** (`tests/security/`, 39 tests, `@pytest.mark.security`):
  - `test_input_guards.py` — RAGService rechaza vacío, whitespace, oversized y
    payload masivo ANTES de llamar al retriever o LLM (LLM01, LLM04)
  - `test_document_guards.py` — PdfLoader rechaza ZIP/DOCX/HTML disfrazados
    de PDF, archivos sobredimensionados, PDFs con > max_pages, PDFs corruptos
  - `test_chunker_sanitization.py` — SlidingWindowChunker sanitiza chars de
    control (null bytes, 0x01-0x1f, DEL); template RAG contiene `<context>…</context>`
    que trata el corpus como dato, no instrucción (LLM01 indirecto)

### Changed

- Umbral de cobertura: 50% → **70%** (ADR-004, cierre Fase 3)
- ADR-004 actualizado con historial completo de incrementos (Fase 0→1→3)

### Stats

- 260 tests (unit + security); 97.85% de cobertura
- 4 PRs de feature integrados a develop (#16, #17, #18, #19)

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
