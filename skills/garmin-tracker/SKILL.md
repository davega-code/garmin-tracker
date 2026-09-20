# Garmin Tracker Analysis

Use this skill when asked to analyze local `garmin-tracker` activity results.

Read monthly JSON files from `data/*.json` in the repo root. Each record has a `kind` field:
`strength` (sets/reps/weight) or `running` (distance/pace/heart rate/route).
Summarize progress by exercise or run, weight, reps, volume, distance, pace, consistency,
plateaus, and PRs. Do not request Garmin credentials. Do not call Garmin APIs. Work only from
local JSON.

Prefer concise recommendations:
- exercises improving
- exercises stalled
- volume trends
- suspicious data gaps
- next workout focus

