"""
Garmin AI Chat — powered by Gemini.
Usage: python garmin_chat.py
"""

import os, json
from google import genai

DATA_PATH = os.path.expanduser("~/.garmin_tokens/latest_data.json")
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

client = genai.Client(api_key=GEMINI_API_KEY)


def load_data() -> dict:
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_context(data: dict) -> str:
    activities_text = "\n".join(
        f"  - {a['date']}: {a['type']} | {a['duration_min']} דקות | {a['calories']} קלוריות | דופק: {a.get('avg_hr', 'N/A')}"
        for a in data.get("activities", [])
    )
    return f"""אתה מאמן כושר אישי של אמיחי. יש לך גישה לנתוני הגרמין שלו.
ענה בעברית, בצורה קצרה ומעשית.

=== נתוני גרמין ({data['date']}) ===
היום:
  צעדים: {data.get('steps', 'N/A')}
  קלוריות: {data.get('calories', 'N/A')}
  סטרס ממוצע: {data.get('stress', 'N/A')}
  Body Battery: {data.get('body_battery', 'N/A')}
  דופק מנוחה: {data.get('resting_hr', 'N/A')} bpm

שינה אמש:
  משך: {data.get('sleep_hours', 'N/A')} שעות
  ציון: {data.get('sleep_score', 'N/A')}

אימונים אחרונים:
{activities_text}
"""


def chat():
    data = load_data()
    system_prompt = build_context(data)

    chat_session = client.chats.create(
        model="gemini-2.0-flash",
        config={"system_instruction": system_prompt},
    )

    print(f"\n🏃 Garmin AI מוכן. נתונים מ-{data['date']}. הקלד 'יציאה' לסיום.\n")

    while True:
        user_input = input("אתה: ").strip()
        if user_input.lower() in ("יציאה", "exit", "quit", "q"):
            break
        if not user_input:
            continue

        response = chat_session.send_message(user_input)
        print(f"\nג'מיני: {response.text}\n")


if __name__ == "__main__":
    chat()
