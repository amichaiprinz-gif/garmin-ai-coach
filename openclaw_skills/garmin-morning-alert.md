---
name: garmin-morning-alert
description: Manual fitness alert check — sends a WhatsApp alert only if something is off (low sleep, low HRV, low Body Battery, high stress). Silent if everything is fine. Daily briefing at 07:15 covers this automatically; use this for manual spot-checks.
triggers:
  - "התראת כושר"
  - "fitness alert"
  - "בדוק כושר"
---

Run the following Python script:
```
python ~/Projects/garmin/bob_morning_alert.py
```

If the script produces output — send it as a WhatsApp message to Amichai.
If the script produces no output — do nothing, stay silent.
