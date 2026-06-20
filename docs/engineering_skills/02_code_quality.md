# Code Quality Skill

> Convenciones de calidad de código para que el proyecto sea legible,
> mantenible y verificable automáticamente. En AI Engineering esto importa más,
> no menos: el código rodea componentes no deterministas (LLMs), así que la
> parte determinista debe ser sólida como roca.

## Por qué importa

El código alrededor de un LLM es donde viven los bugs reproducibles: chunking
mal calculado, metadata perdida, prompts mal ensamblados. Si esa capa es
desordenada, depurar el sistema completo se vuelve imposible porque no sabes si
el problema es el modelo o tu código. Herramientas automáticas (formateo,
linting, tipos) eliminan clases enteras de errores sin esfuerzo manual.

## Herramientas y por qué cada una aporta

| Herramienta | Qué hace | Por qué en AI Engineering |
|-------------|----------|---------------------------|
| **Black** | Formateo automático determinista | Cero discusiones de estilo; diffs limpios y revisables |
| **Ruff** | Linting + ordenación de imports (reemplaza flake8 + isort) | Atrapa imports sin usar, variables muertas, anti-patrones; rapidísimo |
| **mypy** | Verificación de tipos estática | Las interfaces (Protocols) entre LLM/vectorstore/retriever solo valen si los tipos se respetan |
| **pre-commit** | Corre todo lo anterior antes de cada commit | Garantiza que nada sucio entre al repo |

## Configuración recomendada (en `pyproject.toml`)

```toml
[tool.black]
line-length = 88
target-version = ["py311"]

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "N", "SIM"]
# E/F: errores pycodestyle/pyflakes; I: imports; B: bugbear;
# UP: pyupgrade; N: naming; SIM: simplificaciones
ignore = []

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

# Estricto en el núcleo reutilizable, relajado en exploración
[[tool.mypy.overrides]]
module = "genai_toolkit.*"
strict = true

[[tool.mypy.overrides]]
module = "notebooks.*"
ignore_errors = true
```

Regla de oro: **mypy `strict` en `genai_toolkit/`** (el código que reutilizarás),
relajado en notebooks y scripts exploratorios.

## Estructura de imports

Orden (Ruff lo aplica automáticamente con la regla `I`):

1. Librería estándar.
2. Third-party.
3. Imports locales del proyecto.

```python
# stdlib
from pathlib import Path
from typing import Protocol

# third-party
import chromadb
from pydantic import BaseModel

# local
from genai_toolkit.config import Settings
from genai_toolkit.retrieval import Retriever
```

Evita imports relativos profundos (`from ...config import x`). Usa imports
absolutos desde la raíz del paquete.

## Manejo de configuración

Una **única fuente de verdad**: `Settings` con Pydantic Settings, cargando desde
`.env` + YAML. Nunca hardcodees rutas, nombres de modelo o umbrales dispersos por
el código.

```python
# ✅ bien
settings = Settings()
retriever = Retriever(min_score=settings.retrieval_min_score)

# ❌ mal
retriever = Retriever(min_score=0.7)  # número mágico perdido en el código
```

## Manejo de errores

- Define **excepciones de dominio** propias en lugar de lanzar `Exception` genérico:

```python
class IngestionError(Exception):
    """Fallo al ingerir o validar un documento."""

class RetrievalError(Exception):
    """Fallo en la capa de recuperación."""
```

- **Nunca** `except: pass`. Si capturas, o manejas o re-lanzas con contexto:

```python
# ❌ mal — silencia el error
try:
    text = extract_text(pdf)
except Exception:
    pass

# ✅ bien — contexto y propagación controlada
try:
    text = extract_text(pdf)
except PdfReadError as exc:
    raise IngestionError(f"No se pudo leer {pdf.name}: {exc}") from exc
```

- Captura lo específico, no lo genérico. `except PdfReadError`, no `except Exception`.

## Logging

- **Nunca `print`** en código productivo. Usa el módulo `logging` (o el logger
  estructurado del proyecto).
- Niveles con criterio: `DEBUG` (diagnóstico), `INFO` (eventos normales),
  `WARNING` (algo recuperable raro), `ERROR` (fallo que requiere atención).
- Nunca loggees secretos ni PII (ver Observability Skill).

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Ingestados %d chunks de %s", len(chunks), doc_name)
logger.warning("Retrieval devolvió 0 resultados para la query")
```

## Convenciones de nombres

| Elemento | Convención | Ejemplo |
|----------|-----------|---------|
| Módulos / paquetes | `snake_case` | `vector_store.py` |
| Clases | `PascalCase` | `ChromaVectorStore` |
| Funciones / variables | `snake_case` | `retrieve_chunks` |
| Constantes | `UPPER_SNAKE` | `DEFAULT_CHUNK_SIZE` |
| Privados | prefijo `_` | `_normalize_metadata` |

Nombres que dicen *qué hacen*, no *cómo*: `retrieve_chunks`, no `do_search`.

## Separación notebooks vs. código productivo

| Notebooks (`notebooks/`) | Código productivo (`src/`) |
|--------------------------|----------------------------|
| Exploración, prototipos, análisis visual | Lógica reutilizable y testeada |
| Sin garantías de tipo ni tests | mypy strict + tests |
| Pueden ser desordenados | Cumple todas las convenciones |
| Salidas limpiadas antes de commit | — |

Regla: **cuando algo en un notebook funciona y lo vas a reusar, migra la lógica
a `src/` con tests.** El notebook se queda solo con la exploración.

## Checklist de la skill

- [ ] Black aplicado, sin diffs de formato pendientes
- [ ] Ruff sin warnings
- [ ] mypy pasa (strict en `genai_toolkit/`)
- [ ] Configuración centralizada en `Settings`, sin números mágicos
- [ ] Excepciones de dominio propias; ningún `except: pass`
- [ ] `logging` en vez de `print`
- [ ] Nombres siguen las convenciones de la tabla
- [ ] Lógica reutilizable vive en `src/`, no en notebooks
- [ ] pre-commit instalado y corriendo
