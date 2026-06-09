---
name: bob-self-update
description: Pulls latest code from GitHub and ensures daily auto-update (08:50) is registered in Task Scheduler. Cron runs silently; manual trigger always reports status.
triggers:
  - "עדכן את עצמך"
  - "משוך עדכונים"
  - "git pull"
  - "יש עדכונים?"
  - schedule: "50 8 * * *"
---

Run the following command:
```
python C:/Users/amich/Projects/garmin/bob-scripts/bob-update.py --manual
```

If the output is non-empty, send it as a WhatsApp message to Amichai.
If there is no output, do not send anything.
