import subprocess
import time

PI_HOST = "192.168.188.147"
PI_USER = "pi"
PI_PASS = "MarkLukasJonas"

def run_ssh_script(script_text):
    # Write local script
    with open('/tmp/remote_script.sh', 'w') as f:
        f.write(script_text)
    
    # Scp script to pi
    scp_exp = f"""#!/usr/bin/expect -f
set timeout 30
spawn scp -o StrictHostKeyChecking=no /tmp/remote_script.sh {PI_USER}@{PI_HOST}:/tmp/remote_script.sh
expect "*password:*"
send "{PI_PASS}\\r"
expect eof
"""
    with open('/tmp/run_scp.exp', 'w') as f:
        f.write(scp_exp)
    subprocess.run(['expect', '/tmp/run_scp.exp'], check=True)

    # Execute script on pi
    ssh_exp = f"""#!/usr/bin/expect -f
set timeout 180
spawn ssh -o StrictHostKeyChecking=no {PI_USER}@{PI_HOST} "chmod +x /tmp/remote_script.sh && echo '{PI_PASS}' | sudo -S /tmp/remote_script.sh"
expect "*password:*"
send "{PI_PASS}\\r"
expect eof
"""
    with open('/tmp/run_ssh.exp', 'w') as f:
        f.write(ssh_exp)
    res = subprocess.run(['expect', '/tmp/run_ssh.exp'], capture_output=True, text=True)
    return res.stdout

if __name__ == "__main__":
    env_content = open('.env').read()

    remote_commands = f"""#!/usr/bin/env bash
set -e

echo "=== 1. Deploying .env ==="
cat << 'EOF' > /home/pi/NFL-Fantasy/.env
{env_content}
EOF
chown pi:pi /home/pi/NFL-Fantasy/.env

echo "=== 2. Testing Python & Sync ==="
cd /home/pi/NFL-Fantasy
sudo -u pi /home/pi/NFL-Fantasy/.venv/bin/python -m src.sync --mode full

echo "=== 3. Writing systemd service ==="
cat << 'EOF' > /etc/systemd/system/nfl-fantasy.service
[Unit]
Description=Sleeper NFL Fantasy Marimo Dashboard
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/NFL-Fantasy
EnvironmentFile=/home/pi/NFL-Fantasy/.env
ExecStart=/home/pi/NFL-Fantasy/.venv/bin/python -m marimo run app.py --host 0.0.0.0 --port 8501 --no-token
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable nfl-fantasy.service
systemctl restart nfl-fantasy.service

echo "=== 4. Setting Cron Job ==="
CRON_CMD="0 9 * * * cd /home/pi/NFL-Fantasy && .venv/bin/python -m src.sync --mode incremental >> /home/pi/NFL-Fantasy/data/cron.log 2>&1"
(crontab -u pi -l 2>/dev/null | grep -v 'NFL-Fantasy' || true; echo "$CRON_CMD") | crontab -u pi -

echo "=== 5. Nginx Configuration ==="
cat << 'EOF' > /etc/nginx/sites-available/fantasy
server {{
    listen 80;
    listen [::]:80;
    server_name fantasy.local fantasy.home fantasy.lan fantasy;

    location / {{
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \\$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \\$host;
        proxy_set_header X-Real-IP \\$remote_addr;
        proxy_set_header X-Forwarded-For \\$proxy_add_x_forwarded_for;
        proxy_read_timeout 86400;
    }}
}}
EOF

ln -sf /etc/nginx/sites-available/fantasy /etc/nginx/sites-enabled/fantasy
nginx -t
systemctl reload nginx

echo "=== 6. Status check ==="
sleep 2
systemctl status nfl-fantasy.service --no-pager
curl -sI http://127.0.0.1:8501 | head -n 5
"""

    print("Deploying to Raspberry Pi...")
    output = run_ssh_script(remote_commands)
    print(output)
