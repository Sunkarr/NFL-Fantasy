#!/bin/bash
set -e

echo "🏈 Starting Sleeper Fantasy Football Service..."
echo "🕒 Current Container Time: $(date)"

# Ensure data directory exists
mkdir -p /app/data

# Perform initial sync if SQLite DB is missing or empty
if [ ! -f /app/data/fantasy.db ]; then
    echo "⚡ Initializing database and performing initial Sleeper sync..."
    python -m src.sync --mode full || true
fi

# Configure cron for daily sync (Default: 18:30 CET / Europe/Berlin)
CRON_SCHEDULE="${SYNC_CRON:-30 18 * * *}"
echo "📅 Setting up sync schedule: '${CRON_SCHEDULE}'"

# Write crontab file with environment variables preserved
cat <<EOF > /etc/cron.d/fantasy-sync
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
LEAGUE_ID=${LEAGUE_ID}
TEAM_NAME=${TEAM_NAME}
DATA_DIR=/app/data
${CRON_SCHEDULE} root /usr/local/bin/python -m src.sync >> /app/data/cron.log 2>&1
EOF

chmod 0644 /etc/cron.d/fantasy-sync
crontab /etc/cron.d/fantasy-sync

# Start cron daemon in background
cron

echo "🚀 Starting Marimo Dashboard on port ${PORT:-8501}..."
exec python -m marimo run app.py --host 0.0.0.0 --port "${PORT:-8501}" --no-token
