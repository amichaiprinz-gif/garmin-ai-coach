"""
Bob setup script — copies scripts and config to the right places.
Run once on a new machine after git clone.
"""
import os, shutil, subprocess, sys

BASE = os.path.dirname(__file__)
HOME = os.path.expanduser("~")
SCRIPTS_DST = os.path.join(HOME, ".openclaw", "scripts")
SKILL_SRC   = os.path.join(HOME, "Desktop", "fantastic-waddle", "openclaw-skill")


def copy(src, dst):
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(src):
        shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
        print(f"  {f} → {dst}")


print("=== Bob Setup ===\n")

# 1. Copy openclaw scripts
print("1. Copying scripts to ~/.openclaw/scripts/")
copy(os.path.join(BASE, "bob-scripts"), SCRIPTS_DST)

# 2. Copy SKILL.md to openclaw-skill folder
print("\n2. Copying SKILL.md to HomeBase openclaw-skill/")
if os.path.exists(SKILL_SRC):
    copy(os.path.join(BASE, "openclaw-config"), SKILL_SRC)
else:
    print(f"  Skipped — {SKILL_SRC} not found")

# 3. Install Python dependencies
print("\n3. Installing Python dependencies...")
subprocess.check_call([sys.executable, "-m", "pip", "install",
    "groq", "supabase", "garminconnect", "python-dotenv", "requests"])

print("\n✅ Setup complete. Create .env and run: python bob_garmin.py report")
