# Garmin AI — הגדרת בוב

## מה שצריך להעתיק למחשב בבית

העתק את כל התיקייה `C:\Users\amich\Projects\garmin\` למחשב של בוב.
(או רק את הקבצים הבאים למיקום שבוב עובד ממנו)

### קבצי Python הנחוצים:
- `bob_garmin.py` — דוח שבועי + צ'אט
- `bob_whatsapp_report.py` — דוח מפורמט לוואטסאפ
- `bob_morning_alert.py` — התראת בוקר

### Skills לOpenClaw:
- `openclaw_skills/garmin-weekly-report.md`
- `openclaw_skills/garmin-chat.md`
- `openclaw_skills/garmin-morning-alert.md`

---

## התקנת תלויות

```bash
pip install groq supabase
```

---

## הגדרת Skills בOpenClaw

העתק את קבצי ה-`.md` מתוך `openclaw_skills/` לתיקיית ה-skills של OpenClaw.
בדרך כלל:
```
~/.openclaw/skills/
# או
~/openclaw/skills/
```

---

## בדיקה שהכל עובד

### בדיקת דוח שבועי:
```bash
python bob_whatsapp_report.py
```
צריך להדפיס דוח מפורמט בעברית.

### בדיקת התראת בוקר:
```bash
python bob_morning_alert.py
```
אם הנתונים תקינים — שקט. אם יש חריגה — מדפיס הודעה.

### בדיקת צ'אט:
```bash
python bob_garmin.py chat
```

---

## מה קורה אוטומטית

| מה | מתי | מי מפעיל |
|----|-----|-----------|
| משיכת נתונים מגרמין | כל בוקר 07:00 | Task Scheduler (מחשב העבודה) |
| שמירה ל-OneDrive + Supabase | אוטומטי | עם המשיכה |
| דוח שבועי | ראשון 20:00 | OpenClaw (בוב) |
| התראת בוקר (אם צריך) | כל יום 07:30 | OpenClaw (בוב) |

---

## נתיב הנתונים

הנתונים מגיעים מ-OneDrive:
```
~/OneDrive/garmin-data/latest_data.json
```
וודא ש-OneDrive מסונכרן על המחשב הזה.

---

## אם יש בעיה

- אם `latest_data.json` לא קיים — מחשב העבודה לא רץ ב-07:00. בדוק Task Scheduler שם.
- אם יש שגיאת Groq API — הסשן פג, הפעל: `python bob_garmin.py` עם MFA חדש על מחשב העבודה.
- אם Supabase לא מתחבר — בדוק חיבור אינטרנט.
