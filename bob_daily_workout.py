# -*- coding: utf-8 -*-
"""
Daily workout message — reads from weekly_plan.json generated Sunday 19:30.
Sent daily at 12:00 via OpenClaw.
"""
import sys, os, json
from datetime import date
sys.stdout.reconfigure(encoding='utf-8')

PLAN_CACHE   = os.path.join(os.path.expanduser("~"), "OneDrive", "garmin-data", "weekly_plan.json")
WORKOUT_CACHE = os.path.join(os.path.expanduser("~"), "OneDrive", "garmin-data", "latest_workout.txt")

DAY_HE = {0:"שני",1:"שלישי",2:"רביעי",3:"חמישי",4:"שישי",5:"שבת",6:"ראשון"}

# ── Exercise definitions ───────────────────────────────────────────────────
# (name_he, rest_sec, reps_3sets, reps_2sets)
EXERCISES = {
    "strength_upper": [
        ("שכיבות שמיכה",                             60, [10,8,6],  [8,6]),
        ("שכיבות שמיכה צרות (ידיים צמודות לגוף)",    60, [10,8,6],  [8,6]),
        ("לחיצת כתפיים עם משקולת — עמידה",           60, [12,10,8], [10,8]),
        ("הרמות צד עם משקולת",                       45, [15,12,12],[12,10]),
        ("הרמות קדמיות עם משקולת",                   45, [12,10,10],[10,8]),
        ("פלאנק",                                     45, ["45ש","45ש","45ש"],["45ש","45ש"]),
        ("כפיפות בטן אופניים",                       45, [20,20,15], [20,15]),
        ("כפיפות בטן הפוכות",                        45, [15,15,12], [15,12]),
    ],
    "strength_back": [
        ("משיכת משקולת לגב — יד אחת (כפוף קדימה)",  60, [12,10,8], [10,8]),
        ("סופרמן (שוכב על הבטן, מרים ידיים ורגליים)", 45, [15,15,12],[15,12]),
        ("ציפור-כלב (ארבע רגליים, יד ורגל מנוגדות)", 45, [12,12,10],[12,10]),
        ("כפיפות מרפק עם משקולת",                    60, [12,10,8], [10,8]),
        ("כפיפות פטיש עם משקולת",                    60, [12,12,10],[12,10]),
        ("פלאנק",                                     45, ["45ש","45ש","45ש"],["45ש","45ש"]),
        ("כפיפות בטן הפוכות",                        45, [15,15,12], [15,12]),
        ("כפיפות בטן אופניים",                       45, [20,20,15], [20,15]),
    ],
    # SHIN REHAB (June 2026) — per physiotherapist, until shin heals
    "strength_legs": [
        ("סקוואט קיר — גב צמוד לקיר (30 שניות)",      60, ["30ש","30ש","30ש"],["30ש","30ש"]),
        ("עמידה על בוהן — רגל אחת (כל רגל בנפרד)",    60, [15,15,12],[15,12]),
        ("גשר ישבן (שוכב על הגב, מרים אגן)",           45, [12,12,12],[12,12]),
        ("הליכה על עקבים (60 שניות)",                  60, ["60ש","60ש","60ש"],["60ש","60ש"]),
    ],
    "strength_arms": [
        ("כפיפות מרפק עם משקולת",                    60, [12,10,8], [10,8]),
        ("כפיפות פטיש עם משקולת",                    60, [12,12,10],[12,10]),
        ("הרחקת זרוע מאחורה עם משקולת (טריצפס)",     60, [12,10,8], [10,8]),
        ("שכיבות שמיכה צרות (ידיים צמודות לגוף)",    60, [10,8,6],  [8,6]),
        ("פלאנק",                                     45, ["45ש","45ש","45ש"],["45ש","45ש"]),
        ("פלאנק צד — כל צד",                         45, ["30ש","30ש","30ש"],["30ש","30ש"]),
        ("כפיפות בטן",                                45, [20,20,15],[20,15]),
        ("כפיפות בטן הפוכות",                        45, [15,15,12],[15,12]),
        ("V-Sit (יושב, מרים רגליים וגו' יחד)",        45, [12,10,10],[10,8]),
    ],
}

