#!/usr/bin/env bash
# Build a standalone sprint_recap binary (Linux).
# Run from the repo root with the venv active.
set -euo pipefail

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found" >&2
    exit 1
fi

echo "--- Installing build dependency ---"
pip install pyinstaller

echo "--- Building binary ---"
pyinstaller \
    --onefile \
    --windowed \
    --name sprint_recap \
    --clean \
    sprint_recap.py

echo "--- Done ---"
echo "Binary is at: dist/sprint_recap"
echo "Copy it next to your .pptx template."
