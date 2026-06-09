@echo off
cd /d "C:\Users\amich\Projects\garmin"
python bob-scripts\bob-update.py >> "%USERPROFILE%\bob_update.log" 2>&1
