---
name: garmin-morning-alert
description: Daily morning check of Garmin data. Sends a WhatsApp alert only if something is off — low sleep, low HRV, low Body Battery, or high stress. Silent if everything is fine.
triggers:
  - schedule: "30 7 * * *"
---

Run the following Python script:
```
python ~/Projects/garmin/bob_morning_alert.py
```

If the script produces output — send it as a WhatsApp message to Amichai.
If the script produces no output — do nothing, stay silent.
