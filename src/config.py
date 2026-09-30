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

# Application Version (configured in .env)
VERSION = os.getenv("VERSION", "1.8.0")

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DB_PATH = DATA_DIR / "fantasy.db"
HEADSHOTS_DIR = DATA_DIR / "headshots"
PLAYERS_CACHE_FILE = DATA_DIR / "players.json"

# League Configuration (populated from .env or environment variables)
DEFAULT_LEAGUE_ID = os.getenv("LEAGUE_ID", "")
DEFAULT_TEAM_NAME = os.getenv("TEAM_NAME", "")
