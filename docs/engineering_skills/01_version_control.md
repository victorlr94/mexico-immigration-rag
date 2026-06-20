# Version Control Skill

> Estrategia Git/GitHub profesional pero manejable por un desarrollador
> individual. El objetivo doble es: (1) trabajar con disciplina de equipo aunque
> trabajes solo, y (2) que el repositorio comunique competencia a quien lo revise.

## Por qué importa

Un historial de Git limpio es parte del producto en un proyecto de portfolio.
Un reclutador técnico que abre tu repo lee los commits, mira los PRs y revisa
los releases antes que el código. Commits como `fix stuff` o un único branch con
80 commits sin estructura comunican lo contrario de lo que quieres.

## Estrategia de ramas

Usamos **GitHub Flow extendido con `develop`**: simple pero con separación entre
integración y lo desplegable.

| Rama | Propósito | Regla |
|------|-----------|-------|
| `main` | Siempre desplegable, refleja el último release | Solo recibe merges desde `develop` (o `hotfix/*`) vía PR |
| `develop` | Integración continua de features | Recibe merges desde `feature/*` vía PR |
| `feature/<nombre>` | Una unidad de trabajo (≈ un PR) | Nace de `develop`, muere al mergear |
| `fix/<nombre>` | Corrección no urgente | Igual que feature |
| `hotfix/<nombre>` | Corrección urgente sobre producción | Nace de `main`, se mergea a `main` **y** `develop` |

Nombres descriptivos: `feature/pdf-loader`, `fix/empty-retrieval`,
`feature/ragas-runner`. Evita `feature/cambios` o `feature/test`.

## Pull Requests (aunque trabajes solo)

Sí, abres PR aunque seas el único desarrollador. Razones:

- Te obliga a una **auto-revisión** del diff antes de integrar — atrapas errores.
- El PR es la unidad donde corre la CI; nada entra a `develop` sin pasar lint/type/test.
- El historial de PRs es evidencia visible de proceso profesional.

Plantilla mínima de descripción de PR:

```markdown
## Qué hace
Breve descripción del cambio.

## Por qué
El problema o necesidad que resuelve.

## Cómo probarlo
Pasos o comando para verificar (ej. `pytest tests/unit/test_chunking.py`).

## Checklist
- [ ] Tests añadidos/actualizados
- [ ] Lint y type check pasan
- [ ] Documentación actualizada si aplica
```

## Conventional Commits

Formato: `<tipo>(<scope opcional>): <descripción en imperativo>`.

| Tipo | Uso |
|------|-----|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de bug |
| `test` | Añadir o corregir tests |
| `docs` | Documentación |
| `refactor` | Cambio interno sin alterar comportamiento |
| `security` | Mitigación o endurecimiento de seguridad |
| `chore` | Tareas de mantenimiento (deps, config) |
| `ci` | Cambios en CI/CD |
| `perf` | Mejora de rendimiento |

Ejemplos:

```text
feat: add document ingestion pipeline
fix: handle empty retrieval results
test: add unit tests for chunking strategy
docs: update installation guide
security: add prompt injection validation
refactor: separate retriever from generator
chore: pin chromadb to 0.5.x
```

Beneficio concreto: los Conventional Commits alimentan la generación automática
del CHANGELOG (ej. con `git-cliff`) y dejan un historial legible por humanos y
máquinas.

## Versionado semántico (SemVer)

Formato `MAJOR.MINOR.PATCH`:

- **MAJOR**: cambios incompatibles en la interfaz pública.
- **MINOR**: funcionalidad nueva compatible hacia atrás.
- **PATCH**: correcciones compatibles.

Durante la POC vivimos en `0.x`: la API se considera inestable y los incrementos
son más laxos. Sugerencia de mapeo con el roadmap:

| Hito | Versión |
|------|---------|
| Fin Fase 1 (MVP RAG) | `v0.1.0` |
| Fin Fase 2 (UI + logging) | `v0.2.0` |
| Fin Fase 4 (evaluación) | `v0.4.0` |
| Fin Fase 5 (seguridad) — release fuerte de portfolio | `v1.0.0` |

## Releases, tags y changelog

Al cerrar una fase:

1. Mergea `develop` → `main` vía PR.
2. Crea un tag anotado: `git tag -a v0.1.0 -m "MVP RAG local"`.
3. Publica un **GitHub Release** con notas (resumen de lo entregado).
4. Actualiza `CHANGELOG.md`.

Formato de CHANGELOG (basado en *Keep a Changelog*):

```markdown
# Changelog

## [0.1.0] - 2026-XX-XX
### Added
- Pipeline de ingesta de documentos PDF/TXT
- Búsqueda semántica sobre ChromaDB
### Security
- Validación de archivos en la ingesta
```

## Issues y Milestones

- Un **Issue** por cada entregable del roadmap. Etiqueta por tipo
  (`enhancement`, `bug`, `security`, `docs`).
- Un **Milestone** por fase, agrupando sus issues. Da una barra de progreso
  visible y comunica planificación.

## Qué NO subir al repositorio

El `.gitignore` debe cubrir como mínimo:

```gitignore
# Secretos y entorno
.env
.env.*
!.env.example

# Datos (referenciar con script de descarga, no commitear binarios pesados)
data/raw/
data/processed/

# Índices y artefactos del vector store
*.chroma/
chroma_db/

# Modelos descargados
*.gguf
models/

# Resultados voluminosos de evaluación (conservar solo baseline)
evaluations/results/*
!evaluations/results/baseline.json

# Python
__pycache__/
*.pyc
.venv/
.mypy_cache/
.pytest_cache/
.ruff_cache/

# Notebooks: salidas (usar nbstripout o limpiar antes de commit)
*.ipynb_checkpoints/
```

## Manejo de archivos grandes y datasets

- **No commitees binarios pesados** (PDFs grandes, modelos, índices). Infla el
  repo permanentemente — el historial de Git nunca olvida.
- Para documentos fuente: incluye un `scripts/download_data.py` o un
  `data/README.md` con las URLs oficiales y cómo obtenerlos.
- Si un dataset *debe* versionarse, evalúa **Git LFS**, pero para una POC casi
  siempre es preferible un script de descarga.
- Para resultados de evaluación: versiona solo la **baseline** de referencia;
  el resto son artefactos regenerables.

## Checklist de la skill

- [ ] `main` y `develop` existen; `main` protegido por CI
- [ ] Toda feature pasa por `feature/*` → PR → `develop`
- [ ] Commits siguen Conventional Commits desde el commit 1
- [ ] Cada fase cierra con merge a `main`, tag y release
- [ ] CHANGELOG actualizado en cada release
- [ ] Issues vinculados a milestones por fase
- [ ] `.gitignore` cubre secretos, datos, modelos e índices
- [ ] Ningún binario pesado en el historial
