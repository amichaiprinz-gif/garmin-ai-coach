# -*- coding: utf-8 -*-
"""
Sunday 19:30 — generates weekly training plan:
  1. Analyzes last week (Groq LLM)
  2. Builds structured plan for coming week based on Training Readiness
  3. Pushes workouts to Garmin watch
  4. Saves weekly_plan.json + weekly_report.txt (WhatsApp-ready)
"""
import sys, os, json, re
from datetime import date, timedelta
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

from groq import Groq
from config import GROQ_API_KEY, DATA_PATH
from metrics import get_metrics

client = Groq(api_key=GROQ_API_KEY)
MODEL = "openai/gpt-oss-120b"

PLAN_CACHE  = os.path.join(os.path.expanduser("~"), "OneDrive", "garmin-data", "weekly_plan.json")
REPORT_CACHE = os.path.join(os.path.expanduser("~"), "OneDrive", "garmin-data", "latest_report.txt")

DAY_HE = {0:"שני",1:"שלישי",2:"רביעי",3:"חמישי",4:"שישי",5:"שבת",6:"ראשון"}

# weekday(): 0=Mon 1=Tue 2=Wed 3=Thu 4=Fri 5=Sat 6=Sun
SCHEDULE = {
    6: ("strength_upper", "חזה + כתפיים + טריצפס + בטן"),
    0: ("strength_back",  "גב + ביצפס + בטן"),
    1: ("intervals",      "ריצת אינטרוולים"),
    2: ("strength_legs",  "רגליים + ישבן + בטן"),
    3: ("strength_arms",  "בטן + ידיים"),
    4: ("walk",           "הליכה קלה"),
    5: ("long_run",       "ריצה ארוכה"),
}


def load_data():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_history():
    try:
        from supabase import create_client
        from config import SUPABASE_URL, SUPABASE_KEY
        sb = create_client(SUPABASE_URL, SUPABASE_KEY)
        rows = (sb.table("garmin_daily")
                .select("date,steps,resting_hr,sleep_hours,sleep_score,hrv_last_night")
                .order("date", desc=True).limit(14).execute().data)
        if not rows:
            return ""
        lines = ["היסטוריה 14 ימים:"]
        for r in reversed(rows):
            lines.append(f"  {r['date']}: שינה={r.get('sleep_hours','?')}h | דופק={r.get('resting_hr','?')} | HRV={r.get('hrv_last_night','?')}")
        return "\n".join(lines)
    except Exception:
        return ""


def load_workout_feedback():
    try:
        import requests
        r = requests.get(
            "https://fantastic-waddle-coral.vercel.app/api/bot/memory",
            headers={"Authorization": "Bearer homebase-bot-2025"}, timeout=5
        )
        items = [i for i in r.json() if i.get("key","").startswith("workout_feedback_")]
        if not items:
            return ""
        lines = ["פידבק מאימונים:"]
        for i in sorted(items, key=lambda x: x["key"])[-3:]:
            lines.append(f"  {i['value']}")
        return "\n".join(lines)
    except Exception:
        return ""


def determine_load(recovery: int) -> dict:
    """Return training load params based on Training Readiness score."""
    if recovery >= 75:
        return {"sets": 3, "run_min": 55, "intervals": 6, "intensity": "מלא"}
    elif recovery >= 50:
        return {"sets": 3, "run_min": 45, "intervals": 4, "intensity": "בינוני"}
    else:
        return {"sets": 2, "run_min": 35, "intervals": 3, "intensity": "קל"}


def week_dates():
    """Return [Sun, Mon, Tue, Wed, Thu, Fri, Sat] starting this Sunday."""
    today = date.today()
    days_since_sunday = (today.weekday() + 1) % 7
    sunday = today - timedelta(days=days_since_sunday)
    return [sunday + timedelta(days=i) for i in range(7)]


def build_plan(load: dict) -> dict:
    """Build structured weekly plan dict keyed by ISO date string."""
    plan = {}
    for d in week_dates():
        wday = d.weekday()
        wtype, label = SCHEDULE.get(wday, ("rest", "מנוחה"))
        entry = {
            "weekday": DAY_HE[wday],
            "date_fmt": d.strftime("%d.%m"),
            "type": wtype,
            "label": label,
            "sets": load["sets"],
        }
        if wtype == "intervals":
            entry["intervals"] = load["intervals"]
        if wtype == "long_run":
            entry["run_min"] = load["run_min"]
        plan[d.isoformat()] = entry
    return plan


