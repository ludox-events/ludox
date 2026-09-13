@echo off
setlocal
cd /d "%~dp0\.."

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

if exist "build\pyinstaller-windows" rmdir /s /q "build\pyinstaller-windows"
if exist "dist\LudoX" rmdir /s /q "dist\LudoX"
if exist "dist\LudoX-%VERSION%-windows-x64.zip" del /q "dist\LudoX-%VERSION%-windows-x64.zip"

".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --onedir --name LudoX --collect-data ludox --workpath "build\pyinstaller-windows" --distpath "dist" app.py
if errorlevel 1 exit /b 1

if exist "dist\LudoX-Guida-rapida.pdf" (
  copy /y "dist\LudoX-Guida-rapida.pdf" "dist\LudoX\LudoX-Guida-rapida.pdf" >nul
)

powershell -NoProfile -Command "Compress-Archive -Path 'dist\LudoX\*' -DestinationPath 'dist\LudoX-%VERSION%-windows-x64.zip' -Force"
if errorlevel 1 exit /b 1

echo OK: dist\LudoX-%VERSION%-windows-x64.zip
