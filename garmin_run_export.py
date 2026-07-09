"""
Export last run to CSV → Google Drive (ריצות/) → print Drive link for Bob.
Usage: python garmin_run_export.py
"""
import os, csv, sys
sys.stdout.reconfigure(encoding="utf-8")
from garminconnect import Garmin
from config import GARMIN_EMAIL, GARMIN_PASSWORD, TOKEN_PATH

DRIVE_FOLDER = "ריצות"

# ─── connect (reuses saved session) ───────────────────────────────────────────

def connect():
    api = Garmin(email=GARMIN_EMAIL, password=GARMIN_PASSWORD)
    if os.path.exists(TOKEN_PATH):
        try:
            api.client.load(TOKEN_PATH)
            if api.client.is_authenticated:
                return api
        except Exception:
            pass
    api.login()
    api.client.dump(TOKEN_PATH)
    return api

# ─── helpers ───────────────────────────────────────────────────────────────────

def pace(speed_ms):
    if not speed_ms or speed_ms <= 0:
        return ""
    s = 1000 / speed_ms
    return f"{int(s // 60)}:{int(s % 60):02d}"

def hms(seconds):
    seconds = int(seconds or 0)
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"

# ─── CSV export ────────────────────────────────────────────────────────────────

def export_csv(api, activity_id, out_path, silent=False):
    if not silent:
        print("  מושך נתוני שנייה-שנייה...")
    details = api.get_activity_details(activity_id, maxchart=10000)

    descriptors = {d["metricsIndex"]: d["key"] for d in details.get("metricDescriptors", [])}
    raw_rows = details.get("activityDetailMetrics", [])

    rows = []
    for point in raw_rows:
        row = {}
        for i, val in enumerate(point.get("metrics", [])):
            row[descriptors.get(i, f"col_{i}")] = val
        rows.append(row)

    if not rows:
        print("  אין נתוני שנייה-שנייה.")
        return 0

    # Add human-readable derived columns
    for row in rows:
        spd = row.get("directSpeed") or row.get("enhancedSpeed") or 0
        row["pace_min_km"] = pace(spd)
        elapsed = row.get("sumElapsedDuration") or 0
        row["elapsed_hms"] = hms(elapsed)
        cad = row.get("directRunCadence") or row.get("directDoubleCadence") or 0
        row["cadence_spm"] = int(cad)
        dist = row.get("sumDistance") or 0
        row["distance_km"] = round(dist / 1000, 3)
        # Flag warmup/cooldown: pace slower than 9:00/km or cadence < 100
        row["is_running"] = (spd > 1.85 and cad >= 100)

    # Reorder: put human-readable columns first
    priority = ["elapsed_hms", "sumElapsedDuration", "distance_km", "pace_min_km",
                "cadence_spm", "directHeartRate", "directAltitude",
                "directStrideLength", "directVerticalOscillation",
                "directGroundContactTime", "directPower"]
    all_keys = list(rows[0].keys())
    ordered = [k for k in priority if k in all_keys] + [k for k in all_keys if k not in priority]

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=ordered, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)

# ─── summary text ──────────────────────────────────────────────────────────────

