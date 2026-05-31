"""
Scientific training load metrics based on TrainingPeaks model and
running-performance-analyzer recovery scoring.

CTL (Chronic Training Load / Fitness)  = 42-day EMA of daily TSS
ATL (Acute Training Load / Fatigue)    = 7-day EMA of daily TSS
TSB (Training Stress Balance / Form)   = CTL - ATL
ACWR (Acute:Chronic Workload Ratio)    = ATL / CTL  [garmin-ai-coach]

TSB zones:
  > +25 : Undertrained
  +5..+25: Peak form
  -10..+5: Optimal
  -30..-10: High load
  < -30 : Overreaching risk

ACWR zones:
  < 0.8 : Undertraining
  0.8-1.3: Sweet spot
  1.3-1.5: Caution
  > 1.5 : Injury risk

Recovery Score 0-100 [running-performance-analyzer]:
  Sleep (0-35)  + HRV (0-35) + Resting HR (0-20) + Stress (0-10)
"""

import math
from datetime import date, timedelta
from supabase import create_client

from config import SUPABASE_URL, SUPABASE_KEY
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

CTL_DAYS = 42
ATL_DAYS = 7


# ── CTL / ATL / TSB / ACWR ────────────────────────────────────────────────

def get_daily_tss(days: int = 90) -> dict[str, float]:
    since = (date.today() - timedelta(days=days)).isoformat()
    rows = (sb.table("garmin_activities")
            .select("date,training_load")
            .gte("date", since)
            .execute().data)
    daily: dict[str, float] = {}
    for r in rows:
        d = r["date"]
        daily[d] = daily.get(d, 0) + (r.get("training_load") or 0)
    return daily


def compute_ctl_atl(daily_tss: dict[str, float], today: date = None) -> dict:
    if today is None:
        today = date.today()
    ctl_k = 1 - 1 / CTL_DAYS
    atl_k = 1 - 1 / ATL_DAYS
    ctl = atl = 0.0
    current = today - timedelta(days=90)
    while current <= today:
        tss = daily_tss.get(current.isoformat(), 0)
        ctl = ctl * ctl_k + tss * (1 / CTL_DAYS)
        atl = atl * atl_k + tss * (1 / ATL_DAYS)
        current += timedelta(days=1)
    tsb = ctl - atl
    acwr = round(atl / ctl, 2) if ctl > 0 else None
    return {
        "ctl": round(ctl, 1),
        "atl": round(atl, 1),
        "tsb": round(tsb, 1),
        "acwr": acwr,
        "tsb_status": _tsb_status(tsb),
        "acwr_status": _acwr_status(acwr),
    }


def _tsb_status(tsb: float) -> str:
    if tsb > 25:   return "undertrained"
    if tsb > 5:    return "peak_form"
    if tsb > -10:  return "optimal"
    if tsb > -30:  return "high_load"
    return "overreaching_risk"


def _acwr_status(acwr) -> str:
    if acwr is None: return "insufficient_data"
    if acwr < 0.8:   return "undertraining"
    if acwr <= 1.3:  return "sweet_spot"
    if acwr <= 1.5:  return "caution"
    return "injury_risk"


# ── Recovery Score (0-100) ─────────────────────────────────────────────────
# Based on running-performance-analyzer composite formula

