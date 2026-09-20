from __future__ import annotations

from collections import defaultdict
from typing import Any

from .store import load_all


def summarize() -> str:
    # Old cached records predate the "kind" field and are always strength.
    activities = [a for a in load_all() if a.get("kind", "strength") == "strength"]
    if not activities:
        return "No local workout data yet. Run `garmin-tracker sync` first."

    by_exercise: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for workout in activities:
        for set_item in workout.get("sets", []):
            name = set_item.get("exercise") or "Unknown"
            by_exercise[name].append(set_item)

    lines = [
        f"Workouts: {len(activities)}",
        f"Exercises: {len(by_exercise)}",
        "",
        "Top exercises by total volume:",
    ]
    ranked = []
    for name, sets in by_exercise.items():
        volume = sum((s.get("weight") or 0) * (s.get("reps") or 0) for s in sets)
        max_weight = max((s.get("weight") or 0) for s in sets)
        ranked.append((volume, name, len(sets), max_weight))

    for volume, name, set_count, max_weight in sorted(ranked, reverse=True)[:10]:
        lines.append(f"- {name}: volume={volume:g}, sets={set_count}, max_weight={max_weight:g}")
    return "\n".join(lines)

