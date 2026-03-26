#!/usr/bin/env bash
# Start the Clarvia automation orchestrator in the background.
# Checks for an existing instance, loads env vars, and daemonizes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="$PROJECT_ROOT/data"
PID_FILE="$DATA_DIR/orchestrator.pid"
LOG_FILE="$DATA_DIR/automation.log"
ENV_FILE="$PROJECT_ROOT/.env"

mkdir -p "$DATA_DIR"

# --- Check if already running ------------------------------------------------
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "[OK] Orchestrator already running (PID $OLD_PID)"
        exit 0
    else
        echo "[WARN] Stale PID file found (PID $OLD_PID not alive) — removing"
        rm -f "$PID_FILE"
    fi
fi

# --- Load environment variables from .env if present -------------------------
if [ -f "$ENV_FILE" ]; then
    echo "[INFO] Loading env vars from $ENV_FILE"
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

# --- Start orchestrator in background ----------------------------------------
echo "[INFO] Starting orchestrator..."
cd "$PROJECT_ROOT"

nohup python3 scripts/automation/orchestrator.py --tick 30 >> "$LOG_FILE" 2>&1 &
NEW_PID=$!

echo "$NEW_PID" > "$PID_FILE"
echo "[OK] Orchestrator started (PID $NEW_PID)"
echo "     Log: $LOG_FILE"
echo "     PID file: $PID_FILE"

# Give it a moment and verify it's still alive
sleep 2
if kill -0 "$NEW_PID" 2>/dev/null; then
    echo "[OK] Process confirmed alive"
else
    echo "[ERROR] Process died immediately — check $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi
