# ADR-007: Chunking recursivo — evaluado, no concluyente, y el hallazgo real (eval no reproducible)

## Estado

**Rechazado por falta de evidencia · hallazgo metodológico aceptado** ·
Fase 4 / mantenimiento (2026-06-22)

El chunker por defecto sigue siendo `SlidingWindowChunker` (500/80). El
`RecursiveTextChunker` queda en el código como implementación alternativa del
Protocol `TextChunker`, con sus tests, pero **no se usa por defecto**.

Lo importante de este ADR no es el chunker: es lo que la investigación reveló
sobre la **reproducibilidad de la evaluación**.

## Contexto

El demo (v0.4.0) responde bien las preguntas sugeridas, pero **rechazaba
preguntas libres cuya respuesta sí está en el corpus**. Diagnóstico inicial
(logs de interacciones + sondeo de retrieval read-only):

- El error de telemetría de ChromaDB (`capture() takes 1 positional argument…`)
  se descartó: es un bug de `posthog` que solo afecta la analítica anónima, no
  la búsqueda.
- Los rechazos no venían del retriever (siempre devolvía 6 chunks sobre el
  umbral) sino del LLM. La hipótesis fue que el `SlidingWindowChunker` —que parte
  por número fijo de caracteres (500/80), cortando a media frase— fragmentaba los
  artículos legales y dejaba al LLM sin el pasaje completo.

## Hipótesis evaluada

Reemplazar el chunker por uno **recursivo** (`RecursiveCharacterTextSplitter` de
`langchain-text-splitters`, ya en el stack — sin dependencia nueva), con
separadores para prosa legal en español: `["\n\n", "\n", ". ", "; ", ", ",
" ", ""]`, conservando todas las invariantes del anterior (sanitización de
control chars —centralizada en `processing/_sanitize.py`—, chunking por página
para preservar la cita, `id` SHA-256 estable, `chunk_index` global).

## Lo que pasó al medir (el hallazgo que decidió todo)

Primera comparación contra la baseline de v0.4.0:

| Configuración | refusal_quality |
|---|---|
| Sliding-window 500/80 (baseline guardada) | 0.923 |
| Recursivo 700/120 | 0.769 |
| Recursivo 550/100 | 0.769 |

Parecía una regresión clara. **Pero al re-medir el sliding-window 500/80 —la
misma configuración de la baseline, sin cambiar nada— dio 0.769, no 0.923.**
Eso encendió la alarma: el resultado no era estable.

Se investigó la causa. `RAGService` llamaba a `generate(prompt)` **sin pasar
temperatura ni seed**, usando un default hardcodeado de 0.1 (bug latente: la
temperatura configurada en `Settings` nunca llegaba al LLM). Se corrigió: el
`OllamaProvider` ahora toma `temperature` y `seed` de `Settings`, y se añadió
soporte de `seed` (campo `llm_seed`).

Con la eval ya forzada a `temperature=0` + `seed=42`, se corrió **dos veces la
misma configuración** para verificar reproducibilidad:

| Config idéntica | Corrida A | Corrida B |
|---|---|---|
| sliding 500/80, temp 0.1, sin seed | 0.769 | 0.923 |
| sliding 500/80, **temp 0, seed 42** | 0.846 | 0.923 |

**Sigue variando incluso a temperatura 0 con seed fijo.** Se verificó que el
seed y la temperatura sí llegan a Ollama (no es un bug de plumbing). La causa es
el backend: `llama.cpp`/Ollama **no es bit-reproducible ni en decodificación
greedy** — la no-asociatividad de las reducciones en punto flotante en GPU y el
batching continuo producen tokens distintos entre corridas. El `seed` solo
influye cuando hay muestreo (temp > 0); a temp 0 no rescata la determinación.

## Conclusión

1. **Sobre el chunker: no concluyente.** En *todas* las corridas
   `citation_accuracy = 1.000` → el retrieval a nivel documento es estable e
   idéntico entre chunkers; el chunker no degrada la recuperación. La única
   métrica que se mueve (`refusal_quality`) la gobierna la decisión
   *responder vs. rechazar* del LLM sobre el mismo contexto, y esa decisión es
   no-determinista. Una diferencia de 1-2 preguntas en n=13 **no se puede
   atribuir al chunker**: cae dentro del ruido del propio harness.

2. **Decisión:** mantener `SlidingWindowChunker` (500/80) por defecto. No hay
   evidencia fiable de que el recursivo mejore, y añade complejidad. El
   `RecursiveTextChunker` se conserva como implementación válida del Protocol
   (con tests) por si un corpus futuro lo justifica.

3. **El verdadero hallazgo (aceptado):** la evaluación basada en LLM **no es
   reproducible en este backend**. Comparar configuraciones con una sola corrida
   sobre n=13 es metodológicamente inválido para diferencias pequeñas.

## Qué se conserva de esta investigación

- **Fix de bug:** `RAGService` ya honra `Settings.llm_temperature` (antes lo
  ignoraba).
- **Soporte de `seed`** (`llm_seed` en `Settings`, parámetro `seed` en el
  Protocol `LLMProvider` y en `OllamaProvider`) para reproducibilidad cuando el
  backend lo permita y para la futura eval de retrieval.
- Refactor de sanitización a `processing/_sanitize.py` (compartido por ambos
  chunkers).
- El `RecursiveTextChunker` y sus tests.

## El problema de fondo, sin resolver (trabajo futuro)

El caso que motivó todo (delito en p.47, pena en p.48 de la Ley de Migración)
**no lo arregla ningún chunker que troceé por página** ni se puede medir de forma
fiable con el harness actual. Es un problema de **retrieval semántico**
(`multilingual-e5-small` aplana la similitud y la cláusula de la pena no entra
al top-k) + de **evaluación no determinista**.

Próximos pasos correctos (diferidos a Fase 4/5):

1. **Eval de retrieval determinista**: una métrica que mida, por pregunta, si la
   página/pasaje dorado cae en el top-k recuperado. 100% determinista (sin LLM),
   aisla exactamente lo que el chunker afecta. Es la forma correcta de comparar
   chunkers en el futuro.
2. **Promediar N corridas** para cualquier métrica que dependa del LLM, con
   media ± desviación, en vez de una sola corrida.
3. **Búsqueda híbrida (BM25 + vectorial) o re-ranking** para la síntesis entre
   artículos/páginas, que es la causa real de los rechazos en preguntas libres.

## Alternativas consideradas (chunking)

1. **Subir solo `chunk_size` con la ventana de caracteres**: seguiría cortando a
   media frase. Rechazada.
2. **Chunking que cruza páginas**: resolvería delito/pena pero complica la cita
   de página exacta y no arregla el ranking del embedding. Diferida.
3. **Semantic chunking**: más caro y no determinista; prematuro. Diferida.
4. **Re-ranking / búsqueda híbrida**: el siguiente paso correcto. Diferida a
   Fase 5.

## Consecuencias

- No hay cambio funcional en el chunker respecto a v0.4.0 (corpus re-indexado con
  sliding-window 500/80).
- Mejora real: la temperatura configurada ahora sí se aplica, y el sistema es
  reproducible cuando se fija `seed` con `temperature > 0`.
- Queda documentado, con números, por qué no se puede concluir nada del chunker
  con el harness actual — y cuál es la metodología correcta para hacerlo bien.
  Esto evita reabrir la hipótesis sin datos fiables.
