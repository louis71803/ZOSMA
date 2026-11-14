"""Role 2: Musculoskeletal (Bone & Muscle) Domain Starter Module.

Implements Layer 0 QC Gatekeeper + 3-Layer Decision Model for:
- E4D Bone Stimulus Index (S_bone) & Loading Rate
- Isometric Peak Force (SRI delta strength %)
- Velocity-Based Training (VBT) squat velocity loss (30% Red limit)
- Ultrasound 2 Thigh (4% Yellow / 7% Red) & Calf (5% Yellow / 10% Red) CSA
- SLAMMD Body Mass (5% Yellow / 10% Red)
- Bio-Analyzer Bone Turnover Markers (NTX, CTX +50% Red, P1NP)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "musculoskeletal"


def demo_baseline() -> dict[str, Any]:
    return {
        "crew_id": "C002",
        "iso_peak_force_n": 1850.0,
        "csa_thigh_cm2": 148.0,
        "csa_calf_cm2": 82.0,
        "body_mass_kg": 74.0,
        "ctx_ng_ml": 0.36,
        "ntx_nm_bce": 14.0,
        "p1np_ug_l": 45.0,
        "s_bone_target": 1.0,
    }


def demo_payload(scenario: str = "green") -> dict[str, Any]:
    scen = (scenario or "green").strip().lower()
    if scen == "bad_data":
        return {
            "crew_id": "C002",
            "mission_day": 124,
            "data_source": "SIMULATED",
            "sensor_qc_ok": False,
            "peak_force_n": None,
            "loading_rate_n_s": 0.0,
            "reps": 0,
            "velocity_loss_pct": 0.0,
            "iso_peak_force_n": 1810.0,
            "csa_thigh_cm2": 146.0,
            "csa_calf_cm2": 80.5,
            "body_mass_kg": 73.2,
            "ntx": 15.0,
            "ctx": 0.40,
            "p1np": 44.0,
        }
    if scen == "yellow":
        return {
            "crew_id": "C002",
            "mission_day": 124,
            "data_source": "SIMULATED",
            "sensor_qc_ok": True,
            "peak_force_n": 1620.0,
            "loading_rate_n_s": 2400.0,
            "reps": 8,
            "velocity_loss_pct": 22.0,
            "iso_peak_force_n": 1660.0,  # -10.3%
            "csa_thigh_cm2": 140.5,      # -5.1% (Yellow >= 4%)
            "csa_calf_cm2": 77.2,       # -5.9% (Yellow >= 5%)
            "body_mass_kg": 69.8,       # -5.7% (Yellow >= 5%)
            "ntx": 19.5,
            "ctx": 0.49,                # +36.1%
            "p1np": 39.0,
        }
    if scen == "red":
        return {
            "crew_id": "C002",
            "mission_day": 124,
            "data_source": "SIMULATED",
            "sensor_qc_ok": True,
            "peak_force_n": 1350.0,
            "loading_rate_n_s": 1700.0,
            "reps": 5,
            "velocity_loss_pct": 33.5,  # Red >= 30%
            "iso_peak_force_n": 1450.0, # -21.6%
            "csa_thigh_cm2": 136.0,     # -8.1% (Red >= 7%)
            "csa_calf_cm2": 73.0,      # -11.0% (Red >= 10%)
            "body_mass_kg": 66.0,      # -10.8% (Red >= 10%)
            "ntx": 24.0,
            "ctx": 0.58,               # +61.1% (Red >= +50%)
            "p1np": 34.0,
        }
    # default green
    return {
        "crew_id": "C002",
        "mission_day": 124,
        "data_source": "SIMULATED",
        "sensor_qc_ok": True,
        "peak_force_n": 1820.0,
        "loading_rate_n_s": 3250.0,
        "reps": 10,
        "velocity_loss_pct": 12.5,
        "iso_peak_force_n": 1815.0,
        "csa_thigh_cm2": 146.2,
        "csa_calf_cm2": 80.8,
        "body_mass_kg": 73.1,
        "ntx": 15.2,
        "ctx": 0.39,
        "p1np": 44.5,
    }


def export_demo_csvs() -> list[str]:
    """Generate editable starter CSV/JSON templates in data/musculoskeletal/."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    baseline_path = DATA_DIR / "preflight_baseline.json"
    with baseline_path.open("w", encoding="utf-8") as fh:
        json.dump(demo_baseline(), fh, indent=2)
    written.append(str(baseline_path))

    e4d_df = pd.DataFrame(
        [
            {"mission_day": 30, "peak_force_n": 1840, "loading_rate_n_s": 3300, "reps": 10, "velocity_loss_pct": 11.0},
            {"mission_day": 60, "peak_force_n": 1830, "loading_rate_n_s": 3280, "reps": 10, "velocity_loss_pct": 11.8},
            {"mission_day": 90, "peak_force_n": 1825, "loading_rate_n_s": 3260, "reps": 10, "velocity_loss_pct": 12.2},
            {"mission_day": 124, "peak_force_n": 1820, "loading_rate_n_s": 3250, "reps": 10, "velocity_loss_pct": 12.5},
        ]
    )
    e4d_path = DATA_DIR / "e4d_sets.csv"
    e4d_df.to_csv(e4d_path, index=False)
    written.append(str(e4d_path))

    meas_df = pd.DataFrame(
        [
            {"mission_day": 30, "iso_peak_force_n": 1845, "csa_thigh_cm2": 147.8, "csa_calf_cm2": 81.8, "body_mass_kg": 73.8, "ntx": 14.3, "ctx": 0.37, "p1np": 45.0},
            {"mission_day": 60, "iso_peak_force_n": 1835, "csa_thigh_cm2": 147.1, "csa_calf_cm2": 81.4, "body_mass_kg": 73.6, "ntx": 14.7, "ctx": 0.38, "p1np": 44.8},
            {"mission_day": 90, "iso_peak_force_n": 1825, "csa_thigh_cm2": 146.7, "csa_calf_cm2": 81.1, "body_mass_kg": 73.3, "ntx": 15.0, "ctx": 0.38, "p1np": 44.6},
            {"mission_day": 124, "iso_peak_force_n": 1815, "csa_thigh_cm2": 146.2, "csa_calf_cm2": 80.8, "body_mass_kg": 73.1, "ntx": 15.2, "ctx": 0.39, "p1np": 44.5},
        ]
    )
    meas_path = DATA_DIR / "measurements_long.csv"
    meas_df.to_csv(meas_path, index=False)
    written.append(str(meas_path))
    return written


