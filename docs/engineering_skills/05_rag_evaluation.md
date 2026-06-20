# RAG Evaluation Skill

> Cómo medir si el sistema RAG responde bien. Sin evaluación, "funciona" es una
> opinión; con evaluación, es un número con umbral. Esta skill convierte la
> calidad del RAG en algo medible, comparable entre versiones y verificable en CI.

## Por qué importa

Es lo que separa un "RAG de tutorial" de un "RAG de ingeniero applied". Cualquiera
conecta un retriever a un LLM; demostrar que sabes **medir faithfulness, detectar
alucinaciones y poner umbrales de aceptación** es la señal de seniority que busca
un puesto de Applied AI Engineer. Además, sin métricas no puedes saber si un
cambio (otro chunk size, otro modelo) mejora o empeora el sistema.

## Las métricas y qué significan

| Métrica | Pregunta que responde | Por qué importa aquí |
|---------|----------------------|----------------------|
| **Faithfulness** | ¿La respuesta se deriva fielmente del contexto, sin inventar? | La más crítica en dominio regulado: mide alucinación |
| **Answer Relevancy** | ¿La respuesta atiende realmente la pregunta? | Una respuesta fiel pero irrelevante no sirve |
| **Context Precision** | ¿Los chunks recuperados son relevantes (poco ruido)? | Mide la calidad del retriever (señal vs. ruido) |
| **Context Recall** | ¿Se recuperó toda la info necesaria? | Si falta contexto, la respuesta será incompleta |
| **Groundedness** | ¿Cada afirmación tiene soporte en el contexto? | Solapa con faithfulness; foco en cada claim |
| **Refusal quality** *(propia)* | ¿Rechaza bien lo fuera de dominio / sin sustento? | En dominio regulado, rechazar mal es peor que callar |
| **Citation accuracy** *(propia)* | ¿Las fuentes citadas corresponden al contenido? | Una cita incorrecta destruye la confianza |
| **Hallucination rate** *(propia)* | % de respuestas con afirmaciones no sustentadas | KPI directo del riesgo principal |

Las primeras cinco las cubre **RAGAS** (open source). Las tres "propias" se
implementan como evaluadores a medida en `genai_toolkit/evaluation/`.

## Construcción del dataset de evaluación

Combina dos fuentes — necesitas ambas:

**Preguntas manuales (tu ground truth de calidad).** Tú escribes 20-30 preguntas
basadas en los documentos reales, cada una con:

```json
{
  "question": "¿Qué documentos se requieren para el trámite X?",
  "ground_truth": "Se requieren A, B y C.",
  "expected_source": "guia_tramite_x.pdf",
  "expected_page": 4,
  "category": "in_scope"
}
```

**Preguntas sintéticas (cobertura amplia).** RAGAS puede generar pares
pregunta-contexto desde tus documentos automáticamente, ampliando la cobertura
sin escribir todo a mano. Revísalas: descarta las mal formadas.

**Casos adversariales deliberados.** Incluye explícitamente:

- Preguntas **fuera de dominio** (`category: "out_of_scope"`) → deben rechazarse.
- Preguntas **sin respuesta en el corpus** (`category: "no_answer"`) → deben
  responder "no encontrado", no inventar.

Guarda todo en `evaluations/test_questions.jsonl`.

### Cómo crear buenas preguntas

- **Manuales**: cubre los trámites/temas más frecuentes; varía la dificultad
  (factual directa, que requiere combinar dos chunks, ambigua).
- **Sintéticas**: útiles para volumen y casos que no se te ocurrirían; siempre
  con revisión humana.
- Equilibra categorías: mayoría in-scope, pero suficientes out-of-scope y
  no-answer para que `refusal quality` sea medible.

## Umbrales de calidad

| Métrica | POC (mínimo aceptable) | Versión robusta |
|---------|------------------------|-----------------|
| Faithfulness | ≥ 0.80 | ≥ 0.90 |
| Answer Relevancy | ≥ 0.75 | ≥ 0.85 |
| Context Precision | ≥ 0.70 | ≥ 0.85 |
| Context Recall | ≥ 0.70 | ≥ 0.85 |
| Refusal quality | ≥ 0.90 | ≥ 0.95 |
| Hallucination rate | ≤ 0.10 | ≤ 0.03 |

Nota sobre `refusal quality`: el umbral es alto incluso en POC porque, en un
dominio migratorio, **rechazar mal (responder algo inventado a una pregunta sin
sustento) es peor que no responder.**

## Evaluación manual vs. automática

| | Manual | Automática (RAGAS + evaluadores propios) |
|-|--------|------------------------------------------|
| Cuándo | Revisión cualitativa de casos clave | Cada cambio relevante; gate en CI |
| Fortaleza | Capta matices que las métricas no ven | Escalable, reproducible, comparable |
| Debilidad | No escala, subjetiva | Puede pasar por alto sutilezas |

Usa ambas: la automática como red de seguridad continua, la manual para auditar
periódicamente una muestra y calibrar confianza en las métricas.

## Operación

- Corre como script: `scripts/evaluate.py` produce un reporte sobre el dataset.
- Guarda una **baseline** versionada en `evaluations/results/baseline.json`.
- En fases avanzadas, conviértelo en **gate de CI**: si una métrica cae bajo el
  umbral respecto a la baseline, el build falla. Esto previene regresiones de
  calidad al cambiar prompts, modelos o parámetros.

```text
flujo: dataset → ejecutar RAG sobre cada pregunta → RAGAS + evaluadores propios
       → reporte con métricas → comparar contra umbrales → pass/fail
```

## Checklist de la skill

- [ ] Dataset con preguntas manuales (con ground truth y fuente esperada)
- [ ] Preguntas sintéticas generadas y revisadas
- [ ] Casos out-of-scope y no-answer incluidos
- [ ] RAGAS integrado para las cinco métricas base
- [ ] Evaluadores propios: refusal quality, citation accuracy, hallucination rate
- [ ] Umbrales POC definidos y documentados
- [ ] Baseline versionada en el repo
- [ ] `scripts/evaluate.py` reproducible
- [ ] (Fase avanzada) Evaluación como gate de CI
