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

SYNC_CRON=${SYNC_CRON:-"0,30 * * * *"}
echo "📅 Setting up sync schedule (${SYNC_CRON} - every 30 mins: :00 & :30)..."

# Write crontab file with environment variables and working directory preserved
cat <<EOF > /etc/cron.d/fantasy-sync
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
PYTHONPATH=/app
LEAGUE_ID=${LEAGUE_ID}
TEAM_NAME=${TEAM_NAME}
DATA_DIR=/app/data
${SYNC_CRON} root cd /app && /usr/local/bin/python -m src.sync >> /app/data/cron.log 2>&1
EOF

chmod 0644 /etc/cron.d/fantasy-sync

# Start cron daemon in background
cron

echo "🚀 Starting Marimo Dashboard on internal port 8501..."
exec python -m marimo run app.py --host 0.0.0.0 --port 8501 --no-token
