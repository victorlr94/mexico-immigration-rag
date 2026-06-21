# Contexto del proyecto — Mexico Immigration RAG Assistant (Asesor Migratorio RAG)

> Este documento sintetiza todo lo decidido y construido hasta el cierre de la
> **Fase 1 (v0.1.0)**, para que cualquier sesión nueva de Claude (Code o chat)
> recupere el contexto completo sin tener que re-derivarlo.
> Está pensado para pegarse como mensaje inicial o guardarse como `CONTEXT.md`
> en la raíz del repo y referenciarse al abrir una sesión nueva.
>
> **No duplica contenido que ya vive en archivos del repo** — los referencia
> por ruta. Si algo aquí contradice un archivo referenciado, el archivo del
> repo es la fuente de verdad (este documento puede quedar desactualizado;
> los ADRs y skills se actualizan junto con el código).

---

## 1. Qué es este proyecto y por qué existe

**Mexico Immigration RAG Assistant** es una POC de portfolio: un asistente RAG
que responde en lenguaje natural sobre documentación pública migratoria de
México, usando solo tecnologías open source y modelos locales (sin APIs de
pago).

**El objetivo real no es el RAG migratorio en sí** — es demostrar prácticas de
AI Engineering aplicadas para un puesto de Applied AI Engineer: arquitectura
desacoplada, seguridad (prompt injection, OWASP LLM Top 10), evaluación RAG
medible, observabilidad, CI/CD real, y un historial de Git que demuestre
proceso profesional.

**Decisión de diseño fundacional**: el código se divide en un **núcleo
reutilizable agnóstico de dominio** (`src/genai_toolkit/`) y una **capa fina
específica del dominio migratorio** (`src/domain/`, `src/application/`). La
intención explícita es que este sea el primero de una serie de proyectos
GenAI — cambiar de dominio (banca, telco, legal) debe significar reemplazar
solo la capa fina. Ver razonamiento completo en
**`docs/architecture/adr/ADR-001-toolkit-domain-separation.md`**.

## 2. Cómo trabajamos (el "contrato" de la colaboración)

Esto importa tanto como el código — es la lógica de proceso que se ha seguido
y se espera que continúe:

- **Crítico y honesto, no complaciente.** Si una idea es débil o riesgosa, se
  dice y se propone alternativa. No se valida una mala decisión por cortesía.
- **Causa raíz, no parches.** Repetidamente en este proyecto se rechazó la
  solución rápida que esconde el síntoma (ej. `pip-audit || true`, excluir
  archivos del cálculo de cobertura, `# type: ignore` genérico) en favor de
  entender y resolver la causa real, documentándola en un ADR.
- **Verificar, no asumir.** Cuando fue posible ejecutar/validar localmente
  (sintaxis, YAML, TOML, lógica aislada), se hizo antes de entregar código.
  Cuando no fue posible (sin pydantic/red en el entorno de construcción), se
  fue explícito sobre esa limitación y se dejaron tests reales para que el
  usuario verificara en su máquina — varias veces esto sí atrapó bugs reales.
- **Documentar decisiones no obvias como ADR**, con alternativas consideradas
  y por qué se descartaron — no solo "qué se hizo" sino "qué no se hizo y
  por qué". Cinco ADRs ya existen (ver sección 4).
- **Fases pequeñas, una rama por unidad de trabajo, PR aunque se trabaje
  solo**, con auto-revisión del diff antes de mergear. Ver
  **`docs/engineering_skills/01_version_control.md`**.
- **El roadmap por fases es la estructura de avance** — no se salta de fase
  ni se sobrearquitectura adelantándose a necesidades que no existen todavía.

## 3. Las 7 skills de ingeniería (ya escritas, en `docs/engineering_skills/`)

Son las convenciones activas del proyecto, agnósticas de dominio (reusables en
futuros proyectos). **Leerlas es obligatorio antes de implementar cualquier
componente nuevo** — cada una tiene checklist de cierre.

