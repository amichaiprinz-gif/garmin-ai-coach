---
name: garmin-weekly-report
description: Generate and send Amichai's weekly Garmin fitness report every Sunday at 20:00. Analyzes training data, HRV, sleep, Body Battery, and provides a personalized training plan for the coming week.
triggers:
  - "דוח שבועי"
  - "דוח גרמין"
  - "weekly report"
  - schedule: "0 20 * * 0"
---

Run the following Python script and return its output as a WhatsApp message:

```
python ~/Projects/garmin/bob_garmin.py report
```

If the script is not found at that path, try:
```
python C:\Users\amich\Projects\garmin\bob_garmin.py report
```

Send the full output as a formatted WhatsApp message to Amichai.
Do not summarize or shorten — send the complete report.
