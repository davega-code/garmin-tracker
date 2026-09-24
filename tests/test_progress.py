from garmin_tracker.cli import progress_matches
from garmin_tracker.progress import recommendations


activities = [
    {
        "kind": "strength",
        "startTimeLocal": "2026-09-01 10:00:00",
        "sets": [
            {"exercise": "BENCH_PRESS", "weight": 80, "reps": 9},
            {"exercise": "LAT_PULLDOWN", "weight": 55, "reps": 8},
        ],
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
assert len(ready) == 2
assert ready[0].exercise == "BENCH_PRESS"
assert ready[0].current_weight_kg == 80
assert ready[0].target_weight_kg == 85
assert ready[1].exercise == "LAT_PULLDOWN"
assert ready[1].current_weight_kg == 55
assert ready[1].target_weight_kg == 60

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

stale_workout_target = [
    {
        "kind": "strength",
        "startTimeLocal": "2026-09-01 10:00:00",
        "sets": [{"exercise": "ROW", "weight": 50, "reps": 5}],
    },
    {
        "kind": "strength",
        "startTimeLocal": "2026-09-08 10:00:00",
        "sets": [{"exercise": "ROW", "weight": 50, "reps": 6}],
    },
    {
        "kind": "strength",
        "startTimeLocal": "2026-09-15 10:00:00",
        "sets": [{"exercise": "ROW", "weight": 50, "reps": 7}],
    },
]

assert recommendations(stale_workout_target) == []
stale_ready = recommendations(stale_workout_target, configured_weights_kg={"ROW": 45})
assert len(stale_ready) == 1
assert stale_ready[0].exercise == "ROW"
assert stale_ready[0].target_weight_kg == 50
assert stale_ready[0].sessions == 3
assert stale_ready[0].reason == "configured_weight"


class FakeGarmin:
    def get_workouts(self, start=0, limit=100):
        return [{"workoutId": 1, "workoutName": "Back Day"}]

    def get_workout_by_id(self, workout_id):
        return {
            "workoutName": "Back Day",
            "workoutSegments": [
                {
                    "workoutSteps": [
                        {
                            "stepType": {"stepTypeKey": "interval"},
                            "category": "ROW",
                            "weightValue": 45,
                        }
                    ]
                }
            ],
        }


matches = progress_matches(FakeGarmin(), stale_workout_target, "kg")
assert len(matches) == 1
assert matches[0]["workout_name"] == "Back Day"
assert matches[0]["recommendation"].target_weight_kg == 50
