import urllib.request, json, sys

sys.stdout.reconfigure(encoding="utf-8")

TOKEN = "homebase-bot-2025"
URL = "https://fantastic-waddle-coral.vercel.app/api/bot/briefing"

try:
    req = urllib.request.Request(URL, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
except Exception as e:
    print(f"שגיאה בטעינת נתונים: {e}", file=sys.stderr)
    sys.exit(1)

overdue = data.get("tasks", {}).get("overdue", [])
items = [i for i in data.get("shopping", {}).get("items", []) if not i.get("done")]

if not overdue and not items:
    print("🕯️ שבת שלום!")
    sys.exit(0)

lines = ["📅 מחר שישי!"]

if items:
    lines.append(f"🛒 {len(items)} פריטים ברשימת הקניות")

if overdue:
    lines.append("⚠️ משימות דחופות:")
    for t in overdue:
        lines.append(f"- {t['title']}")

print("\n".join(lines))
