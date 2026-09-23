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

seventy_two_lb = [
    {
        "kind": "strength",
        "startTimeLocal": "2026-09-01 10:00:00",
        "sets": [{"exercise": "CABLE_OVERHEAD_TRICEPS_EXTENSION", "weight": 32.687, "reps": 10}],
    },
    {
        "kind": "strength",
        "startTimeLocal": "2026-09-08 10:00:00",
        "sets": [{"exercise": "CABLE_OVERHEAD_TRICEPS_EXTENSION", "weight": 32.687, "reps": 10}],
    },
]

ready_72 = recommendations(seventy_two_lb, "lb")
assert round(ready_72[0].current_weight_kg * 2.2046226218, 1) == 72.1
assert round(ready_72[0].target_weight_kg * 2.2046226218, 1) == 77.1
