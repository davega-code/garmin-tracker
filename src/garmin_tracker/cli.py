from __future__ import annotations

import argparse
import copy
import http.server
import json
import socketserver
import sys
import webbrowser
from typing import Any

from . import garmin_client, normalize, state, store
from .analysis import summarize
from .paths import DASHBOARD_DIR, ensure_dirs
from .progress import ProgressRecommendation, recommendations
from .workout_targets import matching_strength_steps, update_strength_target


def main() -> None:
    parser = argparse.ArgumentParser(prog="garmin-tracker")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth")
    sub.add_parser("sync")
    sub.add_parser("analyze")
    progress = sub.add_parser("progress")
    progress.add_argument("--unit", choices=("kg", "lb"), default="kg")
    target = sub.add_parser("update-workout")
    target.add_argument("workout_id")
    target.add_argument("exercise")
    target.add_argument("target_weight", type=float)
    target.add_argument("--unit", choices=("kg", "lb"), default="kg")
    target.add_argument("--apply", action="store_true", help="Actually update Garmin; without this, only previews.")
    dash = sub.add_parser("dashboard")
    dash.add_argument("--port", type=int, default=8765)

    args = parser.parse_args()
    ensure_dirs()

    if args.cmd == "auth":
        garmin_client.login(require_credentials=True)
        print("Authenticated. Tokens cached outside the repo.")
    elif args.cmd == "sync":
        sync()
    elif args.cmd == "analyze":
        print(summarize())
    elif args.cmd == "progress":
        progress_updates(args.unit)
    elif args.cmd == "update-workout":
        workout_target(args.workout_id, args.exercise, args.target_weight, args.unit, args.apply)
    elif args.cmd == "dashboard":
        dashboard(args.port)


def sync() -> None:
    client = garmin_client.login()
    strength_total, strength_changed = _sync_strength(client)
    running_total, running_changed = _sync_running(client)
    print(
        f"Synced {strength_total} strength activities ({strength_changed} updated) "
        f"and {running_total} running activities ({running_changed} updated)."
    )


def _sync_strength(client: garmin_client.Garmin) -> tuple[int, int]:
    since = state.last_pulled_at("strength")
    summaries = garmin_client.list_activities(client, since, "fitness_equipment", "strength_training")
    normalized = []
    for summary in summaries:
        sets = garmin_client.exercise_sets(client, summary["activityId"])
        normalized.append(normalize.strength_activity(summary, sets))
    changed = store.upsert_activities(normalized)
    state.mark_pulled("strength")
    return len(normalized), changed


def _sync_running(client: garmin_client.Garmin) -> tuple[int, int]:
    since = state.last_pulled_at("running")
    summaries = garmin_client.list_activities(client, since, "running")
    normalized = []
    for summary in summaries:
        details = garmin_client.activity_details(client, summary["activityId"])
        normalized.append(normalize.running_activity(summary, details))
    changed = store.upsert_activities(normalized)
    state.mark_pulled("running")
    return len(normalized), changed


def dashboard(port: int) -> None:
    payload = json.dumps(store.load_all())
    (DASHBOARD_DIR / "data.js").write_text(f"window.GARMIN_TRACKER_DATA = {payload};\n", encoding="utf-8")
    url = f"http://127.0.0.1:{port}"
    webbrowser.open(url)
    handler = lambda *a, **kw: _DashboardHandler(*a, directory=str(DASHBOARD_DIR), **kw)
    with _DashboardServer(("127.0.0.1", port), handler) as server:
        print(f"Dashboard: {url}")
        server.serve_forever()


