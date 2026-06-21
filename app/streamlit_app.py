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


def main() -> None:
    settings = Settings()

    st.set_page_config(
        page_title=settings.app_title,
        page_icon="\U0001f1f2\U0001f1fd",
        layout="centered",
    )

    # ------------------------------------------------------------------ Sidebar
    with st.sidebar:
        st.title("Aviso legal")
        st.warning(DISCLAIMER_ES)
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

    # ------------------------------------------------------------------ Form
    with st.form("question_form", clear_on_submit=False):
        question = st.text_area(
            "Escribe tu pregunta:",
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
            except Exception as exc:
                _render_error(exc)
                return

        _render_response(response)


if __name__ == "__main__":
    main()
