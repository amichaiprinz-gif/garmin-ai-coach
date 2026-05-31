"""
WhatsApp-formatted weekly Garmin report.
Called by OpenClaw skill — output is sent directly to WhatsApp.
Converts markdown to WhatsApp-compatible formatting (*bold*, no ##).
"""

import sys, os, json, re
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


def main():
    data = load_data()
    report = generate_report(data)
    print(to_whatsapp(report))


if __name__ == "__main__":
    main()
