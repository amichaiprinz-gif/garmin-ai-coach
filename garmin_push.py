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
END_TIME   = {"conditionTypeId": 2,  "conditionTypeKey": "time"}
END_DIST   = {"conditionTypeId": 3,  "conditionTypeKey": "distance"}
END_ITER   = {"conditionTypeId": 7,  "conditionTypeKey": "iterations"}
END_REPS   = {"conditionTypeId": 10, "conditionTypeKey": "reps"}


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
        "endCondition": END_REPS,
        "endConditionValue": reps,
        "targetType": NO_TARGET,
        "category": exercise_category,
        "exerciseName": exercise_name,
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
    ("SHOULDER_PRESS",  "DUMBBELL_FRONT_RAISE",            12),  # 7.5kg
]

BACK_EXERCISES = [
    ("ROW",             "DUMBBELL_ROW",                    12),  # 7.5kg one arm
    ("CORE",            "SUPERMAN",                        15),  # bodyweight, back extension
    ("CORE",            "BIRD_DOG",                        12),  # bodyweight, stability
    ("CURL",            "DUMBBELL_BICEPS_CURL",            12),  # 7.5kg
    ("CURL",            "HAMMER_CURL",                     12),  # 7.5kg
]

# Shin rehab program — per physiotherapist instructions (June 2026)
# Goal: strengthen lower leg before returning to running
# Shin rehab program — per physiotherapist instructions (June 2026)
LEG_EXERCISES = [
    ("SQUAT",      "WALL_SQUAT",              30),  # wall squat isometric — 30 seconds
    ("CALF_RAISE", "SINGLE_LEG_CALF_RAISE",   15),  # single-leg calf raise, each leg
    ("HIP_RAISE",  "GLUTE_BRIDGE",            12),  # bridge 4×12
    ("CORE",       "HEEL_WALK",               60),  # heel walk — 60 seconds
]

ARMS_EXERCISES = [
    ("CURL",    "DUMBBELL_BICEPS_CURL",   12),  # 7.5kg
    ("CURL",    "HAMMER_CURL",            12),  # 7.5kg
    ("PUSH_UP", "DIAMOND_PUSH_UP",        10),  # bodyweight, triceps
    ("CORE",    "PLANK",                  45),  # abs
    ("CORE",    "SIDE_PLANK",             30),  # abs
    ("CRUNCH",  "BICYCLE_CRUNCH",         20),  # abs
    ("CRUNCH",  "REVERSE_CRUNCH",         15),  # abs
]

EXERCISE_PLANS = {
    "strength_upper": UPPER_EXERCISES,
    "strength_back":  BACK_EXERCISES,
    "strength_legs":  LEG_EXERCISES,
    "strength_arms":  ARMS_EXERCISES,
}


def build_strength(workout_type: str, label: str, sets: int = 3):
    exercises = EXERCISE_PLANS.get(workout_type, UPPER_EXERCISES)
    steps = [_exec_step(1, "warmup", END_TIME, 5 * 60)]
    order = 2
    for category, name, reps in exercises:
        # Descending reps across sets (e.g. 12/10/8) to match real fatigue
        rep_counts = [reps, max(reps - 2, 6), max(reps - 4, 6)]
        for s in range(sets):
            steps.append(_exercise_step(order, category, name, rep_counts[s]))
            order += 1
        # Rest between sets
        steps.append(_exec_step(order, "rest", END_TIME, 60))
        order += 1
    steps.extend(_core_steps(order))
    return _workout(f"כוח — {label} — בוב AI", "strength", steps)


def build_walk(duration_min=35):
    return _workout("הליכה — בוב AI", "walking", [
        _exec_step(1, "interval", END_TIME, duration_min * 60, hr_low=95, hr_high=115),
    ])


# ── Push week ──────────────────────────────────────────────────────────────

# SHIN REHAB MODE (June 2026) — per physiotherapist
# Reduced running, focus on leg strengthening 1-2 weeks
# Then return to full program
WEEKLY = {
    6: ("strength_upper", "חזה+כתפיים+טריצפס+בטן"),
    0: ("strength_back",  "גב+ביצפס+בטן"),
    1: ("walk",           "הליכה קלה"),          # was: intervals — no running
    2: ("strength_legs",  "שיקום שוק — פיזיו"),   # physio program
    3: ("strength_arms",  "בטן+ידיים"),
    4: ("walk",           "הליכה קלה"),
    5: ("strength_legs",  "שיקום שוק — פיזיו"),   # no running until shin heals
}


def _connect():
    api = Garmin(email=GARMIN_EMAIL, password=GARMIN_PASSWORD)
    api.client.load(TOKEN_PATH)
    prof = api.client.connectapi("/userprofile-service/socialProfile")
    api.display_name = prof.get("displayName", api.username)
    return api


def delete_all_workouts(api) -> int:
    """Delete all existing Bob AI workouts from Garmin Connect."""
    workouts = api.get_workouts(0, 100)
    count = 0
    for w in workouts:
        try:
            api.delete_workout(w["workoutId"])
            count += 1
        except Exception:
            pass
    return count


def push_from_plan(plan: dict, load: dict):
    """Delete existing workouts and push fresh plan (generated by bob_weekly_plan.py)."""
    api = _connect()
    deleted = delete_all_workouts(api)
    results = [f"🗑️ מחקתי {deleted} אימונים קיימים"]
    for d_str, entry in sorted(plan.items()):
        target = date.fromisoformat(d_str)
        wtype = entry.get("type")
        label = entry.get("label", wtype)
        sets  = entry.get("sets", 3)

        if wtype in ("strength_upper","strength_back","strength_legs","strength_arms"):
            w = build_strength(wtype, label, sets)
        elif wtype == "intervals":
            w = build_interval_run(entry.get("intervals", 4))
        elif wtype == "long_run":
            w = build_long_run(entry.get("run_min", 45))
        elif wtype == "walk":
            w = build_walk()
        else:
            continue

        try:
            res = api.upload_workout(w)
            wid = res.get("detailId") or res.get("workoutId")
            if wid:
                api.schedule_workout(wid, d_str)
            results.append(f"✓ {target.strftime('%A %d/%m')} — {label}")
        except Exception as e:
            results.append(f"✗ {label}: {e}")

    return "\n".join(results)


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
        elif wtype in ("strength_upper","strength_back","strength_legs","strength_arms"):
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
