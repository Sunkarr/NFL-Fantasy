#!/bin/bash
set -e

REPO_DIR="/home/azureuser/NFL-Fantasy"
LOG_FILE="/home/azureuser/git-autodeploy.log"

cd "$REPO_DIR"

# Fetch remote changes silently
git fetch origin main > /dev/null 2>&1

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "[$(date)] 🚀 New commit detected! Updating from $LOCAL to $REMOTE..." >> "$LOG_FILE"
    git pull origin main >> "$LOG_FILE" 2>&1
    docker compose restart >> "$LOG_FILE" 2>&1 || docker-compose restart >> "$LOG_FILE" 2>&1
    echo "[$(date)] ✅ Successfully updated and restarted dashboard." >> "$LOG_FILE"
fi
