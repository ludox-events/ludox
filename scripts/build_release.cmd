@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0\.."

echo [1/3] PDF
call scripts\build_pdf.cmd
if errorlevel 1 exit /b 1

echo [2/3] Windows ZIP
call scripts\build_windows.cmd
if errorlevel 1 exit /b 1

echo [3/3] Linux tar.gz via WSL
for /f "delims=" %%i in ('wsl wslpath "%CD%"') do set WSL_REPO=%%i

if "!WSL_REPO!"=="" (
  echo ERRORE: percorso WSL non determinato.
  exit /b 1
)

wsl bash -lc "cd '!WSL_REPO!' && bash scripts/build_linux.sh"
if errorlevel 1 exit /b 1

echo.
echo BUILD COMPLETA:
echo   dist\LudoX-Guida-rapida.pdf
echo   dist\LudoX-*-windows-x64.zip
echo   dist-linux\LudoX-*-linux-x64.tar.gz
