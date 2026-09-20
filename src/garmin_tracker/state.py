from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from .paths import STATE_PATH


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def last_pulled_at(kind: str) -> datetime | None:
    value = load_state().get(kind, {}).get("lastPulledAt")
    return datetime.fromisoformat(value) if value else None


def mark_pulled(kind: str, now: datetime | None = None) -> None:
    current = load_state()
    current.setdefault(kind, {})["lastPulledAt"] = (now or datetime.now(UTC)).isoformat()
    save_state(current)

