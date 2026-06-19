"""
Pulls latest code from GitHub and ensures the auto-update task is registered.
Outputs a message only when there are actual changes (to avoid WhatsApp spam on cron runs).
"""
import sys, subprocess, os
sys.stdout.reconfigure(encoding="utf-8")

REPO = r"C:\Users\amich\Projects\garmin"
HOMEBASE_REPO = r"C:\Users\amich\Projects\fantastic-waddle"
TASK_NAME = "BobAutoUpdate"
BAT_PATH = r"C:\Users\amich\Projects\garmin\bob-scripts\bob-update.bat"
MANUAL = len(sys.argv) > 1 and sys.argv[1] == "--manual"

def pull(repo, branch="main"):
    r = subprocess.run(
        ["git", "pull", "origin", branch],
        cwd=repo, capture_output=True, text=True, encoding="utf-8"
    )
    return (r.stdout + r.stderr).strip(), r.returncode == 0

# Git pull — garmin-ai-coach
pull_out, ok = pull(REPO)
has_changes = "Already up to date" not in pull_out and ok

# Git pull — fantastic-waddle (SKILL.md, SKILL-cron.md)
if os.path.isdir(HOMEBASE_REPO):
    hb_out, hb_ok = pull(HOMEBASE_REPO, "master")
    if hb_ok and "Already up to date" not in hb_out:
        has_changes = True
        pull_out += f"\n[HomeBase] {hb_out}"

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
