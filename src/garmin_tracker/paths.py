from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
STATE_PATH = ROOT / "state.json"
DASHBOARD_DIR = ROOT / "dashboard"


def token_store() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home() / "AppData" / "Local"
    return root / "garmin-tracker" / "garminconnect"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    token_store().mkdir(parents=True, exist_ok=True)

