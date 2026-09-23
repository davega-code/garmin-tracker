from __future__ import annotations

from collections.abc import Iterator
from typing import Any


WEIGHT_UNIT_KILOGRAM = {"unitId": 8, "unitKey": "kilogram", "factor": 1000.0}


def update_strength_target(workout: dict[str, Any], exercise_name: str, target_weight_kg: float) -> int:
    matches = 0
    wanted = _normalized(exercise_name)
    for step in _steps(workout):
        names = [step.get("exerciseName"), step.get("category"), step.get("description"), step.get("stepName")]
        if wanted in {_normalized(name) for name in names if name}:
            step["weightValue"] = float(target_weight_kg) * 1000
            step["weightUnit"] = dict(WEIGHT_UNIT_KILOGRAM)
            matches += 1
    return matches


def _steps(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        if "stepType" in value:
            yield value
        for child in value.values():
            yield from _steps(child)
    elif isinstance(value, list):
        for child in value:
            yield from _steps(child)


def _normalized(value: Any) -> str:
    return "".join(ch for ch in str(value).lower() if ch.isalnum())

