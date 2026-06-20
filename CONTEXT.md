# Contexto del proyecto — Mexico Immigration RAG Assistant (Asesor Migratorio RAG)

> Este documento sintetiza todo lo decidido y construido hasta el cierre de la
> Fase 0 y el avance de Fase 1, para que cualquier sesión nueva de Claude
> (Code o chat) recupere el contexto completo sin tener que re-derivarlo.
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
  usuario verificara en su máquina — varias veces esto sí atrapó bugs reales
  (ver sección 5).
- **Documentar decisiones no obvias como ADR**, con alternativas consideradas
  y por qué se descartaron — no solo "qué se hizo" sino "qué no se hizo y
  por qué". Cinco ADRs ya existen (ver sección 4).
- **Fases pequeñas, una rama por unidad de trabajo, PR aunque se trabaje
  solo**, con auto-revisión del diff antes de mergear. Ver
  **`docs/engineering_skills/01_version_control.md`**.
- **El roadmap por fases es la estructura de avance** — no se salta de fase
  ni se sobrearquitectura adelantándose a necesidades que no existen todavía
  (ej.: no se separó `genai_toolkit/` en librería instalable aparte; vive
  dentro del repo hasta que exista un segundo consumidor real).

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
  proyecto. Pin actualizado a `~=6.0` (resolvió 28 CVEs de la serie 5.x,
  mayoría DoS por PDFs malformados — razón directa por la que el loader debe
  implementar límites de tamaño/páginas/timeout).
- **ADR-003** — Estrategia de gate de seguridad: `pip-audit` con lista
  explícita de excepciones en `security/accepted-vulnerabilities.txt` (cada
  entrada con justificación y fecha de revisión: **2026-09-01**). Un CVE
  nuevo no listado ahí debe seguir bloqueando CI. Pendiente en esa lista:
  upgrade de `langchain` 0.3→1.x (issue de GitHub aún no creado), CVE SSRF
  sin parche en `ragas` (mitigar con restricción de red en Fase 4).
- **ADR-004** — Umbral de cobertura progresivo (no fijo en 70% desde el día
  1): **30% en Fase 0 → 50% en Fase 1 → 70% en Fase 3**. Actualizar
  `pyproject.toml` (`[tool.coverage.report] fail_under`) y este ADR al
  cerrar cada fase — está en el checklist de cierre, no es automático.
- **ADR-005** — Tipos intermedios `RawPage`/`LoadedDocument` en la capa de
  ingesta. El loader produce `LoadedDocument`; el chunker (siguiente pieza)
  lo convierte en `list[Chunk]`. `Chunk`/`ChunkMetadata` no pueden llenarse
  directamente desde el loader porque `chunk_index`, `section` e `id` solo
  existen después del chunking. Ver ADR-005 para alternativa considerada y
  descartada.

## 5. Estado técnico actual (Fase 1 en curso — loader PDF implementado)

### Cerrado en Fase 0 y mergeado a `develop` (rama `feature/genai-toolkit-interfaces`)

- `src/genai_toolkit/retrieval/types.py` — tipos compartidos: `Chunk`,
  `ChunkMetadata`, `ScoredChunk` (score normalizado 0.0–1.0, validado),
  `RetrievalResult` (incluye `has_sufficient_context: bool`).
- `src/genai_toolkit/embeddings/base.py` — `Protocol EmbeddingProvider`.
- `src/genai_toolkit/vectorstore/base.py` — `Protocol VectorStore`.
- `src/genai_toolkit/llm/base.py` — `Protocol LLMProvider`.
- `src/genai_toolkit/retrieval/base.py` — `Protocol Retriever`.
- `src/genai_toolkit/prompts/base.py` — `Protocol PromptManager` +
  `PromptInputs` (dataclass explícito).
- `src/genai_toolkit/config/settings.py` — `Settings` (Pydantic Settings)
  con jerarquía de precedencia: env real > `.env` > kwargs > YAML > defaults.
- `src/genai_toolkit/py.typed` — marcador PEP 561.
- `tests/unit/test_settings.py` — 6 tests reales, todos pasando.
- 4 ADRs, CI/CD en verde (lint + mypy + pip-audit).

### En curso en Fase 1 — rama `feature/pdf-loader` (no mergeada aún)

**Implementado en el commit `06c9f0a` + los cambios de esta sesión:**

- `src/genai_toolkit/ingestion/types.py`:
  - `RawPage` (frozen dataclass): `text`, `page_number` (1-indexed), `source_document`.
  - `LoadedDocument` (frozen dataclass): `source`, `pages: list[RawPage]`, `total_pages`.
  - Jerarquía de excepciones: `IngestError` → `FileTooLargeError`,
    `TooManyPagesError`, `PdfParseError`.

- `src/genai_toolkit/ingestion/base.py`:
  - `DocumentLoader` Protocol (`load(path) -> LoadedDocument`), `@runtime_checkable`.

- `src/genai_toolkit/ingestion/pdf_loader.py` — `PdfLoader`:
  - **Validaciones en orden antes de abrir con pypdf**:
    1. `path.exists()` → `FileNotFoundError`
    2. `_check_file_size()`: `stat().st_size` vs `max_file_size_mb` → `FileTooLargeError`
    3. `_check_mime_type()`: lee primeros 5 bytes, verifica `%PDF-` → `PdfParseError`
       (detecta archivos renombrados sin depender de extensión ni librerías externas)
    4. `pypdf.PdfReader()` en `try/except` → `PdfParseError`
    5. `_check_page_count()`: `len(reader.pages)` vs `max_pages` → `TooManyPagesError`
  - Extracción con timeout de 60 s via `ThreadPoolExecutor` → `PdfParseError` si se agota.
  - `_extract_pages()`: `try/except` por página — fallo individual produce `text=""`,
    no aborta el documento.

