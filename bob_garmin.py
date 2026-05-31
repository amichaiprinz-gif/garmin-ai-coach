"""
Bob's Garmin AI — powered by Groq (free tier).
Reads Garmin data from the shared OneDrive folder.

Usage:
  python bob_garmin.py           → interactive Q&A
  python bob_garmin.py report    → weekly report
  python bob_garmin.py plan      → 4-week progressive training plan
  python bob_garmin.py push      → push this week's workouts to Garmin watch
"""

import sys, os, json
from groq import Groq
from supabase import create_client
from metrics import get_metrics
from weather import get_weather, weather_summary

from config import GROQ_API_KEY, SUPABASE_URL, SUPABASE_KEY, DATA_PATH

client = Groq(api_key=GROQ_API_KEY)
sb = create_client(SUPABASE_URL, SUPABASE_KEY)
MODEL = "openai/gpt-oss-120b"


def load_data() -> dict:
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"No data at {DATA_PATH} — run garmin_data.py on the work computer first.")
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_history() -> str:
    try:
        rows = (sb.table("garmin_daily")
                .select("date,steps,resting_hr,stress_avg,body_battery_current,sleep_hours,sleep_score,hrv_last_night,hrv_status_text,vo2max")
                .order("date", desc=True)
                .limit(28)
                .execute().data)
        if not rows:
            return ""
        lines = ["=== היסטוריה (28 ימים אחרונים) ==="]
        for r in reversed(rows):
            lines.append(
                f"  {r['date']}: צעדים={r.get('steps','?')} | דופק מנוחה={r.get('resting_hr','?')} | "
                f"סטרס={r.get('stress_avg','?')} | BB={r.get('body_battery_current','?')} | "
                f"שינה={r.get('sleep_hours','?')}h | HRV={r.get('hrv_last_night','?')} ({r.get('hrv_status_text','?')})"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"(היסטוריה לא זמינה: {e})"


def build_system_prompt(data: dict) -> str:
    activities_json = json.dumps(data.get("activities", []), indent=2, ensure_ascii=False)
    history = load_history()
    w = get_weather()
    weather_text = weather_summary(w)
    try:
        m = get_metrics(data)
        metrics_text = (
            f"CTL={m['ctl']} | ATL={m['atl']} | TSB={m['tsb']} ({m['tsb_hebrew']}) | "
            f"ACWR={m.get('acwr','N/A')} ({m['acwr_hebrew']})"
        )
        if "recovery_score" in m:
            metrics_text += (
                f"\nRecovery Score: {m['recovery_score']}/100 — {m['recovery_hebrew']}"
                f" (שינה={m['components']['sleep']}/35 | HRV={m['components']['hrv']}/35 | "
                f"דופק={m['components']['resting_hr']}/20 | סטרס={m['components']['stress']}/10)"
            )
    except Exception as e:
        metrics_text = f"(מדדים לא זמינים: {e})"

    return f"""אתה מאמן כושר מקצועי ואנליסט נתוני ספורט של אמיחי. יש לך גישה לנתוני הגרמין המלאים שלו.
ענה בעברית. היה ישיר, מקצועי, וספציפי — אל תהיה מחמיא.

=== מדדי עומס אימון (CTL/ATL/TSB/ACWR/Recovery) ===
{metrics_text}

=== מזג אוויר (תל אביב) ===
{weather_text}


{history}


=== נתוני יום ({data['date']}) ===
צעדים: {data.get('steps', 'N/A')}
קלוריות: {data.get('calories', 'N/A')}
סטרס ממוצע: {data.get('stress', 'N/A')}
Body Battery: {data.get('body_battery', 'N/A')}
דופק מנוחה: {data.get('resting_hr', 'N/A')} bpm

=== שינה אמש ===
משך: {data.get('sleep_hours', 'N/A')} שעות | ציון: {data.get('sleep_score', 'N/A')}

=== אימונים אחרונים (נתונים מלאים) ===
{activities_json}

--- מידע על שדות ---
training_effect_aerobic: 0-5 (0=אין, 1=שחזור, 2=בסיס, 3=שיפור, 4=פיתוח, 5=עומס יתר)
training_effect_anaerobic: 0-5 (אותה סקלה לאנאירובי)
training_load: עומס האימון הכולל
body_battery_used: כמה Body Battery נצרך באימון
"""


def generate_report(data: dict) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": build_system_prompt(data)},
            {"role": "user", "content": """צור דוח שבועי מקצועי עבור אמיחי המורכב משני חלקים:

---
## חלק א׳ — ניתוח השבוע שעבר

נתח את כל הנתונים לעומק: Training Effect, zones דופק, עומס, Body Battery, HRV, תזמון בין אימונים.
אל תהיה גנרי — התייחס לנתונים הספציפיים שלפניך. מה עבד, מה לא יעיל, מה בעייתי ולמה.
היה ישיר. אם משהו גרוע — אמור את זה.
אם יש היסטוריה — זהה מגמות (HRV עולה/יורד? דופק מנוחה משתנה? עומס מצטבר?).

---
## חלק ב׳ — תכנית לשבוע הקרוב

המבנה השבועי קבוע — אל תשנה אותו:
- שבת: ריצה ארוכה
- ראשון: כוח — חזה + כתפיים + טריצפס + בטן
- שני: כוח — גב + ביצפס + בטן
- שלישי: ריצה עם אינטרוולים
- רביעי: כוח — רגליים + ישבן + בטן
- חמישי: מנוחה
- שישי: מנוחה / הליכה קלה

**מה כן משתנה לפי הנתונים:**
- משך ועצימות כל אימון (לפי HRV, Body Battery, עומס שבוע שעבר)
- תרגילים ספציפיים לכל אימון כוח (לפי מה שחסר, מה שעבד, מה שצריך חיזוק)
- כמות סטים/חזרות ומשקל יחסי (לפי רמת התאוששות)
- דופק יעד לריצות (לפי TE ו-zones של השבוע שעבר)
- אורך ומספר האינטרוולים ביום שלישי

חשוב: אמיחי רוצה להוריד כרס — כלול בכל אימון כוח לפחות 3 תרגילי בטן מגוונים ומפורטים.
לכל יום: פרט תרגילים ספציפיים, סטים, חזרות, דופק יעד או עצימות, ולמה בחרת בזה.

חובה: ענה בעברית בלבד. עד 500 מילים."""},
        ],
    )
    return response.choices[0].message.content


