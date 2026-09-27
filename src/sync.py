import sys
import json
import datetime
import argparse
import threading
import time
from pathlib import Path
from typing import Tuple
import requests
from src.config import DB_PATH, PLAYERS_CACHE_FILE, DEFAULT_LEAGUE_ID
from src.db import init_db, get_connection, set_sync_metadata

_scheduler_thread = None
_scheduler_lock = threading.Lock()
_sync_in_progress = threading.RLock()


def sync_players(db_path: Path = DB_PATH, cache_file: Path = PLAYERS_CACHE_FILE, force_refresh: bool = False) -> int:
    """Download and cache Sleeper players database (~5MB) and insert into SQLite."""
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Refresh cache if older than 2 hours (7200s) to keep injury statuses strictly up to date
    cache_ttl_seconds = 7200
    cache_stale = False
    if cache_file.exists():
        try:
            mtime = cache_file.stat().st_mtime
            if (time.time() - mtime) > cache_ttl_seconds:
                cache_stale = True
        except Exception:
            cache_stale = True

    if not cache_file.exists() or force_refresh or cache_stale:
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

    # 1. League metadata
    l_res = requests.get(f"https://api.sleeper.app/v1/league/{league_id}", timeout=10)
    l_res.raise_for_status()
    league_data = l_res.json()
    season = league_data.get("season", "2026")

    # Persist league custom scoring settings to database metadata
    scoring_settings = league_data.get("scoring_settings", {})
    if scoring_settings:
        set_sync_metadata("league_scoring_settings", json.dumps(scoring_settings), db_path=db_path)

    # Fetch NFL active state for dynamic current week
    try:
        st_res = requests.get("https://api.sleeper.app/v1/state/nfl", timeout=5).json()
        current_week = int(st_res.get("display_week") or st_res.get("week") or 1)
    except Exception:
        current_week = int(league_data.get("settings", {}).get("leg", 1))

    # 2. Users (display names & team names)
    u_res = requests.get(f"https://api.sleeper.app/v1/league/{league_id}/users", timeout=10)
    u_res.raise_for_status()
    users_data = u_res.json()
    user_map = {}
    for u in users_data:
        uid = u.get("user_id")
        dname = u.get("display_name")
        tname = u.get("metadata", {}).get("team_name") or dname
        user_map[uid] = (dname, tname)

    # 3. Rosters
    r_res = requests.get(f"https://api.sleeper.app/v1/league/{league_id}/rosters", timeout=10)
    r_res.raise_for_status()
    rosters = r_res.json()

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

    matchup_rows = []
    stats_rows = []

    for w in weeks_to_sync:
        # Matchups
        try:
            m_res = requests.get(f"https://api.sleeper.app/v1/league/{league_id}/matchups/{w}", timeout=10)
            if m_res.status_code == 200:
                matchups = m_res.json()
                for m in matchups:
                    rid = m.get("roster_id")
                    players_pts = m.get("players_points") or {}
                    starters = set(m.get("starters") or [])

                    for pid, pts in players_pts.items():
                        matchup_rows.append((
                            league_id,
                            season,
                            w,
                            rid,
                            str(pid),
                            float(pts) if pts is not None else 0.0,
                            1 if str(pid) in starters else 0,
                            now
                        ))
        except Exception as e:
            print(f"Error fetching matchups for week {w}: {e}")

        # Global NFL Stats
        try:
            s_res = requests.get(f"https://api.sleeper.app/v1/stats/nfl/regular/{season}/{w}", timeout=15)
            if s_res.status_code == 200:
                stats_dict = s_res.json()
                for pid, st in stats_dict.items():
                    stats_rows.append((
                        season,
                        w,
                        str(pid),
                        float(st.get("pts_ppr", st.get("pts_half_ppr", st.get("pts_std", 0.0)))),
                        float(st.get("pass_yd", 0.0)),
                        float(st.get("pass_td", 0.0)),
                        float(st.get("pass_int", 0.0)),
                        float(st.get("rush_yd", 0.0)),
                        float(st.get("rush_td", 0.0)),
                        float(st.get("rec", 0.0)),
                        float(st.get("rec_yd", 0.0)),
                        float(st.get("rec_td", 0.0)),
                        now
                    ))
        except Exception as e:
            print(f"Error fetching stats for week {w}: {e}")

    if matchup_rows:
        cur.executemany('''
            INSERT OR REPLACE INTO weekly_matchup_points
            (league_id, season, week, roster_id, player_id, points, started, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', matchup_rows)

    if stats_rows:
        cur.executemany('''
            INSERT OR REPLACE INTO weekly_nfl_stats
            (season, week, player_id, points, pass_yd, pass_td, pass_int, rush_yd, rush_td, rec, rec_yd, rec_td, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', stats_rows)

    conn.commit()
    conn.close()
    return len(matchup_rows), len(stats_rows)


def run_full_sync(
    league_id: str = DEFAULT_LEAGUE_ID,
    mode: str = "incremental",
    force_players: bool = False,
    db_path: Path = DB_PATH
) -> None:
    """Orchestrate players, league, and weekly stats data download."""
    with _sync_in_progress:
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting sync (mode={mode})...")
        p_count = sync_players(db_path=db_path, force_refresh=force_players)
        print(f"Synced {p_count} players.")

        season, current_week = sync_league_and_rosters(league_id=league_id, db_path=db_path)
        print(f"Synced league & rosters for season {season}, active week {current_week}.")

        m_count, s_count = sync_weekly_data(
            season=season,
            max_week=current_week,
            league_id=league_id,
            mode=mode,
            db_path=db_path
        )
        print(f"Synced {m_count} matchup scores and {s_count} NFL player stats entries.")

        # Proactively refresh current week projections with latest Sleeper estimates
        try:
            from src.optimizer import get_cached_or_live_projections
            get_cached_or_live_projections(season=season, week=current_week, force_refresh=True, db_path=db_path)
            print(f"Synced latest matchup projections for season {season}, week {current_week}.")
        except Exception as pe:
            print(f"[Projections Sync Note]: {pe}")

        set_sync_metadata("last_sync_success", datetime.datetime.now().isoformat(), db_path=db_path)
        print("Data sync completed successfully.")


def _scheduler_worker(league_id: str, db_path: Path):
    """
    Background worker thread running on the exact hour and half-hour (:00 and :30).
    Runs indefinitely without blocking main thread.
    """
    while True:
        try:
            now = datetime.datetime.now()
            minute = now.minute
            second = now.second

            # Target next :00 or :30 boundary
            if minute < 30:
                target_min = 30
            else:
                target_min = 60

            seconds_to_wait = (target_min - minute) * 60 - second
            if seconds_to_wait <= 0:
                seconds_to_wait = 1800  # Fallback: 30 minutes

            time.sleep(seconds_to_wait)
            run_full_sync(league_id=league_id, mode="incremental", db_path=db_path)
        except Exception as e:
            print(f"[Sync Scheduler Error]: {e}", file=sys.stderr)
            time.sleep(60)


def start_background_scheduler(league_id: str = DEFAULT_LEAGUE_ID, db_path: Path = DB_PATH) -> bool:
    """Start persistent background scheduler thread if not already running."""
    global _scheduler_thread
    with _scheduler_lock:
        if _scheduler_thread is None or not _scheduler_thread.is_alive():
            _scheduler_thread = threading.Thread(
                target=_scheduler_worker,
                args=(league_id, db_path),
                daemon=True,
                name="SleeperSyncScheduler"
            )
            _scheduler_thread.start()
            return True
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download NFL Fantasy league data into local SQLite.")
    parser.add_argument("--league-id", default=DEFAULT_LEAGUE_ID, help="Sleeper League ID")
    parser.add_argument("--mode", choices=["full", "incremental"], default="incremental", help="Sync mode")
    parser.add_argument("--force-players", action="store_true", help="Force re-download of players database")
    args = parser.parse_args()

    run_full_sync(
        league_id=args.league_id,
        mode=args.mode,
        force_players=args.force_players
    )
