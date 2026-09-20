from __future__ import annotations

import argparse
import http.server
import json
import socketserver
import sys
import webbrowser
from typing import Any

from . import garmin_client, normalize, state, store
from .analysis import summarize
from .paths import DASHBOARD_DIR, ensure_dirs


def main() -> None:
    parser = argparse.ArgumentParser(prog="garmin-tracker")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth")
    sub.add_parser("sync")
    sub.add_parser("analyze")
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

