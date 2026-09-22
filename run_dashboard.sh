#!/bin/bash
cd "$(dirname "$0")"

PORT=${PORT:-8501}
HOST=${HOST:-0.0.0.0}

echo "🏈 Starting Sleeper Fantasy Football Marimo Dashboard on http://${HOST}:${PORT}..."

# Clean up previous instance on port if running
PORT_PID=$(lsof -ti :${PORT} 2>/dev/null)
if [ -n "$PORT_PID" ]; then
    echo "Stopping previous instance on port ${PORT} (PID: $PORT_PID)..."
    kill -9 $PORT_PID 2>/dev/null
    sleep 1
fi

# Run Marimo App (accessible across local network)
python3 -m marimo run app.py --host ${HOST} --port ${PORT}