- `src/genai_toolkit/ingestion/__init__.py`: exporta API pública completa.

- `tests/unit/test_pdf_loader.py` — 10 tests unitarios, todos pasando:
  - `TestValidation`: FileNotFoundError, FileTooLargeError, TooManyPagesError,
    MIME inválido (magic bytes), cuerpo corrupto con header válido.
  - `TestSuccessPath`: estructura correcta, numeración de páginas, error por
    página → text vacío, None → string vacío, Settings por defecto.

- `docs/architecture/adr/ADR-005-ingestion-intermediate-types.md`: documenta la
  decisión de usar tipos intermedios en lugar de producir `Chunk` directamente.

**Estado de calidad al cierre de esta iteración:**
- 17/17 tests unitarios en verde (10 pdf_loader + 6 settings + 1 placeholder).
- Cobertura total: ~62% (umbral actual: 30%; umbral de Fase 1: 50% — a subir
  en `pyproject.toml` al cerrar la rama).
- `ruff check` y `mypy src/genai_toolkit` limpios.

### Bugs reales atrapados antes de llegar a producción

(Fase 0 — los mismos descritos antes, valen como patrón a vigilar):
1. Aplanado automático de YAML no coincidía con nombres de campo de `Settings`.
2. Jerarquía de precedencia de Pydantic Settings invertida por defecto.
3. `src/__init__.py` de más causaba módulo duplicado en mypy.
4. CI solo instalaba `.[dev]`, nunca `requirements.txt` — pypdf "no encontrado".

### Configuración de calidad activa

- `pyproject.toml`: Black, Ruff (E/F/I/B/UP/N/SIM), mypy strict en
  `genai_toolkit.*`, pytest+coverage (`fail_under = 30`, actualizar a 50 al
  cerrar Fase 1).
- `.github/workflows/ci.yml`: instala `requirements.txt` y `-e ".[dev]"` antes
  de lint/type/test.
- `.github/workflows/security.yml`: gitleaks + `pip-audit` con allowlist de
  `security/accepted-vulnerabilities.txt`.

### Entorno local del usuario

Windows, PowerShell, venv en `.venv\Scripts\activate`. Para commits multilínea
desde PowerShell usar `-F archivo` (no heredoc `@'...'@` — falla con git en PS 5.1).

## 6. Roadmap completo

| Fase | Contenido | Estado |
|---|---|---|
| 0 | Setup, arquitectura, skills, interfaces del toolkit, Configuration Layer, CI/CD básico | **Cerrada** |
| 1 | MVP local: ingesta (loader PDF + validación), chunking, embeddings, ChromaDB, retriever, respuesta con fuentes | **En curso** — loader PDF listo; siguiente: chunker |
| 2 | UI Streamlit + logging básico (Observability Layer real) | Pendiente |
| 3 | Suite de testing completa, pre-commit, sube cobertura a 70% | Pendiente |
| 4 | Evaluación RAG (RAGAS + evaluadores propios), incluye mitigación SSRF de `ragas` | Pendiente |
| 5 | Seguridad: guards in/out, suite de security tests, OWASP checklist — **release v1.0** | Pendiente |
| 6 | CI/CD avanzado | Pendiente |
| 7 | Dockerización | Pendiente |
| 8 | API FastAPI | Pendiente |
| 9 | Prep cloud | Pendiente |

## 7. La pieza inmediata a implementar: chunker de texto

Es el segundo componente con lógica real de Fase 1. Debe:

- Recibir un `LoadedDocument` (salida del loader) y devolver `list[Chunk]`.
- Implementar chunking por tamaño con overlap: `chunk_size` y `chunk_overlap`
  ya están en `Settings` (defaults: 500 tokens/chars, overlap 80).
- Asignar correctamente todos los campos de `Chunk`/`ChunkMetadata`:
  - `chunk_index`: ordinal global dentro del documento (0-indexed).
  - `page`: de la `RawPage` de origen.
  - `section`: opcional, inferir si hay patrones de encabezado (o dejar `None`).
  - `id`: hash estable de `(source_document, chunk_index)`.
- Validar que `chunk_overlap < chunk_size` (ya validado en `Settings`, pero
  el chunker también debe manejar el edge case de páginas de texto muy corto).
- Cubrir con tests unitarios: división correcta, overlap, página vacía, texto
  más corto que `chunk_size`.
- Seguir el mismo patrón de rama: `feature/text-chunker` desde `develop`
  actualizado (esperar a mergear `feature/pdf-loader` primero).

## 8. Cómo seguir trabajando (instrucciones de proceso)

- Mergear `feature/pdf-loader` → `develop` vía PR (verificar CI en verde).
- Rama nueva por unidad de trabajo desde `develop` actualizado.
- Implementar → `ruff check . --fix` → `mypy src/` → `pytest` → commit con
  Conventional Commits → PR → merge.
- Si surge una decisión no obvia, documentarla como ADR-00X siguiendo el
  formato de los 5 existentes.
- Al cerrar Fase 1 completamente: subir `fail_under` de 30 → 50 en
  `pyproject.toml` (ADR-004) y actualizar este documento.

---

**Para Claude Code**: si este documento contradice el estado real del código
en el repo (porque el usuario ya avanzó antes de que esto se sincronizara),
el código y el historial de Git son la fuente de verdad —
usa este documento para recuperar el *razonamiento y las decisiones previas*,
no como especificación exacta del estado actual de archivos.
