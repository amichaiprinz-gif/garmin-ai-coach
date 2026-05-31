@echo off
cd /d "C:\Users\amich\Projects\garmin"
python garmin_data.py >> "%USERPROFILE%\garmin_sync.log" 2>&1
