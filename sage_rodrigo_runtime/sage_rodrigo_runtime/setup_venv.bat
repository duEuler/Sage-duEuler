@echo off
setlocal
cd /d "%~dp0"

set "BUNDLED_PYTHON=C:\Users\euler\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
set "PYTHON_SOURCE="

if exist ".venv\Scripts\python.exe" (
  echo Ambiente .venv ja existe.
  ".venv\Scripts\python.exe" --version
  goto install_requirements
)

if not "%SAGE_RODRIGO_PYTHON%"=="" if exist "%SAGE_RODRIGO_PYTHON%" set "PYTHON_SOURCE=%SAGE_RODRIGO_PYTHON%"
if "%PYTHON_SOURCE%"=="" if exist "%BUNDLED_PYTHON%" set "PYTHON_SOURCE=%BUNDLED_PYTHON%"

if "%PYTHON_SOURCE%"=="" (
  echo Nenhum Python local encontrado.
  echo Configure SAGE_RODRIGO_PYTHON apontando para python.exe, ou ajuste BUNDLED_PYTHON neste arquivo.
  pause
  exit /b 1
)

echo Criando .venv com:
echo %PYTHON_SOURCE%
"%PYTHON_SOURCE%" -m venv .venv

if errorlevel 1 (
  echo Falha ao criar .venv.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" --version

:install_requirements
if exist "requirements.txt" (
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Falha ao instalar requirements.txt.
    pause
    exit /b 1
  )
)
echo .venv pronto.
