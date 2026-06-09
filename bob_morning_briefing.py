"""
Morning briefing — daily at 07:15. Always sends.
Combines Garmin fitness data + calendar + tasks + weather into a Hebrew WhatsApp brief.
"""
import sys, os, json, subprocess, urllib.request, datetime
sys.stdout.reconfigure(encoding="utf-8")
from groq import Groq
from config import GROQ_API_KEY, DATA_PATH

BRIEFING_API = "https://fantastic-waddle-coral.vercel.app/api/bot/briefing"
GCAL_PATH    = r"C:\Users\amich\Projects\garmin\bob-scripts\gcal.py"
WEATHER_URL  = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=31.9516&longitude=34.8978"
    "&hourly=temperature_2m"
    "&daily=temperature_2m_max,temperature_2m_min"
    "&forecast_days=1&timezone=Asia%2FJerusalem"
)

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


def get_calendar(days_ahead=0):
    try:
        res = subprocess.run(
            ["python", GCAL_PATH, str(days_ahead)],
            capture_output=True, text=True, timeout=15, encoding="utf-8"
        )
        raw = res.stdout.strip()
        return json.loads(raw) if raw else []
    except Exception:
        return []


def format_context(garmin, briefing, gcal, weather):
    parts = []

    # Fitness data
    sleep      = garmin.get("sleep_hours", 0)
    sleep_sc   = garmin.get("sleep_score", 0)
    hrv_data   = garmin.get("hrv", {}) or {}
    hrv        = hrv_data.get("last_night_avg")
    hrv_low    = hrv_data.get("baseline_low")
    hrv_high   = hrv_data.get("baseline_high")
    bb         = garmin.get("body_battery_current", 0)
    stress     = garmin.get("stress_avg", 0)
    tr         = garmin.get("training_readiness") or {}
    readiness  = tr.get("score") if isinstance(tr, dict) else None

    fitness = []
    if sleep:
        fitness.append(f"שינה: {sleep}ש׳ (ציון {sleep_sc})")
    if hrv:
        arrow = "↑" if (hrv_high and hrv > hrv_high) else ("↓" if (hrv_low and hrv < hrv_low) else "→")
        fitness.append(f"HRV: {hrv} {arrow} (בסיס {hrv_low}–{hrv_high})")
    if bb:
        fitness.append(f"Body Battery: {bb}%")
    if stress:
        fitness.append(f"סטרס: {stress}")
    if readiness:
        fitness.append(f"מוכנות: {readiness}/100")
    if fitness:
        parts.append("כושר: " + " | ".join(fitness))

    # Alert flags for emphasis
    alerts = []
    if sleep and 0 < sleep < 6:
        alerts.append(f"שינה קצרה ({sleep}ש׳)")
    if hrv and hrv_low and hrv < hrv_low:
        alerts.append(f"HRV נמוך ({hrv})")
    if bb and bb < 40:
        alerts.append(f"BB נמוך ({bb}%)")
    if stress > 60:
        alerts.append(f"סטרס גבוה ({stress})")
    if alerts:
        parts.append("⚠️ התראות: " + ", ".join(alerts))

    # Weather
    if weather and not weather.get("error"):
        h  = weather.get("hourly", {}).get("temperature_2m", [])
        mx = (weather.get("daily") or {}).get("temperature_2m_max", [None])[0]
        if h and mx is not None:
            t7, t12, t18 = h[7], h[12], h[18]
            if mx >= 30:   tip = "חם — שתייה מרובה"
            elif mx >= 25: tip = "נעים עד חם"
            elif mx >= 20: tip = "חולצה, לא צריך ז'קט"
            elif mx >= 15: tip = "קח ז'קט קליל"
            else:          tip = "קר — התלבש חם"
            parts.append(f"מזג אוויר: {t7}° בוקר / {t12}° צהריים / {t18}° ערב — {tip}")

    # Calendar (today only)
    today_events = [e for e in gcal if e.get("day") == "היום"]
    if today_events:
        ev = [f"{e['time']} {e['summary']}" if e.get("time") else e["summary"] for e in today_events[:4]]
        parts.append("יומן: " + "; ".join(ev))

    # Tasks
    if briefing and not briefing.get("error"):
        overdue  = briefing.get("tasks", {}).get("overdue", [])
        upcoming = briefing.get("tasks", {}).get("upcoming", [])
        tasks = [f"[דחוף] {t['title']}" for t in overdue] + [t["title"] for t in upcoming]
        if tasks:
            parts.append("משימות: " + " | ".join(tasks[:5]))

        items = briefing.get("shopping", {}).get("items", [])
        if items:
            parts.append("קניות: " + ", ".join(i["text"] for i in items[:4]))

    return "\n".join(parts)


def generate_brief(context):
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": (
                "אתה בוב, העוזר האישי של עמיחי. צור בריף בוקר קצר לווטסאפ בעברית.\n"
                "חוק ברזל: השתמש אך ורק בנתונים שמופיעים בקונטקסט. אל תמציא, אל תשער, אל תוסיף.\n\n"
                "מבנה קבוע (עד 12 שורות):\n"
                "שורה 1: ברכת בוקר (משפט אחד)\n"
                "שורות 2-3: נתוני כושר עם אייקונים (💤 שינה, ⚡ BB, 🧠 HRV, 🎯 מוכנות). "
                "אם יש ⚠️ התראות — הדגש אותן.\n"
                "שורות 4-5: אירועי יומן — רק אם מופיע 'יומן:' בנתונים. "
                "אם אין 'יומן:' בנתונים — דלג על שורות אלה לחלוטין. אסור להמציא אירועים.\n"
                "שורות 6-7: משימות — רק אם מופיע 'משימות:' בנתונים. "
                "אם אין — דלג. אסור להמציא משימות.\n"
                "שורה 8: המלצה אחת (כושר / אנרגיה / מה לעשות) — מבוסס על נתוני הכושר בלבד.\n"
                "שורה 9: ↩️ השב לי כדי לצלול לנושא\n"
                "ללא ** או ## או markdown."
            )},
            {"role": "user", "content": context},
        ],
        max_tokens=350,
    )
    return resp.choices[0].message.content.strip()


def main():
    freshness_warn = garmin_freshness_warning()

    garmin   = load_garmin()
    briefing = fetch_json(BRIEFING_API, headers={"Authorization": "Bearer homebase-bot-2025"})
    gcal     = get_calendar(days_ahead=0)
    weather  = fetch_json(WEATHER_URL)

    context = format_context(garmin, briefing, gcal, weather)
    if freshness_warn:
        context = freshness_warn + "\n" + context

    brief = generate_brief(context)
    if freshness_warn:
        brief = freshness_warn + "\n" + brief
    print(brief)


if __name__ == "__main__":
    main()
