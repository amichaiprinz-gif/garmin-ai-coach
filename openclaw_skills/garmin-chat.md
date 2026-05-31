---
name: garmin-chat
description: Answer questions about Amichai's Garmin fitness data. Triggered when user asks about workouts, sleep, stress, heart rate, Body Battery, training recommendations, or anything health/fitness related.
triggers:
  - "גרמין"
  - "אימון"
  - "ריצה"
  - "שינה"
  - "דופק"
  - "כושר"
  - "body battery"
  - "hrv"
  - "ספורט"
---

When Amichai asks a fitness or health question, do the following:

1. Read the latest Garmin data file:
   - Path (Windows): `C:\Users\amich\OneDrive\garmin-data\latest_data.json`
   - Path (if OneDrive synced on this machine): `~/OneDrive/garmin-data/latest_data.json`

2. Answer his question based on the data. Be direct and specific — no generic advice.
   Reference actual numbers from the data (HR zones, Training Effect, Body Battery used, HRV, etc).

3. If the question is about a training plan or what to do next, also check Supabase for the last 28 days of history:
   - Run: `python ~/Projects/garmin/bob_garmin.py chat`
   - Or provide the answer directly from the JSON data.

Answer in Hebrew. Be direct, professional, and data-driven.
