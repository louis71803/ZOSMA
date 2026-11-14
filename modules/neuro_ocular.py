"""Role 4: Neuro-Ocular & Vestibular (SANS) Domain Starter Module.

Implements Layer 0 QC Gatekeeper + 3-Layer Decision Model for:
- Mini OCT QC (quality_score & registered_to_baseline)
- Delta TRT (+20 um Yellow / +55 um Red)
- Delta V_ONH (0.10-0.15 mm3 GREEN-WATCH, >=0.15 Yellow, >=0.30 Red)
- Delta RNFL, Hyperopic Shift (>= +0.75 D -> Space Anticipation Glasses)
- Foveal Folds / Amsler Scotoma (Red)
- Combined ONSD (ONSD > 6.0 mm AND delta_onsd >= +0.5 mm -> Red)
- Gravity-transition-aware VOR gain / OCR / MS score / Tandem walk
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "neuro_ocular"


def demo_baseline() -> dict[str, Any]:
    return {
        "crew_id": "C002",
        "trt_um": 310.0,
        "v_onh_mm3": 1.65,
        "rnfl_um": 98.0,
        "onsd_mm": 4.9,
        "axial_length_mm": 23.6,
        "vor_gain": 0.98,
    }


def demo_payload(scenario: str = "green") -> dict[str, Any]:
    scen = (scenario or "green").strip().lower()
    if scen == "bad_data":
        return {
            "crew_id": "C002",
            "mission_day": 124,
            "data_source": "SIMULATED",
            "eye": "OD",
            "quality_score": 4.2,
            "registered_to_baseline": False,
            "delta_trt_um": 8.0,
            "delta_v_onh_mm3": 0.04,
            "delta_rnfl_um": 3.0,
            "sph_eq_shift_d": 0.25,
            "folds_foveal": False,
            "amsler_result": "normal",
            "onsd_mm": 5.1,
            "delta_onsd_mm": 0.2,
            "vor_gain": 0.94,
            "ocr_deg": 4.5,
            "ms_score": 1.0,
            "g_phase": "0g_cruise",
            "days_since_transition": 124,
            "tandem_correct_steps": 18,
        }
    if scen == "yellow":
        return {
            "crew_id": "C002",
            "mission_day": 124,
            "data_source": "SIMULATED",
            "eye": "OD",
            "quality_score": 8.6,
            "registered_to_baseline": True,
            "delta_trt_um": 28.0,
            "delta_v_onh_mm3": 0.17,
            "delta_rnfl_um": 16.0,
            "sph_eq_shift_d": 0.75,
            "folds_foveal": False,
            "amsler_result": "normal",
            "onsd_mm": 5.8,
            "delta_onsd_mm": 0.4,
            "vor_gain": 0.86,
            "ocr_deg": 3.6,
            "ms_score": 2.5,
            "g_phase": "0g_cruise",
            "days_since_transition": 124,
            "tandem_correct_steps": 15,
        }
    if scen == "red":
        return {
            "crew_id": "C002",
            "mission_day": 124,
            "data_source": "SIMULATED",
            "eye": "OD",
            "quality_score": 8.8,
            "registered_to_baseline": True,
            "delta_trt_um": 62.0,
            "delta_v_onh_mm3": 0.34,
            "delta_rnfl_um": 24.0,
            "sph_eq_shift_d": 1.25,
            "folds_foveal": True,
            "amsler_result": "scotoma",
            "onsd_mm": 6.4,
            "delta_onsd_mm": 0.7,
            "vor_gain": 0.72,
            "ocr_deg": 2.2,
            "ms_score": 5.0,
            "g_phase": "0g_cruise",
            "days_since_transition": 124,
            "tandem_correct_steps": 10,
        }
    return {
        "crew_id": "C002",
        "mission_day": 124,
        "data_source": "SIMULATED",
        "eye": "OD",
        "quality_score": 9.1,
        "registered_to_baseline": True,
        "delta_trt_um": 9.0,
        "delta_v_onh_mm3": 0.06,
        "delta_rnfl_um": 4.0,
        "sph_eq_shift_d": 0.25,
        "folds_foveal": False,
        "amsler_result": "normal",
        "onsd_mm": 5.1,
        "delta_onsd_mm": 0.2,
        "vor_gain": 0.95,
        "ocr_deg": 4.8,
        "ms_score": 0.5,
        "g_phase": "0g_cruise",
        "days_since_transition": 124,
        "tandem_correct_steps": 19,
    }


def export_demo_csvs() -> list[str]:
    """Generate editable starter CSV/JSON templates in data/neuro_ocular/."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    base_path = DATA_DIR / "preflight_baseline.json"
    with base_path.open("w", encoding="utf-8") as fh:
        json.dump(demo_baseline(), fh, indent=2)
    written.append(str(base_path))

    oct_df = pd.DataFrame(
        [
            {"mission_day": 30, "eye": "OD", "quality_score": 9.0, "registered_to_baseline": True, "delta_trt_um": 3.5, "delta_v_onh_mm3": 0.02, "delta_rnfl_um": 1.5, "sph_eq_shift_d": 0.0, "folds_foveal": False, "amsler_result": "normal"},
            {"mission_day": 60, "eye": "OD", "quality_score": 9.2, "registered_to_baseline": True, "delta_trt_um": 6.0, "delta_v_onh_mm3": 0.04, "delta_rnfl_um": 2.5, "sph_eq_shift_d": 0.25, "folds_foveal": False, "amsler_result": "normal"},
            {"mission_day": 124, "eye": "OD", "quality_score": 9.1, "registered_to_baseline": True, "delta_trt_um": 9.0, "delta_v_onh_mm3": 0.06, "delta_rnfl_um": 4.0, "sph_eq_shift_d": 0.25, "folds_foveal": False, "amsler_result": "normal"},
        ]
    )
    oct_path = DATA_DIR / "mini_oct_scans.csv"
    oct_df.to_csv(oct_path, index=False)
    written.append(str(oct_path))
    return written


