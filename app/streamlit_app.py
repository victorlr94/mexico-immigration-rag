"""Interfaz de usuario Streamlit para el Asesor Migratorio RAG.

Ejecución desde la raíz del proyecto:
    streamlit run app/streamlit_app.py

Esta capa es exclusivamente de presentación: toda la lógica de consulta,
validación y logging vive en RAGService (src/application/rag_service.py).
El RAGService se construye una sola vez por sesión de servidor via
@st.cache_resource para no recargar el modelo de embeddings (~117 MB) en
cada interacción.
"""

from __future__ import annotations

import logging

import streamlit as st
from ollama import Client

from application.rag_service import RAGService
from application.types import RAGResponse, SourceCitation
from domain.prompt_templates import DISCLAIMER_ES, TEMPLATES
from genai_toolkit.config.settings import Settings
from genai_toolkit.embeddings.sentence_transformer_provider import (
    SentenceTransformerProvider,
)
from genai_toolkit.llm.ollama import OllamaProvider
from genai_toolkit.observability.logger import RAGInteractionLogger
from genai_toolkit.prompts.rag_prompt_manager import RagPromptManager
from genai_toolkit.retrieval.simple_retriever import SimpleRetriever
from genai_toolkit.vectorstore.chroma import ChromaVectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s — %(message)s",
)

# Preguntas de muestra ancladas al corpus por defecto (data/samples/): Ley de
# Migración, lineamientos de visas/trámites y Reglamento de la Ley de Nacionalidad.
SUGGESTED_QUESTIONS: list[str] = [
    "¿Cuáles son las condiciones de estancia que reconoce la Ley de Migración?",
    "¿Qué requisitos se piden para tramitar una visa de visitante?",
    "¿Qué derechos tienen las personas migrantes sin importar su situación migratoria?",
    "¿Qué autoridades pueden ejercer funciones de control migratorio?",
]


@st.cache_resource(show_spinner="Cargando modelos de embeddings…")
def _build_service() -> RAGService:
    """Construye el RAGService una sola vez por sesión de servidor Streamlit."""
    settings = Settings()
    embedder = SentenceTransformerProvider(settings)
    store = ChromaVectorStore(settings)
    retriever = SimpleRetriever(embedder, store, settings)
    llm = OllamaProvider(settings)
    prompt_manager = RagPromptManager(TEMPLATES)
    interaction_logger = RAGInteractionLogger(settings)
    return RAGService(
        retriever,
        llm,
        prompt_manager,
        interaction_logger=interaction_logger,
        settings=settings,
    )


@st.cache_resource(show_spinner=False)
def _vector_store() -> ChromaVectorStore:
    """Store ligero (sin modelo de embeddings) para consultar el conteo del índice."""
    return ChromaVectorStore(Settings())


def _index_count() -> int:
    """Número de chunks indexados; 0 si el store no existe o falla."""
    try:
        return _vector_store().count()
    except Exception:  # noqa: BLE001 — la UI nunca debe romperse por el conteo
        return 0


@st.cache_data(ttl=15, show_spinner=False)
def _ollama_status() -> tuple[str, list[str]]:
    """Pre-flight de Ollama. Devuelve (estado, modelos).

    estado ∈ {"ok", "sin_modelo", "caido"}:
      - ok: servidor activo y el modelo configurado está descargado
      - sin_modelo: servidor activo pero falta `ollama pull <modelo>`
      - caido: el servidor no responde
    """
    settings = Settings()
    try:
        client = Client(host=settings.ollama_base_url, timeout=4.0)
        raw = client.list()
    except Exception:  # noqa: BLE001 — cualquier fallo = servidor no disponible
        return "caido", []

    if isinstance(raw, dict):
        models = raw.get("models", [])
    else:
        models = getattr(raw, "models", [])
    names: list[str] = []
    for m in models:
        name = m.get("name") if isinstance(m, dict) else getattr(m, "model", None)
        if name:
            names.append(str(name))

    target = settings.llm_model
    present = any(n == target or n.startswith(f"{target}") for n in names)
    return ("ok" if present else "sin_modelo", names)


def _render_system_status(settings: Settings, index_count: int) -> None:
    """Panel de estado del sistema en el sidebar (índice + Ollama)."""
    st.subheader("Estado del sistema")

    if index_count > 0:
        st.caption(f"📚 Índice: **{index_count:,} fragmentos** indexados")
    else:
        st.caption("📚 Índice: **vacío** — ejecuta la ingesta")

    estado, _ = _ollama_status()
    if estado == "ok":
        st.caption(f"🟢 Ollama activo · modelo `{settings.llm_model}`")
    elif estado == "sin_modelo":
        st.caption(
            f"🟡 Ollama activo, pero falta el modelo. "
            f"Ejecuta:\n```\nollama pull {settings.llm_model}\n```"
        )
    else:
        st.caption(
            "🔴 Ollama no responde. Inícialo con `ollama serve` "
            "y descarga el modelo."
        )


