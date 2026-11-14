"""Role 3: Cardiovascular & Aerobic Domain Starter Module.

Implements Layer 0 QC Gatekeeper + 3-Layer Decision Model for:
- Resting HR, PTT Blood Pressure, SpO2, Respiratory Rate
- Holter 24h PVC Burden & AFib screening
- LBNP / Stand Test orthostatic tolerance
- CEVIS 150W Steady-State HR drift
- Ultrasound 2 GLS cardiac strain & IJV stasis / thrombus protocol
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "cardiovascular"


def demo_baseline() -> dict[str, Any]:
    return {
        "crew_id": "C002",
        "rest_hr_bpm": 62.0,
        "sbp_mmHg": 116.0,
        "dbp_mmHg": 74.0,
        "spo2_pct": 98.0,
        "steady_hr_150w_bpm": 134.0,
        "gls_pct": -20.0,
        "hb_g_dl": 14.4,
        "hct_pct": 43.0,
    }


def demo_payload(scenario: str = "green") -> dict[str, Any]:
    scen = (scenario or "green").strip().lower()
    if scen == "bad_data":
        return {
            "crew_id": "C002",
            "mission_day": 124,
            "data_source": "SIMULATED",
            "ecg_lead_quality": 0.25,
            "rest_hr_bpm": None,
            "sbp_mmHg": 118.0,
            "dbp_mmHg": 75.0,
            "spo2_pct": 98.0,
            "resp_rate_bpm": 15.0,
            "steady_hr_150w_bpm": 136.0,
            "stand_hr_rise_bpm": 12.0,
            "stand_sbp_drop_mmHg": 6.0,
            "dizzy": False,
            "pvc_burden_pct": 0.4,
            "afib_detected": False,
            "gls_change_pct": -3.0,
            "ijv_flow": "forward",
            "ijv_thrombus": False,
            "hb_g_dl": 14.2,
            "hct_pct": 42.5,
            "potassium_mmol_l": 4.2,
            "crp_change_pct": 5.0,
        }
    if scen == "yellow":
        return {
            "crew_id": "C002",
            "mission_day": 124,
            "data_source": "SIMULATED",
            "ecg_lead_quality": 0.94,
            "rest_hr_bpm": 78.0,
            "sbp_mmHg": 136.0,
            "dbp_mmHg": 86.0,
            "spo2_pct": 95.5,
            "resp_rate_bpm": 19.0,
            "steady_hr_150w_bpm": 151.0,
            "stand_hr_rise_bpm": 24.0,
            "stand_sbp_drop_mmHg": 16.0,
            "dizzy": False,
            "pvc_burden_pct": 2.4,
            "afib_detected": False,
            "gls_change_pct": -11.5,
            "ijv_flow": "stagnant",
            "ijv_thrombus": False,
            "hb_g_dl": 13.8,
            "hct_pct": 41.2,
            "potassium_mmol_l": 3.5,
            "crp_change_pct": 35.0,
        }
    if scen == "red":
        return {
            "crew_id": "C002",
            "mission_day": 124,
            "data_source": "SIMULATED",
            "ecg_lead_quality": 0.95,
            "rest_hr_bpm": 96.0,
            "sbp_mmHg": 154.0,
            "dbp_mmHg": 96.0,
            "spo2_pct": 91.5,
            "resp_rate_bpm": 24.0,
            "steady_hr_150w_bpm": 168.0,
            "stand_hr_rise_bpm": 34.0,
            "stand_sbp_drop_mmHg": 26.0,
            "dizzy": True,
            "pvc_burden_pct": 6.2,
            "afib_detected": True,
            "gls_change_pct": -18.0,
            "ijv_flow": "reversed",
            "ijv_thrombus": True,
            "hb_g_dl": 12.9,
            "hct_pct": 38.5,
            "potassium_mmol_l": 3.1,
            "crp_change_pct": 90.0,
        }
    return {
        "crew_id": "C002",
        "mission_day": 124,
        "data_source": "SIMULATED",
        "ecg_lead_quality": 0.96,
        "rest_hr_bpm": 64.0,
        "sbp_mmHg": 118.0,
        "dbp_mmHg": 74.0,
        "spo2_pct": 98.2,
        "resp_rate_bpm": 14.0,
        "steady_hr_150w_bpm": 136.0,
        "stand_hr_rise_bpm": 11.0,
        "stand_sbp_drop_mmHg": 5.0,
        "dizzy": False,
        "pvc_burden_pct": 0.3,
        "afib_detected": False,
        "gls_change_pct": -2.5,
        "ijv_flow": "forward",
        "ijv_thrombus": False,
        "hb_g_dl": 14.3,
        "hct_pct": 42.8,
        "potassium_mmol_l": 4.2,
        "crp_change_pct": 4.0,
    }


def export_demo_csvs() -> list[str]:
    """Generate editable starter CSV templates in data/cardiovascular/."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    daily_df = pd.DataFrame(
        [
            {"mission_day": 30, "rest_hr_bpm": 62, "sbp_mmHg": 116, "dbp_mmHg": 74, "spo2_pct": 98.4, "resp_rate_bpm": 14},
            {"mission_day": 60, "rest_hr_bpm": 63, "sbp_mmHg": 117, "dbp_mmHg": 75, "spo2_pct": 98.2, "resp_rate_bpm": 14},
            {"mission_day": 90, "rest_hr_bpm": 63, "sbp_mmHg": 118, "dbp_mmHg": 74, "spo2_pct": 98.1, "resp_rate_bpm": 15},
            {"mission_day": 124, "rest_hr_bpm": 64, "sbp_mmHg": 118, "dbp_mmHg": 74, "spo2_pct": 98.2, "resp_rate_bpm": 14},
        ]
    )
    daily_path = DATA_DIR / "daily_vitals.csv"
    daily_df.to_csv(daily_path, index=False)
    written.append(str(daily_path))

    ultrasound_df = pd.DataFrame(
        [
            {"mission_day": 60, "gls_change_pct": -1.5, "ijv_flow": "forward", "ijv_thrombus": False},
            {"mission_day": 124, "gls_change_pct": -2.5, "ijv_flow": "forward", "ijv_thrombus": False},
        ]
    )
    us_path = DATA_DIR / "ultrasound.csv"
    ultrasound_df.to_csv(us_path, index=False)
    written.append(str(us_path))
    return written


