# Documentation Skill

> La documentación es parte del producto, especialmente en un proyecto de
> portfolio. El README es lo primero (y a veces lo único) que un reclutador lee.
> Esta skill define qué documentar y cómo, para que el repositorio comunique
> competencia y sea usable por alguien que llega de cero.

## Por qué importa

Un proyecto técnicamente brillante con documentación pobre **se ve** mediocre,
porque nadie puede evaluar lo brillante sin entenderlo. A la inversa, un proyecto
bien documentado comunica que sabes trabajar en equipo y entregar software que
otros pueden mantener. En un portfolio, la documentación hace el trabajo de
venta.

## README profesional

Estructura recomendada (cada sección con propósito claro):

| Sección | Qué incluye |
|---------|-------------|
| **Nombre + descripción** | Una línea que diga qué es y para quién |
| **Problema que resuelve** | El "por qué existe" en 2-3 frases |
| **Arquitectura** | Diagrama (Mermaid) + descripción breve de capas |
| **Stack tecnológico** | Tabla de herramientas y su rol |
| **Instalación** | Pasos reproducibles desde cero |
| **Ejecución** | Cómo correr ingesta, app y evaluación |
| **Ejemplo de uso** | Una consulta real con su respuesta |
| **Demo / screenshots** | Imágenes de la UI funcionando |
| **Evaluación** | Métricas y umbrales; tabla de resultados |
| **Seguridad** | Resumen de mitigaciones + enlace a la Security Skill |
| **Limitaciones** | Qué NO hace; honestidad técnica |
| **Disclaimer** | Aviso legal/de dominio (ver abajo) |
| **Roadmap** | Fases y estado |
| **Aprendizajes** | Qué aprendiste construyéndolo |
| **Próximos pasos** | Hacia dónde evoluciona |

El bloque de **Aprendizajes** es subestimado: a un reclutador le interesa cómo
piensas, no solo qué construiste. Menciona decisiones difíciles y trade-offs.

## Diagramas

- Usa **Mermaid** embebido en Markdown: se renderiza en GitHub, vive con el
  código y se versiona como texto (no como imagen binaria que se desactualiza).
- Al menos un diagrama de arquitectura. Considera uno de flujo de datos
  (ingesta) y uno de secuencia (query → respuesta).

## Architecture Decision Records (ADRs)

Un ADR documenta **una decisión arquitectónica no obvia**: por qué elegiste algo
y qué descartaste. Viven en `docs/architecture/adr/`, numerados.

Formato (corto, una página):

```markdown
# ADR-001: Uso de ChromaDB como vector store

## Estado
Aceptado

## Contexto
Necesitamos un vector store local, gratuito y sin servidor para la POC.

## Decisión
Usamos ChromaDB, detrás de la interfaz `VectorStore`.

## Alternativas consideradas
- FAISS: rápido pero sin persistencia ni metadata nativa cómoda.
- Qdrant: potente pero requiere correr un servidor.

## Consecuencias
+ Setup trivial, persistencia local, metadata integrada.
- Menos escalable que Qdrant; mitigado por la interfaz que permite cambiarlo.
```

ADRs candidatos para este proyecto: elección de vector store, de modelo de
embeddings (multilingüe por el español), de LLM local, y la separación
`genai_toolkit/` vs `domain/`.

## Carpeta `docs/`

```text
docs/
├── architecture/
│   ├── diagrams/        # fuentes de diagramas si no son inline
│   └── adr/             # Architecture Decision Records
├── engineering_skills/  # estas 7 skills
├── installation.md      # guía detallada de instalación
├── usage.md             # guía de uso (más extensa que el README)
└── screenshots/         # imágenes de la demo
```

## Guías de instalación y uso

- **Instalación**: pasos desde un clon limpio hasta el sistema corriendo.
  Incluye prerequisitos (Python 3.11, Ollama instalado, modelo descargado).
  Debe ser **reproducible**: si alguien la sigue al pie de la letra, funciona.
- **Uso**: cómo ingerir documentos, hacer consultas, correr la evaluación,
  interpretar los resultados.

## Limitaciones

Sé explícito y honesto. Para este proyecto, mínimamente:

- No constituye asesoría legal ni migratoria oficial.
- Responde solo con base en los documentos cargados.
- La información puede estar desactualizada respecto a fuentes oficiales.
- Calidad limitada por el modelo local y el corpus disponible.

Declarar limitaciones **fortalece** la credibilidad: muestra que entiendes el
alcance real del sistema.

## Screenshots y demo examples

- Screenshots de la UI con una consulta real, la respuesta, las fuentes y el
  disclaimer visibles.
- 2-3 ejemplos de consultas con sus respuestas en el README — dan una idea
  inmediata de qué hace sin tener que instalarlo.

## Disclaimer legal/de dominio

Texto propuesto para la app y el README:

> **Aviso.** Este asistente es una herramienta informativa basada en documentos
> públicos y **no constituye asesoría legal ni migratoria oficial**. Las
> respuestas se generan automáticamente a partir de los documentos cargados y
> pueden ser incompletas o estar desactualizadas. Verifica siempre la
> información con las fuentes oficiales y, para decisiones que afecten tu
> situación migratoria, consulta a un profesional acreditado.

Debe ser **visible en cada respuesta**, no escondido en un pie de página.

## Checklist de la skill

- [ ] README con todas las secciones de la tabla
- [ ] Al menos un diagrama Mermaid de arquitectura
- [ ] ADRs para las decisiones no obvias
- [ ] `docs/` organizada (architecture, skills, guías, screenshots)
- [ ] Guía de instalación reproducible desde cero
- [ ] Guía de uso con ejemplos
- [ ] Limitaciones declaradas explícitamente
- [ ] Screenshots de la demo funcionando
- [ ] Disclaimer visible en app y README
- [ ] Sección de aprendizajes (decisiones y trade-offs)