def _render_sources(sources: list[SourceCitation]) -> None:
    if not sources:
        return
    with st.expander("Fuentes consultadas", expanded=True):
        for source in sources:
            page_info = f", página {source.page}" if source.page is not None else ""
            st.markdown(f"- **{source.document}**{page_info}")


def _render_response(response: RAGResponse) -> None:
    if response.has_sufficient_context:
        st.success(
            "Alta confianza — respuesta basada en documentación oficial indexada."
        )
    else:
        st.warning(
            "Contexto insuficiente — no se encontró información relevante "
            "en los documentos indexados."
        )

    st.markdown("### Respuesta")
    st.markdown(response.answer)

    _render_sources(response.sources)
    st.caption(f"Tiempo de respuesta: {response.response_time_ms:.0f} ms")


def _render_error(exc: Exception) -> None:
    msg = str(exc).lower()
    if any(k in msg for k in ("connection", "refused", "connect")):
        st.error(
            "No se pudo conectar con Ollama. "
            "Verifica que el servidor esté activo con `ollama serve` "
            f"y que el modelo `{Settings().llm_model}` esté descargado."
        )
    else:
        st.error(f"Error al procesar la consulta: {exc}")


def _render_empty_index_notice() -> None:
    """Aviso accionable cuando no hay nada indexado (primer arranque tras clonar)."""
    st.info(
        "**Aún no hay documentos indexados.**\n\n"
        "Para ver el asistente en acción, indexa el corpus de muestra incluido "
        "en el repositorio:\n\n"
        "```\npython scripts/ingest.py data/samples/*.pdf\n```\n\n"
        "Luego recarga esta página."
    )


def _set_question(text: str) -> None:
    """Callback de los botones de pregunta sugerida (corre antes del rerun)."""
    st.session_state.question = text


def main() -> None:
    settings = Settings()

    st.set_page_config(
        page_title=settings.app_title,
        page_icon="\U0001f1f2\U0001f1fd",
        layout="centered",
    )

    st.session_state.setdefault("question", "")
    index_count = _index_count()

    # ------------------------------------------------------------------ Sidebar
    with st.sidebar:
        st.title("Aviso legal")
        st.warning(DISCLAIMER_ES)
        st.divider()
        _render_system_status(settings, index_count)
        st.divider()
        st.caption(f"**Modelo LLM:** {settings.llm_model}")
        st.caption(f"**Embeddings:** {settings.embedding_model}")
        st.divider()
        st.caption(
            "Para indexar documentos:\n"
            "```\npython scripts/ingest.py archivo.pdf\n```"
        )

    # ------------------------------------------------------------------ Header
    st.title(f"\U0001f1f2\U0001f1fd {settings.app_title}")
    st.caption(
        "Responde preguntas sobre trámites migratorios en México "
        "con base en documentación oficial indexada localmente."
    )

    # --------------------------------------------------------------- Sin índice
    if index_count == 0:
        _render_empty_index_notice()
        return

    # ------------------------------------------------------- Preguntas sugeridas
    st.markdown("**Prueba con una pregunta de ejemplo:**")
    cols = st.columns(2)
    for i, suggestion in enumerate(SUGGESTED_QUESTIONS):
        cols[i % 2].button(
            suggestion,
            key=f"suggestion_{i}",
            on_click=_set_question,
            args=(suggestion,),
            use_container_width=True,
        )

    # ------------------------------------------------------------------ Form
    with st.form("question_form", clear_on_submit=False):
        question = st.text_area(
            "Escribe tu pregunta:",
            key="question",
            max_chars=settings.max_input_chars,
            height=110,
            placeholder=(
                "¿Cuáles son los requisitos para tramitar "
                "una visa de estudiante en México?"
            ),
        )
        submitted = st.form_submit_button(
            "Consultar",
            type="primary",
            use_container_width=True,
        )

    # ---------------------------------------------------------------- Process
    if submitted:
        if not question or not question.strip():
            st.warning("Escribe una pregunta antes de consultar.")
            return

        with st.spinner("Buscando en la documentación…"):
            try:
                service = _build_service()
                response = service.ask(question)
            except ValueError as exc:
                st.error(f"Pregunta no válida: {exc}")
                return
            except Exception as exc:  # noqa: BLE001 — se traduce a mensaje de UI
                _render_error(exc)
                return

        _render_response(response)


if __name__ == "__main__":
    main()
