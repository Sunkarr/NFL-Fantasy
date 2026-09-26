import sys
import json
import datetime
import argparse
from pathlib import Path
from typing import Tuple
import requests
from src.config import DB_PATH, PLAYERS_CACHE_FILE, DEFAULT_LEAGUE_ID
from src.db import init_db, get_connection, set_sync_metadata


def sync_players(db_path: Path = DB_PATH, cache_file: Path = PLAYERS_CACHE_FILE, force_refresh: bool = False) -> int:
    """Download and cache Sleeper players database (~5MB) and insert into SQLite."""
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    if not cache_file.exists() or force_refresh:
        res = requests.get("https://api.sleeper.app/v1/players/nfl", timeout=15)
        res.raise_for_status()
        players_data = res.json()
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(players_data, f)
    else:
        with open(cache_file, "r", encoding="utf-8") as f:
            players_data = json.load(f)

    conn = get_connection(db_path)
    cur = conn.cursor()
    now = datetime.datetime.now().isoformat()

    rows = []
    for pid, p in players_data.items():
        name = p.get("full_name")
        if not name:
            name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
        if not name:
            name = p.get("last_name") or str(pid)

        pos = p.get("position") or (p.get("fantasy_positions") or ["UNK"])[0]
        rows.append((
            str(pid),
            name,
            pos,
            p.get("team") or "FA",
            p.get("status") or "Active",
            p.get("injury_status") or "Healthy",
            p.get("age"),
            p.get("years_exp"),
            now
        ))

    cur.executemany('''
        INSERT OR REPLACE INTO players 
        (player_id, full_name, position, nfl_team, status, injury_status, age, years_exp, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', rows)

    conn.commit()
    conn.close()
    return len(rows)


def sync_league_and_rosters(league_id: str = DEFAULT_LEAGUE_ID, db_path: Path = DB_PATH) -> Tuple[str, int]:
    """Sync league metadata, users, rosters, and current ownership snapshot."""
    init_db(db_path)
    now = datetime.datetime.now().isoformat()

    # Determine season from league info or fallback to global NFL state
    league_info = requests.get(f"https://api.sleeper.app/v1/league/{league_id}", timeout=10).json()
    season = str(league_info.get("season", "")) if league_info and "season" in league_info else ""

    state = requests.get("https://api.sleeper.app/v1/state/nfl", timeout=10).json()
    if not season:
        season = str(state.get("season", "2026"))
    current_week = state.get("display_week", state.get("week", 1))

    users = requests.get(f"https://api.sleeper.app/v1/league/{league_id}/users", timeout=10).json()
    rosters = requests.get(f"https://api.sleeper.app/v1/league/{league_id}/rosters", timeout=10).json()

    user_map = {}
    for u in users:
        uid = u.get("user_id")
        dname = u.get("display_name", "")
        tname = u.get("metadata", {}).get("team_name") or dname
        user_map[uid] = (dname, tname)

    conn = get_connection(db_path)
    cur = conn.cursor()

    team_rows = []
    roster_rows = []

    cur.execute("DELETE FROM current_rosters WHERE league_id = ?", (league_id,))

    for r in rosters:
        rid = r.get("roster_id")
        oid = r.get("owner_id")
        dname, tname = user_map.get(oid, (f"Owner {rid}", f"Team {rid}"))
        wins = r.get("settings", {}).get("wins", 0)
        losses = r.get("settings", {}).get("losses", 0)
        fpts = r.get("settings", {}).get("fpts", 0) + (r.get("settings", {}).get("fpts_decimal", 0) / 100.0)
        fpts_against = r.get("settings", {}).get("fpts_against", 0) + (r.get("settings", {}).get("fpts_against_decimal", 0) / 100.0)

        team_rows.append((rid, league_id, oid, tname, dname, wins, losses, fpts, fpts_against, now))

        starters = set(r.get("starters") or [])
        for pid in (r.get("players") or []):
            roster_rows.append((league_id, rid, str(pid), 1 if str(pid) in starters else 0, now))

    cur.executemany('''
        INSERT OR REPLACE INTO teams 
        (roster_id, league_id, owner_id, team_name, owner_name, wins, losses, fpts, fpts_against, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', team_rows)

    cur.executemany('''
        INSERT OR REPLACE INTO current_rosters 
        (league_id, roster_id, player_id, is_starter, updated_at)
        VALUES (?, ?, ?, ?, ?)
    ''', roster_rows)

    conn.commit()
    conn.close()
    return season, current_week


def sync_weekly_data(
    season: str,
    max_week: int,
    league_id: str = DEFAULT_LEAGUE_ID,
    mode: str = "incremental",
    db_path: Path = DB_PATH
) -> Tuple[int, int]:
    """Sync matchup points and global NFL stats (incremental or full)."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    now = datetime.datetime.now().isoformat()

    cur.execute("SELECT DISTINCT week FROM weekly_matchup_points WHERE league_id = ? AND season = ?", (league_id, season))
    existing_weeks = {row[0] for row in cur.fetchall()}

    if mode == "incremental":
        all_possible = set(range(1, max_week + 1))
        weeks_to_sync = sorted(list((all_possible - existing_weeks) | {max_week}))
    else:
        weeks_to_sync = list(range(1, max_week + 1))

    if not weeks_to_sync:
        conn.close()
        return 0, 0

    matchup_entries = []
    stats_entries = []

    for w in weeks_to_sync:
        m_res = requests.get(f"https://api.sleeper.app/v1/league/{league_id}/matchups/{w}", timeout=10)
        if m_res.status_code == 200:
            m_data = m_res.json()
            for m in m_data:
                rid = m.get("roster_id")
                starters = set(m.get("starters") or [])
                pts_map = m.get("players_points") or {}
                for pid, pts in pts_map.items():
                    matchup_entries.append((
                        league_id, season, w, rid, str(pid), float(pts), 1 if str(pid) in starters else 0, now
                    ))

        s_res = requests.get(f"https://api.sleeper.app/v1/stats/nfl/regular/{season}/{w}", timeout=10)
        if s_res.status_code == 200:
            s_data = s_res.json()
            for pid, s in s_data.items():
                if str(pid).startswith("TEAM_"):
                    continue
                pts = s.get("pts_ppr", s.get("pts_half_ppr", s.get("pts_std", 0.0)))
                stats_entries.append((
                    season, w, str(pid),
                    float(pts) if pts is not None else 0.0,
                    s.get("pass_yd", 0.0), s.get("pass_td", 0.0), s.get("pass_int", 0.0),
                    s.get("rush_yd", 0.0), s.get("rush_td", 0.0),
                    s.get("rec", 0.0), s.get("rec_yd", 0.0), s.get("rec_td", 0.0),
                    now
                ))

    cur.executemany('''
        INSERT OR REPLACE INTO weekly_matchup_points 
        (league_id, season, week, roster_id, player_id, points, started, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', matchup_entries)

    cur.executemany('''
        INSERT OR REPLACE INTO weekly_nfl_stats 
        (season, week, player_id, points, pass_yd, pass_td, pass_int, rush_yd, rush_td, rec, rec_yd, rec_td, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', stats_entries)

    conn.commit()
    conn.close()
    return len(matchup_entries), len(stats_entries)


def run_full_sync(league_id: str = DEFAULT_LEAGUE_ID, force_refresh_players: bool = False, mode: str = "incremental"):
    """Orchestrate entire sync pipeline."""
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Sleeper sync for league {league_id} (mode: {mode})...")
    init_db()
    num_players = sync_players(force_refresh=force_refresh_players)
    season, current_week = sync_league_and_rosters(league_id=league_id)
    n_matchups, n_stats = sync_weekly_data(season=season, max_week=current_week, league_id=league_id, mode=mode)
    
    # Record last sync timestamp in metadata
    now_iso = datetime.datetime.now().isoformat()
    set_sync_metadata("last_sync", now_iso)

    res = {
        "players": num_players,
        "season": season,
        "current_week": current_week,
        "matchup_points": n_matchups,
        "nfl_stats": n_stats,
        "last_sync": now_iso
    }
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Sync finished successfully: {res}")
    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Sleeper League Data to SQLite")
    parser.add_argument("--league-id", default=DEFAULT_LEAGUE_ID, help="Sleeper League ID")
    parser.add_argument("--mode", default="incremental", choices=["incremental", "full"], help="Sync mode")
    parser.add_argument("--force-players", action="store_true", help="Force re-download of full player database")
    args = parser.parse_args()

    run_full_sync(
        league_id=args.league_id,
        force_refresh_players=args.force_players,
        mode=args.mode
    )
