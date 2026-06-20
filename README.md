# Asesor Migratorio RAG · Mexico Immigration RAG Assistant

> Asistente RAG que responde, en lenguaje natural, consultas sobre documentación
> pública migratoria de México. Construido íntegramente con tecnologías open
> source y modelos locales. Diseñado con un **núcleo de AI Engineering agnóstico
> de dominio** y una **capa fina específica del dominio migratorio**, de modo que
> el sistema pueda reutilizarse en banca, telco, legal o compliance cambiando
> solo la capa de dominio.

> ⚠️ **Estado:** POC en desarrollo · Fase 0 (setup y arquitectura).

---

## Tabla de contenidos

- [Problema que resuelve](#problema-que-resuelve)
- [Arquitectura](#arquitectura)
- [Stack tecnológico](#stack-tecnológico)
- [Instalación](#instalación)
- [Ejecución](#ejecución)
- [Ejemplo de uso](#ejemplo-de-uso)
- [Evaluación](#evaluación)
- [Seguridad](#seguridad)
- [Limitaciones](#limitaciones)
- [Disclaimer](#disclaimer)
- [Roadmap](#roadmap)
- [Aprendizajes](#aprendizajes)
- [Próximos pasos](#próximos-pasos)

---

## Problema que resuelve

La información migratoria pública está dispersa en PDFs, guías y FAQs difíciles
de consultar. Este asistente permite preguntar en lenguaje natural y obtener
respuestas **fundamentadas en los documentos**, con cita de fuente y página, una
señal de confianza, y un disclaimer claro de que no constituye asesoría oficial.

## Arquitectura

> _Diagrama Mermaid pendiente de incorporar (ver `docs/architecture/`)._

El sistema se organiza en capas con dependencias unidireccionales. El núcleo
reutilizable vive en `src/genai_toolkit/`; lo específico del dominio en
`src/domain/`. Ver los Architecture Decision Records en
[`docs/architecture/adr/`](docs/architecture/adr/).

## Stack tecnológico

| Capa | Herramienta |
|------|-------------|
| Lenguaje | Python 3.11 |
| Orquestación RAG | LangChain |
| Vector store | ChromaDB (local) |
| Embeddings | Sentence Transformers (multilingüe) |
| LLM | Ollama (Llama 3.1 / Qwen2.5, local) |
| Interfaz | Streamlit |
| Evaluación | RAGAS + evaluadores propios |
| Calidad | Black · Ruff · mypy · pytest |
| CI/CD | GitHub Actions |

## Instalación

> _Guía detallada en [`docs/installation.md`](docs/installation.md) (pendiente)._

```bash
git clone <repo-url>
cd mexico-immigration-rag
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
cp .env.example .env   # ajusta los valores
```

Prerequisitos: Python 3.11, [Ollama](https://ollama.com) instalado y un modelo
descargado (`ollama pull llama3.1:8b`).

## Ejecución

```bash
python scripts/ingest.py      # ingesta de documentos (pendiente)
streamlit run app/streamlit_app.py   # interfaz (pendiente)
python scripts/evaluate.py    # evaluación RAG (pendiente)
```

## Ejemplo de uso

> _Pendiente: consulta real con su respuesta, fuentes y disclaimer._

## Evaluación

> _Pendiente: tabla de métricas (faithfulness, relevancy, etc.) y umbrales._
> Ver [RAG Evaluation Skill](docs/engineering_skills/05_rag_evaluation.md).

## Seguridad

Mitigaciones contra prompt injection (directo e indirecto desde documentos),
alucinaciones, fuga de datos y documentos maliciosos. Checklist OWASP Top 10 for
LLM Applications. Ver [Security Skill](docs/engineering_skills/04_security.md).

## Limitaciones

- No constituye asesoría legal ni migratoria oficial.
- Responde solo con base en los documentos cargados.
- La información puede estar desactualizada respecto a fuentes oficiales.
- Calidad limitada por el modelo local y el corpus disponible.

## Disclaimer

> **Aviso.** Este asistente es una herramienta informativa basada en documentos
> públicos y **no constituye asesoría legal ni migratoria oficial**. Las
> respuestas se generan automáticamente y pueden ser incompletas o estar
> desactualizadas. Verifica siempre con las fuentes oficiales y, para decisiones
> que afecten tu situación migratoria, consulta a un profesional acreditado.

## Roadmap

| Fase | Objetivo | Estado |
|------|----------|--------|
| 0 | Setup y arquitectura | 🟡 En curso |
| 1 | MVP local RAG | ⚪ Pendiente |
| 2 | UI Streamlit + logging | ⚪ Pendiente |
| 3 | Testing, linting, type checking | ⚪ Pendiente |
| 4 | Evaluación RAG | ⚪ Pendiente |
| 5 | Seguridad + red teaming | ⚪ Pendiente |
| 6 | CI/CD | ⚪ Pendiente |
| 7 | Dockerización | ⚪ Pendiente |
| 8 | API FastAPI | ⚪ Pendiente |
| 9 | Preparación cloud | ⚪ Pendiente |

## Aprendizajes

> _Se irá completando: decisiones, trade-offs y lecciones del desarrollo._

## Próximos pasos

Definir las interfaces (Protocols) del `genai_toolkit/` y la Configuration Layer.

---

## Guías de ingeniería

Este proyecto sigue 7 skills de ingeniería reutilizables documentadas en
[`docs/engineering_skills/`](docs/engineering_skills/).

## Licencia

Ver [LICENSE](LICENSE).
