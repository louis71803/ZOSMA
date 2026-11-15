"""Shared Layer 0/2/3 helpers and standardized card/indicator builders for the 17 Measurement Cards."""

from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np

from modules.cabin_env.measurement_rules import NOMINAL_CADENCE_HOURS, STATUS_SEVERITY


def is_in_saa(lat_deg: Optional[float], lon_deg: Optional[float]) -> bool:
    """South Atlantic Anomaly mask: latitude 50°S–0° (-50..0) AND longitude 90°W–40°E (-90..40)."""
    if lat_deg is None or lon_deg is None:
        return False
    return (-50.0 <= float(lat_deg) <= 0.0) and (-90.0 <= float(lon_deg) <= 40.0)


def _clean_time_series(
    records: list[dict[str, Any]],
    ts_key: str = "timestamp_utc",
) -> tuple[list[dict[str, Any]], list[str]]:
    """Generic L0 helper: sort timestamps ascending and remove duplicate timestamps."""
    notes: list[str] = []
    if not records:
        return [], notes
    indexed: list[tuple[str, int, dict[str, Any]]] = []
    for idx, rec in enumerate(records):
        ts = str(rec.get(ts_key, f"idx-{idx:04d}"))
        indexed.append((ts, idx, rec))

    raw_ts = [item[0] for item in indexed]
    if raw_ts != sorted(raw_ts):
        notes.append("Out-of-order timestamps sorted chronologically.")
    indexed.sort(key=lambda x: (x[0], x[1]))

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    dup_count = 0
    for ts, _, rec in indexed:
        if ts in seen:
            dup_count += 1
            continue
        seen.add(ts)
        deduped.append(rec)
    if dup_count > 0:
        notes.append(f"Removed {dup_count} duplicate timestamp record(s).")
    return deduped, notes


def _check_staleness(card_id: str, age_hours: Optional[float]) -> tuple[bool, Optional[str]]:
    """Generic L0 staleness gate: > 3x nominal cadence -> no_data (never Green)."""
    if age_hours is None:
        return False, None
    cadence = NOMINAL_CADENCE_HOURS[card_id]
    limit_h = 3.0 * cadence
    if card_id == "RAD-03" and float(age_hours) > 0.5:
        return True, f"GOES proton record age {float(age_hours)*60:.1f} min exceeds 30-min freshness limit."
    if float(age_hours) > limit_h:
        return True, f"Last valid reading age {float(age_hours):.2f} h exceeds 3x cadence ({limit_h:.2f} h) -> no_data."
    return False, None


def _ols_trend_layer3(
    times_h: list[float],
    values: list[float],
    red_limit: float,
    horizon_h: float,
    lower_is_worse: bool = False,
    log10_transform: bool = False,
) -> dict[str, Any]:
    """Layer 3: 5-point OLS trend; trigger Yellow ONLY if all 5 valid, R^2 >= 0.6, and 0 < TTR <= horizon_h."""
    if len(values) < 5 or len(times_h) < 5:
        return {"triggered": False, "r2": None, "slope_per_h": None, "ttr_h": None}
    pts_x = np.asarray(times_h[-5:], dtype=float)
    raw_y = np.asarray(values[-5:], dtype=float)
    if np.any(~np.isfinite(pts_x)) or np.any(~np.isfinite(raw_y)):
        return {"triggered": False, "r2": None, "slope_per_h": None, "ttr_h": None}

    if log10_transform:
        if np.any(raw_y <= 0) or red_limit <= 0:
            return {"triggered": False, "r2": None, "slope_per_h": None, "ttr_h": None}
        pts_y = np.log10(raw_y)
        target = math.log10(red_limit)
    else:
        pts_y = raw_y
        target = float(red_limit)

    x_mean = float(np.mean(pts_x))
    y_mean = float(np.mean(pts_y))
    ss_xx = float(np.sum((pts_x - x_mean) ** 2))
    if ss_xx <= 1e-12:
        return {"triggered": False, "r2": None, "slope_per_h": 0.0, "ttr_h": None}

    slope = float(np.sum((pts_x - x_mean) * (pts_y - y_mean)) / ss_xx)
    intercept = y_mean - slope * x_mean
    y_hat = intercept + slope * pts_x
    ss_tot = float(np.sum((pts_y - y_mean) ** 2))
    ss_res = float(np.sum((pts_y - y_hat) ** 2))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-12 else 0.0

    current = float(pts_y[-1])
    moving_toward_red = (slope < -1e-9 and current > target) if lower_is_worse else (slope > 1e-9 and current < target)
    if not moving_toward_red:
        return {"triggered": False, "r2": round(r2, 4), "slope_per_h": round(slope, 6), "ttr_h": None}

    ttr_h = (target - current) / slope
    triggered = bool(r2 >= 0.6 and 0.0 < ttr_h <= horizon_h)
    return {
        "triggered": triggered,
        "r2": round(r2, 4),
        "slope_per_h": round(slope, 6),
        "ttr_h": round(float(ttr_h), 2),
    }


