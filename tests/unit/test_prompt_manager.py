"""Unit tests para RagPromptManager y _build_context_block.

Los tests usan templates simples definidos localmente (no los templates de
dominio) para que sean legibles y no dependan del contenido migratorio.
"""

from __future__ import annotations

import pytest

from genai_toolkit.prompts.base import PromptInputs, PromptTemplateNotFoundError
from genai_toolkit.prompts.rag_prompt_manager import (
    RagPromptManager,
    _build_context_block,
)
from genai_toolkit.retrieval.types import (
    Chunk,
    ChunkMetadata,
    RetrievalResult,
    ScoredChunk,
)

# ---------------------------------------------------------------------------
# Templates de prueba
# ---------------------------------------------------------------------------

_SIMPLE_TEMPLATE = (
    "{domain_instructions}\n<context>\n{context_block}\n</context>\n{question}"
)
_TEMPLATES = {"simple_v1": _SIMPLE_TEMPLATE}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _scored_chunk(
    text: str,
    chunk_id: str = "c0",
    source: str = "doc.pdf",
    page: int | None = 1,
    chunk_index: int = 0,
    score: float = 0.90,
) -> ScoredChunk:
    meta = ChunkMetadata(source_document=source, page=page, chunk_index=chunk_index)
    return ScoredChunk(chunk=Chunk(id=chunk_id, text=text, metadata=meta), score=score)


def _result(chunks: list[ScoredChunk], sufficient: bool = True) -> RetrievalResult:
    return RetrievalResult(
        query="consulta", chunks=chunks, has_sufficient_context=sufficient
    )


def _inputs(
    question: str = "¿Qué documentos necesito?",
    chunks: list[ScoredChunk] | None = None,
    domain_instructions: str = "Instrucción de dominio.",
) -> PromptInputs:
    return PromptInputs(
        question=question,
        retrieval_result=_result(chunks or []),
        domain_instructions=domain_instructions,
    )


@pytest.fixture()
def manager() -> RagPromptManager:
    return RagPromptManager(_TEMPLATES)


# ---------------------------------------------------------------------------
# render — flujo correcto
# ---------------------------------------------------------------------------


class TestRender:
    def test_returns_string(self, manager: RagPromptManager) -> None:
        result = manager.render("simple_v1", _inputs())
        assert isinstance(result, str)

    def test_question_appears_in_prompt(self, manager: RagPromptManager) -> None:
        result = manager.render("simple_v1", _inputs(question="¿Cuál es el plazo?"))
        assert "¿Cuál es el plazo?" in result

    def test_domain_instructions_appear_in_prompt(
        self, manager: RagPromptManager
    ) -> None:
        result = manager.render(
            "simple_v1", _inputs(domain_instructions="Disclaimer legal.")
        )
        assert "Disclaimer legal." in result

    def test_context_block_appears_in_prompt(self, manager: RagPromptManager) -> None:
        chunks = [_scored_chunk("Texto del chunk de prueba.")]
        result = manager.render("simple_v1", _inputs(chunks=chunks))
        assert "Texto del chunk de prueba." in result

    def test_unknown_template_raises_not_found_error(
        self, manager: RagPromptManager
    ) -> None:
        with pytest.raises(PromptTemplateNotFoundError, match="no_existe"):
            manager.render("no_existe", _inputs())

    def test_error_message_lists_available_templates(
        self, manager: RagPromptManager
    ) -> None:
        with pytest.raises(PromptTemplateNotFoundError, match="simple_v1"):
            manager.render("otro", _inputs())

    def test_all_placeholders_replaced(self, manager: RagPromptManager) -> None:
        result = manager.render("simple_v1", _inputs())
        assert "{question}" not in result
        assert "{context_block}" not in result
        assert "{domain_instructions}" not in result

    def test_multiple_templates_selectable_by_id(self) -> None:
        m = RagPromptManager({"t1": "T1:{question}", "t2": "T2:{question}"})
        r1 = m.render("t1", _inputs(question="Q"))
        r2 = m.render("t2", _inputs(question="Q"))
        assert r1.startswith("T1:")
        assert r2.startswith("T2:")


# ---------------------------------------------------------------------------
# _build_context_block
# ---------------------------------------------------------------------------


class TestBuildContextBlock:
    def test_empty_chunks_returns_no_context_marker(self) -> None:
        result = _build_context_block(_result([]))
        assert result == "(sin contexto disponible)"

    def test_single_chunk_includes_source(self) -> None:
        sc = _scored_chunk("contenido", source="ley_migracion.pdf")
        result = _build_context_block(_result([sc]))
        assert "ley_migracion.pdf" in result

    def test_single_chunk_includes_page_when_present(self) -> None:
        sc = _scored_chunk("contenido", page=7)
        result = _build_context_block(_result([sc]))
        assert "Página 7" in result

    def test_single_chunk_omits_page_when_none(self) -> None:
        sc = _scored_chunk("contenido", page=None)
        result = _build_context_block(_result([sc]))
        assert "Página" not in result

    def test_single_chunk_text_included_verbatim(self) -> None:
        texto = "El solicitante deberá presentar forma migratoria FM-2."
        sc = _scored_chunk(texto)
        result = _build_context_block(_result([sc]))
        assert texto in result

    def test_multiple_chunks_all_included(self) -> None:
        chunks = [
            _scored_chunk("Primer chunk.", chunk_id="c1", chunk_index=0),
            _scored_chunk("Segundo chunk.", chunk_id="c2", chunk_index=1),
        ]
        result = _build_context_block(_result(chunks))
        assert "Primer chunk." in result
        assert "Segundo chunk." in result

    def test_multiple_chunks_separated(self) -> None:
        chunks = [
            _scored_chunk("A", chunk_id="c1", chunk_index=0),
            _scored_chunk("B", chunk_id="c2", chunk_index=1),
        ]
        result = _build_context_block(_result(chunks))
        # Los dos chunks aparecen separados (no concatenados directamente)
        assert result.index("A") < result.index("B")
        assert "\n\n" in result

    def test_source_label_format(self) -> None:
        sc = _scored_chunk("texto", source="tramites.pdf", page=3)
        result = _build_context_block(_result([sc]))
        assert "[Fuente: tramites.pdf, Página 3]" in result

    def test_source_label_format_without_page(self) -> None:
        sc = _scored_chunk("texto", source="tramites.pdf", page=None)
        result = _build_context_block(_result([sc]))
        assert "[Fuente: tramites.pdf]" in result


# ---------------------------------------------------------------------------
# Integración: context delimitado en el prompt final
# ---------------------------------------------------------------------------


class TestContextDelimiting:
    def test_context_block_wrapped_in_context_tags(
        self, manager: RagPromptManager
    ) -> None:
        chunks = [_scored_chunk("info importante")]
        result = manager.render("simple_v1", _inputs(chunks=chunks))
        assert "<context>" in result
        assert "</context>" in result

    def test_chunk_text_inside_context_tags(self, manager: RagPromptManager) -> None:
        chunks = [_scored_chunk("dato sensible")]
        result = manager.render("simple_v1", _inputs(chunks=chunks))
        ctx_start = result.index("<context>")
        ctx_end = result.index("</context>")
        assert "dato sensible" in result[ctx_start:ctx_end]
