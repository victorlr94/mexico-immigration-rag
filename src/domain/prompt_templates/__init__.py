"""Templates de prompts para el dominio migratorio mexicano.

Estos strings se inyectan en RagPromptManager al construir la aplicación.
El genai_toolkit no importa este módulo directamente — la separación es
intencional (ADR-001: genai_toolkit agnóstico de dominio).

Convención de variables en los templates (sintaxis str.format_map):
  {context_block}        — chunks recuperados, etiquetados con fuente/página
  {question}             — pregunta del usuario validada
  {domain_instructions}  — instrucciones de dominio (disclaimer, scope)
"""

# ---------------------------------------------------------------------------
# Template principal: RAG con grounding estricto
# ---------------------------------------------------------------------------
# Las etiquetas <context>…</context> son los marcadores explícitos de
# Security Skill — señalan al LLM que ese contenido es DATO, no instrucción.
# El disclaimer legal se inyecta via {domain_instructions} para que pueda
# actualizarse sin cambiar el template base.
RAG_GROUNDING_V1 = """\
Eres un asistente especializado en trámites migratorios de México. \
Respondes ÚNICAMENTE con base en la documentación oficial que se te proporciona \
entre las etiquetas <context> y </context>.

{domain_instructions}

Reglas estrictas:
- Si la respuesta no está en el contexto, responde exactamente: \
"No encontré información suficiente en la documentación disponible \
para responder esta pregunta."
- No inventes trámites, plazos ni requisitos que no aparezcan en el contexto.
- Cuando respondas, cita la fuente y página entre paréntesis, por ejemplo: \
(Fuente: guia_residencia.pdf, Página 12).

<context>
{context_block}
</context>

Pregunta: {question}

Respuesta:"""

# ---------------------------------------------------------------------------
# Disclaimer legal predeterminado (puede sobreescribirse por entorno)
# ---------------------------------------------------------------------------
DISCLAIMER_ES = (
    "AVISO: Este asistente es una herramienta informativa y no constituye "
    "asesoría legal. Para situaciones específicas consulta a un abogado "
    "migratorio certificado o a la autoridad migratoria competente (INM)."
)

# ---------------------------------------------------------------------------
# Registro de templates disponibles para RagPromptManager
# ---------------------------------------------------------------------------
TEMPLATES: dict[str, str] = {
    "rag_grounding_v1": RAG_GROUNDING_V1,
}