def _evaluate_personal_baseline_l2(
    series_valid: list[float],
    mean_val: float,
    sd_val: float,
    lower_is_worse: bool,
) -> tuple[str, str]:
    """Layer 2 personal baseline: Yellow if worse than 1 SD; Red if worse than 2 SD on 2 consecutive valid readings."""
    if not series_valid or sd_val <= 0:
        return "green", ""
    curr = float(series_valid[-1])
    if lower_is_worse:
        worse_2sd = lambda x: x < (mean_val - 2.0 * sd_val)
        worse_1sd = lambda x: x < (mean_val - 1.0 * sd_val)
    else:
        worse_2sd = lambda x: x > (mean_val + 2.0 * sd_val)
        worse_1sd = lambda x: x > (mean_val + 1.0 * sd_val)

    if len(series_valid) >= 2 and worse_2sd(curr) and worse_2sd(float(series_valid[-2])):
        return "red", f"Worse than personal baseline by >2 SD on 2 consecutive valid readings (mean={mean_val:.2f}, SD={sd_val:.2f})."
    if worse_1sd(curr):
        return "yellow", f"Worse than personal baseline by >1 SD (mean={mean_val:.2f}, SD={sd_val:.2f})."
    return "green", ""


def _max_status(*statuses: str) -> str:
    valid = [s for s in statuses if s in {"green", "yellow", "red"}]
    if not valid:
        return "no_data"
    return max(valid, key=lambda s: STATUS_SEVERITY[s])


def _notify_for_card(card_id: str, status: str, is_env_card: bool) -> dict[str, Any]:
    """Notification routing per guide Section (2)."""
    if status == "red":
        if card_id == "ISO-03":
            return {
                "crew": True,
                "ground": True,
                "flight_surgeon": False,
                "private_conference_crew_choice": True,
                "cadence_note": "Immediate alert; crewmember chooses whether to request a private medical conference.",
            }
        return {
            "crew": True,
            "ground": True,
            "flight_surgeon": True,
            "cadence_note": "Immediate notification to crew, ground, and flight surgeon; human decision required.",
        }
    if status == "yellow":
        return {
            "crew": True,
            "ground": True,
            "flight_surgeon": False,
            "cadence_note": "Real-time ground telemetry + crew/ground review at next planning conference."
            if is_env_card
            else "Notify crewmember + ground at next planning conference.",
        }
    if status == "no_data":
        return {
            "crew": True,
            "ground": True,
            "flight_surgeon": False,
            "cadence_note": "Sensor QC/staleness alert -> repeat measurement or switch to backup sensor.",
        }
    return {
        "crew": False,
        "ground": False,
        "flight_surgeon": False,
        "cadence_note": "Dashboard only.",
    }


