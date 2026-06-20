#!/usr/bin/env bash
# Bootstrap del repositorio Git: init + ramas main/develop + primer commit.
# Uso (desde la raíz del proyecto):  bash scripts/init_repo.sh
set -euo pipefail

if [ -d ".git" ]; then
  echo "Ya existe un repositorio Git aquí. Aborto para no sobrescribir."
  exit 1
fi

git init
git add .
git commit -m "chore: initial project scaffold (phase 0)"

# main como rama por defecto
git branch -M main
# develop a partir de main
git branch develop

echo ""
echo "Repositorio inicializado."
echo "  - main:    rama desplegable"
echo "  - develop: rama de integración (estás aquí tras cambiar con: git switch develop)"
echo ""
echo "Siguiente paso sugerido:"
echo "  git switch develop"
echo "  git switch -c feature/<tu-feature>"