| Archivo | Cubre |
|---|---|
| `01_version_control.md` | Ramas (`main`/`develop`/`feature/*`), Conventional Commits, SemVer, qué no subir al repo |
| `02_code_quality.md` | Black, Ruff, mypy (estricto en `genai_toolkit/`), manejo de errores, logging, convenciones de nombres |
| `03_testing.md` | Pirámide de tests (unit/integration/e2e/security), mocks, cobertura mínima (90% en guards/chunking) |
| `04_security.md` | Modelo de amenazas RAG completo, mitigaciones, checklist OWASP Top 10 for LLM Apps |
| `05_rag_evaluation.md` | Métricas RAGAS + propias (refusal quality, citation accuracy, hallucination rate), umbrales POC vs robusto |
| `06_observability.md` | Qué loggear, JSONL→SQLite, qué NO loggear (PII) |
| `07_documentation.md` | Estructura de README, ADRs, disclaimer legal/migratorio |

## 4. Decisiones arquitectónicas ya tomadas (ADRs)

Todos en `docs/architecture/adr/`. **Leer antes de tocar código relacionado:**

- **ADR-001** — Separación `genai_toolkit/` (reutilizable) vs `domain/`
  (migratorio). Interfaces como `Protocol`/ABC para permitir sustituir LLM,
  vector store o embedder sin refactor.
- **ADR-002** — `pypdf` (no PyMuPDF) para extracción de PDF. PyMuPDF
  descartado por: (a) vulnerabilidad de path traversal/escritura arbitraria
  más severa que los DoS de pypdf, (b) licencia AGPL incompatible con MIT del
  proyecto. Pin actualizado a `~=6.0`.
- **ADR-003** — Gate de seguridad: `pip-audit` con lista explícita de
  excepciones en `security/accepted-vulnerabilities.txt` (cada entrada con
  justificación y fecha de revisión: **2026-09-01**). Un CVE nuevo no listado
  ahí sigue bloqueando CI.
- **ADR-004** — Umbral de cobertura progresivo: **30% en Fase 0 → 50% en
  Fase 1 (actual) → 70% en Fase 3**. Actualizar `pyproject.toml` al cerrar
  cada fase.
- **ADR-005** — Tipos intermedios `RawPage`/`LoadedDocument` en la capa de
  ingesta. El loader produce `LoadedDocument`; el chunker lo convierte en
  `list[Chunk]`. `chunk_index`, `section` e `id` solo existen después del
  chunking.

## 5. Estado técnico al cierre de Fase 1 (v0.1.0 — 2026-06-20)

### Rama: `main` (tag `v0.1.0`)

El MVP RAG local está 100% implementado y mergeado a `main`.

| Componente | Módulo | Tests |
|---|---|---|
| Settings (Pydantic) | `src/genai_toolkit/config/settings.py` | 7 tests |
| Interfaces / Protocols | `src/genai_toolkit/*/base.py` | — |
| Types compartidos | `src/genai_toolkit/retrieval/types.py` | — |
| `PdfLoader` | `src/genai_toolkit/ingestion/pdf_loader.py` | 10 tests |
| `SlidingWindowChunker` | `src/genai_toolkit/processing/sliding_window_chunker.py` | 33 tests |
| `SentenceTransformerProvider` | `src/genai_toolkit/embeddings/sentence_transformer_provider.py` | 16 tests |
| `ChromaVectorStore` | `src/genai_toolkit/vectorstore/chroma.py` | ~20 tests |
| `SimpleRetriever` | `src/genai_toolkit/retrieval/simple_retriever.py` | ~15 tests |
| `OllamaProvider` | `src/genai_toolkit/llm/ollama.py` | ~12 tests |
| `RagPromptManager` | `src/genai_toolkit/prompts/rag_prompt_manager.py` | ~15 tests |
| `IngestionPipeline` | `src/genai_toolkit/pipeline/ingest.py` | ~10 tests |
| `scripts/ingest.py` | CLI de ingesta end-to-end | tests de integración |

