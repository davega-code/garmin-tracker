from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import DATA_DIR, ensure_dirs


def month_key(start_time: str) -> str:
    return datetime.fromisoformat(start_time[:19]).strftime("%Y-%m")


def _month_path(month: str) -> Path:
    return DATA_DIR / f"{month}.json"


def load_month(month: str) -> list[dict[str, Any]]:
    path = _month_path(month)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_month(month: str, activities: list[dict[str, Any]]) -> None:
    ensure_dirs()
    path = _month_path(month)
    ordered = sorted(activities, key=lambda item: item.get("startTimeLocal", ""))
    path.write_text(json.dumps(ordered, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def upsert_activities(activities: list[dict[str, Any]]) -> int:
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for activity in activities:
        by_month[month_key(activity["startTimeLocal"])].append(activity)

    changed = 0
    for month, incoming in by_month.items():
        existing = {str(item["activityId"]): item for item in load_month(month)}
        before = json.dumps(existing, sort_keys=True)
        for activity in incoming:
            existing[str(activity["activityId"])] = activity
        after = json.dumps(existing, sort_keys=True)
        if before != after:
            changed += len(incoming)
            save_month(month, list(existing.values()))
    return changed


def load_all() -> list[dict[str, Any]]:
    if not DATA_DIR.exists():
        return []
    activities: list[dict[str, Any]] = []
    for path in sorted(DATA_DIR.glob("*.json")):
        activities.extend(json.loads(path.read_text(encoding="utf-8")))
    return sorted(activities, key=lambda item: item.get("startTimeLocal", ""))

