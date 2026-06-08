---
name: bob-shabbat
description: Friday Shabbat briefing — sends Shabbat entry/exit times plus Friday HomeBase prep (shopping, overdue tasks). Runs automatically every Friday at 18:00.
triggers:
  - "שבת שלום"
  - "זמני שבת"
  - "כניסת שבת"
  - "בריף שישי"
  - schedule: "0 18 * * 5"
---

Run `python C:/Users/amich/Projects/garmin/bob_shabbat_briefing.py` and send its output as-is. Do not add any additional text.