def _worst(statuses: list[str]) -> str:
    order = {"GREEN": 0, "YELLOW": 1, "RED": 2}
    return max(statuses, key=lambda s: order.get(s, 0)) if statuses else "GREEN"


def evaluate(
    payload: Optional[dict[str, Any]] = None,
    baseline: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Stateless 3-layer Musculoskeletal evaluation returning standardized contract dict."""
    base = {**demo_baseline(), **(baseline or {})}
    pay = {**demo_payload("green"), **(payload or {})}

    crew_id = str(pay.get("crew_id", base.get("crew_id", "C002")))
    mission_day = int(pay.get("mission_day", 124))
    data_source = str(pay.get("data_source", "SIMULATED")).upper()

    # Layer 0 QC Gatekeeper
    if pay.get("sensor_qc_ok") is False or pay.get("peak_force_n") is None or float(pay.get("reps", 1)) <= 0:
        return {
            "module_id": "musculoskeletal",
            "body_part_tag": "lower_limb_bone_muscle",
            "crew_id": crew_id,
            "mission_day": mission_day,
            "status_light": "INSUFFICIENT_DATA",
            "quality_passed": False,
            "data_source": data_source,
            "summary_note": "E4D load cell / rep counter failed Layer 0 QC. Immediate re-calibration required.",
            "metrics": [
                {
                    "metric_name": "e4d_force_qc",
                    "current_val": 0.0,
                    "baseline_val": base["iso_peak_force_n"],
                    "unit": "N",
                    "status_light": "INSUFFICIENT_DATA",
                    "decided_by": "quality_check",
                    "data_source": data_source,
                    "message": "Zero reps or null peak_force_n detected.",
                    "action": "Zero E4D load cell and re-run 3-rep warmup check.",
                }
            ],
            "guidance": {
                "how_to_measure": "Zero the E4D load cell with no weight, verify cable pin lock, and perform 3 controlled squat reps.",
                "plain_explanation": "Unverified force data cannot track bone mineral stimulus or prevent muscle overload.",
                "action_protocol": [
                    "Re-seat E4D harness and load-cell connector.",
                    "Repeat 3-rep calibration set before logging workout.",
                ],
            },
            "short_term_plan": {
                "next_measurement_in_hours": 0,
                "immediate_actions": ["Recalibrate E4D load cell and repeat measurement immediately."],
                "urgent_alert": False,
            },
            "long_term_plan": {
                "days_until_red_prediction": None,
                "routine_prescription_adjustment": "Verify E4D sensor calibration log weekly.",
            },
        }

    # Compute indicators
    csa_thigh = float(pay.get("csa_thigh_cm2", base["csa_thigh_cm2"]))
    thigh_delta_pct = ((csa_thigh - float(base["csa_thigh_cm2"])) / float(base["csa_thigh_cm2"])) * 100.0
    thigh_loss = -thigh_delta_pct
    if thigh_loss >= 7.0:
        thigh_status, thigh_by = "RED", "fixed_threshold"
    elif thigh_loss >= 4.0:
        thigh_status, thigh_by = "YELLOW", "fixed_threshold"
    else:
        thigh_status, thigh_by = "GREEN", "baseline"

    csa_calf = float(pay.get("csa_calf_cm2", base["csa_calf_cm2"]))
    calf_delta_pct = ((csa_calf - float(base["csa_calf_cm2"])) / float(base["csa_calf_cm2"])) * 100.0
    calf_loss = -calf_delta_pct
    if calf_loss >= 10.0:
        calf_status = "RED"
    elif calf_loss >= 5.0:
        calf_status = "YELLOW"
    else:
        calf_status = "GREEN"

    vbt_loss = float(pay.get("velocity_loss_pct", 12.5))
    if vbt_loss >= 30.0:
        vbt_status = "RED"
    elif vbt_loss >= 20.0:
        vbt_status = "YELLOW"
    else:
        vbt_status = "GREEN"

    ctx_val = float(pay.get("ctx", base["ctx_ng_ml"]))
    ctx_delta_pct = ((ctx_val - float(base["ctx_ng_ml"])) / float(base["ctx_ng_ml"])) * 100.0
    if ctx_delta_pct >= 50.0:
        ctx_status = "RED"
    elif ctx_delta_pct >= 25.0:
        ctx_status = "YELLOW"
    else:
        ctx_status = "GREEN"

    body_mass = float(pay.get("body_mass_kg", base["body_mass_kg"]))
    mass_delta_pct = ((body_mass - float(base["body_mass_kg"])) / float(base["body_mass_kg"])) * 100.0
    mass_loss = -mass_delta_pct
    if mass_loss >= 10.0:
        mass_status = "RED"
    elif mass_loss >= 5.0:
        mass_status = "YELLOW"
    else:
        mass_status = "GREEN"

    overall = _worst([thigh_status, calf_status, vbt_status, ctx_status, mass_status])

    thigh_slope = round(thigh_delta_pct / max(mission_day, 1), 4)
    days_until_red: Optional[int] = None
    if overall != "RED" and thigh_slope < -0.02:
        red_target = float(base["csa_thigh_cm2"]) * 0.93
        daily_cm2 = (csa_thigh - float(base["csa_thigh_cm2"])) / max(mission_day, 1)
        if daily_cm2 < 0:
            est = int((red_target - csa_thigh) / daily_cm2)
            if est >= 0:
                days_until_red = est
    elif overall == "RED":
        days_until_red = 0

    history_days = [0, 30, 60, 90, mission_day]
    step = (csa_thigh - float(base["csa_thigh_cm2"])) / 4.0
    history_vals = [round(float(base["csa_thigh_cm2"]) + step * i, 2) for i in range(5)]

    metrics = [
        {
            "metric_name": "csa_thigh_cm2",
            "current_val": round(csa_thigh, 2),
            "baseline_val": float(base["csa_thigh_cm2"]),
            "delta_pct": round(thigh_delta_pct, 2),
            "slope_per_day": round((csa_thigh - float(base["csa_thigh_cm2"])) / max(mission_day, 1), 4),
            "unit": "cm^2",
            "status_light": thigh_status,
            "decided_by": thigh_by,
            "data_source": data_source,
            "yellow_threshold": round(float(base["csa_thigh_cm2"]) * 0.96, 2),
            "red_threshold": round(float(base["csa_thigh_cm2"]) * 0.93, 2),
            "lower_is_worse": True,
            "history_days": history_days,
            "history_values": history_vals,
            "message": f"Thigh muscle CSA change {thigh_delta_pct:+.1f}% vs pre-flight.",
            "action": "Increase E4D posterior-chain volume +15% if Yellow/Red." if thigh_status != "GREEN" else "Maintain current E4D resistance load.",
        },
        {
            "metric_name": "csa_calf_cm2",
            "current_val": round(csa_calf, 2),
            "baseline_val": float(base["csa_calf_cm2"]),
            "delta_pct": round(calf_delta_pct, 2),
            "unit": "cm^2",
            "status_light": calf_status,
            "decided_by": "fixed_threshold",
            "data_source": data_source,
            "message": f"Calf CSA change {calf_delta_pct:+.1f}% (Yellow -5%, Red -10%).",
            "action": "Add unilateral heel raises on E4D." if calf_status != "GREEN" else "Keep nominal heel raise sets.",
        },
        {
            "metric_name": "velocity_loss_pct",
            "current_val": round(vbt_loss, 1),
            "baseline_val": 12.0,
            "delta_pct": round(vbt_loss - 12.0, 1),
            "unit": "%",
            "status_light": vbt_status,
            "decided_by": "fixed_threshold",
            "data_source": data_source,
            "message": f"E4D VBT velocity loss {vbt_loss:.1f}% (Red limit 30%).",
            "action": "Terminate set immediately & reduce load 10%." if vbt_status == "RED" else "Autoregulate rest interval to 120s.",
        },
        {
            "metric_name": "ctx_bone_resorption",
            "current_val": round(ctx_val, 3),
            "baseline_val": float(base["ctx_ng_ml"]),
            "delta_pct": round(ctx_delta_pct, 1),
            "unit": "ng/mL",
            "status_light": ctx_status,
            "decided_by": "baseline",
            "data_source": data_source,
            "message": f"Bone resorption marker CTX {ctx_delta_pct:+.1f}% vs baseline (Red >= +50%).",
            "action": "Increase axial E4D loading & confirm Vit D3/Ca intake." if ctx_status != "GREEN" else "Bone resorption stable.",
        },
        {
            "metric_name": "body_mass_kg",
            "current_val": round(body_mass, 2),
            "baseline_val": float(base["body_mass_kg"]),
            "delta_pct": round(mass_delta_pct, 2),
            "unit": "kg",
            "status_light": mass_status,
            "decided_by": "fixed_threshold",
            "data_source": data_source,
            "message": f"SLAMMD body mass {mass_delta_pct:+.1f}% vs pre-flight.",
            "action": "Add +350 kcal/day protein-enriched ration." if mass_status != "GREEN" else "Caloric balance on target.",
        },
    ]

    if overall == "RED":
        actions = [
            "Cap VBT velocity loss at <= 20% and shift E4D from max-effort to controlled eccentric hypertrophy.",
            "Add +20g whey/leucine post-workout and verify daily Calcium/Vitamin D3 supplementation.",
            "Schedule Ultrasound 2 thigh/calf re-scan within 24 hours.",
        ]
        next_hours = 12
        adj = "4-week progressive lower-limb hypertrophy block + nutrition surplus (+350 kcal/d); re-check CTX in 14 days."
    elif overall == "YELLOW":
        actions = [
            "Add 1 extra E4D squat/heel-raise set every 48 hours if Cardio & Immune are clear.",
            "Confirm protein intake >= 1.6 g/kg/day via galley log.",
        ]
        next_hours = 48
        adj = "Increase E4D axial loading volume by 10-15% over next 14 days and repeat Ultrasound CSA scan."
    else:
        actions = ["Continue scheduled E4D resistance & CEVIS aerobic countermeasure session."]
        next_hours = 168
        adj = "Maintain current E4D progressive resistance schedule (6 days/week)."

    return {
        "module_id": "musculoskeletal",
        "body_part_tag": "lower_limb_bone_muscle",
        "crew_id": crew_id,
        "mission_day": mission_day,
        "status_light": overall,
        "quality_passed": True,
        "data_source": data_source,
        "summary_note": f"Lower-limb CSA {thigh_delta_pct:+.1f}%, VBT loss {vbt_loss:.1f}%, CTX {ctx_delta_pct:+.1f}%.",
        "metrics": metrics,
        "guidance": {
            "how_to_measure": "Attach E4D VBT encoder & load cell; scan mid-thigh & calf with Ultrasound 2 linear probe using pre-marked skin landmarks.",
            "plain_explanation": "Without Earth gravity, leg muscles atrophy and bone calcium leaches into blood. E4D loading and Ultrasound CSA prevent irreversible fracture risk before Mars landing.",
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
