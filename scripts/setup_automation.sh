#!/usr/bin/env bash
# Clarvia Automation Setup Script
#
# Sets up the Phase 0 survival infrastructure:
#   1. Installs required Python packages
#   2. Creates necessary directories
#   3. Generates config.yaml (if missing)
#   4. Sets up launchd plist (macOS) or systemd service (Linux) for auto-start
#
# Usage:
#   bash scripts/setup_automation.sh          # full setup
#   bash scripts/setup_automation.sh --skip-service  # skip launchd/systemd

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AUTOMATION_DIR="$SCRIPT_DIR/automation"

echo "=== Clarvia Automation Setup ==="
echo "Project root: $PROJECT_ROOT"
echo ""

# -------------------------------------------------------------------
# 1. Install Python dependencies
# -------------------------------------------------------------------
echo ">>> Installing Python dependencies..."
pip3 install --quiet requests pyyaml schedule 2>/dev/null || \
    pip install --quiet requests pyyaml schedule

echo "    Verifying imports..."
python3 -c "import requests; import yaml; print('    OK: requests, pyyaml')"

# -------------------------------------------------------------------
# 2. Create directories
# -------------------------------------------------------------------
echo ""
echo ">>> Creating directories..."
for dir in data backups logs; do
    mkdir -p "$PROJECT_ROOT/$dir"
    echo "    Created: $dir/"
done

mkdir -p "$AUTOMATION_DIR"
echo "    Created: scripts/automation/"

# -------------------------------------------------------------------
# 3. Generate config.yaml if missing
# -------------------------------------------------------------------
CONFIG_PATH="$AUTOMATION_DIR/config.yaml"
if [ ! -f "$CONFIG_PATH" ]; then
    echo ""
    echo ">>> Generating config.yaml template..."
    cat > "$CONFIG_PATH" << 'YAML'
# Clarvia Automation Orchestrator Configuration
tasks:
  - name: "Healthcheck"
    script: "scripts/healthcheck.py"
    schedule: "*/5 * * * *"
    enabled: true
    timeout: 60
    args: []

  - name: "Error Monitor"
    script: "scripts/error_monitor.py"
    schedule: "*/5 * * * *"
    enabled: true
    timeout: 120
    args: ["--source", "auto"]

  - name: "Daily Backup"
    script: "scripts/backup.py"
    schedule: "0 3 * * *"
    enabled: true
    timeout: 300
    args: ["--retain", "7"]
YAML
    echo "    Generated: $CONFIG_PATH"
else
    echo ""
    echo ">>> config.yaml already exists — skipping"
fi

# -------------------------------------------------------------------
# 4. Update .gitignore
# -------------------------------------------------------------------
GITIGNORE="$PROJECT_ROOT/.gitignore"
ENTRIES=("backups/" "data/healthcheck.log" "data/automation.log" "data/error_monitor_state.json" "data/orchestrator_state.json" "logs/")

echo ""
echo ">>> Updating .gitignore..."
for entry in "${ENTRIES[@]}"; do
    if ! grep -qF "$entry" "$GITIGNORE" 2>/dev/null; then
        echo "$entry" >> "$GITIGNORE"
        echo "    Added: $entry"
    fi
done

# -------------------------------------------------------------------
# 5. Set up auto-start (launchd or systemd)
# -------------------------------------------------------------------
SKIP_SERVICE=false
for arg in "$@"; do
    if [ "$arg" = "--skip-service" ]; then
        SKIP_SERVICE=true
    fi
done

if [ "$SKIP_SERVICE" = true ]; then
    echo ""
    echo ">>> Skipping service setup (--skip-service)"
else
    echo ""
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS launchd
        PLIST_NAME="com.clarvia.orchestrator"
        PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"
        PYTHON_PATH=$(which python3)
        ORCHESTRATOR_SCRIPT="$AUTOMATION_DIR/orchestrator.py"

        echo ">>> Setting up macOS launchd agent..."
        cat > "$PLIST_PATH" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON_PATH}</string>
        <string>${ORCHESTRATOR_SCRIPT}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${PROJECT_ROOT}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${PROJECT_ROOT}/logs/orchestrator-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${PROJECT_ROOT}/logs/orchestrator-stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:$(dirname "$PYTHON_PATH")</string>
    </dict>
</dict>
</plist>
PLIST

        echo "    Created: $PLIST_PATH"
        echo ""
        echo "    To start now:"
        echo "      launchctl load $PLIST_PATH"
        echo ""
        echo "    To stop:"
        echo "      launchctl unload $PLIST_PATH"
        echo ""
        echo "    NOTE: Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in the plist"
        echo "          EnvironmentVariables section for alerts to work."

    elif [[ "$(uname)" == "Linux" ]]; then
        # Linux systemd
        SERVICE_NAME="clarvia-orchestrator"
        SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
        PYTHON_PATH=$(which python3)
        ORCHESTRATOR_SCRIPT="$AUTOMATION_DIR/orchestrator.py"

        echo ">>> Setting up Linux systemd service..."
        echo "    NOTE: This requires sudo access"

        sudo tee "$SERVICE_PATH" > /dev/null << SERVICE
[Unit]
Description=Clarvia Automation Orchestrator
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=${PROJECT_ROOT}
ExecStart=${PYTHON_PATH} ${ORCHESTRATOR_SCRIPT}
Restart=always
RestartSec=10
StandardOutput=append:${PROJECT_ROOT}/logs/orchestrator-stdout.log
StandardError=append:${PROJECT_ROOT}/logs/orchestrator-stderr.log

[Install]
WantedBy=multi-user.target
SERVICE

        echo "    Created: $SERVICE_PATH"
        echo ""
        echo "    To enable and start:"
        echo "      sudo systemctl daemon-reload"
        echo "      sudo systemctl enable $SERVICE_NAME"
        echo "      sudo systemctl start $SERVICE_NAME"
    else
        echo ">>> Unsupported OS for auto-start setup: $(uname)"
    fi
fi

# -------------------------------------------------------------------
# 6. Summary
# -------------------------------------------------------------------
echo ""
echo "=== Setup Complete ==="
echo ""
echo "Files created/verified:"
echo "  scripts/telegram_notifier.py  — Telegram integration module"
echo "  scripts/healthcheck.py        — Endpoint monitoring + auto-recovery"
echo "  scripts/error_monitor.py      — Error spike detection + alerts"
echo "  scripts/backup.py             — Daily compressed backups"
echo "  scripts/automation/orchestrator.py — Central task scheduler"
echo "  scripts/automation/config.yaml     — Task schedule configuration"
echo ""
echo "Required environment variables:"
echo "  TELEGRAM_BOT_TOKEN   — Telegram bot token from @BotFather"
echo "  TELEGRAM_CHAT_ID     — Target chat ID for alerts"
echo "  RENDER_API_KEY       — (optional) Render API key for auto-redeploy"
echo "  RENDER_SERVICE_ID    — (optional) Render service ID"
echo ""
echo "Quick test:"
echo "  python3 scripts/telegram_notifier.py --dry-run"
echo "  python3 scripts/healthcheck.py --dry-run"
echo "  python3 scripts/backup.py --dry-run"
echo "  python3 scripts/automation/orchestrator.py --once --dry-run"
