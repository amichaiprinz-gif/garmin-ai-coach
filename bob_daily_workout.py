# -*- coding: utf-8 -*-
"""
Daily workout message for Bob — sent at 12:00 every day.
Reads Garmin data, adjusts by Recovery Score, outputs WhatsApp-ready text.
"""
import sys, os, json
from datetime import date
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

from config import DATA_PATH
from metrics import get_metrics

# weekday(): 0=Mon 1=Tue 2=Wed 3=Thu 4=Fri 5=Sat 6=Sun
SCHEDULE = {
    6: "upper",      # Sunday   — חזה+כתפיים+טריצפס+בטן
    0: "back",       # Monday   — גב+ביצפס+בטן
    1: "intervals",  # Tuesday  — אינטרוולים
    2: "legs",       # Wednesday— רגליים+ישבן+בטן
    3: "rest",       # Thursday — מנוחה
    4: "walk",       # Friday   — הליכה
    5: "long_run",   # Saturday — ריצה ארוכה
}

DAY_HE = {0:"שני",1:"שלישי",2:"רביעי",3:"חמישי",4:"שישי",5:"שבת",6:"ראשון"}

# Each exercise: (name_he, sets, [reps_s1, reps_s2, reps_s3], rest_sec)
UPPER = [
    ("שכיבות שמיכה",                        3, [10, 8, 6],   60),
    ("שכיבות שמיכה צרות (ידיים קרובות)",    3, [10, 8, 6],   60),
    ("לחיצת כתפיים עם משקולת — עמידה",      3, [12, 10, 8],  60),
    ("הרמות צד עם משקולת",                  3, [15, 12, 12], 45),
    ("הרמות קדמיות עם משקולת",              3, [12, 10, 10], 45),
    ("פלאנק",                                3, ["45ש","45ש","45ש"], 45),
    ("כפיפות בטן אופניים",                  3, [20, 20, 15], 45),
    ("כפיפות בטן הפוכות",                   3, [15, 15, 12], 45),
]

BACK = [
    ("משיכת משקולת לגב — יד אחת (כפוף קדימה)", 3, [12, 10, 8],  60),
    ("הרחבת גב — שוכב על הבטן (סופרמן)",        3, [15, 15, 12], 45),
    ("ציפור-כלב — ארבע רגליים, יד ורגל מנוגדות",3, [12, 12, 10], 45),
    ("כפיפות מרפק עם משקולת",                   3, [12, 10, 8],  60),
    ("כפיפות פטיש עם משקולת",                   3, [12, 12, 10], 60),
    ("פלאנק",                                    3, ["45ש","45ש","45ש"], 45),
    ("כפיפות בטן הפוכות",                        3, [15, 15, 12], 45),
    ("כפיפות בטן אופניים",                       3, [20, 20, 15], 45),
]

LEGS = [
    ("סקוואט משקל גוף",                          3, [15, 15, 12], 60),
    ("סקוואט עם משקולת — מחזיק ביד אחת",         3, [12, 10, 8],  60),
    ("לאנג' — צעד קדימה, רגל מתחלפת",            3, [12, 12, 10], 60),
    ("גשר ישבן — שוכב, מרים אגן",                3, [15, 15, 15], 45),
    ("גשר ישבן רגל אחת",                          3, [12, 12, 10], 45),
    ("פלאנק",                                     3, ["45ש","45ש","45ש"], 45),
    ("הרמת רגליים — שוכב על הגב",                3, [15, 15, 12], 45),
    ("כפיפות בטן אופניים",                        3, [20, 20, 15], 45),
]

NUTRITION = {
    "upper": {
        "before": "🍌 שעה לפני: בננה + חופן אגוזים, או פרוסת לחם עם חמאת בוטנים",
        "after":  "🥚 תוך 30 דקות: 3 ביצים קשות / חזה עוף + אורז / גביע קוטג' עם פרי",
    },
    "back": {
        "before": "🍌 שעה לפני: בננה + חופן אגוזים, או פרוסת לחם עם חמאת בוטנים",
        "after":  "🥚 תוך 30 דקות: 3 ביצים קשות / טונה + לחם / גביע קוטג' עם פרי",
    },
    "legs": {
        "before": "🍚 שעה לפני: פחמימות קצת יותר — אורז + קצת חלבון, או לחם עם גבינה",
        "after":  "🥩 תוך 30 דקות: חלבון + פחמימות — עוף עם תפוח אדמה / קוטג' עם בננה",
    },
    "intervals": {
        "before": "🍌 45 דקות לפני: בננה / תמרים / לחם עם דבש — פחמימות מהירות בלבד",
        "after":  "🥛 תוך 20 דקות: שייק חלבון + בננה, או חלב + פרי",
    },
    "long_run": {
        "before": "🍚 שעה וחצי לפני: ארוחה עם פחמימות — אורז, לחם, שיבולת שועל",
        "after":  "🥩 תוך 30 דקות: חלבון + פחמימות — עוף עם אורז / שייק חלבון",
    },
    "walk": {
        "before": "☕ אין חובה — אפשר לאכול רגיל",
        "after":  "💧 שתייה מרובה, ארוחה רגילה",
    },
}


