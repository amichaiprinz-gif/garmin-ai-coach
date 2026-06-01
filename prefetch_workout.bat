@echo off
set PYTHONUTF8=1
cd /d C:\Users\amich\Projects\garmin
C:\Users\amich\AppData\Local\Programs\Python\Python313\python.exe bob_daily_workout.py >> C:\Users\amich\.openclaw\logs\garmin-workout-prefetch.log 2>&1
