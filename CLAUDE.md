# Garmin AI Coach — הוראות לקלוד

## מה המערכת הזאת עושה
מושכת נתוני כושר מגרמין של אמיחי ומייצרת דוח שבועי + עונה על שאלות בזמן אמת.

---

## קבצים חשובים

| קובץ | תפקיד |
|------|--------|
| `bob_garmin.py` | הלב — מייצר דוחות ועונה שאלות |
| `bob_whatsapp_report.py` | דוח מפורמט לווטסאפ (בלי markdown) |
| `bob_morning_alert.py` | התראת בוקר אם יש חריגה |
| `metrics.py` | מחשב CTL/ATL/TSB |
| `garmin_data.py` | מושך נתונים מגרמין (רץ על מחשב העבודה) |

---

## משימה 1 — דוח שבועי (כל ראשון 20:00)

**הרץ בדיוק את הפקודה הזאת:**
```
python bob_whatsapp_report.py
```

**מה לעשות עם הפלט:** שלח את כל הטקסט שיוצא כהודעת ווטסאפ לאמיחי. אל תקצר, אל תשנה, שלח הכל.

---

## משימה 2 — שאלה על נתוני כושר

כשאמיחי שואל שאלה על הכושר שלו (ריצה, שינה, דופק, אימון, Body Battery, HRV, המלצה לאימון וכדומה):

**שלב 1 — קרא את הנתונים:**
```python
import json, os
with open(os.path.join(os.path.expanduser("~"), "OneDrive", "garmin-data", "latest_data.json"), encoding="utf-8") as f:
    data = json.load(f)
print(json.dumps(data, ensure_ascii=False, indent=2))
```

**שלב 2 — קרא את מדדי העומס:**
```
python metrics.py
```

**שלב 3 — ענה על השאלה** לפי הנתונים שקראת. היה ספציפי ומספרי. ענה בעברית.

---

## משימה 3 — התראת בוקר (כל יום 07:30)

**הרץ:**
```
python bob_morning_alert.py
```

**אם יצא טקסט** — שלח אותו כהודעת ווטסאפ לאמיחי.
**אם לא יצא כלום** — אל תשלח כלום, הכל תקין.

---

## מבנה הנתונים (מה יש ב-latest_data.json)

```
date, steps, calories_total, resting_hr, stress_avg,
body_battery_current/highest/lowest/charged/drained/at_wake,
spo2_avg, sleep_hours, sleep_score, sleep_deep_min, sleep_rem_min,
hrv: {weekly_avg, last_night_avg, status, baseline_low, baseline_high},
vo2max: {vo2max, vo2max_date},
activities: [
  {date, type, duration_min, distance_km, calories, avg_hr, max_hr,
   training_effect_aerobic (0-5), training_effect_anaerobic (0-5),
   training_effect_label, training_load, body_battery_used,
   hr_zones: {zone1..zone5: {min_hr, seconds}}}
]
```

**פירוש Training Effect:**
- 0-1: כמעט ללא השפעה
- 2: שמירת כושר בסיסי
- 3: שיפור
- 4: פיתוח משמעותי
- 5: עומס יתר

**פירוש TSB (מ-metrics.py):**
- מעל +25: תת-אימון
- +5 עד +25: כושר שיא
- -10 עד +5: אזור אימון אופטימלי
- -30 עד -10: עומס גבוה
- מתחת -30: סיכון עומס יתר

---

## תכנית אימונים קבועה של אמיחי

| יום | אימון |
|-----|-------|
| שבת | ריצה ארוכה |
| ראשון | כוח — חזה + כתפיים + טריצפס + בטן |
| שני | כוח — גב + ביצפס + בטן |
| שלישי | ריצה עם אינטרוולים |
| רביעי | כוח — רגליים + ישבן + בטן |
| חמישי | מנוחה |
| שישי | מנוחה / הליכה קלה |

**חשוב:** בכל אימון כוח — לפחות 3 תרגילי בטן (אמיחי רוצה להוריד כרס).

---

## אם יש שגיאה

**"No such file or directory" על latest_data.json:**
הנתונים לא עודכנו היום. בדוק שה-OneDrive מסונכרן. הקובץ צריך להיות ב:
`~/OneDrive/garmin-data/latest_data.json`

**שגיאת Groq API:**
```
python -c "from config import GROQ_API_KEY; from groq import Groq; c = Groq(api_key=GROQ_API_KEY); print('ok')"
```
אם לא עובד — API key פג. ספר לאמיחי.

**שגיאת Supabase:**
בדוק חיבור אינטרנט. אם יש חיבור ועדיין לא עובד — ספר לאמיחי.
