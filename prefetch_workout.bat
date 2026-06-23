@echo off
set PYTHONUTF8=1
cd /d C:\Users\amich\Projects\garmin
git pull origin main >> C:\Users\amich\.openclaw\logs\garmin-workout-prefetch.log 2>&1
