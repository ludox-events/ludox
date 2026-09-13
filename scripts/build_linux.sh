#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VERSION="$(tr -d '[:space:]' < VERSION)"
PYTHON=".venv-linux/bin/python"

if [[ -z "$VERSION" ]]; then
  echo "ERRORE: VERSION vuoto."
  exit 1
fi

if [[ ! -x "$PYTHON" ]]; then
  echo "ERRORE: .venv-linux non trovato."
  exit 1
fi

"$PYTHON" -m pip install -r requirements.txt

if [[ -f requirements-build.txt ]]; then
  "$PYTHON" -m pip install -r requirements-build.txt
else
  "$PYTHON" -m pip install pyinstaller
fi

mkdir -p dist/linux

"$PYTHON" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --onedir \
  --name LudoX \
  --collect-data ludox \
  --workpath build/linux/pyinstaller \
  --distpath build/linux \
  --specpath build/linux \
  app.py

if [[ -f dist/LudoX-Guida-rapida.pdf ]]; then
  cp dist/LudoX-Guida-rapida.pdf build/linux/LudoX/LudoX-Guida-rapida.pdf
fi

tar -C build/linux -czf "dist/linux/LudoX-${VERSION}-linux-x64.tar.gz" LudoX

echo "OK: dist/linux/LudoX-${VERSION}-linux-x64.tar.gz"
