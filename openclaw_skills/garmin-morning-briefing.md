---
name: garmin-morning-briefing
description: Daily morning briefing at 09:30 — always sends. Combines Garmin fitness data (sleep, HRV, Body Battery), Google Calendar, tasks, weather. Replaces the conditional morning alert for the daily briefing.
triggers:
  - "בריף בוקר"
  - "morning briefing"
  - "מה הבוקר"
  - schedule: "30 9 * * *"
---

Run the following Python script:
```
python ~/Projects/garmin/bob_morning_briefing.py
```

Send the full output as a WhatsApp message to Amichai.