def load_data():
    if not os.path.exists(DATA_PATH):
        return None
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def format_exercises(exercises, sets_override=None):
    lines = []
    for name, sets, reps, rest in exercises:
        s = sets_override or sets
        if isinstance(reps[0], str):
            reps_str = " / ".join(reps[:s])
        else:
            reps_str = " / ".join(str(r) for r in reps[:s])
        lines.append(f"• {name}: {s} סטים × {reps_str} חזרות | מנוחה {rest}ש'")
    return "\n".join(lines)


def build_message(wtype, data, recovery):
    today = date.today()
    day_he = DAY_HE[today.weekday()]

    # Adjust sets based on recovery
    if recovery >= 70:
        sets_note = "💪 התאוששות טובה — תן הכל"
        sets_override = 3
    elif recovery >= 50:
        sets_note = "👍 התאוששות בינונית — 3 סטים, שמור על טכניקה"
        sets_override = 3
    else:
        sets_note = "⚠️ התאוששות נמוכה — 2 סטים, אל תדחוף יותר מדי"
        sets_override = 2

    bb = data.get("body_battery_current", "?") if data else "?"
    hrv = (data.get("hrv") or {}).get("last_night_avg", "?") if data else "?"

    header = f"🏋️ *אימון יום {day_he}*\n📊 Body Battery: {bb} | HRV: {hrv} | Recovery: {recovery}/100\n{sets_note}\n"

    if wtype == "upper":
        body = f"*חזה + כתפיים + טריצפס + בטן*\n\n" + format_exercises(UPPER, sets_override)
    elif wtype == "back":
        body = f"*גב + ביצפס + בטן*\n\n" + format_exercises(BACK, sets_override)
    elif wtype == "legs":
        body = f"*רגליים + ישבן + בטן*\n\n" + format_exercises(LEGS, sets_override)
    elif wtype == "intervals":
        if recovery < 50:
            body = "🏃 *ריצה קלה* (החלפת אינטרוולים בגלל התאוששות נמוכה)\n\n• חימום 10 דקות\n• 30 דקות ריצה קלה — דופק 120-135\n• קירור 5 דקות"
        else:
            n = 6 if recovery >= 65 else 4
            body = f"🏃 *אינטרוולים*\n\n• חימום: 10 דקות ריצה קלה (דופק 115-130)\n• {n} × 400 מטר @ ~85% — דופק 150-160 | מנוחה 90 שניות בין חזרות\n• קירור: 10 דקות ריצה קלה"
    elif wtype == "long_run":
        minutes = 55 if recovery >= 65 else 40
        body = f"🏃 *ריצה ארוכה*\n\n• חימום 5 דקות\n• {minutes - 10} דקות ריצה — דופק 120-145\n• קירור 5 דקות\n\n_שמור על קצב שנוח לדבר בו_"
    elif wtype == "walk":
        body = "🚶 *הליכה*\n\n• 35-45 דקות — דופק מתחת ל-110\n• קצב נינוח, אוויר טרי"
    else:
        return None  # Rest day — no message

    nut = NUTRITION.get(wtype, {})
    nutrition = f"\n\n🍽️ *תזונה*\n{nut.get('before','')}\n{nut.get('after','')}"

    return header + "\n" + body + nutrition


WORKOUT_CACHE = os.path.join(os.path.expanduser("~"), "OneDrive", "garmin-data", "latest_workout.txt")


def main():
    wtype = SCHEDULE.get(date.today().weekday())
    if wtype == "rest":
        text = "😴 יום מנוחה — אין אימון היום. גוף שיודע לנוח מתחזק יותר."
    else:
        data = load_data()
        try:
            m = get_metrics(data) if data else {}
            recovery = m.get("recovery_score", 60)
        except Exception:
            recovery = 60
        text = build_message(wtype, data, recovery) or ""

    # Save to cache
    try:
        os.makedirs(os.path.dirname(WORKOUT_CACHE), exist_ok=True)
        with open(WORKOUT_CACHE, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        pass
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