def build_summary(api, activity):
    act_id = activity["activityId"]
    detail = api.get_activity(act_id)
    s = detail.get("summaryDTO", {})

    avg_spd = s.get("averageSpeed") or 0
    max_spd = s.get("maxSpeed") or 0
    dist = s.get("distance") or 0
    dur = s.get("duration") or 0
    avg_cad = s.get("averageRunCadence") or 0
    max_cad = s.get("maxRunCadence") or 0

    # Per-km splits
    splits_lines = []
    try:
        splits = api.get_activity_splits(act_id)
        for i, lap in enumerate(splits.get("lapDTOs", []), 1):
            spd = lap.get("averageSpeed") or 0
            c = lap.get("averageRunCadence") or 0
            splits_lines.append(
                f"  ק\"מ {i}: {pace(spd)} | דופק {lap.get('averageHR','?')} | "
                f"קאדנס {c:.0f} spm | עלייה {lap.get('totalAscent','?')}מ'"
            )
    except Exception:
        splits_lines = ["  לא זמין"]

    # HR zones
    zones_lines = []
    try:
        zones = api.get_activity_hr_in_timezones(act_id)
        for z in zones:
            mins = int(z["secsInZone"] // 60)
            zones_lines.append(f"  Zone {z['zoneNumber']} (>{z['zoneLowBoundary']} bpm): {mins} דקות")
    except Exception:
        pass

    # Compute running-only stats from activity details (exclude warmup/cooldown)
    try:
        det = api.get_activity_details(act_id, maxchart=10000)
        desc = {d["metricsIndex"]: d["key"] for d in det.get("metricDescriptors", [])}
        run_spds, run_hrs, run_cads = [], [], []
        for pt in det.get("activityDetailMetrics", []):
            row = {desc.get(i, ""): v for i, v in enumerate(pt.get("metrics", []))}
            spd = row.get("directSpeed") or 0
            cad = row.get("directRunCadence") or row.get("directDoubleCadence") or 0
            hr  = row.get("directHeartRate") or 0
            if spd > 1.85 and cad >= 100:
                run_spds.append(spd); run_hrs.append(hr); run_cads.append(cad)
        run_note = ""
        if run_spds:
            run_avg_pace = pace(sum(run_spds) / len(run_spds))
            run_avg_hr   = round(sum(run_hrs) / len(run_hrs))
            run_avg_cad  = round(sum(run_cads) / len(run_cads))
            run_secs     = len(run_spds)
            run_note = (f"\nריצה בלבד (ללא חימום/הרפיה — {run_secs//60}:{run_secs%60:02d} דקות):\n"
                        f"  קצב: {run_avg_pace} | דופק: {run_avg_hr} | קאדנס: {run_avg_cad} spm")
    except Exception:
        run_note = ""

    return f"""=== ריצה {activity['startTimeLocal'][:10]} {activity['startTimeLocal'][11:16]} ===

מרחק:           {dist/1000:.2f} ק"מ
זמן כולל:       {hms(dur)}
קצב ממוצע:      {pace(avg_spd)} /ק"מ (כולל חימום/הרפיה)
קצב מהיר ביותר:{pace(max_spd)} /ק"מ
דופק ממוצע:     {s.get('averageHR','N/A')} bpm
דופק מקסימלי:   {s.get('maxHR','N/A')} bpm
דופק מינימלי:   {s.get('minHR','N/A')} bpm
קאדנס ממוצע:    {avg_cad:.0f} spm
קאדנס מקסימלי:  {max_cad:.0f} spm{run_note}
אורך צעד:       {s.get('strideLength','N/A')} ס"מ
תנודה אנכית:    {s.get('verticalOscillation','N/A')} ס"מ
יחס אנכי:       {s.get('verticalRatio','N/A')} %
זמן מגע קרקע:   {s.get('groundContactTime','N/A')} ms
עלייה כוללת:    {s.get('totalAscent','N/A')} מ'
ירידה כוללת:    {s.get('totalDescent','N/A')} מ'
קלוריות:        {s.get('calories','N/A')}
Body Battery:   {s.get('differenceBodyBattery','N/A')}
TE אירובי:       {s.get('trainingEffect','N/A')} — {s.get('trainingEffectLabel','')}
TE אנאירובי:     {s.get('anaerobicTrainingEffect','N/A')}
עומס אימון:     {s.get('activityTrainingLoad','N/A')}
VO2max:         {s.get('vo2MaxValue','N/A')}

=== ספליטים לפי ק"מ ===
{chr(10).join(splits_lines)}

=== אזורי דופק ===
{chr(10).join(zones_lines) or '  לא זמין'}
"""

# ─── Google Drive via rclone ───────────────────────────────────────────────────

RCLONE = r"C:\Users\amich\AppData\Local\Microsoft\WinGet\Packages\Rclone.Rclone_Microsoft.Winget.Source_8wekyb3d8bbwe\rclone-v1.74.3-windows-amd64\rclone.exe"

def upload_to_drive(local_path, filename):
    import subprocess
    dest = f"gdrive:{DRIVE_FOLDER}/{filename}"
    subprocess.run([RCLONE, "copyto", local_path, dest], check=True)
    result = subprocess.run([RCLONE, "link", dest], capture_output=True, text=True, check=True)
    return result.stdout.strip()


# ─── main ──────────────────────────────────────────────────────────────────────

def main(bob_mode=False):
    api = connect()

    # Only running activities
    activities = api.get_activities(0, 20)
    activity = next(
        (a for a in activities if "running" in a["activityType"]["typeKey"].lower()),
        None
    )
    if not activity:
        print("לא נמצאה ריצה אחרונה.")
        return

    act_id = activity["activityId"]
    date_str = activity["startTimeLocal"][:10]
    if not bob_mode:
        print(f"ריצה: {date_str} — {activity.get('activityName', '')}")

    # Save CSV to temp, then upload to Drive
    tmp = os.path.join(os.path.expanduser("~/.garmin_tokens"), f"run_{date_str}.csv")
    n = export_csv(api, act_id, tmp, silent=bob_mode)
    if not bob_mode:
        print(f"  {n} נקודות נתונים")

    summary = build_summary(api, activity)

    filename = f"run_{date_str}.csv"
    if not bob_mode:
        print("מעלה ל-Google Drive...")
    link = upload_to_drive(tmp, filename)
    os.remove(tmp)

    if bob_mode:
        # Bob gets only what's needed for WhatsApp
        run_date = activity["startTimeLocal"][:10]
        print(f"ריצה {run_date} נשמרה בדרייב!\n{link}")
    else:
        print(summary)
        print(f"\n📁 הריצה נשמרה ב-Google Drive / {DRIVE_FOLDER}:\n{link}")


if __name__ == "__main__":
    main(bob_mode="--bob" in sys.argv)
