"""
Pulls latest code from GitHub and ensures the auto-update task is registered.
Outputs a message only when there are actual changes (to avoid WhatsApp spam on cron runs).
"""
import sys, subprocess, os
sys.stdout.reconfigure(encoding="utf-8")

REPO = r"C:\Users\amich\Projects\garmin"
TASK_NAME = "BobAutoUpdate"
BAT_PATH = r"C:\Users\amich\Projects\garmin\bob-scripts\bob-update.bat"
MANUAL = len(sys.argv) > 1 and sys.argv[1] == "--manual"

# Git pull
result = subprocess.run(
    ["git", "pull", "origin", "main"],
    cwd=REPO, capture_output=True, text=True, encoding="utf-8"
)
pull_out = (result.stdout + result.stderr).strip()
has_changes = "Already up to date" not in pull_out and result.returncode == 0

# Ensure Task Scheduler task exists (idempotent)
check = subprocess.run(
    ["schtasks", "/query", "/tn", TASK_NAME],
    capture_output=True
)
task_existed = check.returncode == 0

if not task_existed:
    ps_cmd = f"""
$action = New-ScheduledTaskAction -Execute '{BAT_PATH}'
$trigger = New-ScheduledTaskTrigger -Daily -At '08:50'
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
Register-ScheduledTask -TaskName '{TASK_NAME}' -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force
"""
    subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
                   capture_output=True)

# Output
if MANUAL:
    if has_changes:
        print(f"עדכון ירד מ-GitHub:\n{pull_out}")
    else:
        print("בוב מעודכן — אין שינויים חדשים.")
    if not task_existed:
        print("עדכון אוטומטי הוגדר — ירוץ כל יום ב-08:50.")
elif has_changes:
    print(f"עדכון אוטומטי: ירדו שינויים חדשים:\n{pull_out}")
# if cron + no changes → print nothing → no WhatsApp message
