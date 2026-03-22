#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "==> Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "==> Installing dependencies..."
pip install -r requirements.txt --quiet

echo "==> Starting Clarvia AEO Scanner on http://0.0.0.0:8000"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
