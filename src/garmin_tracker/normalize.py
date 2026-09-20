from __future__ import annotations

from typing import Any


def strength_activity(activity_summary: dict[str, Any], exercise_sets: dict[str, Any]) -> dict[str, Any]:
    sets = _sets(exercise_sets)
    return {
        "kind": "strength",
        "activityId": activity_summary["activityId"],
        "activityName": activity_summary.get("activityName"),
        "activityType": (activity_summary.get("activityType") or {}).get("typeKey"),
        "startTimeLocal": activity_summary.get("startTimeLocal") or activity_summary.get("startTimeGMT"),
        "durationSeconds": activity_summary.get("duration"),
        "sets": sets,
        "totalVolume": sum((s.get("weight") or 0) * (s.get("reps") or 0) for s in sets),
    }


def running_activity(activity_summary: dict[str, Any], details: dict[str, Any] | None) -> dict[str, Any]:
    distance = activity_summary.get("distance") or 0
    avg_speed = activity_summary.get("averageSpeed") or 0
    return {
        "kind": "running",
        "activityId": activity_summary["activityId"],
        "activityName": activity_summary.get("activityName"),
        "activityType": (activity_summary.get("activityType") or {}).get("typeKey"),
        "startTimeLocal": activity_summary.get("startTimeLocal") or activity_summary.get("startTimeGMT"),
        "durationSeconds": activity_summary.get("duration"),
        "distanceKm": distance / 1000,
        # Garmin reports average speed in m/s; pace is more legible as seconds per km.
        "avgPaceSecPerKm": (1000 / avg_speed) if avg_speed else None,
        "elevationGainM": activity_summary.get("elevationGain"),
        "avgHR": activity_summary.get("averageHR"),
        "maxHR": activity_summary.get("maxHR"),
        "cadence": activity_summary.get("averageRunningCadenceInStepsPerMinute"),
        "calories": activity_summary.get("calories"),
        "route": _route(details),
    }


def _route(details: dict[str, Any] | None) -> list[dict[str, float]]:
    if not details:
        return []
    points = (details.get("geoPolylineDTO") or {}).get("polyline") or []
    return [{"lat": p["lat"], "lon": p["lon"]} for p in points if p.get("lat") is not None and p.get("lon") is not None]


def _sets(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for raw in _raw_sets(payload):
        exercise = _primary_exercise(raw)
        weight = raw.get("weight")
        result.append(
            {
                "exercise": exercise.get("name") if exercise else None,
                "reps": raw.get("repetitionCount"),
                # Garmin reports set weight in grams; normalize to kilograms.
                "weight": weight / 1000 if weight else weight,
            }
        )
    return result


def _raw_sets(payload: dict[str, Any]) -> list[dict[str, Any]]:
    # Garmin interleaves rest intervals with worked sets in the same list;
    # rests carry no reps/weight/exercise and would otherwise show as "Unknown".
    for key in ("exerciseSets", "sets", "activityExerciseSets"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict) and item.get("setType") != "REST"]
    return []


def _primary_exercise(raw: dict[str, Any]) -> dict[str, Any] | None:
    # Each set carries a ranked list of ML-guessed exercise candidates;
    # the first entry is the highest-probability match.
    candidates = raw.get("exercises")
    if isinstance(candidates, list) and candidates and isinstance(candidates[0], dict):
        return candidates[0]
    return None