NUTRITION = {
    "strength_upper": (
        "🍌 שעה לפני: בננה + חופן אגוזים / פרוסת לחם עם חמאת בוטנים",
        "🥚 תוך 30 דקות: 3 ביצים / חזה עוף + אורז / גביע קוטג' עם פרי",
    ),
    "strength_back": (
        "🍌 שעה לפני: בננה + חופן אגוזים / פרוסת לחם עם חמאת בוטנים",
        "🥚 תוך 30 דקות: 3 ביצים / טונה + לחם / גביע קוטג' עם פרי",
    ),
    "strength_legs": (
        "🍚 שעה לפני: אורז + קצת חלבון / לחם עם גבינה — יותר פחמימות",
        "🥩 תוך 30 דקות: עוף עם תפוח אדמה / קוטג' עם בננה",
    ),
    "strength_arms": (
        "🍌 שעה לפני: בננה + חופן אגוזים",
        "🥚 תוך 30 דקות: 3 ביצים / טונה + לחם",
    ),
    "intervals": (
        "🍌 45 דקות לפני: בננה / תמרים / לחם עם דבש — פחמימות מהירות בלבד",
        "🥛 תוך 20 דקות: שייק חלבון + בננה / חלב + פרי",
    ),
    "long_run": (
        "🍚 שעה וחצי לפני: ארוחה עם פחמימות — אורז / לחם / שיבולת שועל",
        "🥩 תוך 30 דקות: עוף עם אורז / שייק חלבון",
    ),
    "walk": (
        "☕ אין חובה מיוחדת — אכול רגיל",
        "💧 שתייה מרובה",
    ),
}


def format_strength(wtype: str, sets: int) -> str:
    exercises = EXERCISES.get(wtype, [])
    lines = []
    for name, rest, reps3, reps2 in exercises:
        reps = reps3 if sets == 3 else reps2
        reps_str = " / ".join(str(r) for r in reps[:sets])
        lines.append(f"• {name}\n  {sets} סטים × {reps_str} חזרות | מנוחה {rest} שניות")
    return "\n".join(lines)


def format_run(wtype: str, entry: dict) -> str:
    if wtype == "intervals":
        n = entry.get("intervals", 4)
        return (f"• חימום: 10 דקות ריצה קלה (דופק 115-130)\n"
                f"• {n} × 400 מטר — דופק ~150-165 | מנוחה 90 שניות בין חזרות\n"
                f"• קירור: 10 דקות ריצה קלה")
    else:
        mins = entry.get("run_min", 45)
        return (f"• חימום: 5 דקות הליכה מהירה\n"
                f"• {mins - 10} דקות ריצה — דופק 120-145 (קצב שנוח לדבר בו)\n"
                f"• קירור: 5 דקות הליכה")


def build_message(entry: dict, recovery: int) -> str:
    wtype = entry["type"]
    label = entry["label"]
    day   = entry["weekday"]
    sets  = entry.get("sets", 3)
    date_fmt = entry.get("date_fmt", "")

    if recovery >= 75:
        rec_line = f"Recovery {recovery}/100 — גוף מוכן 💪 ({sets} סטים)"
    elif recovery >= 50:
        rec_line = f"Recovery {recovery}/100 — בסדר 👍 ({sets} סטים)"
    else:
        rec_line = f"Recovery {recovery}/100 — התאוששות נמוכה ⚠️ ({sets} סטים — לא לדחוף)"

    header = f"🏋️ *אימון יום {day} {date_fmt}*\n{rec_line}\n\n*{label}*\n"

    if wtype in EXERCISES:
        body = format_strength(wtype, sets)
    elif wtype in ("intervals", "long_run"):
        body = format_run(wtype, entry)
    elif wtype == "walk":
        body = "• 35-45 דקות הליכה — דופק מתחת ל-110\n• קצב נינוח, לא לדחוף"
    else:
        return None  # rest day

    before, after = NUTRITION.get(wtype, ("", ""))
    nutrition = f"\n\n🍽️ *תזונה*\n{before}\n{after}"

    return header + body + nutrition


def load_today_entry() -> tuple:
    """Returns (entry_dict, recovery_score) for today from weekly plan."""
    today = date.today().isoformat()
    if not os.path.exists(PLAN_CACHE):
        return None, 60

    with open(PLAN_CACHE, encoding="utf-8") as f:
        cache = json.load(f)

    plan = cache.get("plan", {})
    entry = plan.get(today)
    recovery = cache.get("load", {}).get("recovery", 60)

    # Try to get fresh recovery from data file
    try:
        data_path = os.path.join(os.path.expanduser("~"), "OneDrive", "garmin-data", "latest_data.json")
        with open(data_path, encoding="utf-8") as f:
            data = json.load(f)
        tr = data.get("training_readiness", {})
        if tr.get("score"):
            recovery = tr["score"]
    except Exception:
        pass

    return entry, recovery


def main():
    entry, recovery = load_today_entry()

    if entry is None:
        # No weekly plan yet — show message
        text = "⚠️ אין תכנית שבועית — בוב מכין בכל ראשון ב-19:30"
    elif entry["type"] in ("rest",):
        text = "😴 יום מנוחה — הגוף בונה שריר בזמן מנוחה, לא בזמן אימון."
    else:
        text = build_message(entry, recovery) or "😴 יום מנוחה"

    os.makedirs(os.path.dirname(WORKOUT_CACHE), exist_ok=True)
    with open(WORKOUT_CACHE, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)


def send_cached():
    if not os.path.exists(WORKOUT_CACHE):
        print("⚠️ אימון לא נמצא")
        return
    with open(WORKOUT_CACHE, encoding="utf-8") as f:
        print(f.read())


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "send":
        send_cached()
    else:
        main()
