"""Central config — reads from .env or environment variables."""
import os
from pathlib import Path

# Load .env if present
_env = Path(__file__).parent / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

GROQ_API_KEY   = os.environ["GROQ_API_KEY"]
SUPABASE_URL   = os.environ["SUPABASE_URL"]
SUPABASE_KEY   = os.environ["SUPABASE_KEY"]
GARMIN_EMAIL   = os.environ["GARMIN_EMAIL"]
GARMIN_PASSWORD = os.environ["GARMIN_PASSWORD"]
TOKEN_PATH     = os.path.expanduser("~/.garmin_tokens/session.json")
DATA_PATH      = os.path.join(os.path.expanduser("~"), "OneDrive", "garmin-data", "latest_data.json")
