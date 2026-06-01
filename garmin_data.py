"""
Garmin Connect data fetcher.
Usage:  python garmin_data.py <MFA_CODE>
After first login, session is saved and MFA is no longer needed.
"""

import sys, os, json
from datetime import date, timedelta
from garminconnect import Garmin
from supabase import create_client

from config import GARMIN_EMAIL as EMAIL, GARMIN_PASSWORD as PASSWORD, TOKEN_PATH, SUPABASE_URL, SUPABASE_KEY, DATA_PATH as SHARED_DATA_PATH
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
os.makedirs(os.path.dirname(SHARED_DATA_PATH), exist_ok=True)

MFA_CODE = sys.argv[1] if len(sys.argv) > 1 else None


def get_mfa():
    if MFA_CODE:
        print(f"Using MFA: {MFA_CODE}")
        return MFA_CODE
    return input("Enter Garmin MFA code: ").strip()


def connect():
    api = Garmin(email=EMAIL, password=PASSWORD)
    if os.path.exists(TOKEN_PATH):
        try:
            api.client.load(TOKEN_PATH)
            if api.client.is_authenticated:
                prof = api.client.connectapi("/userprofile-service/socialProfile")
                api.display_name = prof.get("displayName", api.username)
                api.full_name = prof.get("fullName", "")
                print(f"Loaded saved session ({api.display_name}).")
                return api
            print("Session expired, re-logging in...")
        except Exception as e:
            print(f"Could not load session ({e}), re-logging in...")

    api = Garmin(email=EMAIL, password=PASSWORD, prompt_mfa=get_mfa)
    api.login()
    api.client.dump(TOKEN_PATH)
    print(f"Session saved to {TOKEN_PATH}")
    return api


