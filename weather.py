"""
Weather integration — no API key needed (wttr.in).
Used to adjust training recommendations based on conditions.
"""

import urllib.request, json

CITY = "Tel Aviv"

HEAT_THRESHOLDS = {
    "easy":     28,  # above this: reduce intensity 10%
    "moderate": 33,  # above this: reduce intensity 20%, shorten run
    "extreme":  38,  # above this: move run indoors or skip
}


def get_weather() -> dict:
    try:
        url = f"https://wttr.in/{CITY.replace(' ', '+')}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())

        current = data["current_condition"][0]
        today   = data["weather"][0]
        tomorrow = data["weather"][1]

        def desc(hourly): return hourly["weatherDesc"][0]["value"]

        return {
            "now_temp_c":        int(current["temp_C"]),
            "now_feels_like_c":  int(current["FeelsLikeC"]),
            "now_humidity_pct":  int(current["humidity"]),
            "now_desc":          desc(current),
            "today_max_c":       int(today["maxtempC"]),
            "today_min_c":       int(today["mintempC"]),
            "tomorrow_max_c":    int(tomorrow["maxtempC"]),
            "tomorrow_min_c":    int(tomorrow["mintempC"]),
            "tomorrow_desc":     desc(tomorrow["hourly"][4]),
            "tomorrow_humidity": int(tomorrow["hourly"][4]["humidity"]),
            "heat_advisory":     _heat_advisory(int(tomorrow["maxtempC"])),
        }
    except Exception as e:
        return {"error": str(e)}


def _heat_advisory(temp_c: int) -> str:
    if temp_c >= HEAT_THRESHOLDS["extreme"]:
        return f"חום קיצוני ({temp_c}°C) — הזז ריצה לפנות בוקר מוקדם או פנימה"
    if temp_c >= HEAT_THRESHOLDS["moderate"]:
        return f"חום גבוה ({temp_c}°C) — קצר ריצה ב-20%, שתה כפול"
    if temp_c >= HEAT_THRESHOLDS["easy"]:
        return f"חם ({temp_c}°C) — הפחת עצימות 10%, התחל מוקדם"
    return ""


def weather_summary(w: dict) -> str:
    if "error" in w:
        return f"(מזג אוויר לא זמין: {w['error']})"
    lines = [
        f"עכשיו: {w['now_temp_c']}°C, מרגיש {w['now_feels_like_c']}°C, {w['now_desc']}",
        f"מחר: {w['tomorrow_min_c']}-{w['tomorrow_max_c']}°C, {w['tomorrow_desc']}, לחות {w['tomorrow_humidity']}%",
    ]
    if w.get("heat_advisory"):
        lines.append(f"⚠ {w['heat_advisory']}")
    return "\n".join(lines)


if __name__ == "__main__":
    w = get_weather()
    print(weather_summary(w))
