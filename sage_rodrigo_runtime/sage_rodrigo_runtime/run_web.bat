@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ambiente .venv nao encontrado. Execute setup_venv.bat primeiro.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" web_app.py
if errorlevel 1 (
  echo.
  echo Falha ao executar web_app.py usando .venv.
  pause
)
