$ErrorActionPreference = "Stop"

Write-Host "=== LudoX: generazione PDF guida ==="

python -m pip install -r requirements-docs.txt
python -m playwright install chromium
python scripts/build_user_guide.py

Write-Host ""
Write-Host "Output:"
Write-Host "  dist\LudoX-Guida-rapida.pdf"
