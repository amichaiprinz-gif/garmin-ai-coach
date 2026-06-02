"""
Fetches Google Calendar iCal and returns today's + upcoming events as JSON.
Usage: python gcal.py [days_ahead]
"""

import sys
import json
import urllib.request
from datetime import datetime, timedelta

ICAL_URL = "https://calendar.google.com/calendar/ical/amichai.prinz%40gmail.com/private-0f2e515ac3df94e6ba3864075e569c14/basic.ics"

def fetch_ical(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read().decode("utf-8", errors="replace")

def unfold(text):
    """Unfold iCal lines folded with CRLF/LF + whitespace."""
    text = text.replace("\r\n ", "").replace("\r\n\t", "")
    text = text.replace("\n ", "").replace("\n\t", "")
    return text

def get_field(block, field):
    for line in block.split("\n"):
        name_part = line.split(":")[0]
        base_name = name_part.split(";")[0].strip()
        if base_name == field and ":" in line:
            return line.split(":", 1)[1].strip()
    return ""

def parse_dt(val):
    val = val.strip().replace("Z", "")
    for fmt in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M", "%Y%m%d"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None

def main():
    days_ahead = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    window_end = today + timedelta(days=days_ahead + 1)

    try:
        raw = fetch_ical(ICAL_URL)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    raw = unfold(raw)
    blocks = raw.split("BEGIN:VEVENT")[1:]

    events = []
    for block in blocks:
        end = block.find("END:VEVENT")
        block = block[:end]

        summary = get_field(block, "SUMMARY")
        location = get_field(block, "LOCATION")
        dtstart_raw = get_field(block, "DTSTART")

        dt = parse_dt(dtstart_raw) if dtstart_raw else None
        if not dt or not summary:
            continue
        if not (today <= dt < window_end):
            continue

        day_label = "היום" if dt.date() == today.date() else "מחר"
        time_str = "" if "T" not in dtstart_raw else dt.strftime("%H:%M")
        events.append({
            "day": day_label,
            "time": time_str,
            "summary": summary,
            "location": location,
        })

    events.sort(key=lambda e: (e["day"] != "היום", e["time"]))
    print(json.dumps(events, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
