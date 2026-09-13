@echo off
setlocal
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
  echo ERRORE: ambiente .venv non trovato.
  exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements-docs.txt
if errorlevel 1 exit /b 1

".venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 exit /b 1

".venv\Scripts\python.exe" scripts\build_user_guide.py
if errorlevel 1 exit /b 1

if not exist "dist\LudoX-Guida-rapida.pdf" (
  echo ERRORE: PDF non generato.
  exit /b 1
)

echo OK: dist\LudoX-Guida-rapida.pdf
