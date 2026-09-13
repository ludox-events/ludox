$ErrorActionPreference = "Stop"

Write-Host "=== LudoX: build Windows con PyInstaller ==="

if (-not (Test-Path ".venv-build")) {
    python -m venv .venv-build
}

& ".\.venv-build\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv-build\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv-build\Scripts\python.exe" -m pip install -r requirements-build.txt

& ".\.venv-build\Scripts\python.exe" -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onedir `
    --name LudoX `
    --workpath "build\windows\pyinstaller" `
    --distpath "build\windows" `
    --specpath "build\windows" `
    --collect-data ludox `
    app.py

Write-Host ""
Write-Host "Build completata."
Write-Host "Avvia:"
Write-Host "  build\windows\LudoX\LudoX.exe"
