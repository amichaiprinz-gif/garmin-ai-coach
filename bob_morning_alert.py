"""
Morning alert — runs daily, sends WhatsApp message only if something is off.
Called by OpenClaw scheduled skill or Windows Task Scheduler.
"""

import sys, os, json, re
sys.stdout.reconfigure(encoding='utf-8')
from datetime import date
from supabase import create_client
from groq import Groq

from config import GROQ_API_KEY, SUPABASE_URL, SUPABASE_KEY, DATA_PATH

sb = create_client(SUPABASE_URL, SUPABASE_KEY)
client = Groq(api_key=GROQ_API_KEY)


def load_data():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def needs_alert(data: dict) -> bool:
    hrv = data.get("hrv", {}).get("last_night_avg", 99)
    sleep = data.get("sleep_hours", 99)
    bb = data.get("body_battery_current", 99)
    stress = data.get("stress_avg", 0)

    return (
        sleep < 6
        or (hrv and hrv < 45)
        or bb < 40
        or stress > 60
    )


def generate_alert(data: dict) -> str:
    hrv = data.get("hrv", {})
    issues = []

    sleep = data.get("sleep_hours", 0)
    if sleep < 6:
        issues.append(f"שינה {sleep} שעות בלבד")

    hrv_val = hrv.get("last_night_avg")
    if hrv_val and hrv_val < 45:
        issues.append(f"HRV נמוך ({hrv_val}, בסיס {hrv.get('baseline_low')}-{hrv.get('baseline_high')})")

    bb = data.get("body_battery_current", 100)
    if bb < 40:
        issues.append(f"Body Battery נמוך ({bb})")

    stress = data.get("stress_avg", 0)
    if stress > 60:
        issues.append(f"סטרס גבוה ({stress})")

    issues_text = " | ".join(issues)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "אתה בוב, מאמן כושר של עמיחי. שלח התראת בוקר קצרה (3-4 שורות) בעברית. היה ישיר ומעשי."},
            {"role": "user", "content": f"הנתונים של הבוקר מראים: {issues_text}. מה כדאי לעמיחי לדעת ולעשות היום?"},
        ],
        max_tokens=150,
    )
    return f"🌅 בוקר טוב עמיחי\n\n{response.choices[0].message.content}"


def main():
    data = load_data()
    if needs_alert(data):
        alert = generate_alert(data)
        print(alert)
    else:
        # No alert needed — silent exit
        pass


if __name__ == "__main__":
    main()
