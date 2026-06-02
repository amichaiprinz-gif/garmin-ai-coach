"""
Generates the complete morning WhatsApp briefing message.
Output is the final WhatsApp message ready to send.
"""
import subprocess, json, sys, urllib.request, datetime, hashlib

sys.stdout.reconfigure(encoding="utf-8")

def fetch_json(url, headers=None, timeout=10):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return {"error": True}

day_seed = int(hashlib.md5(str(datetime.date.today()).encode()).hexdigest(), 16)
weekday = datetime.date.today().weekday()  # 0=Mon, 3=Thu, 6=Sun

GREETINGS = [
    "בוקר טוב! ☀️ קפה ראשון או שינה שנייה — הבחירה שלך.",
    "בוקר טוב! יום חדש, הזדמנות חדשה להיות גרסה טובה יותר של אתמול.",
    "בוקר טוב! העולם עוד כאן, אתה עוד כאן — זה כבר התחלה טובה.",
    "בוקר טוב! ☕ שמש, קפה, ואתה. שלושת הדברים שהיום צריך.",
    "בוקר טוב! אם הבוקר קשה, זכור: לפחות אין שני-בשני.",
    "בוקר טוב! היום מגיע רק פעם אחת — כדאי שיהיה שווה.",
    "בוקר טוב! העיניים פקוחות, הקפה מוכן — מה עוד צריך?",
    "בוקר טוב! 🌅 יום חדש, דף חדש.",
    "בוקר טוב! אפילו הכוכבים כיבו אור — הגיע הזמן לקום.",
    "בוקר טוב! כל יום הוא עוד צ'אנס לעשות משהו שאתה גאה בו.",
]

DAY_GREETINGS = {
    3: "בוקר טוב! יום חמישי — כבר ריח של שישי באוויר.",  # Thu
    4: "בוקר טוב! 🕍 שישי! עוד קצת ואפשר לנשום.",         # Fri
    6: "בוקר טוב! ☀️ ראשון — שבוע חדש, אנרגיות טריות.",   # Sun
}

greeting = DAY_GREETINGS.get(weekday, GREETINGS[day_seed % len(GREETINGS)])

JOKES = [
    "שאל הבן את האבא: 'אבא, מה זה אופטימיסט?' השיב האבא: 'לא יודע, שאל אותי מחר בבוקר.'",
    "למה הכוכב לכה אף פעם לא מאחר? כי הוא תמיד נופל בזמן.",
    "מה אומר המחשב לאצבע? 'תלחץ עלי שוב ואני אמחק הכל.'",
    "שאל המנהל: 'למה אתה תמיד מאחר?' ענה העובד: 'כי אתה תמיד צועק שמי שמגיע ראשון מתחיל לעבוד ראשון.'",
    "למה הים מלוח? כי החוף לא עוצר לבכות.",
    "שאלה: איך קוראים לדג שאין לו עיניים? תשובה: דג.",
    "למה עגבניות לא רבות עם מלפפונים? כי הן בסלט אחד.",
    "שאל הילד: 'אמא, למה המכונית זזה?' ענתה האמא: 'כי אבא לא מסיים לשתות קפה.'",
    "מה ההפרש בין מורה למסילת ברזל? המורה מאמן את המוח, המסילה — את הגוף.",
    "למה הציפור לא נכנסת לאינטרנט? כי היא כבר בטוויטר.",
]

joke = JOKES[(day_seed // 7) % len(JOKES)]

briefing = fetch_json(
    "https://fantastic-waddle-coral.vercel.app/api/bot/briefing",
    headers={"Authorization": "Bearer homebase-bot-2025"}
)

try:
    res = subprocess.run(
        ["python", r"C:\Users\amich\.openclaw\scripts\gcal.py", "1"],
        capture_output=True, text=True, timeout=15, encoding="utf-8"
    )
    raw = res.stdout.strip()
    gcal = json.loads(raw) if raw else []
except Exception:
    gcal = []

weather = fetch_json(
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=31.9516&longitude=34.8978"
    "&hourly=temperature_2m"
    "&daily=temperature_2m_max,temperature_2m_min"
    "&forecast_days=1&timezone=Asia%2FJerusalem"
)

lines = [greeting, ""]

if not weather.get("error"):
    h = weather["hourly"]["temperature_2m"]
    mx = weather["daily"]["temperature_2m_max"][0]
    t7, t12, t18 = h[7], h[12], h[18]
    if mx >= 30:   rec = "חולצה קצרה + שתייה מרובה"
    elif mx >= 25: rec = "חולצה קצרה, נעים ואפילו חם"
    elif mx >= 20: rec = "חולצה, לא צריך ז'קט"
    elif mx >= 15: rec = "קח ז'קט קליל"
    else:          rec = "התלבש חם, ז'קט ואולי סוודר"
    lines.append("🌤️ *מזג אוויר בלוד*")
    lines.append(f"07:00 — {t7}°  |  12:00 — {t12}°  |  18:00 — {t18}°")
    lines.append(f"👕 {rec}")

if not briefing.get("error"):
    overdue  = briefing.get("tasks", {}).get("overdue", [])
    upcoming = briefing.get("tasks", {}).get("upcoming", [])
    if overdue or upcoming:
        lines.append("")
        lines.append("📋 *משימות להיום*")
        for t in overdue:
            lines.append(f"- {t['title']} ⚠️")
        for t in upcoming:
            lines.append(f"- {t['title']}")

    items = briefing.get("shopping", {}).get("items", [])
    if items:
        lines.append("")
        lines.append("🛒 *קניות*")
        for item in items:
            q = f" ({item['quantity']})" if item.get("quantity") else ""
            lines.append(f"- {item['text']}{q}")

    memory = briefing.get("memory", {})
    budget_total = briefing.get("budget", {}).get("total", 0)
    budget_limit_str = memory.get("budget_limit", "")
    budget_limit = int(budget_limit_str) if budget_limit_str and budget_limit_str.isdigit() else 0
    if budget_limit > 0 and budget_total > budget_limit:
        lines.append("")
        lines.append(f"💰 *תקציב* — {budget_total} ₪ (חריג!)")

if gcal:
    lines.append("")
    lines.append("📅 *יומן*")
    for event in gcal:
        lines.append(f"- {event}")

lines.append("")
lines.append(f"😄 {joke}")

print("\n".join(lines))
