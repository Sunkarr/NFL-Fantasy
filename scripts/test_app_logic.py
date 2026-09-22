import subprocess

PI_HOST = "192.168.188.147"
PI_USER = "pi"
PI_PASS = "MarkLukasJonas"

def run_ssh_script(script_text):
    with open('/tmp/test_py_script.sh', 'w') as f:
        f.write(script_text)
    
    scp_exp = f"""#!/usr/bin/expect -f
set timeout 30
spawn scp -o StrictHostKeyChecking=no /tmp/test_py_script.sh {PI_USER}@{PI_HOST}:/tmp/test_py_script.sh
expect "*password:*"
send "{PI_PASS}\\r"
expect eof
"""
    with open('/tmp/run_scp.exp', 'w') as f:
        f.write(scp_exp)
    subprocess.run(['expect', '/tmp/run_scp.exp'], check=True)

    ssh_exp = f"""#!/usr/bin/expect -f
set timeout 60
spawn ssh -o StrictHostKeyChecking=no {PI_USER}@{PI_HOST} "chmod +x /tmp/test_py_script.sh && /tmp/test_py_script.sh"
expect "*password:*"
send "{PI_PASS}\\r"
expect eof
"""
    with open('/tmp/run_ssh.exp', 'w') as f:
        f.write(ssh_exp)
    res = subprocess.run(['expect', '/tmp/run_ssh.exp'], capture_output=True, text=True)
    return res.stdout

if __name__ == "__main__":
    script = """#!/usr/bin/env bash
cd /home/pi/NFL-Fantasy
/home/pi/NFL-Fantasy/.venv/bin/python - << 'EOF'
import marimo
import pandas as pd
from src.config import DB_PATH, DEFAULT_LEAGUE_ID
from src.db import load_league_data
from src.stats import compute_player_aggregates, get_league_overview_analytics, get_team_roster_analytics

print("Loading data...")
df_teams, df_rosters, df_matchups, df_stats = load_league_data(DB_PATH, DEFAULT_LEAGUE_ID)
print(f"Teams: {len(df_teams)}, Rosters: {len(df_rosters)}, Stats: {len(df_stats) if df_stats is not None else 0}")
df_p = compute_player_aggregates(df_stats)
print(f"Player aggregates: {len(df_p)}")
an = get_league_overview_analytics(df_teams, df_rosters, df_p)
print(f"Overview: {list(an.keys())}")
t_name = df_teams['team_name'].iloc[0]
t_an = get_team_roster_analytics(t_name, df_rosters, df_p, df_teams)
print(f"Team {t_name}: {list(t_an.keys())}")
print("ALL TESTS PASSED SUCCESSFULLY!")
EOF
"""
    print(run_ssh_script(script))