**Total al cierre de Fase 3**: 260 tests (unit + security); **97.85% de cobertura**; `fail_under = 70` (ADR-004).
Los 20 tests de integración (`@pytest.mark.integration`) se excluyen del CI rápido — requieren el modelo real de 117 MB.

### Componentes añadidos en Fase 2

| Componente | Módulo | Tests |
|---|---|---|
| `ObservabilityStore` | `src/genai_toolkit/observability/store.py` | 8 tests |
| `RAGInteractionLogger` + `redact_pii` | `src/genai_toolkit/observability/logger.py` | 19 tests |
| `RAGService` | `src/application/rag_service.py` | 31 tests |
| `RAGResponse` + `SourceCitation` | `src/application/types.py` | (via RAGService) |
| `app/streamlit_app.py` | UI Streamlit | presentación pura |

### Detalles de implementación que importan en Fase 3

- **PdfLoader**: magic bytes `%PDF-`, límites de `Settings` (`max_file_size_mb`, `max_pages`), timeout 60 s via `ThreadPoolExecutor`.
- **SlidingWindowChunker**: sanitiza `[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]`; IDs = SHA-256(`source:index`)[:16]; `section=None`.
- **SentenceTransformerProvider**: prefijos `"passage: "` / `"query: "` obligatorios; `.tolist() + cast` para tipos nativos.
- **ChromaVectorStore**: coseno, upsert; sentinel `page=None→-1`, `section=None→""`.
- **SimpleRetriever**: `min_score=0.70`, `top_k=4` (Settings); `has_sufficient_context` en un solo lugar.
- **OllamaProvider**: `llama3.1:8b`; timeout 120 s; temperatura 0.1; guarda explícito contra `response.response is None`.
- **RagPromptManager**: delimitadores `<context>…</context>` en el template, no en `_build_context_block`.
- **IngestionPipeline**: si `chunks == []`, retorna `IngestResult(chunks_indexed=0)` sin llamar al embedder.
- **ObservabilityStore**: JSONL append-only; `_to_dict` usa `asdict()` (convierte `SourceReference` a dict automáticamente).
- **RAGInteractionLogger**: `redact_pii=True` → aplica regex antes de loggear; nunca omite la pregunta completa.
- **RAGService**: `_log()` captura excepciones del logger con `except Exception` (logger nunca interrumpe la respuesta); `_extract_sources()` deduplica por `(doc, page)` preservando orden.
- **Streamlit**: `@st.cache_resource` en `_build_service()` — el modelo de embeddings se carga una vez por sesión de servidor.

### Bugs reales atrapados en Fase 0–2

1. Aplanado automático de YAML no coincidía con nombres de campo de `Settings`.
2. Jerarquía de precedencia de Pydantic Settings invertida por defecto.
3. `src/__init__.py` de más causaba módulo duplicado en mypy.
4. CI solo instalaba `.[dev]`, nunca `requirements.txt` → pypdf "no encontrado".
5. Black sin pin → versión CI distinta a local → CI rojo; fix: `black==26.5.1`.
6. `list(numpy_array)` produce `np.float32`, no `float` Python; fix: `.tolist() + cast`.
7. Teléfono `+52NNNNNNNNNN` compacto no matcheaba `\b\d{10}\b` (no hay word boundary entre dígitos adyacentes); fix: patrón separado `\+52\d{10}(?!\d)` antes del patrón genérico de 10 dígitos.

### Configuración de calidad activa

- `pyproject.toml`: black==26.5.1, Ruff (E/F/I/B/UP/N/SIM), mypy strict en `genai_toolkit.*`, pytest + coverage (`fail_under = 50`).
- `.github/workflows/ci.yml`: instala `requirements.txt` y `-e ".[dev]"` antes de lint/type/test.
- `.github/workflows/security.yml`: gitleaks + `pip-audit` con allowlist `security/accepted-vulnerabilities.txt`.

### Entorno local del usuario

