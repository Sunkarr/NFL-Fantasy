#!/usr/bin/env bash
# Quick helper to open interactive GoAccess terminal dashboard
sudo docker exec -it nfl-fantasy-goaccess goaccess /srv/logs/access.log --log-format=CADDY
