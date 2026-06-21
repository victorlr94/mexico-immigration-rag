# Makefile — atajos del proyecto Asesor Migratorio RAG.
#
# Pensado para ejecutarse en un shell POSIX (Linux/macOS/WSL/Git Bash). En
# Windows con PowerShell puro, ejecuta directamente los comandos equivalentes
# que documenta el README (o usa WSL/Git Bash).
#
# Uso: `make help` lista todos los targets.

MODEL ?= llama3.1:8b
SAMPLES := data/samples/*.pdf

.DEFAULT_GOAL := help
.PHONY: help install pull-model ingest run eval test test-all lint format clean demo

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Instala dependencias (runtime + dev) y los hooks de pre-commit
	pip install -r requirements.txt
	pip install -e ".[dev]"
	pre-commit install

pull-model: ## Descarga el modelo LLM local en Ollama (MODEL=llama3.1:8b)
	ollama pull $(MODEL)

ingest: ## Indexa el corpus de muestra (data/samples/*.pdf) en ChromaDB
	python scripts/ingest.py $(SAMPLES)

run: ## Lanza la interfaz Streamlit
	streamlit run app/streamlit_app.py

eval: ## Ejecuta la evaluación RAG (RAGAS + evaluadores propios)
	python scripts/evaluate.py

test: ## Tests rápidos (unit + security; excluye integración)
	pytest -m "not integration and not e2e"

test-all: ## Toda la suite, incluyendo integración (requiere modelo de embeddings)
	pytest

lint: ## Verifica formato y linting (Black + Ruff + mypy del núcleo)
	black --check .
	ruff check .
	mypy src/

format: ## Aplica formato y autofixes (Black + Ruff --fix)
	black .
	ruff check . --fix

clean: ## Borra caches e índice local de ChromaDB
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov chroma_db

demo: install pull-model ingest ## Deja todo listo para el demo, luego: make run
	@echo "Listo. Ahora ejecuta: make run"