def fetch_data(api):
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    print(f"\n=== TODAY ({today}) ===")
    stats = api.get_stats(today)
    print(f"  Steps:        {stats.get('totalSteps', 'N/A')}")
    print(f"  Calories:     {stats.get('totalKilocalories', 'N/A')} kcal")
    print(f"  Stress avg:   {stats.get('averageStressLevel', 'N/A')}")
    print(f"  Body Battery: {stats.get('bodyBatteryMostRecentValue', 'N/A')}")
    print(f"  Resting HR:   {stats.get('restingHeartRate', 'N/A')} bpm")
    print(f"  SpO2:         {stats.get('averageSpo2', 'N/A')}%")
    print(f"  Respiration:  {stats.get('avgWakingRespirationValue', 'N/A')} brpm")

    print(f"\n=== SLEEP ({yesterday}) ===")
    sleep = api.get_sleep_data(yesterday)
    s = sleep.get("dailySleepDTO", {})
    duration_h = (s.get("sleepTimeSeconds") or 0) / 3600
    print(f"  Duration:     {duration_h:.1f}h")
    print(f"  Score:        {s.get('sleepScores', {}).get('overall', {}).get('value', 'N/A')}")
    print(f"  Deep sleep:   {(s.get('deepSleepSeconds') or 0) // 60} min")
    print(f"  REM sleep:    {(s.get('remSleepSeconds') or 0) // 60} min")

    # HRV
    hrv_data = {}
    try:
        hrv = api.get_hrv_data(today)
        hrv_s = hrv.get("hrvSummary", {})
        hrv_data = {
            "weekly_avg": hrv_s.get("weeklyAvg"),
            "last_night_avg": hrv_s.get("lastNightAvg"),
            "last_night_5min_high": hrv_s.get("lastNight5MinHigh"),
            "status": hrv_s.get("status"),
            "baseline_low": hrv_s.get("baseline", {}).get("balancedLow"),
            "baseline_high": hrv_s.get("baseline", {}).get("balancedUpper"),
        }
        print(f"  HRV last night: {hrv_data['last_night_avg']} (baseline {hrv_data['baseline_low']}-{hrv_data['baseline_high']}, status: {hrv_data['status']})")
    except Exception as e:
        print(f"  HRV: N/A ({e})")

    # Training Readiness (Garmin's official recovery score)
    readiness_data = {}
    try:
        tr = api.get_training_readiness(today)
        if tr:
            r = tr[0]
            readiness_data = {
                "score": r.get("score"),
                "level": r.get("level"),
                "feedback": r.get("feedbackShort"),
                "sleep_score": r.get("sleepScore"),
                "hrv_factor_pct": r.get("hrvFactorPercent"),
                "recovery_time_h": r.get("recoveryTime"),
            }
            print(f"  Training Readiness: {readiness_data['score']} ({readiness_data['level']})")
    except Exception as e:
        print(f"  Training Readiness: N/A ({e})")

    # Training status / VO2 Max
    vo2_data = {}
    try:
        ts = api.get_training_status(today)
        vo2_info = ts.get("mostRecentVO2Max", {}).get("generic", {})
        vo2_data = {
            "vo2max": vo2_info.get("vo2MaxPreciseValue"),
            "vo2max_date": vo2_info.get("calendarDate"),
        }
        print(f"  VO2 Max: {vo2_data['vo2max']} (as of {vo2_data['vo2max_date']})")
    except Exception as e:
        print(f"  VO2 Max: N/A ({e})")

    print(f"\n=== LAST 7 ACTIVITIES (fetching full details) ===" )
    activities = api.get_activities(0, 7)
    detailed_activities = []
    for a in activities:
        act_id = a["activityId"]
        detail = api.get_activity(act_id)
        s2 = detail.get("summaryDTO", {})
        entry = {
            "date": a["startTimeLocal"][:10],
            "time": a["startTimeLocal"][11:16],
            "type": a["activityType"]["typeKey"],
            "duration_min": round(s2.get("duration", 0) / 60, 1),
            "distance_km": round(s2.get("distance", 0) / 1000, 2) if s2.get("distance") else None,
            "calories": s2.get("calories"),
            "avg_hr": s2.get("averageHR"),
            "max_hr": s2.get("maxHR"),
            "min_hr": s2.get("minHR"),
            "training_effect_aerobic": s2.get("trainingEffect"),
            "training_effect_anaerobic": s2.get("anaerobicTrainingEffect"),
            "training_effect_label": s2.get("trainingEffectLabel"),
            "aerobic_te_message": s2.get("aerobicTrainingEffectMessage"),
            "anaerobic_te_message": s2.get("anaerobicTrainingEffectMessage"),
            "training_load": s2.get("activityTrainingLoad"),
            "body_battery_used": s2.get("differenceBodyBattery"),
            "vigorous_intensity_min": s2.get("vigorousIntensityMinutes"),
            "moderate_intensity_min": s2.get("moderateIntensityMinutes"),
            "avg_run_cadence": s2.get("averageRunCadence"),
            "stride_length_cm": s2.get("strideLength"),
            "vertical_oscillation_cm": s2.get("verticalOscillation"),
            "ground_contact_time_ms": s2.get("groundContactTime"),
            "normalized_power_w": s2.get("normalizedPower"),
            "avg_power_w": s2.get("averagePower"),
        }
        # HR zones
        try:
            zones = api.get_activity_hr_in_timezones(act_id)
            entry["hr_zones"] = {
                f"zone{z['zoneNumber']}": {
                    "min_hr": z["zoneLowBoundary"],
                    "seconds": round(z["secsInZone"])
                }
                for z in zones
            }
        except Exception:
            pass

        # remove None values to keep JSON clean
        entry = {k: v for k, v in entry.items() if v is not None}
        detailed_activities.append(entry)
        print(f"  {entry['date']} | {entry['type']:<20} | {entry['duration_min']}min | TE={entry.get('training_effect_aerobic','?')}")

    return {
        "date": today,
        "steps": stats.get("totalSteps"),
        "step_goal": stats.get("dailyStepGoal"),
        "calories_total": stats.get("totalKilocalories"),
        "calories_active": stats.get("activeKilocalories"),
        "resting_hr": stats.get("restingHeartRate"),
        "resting_hr_7day_avg": stats.get("lastSevenDaysAvgRestingHeartRate"),
        "hr_min": stats.get("minHeartRate"),
        "hr_max": stats.get("maxHeartRate"),
        "stress_avg": stats.get("averageStressLevel"),
        "stress_max": stats.get("maxStressLevel"),
        "stress_low_pct": stats.get("lowStressPercentage"),
        "stress_medium_pct": stats.get("mediumStressPercentage"),
        "stress_high_pct": stats.get("highStressPercentage"),
        "body_battery_current": stats.get("bodyBatteryMostRecentValue"),
        "body_battery_highest": stats.get("bodyBatteryHighestValue"),
        "body_battery_lowest": stats.get("bodyBatteryLowestValue"),
        "body_battery_charged": stats.get("bodyBatteryChargedValue"),
        "body_battery_drained": stats.get("bodyBatteryDrainedValue"),
        "body_battery_at_wake": stats.get("bodyBatteryAtWakeTime"),
        "spo2_avg": stats.get("averageSpo2"),
        "spo2_lowest": stats.get("lowestSpo2"),
        "respiration_avg": stats.get("avgWakingRespirationValue"),
        "sedentary_hours": round(stats.get("sedentarySeconds", 0) / 3600, 1),
        "highly_active_min": round(stats.get("highlyActiveSeconds", 0) / 60),
        "vigorous_intensity_min": stats.get("vigorousIntensityMinutes"),
        "moderate_intensity_min": stats.get("moderateIntensityMinutes"),
        "sleep_hours": round(duration_h, 1),
        "sleep_score": s.get("sleepScores", {}).get("overall", {}).get("value"),
        "sleep_deep_min": (s.get("deepSleepSeconds") or 0) // 60,
        "sleep_rem_min": (s.get("remSleepSeconds") or 0) // 60,
        "hrv": hrv_data,
        "training_readiness": readiness_data,
        "vo2max": vo2_data,
        "activities": detailed_activities,
    }


