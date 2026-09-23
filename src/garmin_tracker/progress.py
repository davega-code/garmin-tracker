from __future__ import annotations

from dataclasses import dataclass
from typing import Any


OVERLOAD_REPS = 9
OVERLOAD_SESSIONS = 2
KG_PER_LB = 1 / 2.2046226218


@dataclass(frozen=True)
class ProgressRecommendation:
    exercise: str
    current_weight_kg: float
    target_weight_kg: float
    reps: int
    sessions: int


def recommendations(activities: list[dict[str, Any]], unit: str = "kg") -> list[ProgressRecommendation]:
    history = _exercise_history(activities)
    ready = [rec for points in history.values() if (rec := _recommendation(points, unit))]
    return sorted(ready, key=lambda rec: rec.exercise)


def _exercise_history(activities: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    history: dict[str, list[dict[str, Any]]] = {}
    workouts = sorted(
        (a for a in activities if a.get("kind", "strength") == "strength"),
        key=lambda a: a.get("startTimeLocal", ""),
    )
    for workout in workouts:
        best: dict[str, dict[str, Any]] = {}
        for set_item in workout.get("sets", []):
            exercise = set_item.get("exercise")
            weight = float(set_item.get("weight") or 0)
            reps = int(set_item.get("reps") or 0)
            if not exercise or weight <= 0 or reps <= 0:
                continue
            current = best.get(exercise)
            if not current or weight > current["weight"]:
                best[exercise] = {"exercise": exercise, "weight": weight, "reps": reps}
        for exercise, point in best.items():
            history.setdefault(exercise, []).append(point)
    return history


def _recommendation(points: list[dict[str, Any]], unit: str) -> ProgressRecommendation | None:
    if len(points) < OVERLOAD_SESSIONS:
        return None
    current = points[-1]["weight"]
    recent = []
    for point in reversed(points):
        if point["weight"] != current:
            break
        recent.append(point)
    ready = recent[:OVERLOAD_SESSIONS]
    if len(ready) < OVERLOAD_SESSIONS or any(point["reps"] < OVERLOAD_REPS for point in ready):
        return None
    target = _display_target_kg(current, unit)
    return ProgressRecommendation(
        exercise=str(points[-1]["exercise"]),
        current_weight_kg=current,
        target_weight_kg=target,
        reps=min(point["reps"] for point in ready),
        sessions=len(ready),
    )


def _display_target_kg(current_weight_kg: float, unit: str) -> float:
    if unit == "lb":
        current_lb = current_weight_kg / KG_PER_LB
        step = 10 if current_lb >= 100 else 5
        return (round(current_lb, 1) + step) * KG_PER_LB
    step = 5 if current_weight_kg >= 45 else 2.5
    return round(current_weight_kg, 1) + step