def compute_recovery_score(sleep_h, hrv, hrv_baseline_low, hrv_baseline_high,
                            resting_hr, stress_avg) -> dict:
    """
    Returns score 0-100 and component breakdown.
    Lower resting HR and stress = better. Higher HRV and sleep = better.
    """
    # Sleep component (0-35): 35 = 8h+, 0 = 4h or less
    sleep_score = max(0, min(35, (sleep_h - 4) / 4 * 35)) if sleep_h else 0

    # HRV component (0-35): compare to personal baseline
    if hrv and hrv_baseline_low and hrv_baseline_high:
        baseline_mid = (hrv_baseline_low + hrv_baseline_high) / 2
        baseline_range = (hrv_baseline_high - hrv_baseline_low) / 2 or 1
        hrv_score = max(0, min(35, 17.5 + (hrv - baseline_mid) / baseline_range * 17.5))
    else:
        hrv_score = 17.5  # neutral if no data

    # Resting HR component (0-20): 45 bpm = 20, 80 bpm = 0
    if resting_hr:
        hr_score = max(0, min(20, (80 - resting_hr) / 35 * 20))
    else:
        hr_score = 10

    # Stress component (0-10): 0 stress = 10, 100 stress = 0
    stress_score = max(0, min(10, (100 - (stress_avg or 50)) / 100 * 10))

    total = sleep_score + hrv_score + hr_score + stress_score

    return {
        "recovery_score": round(total),
        "recovery_label": _recovery_label(total),
        "components": {
            "sleep": round(sleep_score, 1),
            "hrv": round(hrv_score, 1),
            "resting_hr": round(hr_score, 1),
            "stress": round(stress_score, 1),
        }
    }


def _recovery_label(score: float) -> str:
    if score >= 80: return "excellent"
    if score >= 65: return "good"
    if score >= 50: return "moderate"
    if score >= 35: return "poor"
    return "very_poor"


RECOVERY_HEBREW = {
    "excellent": "מצוין — גוף מוכן לעומס גבוה",
    "good":      "טוב — אפשר לאמן בנורמה",
    "moderate":  "בינוני — הפחת עצימות ב-10%",
    "poor":      "חלש — אימון קל בלבד",
    "very_poor": "גרוע — מנוחה מלאה",
}

TSB_HEBREW = {
    "undertrained":      "תת-אימון",
    "peak_form":         "כושר שיא",
    "optimal":           "אזור אופטימלי",
    "high_load":         "עומס גבוה",
    "overreaching_risk": "סיכון עומס יתר",
}

ACWR_HEBREW = {
    "undertraining":       "תת-אימון",
    "sweet_spot":          "אזור מיטבי",
    "caution":             "זהירות — עומס עולה",
    "injury_risk":         "סיכון פציעה גבוה",
    "insufficient_data":   "נתונים לא מספיקים",
}


# ── Main ───────────────────────────────────────────────────────────────────

def get_metrics(data: dict = None) -> dict:
    """
    data: optional latest_data dict. If None, skips recovery score.
    Returns all metrics combined.
    """
    daily_tss = get_daily_tss(90)
    load = compute_ctl_atl(daily_tss)

    result = {
        **load,
        "tsb_hebrew":  TSB_HEBREW.get(load["tsb_status"], load["tsb_status"]),
        "acwr_hebrew": ACWR_HEBREW.get(load["acwr_status"], load["acwr_status"]),
    }

    if data:
        hrv = data.get("hrv", {})
        rec = compute_recovery_score(
            sleep_h=data.get("sleep_hours"),
            hrv=hrv.get("last_night_avg"),
            hrv_baseline_low=hrv.get("baseline_low"),
            hrv_baseline_high=hrv.get("baseline_high"),
            resting_hr=data.get("resting_hr"),
            stress_avg=data.get("stress_avg"),
        )
        result.update(rec)
        result["recovery_hebrew"] = RECOVERY_HEBREW.get(rec["recovery_label"], "")

    return result


if __name__ == "__main__":
    import json, os
    data_path = os.path.join(os.path.expanduser("~"), ".garmin_tokens", "latest_data.json")
    try:
        with open(data_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = None

    m = get_metrics(data)
    print(f"CTL (כושר 42י):   {m['ctl']}")
    print(f"ATL (עייפות 7י):   {m['atl']}")
    print(f"TSB (מצב):         {m['tsb']} — {m['tsb_hebrew']}")
    print(f"ACWR (יחס עומס):   {m.get('acwr', 'N/A')} — {m['acwr_hebrew']}")
    if "recovery_score" in m:
        print(f"Recovery Score:    {m['recovery_score']}/100 — {m['recovery_hebrew']}")
        print(f"  שינה: {m['components']['sleep']}/35 | HRV: {m['components']['hrv']}/35 | דופק: {m['components']['resting_hr']}/20 | סטרס: {m['components']['stress']}/10")
