"""Sanitización de texto compartida entre chunkers (ver Security Skill).

Eliminar caracteres de control antes de indexar mitiga secuencias sospechosas
embebidas en PDFs (prompt injection indirecto). Este módulo centraliza la lógica
para que todas las implementaciones de TextChunker la apliquen de forma idéntica.
"""

from __future__ import annotations

import re

# Caracteres de control ASCII excepto \t (0x09) y \n (0x0a).
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_text(text: str) -> str:
    """Elimina caracteres de control del texto extraído de un PDF."""
    return _CONTROL_RE.sub("", text)