def chat_mode(data: dict):
    system = build_system_prompt(data)
    messages = [{"role": "system", "content": system}]
    print(f"\nבוב מוכן. נתונים מ-{data['date']}. הקלד 'יציאה' לסיום.\n")

    while True:
        user_input = input("אתה: ").strip()
        if user_input.lower() in ("יציאה", "exit", "quit", "q"):
            break
        if not user_input:
            continue
        messages.append({"role": "user", "content": user_input})
        response = client.chat.completions.create(model=MODEL, messages=messages)
        reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})
        print(f"\nבוב: {reply}\n")


def generate_4week_plan(data: dict) -> str:
    system = build_system_prompt(data)
    prompt = """בנה תוכנית אימונים ל-4 שבועות קדימה עבור אמיחי.

עקרונות periodization:
- שבוע 1: עומס בסיס (לפי הנתונים הנוכחיים)
- שבוע 2: +10% עומס
- שבוע 3: +20% עומס
- שבוע 4: deload — -30% (התאוששות)

המבנה הקבוע לכל שבוע:
שבת=ריצה ארוכה | ראשון=חזה+כתפיים+טריצפס+בטן | שני=גב+ביצפס+בטן |
שלישי=אינטרוולים | רביעי=רגליים+ישבן+בטן | חמישי=מנוחה | שישי=הליכה

לכל שבוע ציין:
- אורך הריצה הארוכה (דקות)
- מספר/אורך האינטרוולים
- משקל יחסי באימוני כוח (% מ-1RM)
- כמות הסטים

בסס את שבוע 1 על CTL/ATL/TSB/Recovery Score הנוכחיים.
ענה בעברית, טבלה ברורה לכל שבוע. עד 400 מילים."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "chat"
    data = load_data()

    if mode == "report":
        print(generate_report(data))
    elif mode == "plan":
        print(generate_4week_plan(data))
    elif mode == "push":
        from garmin_push import push_week
        from metrics import get_metrics
        m = get_metrics(data)
        recovery = m.get("recovery_score", 60)
        # Adjust intensity based on recovery score
        long_run_min  = 55 if recovery >= 65 else 40
        intervals     = 6  if recovery >= 65 else 4
        interval_sec  = 400
        strength_min  = 40 if recovery >= 65 else 30
        hr_high       = 155 if recovery >= 50 else 145
        print(f"Recovery Score: {recovery}/100 — מתאים עומס לפי זה")
        result = push_week(long_run_min, intervals, interval_sec, strength_min, hr_high)
        print(result)
    else:
        chat_mode(data)
