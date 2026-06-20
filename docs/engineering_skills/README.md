# Engineering Skills

Guías de ingeniería reutilizables para proyectos de AI Engineering y GenAI.
Aunque nacieron en el proyecto **Mexico Immigration RAG Assistant**, están
escritas para ser **agnósticas de dominio**: copia esta carpeta como punto de
partida en cualquier proyecto futuro (banca, telco, legal, compliance, etc.).

## Cómo usar estas skills

Cada documento es una **directiva activa**: define convenciones, da el porqué y
muestra ejemplos. Durante el desarrollo, en lugar de repetir reglas, basta
referenciar la skill: *"implementa X siguiendo la Testing Skill"*.

Las skills se versionan junto con el código. Si una convención cambia, se
actualiza aquí y el cambio queda trazado en el historial de Git.

## Índice

| # | Skill | Propósito |
|---|-------|-----------|
| 1 | [Version Control](01_version_control.md) | Ramas, commits, releases, qué no subir |
| 2 | [Code Quality](02_code_quality.md) | Black, Ruff, mypy, errores, logging, estructura |
| 3 | [Testing](03_testing.md) | Pytest, unit/integration/e2e, mocks, cobertura |
| 4 | [Security](04_security.md) | Input/output guards, prompt injection, OWASP LLM |
| 5 | [RAG Evaluation](05_rag_evaluation.md) | Métricas, dataset, umbrales POC vs robusto |
| 6 | [Observability](06_observability.md) | Logging estructurado, métricas, qué no registrar |
| 7 | [Documentation](07_documentation.md) | README, ADRs, guías, disclaimers |

## Principio rector

> Profesional pero manejable por una sola persona. Cada regla debe pagar su
> costo: si una convención no mejora calidad, mantenibilidad o seguridad de
> forma tangible, no se adopta.
