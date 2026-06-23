import os
import sys
from pathlib import Path

# Application Directory (resolve AppData for persistent data)
if sys.platform == "win32":
    APP_DATA_DIR = Path(os.environ.get("APPDATA", ".")) / "FileSniffer"
else:
    APP_DATA_DIR = Path.home() / ".filesniffer"

# Create application directory if it doesn't exist
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database file path
DB_PATH = APP_DATA_DIR / "filesniffer.db"

# Settings file path (fallback JSON settings if needed, though we will store them in DB)
SETTINGS_PATH = APP_DATA_DIR / "settings.json"

# Default config settings
DEFAULT_SETTINGS = {
    "oiiotool_path": "oiiotool.exe",  # Assumes it might be on PATH, or user selects it
    "ffmpeg_path": "ffmpeg",          # Default FFmpeg binary name/path
    "settle_time_seconds": 60,       # Default file lock settle time
    "max_threads": 4,                # Parallel copies/conversions
    "poll_interval_seconds": 30,     # Core tick rate of background loop
}

