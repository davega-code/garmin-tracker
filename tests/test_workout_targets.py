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

triceps_workout = {
    "workoutSegments": [
        {
            "workoutSteps": [
                {
                    "stepType": {"stepTypeKey": "interval"},
                    "category": "TRICEPS_EXTENSION",
                    "exerciseName": "TRICEPS_PRESS_DOWN",
                    "weightValue": 20,
                },
                {
                    "stepType": {"stepTypeKey": "interval"},
                    "category": "TRICEPS_EXTENSION",
                    "exerciseName": "CABLE_OVERHEAD_TRICEPS_EXTENSION",
                    "weightValue": 30,
                },
            ]
        }
    ]
}

assert update_strength_target(triceps_workout, "CABLE_OVERHEAD_TRICEPS_EXTENSION", 29.5) == 1
press_down, overhead = triceps_workout["workoutSegments"][0]["workoutSteps"]
assert press_down["weightValue"] == 20
assert overhead["weightValue"] == 29.5
