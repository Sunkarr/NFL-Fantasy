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

# Application Version
VERSION = "1.5.0"

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DB_PATH = DATA_DIR / "fantasy.db"
HEADSHOTS_DIR = DATA_DIR / "headshots"
PLAYERS_CACHE_FILE = DATA_DIR / "players.json"

# League Configuration (populated from .env or environment variables)
DEFAULT_LEAGUE_ID = os.getenv("LEAGUE_ID", "")
DEFAULT_TEAM_NAME = os.getenv("TEAM_NAME", "")

# Color Palette for Owners
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
