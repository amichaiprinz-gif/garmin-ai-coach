# -*- coding: utf-8 -*-
"""
Bob's Garmin AI — powered by Groq (free tier).
Reads Garmin data from the shared OneDrive folder.

Usage:
  python bob_garmin.py           → interactive Q&A
  python bob_garmin.py report    → weekly report
  python bob_garmin.py plan      → 4-week progressive training plan
  python bob_garmin.py push      → push this week's workouts to Garmin watch
"""

import sys, os, json, requests
from groq import Groq
from supabase import create_client
from metrics import get_metrics
from weather import get_weather, weather_summary

from config import GROQ_API_KEY, SUPABASE_URL, SUPABASE_KEY, DATA_PATH, HOMEBASE_API_URL, HOMEBASE_API_TOKEN

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


def load_workout_feedback() -> str:
    if not HOMEBASE_API_URL:
        return ""
    try:
        r = requests.get(
            HOMEBASE_API_URL,
            headers={"Authorization": f"Bearer {HOMEBASE_API_TOKEN}"},
            timeout=5
        )
        items = r.json()
        feedback = [i for i in items if i.get("key", "").startswith("workout_feedback_")]
        if not feedback:
            return ""
        lines = ["=== פידבק מאימונים קודמים ==="]
        for item in sorted(feedback, key=lambda x: x["key"])[-5:]:
            lines.append(f"  {item['key'].replace('workout_feedback_','')}: {item['value']}")
        return "\n".join(lines)
    except Exception:
        return ""


def build_system_prompt(data: dict) -> str:
    activities_json = json.dumps(data.get("activities", []), indent=2, ensure_ascii=False)
    history = load_history()
    workout_feedback = load_workout_feedback()
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

    return f"""אתה מאמן כושר מקצועי ואנליסט נתוני ספורט של עמיחי. יש לך גישה לנתוני הגרמין המלאים שלו.
ענה בעברית. היה ישיר, מקצועי, וספציפי — אל תהיה מחמיא.

=== ציוד זמין ===
משקולת אחת של 7.5 ק"ג בלבד + מזרן. אין מוט, אין מכשירים, אין פולי, אין ספסל.
תרגילי כוח אפשריים: שכיבות שמיכה, משיכת משקולת לגב (חד-ידית), כפיפות מרפק עם משקולת, לחיצת כתפיים עם משקולת, הרמות צד עם משקולת, סקוואט עם משקולת, לאנג', גשר ישבן, תרגילי בטן (פלאנק, כפיפות בטן, כפיפות בטן הפוכות, סופרמן, ציפור-כלב).
אסור להציע: לחיצת חזה, משיכת פולי, דדליפט עם מוט, שכיבות שמיכה עם משקל נוסף.

=== הערה לגבי שינה ===
אם sleep_hours = 0, ייתכן שהשעון פשוט לא נלבש באותו לילה — אל תסיק מסקנה שהמשתמש לא ישן. אל תכתוב "שינה 0 שעות" כממצא אם אין נתון.

=== מדדי עומס אימון (CTL/ATL/TSB/ACWR/Recovery) ===
{metrics_text}

{workout_feedback}

=== מזג אוויר (תל אביב) ===
{weather_text}


{history}


=== נתוני יום ({data['date']}) ===
צעדים: {data.get('steps', 'N/A')}
קלוריות: {data.get('calories_total', 'N/A')}
סטרס ממוצע: {data.get('stress_avg', 'N/A')}
Body Battery: {data.get('body_battery_current', 'N/A')} (גבוה={data.get('body_battery_highest','?')}, קימה={data.get('body_battery_at_wake','?')})
דופק מנוחה: {data.get('resting_hr', 'N/A')} bpm (ממוצע 7י: {data.get('resting_hr_7day_avg','N/A')})

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
            {"role": "user", "content": """כתוב דוח שבועי לעמיחי בשני חלקים. שפה פשוטה, ישירה, קריאה בוואטסאפ. אין מונחים טכניים ללא הסבר.

*חלק א׳ — השבוע שעבר*
3-4 נקודות קצרות (שורה-שתיים כל אחת):
- מצב ההתאוששות (שינה, HRV, Body Battery) — בשפה פשוטה, מה זה אומר בפועל
- עומס האימונים — האם מתאים לכושר הנוכחי? מה היה חסר?
- מה עבד טוב השבוע
- אם יש משהו דורש תשומת לב — אמור ישיר ובלי רחמים

*חלק ב׳ — תכנית השבוע הקרוב*
לכל יום בנפרד, פורמט קבוע:
📅 [יום] — [שם האימון]
[תרגילים ספציפיים עם סטים וחזרות, שורה לכל תרגיל]
⏱ [משך] | 💓 [דופק יעד אם רלוונטי]

ימים קבועים: שבת=ריצה ארוכה | ראשון=כוח חזה+כתפיים+בטן | שני=כוח גב+ביצפס+בטן | שלישי=אינטרוולים | רביעי=כוח רגליים+ישבן+בטן | חמישי=מנוחה | שישי=הליכה קלה
עצימות ומשך — לפי נתוני ההתאוששות הנוכחיים.
בכל אימון כוח: 3 תרגילי בטן לפחות (עמיחי רוצה להוריד כרס).

תרגילים אפשריים (בחר מתוך הרשימה — שמות בעברית פשוטה):
• חזה/טריצפס: שכיבות שמיכה, שכיבות שמיכה צרות (ידיים קרובות לגוף)
• כתפיים: לחיצת כתפיים עם משקולת (עמידה), הרמות צד עם משקולת, הרמות קדמיות עם משקולת
• גב/ביצפס: משיכת משקולת לגב (כפיפה קדימה, יד אחת), כפיפות מרפק עם משקולת, כפיפות פטיש עם משקולת, הרחבת גב (שוכב על הבטן, מרים ידיים ורגליים)
• רגליים/ישבן: סקוואט עם משקולת, לאנג', גשר ישבן (שוכב על הגב, מרים אגן), גשר ישבן רגל אחת
• בטן: פלאנק, כפיפות בטן, כפיפות בטן הפוכות, כפיפות אופניים, פלאנק צד, הרמת רגליים שוכב

ענה בעברית בלבד. עד 450 מילים."""},
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
    prompt = """בנה תוכנית אימונים ל-4 שבועות קדימה עבור עמיחי.

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
