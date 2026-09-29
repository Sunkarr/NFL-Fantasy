#!/bin/sh
set -e

mkdir -p /srv/logs /srv/report

# If access.log doesn't exist or is empty, add a valid starter line so GoAccess starts immediately
if [ ! -s /srv/logs/access.log ]; then
  echo '{"ts": 1727600000.0, "request": {"remote_ip": "127.0.0.1", "method": "GET", "proto": "HTTP/2.0", "host": "nfl-fantasy-jonas.belgiumcentral.cloudapp.azure.com", "uri": "/"}, "status": 200, "size": 100}' >> /srv/logs/access.log
fi

exec goaccess /srv/logs/access.log \
  -o /srv/report/index.html \
  --log-format=CADDY \
  --real-time-html \
  --ws-url=wss://nfl-fantasy-jonas.belgiumcentral.cloudapp.azure.com:443/goaccess-ws \
  --port=7890