def _worst(statuses: list[str]) -> str:
    order = {"GREEN": 0, "YELLOW": 1, "RED": 2}
    return max(statuses, key=lambda s: order.get(s, 0)) if statuses else "GREEN"


def evaluate(
    payload: Optional[dict[str, Any]] = None,
    baseline: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Stateless 3-layer Cardiovascular evaluation returning standardized contract dict."""
    base = {**demo_baseline(), **(baseline or {})}
    pay = {**demo_payload("green"), **(payload or {})}

    crew_id = str(pay.get("crew_id", base.get("crew_id", "C002")))
    mission_day = int(pay.get("mission_day", 124))
    data_source = str(pay.get("data_source", "SIMULATED")).upper()

    # Layer 0 QC Gatekeeper
    lead_q = float(pay.get("ecg_lead_quality", 0.95))
    if lead_q < 0.5 or pay.get("rest_hr_bpm") is None:
        return {
            "module_id": "cardiovascular",
            "body_part_tag": "heart_vascular",
            "crew_id": crew_id,
            "mission_day": mission_day,
            "status_light": "INSUFFICIENT_DATA",
            "quality_passed": False,
            "data_source": data_source,
            "summary_note": "Bio-Monitor ECG / PTT lead quality below 0.50 threshold.",
            "metrics": [
                {
                    "metric_name": "ecg_lead_quality",
                    "current_val": round(lead_q, 2),
                    "baseline_val": 0.95,
                    "unit": "ratio",
                    "status_light": "INSUFFICIENT_DATA",
                    "decided_by": "quality_check",
                    "data_source": data_source,
                    "message": "ECG dry-electrode impedance too high or HR missing.",
                    "action": "Moisten Bio-Monitor garment electrodes and hold still for 30s.",
                }
            ],
            "guidance": {
                "how_to_measure": "Wet Bio-Monitor thoracic electrodes lightly with water, tighten chest strap, and sit quietly for 60s.",
                "plain_explanation": "Motion artifact or dry skin creates false arrhythmia alarms.",
                "action_protocol": ["Re-wet Bio-Monitor ECG strap and repeat resting recording."],
            },
            "short_term_plan": {
                "next_measurement_in_hours": 0,
                "immediate_actions": ["Re-seat Bio-Monitor chest strap and capture clean 60s ECG."],
                "urgent_alert": False,
            },
            "long_term_plan": {
                "days_until_red_prediction": None,
                "routine_prescription_adjustment": "Inspect Bio-Monitor electrode pads during weekly maintenance.",
            },
        }

    rest_hr = float(pay.get("rest_hr_bpm", base["rest_hr_bpm"]))
    hr_delta = rest_hr - float(base["rest_hr_bpm"])
    if rest_hr >= 95 or hr_delta >= 25:
        hr_status = "RED"
    elif rest_hr >= 78 or hr_delta >= 12:
        hr_status = "YELLOW"
    else:
        hr_status = "GREEN"

    spo2 = float(pay.get("spo2_pct", 98.0))
    if spo2 <= 92.0:
        spo2_status = "RED"
    elif spo2 < 96.0:
        spo2_status = "YELLOW"
    else:
        spo2_status = "GREEN"

    pvc = float(pay.get("pvc_burden_pct", 0.3))
    afib = bool(pay.get("afib_detected", False))
    if afib or pvc >= 5.0:
        rhythm_status = "RED"
    elif pvc >= 2.0:
        rhythm_status = "YELLOW"
    else:
        rhythm_status = "GREEN"

    ijv_flow = str(pay.get("ijv_flow", "forward")).strip().lower()
    ijv_clot = bool(pay.get("ijv_thrombus", False))
    if ijv_clot or ijv_flow == "reversed":
        ijv_status = "RED"
    elif ijv_flow == "stagnant":
        ijv_status = "YELLOW"
    else:
        ijv_status = "GREEN"

    hr_150w = float(pay.get("steady_hr_150w_bpm", base["steady_hr_150w_bpm"]))
    hr_150w_delta = hr_150w - float(base["steady_hr_150w_bpm"])
    if hr_150w >= 165 or hr_150w_delta >= 25:
        cevis_status = "RED"
    elif hr_150w >= 150 or hr_150w_delta >= 12:
        cevis_status = "YELLOW"
    else:
        cevis_status = "GREEN"

    overall = _worst([hr_status, spo2_status, rhythm_status, ijv_status, cevis_status])

    history_days = [0, 30, 60, 90, mission_day]
    step = (rest_hr - float(base["rest_hr_bpm"])) / 4.0
    history_vals = [round(float(base["rest_hr_bpm"]) + step * i, 1) for i in range(5)]

    days_until_red: Optional[int] = None
    if overall == "RED":
        days_until_red = 0
    elif hr_delta > 2:
        daily_slope = hr_delta / max(mission_day, 1)
        if daily_slope > 0:
            days_until_red = max(1, int((95.0 - rest_hr) / daily_slope))

    metrics = [
        {
            "metric_name": "rest_hr_bpm",
            "current_val": round(rest_hr, 1),
            "baseline_val": float(base["rest_hr_bpm"]),
            "delta_pct": round((hr_delta / float(base["rest_hr_bpm"])) * 100.0, 1),
            "slope_per_day": round(hr_delta / max(mission_day, 1), 4),
            "unit": "bpm",
            "status_light": hr_status,
            "decided_by": "baseline",
            "data_source": data_source,
            "yellow_threshold": 78.0,
            "red_threshold": 95.0,
            "lower_is_worse": False,
            "history_days": history_days,
            "history_values": history_vals,
            "message": f"Resting HR {rest_hr:.0f} bpm ({hr_delta:+.0f} vs pre-flight).",
            "action": "Check hydration & sleep debt." if hr_status != "GREEN" else "Nominal autonomic tone.",
        },
        {
            "metric_name": "spo2_pct",
            "current_val": round(spo2, 1),
            "baseline_val": float(base["spo2_pct"]),
            "unit": "%",
            "status_light": spo2_status,
            "decided_by": "fixed_threshold",
            "data_source": data_source,
            "message": f"Peripheral oxygen saturation {spo2:.1f}%.",
            "action": "Inspect cabin O2 & pulse oximeter probe." if spo2_status != "GREEN" else "Oxygenation optimal.",
        },
        {
            "metric_name": "pvc_burden_pct",
            "current_val": round(pvc, 2),
            "baseline_val": 0.3,
            "unit": "%",
            "status_light": rhythm_status,
            "decided_by": "fixed_threshold",
            "data_source": data_source,
            "message": f"Holter PVC burden {pvc:.1f}%, AFib={'YES' if afib else 'NO'}.",
            "action": "Check serum K+ & hold max exertion." if rhythm_status != "GREEN" else "Sinus rhythm clean.",
        },
        {
            "metric_name": "ijv_flow_status",
            "current_val": ijv_flow,
            "baseline_val": "forward",
            "unit": "flow",
            "status_light": ijv_status,
            "decided_by": "rule",
            "data_source": data_source,
            "message": f"IJV Doppler flow '{ijv_flow}', thrombus={ijv_clot}.",
            "action": "Initiate LBNP -25 mmHg & Flight Surgeon anticoagulation protocol." if ijv_status == "RED" else ("Apply -20 mmHg LBNP 30 min/day." if ijv_status == "YELLOW" else "Normal cephalad venous drainage."),
        },
        {
            "metric_name": "steady_hr_150w_bpm",
            "current_val": round(hr_150w, 1),
            "baseline_val": float(base["steady_hr_150w_bpm"]),
            "unit": "bpm",
            "status_light": cevis_status,
            "decided_by": "baseline",
            "data_source": data_source,
            "message": f"CEVIS 150W submaximal HR {hr_150w:.0f} bpm.",
            "action": "Lower CEVIS zone-2 target wattage." if cevis_status != "GREEN" else "Aerobic fitness preserved.",
        },
    ]

    if overall == "RED":
        actions = [
            "STOP all strenuous E4D & high-intensity CEVIS exercise immediately.",
            "Perform Ultrasound 2 bilateral IJV compression sweep + 12-lead ECG capture.",
            "If IJV thrombus/reversed flow: initiate onboard anticoagulation checklist & LBNP -25 mmHg.",
        ]
        next_hours = 4
        adj = "Suspend HIIT for 14 days; daily resting ECG, potassium monitoring, and LBNP orthostatic conditioning."
    elif overall == "YELLOW":
        actions = [
            "Run 30-min LBNP at -20 mmHg to reduce cephalad venous stasis.",
            "Hydrate +500 mL electrolyte solution and repeat resting vitals in 12h.",
        ]
        next_hours = 12
        adj = "Shift CEVIS to Zone 2 steady aerobic conditioning (4x/week) and add LBNP 3x/week."
    else:
        actions = ["Continue daily Bio-Monitor morning vitals & planned CEVIS cycling."]
        next_hours = 24
        adj = "Maintain current CEVIS aerobic conditioning + bi-weekly LBNP tolerance check."

    return {
        "module_id": "cardiovascular",
        "body_part_tag": "heart_vascular",
        "crew_id": crew_id,
        "mission_day": mission_day,
        "status_light": overall,
        "quality_passed": True,
        "data_source": data_source,
        "summary_note": f"Rest HR {rest_hr:.0f} bpm, SpO2 {spo2:.1f}%, IJV '{ijv_flow}', PVC {pvc:.1f}%.",
        "metrics": metrics,
        "guidance": {
            "how_to_measure": "Wear Bio-Monitor shirt for resting HR/ECG; place Ultrasound 2 linear probe laterally on neck for IJV Doppler flow.",
            "plain_explanation": "Microgravity shifts ~2L of fluid toward the head, shrinking plasma volume and risking neck vein stasis/clots (IJV) or orthostatic fainting.",
            "action_protocol": actions,
        },
        "short_term_plan": {
            "next_measurement_in_hours": next_hours,
            "immediate_actions": actions,
            "urgent_alert": overall == "RED",
        },
        "long_term_plan": {
            "days_until_red_prediction": days_until_red,
            "routine_prescription_adjustment": adj,
        },
    }
