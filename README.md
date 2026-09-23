# garmin-tracker

Small local Garmin strength-training and running tracker, with a dashboard that runs entirely
on your own machine.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```powershell
git clone https://github.com/davega-code/garmin-tracker.git
cd garmin-tracker
uv tool install --editable .
```

Reinstall after pulling changes:

```powershell
uv tool install --editable . --reinstall
```

If your network blocks direct PyPI access (common on corporate devices), add
`--default-index <your-mirror-url>` to either command.

## Commands

```powershell
garmin-tracker auth
garmin-tracker sync
garmin-tracker dashboard
garmin-tracker analyze
garmin-tracker progress [--unit kg|lb]
garmin-tracker update-workout <workout-id> <exercise> <target-weight> [--unit kg|lb] [--apply]
```

`auth` prompts for your Garmin email, password, and MFA if needed. The password is never stored. Tokens are cached outside the repo in `%LOCALAPPDATA%\garmin-tracker\garminconnect`.

`sync` pulls your full history the first time, then only new activities on later runs.

`progress` shows exercises ready for progressive overload, matches them to Garmin workout
templates, then asks whether to apply all updates, only selected numbers, or none.

`update-workout` previews one manual target-weight change; add `--apply` only after
confirming the workout and exercise are correct.

## Dashboard

`garmin-tracker dashboard` opens a local page with a **Strength** / **Running** toggle:

- **Strength** — a chronological log of sessions, a **Routines** view (trend per recurring
  workout name, e.g. "Leg Day"), and an **Exercises** view (weight progression per lift, with
  personal records marked and target-weight suggestions for progressive overload). Switch
  weight units (kg/lb) from the header.
- **Running** — a log of runs with pace, heart rate, and a route map (via
  [Leaflet](https://leafletjs.com/) and OpenStreetMap tiles, so viewing a route needs internet;
  everything else works offline), plus a **Trends** view for distance/pace/heart rate over time.

## Storage

- `state.json` tracks the last successful sync, per activity type.
- `data\YYYY-MM.json` stores normalized activities for that month.
- `dashboard\data.js` is regenerated on every `dashboard` run from the files above.

All three contain your personal activity data (including GPS routes and heart rate) and are
gitignored — they never leave your machine.

This prototype only uses read APIs from `garminconnect`. The dependency is pinned to `0.3.13`,
which includes the token-permission fix released in `0.3.5`.
