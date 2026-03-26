#!/usr/bin/env bash
# Stop the Clarvia automation orchestrator gracefully.
# Sends SIGTERM, waits for shutdown, then cleans up the PID file.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="$PROJECT_ROOT/data"
PID_FILE="$DATA_DIR/orchestrator.pid"

GRACEFUL_TIMEOUT=15  # seconds to wait before SIGKILL

if [ ! -f "$PID_FILE" ]; then
    echo "[WARN] No PID file found at $PID_FILE — orchestrator not running?"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ! kill -0 "$PID" 2>/dev/null; then
    echo "[WARN] Process $PID not alive — cleaning up stale PID file"
    rm -f "$PID_FILE"
    exit 0
fi

echo "[INFO] Sending SIGTERM to orchestrator (PID $PID)..."
kill -TERM "$PID"

# Wait for graceful shutdown
ELAPSED=0
while kill -0 "$PID" 2>/dev/null; do
    if [ "$ELAPSED" -ge "$GRACEFUL_TIMEOUT" ]; then
        echo "[WARN] Graceful timeout ($GRACEFUL_TIMEOUT s) exceeded — sending SIGKILL"
        kill -9 "$PID" 2>/dev/null || true
        break
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

rm -f "$PID_FILE"
echo "[OK] Orchestrator stopped (was PID $PID)"
