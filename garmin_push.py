"""
Push structured workouts to Garmin Connect.
Format reverse-engineered from garmin-workouts-mcp and sydspost/garmin-connect-workout-creator.
"""

import os
from datetime import date, timedelta
from garminconnect import Garmin

from config import GARMIN_EMAIL, GARMIN_PASSWORD, TOKEN_PATH

SPORT = {
    "running":  {"sportTypeId": 1,  "sportTypeKey": "running"},
    "strength": {"sportTypeId": 5,  "sportTypeKey": "strength_training"},
    "walking":  {"sportTypeId": 11, "sportTypeKey": "walking"},
}

STEP_TYPE = {
    "warmup":   {"stepTypeId": 0, "stepTypeKey": "warmup"},
    "interval": {"stepTypeId": 3, "stepTypeKey": "interval"},
    "recovery": {"stepTypeId": 4, "stepTypeKey": "recovery"},
    "cooldown": {"stepTypeId": 4, "stepTypeKey": "cooldown"},
    "rest":     {"stepTypeId": 5, "stepTypeKey": "rest"},
}

NO_TARGET  = {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target"}
HR_TARGET  = {"workoutTargetTypeId": 4, "workoutTargetTypeKey": "heart.rate.zone"}
END_TIME   = {"conditionTypeId": 2, "conditionTypeKey": "time"}
END_DIST   = {"conditionTypeId": 3, "conditionTypeKey": "distance"}
END_ITER   = {"conditionTypeId": 7, "conditionTypeKey": "iterations"}


def _exec_step(order, step_key, end_condition, end_value,
               target=None, hr_low=None, hr_high=None) -> dict:
    step = {
        "type": "ExecutableStepDTO",
        "stepOrder": order,
        "stepType": STEP_TYPE[step_key],
        "endCondition": end_condition,
        "endConditionValue": end_value,
        "targetType": target or NO_TARGET,
    }
    if hr_low and hr_high:
        step["targetType"] = HR_TARGET
        step["targetValueOne"] = hr_low
        step["targetValueTwo"] = hr_high
    return step


def _repeat_group(order, count, child_steps) -> dict:
    return {
        "type": "RepeatGroupDTO",
        "stepOrder": order,
        "stepType": {"stepTypeId": 6, "stepTypeKey": "repeat"},
        "endCondition": END_ITER,
        "endConditionValue": count,
        "numberOfIterations": count,
        "workoutSteps": child_steps,
    }


def _workout(name, sport_key, steps) -> dict:
    return {
        "workoutName": name,
        "description": f"בוב AI — {date.today().isoformat()}",
        "sportType": SPORT[sport_key],
        "workoutSegments": [{
            "segmentOrder": 1,
            "sportType": SPORT[sport_key],
            "workoutSteps": steps,
        }]
    }


# ── Workout templates ──────────────────────────────────────────────────────

def build_long_run(duration_min=55, hr_low=130, hr_high=155):
    return _workout("ריצה ארוכה — בוב AI", "running", [
        _exec_step(1, "warmup",   END_TIME, 5 * 60,                    hr_low=115, hr_high=130),
        _exec_step(2, "interval", END_TIME, (duration_min - 10) * 60,  hr_low=hr_low, hr_high=hr_high),
        _exec_step(3, "cooldown", END_TIME, 5 * 60,                    hr_low=100, hr_high=120),
    ])


def build_interval_run(intervals=6, interval_m=400, recovery_sec=90,
                       hr_low=165, hr_high=180):
    child = [
        _exec_step(1, "interval", END_DIST, interval_m, hr_low=hr_low, hr_high=hr_high),
        _exec_step(2, "recovery", END_TIME, recovery_sec, hr_low=120, hr_high=140),
    ]
    return _workout("אינטרוולים — בוב AI", "running", [
        _exec_step(1, "warmup",   END_TIME, 10 * 60, hr_low=115, hr_high=135),
        _repeat_group(2, intervals, child),
        _exec_step(3, "cooldown", END_TIME, 10 * 60, hr_low=100, hr_high=120),
    ])


def _exercise_step(order, exercise_category, exercise_name, reps, sets=3) -> dict:
    """Single exercise step with specific Garmin exercise name."""
    return {
        "type": "ExecutableStepDTO",
        "stepOrder": order,
        "stepType": STEP_TYPE["interval"],
        "endCondition": {"conditionTypeId": 4, "conditionTypeKey": "reps"},
        "endConditionValue": reps,
        "targetType": NO_TARGET,
        "exerciseName": exercise_name,
        "exerciseCategory": exercise_category,
    }


def _core_steps(start_order: int) -> list:
    """3 core/abs exercises — mat only, no equipment."""
    return [
        _exercise_step(start_order,     "PLANK",  "PLANK",           reps=45),
        _exercise_step(start_order + 1, "CRUNCH", "BICYCLE_CRUNCH",  reps=20),
        _exercise_step(start_order + 2, "CRUNCH", "REVERSE_CRUNCH",  reps=15),
    ]


# All exercises: mat + 7.5kg dumbbell only
UPPER_EXERCISES = [
    ("PUSH_UP",         "PUSH_UP",                        12),  # bodyweight
    ("SHOULDER_PRESS",  "DUMBBELL_SHOULDER_PRESS",         12),  # 7.5kg
    ("LATERAL_RAISE",   "DUMBBELL_LATERAL_RAISE",          15),  # 7.5kg
    ("PUSH_UP",         "DIAMOND_PUSH_UP",                 10),  # bodyweight, triceps
    ("FRONT_RAISE",     "DUMBBELL_FRONT_RAISE",            12),  # 7.5kg
]

BACK_EXERCISES = [
    ("ROW",             "DUMBBELL_ROW",                    12),  # 7.5kg one arm
    ("CORE",            "SUPERMAN",                        15),  # bodyweight, back extension
    ("CORE",            "BIRD_DOG",                        12),  # bodyweight, stability
    ("CURL",            "DUMBBELL_BICEPS_CURL",            12),  # 7.5kg
    ("CURL",            "HAMMER_CURL",                     12),  # 7.5kg
]

LEG_EXERCISES = [
    ("SQUAT",           "BODYWEIGHT_SQUAT",               15),  # bodyweight
    ("SQUAT",           "DUMBBELL_SQUAT",                 12),  # 7.5kg held
    ("LUNGE",           "BODYWEIGHT_WALKING_LUNGE",       12),  # bodyweight
    ("HIP_RAISE",       "GLUTE_BRIDGE",                   15),  # bodyweight
    ("HIP_RAISE",       "SINGLE_LEG_GLUTE_BRIDGE",        12),  # bodyweight
]

EXERCISE_PLANS = {
    "strength_upper": UPPER_EXERCISES,
    "strength_back":  BACK_EXERCISES,
    "strength_legs":  LEG_EXERCISES,
}


def build_strength(workout_type: str, label: str, sets: int = 3):
    exercises = EXERCISE_PLANS.get(workout_type, UPPER_EXERCISES)
    steps = [_exec_step(1, "warmup", END_TIME, 5 * 60)]
    for i, (category, name, reps) in enumerate(exercises, start=2):
        steps.append(_exercise_step(i, category, name, reps, sets))
    steps.extend(_core_steps(len(steps) + 1))
    return _workout(f"כוח — {label} — בוב AI", "strength", steps)


def build_walk(duration_min=35):
    return _workout("הליכה — בוב AI", "walking", [
        _exec_step(1, "interval", END_TIME, duration_min * 60, hr_low=95, hr_high=115),
    ])


# ── Push week ──────────────────────────────────────────────────────────────

WEEKLY = {
    5: ("long_run",       "ריצה ארוכה"),
    6: ("strength_upper", "חזה+כתפיים+בטן"),
    0: ("strength_back",  "גב+ביצפס+בטן"),
    1: ("interval_run",   "אינטרוולים"),
    2: ("strength_legs",  "רגליים+ישבן+בטן"),
    3: None,
    4: ("walk",           "הליכה קלה"),
}


def _connect():
    api = Garmin(email=GARMIN_EMAIL, password=GARMIN_PASSWORD)
    api.client.load(TOKEN_PATH)
    prof = api.client.connectapi("/userprofile-service/socialProfile")
    api.display_name = prof.get("displayName", api.username)
    return api


def push_week(long_run_min=55, intervals=6, interval_m=400,
              strength_min=40, long_run_hr_high=155):
    api = _connect()
    today = date.today()
    results = []

    for days in range(7):
        target = today + timedelta(days=days)
        plan = WEEKLY.get(target.weekday())
        if not plan:
            continue
        wtype, label = plan

        if wtype == "long_run":
            w = build_long_run(long_run_min, hr_high=long_run_hr_high)
        elif wtype == "interval_run":
            w = build_interval_run(intervals, interval_m)
        elif wtype in ("strength_upper", "strength_back", "strength_legs"):
            w = build_strength(wtype, label)
        elif wtype == "walk":
            w = build_walk()
        else:
            continue

        try:
            res = api.upload_workout(w)
            wid = res.get("detailId") or res.get("workoutId")
            if wid:
                api.schedule_workout(wid, target.isoformat())
            results.append(f"✓ {target.strftime('%A %d/%m')} — {label}")
        except Exception as e:
            results.append(f"✗ {label}: {e}")

    return "\n".join(results)


if __name__ == "__main__":
    print("דוחף אימונים לגרמין...")
    print(push_week())
