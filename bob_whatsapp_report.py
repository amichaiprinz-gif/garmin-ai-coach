"""
WhatsApp-formatted weekly Garmin report.
Called by OpenClaw skill — output is sent directly to WhatsApp.
Converts markdown to WhatsApp-compatible formatting (*bold*, no ##).
"""

import sys, os, json, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

from bob_garmin import load_data, build_system_prompt, generate_report, load_history
from groq import Groq

from config import GROQ_API_KEY
client = Groq(api_key=GROQ_API_KEY)
MODEL = "openai/gpt-oss-120b"


def to_whatsapp(text: str) -> str:
    # ## Header → *Header*
    text = re.sub(r'^#{1,3}\s+(.+)$', r'*\1*', text, flags=re.MULTILINE)
    # **bold** → *bold*
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)
    # Remove table separators
    text = re.sub(r'^\|[-| :]+\|$', '', text, flags=re.MULTILINE)
    # Clean up multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


CACHE_PATH = os.path.join(os.path.expanduser("~"), "OneDrive", "garmin-data", "latest_report.txt")


def main():
    data = load_data()
    report = generate_report(data)
    text = to_whatsapp(report)
    # Save cache so the 20:00 send job can deliver instantly without AI call
    try:
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        pass
    print(text)


def send_cached():
    """Read cached report and print — fast, no AI call."""
    if not os.path.exists(CACHE_PATH):
        print("⚠️ דוח לא נמצא — הרץ bob_whatsapp_report.py קודם")
        return
    with open(CACHE_PATH, encoding="utf-8") as f:
        print(f.read())


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "send":
        send_cached()
    else:
        main()