Windows, PowerShell, venv en `.venv\Scripts\activate`. Para commits multilínea
desde PowerShell usar `-F archivo` (no heredoc `@'...'@` — falla con git en PS 5.1).

## 6. Roadmap completo

| Fase | Contenido | Estado |
|---|---|---|
| 0 | Setup, arquitectura, skills, interfaces del toolkit, Configuration Layer, CI/CD básico | **Cerrada** (incluida en v0.1.0) |
| 1 | MVP local: PdfLoader, Chunker, Embeddings, ChromaDB, Retriever, OllamaProvider, PromptManager, IngestionPipeline + CLI | **Cerrada** → `v0.1.0` |
| 2 | UI Streamlit + Observability Layer (logging estructurado JSONL, redacción PII) | **Cerrada** → `v0.2.0` |
| 3 | Suite de testing completa, pre-commit, sube `fail_under` de 50 → 70% | **Cerrada** → `v0.3.0` |
| 4 | Evaluación RAG (RAGAS + evaluadores propios), mitigación SSRF de `ragas` | Pendiente |
| 5 | Seguridad: guards in/out, suite de security tests, OWASP checklist | Pendiente |
| 6 | CI/CD avanzado | Pendiente |
| 7 | Dockerización | Pendiente |
| 8 | API FastAPI | Pendiente |
| 9 | Prep cloud | Pendiente |

## 7. ✅ Fase 3 cerrada — Testing Suite (v0.3.0, 2026-06-20)

### Lo que se implementó

1. **Pre-commit hooks** — `.pre-commit-config.yaml` actualizado: Black 26.5.1, ruff v0.15.18,
   mypy v2.1.0 scope `^src/genai_toolkit/`, hooks de higiene y secret scanning (gitleaks).

2. **Suite de integración** (`tests/integration/`, 20 tests, `@pytest.mark.integration`):
   - `test_chroma_e2e.py`: ChromaVectorStore real con vectores fijos (sin modelo)
   - `test_retrieval_e2e.py`: SimpleRetriever + SentenceTransformerProvider + ChromaDB reales
   - `test_ingestion_e2e.py`: IngestionPipeline con blank PDF y con LoadedDocument de texto
   - CI actualizado: `pytest -m "not integration and not e2e"` en el job rápido

3. **Suite de seguridad** (`tests/security/`, 39 tests, `@pytest.mark.security`):
   - `test_input_guards.py`: RAGService rechaza vacío/whitespace/oversized antes del pipeline
   - `test_document_guards.py`: PdfLoader rechaza ZIP/DOCX/HTML disfrazados, sobredimensionados, corruptos
   - `test_chunker_sanitization.py`: sanitización de control chars + integridad de marcadores `<context>`

4. **`fail_under` = 70%** — meta de ADR-004 alcanzada; ADR-004 actualizado con historial.

### Siguiente: Fase 4 — Evaluación RAG (RAGAS)

Rama sugerida: `feature/ragas-evaluation`


## 8. Cómo seguir trabajando (instrucciones de proceso)

- Rama nueva desde `develop` actualizado: `git checkout -b feature/<nombre>`.
- Implementar → `black .` → `ruff check . --fix` → `mypy src/` → `pytest` → commit con
  Conventional Commits → PR → merge a `develop`.
- Al cerrar Fase N: PR `develop` → `main`, tag `vX.Y.0`, GitHub Release, actualizar CHANGELOG.md.
- Si surge una decisión no obvia, documentarla como ADR-006+ siguiendo el
  formato de los 5 existentes en `docs/architecture/adr/`.

### Para ejecutar los tests de integración localmente

```bash
# Requiere el modelo intfloat/multilingual-e5-small descargado
pytest -m integration -v
```

---

**Para Claude Code**: si este documento contradice el estado real del código
en el repo (porque el usuario ya avanzó antes de que esto se sincronizara),
el código y el historial de Git son la fuente de verdad —
usa este documento para recuperar el *razonamiento y las decisiones previas*,
no como especificación exacta del estado actual de archivos.
