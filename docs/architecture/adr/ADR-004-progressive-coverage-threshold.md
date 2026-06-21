# ADR-004: Umbral de cobertura progresivo por fase del roadmap

## Estado

Aceptado · Actualizado en Fase 3 (2026-06-20)

**Historial de cambios:**

| Fecha | Fase | fail_under anterior | fail_under nuevo | Motivo |
|---|---|---|---|---|
| 2026-06-20 | Fase 0 → 1 | — | 30% | Setup inicial; solo Settings implementado |
| 2026-06-20 | Fase 1 → 2 | 30% | 50% | MVP RAG completo; ingestion, embeddings, LLM, prompts |
| 2026-06-20 | Fase 3 | 50% | **70%** | Suite completa: unit + security (39 tests) + integración (20 tests) |

## Contexto

La Testing Skill define 70% de cobertura global como mínimo para el
proyecto, y ese valor se configuró como `fail_under = 70` desde el
scaffold inicial (Fase 0). En esta fase, `genai_toolkit/` contiene
únicamente `Protocol`s y `dataclass`es sin implementación concreta — código
que, por diseño, no se ejecuta (un `Protocol` con cuerpo `...` no tiene
lógica que un test pueda cubrir). Solo `Settings` (con lógica real) tiene
tests reales.

Resultado: cobertura real de 42.86% sobre un umbral fijo de 70%, lo cual
hace que **cada** ejecución de `pytest` en CI falle — no porque haya un test
roto (los 7 tests existentes pasan), sino porque el umbral no es alcanzable
mientras el código sea mayoritariamente interfaces sin implementar. Esto
bloquearía cada PR durante toda la Fase 0 y buena parte de la Fase 1, sin
que el rojo señale ningún problema real — exactamente el efecto contrario al
que un gate de calidad debe tener.

## Decisión

Se baja `fail_under` a **30%** (alcanzable con la cobertura actual sin
trucos: `Settings` ya cubierto al 96%) y se documenta un plan explícito de
incremento alineado al roadmap:

| Fase | Umbral | Justificación |
|------|--------|----------------|
| 0 (actual) | 30% | Solo `Settings` tiene lógica implementada y testeada |
| 1 | 50% | Se suman ingestion, chunking, embeddings, vectorstore con tests |
| 3 | 70% | Meta original; retriever y pipeline ya implementados y testeados |

El valor y su comentario en `pyproject.toml` deben actualizarse al cerrar
cada fase — es responsabilidad explícita del checklist de cierre de fase
(ver Version Control Skill), no un ajuste automático.

## Alternativas consideradas

1. **Excluir del cálculo los archivos `Protocol`-only** (vía `[tool.coverage.run] omit`):
   técnicamente resuelve el número, pero esconde la cobertura real del
   proyecto — un lector del reporte no vería que esos módulos existen sin
   tests, solo que "no se cuentan". Rechazada por menos transparente que
   un umbral progresivo documentado.
2. **Quitar `fail_under` por completo**: el reporte de cobertura seguiría
   imprimiéndose pero nunca bloquearía nada. Rechazada por la misma razón
   que se rechazó `pip-audit || true` en ADR-003: convierte el gate en
   decorativo, sin distinguir una regresión real de no-regresión.
3. **Mantener 70% fijo y aceptar que CI falle hasta la Fase 3**: técnicamente
   "honesto" en el sentido de no relajar nada, pero entrena el hábito de
   ignorar checks en rojo, que es el riesgo que más queremos evitar en un
   pipeline de CI real.

## Consecuencias

- (+) El gate de cobertura vuelve a ser informativo y accionable: un PR que
  baje la cobertura por debajo del umbral de su fase sí debe fallar.
- (+) El incremento documentado por fase da una métrica de progreso visible
  y verificable en el historial de commits (subir el número es evidencia
  de avance real, no solo una promesa).
- (−) Requiere disciplina manual para subir el umbral al cerrar cada fase;
  se mitiga incluyéndolo en el checklist de cierre de fase del roadmap.
- (−) Entre el cierre de una fase y la actualización del umbral, podría
  haber una ventana breve donde el umbral sea más laxo de lo que la
  cobertura real permitiría — riesgo menor, aceptado.
