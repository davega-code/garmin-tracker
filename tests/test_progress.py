from garmin_tracker.progress import recommendations


activities = [
    {
        "kind": "strength",
        "startTimeLocal": "2026-09-01 10:00:00",
        "sets": [{"exercise": "BENCH_PRESS", "weight": 80, "reps": 9}],
    },
    {
        "kind": "strength",
        "startTimeLocal": "2026-09-08 10:00:00",
        "sets": [{"exercise": "BENCH_PRESS", "weight": 80, "reps": 10}],
    },
    {
        "kind": "strength",
        "startTimeLocal": "2026-09-08 10:00:00",
        "sets": [{"exercise": "LAT_PULLDOWN", "weight": 55, "reps": 8}],
    },
]

ready = recommendations(activities)
assert len(ready) == 1
assert ready[0].exercise == "BENCH_PRESS"
assert ready[0].current_weight_kg == 80
assert ready[0].target_weight_kg == 85

ready_lb = recommendations(activities, "lb")
assert round(ready_lb[0].target_weight_kg * 2.2046226218, 1) == 186.4
