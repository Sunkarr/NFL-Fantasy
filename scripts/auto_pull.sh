#!/bin/bash
set -e

# Prevent parallel executions (race condition) using a non-blocking flock
LOCK_FILE="/tmp/git-autodeploy.lock"
exec 200>"$LOCK_FILE"
flock -n 200 || exit 0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="/home/azureuser/git-autodeploy.log"

# Fallback log destination if /home/azureuser is not writable
if [ ! -w "$(dirname "$LOG_FILE")" ] 2>/dev/null; then
    LOG_FILE="$REPO_DIR/data/git-autodeploy.log"
fi

cd "$REPO_DIR"

# Silently fetch latest remote changes
git fetch origin main > /dev/null 2>&1 || true

LOCAL=$(git rev-parse HEAD 2>/dev/null || echo "")
REMOTE=$(git rev-parse origin/main 2>/dev/null || echo "")

if [ -n "$REMOTE" ] && [ "$LOCAL" != "$REMOTE" ]; then
    echo "[$(date)] 🚀 New commit detected! Updating from $LOCAL to $REMOTE..." >> "$LOG_FILE"

    # Robust hard sync to origin/main:
    # Completely prevents divergent branches, dirty file conflicts, or failed fast-forwards
    git reset --hard origin/main >> "$LOG_FILE" 2>&1

    # Reload Docker Compose containers and restart the dashboard process
    # Note: 'up -d' ensures services/ports are healthy, while 'restart fantasy-dashboard'
    # forces Python in memory to reload mounted code changes immediately.
    if command -v docker >/dev/null 2>&1; then
        sudo docker compose up -d --remove-orphans >> "$LOG_FILE" 2>&1
        sudo docker compose restart fantasy-dashboard >> "$LOG_FILE" 2>&1
    fi

    echo "[$(date)] ✅ Code updated and dashboard restarted." >> "$LOG_FILE"
fi
