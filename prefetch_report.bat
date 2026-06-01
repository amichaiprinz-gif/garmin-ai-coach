@echo off
set PYTHONUTF8=1
cd /d C:\Users\amich\Projects\garmin
C:\Users\amich\AppData\Local\Programs\Python\Python313\python.exe bob_weekly_plan.py >> C:\Users\amich\.openclaw\logs\garmin-prefetch.log 2>&1
