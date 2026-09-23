from __future__ import annotations

import getpass
import logging
from datetime import date, datetime
from typing import Any

from garminconnect import Garmin

from .paths import ensure_dirs, token_store
from .workout_targets import update_strength_target


logging.getLogger("garminconnect").setLevel(logging.WARNING)


def login(require_credentials: bool = False) -> Garmin:
    ensure_dirs()
    token_path = str(token_store())

    if not require_credentials:
        try:
            client = Garmin()
            client.login(token_path)
            return client
        except Exception:
            pass

    email = input("Garmin email: ").strip()
    password = getpass.getpass("Garmin password: ")
    client = Garmin(email=email, password=password, prompt_mfa=lambda: input("MFA code: ").strip())
    client.login(token_path)
    return client


def list_activities(
    client: Garmin,
    since: datetime | None,
    activitytype: str,
    activitysubtype: str | None = None,
) -> list[dict[str, Any]]:
    """Page through Garmin's activity list for one type.

    With no `since`, pages through full history (first-time backfill).
    With `since`, stops once an older activity is reached (incremental sync).
    """
    activities: list[dict[str, Any]] = []
    start = 0
    cutoff = since.date() if since else None

    while True:
        page = client.get_activities(
            start=start, limit=100, activitytype=activitytype, activitysubtype=activitysubtype
        )
        if not page:
            break
        page_items = page.get("activityList", []) if isinstance(page, dict) else page
        if not page_items:
            break

        for item in page_items:
            started = _activity_date(item)
            if cutoff and started and started < cutoff:
                return activities
            activities.append(item)
        start += len(page_items)
    return activities


def exercise_sets(client: Garmin, activity_id: int | str) -> dict[str, Any]:
    return client.get_activity_exercise_sets(activity_id)


def activity_details(client: Garmin, activity_id: int | str, maxpoly: int = 50) -> dict[str, Any]:
    # ponytail: 50 points is plenty for a 220px route silhouette; route data was 54% of stored bytes at 200.
    return client.get_activity_details(activity_id, maxpoly=maxpoly)


def workouts(client: Garmin, start: int = 0, limit: int = 100) -> list[dict[str, Any]]:
    if hasattr(client, "get_workouts"):
        return client.get_workouts(start=start, limit=limit)
    return client.connectapi("/workout-service/workouts", params={"start": start, "limit": limit})


def workout_by_id(client: Garmin, workout_id: int | str) -> dict[str, Any]:
    if hasattr(client, "get_workout_by_id"):
        return client.get_workout_by_id(workout_id)
    return client.connectapi(f"/workout-service/workout/{workout_id}")


def update_workout(client: Garmin, workout_id: int | str, workout: dict[str, Any]) -> dict[str, Any]:
    if hasattr(client, "update_workout"):
        return client.update_workout(workout_id, workout)
    body = workout | {"workoutId": int(workout_id)}
    return client.client.put("connectapi", f"/workout-service/workout/{workout_id}", json=body, api=True).json()


def update_workout_target(
    client: Garmin,
    workout_id: int | str,
    exercise_name: str,
    target_weight_kg: float,
    apply: bool = False,
) -> tuple[dict[str, Any], int]:
    if target_weight_kg <= 0:
        raise ValueError("target_weight_kg must be positive.")
    workout = workout_by_id(client, workout_id)
    matches = update_strength_target(workout, exercise_name, target_weight_kg)
    if matches == 0:
        raise ValueError(f"No matching strength step found for {exercise_name!r} in workout {workout_id}.")
    if apply:
        update_workout(client, workout_id, workout)
    return workout, matches


def _activity_date(activity: dict[str, Any]) -> date | None:
    value = activity.get("startTimeLocal") or activity.get("startTimeGMT")
    if not value:
        return None
    return datetime.fromisoformat(str(value)[:19]).date()