def _make_indicator(
    indicator: str,
    value: Any,
    unit: str,
    status: str,
    message: str,
    action: str,
    decided_by: str,
    rule_id: str,
    source_ref: str,
    data_source: str,
    baseline_val: Any = None,
    slope_per_day: Optional[float] = None,
    yellow_threshold: Optional[float] = None,
    red_threshold: Optional[float] = None,
    lower_is_worse: bool = False,
    history_days: Optional[list[int]] = None,
    history_values: Optional[list[float]] = None,
) -> dict[str, Any]:
    """Build a compliant indicator dict matching both the v2 Guide and core/schema.py."""
    st_low = status.strip().lower()
    if st_low in {"rejected", "no_data"}:
        schema_light = "NO_DATA"
    else:
        schema_light = st_low.upper()

    return {
        "indicator": indicator,
        "metric_name": indicator,
        "value": value,
        "current_val": value,
        "baseline_val": baseline_val,
        "slope_per_day": slope_per_day,
        "unit": unit,
        "status": st_low,
        "status_light": schema_light,
        "quality_passed": st_low not in {"rejected", "no_data"},
        "message": message,
        "action": action,
        "decided_by": decided_by,
        "rule_id": rule_id,
        "source_ref": source_ref,
        "data_source": data_source,
        "yellow_threshold": yellow_threshold,
        "red_threshold": red_threshold,
        "lower_is_worse": lower_is_worse,
        "history_days": history_days or [],
        "history_values": history_values or [],
    }


def _make_card_assessment(
    module_id: str,
    body_part_tag: str,
    crew_id: Optional[str],
    mission_day: int,
    timestamp_utc: str,
    location: str,
    overall_status: str,
    quality_passed: bool,
    quality_notes: list[str],
    indicators: list[dict[str, Any]],
    is_env_card: bool,
    conclusion_actions: list[str],
    routine_countermeasures: list[str],
    how_to_measure: str,
    plain_explanation: str,
    next_hours: int,
    days_until_red: Optional[int] = None,
) -> dict[str, Any]:
    st_low = overall_status.strip().lower()
    if st_low == "red" and not any("human decision" in a.lower() for a in conclusion_actions):
        conclusion_actions = list(conclusion_actions) + [
            "Final operational intervention requires human decision (Crew Commander / Flight Surgeon)."
        ]
    return {
        "module_id": module_id,
        "body_part_tag": body_part_tag,
        "crew_id": crew_id,
        "mission_day": mission_day,
        "timestamp_utc": timestamp_utc,
        "location": location,
        "overall_status": st_low,
        "quality_passed": quality_passed,
        "quality_notes": quality_notes,
        "indicators": indicators,
        "notify": _notify_for_card(module_id, st_low, is_env_card=is_env_card),
        "decision_owner": "human",
        "guidance": {
            "how_to_measure": how_to_measure,
            "plain_explanation": plain_explanation,
            "action_protocol": conclusion_actions,
        },
        "short_term_plan": {
            "next_measurement_in_hours": next_hours,
            "immediate_actions": conclusion_actions,
            "urgent_alert": st_low == "red",
        },
        "long_term_plan": {
            "days_until_red_prediction": days_until_red,
            "routine_prescription_adjustment": routine_countermeasures,
        },
    }


def _parse_water_val(raw_val: Any, detection_limit: float) -> tuple[Optional[float], str, bool]:
    """Store below-detection-limit values as '< DL', never 0."""
    if raw_val is None:
        return None, "missing", False
    if isinstance(raw_val, str):
        s = raw_val.strip()
        if s.upper().startswith("<"):
            return 0.5 * detection_limit, "< DL", True
        val = float(s)
    else:
        val = float(raw_val)
    if val < 0.0:
        return None, "negative", False
    if val == 0.0 or val < detection_limit:
        return 0.5 * detection_limit, "< DL", True
    return val, f"{val}", False
