---
name: garmin-evening-brief
description: Daily evening briefing at 20:00 — always sends. Summarizes today (steps, activity, stress) and prepares for tomorrow (calendar, workout plan, open tasks).
triggers:
  - "בריף ערב"
  - "evening brief"
  - "מה מחר"
  - "סיכום יום"
  - schedule: "0 20 * * *"
---

Run the following Python script:
```
python ~/Projects/garmin/bob_evening_brief.py
```

Send the full output as a WhatsApp message to Amichai.
