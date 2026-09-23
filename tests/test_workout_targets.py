from garmin_tracker.workout_targets import update_strength_target


workout = {
    "workoutSegments": [
        {
            "workoutSteps": [
                {
                    "stepType": {"stepTypeKey": "interval"},
                    "category": "BENCH_PRESS",
                    "exerciseName": "BARBELL_BENCH_PRESS",
                },
                {
                    "stepType": {"stepTypeKey": "rest"},
                },
            ]
        }
    ]
}

assert update_strength_target(workout, "barbell bench press", 82.5) == 1
step = workout["workoutSegments"][0]["workoutSteps"][0]
assert step["weightValue"] == 82.5
assert step["weightUnit"]["unitKey"] == "kilogram"
assert update_strength_target(workout, "lat pulldown", 60) == 0
