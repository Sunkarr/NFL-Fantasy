import sqlite3
import datetime
from pathlib import Path
from typing import Tuple, Optional
import pandas as pd
from src.config import DB_PATH, DEFAULT_LEAGUE_ID


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    return sqlite3.connect(str(db_path))


def init_db(db_path: Path = DB_PATH):
    """Create SQLite tables if they do not exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS players (
            player_id TEXT PRIMARY KEY,
            full_name TEXT,
            position TEXT,
            nfl_team TEXT,
            status TEXT,
            injury_status TEXT,
            age INTEGER,
            years_exp INTEGER,
            updated_at TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            roster_id INTEGER,
            league_id TEXT,
            owner_id TEXT,
            team_name TEXT,
            owner_name TEXT,
            wins INTEGER,
            losses INTEGER,
            fpts REAL,
            fpts_against REAL DEFAULT 0.0,
            updated_at TIMESTAMP,
            PRIMARY KEY (roster_id, league_id)
        )
    ''')

    # Ensure fpts_against exists if table was previously created
    cur.execute("PRAGMA table_info(teams);")
    cols = [c[1] for c in cur.fetchall()]
    if 'fpts_against' not in cols:
        cur.execute("ALTER TABLE teams ADD COLUMN fpts_against REAL DEFAULT 0.0;")

    cur.execute('''
        CREATE TABLE IF NOT EXISTS current_rosters (
            league_id TEXT,
            roster_id INTEGER,
            player_id TEXT,
            is_starter INTEGER,
            updated_at TIMESTAMP,
            PRIMARY KEY (league_id, roster_id, player_id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS weekly_matchup_points (
            league_id TEXT,
            season TEXT,
            week INTEGER,
            roster_id INTEGER,
            player_id TEXT,
            points REAL,
            started INTEGER,
            updated_at TIMESTAMP,
            PRIMARY KEY (league_id, season, week, roster_id, player_id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS weekly_nfl_stats (
            season TEXT,
            week INTEGER,
            player_id TEXT,
            points REAL,
            pass_yd REAL,
            pass_td REAL,
            pass_int REAL,
            rush_yd REAL,
            rush_td REAL,
            rec REAL,
            rec_yd REAL,
            rec_td REAL,
            updated_at TIMESTAMP,
            PRIMARY KEY (season, week, player_id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS sync_metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    conn.commit()
    conn.close()


def set_sync_metadata(key: str, value: str, db_path: Path = DB_PATH) -> None:
    """Set or update key-value pair in sync_metadata table."""
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO sync_metadata (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def get_sync_metadata(key: str, db_path: Path = DB_PATH) -> Optional[str]:
    """Retrieve value for key from sync_metadata table, or None if table or key doesn't exist."""
    if not db_path.exists():
        return None
    try:
        conn = get_connection(db_path)
        cur = conn.cursor()
        cur.execute("SELECT value FROM sync_metadata WHERE key = ?", (key,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except sqlite3.OperationalError:
        return None


def get_last_sync_time(db_path: Path = DB_PATH) -> Optional[datetime.datetime]:
    """
    Retrieve the timestamp of the last data sync.
    Checks:
    1. sync_metadata table ('last_sync')
    2. MAX(updated_at) across teams/current_rosters
    3. File modification timestamp of fantasy.db
    """
    if not db_path.exists():
        return None

    # 1. Try sync_metadata
    val = get_sync_metadata("last_sync", db_path)
    if val:
        try:
            return datetime.datetime.fromisoformat(val)
        except Exception:
            pass

    # 2. Try MAX(updated_at) from teams or current_rosters
    try:
        conn = get_connection(db_path)
        cur = conn.cursor()
        cur.execute("SELECT MAX(updated_at) FROM teams")
        row = cur.fetchone()
        if not row or not row[0]:
            cur.execute("SELECT MAX(updated_at) FROM current_rosters")
            row = cur.fetchone()
        conn.close()
        if row and row[0]:
            try:
                return datetime.datetime.fromisoformat(row[0])
            except Exception:
                pass
    except Exception:
        pass

    # 3. Fallback to file mtime
    try:
        mtime = db_path.stat().st_mtime
        return datetime.datetime.fromtimestamp(mtime)
    except Exception:
        return None


def format_last_sync(dt: Optional[datetime.datetime]) -> str:
    """Format last sync datetime into a concise human-friendly string for UI display."""
    if not dt:
        return "N/A"

    now = datetime.datetime.now()
    if dt.date() == now.date():
        return dt.strftime("%H:%M")
    elif (now.date() - dt.date()).days == 1:
        return f"Yesterday, {dt.strftime('%H:%M')}"
    elif dt.year == now.year:
        return dt.strftime("%d.%m. %H:%M")
    else:
        return dt.strftime("%d.%m.%Y %H:%M")


def get_active_season(db_path: Path = DB_PATH, league_id: str = DEFAULT_LEAGUE_ID) -> Optional[str]:
    """Retrieve the most recent active season from matchup or stats data."""
    if not db_path.exists():
        return None
    conn = get_connection(db_path)
    cur = conn.cursor()
    
    cur.execute("SELECT MAX(season) FROM weekly_matchup_points WHERE league_id = ?", (league_id,))
    row = cur.fetchone()
    season = row[0] if row and row[0] else None

    if not season:
        cur.execute("SELECT MAX(season) FROM weekly_nfl_stats")
        row = cur.fetchone()
        season = row[0] if row and row[0] else None

    conn.close()
    return season


def get_available_seasons(db_path: Path = DB_PATH, league_id: str = DEFAULT_LEAGUE_ID) -> list[str]:
    """Retrieve all available seasons stored in the database for the given league."""
    if not db_path.exists():
        return []
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT season FROM weekly_matchup_points WHERE league_id = ? ORDER BY season DESC", (league_id,))
    seasons = [row[0] for row in cur.fetchall() if row[0]]
    if not seasons:
        cur.execute("SELECT DISTINCT season FROM weekly_nfl_stats ORDER BY season DESC")
        seasons = [row[0] for row in cur.fetchall() if row[0]]
    conn.close()
    return seasons


def load_league_data(
    db_path: Path = DB_PATH,
    league_id: str = DEFAULT_LEAGUE_ID,
    season: Optional[str] = None
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Load core relational datasets for dashboards.
    Filters weekly stats and matchup points to the specified (or most recent active) season
    to ensure multi-year separation.
    """
    if not db_path.exists():
        return None, None, None, None

    conn = get_connection(db_path)

    # Detect active season if not provided
    if season is None:
        season = get_active_season(db_path, league_id)

    # 1. Teams
    teams = pd.read_sql_query(
        "SELECT roster_id, team_name, owner_name, wins, losses, fpts, fpts_against FROM teams WHERE league_id = ? ORDER BY wins DESC, fpts DESC",
        conn, params=(league_id,)
    )

    # 2. Current Rosters with player metadata
    rosters = pd.read_sql_query('''
        SELECT r.roster_id, t.team_name, r.player_id, r.is_starter, p.full_name as player_name,
               p.position, p.nfl_team, p.injury_status
        FROM current_rosters r
        JOIN teams t ON r.roster_id = t.roster_id AND r.league_id = t.league_id
        JOIN players p ON r.player_id = p.player_id
        WHERE r.league_id = ?
    ''', conn, params=(league_id,))

    # 3. Matchup Points (filtered strictly to season)
    if season:
        matchups = pd.read_sql_query('''
            SELECT m.season, m.week, m.roster_id, t.team_name, m.player_id, p.full_name as player_name,
                   p.position, p.nfl_team, m.points, m.started
            FROM weekly_matchup_points m
            JOIN teams t ON m.roster_id = t.roster_id AND m.league_id = t.league_id
            JOIN players p ON m.player_id = p.player_id
            WHERE m.league_id = ? AND m.season = ?
        ''', conn, params=(league_id, season))

        # 4. Weekly NFL Stats with player metadata & ownership (filtered strictly to season)
        nfl_stats = pd.read_sql_query('''
            SELECT s.season, s.week, s.player_id, p.full_name as player_name, p.position, p.nfl_team,
                   p.injury_status, COALESCE(t.team_name, 'Free Agent') as current_owner,
                   s.points, s.pass_yd, s.pass_td, s.pass_int, s.rush_yd, s.rush_td, s.rec, s.rec_yd, s.rec_td
            FROM weekly_nfl_stats s
            JOIN players p ON s.player_id = p.player_id
            LEFT JOIN current_rosters r ON s.player_id = r.player_id AND r.league_id = ?
            LEFT JOIN teams t ON r.roster_id = t.roster_id AND r.league_id = t.league_id
            WHERE s.season = ?
        ''', conn, params=(league_id, season))
    else:
        matchups = pd.read_sql_query('''
            SELECT m.season, m.week, m.roster_id, t.team_name, m.player_id, p.full_name as player_name,
                   p.position, p.nfl_team, m.points, m.started
            FROM weekly_matchup_points m
            JOIN teams t ON m.roster_id = t.roster_id AND m.league_id = t.league_id
            JOIN players p ON m.player_id = p.player_id
            WHERE m.league_id = ?
        ''', conn, params=(league_id,))

        nfl_stats = pd.read_sql_query('''
            SELECT s.season, s.week, s.player_id, p.full_name as player_name, p.position, p.nfl_team,
                   p.injury_status, COALESCE(t.team_name, 'Free Agent') as current_owner,
                   s.points, s.pass_yd, s.pass_td, s.pass_int, s.rush_yd, s.rush_td, s.rec, s.rec_yd, s.rec_td
            FROM weekly_nfl_stats s
            JOIN players p ON s.player_id = p.player_id
            LEFT JOIN current_rosters r ON s.player_id = r.player_id AND r.league_id = ?
            LEFT JOIN teams t ON r.roster_id = t.roster_id AND r.league_id = t.league_id
        ''', conn, params=(league_id,))

    conn.close()
    return teams, rosters, matchups, nfl_stats
