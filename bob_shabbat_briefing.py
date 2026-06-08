"""
Shabbat briefing — Friday ~18:00. Sends Shabbat times + HomeBase Friday prep.
"""
import sys, json, urllib.request, datetime
sys.stdout.reconfigure(encoding="utf-8")

BRIEFING_API = "https://fantastic-waddle-coral.vercel.app/api/bot/briefing"
HEBCAL_URL   = (
    "https://www.hebcal.com/shabbat"
    "?cfg=json&latitude=31.9516&longitude=34.8978"
    "&tzid=Asia%2FJerusalem&b=18&M=on"
)


def fetch_json(url, headers=None):
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception:
        return {}


def get_shabbat_times(hebcal):
    candles, havdalah = None, None
    for item in hebcal.get("items", []):
        cat = item.get("category", "")
        title = item.get("title", "")
        if cat == "candles":
            candles = item.get("date", "")
        elif cat == "havdalah":
            havdalah = item.get("date", "")
    return candles, havdalah


def format_time(iso):
    if not iso:
        return "?"
    try:
        dt = datetime.datetime.fromisoformat(iso)
        return dt.strftime("%H:%M")
    except Exception:
        return iso[:5] if len(iso) >= 5 else iso


hebcal  = fetch_json(HEBCAL_URL)
briefing = fetch_json(BRIEFING_API, headers={"Authorization": "Bearer homebase-bot-2025"})

candles_iso, havdalah_iso = get_shabbat_times(hebcal)
candles  = format_time(candles_iso)
havdalah = format_time(havdalah_iso)

lines = [f"🕯️ שבת שלום!"]
lines.append(f"כניסת שבת: {candles} | מוצ\"ש: {havdalah}")
lines.append("")

if not briefing.get("error"):
    overdue  = briefing.get("tasks", {}).get("overdue", [])
    items    = [i for i in briefing.get("shopping", {}).get("items", []) if not i.get("done")]

    if items:
        names = ", ".join(i["text"] for i in items[:5])
        lines.append(f"🛒 קניות לפני שבת: {names}")

    if overdue:
        lines.append("⚠️ משימות דחופות שלא הסתיימו:")
        for t in overdue[:4]:
            lines.append(f"  - {t['title']}")

if not any([candles_iso, briefing.get("tasks")]):
    lines.append("שבת שלום ומנוחה!")

print("\n".join(lines))
