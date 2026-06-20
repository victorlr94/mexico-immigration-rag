@echo off
REM Bootstrap del repositorio Git en Windows: init + ramas main/develop + primer commit.
REM Uso (desde la raiz del proyecto):  scripts\init_repo.bat

IF EXIST ".git" (
  echo Ya existe un repositorio Git aqui. Aborto para no sobrescribir.
  exit /b 1
)

git init
git add .
git commit -m "chore: initial project scaffold (phase 0)"
git branch -M main
git branch develop

echo.
echo Repositorio inicializado.
echo   - main:    rama desplegable
echo   - develop: rama de integracion
echo.
echo Siguiente paso sugerido:
echo   git switch develop
echo   git switch -c feature/tu-feature
