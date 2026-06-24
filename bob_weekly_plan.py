# -*- coding: utf-8 -*-
"""
Sunday — summarizes last week's actual training. Amichai builds his own
workout plan; this script never generates or pushes one.
"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

from groq import Groq
from config import GROQ_API_KEY, DATA_PATH
from metrics import get_metrics

client = Groq(api_key=GROQ_API_KEY)
MODEL = "openai/gpt-oss-120b"

REPORT_CACHE = os.path.join(os.path.expanduser("~"), "OneDrive", "garmin-data", "latest_report.txt")


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


def generate_analysis(data: dict, m: dict, history: str, feedback: str) -> str:
    """Summarize last week's actual workouts (no plan, no recommendation for next week)."""
    activities_json = json.dumps(data.get("activities", [])[:7], ensure_ascii=False)
    tr = data.get("training_readiness", {})

    system = f"""אתה מאמן כושר של עמיחי. סכם את כל האימונים שהוא עשה בשבוע שעבר, בעברית פשוטה.
Recovery: {m.get('recovery_score','?')}/100 ({tr.get('level','')}) | CTL={m['ctl']} | ATL={m['atl']} | TSB={m['tsb']}

{history}
{feedback}

אימונים אחרונים:
{activities_json}"""

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": """כתוב סיכום של האימונים שהיו השבוע שעבר — 3-4 נקודות בלבד:
• אילו אימונים בוצעו ומה הייתה התוצאה
• מה עבד טוב / מה דרש שיפור
• מגמה אחת (עולה/יורדת) אם יש
• משפט מסכם אחד

עברית פשוטה, ישירה. אל תמליץ או תתכנן את השבוע הקרוב. ללא כותרות מרובות. עד 120 מילים."""}
        ],
    )
    return resp.choices[0].message.content.strip()


def format_whatsapp(analysis: str, m: dict) -> str:
    lines = [
        f"*סיכום שבועי — עמיחי* 🏋️",
        "",
        f"📊 *מצב הכושר*",
        f"Recovery: *{m.get('recovery_score','?')}/100*  |  TSB: {m['tsb']} ({m['tsb_hebrew']})",
        f"עומס שבועי: {'גבוה מדי ⚠️' if m.get('acwr',0) and m['acwr'] > 1.5 else 'תקין ✅'}",
        "",
        f"*סיכום האימונים בשבוע שעבר*",
        analysis,
    ]
    return "\n".join(lines)


def main():
    data = load_data()
    m = get_metrics(data)
    history = load_history()
    feedback = load_workout_feedback()

    analysis = generate_analysis(data, m, history, feedback)
    report = format_whatsapp(analysis, m)

    os.makedirs(os.path.dirname(REPORT_CACHE), exist_ok=True)
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