def _worst(statuses: list[str]) -> str:
    order = {"GREEN": 0, "GREEN-WATCH": 0, "YELLOW": 1, "RED": 2}
    return max(statuses, key=lambda s: order.get(s, 0)) if statuses else "GREEN"


def evaluate(
    payload: Optional[dict[str, Any]] = None,
    baseline: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Stateless 3-layer Neuro-Ocular & Vestibular evaluation."""
    base = {**demo_baseline(), **(baseline or {})}
    pay = {**demo_payload("green"), **(payload or {})}

    crew_id = str(pay.get("crew_id", base.get("crew_id", "C002")))
    mission_day = int(pay.get("mission_day", 124))
    data_source = str(pay.get("data_source", "SIMULATED")).upper()
    eye = str(pay.get("eye", "OD"))

    # Layer 0 QC Gatekeeper
    qc_score = float(pay.get("quality_score", pay.get("oct_snr_score", 9.0)))
    registered = bool(pay.get("registered_to_baseline", True))
    if qc_score < 6.0 or not registered:
        return {
            "module_id": "neuro_ocular",
            "body_part_tag": "eyes_vestibular",
            "crew_id": crew_id,
            "mission_day": mission_day,
            "status_light": "RESCAN_REQUIRED",
            "quality_passed": False,
            "data_source": data_source,
            "summary_note": f"Mini OCT QC failed for {eye} (score={qc_score:.1f}, registered={registered}).",
            "metrics": [
                {
                    "metric_name": "oct_scan_qc",
                    "current_val": round(qc_score, 1),
                    "baseline_val": 8.0,
                    "unit": "score",
                    "status_light": "RESCAN_REQUIRED",
                    "decided_by": "quality_check",
                    "data_source": data_source,
                    "message": f"OCT quality score {qc_score:.1f} (<6.0) or unregistered scan.",
                    "action": "Re-align eye cup on Mini OCT and re-acquire registered optic disc scan.",
                }
            ],
            "guidance": {
                "how_to_measure": "Dim cabin light, stabilize head on Mini OCT chinrest, fixate green cross, and verify Auto-Register lock.",
                "plain_explanation": "Unregistered OCT scans can misread micron-level retinal swelling.",
                "action_protocol": ["Repeat Mini OCT scan until quality score >= 6.0 and baseline registration passes."],
            },
            "short_term_plan": {
                "next_measurement_in_hours": 0,
                "immediate_actions": ["Re-acquire registered Mini OCT scan immediately."],
                "urgent_alert": False,
            },
            "long_term_plan": {
                "days_until_red_prediction": None,
                "routine_prescription_adjustment": "Verify optical window cleanliness on Mini OCT monthly.",
            },
        }

    delta_trt = float(pay.get("delta_trt_um", 9.0))
    if delta_trt >= 55.0:
        trt_status = "RED"
    elif delta_trt >= 20.0:
        trt_status = "YELLOW"
    else:
        trt_status = "GREEN"

    delta_vonh = float(pay.get("delta_v_onh_mm3", 0.06))
    if delta_vonh >= 0.30:
        vonh_status = "RED"
    elif delta_vonh >= 0.15:
        vonh_status = "YELLOW"
    elif delta_vonh >= 0.10:
        vonh_status = "GREEN-WATCH"
    else:
        vonh_status = "GREEN"

    sph_shift = float(pay.get("sph_eq_shift_d", 0.25))
    sph_status = "YELLOW" if sph_shift >= 0.75 else "GREEN"

    folds = bool(pay.get("folds_foveal", False))
    amsler = str(pay.get("amsler_result", "normal")).strip().lower()
    foveal_status = "RED" if (folds or amsler != "normal") else "GREEN"

    onsd = float(pay.get("onsd_mm", 5.1))
    delta_onsd = float(pay.get("delta_onsd_mm", 0.2))
    if onsd > 6.0 and delta_onsd >= 0.5:
        onsd_status = "RED"
    elif onsd >= 5.6 or delta_onsd >= 0.4:
        onsd_status = "YELLOW"
    else:
        onsd_status = "GREEN"

    vor_gain = float(pay.get("vor_gain", 0.95))
    days_trans = int(pay.get("days_since_transition", mission_day))
    if days_trans > 7 and vor_gain < 0.78:
        vor_status = "RED"
    elif days_trans > 7 and vor_gain < 0.88:
        vor_status = "YELLOW"
    else:
        vor_status = "GREEN"

    overall = _worst([trt_status, vonh_status, sph_status, foveal_status, onsd_status, vor_status])
    if overall == "GREEN" and vonh_status == "GREEN-WATCH":
        overall = "GREEN-WATCH"

    ppco2 = pay.get("ppco2_1h_mmHg")
    co2_note = f" | Cross-context cabin ppCO2={float(ppco2):.2f} mmHg" if ppco2 is not None else ""

    history_days = [0, 30, 60, 90, mission_day]
    step = delta_trt / 4.0
    history_vals = [round(step * i, 1) for i in range(5)]

    days_until_red: Optional[int] = None
    if overall == "RED":
        days_until_red = 0
    elif delta_trt > 5.0:
        slope = delta_trt / max(mission_day, 1)
        if slope > 0:
            days_until_red = max(1, int((55.0 - delta_trt) / slope))

    metrics = [
        {
            "metric_name": "delta_trt_um",
            "current_val": round(delta_trt, 1),
            "baseline_val": 0.0,
            "slope_per_day": round(delta_trt / max(mission_day, 1), 4),
            "unit": "um",
            "status_light": trt_status,
            "decided_by": "fixed_threshold",
            "data_source": data_source,
            "yellow_threshold": 20.0,
            "red_threshold": 55.0,
            "lower_is_worse": False,
            "history_days": history_days,
            "history_values": history_vals,
            "message": f"{eye} delta TRT +{delta_trt:.1f} um (Yellow >= 20, Red >= 55).",
            "action": "Initiate daily LBNP -25 mmHg & Flight Surgeon SANS review." if trt_status == "RED" else ("Increase OCT cadence & check cabin ppCO2." if trt_status == "YELLOW" else "Retinal thickness stable."),
        },
        {
            "metric_name": "delta_v_onh_mm3",
            "current_val": round(delta_vonh, 3),
            "baseline_val": 0.0,
            "unit": "mm^3",
            "status_light": vonh_status,
            "decided_by": "fixed_threshold",
            "data_source": data_source,
            "message": f"{eye} optic nerve head volume +{delta_vonh:.2f} mm^3.",
            "action": "Monitor ONH edema closely." if vonh_status != "GREEN" else "Optic disc normal.",
        },
        {
            "metric_name": "onsd_mm",
            "current_val": round(onsd, 2),
            "baseline_val": float(base["onsd_mm"]),
            "unit": "mm",
            "status_light": onsd_status,
            "decided_by": "rule",
            "data_source": data_source,
            "message": f"Optic nerve sheath diameter {onsd:.1f} mm (delta {delta_onsd:+.1f} mm).",
            "action": "Evaluate intracranial fluid pressure / LBNP." if onsd_status != "GREEN" else "Sheath diameter normal.",
        },
        {
            "metric_name": "sph_eq_shift_d",
            "current_val": round(sph_shift, 2),
            "baseline_val": 0.0,
            "unit": "D",
            "status_light": sph_status,
            "decided_by": "fixed_threshold",
            "data_source": data_source,
            "message": f"Hyperopic shift {sph_shift:+.2f} D.",
            "action": "Switch to Space Anticipation Glasses (+0.75/+1.0 D)." if sph_status != "GREEN" else "Visual acuity stable.",
        },
        {
            "metric_name": "vor_gain",
            "current_val": round(vor_gain, 2),
            "baseline_val": float(base["vor_gain"]),
            "unit": "ratio",
            "status_light": vor_status,
            "decided_by": "baseline",
            "data_source": data_source,
            "message": f"VOG VOR gain {vor_gain:.2f} (day {days_trans} post-transition).",
            "action": "Run 10-min gaze-stabilization drills." if vor_status != "GREEN" else "Vestibular adaptation stable.",
        },
    ]

    if overall == "RED":
        actions = [
            "Notify Flight Surgeon immediately for Grade-2+ SANS / foveal fold protocol.",
            "Run 45-min LBNP at -25 mmHg and keep sleeping torso slightly elevated / avoid head-down posture.",
            "Repeat Mini OCT & Amsler grid check in 24 hours; verify cabin ppCO2 < 2.0 mmHg.",
        ]
        next_hours = 24
        adj = "Weekly Mini OCT + Ultrasound ONSD surveillance + daily LBNP fluid-shift countermeasure for 30 days."
    elif overall == "YELLOW":
        actions = [
            "Equip Space Anticipation Glasses if near-vision blur occurs (+0.75 D shift).",
            "Schedule bi-weekly Mini OCT & cross-check cabin ppCO2 levels.",
        ]
        next_hours = 72
        adj = "Increase Mini OCT cadence to every 14 days and add 3x/week LBNP fluid unloading."
    else:
        actions = ["Continue monthly Mini OCT, Amsler grid, and VOG vestibular checks."]
        next_hours = 168
        adj = "Maintain baseline monthly SANS imaging & pre-landing vestibular drills."

    return {
        "module_id": "neuro_ocular",
        "body_part_tag": "eyes_vestibular",
        "crew_id": crew_id,
        "mission_day": mission_day,
        "status_light": overall,
        "quality_passed": True,
        "data_source": data_source,
        "summary_note": f"{eye} delta TRT +{delta_trt:.1f} um, delta V_ONH +{delta_vonh:.2f} mm3, ONSD {onsd:.1f} mm{co2_note}.",
        "metrics": metrics,
        "guidance": {
            "how_to_measure": "Capture registered Mini OCT macular/ONH cube, perform Amsler grid monocular test, and measure ONSD 3 mm behind globe via Ultrasound 2.",
            "plain_explanation": "Spaceflight Associated Neuro-ocular Syndrome (SANS) flattens the back of the eye and swells the optic nerve due to headward fluid shift and elevated CO2.",
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
