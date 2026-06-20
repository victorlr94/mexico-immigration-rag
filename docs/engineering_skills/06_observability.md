# Observability Skill

> Cómo ver qué está haciendo el sistema en tiempo de ejecución, sin
> infraestructura pesada. Para una POC local, observabilidad significa logging
> estructurado a archivos consultables — suficiente para depurar, medir
> rendimiento y demostrar madurez operativa, sin montar un stack de monitoreo.

## Por qué importa

Un RAG falla de formas silenciosas: retrieval que devuelve chunks irrelevantes,
latencias que se disparan, refusal rate que sube tras cambiar un prompt. Sin
registro estructurado, depuras a ciegas. Con él, cada interacción deja un rastro
analizable, y puedes responder preguntas como "¿cuál es la latencia media?" o
"¿qué porcentaje de queries se rechaza?" con datos, no intuición.

## Qué registrar por interacción

| Campo | Descripción |
|-------|-------------|
| `timestamp` | Momento de la interacción (UTC, ISO 8601) |
| `question` | La pregunta (ver políticas de privacidad abajo) |
| `question_type` | `in_scope` / `out_of_scope` / `refused` |
| `retrieved_context_ids` | IDs de los chunks recuperados |
| `source_documents` | Documentos fuente + página |
| `retrieval_scores` | Scores de similitud de los chunks |
| `answer` | Respuesta generada |
| `response_time_ms` | Latencia total |
| `stage_latencies` | (Opcional) latencia por etapa: retrieval, generación |
| `model` | Modelo LLM usado (nombre + versión) |
| `embedding_model` | Modelo de embeddings usado |
| `error` | Error capturado, si lo hubo |
| `evaluation` | Métricas, si la corrida fue evaluada |

## Métricas derivadas

A partir de los registros puedes computar:

- **Retrieval**: score medio de los top-k, tasa de queries sin resultados sobre
  umbral, distribución de documentos fuente.
- **Generación**: latencia media/p95, tasa de errores.
- **Comportamiento**: refusal rate, proporción in-scope vs out-of-scope.
- **Evaluación**: tendencia de las métricas RAG en el tiempo.

## Cómo almacenar localmente

Progresión por madurez — empieza simple, sube cuando lo necesites:

| Formato | Cuándo | Ventaja | Limitación |
|---------|--------|---------|------------|
| **JSONL** | Punto de partida (POC) | Un evento por línea; trivial de escribir y leer; sin dependencias | Consultas/agregaciones requieren parsear todo |
| **SQLite** | Cuando quieras consultar/agregar | SQL sobre los datos; ideal para un dashboard local; sin servidor | Algo más de setup |
| **CSV** | Exports puntuales | Abre en cualquier hoja de cálculo | Pobre para datos anidados |

Recomendación: **JSONL desde el día 1, SQLite cuando empieces a hacer
analítica.** La interfaz `ObservabilityStore` permite cambiar el sink sin tocar
el código que loggea.

```text
genai_toolkit/observability/
├── logger.py    # API de logging estructurado (qué se registra)
└── store.py     # ObservabilityStore: JSONL / SQLite (dónde se registra)
```

Ejemplo de registro JSONL:

```json
{"timestamp":"2026-06-19T14:30:00Z","question_type":"in_scope","model":"llama3.1:8b","response_time_ms":1840,"retrieval_scores":[0.82,0.79,0.71],"source_documents":[{"doc":"guia.pdf","page":4}],"error":null}
```

## Logging estructurado vs. logging de aplicación

Distingue dos planos:

- **Logging de aplicación** (módulo `logging`): eventos técnicos, niveles
  DEBUG/INFO/WARNING/ERROR, para depurar el código. Va a `logs/app.log`.
- **Logging de interacciones** (`ObservabilityStore`): el registro estructurado
  de la tabla anterior, para analítica del RAG. Va a JSONL/SQLite.

No los mezcles: uno es para el desarrollador, otro es el dataset operativo.

## Qué NO registrar (privacidad y seguridad)

Crítico, sobre todo en dominio migratorio donde los usuarios pueden escribir
datos personales:

- **PII en las preguntas**: números de documento, nombres, datos de caso
  personal. Si se detectan, **redactar antes de loggear** (sustituir por
  `[REDACTED]`). Considera ofrecer un modo que no registre el texto crudo de la
  pregunta, solo su tipo y metadata.
- **Secretos**: nunca claves, tokens ni credenciales.
- **Rutas absolutas del sistema** que revelen la estructura del host.
- **Contenido íntegro de documentos sensibles**: registra IDs y referencias, no
  el texto completo.

Documenta la **política de retención** (cuánto tiempo se guardan los logs) y la
de **anonimización**. Para una POC, retención corta y redacción de PII por
defecto.

## Checklist de la skill

- [ ] `ObservabilityStore` con sink JSONL implementado
- [ ] Todos los campos de la tabla se registran por interacción
- [ ] Logging de aplicación (`logging`) separado del de interacciones
- [ ] Redacción de PII activada por defecto
- [ ] Ningún secreto, ruta absoluta ni documento íntegro en los logs
- [ ] Política de retención y anonimización documentada
- [ ] (Cuando aplique) Migración a SQLite para analítica
- [ ] Métricas derivadas (latencia, refusal rate) computables desde los logs
