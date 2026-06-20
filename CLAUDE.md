# CLAUDE.md — Contexto de continuidad del proyecto

> Este archivo existe para que cualquier sesión de Claude (Cowork o Claude Code)
> recupere el estado real del proyecto sin tener que re-explicarlo. Generado el
> 2026-06-20 a partir de una inspección directa del repo (no de memoria de chat).
> Actualízalo al cerrar cada fase o feature branch relevante.

## Qué es este proyecto

**Asesor Migratorio RAG** (paquete `mexico-immigration-rag`): asistente RAG que
responde en lenguaje natural sobre documentación pública migratoria de México,
con cita de fuente/página, señal de confianza y disclaimer legal. Construido
100% con tecnologías open source y modelos locales (sin APIs de pago).

Objetivo de fondo (importa para cualquier decisión de diseño): es el primer
proyecto de una serie de portafolio en **AI Engineering**. El núcleo
(`src/genai_toolkit/`) debe quedar **agnóstico de dominio** para reutilizarse
después en banca, telco, legal o compliance — ver ADR-001. No metas referencias
al dominio migratorio dentro de `genai_toolkit/`.

## Stack

| Capa | Herramienta |
|---|---|
| Lenguaje | Python 3.11 |
| Orquestación RAG | LangChain |
| Vector store | ChromaDB (local) |
| Embeddings | `intfloat/multilingual-e5-small` (Sentence Transformers) |
| LLM | Ollama, `llama3.1:8b` local |
| Interfaz | Streamlit |
| Evaluación | RAGAS + evaluadores propios |
| Calidad | Black · Ruff · mypy (strict en `genai_toolkit`) · pytest+coverage |
| CI/CD | GitHub Actions (lint/type/test + security) |

## ⚠️ Estado real del repositorio (léelo antes de tocar nada)

El working tree por defecto está en `develop`, pero **el trabajo real de Fase 0
vive en `feature/genai-toolkit-interfaces`, que va 8 commits adelante de
`develop` y todavía no se ha mergeado vía PR**. Si solo miras los archivos de
`develop` vas a ver `genai_toolkit/` casi vacío (solo `__init__.py`) y vas a
pensar que no hay nada hecho. No es así.

```
main
 └─ develop                              (a655ff9 — solo el scaffold inicial)
     └─ feature/genai-toolkit-interfaces (be08f6c — HEAD real del trabajo)
```

Acción pendiente antes de seguir con Fase 1: abrir/mergear el PR de
`feature/genai-toolkit-interfaces` → `develop` (regla del Version Control
Skill: toda feature se integra a `develop` vía PR antes de empezar la
siguiente). Hasta entonces, sigue trabajando sobre esa rama, no sobre `develop`.

Nota operativa: detecté cambios sin commitear en `develop` en
`ci.yml`, `security.yml`, `pyproject.toml`, `requirements.txt` que al revisarlos
son **ruido de fin de línea (CRLF/LF)**, no cambios de contenido — probablemente
por el montaje del repo entre Windows y el sandbox Linux de esta sesión. No los
toqué. Verifícalo con `git diff` antes de commitear cualquier cosa en esa rama.

## Qué está implementado (en `feature/genai-toolkit-interfaces`)

- **Interfaces del core** (`typing.Protocol`, sin implementación concreta
  todavía): `EmbeddingProvider`, `VectorStore`, `LLMProvider`, `Retriever`,
  `PromptManager`.
- **Tipos compartidos**: `Chunk`, `ChunkMetadata`, `ScoredChunk`,
  `RetrievalResult` (`src/genai_toolkit/retrieval/types.py`).
- **Configuration Layer completa** (`src/genai_toolkit/config/settings.py`):
  `Settings` (Pydantic) con jerarquía de precedencia explícita: env real >
  `.env` > kwargs del constructor > `configs/default.yaml` > defaults de campo.
  Mapeo YAML→campo explícito (no aplanado automático, a propósito — ver
  docstring del archivo). 96% de cobertura, 7 tests unitarios en
  `tests/unit/test_settings.py`, todos pasando.
- **`configs/default.yaml` y `.env.example`** ya definen los parámetros reales
  del sistema: `llm.model=llama3.1:8b`, `embeddings.model=multilingual-e5-small`,
  `chunking.chunk_size=500/overlap=80`, `retrieval.top_k=4/min_score=0.70`,
  límites de seguridad de ingesta (`max_file_size_mb=25`, `max_pages=300`,
  `max_input_chars=2000`), umbrales de evaluación RAGAS (faithfulness 0.80,
  answer_relevancy 0.75, etc.), observabilidad (`jsonl`, `redact_pii=true`).
- **CI/CD endurecido**: lint (Ruff) y mypy en verde, `pip-audit` como gate
  bloqueante con lista explícita de excepciones revisadas (ver ADR-003),
  umbral de cobertura ajustado a la fase real (ver ADR-004).
- **4 ADRs** en `docs/architecture/adr/` (ver resumen abajo).

## Qué NO está implementado todavía (esto es lo que sigue, Fase 1)

- Ningún loader/parser real de documentos (`src/genai_toolkit/ingestion/` solo
  tiene `__init__.py`). El plan ya decidido es usar **pypdf ~=6.0** (ADR-002),
  con `try/except` aislado y timeout explícito al implementarlo — pendiente.
