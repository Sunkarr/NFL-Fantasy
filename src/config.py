import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    # Load .env from project root
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    pass

# Application Version (managed directly in code repository)
VERSION = "1.9.4"

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DB_PATH = DATA_DIR / "fantasy.db"
HEADSHOTS_DIR = DATA_DIR / "headshots"
PLAYERS_CACHE_FILE = DATA_DIR / "players.json"

# League Configuration (populated from .env or environment variables)
DEFAULT_LEAGUE_ID = os.getenv("LEAGUE_ID", "")
DEFAULT_TEAM_NAME = os.getenv("TEAM_NAME", "") or os.getenv("DEFAULT_TEAM_NAME", "")
CURRENT_SEASON = os.getenv("CURRENT_SEASON", "2026")
DEFAULT_LIMIT = int(os.getenv("DEFAULT_LIMIT", 20))

# Sync Schedule Configuration (every 30 minutes on the hour and half-hour)
SYNC_CRON = os.getenv("SYNC_CRON", "0,30 * * * *")
SYNC_INTERVAL_DESC = "Every 30 min (:00, :30)"

# Colors & Visualization
TEAM_PALETTE = [
    '#38bdf8',  # Sky Blue
    '#34d399',  # Emerald Green
    '#f43f5e',  # Rose
    '#a855f7',  # Purple
    '#fb923c',  # Orange
    '#f472b6',  # Pink
    '#2dd4bf',  # Teal
    '#818cf8',  # Indigo
    '#facc15',  # Yellow
    '#4ade80',  # Lime
]

FREE_AGENT_COLOR = '#94a3b8'  # Slate grey

# Database sync metadata keys
METADATA_LAST_SYNC = "last_sync_timestamp"
METADATA_VERSION = "schema_version"
