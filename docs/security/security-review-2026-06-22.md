# Security Review — Branch `feature/recursive-chunker` → `develop`

**Date:** 2026-06-22
**Reviewer:** Claude Code (automated multi-agent review)
**Scope:** Changes introduced between `develop` and the current branch HEAD (`b21adb3`)
**Files reviewed:** `app/streamlit_app.py`, `src/genai_toolkit/processing/_sanitize.py`, `src/genai_toolkit/processing/recursive_text_chunker.py`, `src/genai_toolkit/processing/sliding_window_chunker.py`, `src/genai_toolkit/llm/ollama.py`, `src/genai_toolkit/config/settings.py`

---

## Result: No confirmed vulnerabilities

The review examined 3 candidate findings and all were rejected after false-positive filtering. No high-confidence (≥ 8/10) exploitable vulnerabilities were identified in this PR.

---

## Candidates Examined (all rejected)

### Candidate 1 — Exception message rendered verbatim in UI
**File:** `app/streamlit_app.py:187`
**Category:** Data Exposure
**Candidate confidence:** 8/10 → **Rejected**

`st.error(f"Error al procesar la consulta: {exc}")` renders the raw exception string to the UI. ChromaDB or pypdf exceptions may include internal file paths (e.g., `sqlite3.OperationalError: unable to open database file /home/prod/chroma_db/chroma.sqlite3`).

**Why rejected:** The application is designed for local/single-user deployment (local Ollama, local ChromaDB SQLite, `streamlit run` from the CLI). There is no multi-tenant or unauthenticated-user threat model. Even if a file path were disclosed, it would not enable privilege escalation or data breach in this environment. This falls under "lack of hardening measures" rather than a concrete exploitable vulnerability. Recommend as a low-severity code-hygiene item: sanitize `str(exc)` to a generic message and route the raw exception to server-side logs only.

---

### Candidate 2 — Filename stored as `source_document` rendered via `st.markdown` without sanitization
**File:** `app/streamlit_app.py:142`, `src/genai_toolkit/ingestion/pdf_loader.py:89`
**Category:** Stored Markdown Injection
**Candidate confidence:** 7/10 → **Rejected**

`PdfLoader` stores `path.name` as `source_document`, which flows to `st.markdown(f"- **{source.document}**{page_info}")`. A crafted filename (e.g., `[label](http://attacker.example/)`) would render as a Markdown link.

**Why rejected:** (1) Streamlit's markdown renderer strips `<script>` and dangerous HTML by default — no JavaScript execution, no XSS. The worst realistic outcome is a rendered hyperlink the user might click (open-redirect-adjacent, excluded per precedents). (2) The only actor who can feed a crafted filename into the pipeline is the operator running `scripts/ingest.py` — a fully trusted, server-local user who already has shell access to the machine. This is not an untrusted-user attack surface.

---

### Candidate 3 — `ollama_base_url` unvalidated, controllable via env var — potential SSRF to arbitrary host
**File:** `src/genai_toolkit/config/settings.py:160`, `src/genai_toolkit/llm/ollama.py:44`
**Category:** SSRF
**Candidate confidence:** 7/10 → **Rejected**

`ollama_base_url` accepts any string from `OLLAMA_BASE_URL` env var with no host/protocol validation and passes it directly to `ollama.Client(host=...)`. In theory, `http://169.254.169.254/` would redirect calls to a cloud metadata endpoint.

**Why rejected:** The only described attack vector is an attacker controlling the environment variable. Per the review's own false-positive filtering rules: *"Environment variables and CLI flags are trusted values. Attackers are generally not able to modify them in a secure environment. Any attack that relies on controlling an environment variable is INVALID."* No alternative injection path (user-supplied input, database-backed config, unauthenticated API endpoint) exists for this value.

---

## Code-Quality Observations (non-security, informational)

These did not meet the security threshold but may be worth addressing:

- **Exception surface area in `_render_error`:** The generic `except Exception` fallback exposes internal exception text to the UI. For defense-in-depth, replace with a generic user-facing message and log the raw exception server-side.
- **`source_document` not sanitized before Markdown rendering:** Even without a real exploit path today, sanitizing filenames (stripping `[]()` characters) before `st.markdown` would eliminate this class of concern if the threat model ever changes (e.g., multi-user deployment).

---

## Conclusion

The changes in this PR (`RecursiveTextChunker`, `_sanitize.py` refactor, LLM temperature/seed fix, Streamlit UX improvements) do not introduce any confirmed exploitable security vulnerabilities. The branch is clear from a security standpoint.
