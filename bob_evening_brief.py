"""
Evening briefing — daily at 20:00. Always sends.
Summarizes today and prepares for tomorrow.
"""
import sys, os, json, subprocess, urllib.request, datetime
sys.stdout.reconfigure(encoding="utf-8")
from groq import Groq
from config import GROQ_API_KEY, DATA_PATH

BRIEFING_API = "https://fantastic-waddle-coral.vercel.app/api/bot/briefing"
GCAL_PATH    = r"C:\Users\amich\Projects\garmin\bob-scripts\gcal.py"
PLAN_CACHE   = os.path.join(os.path.expanduser("~"), "OneDrive", "garmin-data", "weekly_plan.json")

client = Groq(api_key=GROQ_API_KEY)


def fetch_json(url, headers=None):
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception:
        return {}


def load_garmin():
    try:
        with open(DATA_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def garmin_freshness_warning():
    try:
        mtime = os.path.getmtime(DATA_PATH)
        age_h = (datetime.datetime.now().timestamp() - mtime) / 3600
        if age_h > 24:
            return f"⚠️ נתוני גרמין לא עודכנו ({int(age_h)} שעות) — סנכרן OneDrive"
    except Exception:
        return "⚠️ קובץ גרמין לא נמצא — בדוק OneDrive"
    return None


def get_calendar(days_ahead=1):
    try:
        res = subprocess.run(
            ["python", GCAL_PATH, str(days_ahead)],
            capture_output=True, text=True, timeout=15, encoding="utf-8"
        )
        raw = res.stdout.strip()
        return json.loads(raw) if raw else []
    except Exception:
        return []


def get_tomorrow_workout():
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    try:
        with open(PLAN_CACHE, encoding="utf-8") as f:
            cache = json.load(f)
        entry = cache.get("plan", {}).get(tomorrow)
        return entry.get("label", "") if entry else ""
    except Exception:
        return ""


def format_context(garmin, briefing, gcal):
    parts = []

    # Today's summary
    steps      = garmin.get("steps", 0)
    calories   = garmin.get("calories_total", 0)
    stress     = garmin.get("stress_avg", 0)
    bb         = garmin.get("body_battery_current", 0)
    activities = garmin.get("activities", [])

    today = datetime.date.today().isoformat()
    today_acts = [a for a in activities if a.get("date") == today]
    if today_acts:
        a = today_acts[0]
        act_str = f"{a.get('type', '')} {a.get('duration_min', 0)} דקות"
        if a.get("distance_km"):
            act_str += f" / {a['distance_km']} ק״מ"
        parts.append(f"אימון היום: {act_str}")

    today_summary = []
    if steps:
        today_summary.append(f"צעדים: {steps:,}")
    if calories:
        today_summary.append(f"קלוריות: {calories}")
    if stress:
        today_summary.append(f"סטרס: {stress}")
    if bb:
        today_summary.append(f"BB: {bb}%")
    if today_summary:
        parts.append("סיכום: " + " | ".join(today_summary))

    # Tomorrow
    tomorrow_events = [e for e in gcal if e.get("day") == "מחר"]
    if tomorrow_events:
        ev = [f"{e['time']} {e['summary']}" if e.get("time") else e["summary"] for e in tomorrow_events[:4]]
        parts.append("מחר ביומן: " + "; ".join(ev))

    workout = get_tomorrow_workout()
    if workout:
        parts.append(f"אימון מחר: {workout}")

    # Pending tasks
    if briefing and not briefing.get("error"):
        overdue  = briefing.get("tasks", {}).get("overdue", [])
        upcoming = briefing.get("tasks", {}).get("upcoming", [])
        tasks = [f"[דחוף] {t['title']}" for t in overdue] + [t["title"] for t in upcoming[:3]]
        if tasks:
            parts.append("משימות פתוחות: " + " | ".join(tasks[:4]))

    return "\n".join(parts)


def generate_brief(context):
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": (
                "אתה בוב, העוזר האישי של עמיחי. צור בריף ערב קצר לווטסאפ בעברית.\n"
                "מבנה (עד 10 שורות):\n"
                "שורה 1: ברכת ערב\n"
                "שורות 2-3: סיכום היום (אימון, צעדים, BB)\n"
                "שורות 4-5: מחר — יומן + אימון\n"
                "שורות 6-7: משימות שנשארו (⚠️ לדחופות)\n"
                "שורה 8: המלצה אחת לערב / להכנה למחר\n"
                "ללא ** או ## או markdown."
            )},
            {"role": "user", "content": context},
        ],
        max_tokens=250,
    )
    return resp.choices[0].message.content.strip()


def main():
    freshness_warn = garmin_freshness_warning()

    garmin   = load_garmin()
    briefing = fetch_json(BRIEFING_API, headers={"Authorization": "Bearer homebase-bot-2025"})
    gcal     = get_calendar(days_ahead=1)

    context = format_context(garmin, briefing, gcal)
    if freshness_warn:
        context = freshness_warn + "\n" + context

    brief = generate_brief(context)
    if freshness_warn:
        brief = freshness_warn + "\n" + brief
    print(brief)


if __name__ == "__main__":
    main()