def progress_updates(unit: str) -> None:
    recs = recommendations(store.load_all(), unit)
    if not recs:
        print("No progressive overload updates ready. Keep logging sets until an exercise hits 9+ reps for 2 straight sessions.")
        return

    print("Ready target-weight recommendations:")
    for i, rec in enumerate(recs, start=1):
        print(f"{i}. {rec.exercise}: {format_weight(rec.current_weight_kg, unit)} -> {format_weight(rec.target_weight_kg, unit)} ({rec.sessions} sessions at {rec.reps}+ reps)")

    client = garmin_client.login()
    matches = progress_matches(client, recs)
    matches = [match for match in matches if match["steps"] > 0]
    if not matches:
        print("No matching Garmin workout-template steps found. Use `garmin-tracker update-workout` for a manual update.")
        return

    print("\nGarmin updates to apply:")
    for i, match in enumerate(matches, start=1):
        rec = match["recommendation"]
        print(
            f"{i}. {match['workout_name']}: {rec.exercise} -> {format_weight(rec.target_weight_kg, unit)} "
            f"({match['steps']} step{'s' if match['steps'] != 1 else ''})"
        )

    selected = prompt_selection(len(matches))
    if not selected:
        print("Skipped Garmin updates.")
        return

    changed: dict[str, dict[str, Any]] = {}
    for index in selected:
        match = matches[index - 1]
        workout_id = str(match["workout_id"])
        workout = changed.setdefault(workout_id, copy.deepcopy(match["workout"]))
        rec = match["recommendation"]
        update_strength_target(workout, rec.exercise, rec.target_weight_kg)

    for workout_id, workout in changed.items():
        garmin_client.update_workout(client, workout_id, workout)
    print(f"Updated {len(changed)} Garmin workout template(s).")


def progress_matches(client: garmin_client.Garmin, recs: list[ProgressRecommendation]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for summary in garmin_client.workouts(client):
        workout_id = summary.get("workoutId")
        if not workout_id:
            continue
        workout = garmin_client.workout_by_id(client, workout_id)
        workout_name = workout.get("workoutName") or summary.get("workoutName") or workout_id
        for rec in recs:
            steps = len(matching_strength_steps(workout, rec.exercise))
            if steps:
                matches.append(
                    {
                        "workout_id": workout_id,
                        "workout_name": workout_name,
                        "workout": workout,
                        "recommendation": rec,
                        "steps": steps,
                    }
                )
    return matches


def prompt_selection(count: int) -> list[int]:
    while True:
        try:
            answer = input("\nApply which updates? [all, numbers like 1,3, or blank to skip]: ").strip().lower()
        except EOFError:
            return []
        if not answer or answer in {"n", "no", "none", "skip"}:
            return []
        if answer in {"a", "all"}:
            return list(range(1, count + 1))
        try:
            selected = sorted({int(part.strip()) for part in answer.split(",") if part.strip()})
        except ValueError:
            selected = []
        if selected and all(1 <= item <= count for item in selected):
            return selected
        print(f"Enter all, blank, or numbers between 1 and {count}.")


def workout_target(workout_id: str, exercise: str, target_weight: float, unit: str, apply: bool) -> None:
    client = garmin_client.login()
    target_weight_kg = target_weight / 2.2046226218 if unit == "lb" else target_weight
    workout, matches = garmin_client.update_workout_target(client, workout_id, exercise, target_weight_kg, apply=apply)
    verb = "Updated" if apply else "Previewed"
    suffix = "" if apply else " Re-run with --apply to confirm and write to Garmin."
    print(f"{verb} {matches} step(s) in {workout.get('workoutName') or workout_id} to {target_weight:g} {unit}.{suffix}")


def format_weight(weight_kg: float, unit: str) -> str:
    value = weight_kg * 2.2046226218 if unit == "lb" else weight_kg
    return f"{round(value, 1):g} {unit}"


class _DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        # This is under active development; never let the browser serve a cached copy.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


class _DashboardServer(socketserver.TCPServer):
    def handle_error(self, request: Any, client_address: Any) -> None:
        # Browsers routinely abort in-flight requests (tab reload, cache reuse);
        # that is not an application error worth a scary traceback.
        if isinstance(sys.exc_info()[1], (ConnectionAbortedError, ConnectionResetError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


if __name__ == "__main__":
    main()