api = connect()
data = fetch_data(api)

# Save locally
out_path = os.path.expanduser("~/.garmin_tokens/latest_data.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
with open(SHARED_DATA_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print(f"\nData saved locally and to OneDrive.")

# Save to Supabase
try:
    daily_row = {
        "date": data["date"],
        "steps": data.get("steps"),
        "calories_total": data.get("calories_total"),
        "resting_hr": data.get("resting_hr"),
        "resting_hr_7day_avg": data.get("resting_hr_7day_avg"),
        "stress_avg": data.get("stress_avg"),
        "body_battery_current": data.get("body_battery_current"),
        "body_battery_highest": data.get("body_battery_highest"),
        "body_battery_lowest": data.get("body_battery_lowest"),
        "body_battery_charged": data.get("body_battery_charged"),
        "body_battery_drained": data.get("body_battery_drained"),
        "body_battery_at_wake": data.get("body_battery_at_wake"),
        "spo2_avg": data.get("spo2_avg"),
        "respiration_avg": data.get("respiration_avg"),
        "sleep_hours": data.get("sleep_hours"),
        "sleep_score": data.get("sleep_score"),
        "sleep_deep_min": data.get("sleep_deep_min"),
        "sleep_rem_min": data.get("sleep_rem_min"),
        "hrv_weekly_avg": data.get("hrv", {}).get("weekly_avg"),
        "hrv_last_night": data.get("hrv", {}).get("last_night_avg"),
        "hrv_status_text": data.get("hrv", {}).get("status"),
        "vo2max": data.get("vo2max", {}).get("vo2max"),
        "sedentary_hours": data.get("sedentary_hours"),
        "vigorous_intensity_min": data.get("vigorous_intensity_min"),
        "moderate_intensity_min": data.get("moderate_intensity_min"),
    }
    daily_row = {k: v for k, v in daily_row.items() if v is not None}
    sb.table("garmin_daily").upsert(daily_row, on_conflict="date").execute()
    print(f"Daily data saved to Supabase.")

    for a in data.get("activities", []):
        act_row = {
            "date": a["date"],
            "activity_time": a.get("time"),
            "activity_type": a.get("type"),
            "duration_min": a.get("duration_min"),
            "distance_km": a.get("distance_km"),
            "calories": a.get("calories"),
            "avg_hr": a.get("avg_hr"),
            "max_hr": a.get("max_hr"),
            "training_effect_aerobic": a.get("training_effect_aerobic"),
            "training_effect_anaerobic": a.get("training_effect_anaerobic"),
            "training_effect_label": a.get("training_effect_label"),
            "training_load": a.get("training_load"),
            "body_battery_used": a.get("body_battery_used"),
            "normalized_power_w": a.get("normalized_power_w"),
            "hr_zones": json.dumps(a.get("hr_zones", {})),
        }
        act_row = {k: v for k, v in act_row.items() if v is not None}
        sb.table("garmin_activities").upsert(act_row, on_conflict="id").execute()
    print(f"Activities saved to Supabase ({len(data.get('activities', []))} records).")
except Exception as e:
    print(f"Supabase save failed: {e}")