def generate_analysis(data: dict, m: dict, history: str, feedback: str) -> str:
    """Call Groq for last-week analysis only (not workout plan)."""
    activities_json = json.dumps(data.get("activities", [])[:7], ensure_ascii=False)
    tr = data.get("training_readiness", {})

    system = f"""אתה מאמן כושר של עמיחי. נתח את השבוע שעבר בעברית פשוטה.
ציוד: משקולת 7.5 ק"ג + מזרן בלבד.
Recovery: {m.get('recovery_score','?')}/100 ({tr.get('level','')}) | CTL={m['ctl']} | ATL={m['atl']} | TSB={m['tsb']}

{history}
{feedback}

אימונים אחרונים:
{activities_json}"""

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": """כתוב ניתוח קצר של השבוע שעבר — 3-4 נקודות בלבד:
• מה עבד טוב
• מה דרש שיפור
• מגמה אחת (עולה/יורדת) אם יש
• משפט מסכם אחד

עברית פשוטה, ישירה. ללא כותרות מרובות. עד 120 מילים."""}
        ],
    )
    return resp.choices[0].message.content.strip()


def format_whatsapp(plan: dict, analysis: str, m: dict, load: dict) -> str:
    tr_level = {"HIGH": "גבוה 💪", "MODERATE": "בינוני 👍", "LOW": "נמוך ⚠️"}.get(
        m.get("recovery_source") and "HIGH", "")

    lines = [
        f"*דוח שבועי — עמיחי* 🏋️",
        "",
        f"📊 *מצב הכושר*",
        f"Recovery: *{m.get('recovery_score','?')}/100*  |  TSB: {m['tsb']} ({m['tsb_hebrew']})",
        f"עומס שבועי: {'גבוה מדי ⚠️' if m.get('acwr',0) and m['acwr'] > 1.5 else 'תקין ✅'}",
        "",
        f"*ניתוח השבוע שעבר*",
        analysis,
        "",
        f"*תכנית השבוע הקרוב* ({load['intensity']})",
    ]

    for d_str, entry in sorted(plan.items()):
        wtype = entry["type"]
        label = entry["label"]
        day = entry["weekday"]
        date_fmt = entry["date_fmt"]

        if wtype in ("strength_upper","strength_back","strength_legs","strength_arms"):
            detail = f"{entry['sets']} סטים"
        elif wtype == "intervals":
            detail = f"{entry['intervals']} × 400מ'"
        elif wtype == "long_run":
            detail = f"{entry['run_min']} דקות"
        elif wtype == "walk":
            detail = "הליכה קלה 30-45 דקות"
        else:
            detail = "מנוחה"

        emoji = {"strength_upper":"💪","strength_back":"🔙","strength_legs":"🦵",
                 "strength_arms":"💪","intervals":"🏃","long_run":"🏃","walk":"🚶"}.get(wtype,"📅")
        lines.append(f"{emoji} *{day} {date_fmt}* — {label} ({detail})")

    lines += ["", "✅ האימונים נשלחו לשעון"]
    return "\n".join(lines)


def push_to_garmin(plan: dict, load: dict):
    try:
        from garmin_push import push_from_plan
        push_from_plan(plan, load)
        return True
    except Exception as e:
        print(f"שגיאת דחיפה לגרמין: {e}", file=sys.stderr)
        return False


def main():
    data = load_data()
    m = get_metrics(data)
    recovery = m.get("recovery_score", 60)
    load = determine_load(recovery)
    history = load_history()
    feedback = load_workout_feedback()

    plan = build_plan(load)
    analysis = generate_analysis(data, m, history, feedback)
    report = format_whatsapp(plan, analysis, m, load)

    # Push to Garmin watch
    push_to_garmin(plan, load)

    # Save caches
    os.makedirs(os.path.dirname(PLAN_CACHE), exist_ok=True)
    with open(PLAN_CACHE, "w", encoding="utf-8") as f:
        json.dump({"generated": date.today().isoformat(), "load": load, "plan": plan}, f,
                  indent=2, ensure_ascii=False)
    with open(REPORT_CACHE, "w", encoding="utf-8") as f:
        f.write(report)

    print(report)


def send_cached():
    if not os.path.exists(REPORT_CACHE):
        print("⚠️ דוח לא נמצא")
        return
    with open(REPORT_CACHE, encoding="utf-8") as f:
        print(f.read())


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "send":
        send_cached()
    else:
        main()
