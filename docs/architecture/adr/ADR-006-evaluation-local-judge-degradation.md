# ADR-006: Evaluación RAG en dos capas — evaluadores deterministas + RAGAS con juez local degradable

## Estado

Aceptado · Fase 4 (2026-06-21)

## Contexto

La RAG Evaluation Skill (`docs/engineering_skills/05_rag_evaluation.md`) define
ocho métricas: cinco que cubre RAGAS (faithfulness, answer relevancy, context
precision/recall, groundedness) y tres propias (refusal quality, citation
accuracy, hallucination rate). RAGAS requiere un **LLM juez** para calcular sus
métricas.

Restricción dura del proyecto (ver CONTEXT.md y README): **sin APIs de pago**.
RAGAS por defecto usa OpenAI; usarlo violaría esa restricción. La alternativa es
apuntar RAGAS al mismo Ollama local (`llama3.1:8b`) que ya usa el sistema.

El problema: RAGAS con un juez local pequeño en CPU es **lento y frágil** —
tarda minutos por lote, depende de que el modelo siga formatos de salida
esperados, y de la compatibilidad entre versiones de `ragas`, `langchain` y el
backend de Ollama. Si esa integración falla, no debe tumbar toda la evaluación
ni bloquear el cierre de fase / la vitrina del MVP.

## Decisión

Evaluación en **dos capas**, con la capa cara claramente subordinada:

1. **Evaluadores propios, deterministas, siempre activos** — viven en
   `src/genai_toolkit/evaluation/` (agnósticos de dominio, ADR-001) y se calculan
   sin ningún LLM: `refusal_quality`, `citation_accuracy`, `hallucination_rate`
   (este último, un proxy determinista del riesgo principal). Son reproducibles
   bit a bit, baratos y testeables en CI (16 tests unitarios).

2. **RAGAS con juez local, best-effort** — `scripts/evaluate.py` intenta calcular
   las métricas de RAGAS apuntando a Ollama local + embeddings e5. La integración
   está aislada en una función con import perezoso y `try/except`: si falla
   (import, versión, timeout, formato), se emite un aviso y la evaluación
   **continúa solo con las métricas deterministas**, sin error fatal.

`hallucination_rate` se modela como proxy determinista (fracción de preguntas que
debían rechazarse pero recibieron respuesta sustantiva), reconociendo que la
medición a nivel de afirmación (claim) la cubre RAGAS faithfulness cuando está
disponible.

## Alternativas consideradas

1. **Solo RAGAS (juez local), sin evaluadores propios**: deja la evaluación
   entera a merced de la parte más frágil del stack. Un fallo de RAGAS = cero
   señal de calidad. Rechazada por frágil.
2. **Usar OpenAI como juez (más estable)**: viola la restricción "sin APIs de
   pago" que es parte de la identidad del proyecto. Rechazada.
3. **Solo evaluadores deterministas, sin RAGAS**: pierde justo las métricas
   (faithfulness, answer relevancy) que son la señal de seniority para un rol de
   Applied AI Engineer. Rechazada: el valor de portafolio de RAGAS justifica
   integrarlo aunque sea best-effort.
4. **RAGAS como gate bloqueante de CI ya**: prematuro — el juez local es lento y
   no determinista; convertirlo en gate haría el CI lento e inestable. Se difiere
   a una fase posterior (ver Testing Skill: "evaluación como gate de CI" es fase
   avanzada).

## Consecuencias

- (+) La evaluación siempre produce señal accionable (las métricas deterministas),
  incluso si RAGAS no está disponible en una máquina dada.
- (+) Cuando Ollama está activo, se obtienen además las métricas RAGAS y la tabla
  completa para el README — el diferenciador de portafolio.
- (+) Las métricas propias corren en CI sin coste (no necesitan modelo); RAGAS no.
- (−) La baseline (`evaluations/results/baseline.json`) solo puede generarse en
  una máquina con Ollama y el modelo descargado; no se produce en CI. Se versiona
  manualmente al correr `python scripts/evaluate.py --update-baseline`.
- (−) El `hallucination_rate` determinista es un proxy, no la medición a nivel de
  claim; se documenta como tal para no sobre-interpretarlo.
