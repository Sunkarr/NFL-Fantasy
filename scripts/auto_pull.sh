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
    sudo docker compose up -d --remove-orphans >> "$LOG_FILE" 2>&1
    echo "[$(date)] ✅ Code updated and compose services deployed." >> "$LOG_FILE"
fi
