@echo off
setlocal
cd /d "%~dp0\.."

set "VERSION="
set /p VERSION=<VERSION
set VERSION=%VERSION: =%

if "%VERSION%"=="" (
  echo ERRORE: VERSION vuoto.
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo ERRORE: ambiente .venv non trovato.
  exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

if exist "requirements-build.txt" (
  ".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
) else (
  ".venv\Scripts\python.exe" -m pip install pyinstaller
)
if errorlevel 1 exit /b 1

if not exist "dist\windows" mkdir "dist\windows"
if errorlevel 1 exit /b 1

".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --onedir --name LudoX --collect-data ludox --workpath "build\windows\pyinstaller" --distpath "build\windows" --specpath "build\windows" app.py
if errorlevel 1 exit /b 1

if exist "dist\LudoX-Guida-rapida.pdf" (
  copy /y "dist\LudoX-Guida-rapida.pdf" "build\windows\LudoX\LudoX-Guida-rapida.pdf" >nul
  if errorlevel 1 exit /b 1
)

powershell -NoProfile -Command "Compress-Archive -Path 'build\windows\LudoX\*' -DestinationPath 'dist\windows\LudoX-%VERSION%-windows-x64.zip' -Force"
if errorlevel 1 exit /b 1

echo OK: dist\windows\LudoX-%VERSION%-windows-x64.zip