- Chunking, embeddings concretos, VectorStore concreto (Chroma), LLM provider
  concreto (Ollama), Retriever concreto, PromptManager concreto: todo son
  `Protocol`s sin clase que los implemente.
- `src/domain/` y `src/application/` (capa fina del dominio migratorio):
  prácticamente vacíos, solo placeholders.
- `app/streamlit_app.py`, `scripts/ingest.py`, `scripts/evaluate.py`: no existen
  aún (el README los referencia como "pendiente").
- Subir cobertura de 30% → 50% conforme se implementen estos módulos (ADR-004).

## Decisiones de arquitectura ya tomadas (no las reabras sin una razón nueva)

| ADR | Decisión | Por qué |
|---|---|---|
| ADR-001 | `genai_toolkit/` agnóstico de dominio, separado de `domain/`+`application/`. Interfaces vía `Protocol`/ABC. | Reutilización futura en otros dominios sin refactor; rechazado monolito y librería separada desde el día 1 (prematuro). |
| ADR-002 | `pypdf~=6.0` para extracción de PDF (no PyMuPDF). | Resuelve los CVEs de DoS conocidos; PyMuPDF tiene una vulnerabilidad más grave (path traversal/escritura arbitraria) y es AGPL (incompatible con MIT del repo). |
| ADR-003 | `security/accepted-vulnerabilities.txt` con IDs explícitos + justificación + fecha de revisión, alimentando `pip-audit --ignore-vuln`. | Mantiene el gate bloqueante para vulns *nuevas* sin que vulns ya revisadas (sin parche disponible, ej. RAGAS SSRF) bloqueen cada build para siempre. Próxima revisión: **2026-09-01**. |
| ADR-004 | `fail_under` de cobertura: 30% (Fase 0) → 50% (Fase 1) → 70% (Fase 3). | En Fase 0 el toolkit es solo `Protocol`s sin lógica ejecutable; un 70% fijo bloquearía cada PR sin señalar ningún problema real. |

## Reglas de trabajo del proyecto (resumen — el detalle vive en `docs/engineering_skills/`)

- **Branching**: GitHub Flow extendido. `main` (deploy) ← `develop` (integración)
  ← `feature/<nombre>` (una unidad de trabajo). PR obligatorio incluso
  trabajando solo. Ejemplo de nombre ya usado en el roadmap: `feature/pdf-loader`.
- **Commits**: Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`,
  `security:`, `chore:`, `ci:`, `refactor:`, `perf:`).
- **Cierre de fase**: merge `develop`→`main`, tag SemVer (`v0.1.0` = fin Fase 1),
  GitHub Release, actualizar `CHANGELOG.md` y el umbral de cobertura.
- **Seguridad**: `pip-audit` bloqueante; toda vuln nueva debe revisarse y, si se
  acepta, documentarse en `security/accepted-vulnerabilities.txt` con fecha de
  revisión (no "ignorar y olvidar").
- Las 7 "engineering skills" en `docs/engineering_skills/` son la fuente de
  verdad detallada: version control, code quality, testing, security,
  evaluación RAG, observabilidad, documentación. Conséltalas antes de
  desviarte de lo aquí resumido.

## Roadmap completo

| Fase | Objetivo | Estado |
|---|---|---|
| 0 | Setup, arquitectura, interfaces, configuración | 🟡 Casi cerrada — falta mergear `feature/genai-toolkit-interfaces` → `develop` |
| 1 | MVP local RAG (ingestion, chunking, embeddings, vectorstore, retriever, LLM, prompts) | ⚪ Siguiente |
| 2 | UI Streamlit + logging | ⚪ Pendiente |
| 3 | Testing, linting, type checking (cobertura → 70%) | ⚪ Pendiente |
| 4 | Evaluación RAG (RAGAS) | ⚪ Pendiente |
| 5 | Seguridad + red teaming | ⚪ Pendiente |
| 6 | CI/CD | ⚪ Pendiente (ya hay base) |
| 7 | Dockerización | ⚪ Pendiente |
| 8 | API FastAPI | ⚪ Pendiente |
| 9 | Preparación cloud | ⚪ Pendiente |

## Cómo verificar este estado tú mismo (no confíes solo en este archivo)

```bash
git branch -a                                            # confirma las 3 ramas
git log --oneline develop..feature/genai-toolkit-interfaces   # commits no mergeados
git diff develop feature/genai-toolkit-interfaces --stat      # qué archivos difieren
pytest --cov=src --cov-report=term-missing                    # estado real de tests/cobertura
cat security/accepted-vulnerabilities.txt                     # (en la feature branch)
```

## Próximo paso inmediato sugerido

1. `git checkout feature/genai-toolkit-interfaces` y confirmar que CI sigue verde.
2. Abrir PR `feature/genai-toolkit-interfaces` → `develop`, revisar el diff,
   mergear (cierra Fase 0 a falta de docs finales).
3. Empezar Fase 1 en una nueva rama (`feature/pdf-loader` es el nombre sugerido
   en el propio roadmap) implementando el loader de PDF con pypdf~=6.0 y los
   límites de seguridad ya definidos en `Settings` (`max_file_size_mb`,
   `max_pages`).
