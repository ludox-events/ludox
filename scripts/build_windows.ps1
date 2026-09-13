$ErrorActionPreference = "Stop"

Write-Host "=== LudoX: build Windows con PyInstaller ==="

if (-not (Test-Path ".venv-build")) {
    python -m venv .venv-build
}

& ".\.venv-build\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv-build\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv-build\Scripts\python.exe" -m pip install -r requirements-build.txt

# Pulisce solo gli output di PyInstaller.
if (Test-Path "build\pyinstaller") {
    Remove-Item "build\pyinstaller" -Recurse -Force
}
if (Test-Path "dist\LudoX") {
    Remove-Item "dist\LudoX" -Recurse -Force
}

& ".\.venv-build\Scripts\python.exe" -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onedir `
    --name LudoX `
    --workpath "build\pyinstaller" `
    --distpath "dist" `
    --collect-data ludox `
    app.py

Write-Host ""
Write-Host "Build completata."
Write-Host "Avvia:"
Write-Host "  dist\LudoX\LudoX.exe"
