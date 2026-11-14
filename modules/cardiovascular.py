"""Role 3: Cardiovascular & Aerobic Capacity Domain Module (Team Z.O.S.M.A.).

Branch: feat/cardiovascular
Primary entry point: modules/cardiovascular.py (used by app.py & core/data_loader.py).

Implements:
1. Layer 0 QC Gatekeeper (ecg_lead_quality, motion_artifact_g, impossible/missing values)
2. 3-Layer Decision Model (Worst Result Wins):
   - Layer 1: Fixed Clinical / NASA-STD-3001 Rules
   - Layer 2: Personal Pre-flight Baseline (+/-2 SD or delta %)
   - Layer 3: 14-day Linear Trend Projection (5-point / recent trend fit flagging YELLOW if RED predicted within 14 days)
3. All 11 Cardiovascular & Aerobic Measurements (M1-M11):
   - M1: Resting HR (Bio-Monitor)
   - M2: Blood Pressure (Bio-Monitor PTT + weekly arm cuff calibration & PhysioNet PRCP check)
   - M3: SpO2 (Bio-Monitor optical)
   - M4: Breathing Rate (Bio-Monitor chest sensor)
   - M5: Heart Rhythm & PVC Burden (Holter Monitor 2 & PhysioNet MIT-BIH records 100/106/119/208/223 check)
   - M6: Stand Test / Orthostatic Tolerance (in-flight LBNP / post-landing stand test & PhysioNet PRCP check)
   - M7: Aerobic Fitness 150W Bike HR Drift (CEVIS + ECG)
   - M8: Heart Muscle Strength GLS (Ultrasound 2 echocardiography)
   - M9: Internal Jugular Vein Flow & Clot Protocol (Ultrasound 2 vascular Doppler + compression)
   - M10: Plasma Volume %DeltaPV via Dill & Costill 1974 (NASA OSDR OSD-569 Hb/Hct)
   - M11: Serum Blood Markers: K+, CRP, Albumin, Total Protein, Na+, Fibrinogen, PF4 (NASA OSDR OSD-575)
4. Cross-Indicator Clinical Correlations:
   - M3 low SpO2 + M4 tachypnea (>25/min) -> M9 suspected IJV thromboembolism / PE & cabin O2/CO2 check
   - M5 elevated PVC burden -> M11 hypokalemia (<3.5 mmol/L) check
   - M6 orthostatic intolerance -> M10 plasma volume loss fluid-loading protocol
5. Dual Input Modes:
   - Batch/historical loading from data/cardiovascular/*.csv & data/shared_real/*.csv (never FileNotFoundError)
   - Real-time manual parameter overrides from Streamlit UI sliders/forms
6. `demo_baseline()`, `demo_payload(scenario)` (Crew C002, days 1-124), `export_demo_csvs()`, `evaluate()`, `to_schema()`,
   plus Matplotlib & Plotly visualization helpers.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Optional, Sequence

import numpy as np
import pandas as pd

from core.schema import (
    CrewGuidance,
    LongTermPlan,
    MetricItem,
    ModuleEvaluationResult,
    ScheduleMutation,
    ShortTermPlan,
    normalize_module_result,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "cardiovascular"
SHARED_REAL_DIR = BASE_DIR / "data" / "shared_real"
REAL_SUBDIR = DATA_DIR / "real"

STATUS_RANK: dict[str, int] = {
    "GREEN": 0,
    "GREEN-WATCH": 0,
    "YELLOW": 1,
    "RED": 2,
}

EXPECTED_CSV_SCHEMAS: dict[str, list[str]] = {
    "daily_vitals.csv": [
        "crew_id",
        "mission_day",
        "rest_hr_bpm",
        "sbp_mmHg",
        "dbp_mmHg",
        "spo2_pct",
        "resp_rate_bpm",
        "ecg_lead_quality",
        "motion_artifact_g",
        "ptt_calibrated_days_ago",
    ],
    "bike_test.csv": [
        "crew_id",
        "mission_day",
        "steady_hr_150w_bpm",
        "cevis_power_w",
        "hr_drift_bpm",
    ],
    "stand_test.csv": [
        "crew_id",
        "mission_day",
        "protocol_mode",
        "stand_hr_rise_bpm",
        "stand_sbp_drop_mmHg",
        "dizzy",
        "prcp_reference_ok",
    ],
    "holter_24h.csv": [
        "crew_id",
        "mission_day",
        "pvc_burden_pct",
        "afib_detected",
        "mitbih_record_check",
        "mitbih_pvc_rate_pct",
    ],
    "ultrasound.csv": [
        "crew_id",
        "mission_day",
        "gls_pct",
        "gls_change_pct",
        "ijv_flow",
        "ijv_compressible",
        "ijv_thrombus",
    ],
    "biomonitor_stream_day124.csv": [
        "crew_id",
        "mission_day",
        "timestamp_min",
        "hr_bpm",
        "sbp_mmHg",
        "dbp_mmHg",
        "spo2_pct",
        "resp_rate_bpm",
        "ecg_lead_quality",
        "motion_artifact_g",
    ],
}

# Reference MIT-BIH arrhythmia validation records (PhysioNet records 100, 106, 119, 208, 223)
MITBIH_REFERENCE_RECORDS: dict[str, dict[str, Any]] = {
    "100": {"rhythm": "Normal Sinus Rhythm", "expected_pvc_pct": 0.04, "afib": False},
    "106": {"rhythm": "Frequent Ventricular Bigeminy / PVCs", "expected_pvc_pct": 22.8, "afib": False},
    "119": {"rhythm": "Ventricular Bigeminy & Trigeminy", "expected_pvc_pct": 19.6, "afib": False},
    "208": {"rhythm": "Frequent Uniform/Multiform PVCs", "expected_pvc_pct": 33.7, "afib": False},
    "223": {"rhythm": "Ventricular Tachycardia / Bigeminy Runs", "expected_pvc_pct": 16.2, "afib": False},
}


# ---------------------------------------------------------------------------
# Helpers: Math, Trend Projection, Dill & Costill, Status Rollup
# ---------------------------------------------------------------------------

def _worst_status(statuses: Sequence[str]) -> str:
    if not statuses:
        return "GREEN"
    return max(statuses, key=lambda s: STATUS_RANK.get(str(s).upper(), 0))


def _safe_float(val: Any, default: Optional[float] = None) -> Optional[float]:
    if val is None:
        return default
    if isinstance(val, bool):
        return float(val)
    try:
        num = float(val)
        if math.isnan(num) or math.isinf(num):
            return default
        return num
    except (TypeError, ValueError):
        return default


def _safe_bool(val: Any, default: bool = False) -> bool:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    tok = str(val).strip().lower()
    if tok in {"true", "1", "yes", "y"}:
        return True
    if tok in {"false", "0", "no", "n", ""}:
        return False
    return default


def dill_costill_delta_pv_pct(
    hb_pre: float,
    hct_pre_pct: float,
    hb_post: float,
    hct_post_pct: float,
) -> float:
    """Calculate % change in Plasma Volume (%DeltaPV) via Dill & Costill (1974).

    Formula:
        %DeltaPV = 100 * [ (Hb_pre / Hb_post) * ((1 - Hct_post) / (1 - Hct_pre)) - 1 ]
    where Hct is fractional hematocrit (0-1).
    """
    if hb_post <= 0 or hb_pre <= 0:
        return 0.0
    hct_pre = max(0.10, min(0.75, hct_pre_pct / 100.0))
    hct_post = max(0.10, min(0.75, hct_post_pct / 100.0))
    bv_ratio = hb_pre / hb_post
    pv_ratio = bv_ratio * ((1.0 - hct_post) / (1.0 - hct_pre))
    return round((pv_ratio - 1.0) * 100.0, 2)


def _linear_trend_projection(
    days: Sequence[int],
    values: Sequence[float],
    red_threshold: Optional[float],
    lower_is_worse: bool = False,
    horizon_days: int = 14,
) -> tuple[Optional[float], Optional[int], bool]:
    """Fit a linear slope on recent points (last 5 points) and check 14-day RED crossing.

    Returns:
        (slope_per_day, days_until_red, yellow_trend_triggered)
    """
    if len(days) < 2 or len(values) < 2 or len(days) != len(values):
        return None, None, False

    x = np.asarray(days[-5:], dtype=float)
    y = np.asarray(values[-5:], dtype=float)
    if np.ptp(x) <= 0:
        return 0.0, None, False

    slope, _intercept = np.polyfit(x, y, 1)
    slope = float(slope)
    current_val = float(y[-1])

    if red_threshold is None:
        return round(slope, 4), None, False

    if lower_is_worse:
        if current_val <= red_threshold:
            return round(slope, 4), 0, False
        if slope < -1e-6:
            days_to_red = int(math.ceil((red_threshold - current_val) / slope))
            days_to_red = max(0, days_to_red)
            return round(slope, 4), days_to_red, days_to_red <= horizon_days
    else:
        if current_val >= red_threshold:
            return round(slope, 4), 0, False
        if slope > 1e-6:
            days_to_red = int(math.ceil((red_threshold - current_val) / slope))
            days_to_red = max(0, days_to_red)
            return round(slope, 4), days_to_red, days_to_red <= horizon_days

    return round(slope, 4), None, False


def _layer2_baseline_status(
    current: float,
    baseline: Optional[float],
    sd: Optional[float] = None,
    warn_sd: float = 2.0,
    red_sd: float = 3.0,
    warn_pct: Optional[float] = None,
    red_pct: Optional[float] = None,
    direction: str = "both",  # "high" | "low" | "both"
) -> tuple[str, Optional[float]]:
    """Evaluate Layer 2 personal baseline deviation (+/-2 SD or % delta)."""
    if baseline is None or baseline == 0:
        return "GREEN", None

    delta = current - baseline
    delta_pct = (delta / abs(baseline)) * 100.0

    # Directional check
    if direction == "high":
        eff_delta = max(0.0, delta)
        eff_pct = max(0.0, delta_pct)
    elif direction == "low":
        eff_delta = max(0.0, -delta)
        eff_pct = max(0.0, -delta_pct)
    else:
        eff_delta = abs(delta)
        eff_pct = abs(delta_pct)

    status = "GREEN"
    if sd is not None and sd > 0:
        if eff_delta >= red_sd * sd:
            status = "RED"
        elif eff_delta >= warn_sd * sd:
            status = "YELLOW"

    if red_pct is not None and eff_pct >= red_pct:
        status = "RED"
    elif warn_pct is not None and eff_pct >= warn_pct and status == "GREEN":
        status = "YELLOW"

    return status, round(delta_pct, 2)


# ---------------------------------------------------------------------------
# Baseline & Simulated Longitudinal Data Generators (Days 1-124, Crew C002)
# ---------------------------------------------------------------------------

def demo_baseline() -> dict[str, Any]:
    """Pre-flight personal cardiovascular baseline for Crew C002."""
    return {
        "crew_id": "C002",
        "rest_hr_bpm": 62.0,
        "rest_hr_sd": 4.0,
        "sbp_mmHg": 116.0,
        "sbp_sd": 6.0,
        "dbp_mmHg": 74.0,
        "dbp_sd": 5.0,
        "spo2_pct": 98.4,
        "spo2_sd": 0.6,
        "resp_rate_bpm": 14.0,
        "resp_rate_sd": 1.5,
        "pvc_burden_pct": 0.25,
        "stand_hr_rise_bpm": 11.0,
        "stand_sbp_drop_mmHg": 4.0,
        "steady_hr_150w_bpm": 134.0,
        "steady_hr_150w_sd": 5.0,
        "gls_pct": -20.0,
        "gls_change_pct": 0.0,
        "hb_g_dl": 14.4,
        "hct_pct": 43.0,
        "potassium_mmol_l": 4.2,
        "sodium_mmol_l": 140.0,
        "albumin_g_dl": 4.4,
        "total_protein_g_dl": 7.1,
        "fibrinogen_mg_dl": 285.0,
        "pf4_ng_ml": 8.0,
        "crp_mg_l": 0.9,
    }


def _generate_longitudinal_series(scenario: str = "green", mission_day: int = 124) -> dict[str, dict[str, list[Any]]]:
    """Generate realistic multi-day synthetic trajectories (Days 1-124) for Crew C002."""
    scen = (scenario or "green").strip().lower()
    days = [1, 15, 30, 60, 90, 110, 117, int(mission_day)]

    if scen == "red":
        hr_vals = [62, 65, 70, 76, 84, 90, 94, 98]
        sbp_vals = [116, 120, 124, 132, 140, 146, 151, 156]
        dbp_vals = [74, 76, 79, 83, 88, 92, 95, 97]
        spo2_vals = [98.4, 98.0, 97.4, 96.6, 95.1, 93.8, 92.6, 91.2]
        resp_vals = [14.0, 15.0, 16.5, 18.0, 20.5, 22.5, 24.5, 26.5]
        pvc_vals = [0.2, 0.4, 0.8, 1.5, 2.8, 4.1, 5.2, 6.4]
        stand_hr_vals = [11, 14, 18, 22, 26, 29, 32, 35]
        stand_sbp_vals = [4, 6, 9, 13, 17, 21, 24, 27]
        cevis_vals = [134, 138, 143, 149, 156, 161, 165, 169]
        gls_chg_vals = [0.0, -2.0, -4.5, -7.5, -10.5, -13.5, -16.0, -18.2]
        hb_vals = [14.4, 15.0, 15.3, 15.6, 15.9, 16.2, 16.4, 16.6]
        hct_vals = [43.0, 44.5, 45.4, 46.2, 47.0, 47.7, 48.3, 48.8]
        k_vals = [4.2, 4.1, 3.9, 3.7, 3.5, 3.3, 3.15, 3.05]
        crp_chg_vals = [0, 8, 18, 32, 48, 65, 82, 96]
    elif scen == "yellow":
        hr_vals = [62, 63, 66, 69, 73, 76, 79, 82]
        sbp_vals = [116, 118, 121, 125, 130, 134, 137, 139]
        dbp_vals = [74, 75, 77, 79, 82, 84, 86, 88]
        spo2_vals = [98.4, 98.1, 97.8, 97.3, 96.8, 96.2, 95.8, 95.4]
        resp_vals = [14.0, 14.5, 15.2, 16.2, 17.5, 18.4, 19.2, 20.2]
        pvc_vals = [0.2, 0.3, 0.5, 0.9, 1.4, 1.8, 2.2, 2.6]
        stand_hr_vals = [11, 13, 15, 17, 20, 22, 24, 25]
        stand_sbp_vals = [4, 5, 7, 9, 11, 13, 15, 16]
        cevis_vals = [134, 136, 139, 142, 146, 149, 151, 153]
        gls_chg_vals = [0.0, -1.5, -3.0, -5.0, -7.2, -9.0, -10.4, -11.6]
        hb_vals = [14.4, 14.8, 15.0, 15.2, 15.4, 15.6, 15.7, 15.9]
        hct_vals = [43.0, 44.0, 44.6, 45.2, 45.8, 46.2, 46.6, 47.0]
        k_vals = [4.2, 4.1, 4.0, 3.9, 3.75, 3.65, 3.55, 3.45]
        crp_chg_vals = [0, 4, 9, 15, 22, 28, 34, 38]
    else:
        hr_vals = [62, 62, 63, 63, 64, 64, 64, 65]
        sbp_vals = [116, 116, 117, 118, 118, 119, 118, 119]
        dbp_vals = [74, 74, 75, 74, 75, 75, 74, 75]
        spo2_vals = [98.4, 98.5, 98.3, 98.4, 98.2, 98.3, 98.2, 98.2]
        resp_vals = [14.0, 14.0, 14.2, 14.5, 14.3, 14.6, 14.5, 14.5]
        pvc_vals = [0.2, 0.2, 0.25, 0.25, 0.3, 0.3, 0.3, 0.3]
        stand_hr_vals = [11, 11, 12, 12, 12, 13, 12, 12]
        stand_sbp_vals = [4, 4, 5, 5, 5, 5, 5, 5]
        cevis_vals = [134, 134, 135, 135, 136, 136, 136, 137]
        gls_chg_vals = [0.0, -0.5, -1.0, -1.5, -2.0, -2.2, -2.4, -2.5]
        hb_vals = [14.4, 14.6, 14.7, 14.7, 14.8, 14.8, 14.8, 14.9]
        hct_vals = [43.0, 43.4, 43.6, 43.7, 43.8, 43.9, 43.9, 44.0]
        k_vals = [4.2, 4.2, 4.15, 4.2, 4.15, 4.2, 4.18, 4.15]
        crp_chg_vals = [0, 2, 3, 4, 4, 5, 4, 5]

    return {
        "days": days,
        "rest_hr_bpm": {"days": days, "values": hr_vals},
        "sbp_mmHg": {"days": days, "values": sbp_vals},
        "dbp_mmHg": {"days": days, "values": dbp_vals},
        "spo2_pct": {"days": days, "values": spo2_vals},
        "resp_rate_bpm": {"days": days, "values": resp_vals},
        "pvc_burden_pct": {"days": days, "values": pvc_vals},
        "stand_hr_rise_bpm": {"days": days, "values": stand_hr_vals},
        "stand_sbp_drop_mmHg": {"days": days, "values": stand_sbp_vals},
        "steady_hr_150w_bpm": {"days": days, "values": cevis_vals},
        "gls_change_pct": {"days": days, "values": gls_chg_vals},
        "hb_g_dl": {"days": days, "values": hb_vals},
        "hct_pct": {"days": days, "values": hct_vals},
        "potassium_mmol_l": {"days": days, "values": k_vals},
        "crp_change_pct": {"days": days, "values": crp_chg_vals},
    }


def demo_payload(scenario: str = "green") -> dict[str, Any]:
    """Return Crew C002 mission day 124 telemetry payload for green/yellow/red/bad_data."""
    scen = (scenario or "green").strip().lower()
    series = _generate_longitudinal_series(scen, mission_day=124)

    if scen == "bad_data":
        return {
            "crew_id": "C002",
            "mission_day": 124,
            "data_source": "SIMULATED",
            "scenario": "bad_data",
            "ecg_lead_quality": 0.24,
            "motion_artifact_g": 0.85,
            "ptt_calibrated_days_ago": 14,
            "rest_hr_bpm": None,
            "sbp_mmHg": 118.0,
            "dbp_mmHg": 74.0,
            "spo2_pct": 38.0,  # physiologically impossible sensor dropout
            "resp_rate_bpm": 15.0,
            "pvc_burden_pct": 0.3,
            "afib_detected": False,
            "mitbih_record_check": "100",
            "stand_hr_rise_bpm": 12.0,
            "stand_sbp_drop_mmHg": 5.0,
            "dizzy": False,
            "protocol_mode": "LBNP",
            "prcp_reference_ok": True,
            "steady_hr_150w_bpm": 136.0,
            "gls_pct": -19.5,
            "gls_change_pct": -2.5,
            "ijv_flow": "forward",
            "ijv_compressible": True,
            "ijv_thrombus": False,
            "hb_g_dl": 14.8,
            "hct_pct": 44.0,
            "potassium_mmol_l": 4.15,
            "sodium_mmol_l": 140.0,
            "albumin_g_dl": 4.3,
            "total_protein_g_dl": 7.0,
            "fibrinogen_mg_dl": 290.0,
            "pf4_ng_ml": 8.5,
            "crp_mg_l": 0.95,
            "crp_change_pct": 5.0,
            "_history_series": series,
        }

    if scen == "yellow":
        return {
            "crew_id": "C002",
            "mission_day": 124,
            "data_source": "SIMULATED",
            "scenario": "yellow",
            "ecg_lead_quality": 0.93,
            "motion_artifact_g": 0.08,
            "ptt_calibrated_days_ago": 4,
            "rest_hr_bpm": 82.0,
            "sbp_mmHg": 139.0,
            "dbp_mmHg": 88.0,
            "spo2_pct": 95.4,
            "resp_rate_bpm": 20.2,
            "pvc_burden_pct": 2.6,
            "afib_detected": False,
            "mitbih_record_check": "106",
            "stand_hr_rise_bpm": 25.0,
            "stand_sbp_drop_mmHg": 16.0,
            "dizzy": False,
            "protocol_mode": "LBNP",
            "prcp_reference_ok": True,
            "steady_hr_150w_bpm": 153.0,
            "gls_pct": -17.7,
            "gls_change_pct": -11.6,
            "ijv_flow": "stagnant",
            "ijv_compressible": True,
            "ijv_thrombus": False,
            "hb_g_dl": 15.9,
            "hct_pct": 47.0,
            "potassium_mmol_l": 3.45,
            "sodium_mmol_l": 143.0,
            "albumin_g_dl": 4.6,
            "total_protein_g_dl": 7.5,
            "fibrinogen_mg_dl": 360.0,
            "pf4_ng_ml": 14.0,
            "crp_mg_l": 1.24,
            "crp_change_pct": 38.0,
            "_history_series": series,
        }

    if scen == "red":
        return {
            "crew_id": "C002",
            "mission_day": 124,
            "data_source": "SIMULATED",
            "scenario": "red",
            "ecg_lead_quality": 0.95,
            "motion_artifact_g": 0.06,
            "ptt_calibrated_days_ago": 2,
            "rest_hr_bpm": 98.0,
            "sbp_mmHg": 156.0,
            "dbp_mmHg": 97.0,
            "spo2_pct": 91.2,
            "resp_rate_bpm": 26.5,
            "pvc_burden_pct": 6.4,
            "afib_detected": True,
            "mitbih_record_check": "208",
            "stand_hr_rise_bpm": 35.0,
            "stand_sbp_drop_mmHg": 27.0,
            "dizzy": True,
            "protocol_mode": "LBNP",
            "prcp_reference_ok": True,
            "steady_hr_150w_bpm": 169.0,
            "gls_pct": -16.4,
            "gls_change_pct": -18.2,
            "ijv_flow": "reversed",
            "ijv_compressible": False,
            "ijv_thrombus": True,
            "hb_g_dl": 16.6,
            "hct_pct": 48.8,
            "potassium_mmol_l": 3.05,
            "sodium_mmol_l": 147.0,
            "albumin_g_dl": 5.0,
            "total_protein_g_dl": 8.1,
            "fibrinogen_mg_dl": 460.0,
            "pf4_ng_ml": 26.0,
            "crp_mg_l": 1.76,
            "crp_change_pct": 96.0,
            "_history_series": series,
        }

    # Default: green (Day 124 nominal)
    return {
        "crew_id": "C002",
        "mission_day": 124,
        "data_source": "SIMULATED",
        "scenario": "green",
        "ecg_lead_quality": 0.97,
        "motion_artifact_g": 0.04,
        "ptt_calibrated_days_ago": 3,
        "rest_hr_bpm": 65.0,
        "sbp_mmHg": 119.0,
        "dbp_mmHg": 75.0,
        "spo2_pct": 98.2,
        "resp_rate_bpm": 14.5,
        "pvc_burden_pct": 0.3,
        "afib_detected": False,
        "mitbih_record_check": "100",
        "stand_hr_rise_bpm": 12.0,
        "stand_sbp_drop_mmHg": 5.0,
        "dizzy": False,
        "protocol_mode": "LBNP",
        "prcp_reference_ok": True,
        "steady_hr_150w_bpm": 137.0,
        "gls_pct": -19.5,
        "gls_change_pct": -2.5,
        "ijv_flow": "forward",
        "ijv_compressible": True,
        "ijv_thrombus": False,
        "hb_g_dl": 14.9,
        "hct_pct": 44.0,
        "potassium_mmol_l": 4.15,
        "sodium_mmol_l": 140.0,
        "albumin_g_dl": 4.4,
        "total_protein_g_dl": 7.1,
        "fibrinogen_mg_dl": 290.0,
        "pf4_ng_ml": 8.2,
        "crp_mg_l": 0.94,
        "crp_change_pct": 5.0,
        "_history_series": series,
    }


# ---------------------------------------------------------------------------
# CSV / Real Dataset Loaders (Zero FileNotFoundError Guarantee)
# ---------------------------------------------------------------------------

def generate_synthetic_dataframes(scenario: str = "green", crew_id: str = "C002") -> dict[str, pd.DataFrame]:
    """Build realistic in-memory DataFrames matching the documented cardiovascular CSV schemas."""
    series = _generate_longitudinal_series(scenario=scenario, mission_day=124)
    days = series["days"]

    daily_df = pd.DataFrame(
        {
            "crew_id": [crew_id] * len(days),
            "mission_day": days,
            "rest_hr_bpm": series["rest_hr_bpm"]["values"],
            "sbp_mmHg": series["sbp_mmHg"]["values"],
            "dbp_mmHg": series["dbp_mmHg"]["values"],
            "spo2_pct": series["spo2_pct"]["values"],
            "resp_rate_bpm": series["resp_rate_bpm"]["values"],
            "ecg_lead_quality": [0.96] * len(days),
            "motion_artifact_g": [0.05] * len(days),
            "ptt_calibrated_days_ago": [3] * len(days),
        }
    )

    bike_df = pd.DataFrame(
        {
            "crew_id": [crew_id] * len(days),
            "mission_day": days,
            "steady_hr_150w_bpm": series["steady_hr_150w_bpm"]["values"],
            "cevis_power_w": [150] * len(days),
            "hr_drift_bpm": [round(v - 134.0, 1) for v in series["steady_hr_150w_bpm"]["values"]],
        }
    )

    stand_df = pd.DataFrame(
        {
            "crew_id": [crew_id] * len(days),
            "mission_day": days,
            "protocol_mode": ["LBNP"] * len(days),
            "stand_hr_rise_bpm": series["stand_hr_rise_bpm"]["values"],
            "stand_sbp_drop_mmHg": series["stand_sbp_drop_mmHg"]["values"],
            "dizzy": [False] * (len(days) - 1) + [scenario == "red"],
            "prcp_reference_ok": [True] * len(days),
        }
    )

    holter_df = pd.DataFrame(
        {
            "crew_id": [crew_id] * len(days),
            "mission_day": days,
            "pvc_burden_pct": series["pvc_burden_pct"]["values"],
            "afib_detected": [False] * (len(days) - 1) + [scenario == "red"],
            "mitbih_record_check": ["100"] * (len(days) - 1)
            + [{"red": "208", "yellow": "106"}.get(scenario, "100")],
            "mitbih_pvc_rate_pct": series["pvc_burden_pct"]["values"],
        }
    )

    ijv_states = ["forward"] * (len(days) - 1) + [
        {"red": "reversed", "yellow": "stagnant"}.get(scenario, "forward")
    ]
    ultrasound_df = pd.DataFrame(
        {
            "crew_id": [crew_id] * len(days),
            "mission_day": days,
            "gls_pct": [round(-20.0 * (1.0 + v / 100.0), 2) for v in series["gls_change_pct"]["values"]],
            "gls_change_pct": series["gls_change_pct"]["values"],
            "ijv_flow": ijv_states,
            "ijv_compressible": [s != "reversed" for s in ijv_states],
            "ijv_thrombus": [s == "reversed" for s in ijv_states],
        }
    )

    # 15-minute high-resolution Day-124 Bio-Monitor stream
    t_mins = list(range(0, 60, 5))
    last_hr = series["rest_hr_bpm"]["values"][-1]
    last_sbp = series["sbp_mmHg"]["values"][-1]
    last_dbp = series["dbp_mmHg"]["values"][-1]
    last_spo2 = series["spo2_pct"]["values"][-1]
    last_resp = series["resp_rate_bpm"]["values"][-1]
    stream_df = pd.DataFrame(
        {
            "crew_id": [crew_id] * len(t_mins),
            "mission_day": [124] * len(t_mins),
            "timestamp_min": t_mins,
            "hr_bpm": [round(last_hr + ((i % 3) - 1) * 0.5, 1) for i in range(len(t_mins))],
            "sbp_mmHg": [round(last_sbp + ((i % 2) - 0.5) * 1.0, 1) for i in range(len(t_mins))],
            "dbp_mmHg": [round(last_dbp + ((i % 2) - 0.5) * 0.5, 1) for i in range(len(t_mins))],
            "spo2_pct": [last_spo2] * len(t_mins),
            "resp_rate_bpm": [last_resp] * len(t_mins),
            "ecg_lead_quality": [0.97] * len(t_mins),
            "motion_artifact_g": [0.04] * len(t_mins),
        }
    )

    return {
        "daily_vitals.csv": daily_df,
        "bike_test.csv": bike_df,
        "stand_test.csv": stand_df,
        "holter_24h.csv": holter_df,
        "ultrasound.csv": ultrasound_df,
        "biomonitor_stream_day124.csv": stream_df,
    }


def export_demo_csvs(overwrite: bool = False) -> list[str]:
    """Write starter CSV templates and preflight_baseline.json to data/cardiovascular/.

    If files already exist and do not match the expected cardiovascular schemas
    (e.g., generic placeholder files), replace them when `overwrite=True` or when empty.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    dfs = generate_synthetic_dataframes(scenario="green", crew_id="C002")

    for filename, df in dfs.items():
        path = DATA_DIR / filename
        needs_write = overwrite or (not path.exists()) or path.stat().st_size == 0
        if not needs_write and path.exists():
            try:
                existing_cols = set(pd.read_csv(path, nrows=1).columns)
                expected_cols = set(EXPECTED_CSV_SCHEMAS.get(filename, []))
                if not expected_cols.issubset(existing_cols):
                    needs_write = True
            except Exception:
                needs_write = True
        if needs_write:
            df.to_csv(path, index=False)
            written.append(str(path))

    baseline_path = DATA_DIR / "preflight_baseline.json"
    if overwrite or not baseline_path.exists():
        with baseline_path.open("w", encoding="utf-8") as fh:
            json.dump(demo_baseline(), fh, indent=2)
        written.append(str(baseline_path))

    return written


def check_data_files() -> dict[str, Any]:
    """Inspect data/cardiovascular/ and data/shared_real/ without raising errors."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SHARED_REAL_DIR.mkdir(parents=True, exist_ok=True)

    present_local = [f for f in EXPECTED_CSV_SCHEMAS if (DATA_DIR / f).exists()]
    missing_local = [f for f in EXPECTED_CSV_SCHEMAS if f not in present_local]

    shared_expected = ["OSD-569_inspiration4_cbc.csv", "OSD-575_cmp.csv", "OSD-575_cv_panel.csv"]
    present_shared = [f for f in shared_expected if (SHARED_REAL_DIR / f).exists()]
    missing_shared = [f for f in shared_expected if f not in present_shared]

    real_files = sorted([p.name for p in REAL_SUBDIR.iterdir() if p.is_file()]) if REAL_SUBDIR.exists() else []
    return {
        "local_dir": str(DATA_DIR),
        "present_local": present_local,
        "missing_local": missing_local,
        "shared_dir": str(SHARED_REAL_DIR),
        "present_shared": present_shared,
        "missing_shared": missing_shared,
        "real_dir": str(REAL_SUBDIR),
        "real_files": real_files,
        "schemas": EXPECTED_CSV_SCHEMAS,
    }


def _load_shared_osdr_overrides() -> tuple[dict[str, Any], bool]:
    """Safely inspect data/shared_real/ for OSD-569 and OSD-575 CSVs. Never crashes."""
    updates: dict[str, Any] = {}
    found_real = False

    osd569_candidates = [
        SHARED_REAL_DIR / "OSD-569_inspiration4_cbc.csv",
        SHARED_REAL_DIR / "osd569_cbc_transformed.csv",
    ]
    for path in osd569_candidates:
        if path.exists():
            try:
                df = pd.read_csv(path)
                if not df.empty:
                    row = df.iloc[-1].to_dict()
                    for k in ("hb_g_dl", "hgb", "hemoglobin"):
                        if k in row and _safe_float(row[k]) is not None:
                            updates["hb_g_dl"] = _safe_float(row[k])
                            found_real = True
                    for k in ("hct_pct", "hct", "hematocrit"):
                        if k in row and _safe_float(row[k]) is not None:
                            val = _safe_float(row[k])
                            if val is not None:
                                updates["hct_pct"] = val * 100.0 if val <= 1.0 else val
                                found_real = True
            except Exception:
                pass
            break

    for fname in ("OSD-575_cmp.csv", "osd575_cmp.csv", "OSD-575_cv_panel.csv"):
        path = SHARED_REAL_DIR / fname
        if path.exists():
            try:
                df = pd.read_csv(path)
                if not df.empty:
                    row = {str(k).lower(): v for k, v in df.iloc[-1].to_dict().items()}
                    mapping = {
                        "potassium_mmol_l": ("potassium_mmol_l", "potassium", "k", "k_mmol_l"),
                        "sodium_mmol_l": ("sodium_mmol_l", "sodium", "na", "na_mmol_l"),
                        "albumin_g_dl": ("albumin_g_dl", "albumin"),
                        "total_protein_g_dl": ("total_protein_g_dl", "total_protein"),
                        "fibrinogen_mg_dl": ("fibrinogen_mg_dl", "fibrinogen"),
                        "pf4_ng_ml": ("pf4_ng_ml", "pf4"),
                        "crp_mg_l": ("crp_mg_l", "crp"),
                    }
                    for target, aliases in mapping.items():
                        for alias in aliases:
                            if alias in row and _safe_float(row[alias]) is not None:
                                updates[target] = _safe_float(row[alias])
                                found_real = True
                                break
            except Exception:
                pass

    return updates, found_real


def _extract_history_from_payload(payload: dict[str, Any], scenario: str, mission_day: int) -> dict[str, dict[str, list[Any]]]:
    """Extract time-series history from CSV records in payload or fall back to synthetic history."""
    fallback = _generate_longitudinal_series(scenario=scenario, mission_day=mission_day)
    if isinstance(payload.get("_history_series"), dict):
        fallback.update(payload["_history_series"])

    csv_table_map = {
        "csv_daily_vitals": ["rest_hr_bpm", "sbp_mmHg", "dbp_mmHg", "spo2_pct", "resp_rate_bpm"],
        "csv_bike_test": ["steady_hr_150w_bpm"],
        "csv_stand_test": ["stand_hr_rise_bpm", "stand_sbp_drop_mmHg"],
        "csv_holter_24h": ["pvc_burden_pct"],
        "csv_ultrasound": ["gls_change_pct"],
    }
    for key, cols in csv_table_map.items():
        records = payload.get(key)
        if isinstance(records, list) and len(records) >= 2:
            days = []
            for idx, r in enumerate(records, start=1):
                if isinstance(r, dict):
                    d = _safe_float(r.get("mission_day"), float(idx * 30))
                    days.append(int(d) if d is not None else idx * 30)
            for col in cols:
                vals = []
                valid_days = []
                for d, r in zip(days, records):
                    if isinstance(r, dict):
                        v = _safe_float(r.get(col))
                        if v is not None:
                            valid_days.append(d)
                            vals.append(v)
                if len(vals) >= 2:
                    fallback[col] = {"days": valid_days, "values": vals}

    return fallback


# ---------------------------------------------------------------------------
# Layer 0 QC Gatekeeper
# ---------------------------------------------------------------------------

def run_qc_gatekeeper(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    """Layer 0 Data Quality Gatekeeper.

    Flags poor ECG contact, excessive motion artifact, stale PTT calibration,
    missing critical fields, or physiologically impossible values.
    """
    reasons: list[str] = []

    lead_q = _safe_float(payload.get("ecg_lead_quality"), 0.95)
    if lead_q is None or lead_q < 0.50:
        reasons.append(f"Bio-Monitor ECG lead quality too low ({lead_q} < 0.50).")

    motion_g = _safe_float(payload.get("motion_artifact_g"), 0.05)
    if motion_g is not None and motion_g > 0.50:
        reasons.append(f"Excessive motion artifact ({motion_g:.2f} g > 0.50 g).")

    rest_hr = _safe_float(payload.get("rest_hr_bpm"))
    if rest_hr is None or rest_hr <= 20.0 or rest_hr > 240.0:
        reasons.append(f"Resting HR missing or physiologically invalid ({payload.get('rest_hr_bpm')}).")

    spo2 = _safe_float(payload.get("spo2_pct"))
    if spo2 is None or spo2 < 50.0 or spo2 > 100.0:
        reasons.append(f"SpO2 missing or physiologically invalid ({payload.get('spo2_pct')}%).")

    sbp = _safe_float(payload.get("sbp_mmHg"))
    dbp = _safe_float(payload.get("dbp_mmHg"))
    if sbp is None or dbp is None or sbp < 40.0 or sbp > 260.0 or dbp < 20.0 or dbp > 160.0 or sbp <= dbp:
        reasons.append(f"Blood pressure missing or invalid ({sbp}/{dbp} mmHg).")

    resp = _safe_float(payload.get("resp_rate_bpm"))
    if resp is None or resp < 4.0 or resp > 60.0:
        reasons.append(f"Respiratory rate missing or invalid ({resp} breaths/min).")

    return len(reasons) == 0, reasons


# ---------------------------------------------------------------------------
# 3-Layer Evaluation Engine for All 11 Measurements (M1-M11)
# ---------------------------------------------------------------------------

def _combine_three_layers(
    layer1_status: str,
    layer2_status: str,
    trend_yellow: bool,
    days_until_red: Optional[int],
) -> tuple[str, str]:
    """Worst-result-wins combination across Layer 1 (Rules), Layer 2 (Baseline), Layer 3 (Trend)."""
    layer3_status = "YELLOW" if trend_yellow else "GREEN"
    overall = _worst_status([layer1_status, layer2_status, layer3_status])

    if overall == layer1_status and layer1_status != "GREEN":
        decided_by = "rule"
    elif overall == layer2_status and layer2_status != "GREEN":
        decided_by = "baseline"
    elif trend_yellow and overall == "YELLOW":
        decided_by = "trend"
    else:
        decided_by = "rule"

    return overall, decided_by


def _build_bad_data_result(
    crew_id: str,
    mission_day: int,
    data_source: str,
    reasons: list[str],
    payload: dict[str, Any],
) -> dict[str, Any]:
    reason_summary = " ".join(reasons)
    metrics = [
        {
            "metric_name": "ecg_lead_quality",
            "indicator": "M0: Layer 0 Bio-Monitor QC Gatekeeper",
            "current_val": _safe_float(payload.get("ecg_lead_quality"), 0.0),
            "value": _safe_float(payload.get("ecg_lead_quality"), 0.0),
            "baseline_val": 0.95,
            "unit": "ratio",
            "status_light": "INSUFFICIENT_DATA",
            "status": "INSUFFICIENT_DATA",
            "quality_passed": False,
            "decided_by": "quality_check",
            "data_source": data_source,
            "message": reason_summary,
            "action": "Moisten Bio-Monitor textile electrodes, tighten thoracic strap, remain still 60s, and re-measure.",
            "how_to_measure": "Wet Bio-Monitor thoracic electrodes with sterile wipe, fasten strap snugly at xiphoid level, and sit still for 60 seconds.",
            "why_in_space": "Microgravity shifts chest shape and reduces skin moisture; dry electrodes or motion cause false PVC/SpO2 alarms.",
        }
    ]

    actions = [
        "Re-wet Bio-Monitor thoracic ECG pads and tighten chest strap.",
        "Clean optical SpO2 fingertip/wrist sensor and eliminate cabin vibration/motion for 60 seconds.",
        "Repeat resting vitals capture immediately before running clinical evaluation.",
    ]

    result = ModuleEvaluationResult(
        module_id="cardiovascular",
        body_part_tag="heart_vascular",
        crew_id=crew_id,
        mission_day=mission_day,
        status_light="INSUFFICIENT_DATA",
        quality_passed=False,
        data_source=data_source,
        summary_note=f"Layer 0 QC Gatekeeper rejected telemetry: {reason_summary}",
        metrics=[MetricItem(**m) for m in metrics],
        guidance=CrewGuidance(
            how_to_measure="Verify Bio-Monitor ECG strap skin contact (quality >= 0.50), keep motion < 0.50 g, and confirm weekly BP cuff calibration.",
            plain_explanation="Sensor dropout, dry electrodes, or impossible readings (e.g., SpO2 < 50% or null HR) cannot safely evaluate heart or clot status.",
            action_protocol=actions,
        ),
        short_term_plan=ShortTermPlan(
            next_measurement_in_hours=0,
            immediate_actions=actions,
            urgent_alert=False,
        ),
        long_term_plan=LongTermPlan(
            days_until_red_prediction=None,
            routine_prescription_adjustment="Inspect Bio-Monitor garment conductive pads and SpO2 clip during weekly hardware check.",
        ),
    )
    out = result.model_dump()
    out["overall_status"] = out["status_light"]
    out["indicators"] = out["metrics"]
    return out


def evaluate(
    payload: Optional[dict[str, Any]] = None,
    baseline: Optional[dict[str, Any]] = None,
    manual_inputs: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Stateless 3-layer Cardiovascular & Aerobic evaluation (M1-M11).

    Supports:
    - `payload`: batch/CSV/demo dictionary
    - `baseline`: pre-flight baseline dictionary
    - `manual_inputs`: optional real-time UI slider/form overrides (takes highest precedence)
    """
    base = {**demo_baseline(), **(baseline or {})}

    # Determine starting scenario without crashing if files are absent
    raw_pay = dict(payload or {})
    scenario = str(raw_pay.get("scenario", "green")).strip().lower()
    if scenario not in {"green", "yellow", "red", "bad_data"}:
        scenario = "green"

    # Merge synthetic fallback -> shared OSDR if available -> incoming payload -> manual_inputs
    merged: dict[str, Any] = demo_payload(scenario)
    osdr_updates, has_osdr_real = _load_shared_osdr_overrides()
    merged.update(osdr_updates)
    merged.update({k: v for k, v in raw_pay.items() if v is not None or k in {"rest_hr_bpm", "spo2_pct"}})
    if manual_inputs:
        for k, v in manual_inputs.items():
            if v is not None:
                merged[k] = v

    crew_id = str(merged.get("crew_id", base.get("crew_id", "C002")))
    mission_day = int(_safe_float(merged.get("mission_day"), 124) or 124)

    has_csv_records = any(k.startswith("csv_") for k in merged)
    if merged.get("data_source"):
        data_source = str(merged["data_source"]).upper()
    elif has_csv_records or has_osdr_real:
        data_source = "REAL"
    else:
        data_source = "SIMULATED"

    # --- Layer 0: QC Gatekeeper ---
    qc_ok, qc_reasons = run_qc_gatekeeper(merged)
    if not qc_ok:
        return _build_bad_data_result(crew_id, mission_day, data_source, qc_reasons, merged)

    history = _extract_history_from_payload(merged, scenario=scenario, mission_day=mission_day)

    def _hist(key: str, current_val: float) -> tuple[list[int], list[float]]:
        item = history.get(key)
        if item and len(item.get("days", [])) >= 2:
            d = list(item["days"])
            v = [float(x) for x in item["values"]]
            if d[-1] == mission_day:
                v[-1] = float(current_val)
            else:
                d.append(mission_day)
                v.append(float(current_val))
            return d, v
        base_v = _safe_float(base.get(key), current_val) or current_val
        days_arr = [1, 30, 60, 90, mission_day]
        step = (current_val - base_v) / 4.0
        vals_arr = [round(base_v + step * i, 2) for i in range(5)]
        return days_arr, vals_arr

    metrics: list[dict[str, Any]] = []
    projected_red_days: list[int] = []

    # ------------------------------------------------------------------
    # M1: Resting Heart Rate (Bio-Monitor)
    # ------------------------------------------------------------------
    rest_hr = float(_safe_float(merged.get("rest_hr_bpm"), base["rest_hr_bpm"]))
    hr_l1 = "RED" if (rest_hr >= 100 or rest_hr <= 40) else ("YELLOW" if (rest_hr >= 80 or rest_hr < 48) else "GREEN")
    hr_l2, hr_delta_pct = _layer2_baseline_status(
        rest_hr, base["rest_hr_bpm"], sd=base.get("rest_hr_sd", 4.0), warn_sd=3.0, red_sd=6.0, warn_pct=20.0, red_pct=45.0, direction="high"
    )
    hr_days, hr_vals = _hist("rest_hr_bpm", rest_hr)
    hr_slope, hr_days_red, hr_trend_warn = _linear_trend_projection(hr_days, hr_vals, red_threshold=100.0, lower_is_worse=False)
    hr_status, hr_by = _combine_three_layers(hr_l1, hr_l2, hr_trend_warn, hr_days_red)
    if hr_days_red is not None and hr_status != "RED":
        projected_red_days.append(hr_days_red)
    metrics.append({
        "metric_name": "rest_hr_bpm",
        "indicator": "M1: Resting Heart Rate (Bio-Monitor)",
        "current_val": round(rest_hr, 1),
        "value": round(rest_hr, 1),
        "baseline_val": float(base["rest_hr_bpm"]),
        "delta_pct": hr_delta_pct,
        "slope_per_day": hr_slope,
        "unit": "bpm",
        "status_light": hr_status,
        "status": hr_status,
        "decided_by": hr_by,
        "data_source": data_source,
        "yellow_threshold": 80.0,
        "red_threshold": 100.0,
        "lower_is_worse": False,
        "history_days": hr_days,
        "history_values": hr_vals,
        "message": f"Resting HR {rest_hr:.1f} bpm (baseline {base['rest_hr_bpm']:.0f} bpm, slope {hr_slope:+.3f}/day).",
        "action": "Evaluate hydration, sleep debt, infection, or sympathetic stress." if hr_status != "GREEN" else "Autonomic resting heart rate nominal.",
        "how_to_measure": "Sit or float relaxed for 5 min wearing Bio-Monitor thoracic ECG garment; avoid caffeine 2h prior.",
        "why_in_space": "Elevated resting HR signals plasma volume loss, stress, infection, or cardiovascular deconditioning.",
    })

    # ------------------------------------------------------------------
    # M2: Blood Pressure (Bio-Monitor PTT + Weekly Arm Cuff + PRCP check)
    # ------------------------------------------------------------------
    sbp = float(_safe_float(merged.get("sbp_mmHg"), base["sbp_mmHg"]))
    dbp = float(_safe_float(merged.get("dbp_mmHg"), base["dbp_mmHg"]))
    ptt_age = int(_safe_float(merged.get("ptt_calibrated_days_ago"), 3) or 3)
    bp_l1 = "RED" if (sbp >= 160 or dbp >= 100 or sbp <= 85) else ("YELLOW" if (sbp >= 140 or dbp >= 90 or sbp <= 95) else "GREEN")
    sbp_l2, sbp_delta_pct = _layer2_baseline_status(sbp, base["sbp_mmHg"], sd=base.get("sbp_sd", 6.0), warn_sd=2.5, red_sd=4.0, direction="both")
    sbp_days, sbp_vals = _hist("sbp_mmHg", sbp)
    sbp_slope, sbp_days_red, sbp_trend_warn = _linear_trend_projection(sbp_days, sbp_vals, red_threshold=160.0, lower_is_worse=False)
    bp_status, bp_by = _combine_three_layers(bp_l1, sbp_l2, sbp_trend_warn, sbp_days_red)
    if sbp_days_red is not None and bp_status != "RED":
        projected_red_days.append(sbp_days_red)
    cal_note = " (cuff recalibration due >7d)" if ptt_age > 7 else ""
    metrics.append({
        "metric_name": "sbp_mmHg",
        "indicator": "M2: Blood Pressure (PTT + Cuff & PRCP)",
        "current_val": round(sbp, 1),
        "value": f"{sbp:.0f}/{dbp:.0f}",
        "baseline_val": float(base["sbp_mmHg"]),
        "delta_pct": sbp_delta_pct,
        "slope_per_day": sbp_slope,
        "unit": "mmHg",
        "status_light": bp_status,
        "status": bp_status,
        "decided_by": bp_by,
        "data_source": data_source,
        "yellow_threshold": 140.0,
        "red_threshold": 160.0,
        "lower_is_worse": False,
        "history_days": sbp_days,
        "history_values": sbp_vals,
        "message": f"BP {sbp:.0f}/{dbp:.0f} mmHg vs baseline {base['sbp_mmHg']:.0f}/{base['dbp_mmHg']:.0f}{cal_note}.",
        "action": "Verify with manual arm cuff & evaluate fluid/sodium load." if bp_status != "GREEN" else "Vascular pressure within NASA-STD-3001 bounds.",
        "how_to_measure": "Continuous Bio-Monitor Pulse Transit Time (PTT) calibrated weekly with brachial arm cuff at heart level.",
        "why_in_space": "Tracks arterial baroreceptor adaptation and hypertension/hypotension risk across microgravity and PhysioNet PRCP profiles.",
    })

    # ------------------------------------------------------------------
    # M3: SpO2 (Bio-Monitor Optical)
    # ------------------------------------------------------------------
    spo2 = float(_safe_float(merged.get("spo2_pct"), base["spo2_pct"]))
    spo2_l1 = "RED" if spo2 <= 92.0 else ("YELLOW" if spo2 < 96.0 else "GREEN")
    spo2_l2, spo2_delta_pct = _layer2_baseline_status(spo2, base["spo2_pct"], sd=base.get("spo2_sd", 0.6), warn_sd=3.5, red_sd=7.0, direction="low")
    spo2_days, spo2_vals = _hist("spo2_pct", spo2)
    spo2_slope, spo2_days_red, spo2_trend_warn = _linear_trend_projection(spo2_days, spo2_vals, red_threshold=92.0, lower_is_worse=True)
    spo2_status, spo2_by = _combine_three_layers(spo2_l1, spo2_l2, spo2_trend_warn, spo2_days_red)
    if spo2_days_red is not None and spo2_status != "RED":
        projected_red_days.append(spo2_days_red)
    metrics.append({
        "metric_name": "spo2_pct",
        "indicator": "M3: Oxygen Saturation SpO2 (Bio-Monitor)",
        "current_val": round(spo2, 1),
        "value": round(spo2, 1),
        "baseline_val": float(base["spo2_pct"]),
        "delta_pct": spo2_delta_pct,
        "slope_per_day": spo2_slope,
        "unit": "%",
        "status_light": spo2_status,
        "status": spo2_status,
        "decided_by": spo2_by,
        "data_source": data_source,
        "yellow_threshold": 96.0,
        "red_threshold": 92.0,
        "lower_is_worse": True,
        "history_days": spo2_days,
        "history_values": spo2_vals,
        "message": f"SpO2 {spo2:.1f}% (Yellow < 96%, Red <= 92%).",
        "action": "Cross-check cabin pO2/CO2 and screen for pulmonary embolism if combined with tachypnea." if spo2_status != "GREEN" else "Arterial oxygenation optimal.",
        "how_to_measure": "Ensure warm extremity and snug optical pulse oximeter placement; wait 20s for pleth waveform lock.",
        "why_in_space": "Detects cabin hypoxia, respiratory infection, or pulmonary embolism originating from IJV/DVT clots.",
    })

    # ------------------------------------------------------------------
    # M4: Breathing Rate (Bio-Monitor Chest Sensor)
    # ------------------------------------------------------------------
    resp = float(_safe_float(merged.get("resp_rate_bpm"), base["resp_rate_bpm"]))
    resp_l1 = "RED" if (resp > 25.0 or resp < 8.0) else ("YELLOW" if resp > 20.0 else "GREEN")
    resp_l2, resp_delta_pct = _layer2_baseline_status(resp, base["resp_rate_bpm"], sd=base.get("resp_rate_sd", 1.5), warn_sd=3.0, red_sd=5.0, direction="high")
    resp_days, resp_vals = _hist("resp_rate_bpm", resp)
    resp_slope, resp_days_red, resp_trend_warn = _linear_trend_projection(resp_days, resp_vals, red_threshold=25.0, lower_is_worse=False)
    resp_status, resp_by = _combine_three_layers(resp_l1, resp_l2, resp_trend_warn, resp_days_red)
    if resp_days_red is not None and resp_status != "RED":
        projected_red_days.append(resp_days_red)
    metrics.append({
        "metric_name": "resp_rate_bpm",
        "indicator": "M4: Breathing Rate (Bio-Monitor)",
        "current_val": round(resp, 1),
        "value": round(resp, 1),
        "baseline_val": float(base["resp_rate_bpm"]),
        "delta_pct": resp_delta_pct,
        "slope_per_day": resp_slope,
        "unit": "breaths/min",
        "status_light": resp_status,
        "status": resp_status,
        "decided_by": resp_by,
        "data_source": data_source,
        "yellow_threshold": 20.0,
        "red_threshold": 25.0,
        "lower_is_worse": False,
        "history_days": resp_days,
        "history_values": resp_vals,
        "message": f"Respiratory rate {resp:.1f} breaths/min (Yellow > 20, Red > 25).",
        "action": "Check cabin ppCO2 and correlate with SpO2 & IJV status." if resp_status != "GREEN" else "Resting ventilation normal.",
        "how_to_measure": "Bio-Monitor thoracic impedance band records resting chest excursion while seated/floating quietly.",
        "why_in_space": "Tachypnea (>25/min) warns of CO2 buildup, hypoxia, metabolic acidosis, or pulmonary thromboembolism.",
    })

    # ------------------------------------------------------------------
    # M5: Heart Rhythm & PVC Burden (Holter Monitor 2 + MIT-BIH Check)
    # ------------------------------------------------------------------
    pvc = float(_safe_float(merged.get("pvc_burden_pct"), base["pvc_burden_pct"]))
    afib = _safe_bool(merged.get("afib_detected"), False)
    mitbih_rec = str(merged.get("mitbih_record_check", "100"))
    mitbih_info = MITBIH_REFERENCE_RECORDS.get(mitbih_rec, MITBIH_REFERENCE_RECORDS["100"])
    pvc_l1 = "RED" if (afib or pvc >= 5.0) else ("YELLOW" if pvc >= 1.5 else "GREEN")
    pvc_days, pvc_vals = _hist("pvc_burden_pct", pvc)
    pvc_slope, pvc_days_red, pvc_trend_warn = _linear_trend_projection(pvc_days, pvc_vals, red_threshold=5.0, lower_is_worse=False)
    pvc_status, pvc_by = _combine_three_layers(pvc_l1, "GREEN", pvc_trend_warn, pvc_days_red)
    if pvc_days_red is not None and pvc_status != "RED":
        projected_red_days.append(pvc_days_red)
    metrics.append({
        "metric_name": "pvc_burden_pct",
        "indicator": "M5: Heart Rhythm & PVC Burden (Holter + MIT-BIH)",
        "current_val": round(pvc, 2),
        "value": round(pvc, 2),
        "baseline_val": float(base["pvc_burden_pct"]),
        "delta_pct": round(((pvc - base["pvc_burden_pct"]) / max(base["pvc_burden_pct"], 0.1)) * 100.0, 1),
        "slope_per_day": pvc_slope,
        "unit": "%",
        "status_light": pvc_status,
        "status": pvc_status,
        "decided_by": pvc_by,
        "data_source": data_source,
        "yellow_threshold": 1.5,
        "red_threshold": 5.0,
        "lower_is_worse": False,
        "history_days": pvc_days,
        "history_values": pvc_vals,
        "message": f"Holter PVC {pvc:.2f}%, AFib={'YES' if afib else 'NO'} (MIT-BIH ref {mitbih_rec}: {mitbih_info['rhythm']}).",
        "action": "Check serum K+ (<3.5 mmol/L) immediately & halt max exertion." if pvc_status != "GREEN" else "Sinus rhythm clean.",
        "how_to_measure": "Attach 5-lead Holter Monitor 2 for 24h ambulatory capture; run automated MIT-BIH QRS/PVC template validation.",
        "why_in_space": "Cardiac remodeling, electrolyte shifts (hypokalemia), and stress can trigger PVCs or atrial fibrillation.",
    })

    # ------------------------------------------------------------------
    # M6: Orthostatic Tolerance (LBNP / Stand Test + PRCP Check)
    # ------------------------------------------------------------------
    stand_hr = float(_safe_float(merged.get("stand_hr_rise_bpm"), base["stand_hr_rise_bpm"]))
    stand_sbp = float(_safe_float(merged.get("stand_sbp_drop_mmHg"), base["stand_sbp_drop_mmHg"]))
    dizzy = _safe_bool(merged.get("dizzy"), False)
    proto_mode = str(merged.get("protocol_mode", "LBNP"))
    prcp_ok = _safe_bool(merged.get("prcp_reference_ok"), True)
    stand_l1 = "RED" if (dizzy or stand_hr >= 30.0 or stand_sbp >= 20.0) else ("YELLOW" if (stand_hr >= 20.0 or stand_sbp >= 10.0) else "GREEN")
    stand_days, stand_vals = _hist("stand_hr_rise_bpm", stand_hr)
    stand_slope, stand_days_red, stand_trend_warn = _linear_trend_projection(stand_days, stand_vals, red_threshold=30.0, lower_is_worse=False)
    stand_status, stand_by = _combine_three_layers(stand_l1, "GREEN", stand_trend_warn, stand_days_red)
    if stand_days_red is not None and stand_status != "RED":
        projected_red_days.append(stand_days_red)
    metrics.append({
        "metric_name": "stand_hr_rise_bpm",
        "indicator": "M6: Orthostatic Tolerance (LBNP/Stand + PRCP)",
        "current_val": round(stand_hr, 1),
        "value": round(stand_hr, 1),
        "baseline_val": float(base["stand_hr_rise_bpm"]),
        "delta_pct": round(((stand_hr - base["stand_hr_rise_bpm"]) / max(base["stand_hr_rise_bpm"], 1.0)) * 100.0, 1),
        "slope_per_day": stand_slope,
        "unit": "bpm rise",
        "status_light": stand_status,
        "status": stand_status,
        "decided_by": stand_by,
        "data_source": data_source,
        "yellow_threshold": 20.0,
        "red_threshold": 30.0,
        "lower_is_worse": False,
        "history_days": stand_days,
        "history_values": stand_vals,
        "message": f"{proto_mode} HR rise +{stand_hr:.0f} bpm, SBP drop -{stand_sbp:.0f} mmHg, dizzy={dizzy} (PRCP ref={'OK' if prcp_ok else 'CHECK'}).",
        "action": "Initiate NASA salt-water fluid loading & compression garment check." if stand_status != "GREEN" else "Orthostatic baroreflex intact.",
        "how_to_measure": "Seal waist in LBNP (-25/-40 mmHg) or perform 3-min post-landing stand test while logging HR & SBP.",
        "why_in_space": "Reduced plasma volume and blunted baroreflex cause fainting (presyncope) during planetary landing or EVA.",
    })

    # ------------------------------------------------------------------
    # M7: Aerobic Fitness 150W Bike HR Drift (CEVIS + ECG)
    # ------------------------------------------------------------------
    cevis_hr = float(_safe_float(merged.get("steady_hr_150w_bpm"), base["steady_hr_150w_bpm"]))
    cevis_l1 = "RED" if cevis_hr >= 165.0 else ("YELLOW" if cevis_hr >= 150.0 else "GREEN")
    cevis_l2, cevis_delta_pct = _layer2_baseline_status(cevis_hr, base["steady_hr_150w_bpm"], sd=base.get("steady_hr_150w_sd", 5.0), warn_sd=2.5, red_sd=4.5, warn_pct=10.0, red_pct=20.0, direction="high")
    cevis_days, cevis_vals = _hist("steady_hr_150w_bpm", cevis_hr)
    cevis_slope, cevis_days_red, cevis_trend_warn = _linear_trend_projection(cevis_days, cevis_vals, red_threshold=165.0, lower_is_worse=False)
    cevis_status, cevis_by = _combine_three_layers(cevis_l1, cevis_l2, cevis_trend_warn, cevis_days_red)
    if cevis_days_red is not None and cevis_status != "RED":
        projected_red_days.append(cevis_days_red)
    metrics.append({
        "metric_name": "steady_hr_150w_bpm",
        "indicator": "M7: Aerobic Fitness 150W Bike HR Drift (CEVIS)",
        "current_val": round(cevis_hr, 1),
        "value": round(cevis_hr, 1),
        "baseline_val": float(base["steady_hr_150w_bpm"]),
        "delta_pct": cevis_delta_pct,
        "slope_per_day": cevis_slope,
        "unit": "bpm",
        "status_light": cevis_status,
        "status": cevis_status,
        "decided_by": cevis_by,
        "data_source": data_source,
        "yellow_threshold": 150.0,
        "red_threshold": 165.0,
        "lower_is_worse": False,
        "history_days": cevis_days,
        "history_values": cevis_vals,
        "message": f"CEVIS 150W steady-state HR {cevis_hr:.0f} bpm (drift {cevis_hr - base['steady_hr_150w_bpm']:+.0f} bpm).",
        "action": "Adjust CEVIS interval prescription & verify plasma volume." if cevis_status != "GREEN" else "VO2max / aerobic capacity preserved.",
        "how_to_measure": "Cycle on CEVIS at constant 150W for 10 min; average ECG HR over final 3 minutes.",
        "why_in_space": "Rising HR at fixed 150W workload directly measures aerobic deconditioning and reduced stroke volume.",
    })

    # ------------------------------------------------------------------
    # M8: Heart Muscle Strength GLS (Ultrasound 2 Echocardiography)
    # ------------------------------------------------------------------
    gls_change = float(_safe_float(merged.get("gls_change_pct"), 0.0))
    gls_l1 = "RED" if gls_change <= -15.0 else ("YELLOW" if gls_change <= -10.0 else "GREEN")
    gls_days, gls_vals = _hist("gls_change_pct", gls_change)
    gls_slope, gls_days_red, gls_trend_warn = _linear_trend_projection(gls_days, gls_vals, red_threshold=-15.0, lower_is_worse=True)
    gls_status, gls_by = _combine_three_layers(gls_l1, "GREEN", gls_trend_warn, gls_days_red)
    if gls_days_red is not None and gls_status != "RED":
        projected_red_days.append(gls_days_red)
    metrics.append({
        "metric_name": "gls_change_pct",
        "indicator": "M8: Myocardial Strain GLS (Ultrasound 2)",
        "current_val": round(gls_change, 1),
        "value": round(gls_change, 1),
        "baseline_val": 0.0,
        "delta_pct": round(gls_change, 1),
        "slope_per_day": gls_slope,
        "unit": "% change",
        "status_light": gls_status,
        "status": gls_status,
        "decided_by": gls_by,
        "data_source": data_source,
        "yellow_threshold": -10.0,
        "red_threshold": -15.0,
        "lower_is_worse": True,
        "history_days": gls_days,
        "history_values": gls_vals,
        "message": f"Left-ventricular GLS relative change {gls_change:+.1f}% (Yellow <= -10%, Red <= -15%).",
        "action": "Schedule Flight Surgeon echocardiogram review & suspend HIIT if Red." if gls_status != "GREEN" else "Myocardial contractility preserved.",
        "how_to_measure": "Acquire apical 4-, 3-, and 2-chamber Ultrasound 2 cine loops for automated speckle-tracking GLS.",
        "why_in_space": "Prolonged unloading causes mild cardiac atrophy; GLS detects subclinical systolic dysfunction early.",
    })

    # ------------------------------------------------------------------
    # M9: Internal Jugular Vein Flow & Clot Protocol (Ultrasound 2)
    # ------------------------------------------------------------------
    ijv_flow = str(merged.get("ijv_flow", "forward")).strip().lower()
    ijv_comp = _safe_bool(merged.get("ijv_compressible"), True)
    ijv_thrombus = _safe_bool(merged.get("ijv_thrombus"), False)
    if ijv_thrombus or (not ijv_comp) or ijv_flow == "reversed":
        ijv_status = "RED"
    elif ijv_flow == "stagnant":
        ijv_status = "YELLOW"
    else:
        ijv_status = "GREEN"
    metrics.append({
        "metric_name": "ijv_flow_status",
        "indicator": "M9: IJV Neck Vein Flow & Clot (Ultrasound 2)",
        "current_val": ijv_flow,
        "value": ijv_flow,
        "baseline_val": "forward",
        "unit": "flow",
        "status_light": ijv_status,
        "status": ijv_status,
        "decided_by": "rule",
        "data_source": data_source,
        "message": f"IJV Doppler='{ijv_flow}', compressible={ijv_comp}, thrombus={ijv_thrombus}.",
        "action": "EMERGENCY: Start IJV thrombus anticoagulation & -25 mmHg LBNP; notify CMO/Flight Surgeon." if ijv_status == "RED" else ("Apply -20 mmHg LBNP 30 min/day for venous stasis." if ijv_status == "YELLOW" else "Normal cephalad venous return."),
        "how_to_measure": "Place Ultrasound 2 linear transducer laterally over left/right neck; verify full vein collapse under gentle probe compression and forward color Doppler.",
        "why_in_space": "Headward fluid shift stalls neck vein blood flow (stagnant/reversed), risking spaceflight venous thrombosis and pulmonary embolism.",
    })

    # ------------------------------------------------------------------
    # M10: Plasma Volume %DeltaPV via Dill & Costill (1974) [OSD-569]
    # ------------------------------------------------------------------
    hb = float(_safe_float(merged.get("hb_g_dl"), base["hb_g_dl"]))
    hct = float(_safe_float(merged.get("hct_pct"), base["hct_pct"]))
    pv_delta_pct = dill_costill_delta_pv_pct(base["hb_g_dl"], base["hct_pct"], hb, hct)
    pv_l1 = "RED" if pv_delta_pct <= -20.0 else ("YELLOW" if pv_delta_pct <= -12.0 else "GREEN")
    # Build PV history from Hb/Hct history
    hb_days, hb_vals = _hist("hb_g_dl", hb)
    _, hct_vals = _hist("hct_pct", hct)
    pv_vals = [dill_costill_delta_pv_pct(base["hb_g_dl"], base["hct_pct"], b_i, c_i) for b_i, c_i in zip(hb_vals, hct_vals)]
    pv_slope, pv_days_red, pv_trend_warn = _linear_trend_projection(hb_days, pv_vals, red_threshold=-20.0, lower_is_worse=True)
    pv_status, pv_by = _combine_three_layers(pv_l1, "GREEN", pv_trend_warn, pv_days_red)
    if pv_days_red is not None and pv_status != "RED":
        projected_red_days.append(pv_days_red)
    metrics.append({
        "metric_name": "plasma_volume_delta_pct",
        "indicator": "M10: Plasma Volume %DeltaPV (Dill & Costill / OSD-569)",
        "current_val": pv_delta_pct,
        "value": pv_delta_pct,
        "baseline_val": 0.0,
        "delta_pct": pv_delta_pct,
        "slope_per_day": pv_slope,
        "unit": "%",
        "status_light": pv_status,
        "status": pv_status,
        "decided_by": pv_by,
        "data_source": data_source,
        "yellow_threshold": -12.0,
        "red_threshold": -20.0,
        "lower_is_worse": True,
        "history_days": hb_days,
        "history_values": pv_vals,
        "message": f"%DeltaPV = {pv_delta_pct:+.1f}% (Hb {hb:.1f} g/dL, Hct {hct:.1f}% vs pre-flight {base['hb_g_dl']}/{base['hct_pct']}).",
        "action": "Execute oral electrolyte fluid-loading protocol (1L isotonic saline eq.)." if pv_status != "GREEN" else "Intravascular volume stable.",
        "how_to_measure": "Run finger-stick Bio-Analyzer CBC cartridge for Hemoglobin (Hb) and Hematocrit (Hct); compute Dill & Costill 1974 ratio.",
        "why_in_space": "Microgravity diuresis contracts plasma volume by 10-20%, driving orthostatic intolerance and hemoconcentration.",
    })

    # ------------------------------------------------------------------
    # M11: Serum Blood Chemistry (K+, CRP, Albumin, Protein, Na+, Fibrinogen, PF4) [OSD-575]
    # ------------------------------------------------------------------
    potassium = float(_safe_float(merged.get("potassium_mmol_l"), base["potassium_mmol_l"]))
    sodium = float(_safe_float(merged.get("sodium_mmol_l"), base["sodium_mmol_l"]))
    albumin = float(_safe_float(merged.get("albumin_g_dl"), base["albumin_g_dl"]))
    total_protein = float(_safe_float(merged.get("total_protein_g_dl"), base["total_protein_g_dl"]))
    fibrinogen = float(_safe_float(merged.get("fibrinogen_mg_dl"), base["fibrinogen_mg_dl"]))
    pf4 = float(_safe_float(merged.get("pf4_ng_ml"), base["pf4_ng_ml"]))
    crp_change = float(_safe_float(merged.get("crp_change_pct"), 0.0))

    k_l1 = "RED" if (potassium < 3.0 or potassium > 5.5) else ("YELLOW" if (potassium < 3.5 or potassium > 5.1) else "GREEN")
    crp_l1 = "RED" if (crp_change >= 75.0 or fibrinogen >= 450.0 or pf4 >= 25.0) else ("YELLOW" if (crp_change >= 30.0 or fibrinogen >= 380.0) else "GREEN")
    blood_l1 = _worst_status([k_l1, crp_l1])
    k_days, k_vals = _hist("potassium_mmol_l", potassium)
    k_slope, k_days_red, k_trend_warn = _linear_trend_projection(k_days, k_vals, red_threshold=3.0, lower_is_worse=True)
    blood_status, blood_by = _combine_three_layers(blood_l1, "GREEN", k_trend_warn, k_days_red)
    if k_days_red is not None and blood_status != "RED":
        projected_red_days.append(k_days_red)
    metrics.append({
        "metric_name": "potassium_mmol_l",
        "indicator": "M11: Serum Blood Chemistry (K+, CRP, Clotting / OSD-575)",
        "current_val": round(potassium, 2),
        "value": round(potassium, 2),
        "baseline_val": float(base["potassium_mmol_l"]),
        "delta_pct": round(((potassium - base["potassium_mmol_l"]) / base["potassium_mmol_l"]) * 100.0, 1),
        "slope_per_day": k_slope,
        "unit": "mmol/L (K+)",
        "status_light": blood_status,
        "status": blood_status,
        "decided_by": blood_by,
        "data_source": data_source,
        "yellow_threshold": 3.5,
        "red_threshold": 3.0,
        "lower_is_worse": True,
        "history_days": k_days,
        "history_values": k_vals,
        "message": (
            f"K+ {potassium:.2f} mmol/L, Na+ {sodium:.0f}, Alb {albumin:.1f}, TP {total_protein:.1f}, "
            f"CRP {crp_change:+.0f}%, Fibrinogen {fibrinogen:.0f} mg/dL, PF4 {pf4:.1f} ng/mL."
        ),
        "action": "Supplement oral K+ if <3.5 mmol/L & evaluate prothrombotic/inflammatory panel." if blood_status != "GREEN" else "Electrolytes and clotting panel normal.",
        "how_to_measure": "Insert lithium-heparin venous/capillary cartridge into onboard Bio-Analyzer chemistry panel.",
        "why_in_space": "Hypokalemia triggers dangerous PVCs; elevated CRP, Fibrinogen, and PF4 signal vascular inflammation and clot risk.",
    })

    # ------------------------------------------------------------------
    # Cross-Indicator Clinical Correlations (Enforced per USER.md)
    # ------------------------------------------------------------------
    correlation_alerts: list[str] = []
    if spo2 < 95.0 and resp > 25.0:
        correlation_alerts.append(
            "PE / HYPOXIA CORRELATION (M3+M4->M9): Low SpO2 + Tachypnea (>25/min) — perform immediate bilateral IJV Ultrasound 2 clot check and verify cabin O2/ppCO2."
        )
    if pvc >= 1.5 and potassium < 3.5:
        correlation_alerts.append(
            f"ARRHYTHMIA-ELECTROLYTE CORRELATION (M5+M11): Elevated PVC burden ({pvc:.1f}%) paired with hypokalemia (K+={potassium:.2f} mmol/L) — administer oral KCl and repeat ECG."
        )
    elif pvc >= 1.5:
        correlation_alerts.append(
            f"RHYTHM-ELECTROLYTE CHECK (M5->M11): Elevated PVC burden ({pvc:.1f}%) — verify serum K+ >= 3.5 mmol/L before exercise."
        )
    if (stand_hr >= 20.0 or stand_sbp >= 10.0 or dizzy) and pv_delta_pct <= -12.0:
        correlation_alerts.append(
            f"ORTHOSTATIC-HYPOVOLEMIA CORRELATION (M6+M10): Orthostatic intolerance paired with {pv_delta_pct:.1f}% plasma volume loss — initiate oral salt+fluid loading."
        )

    # ------------------------------------------------------------------
    # Overall Rollup & Closed-Loop Plans
    # ------------------------------------------------------------------
    overall_status = _worst_status([m["status_light"] for m in metrics])
    earliest_red_days: Optional[int] = 0 if overall_status == "RED" else (min(projected_red_days) if projected_red_days else None)

    if overall_status == "RED":
        actions = [
            "STOP all high-intensity CEVIS & heavy E4D resistance workouts immediately.",
            "Perform Ultrasound 2 bilateral IJV compression sweep + 12-lead ECG + serum K+/clotting re-check.",
            "If IJV thrombus/reversed flow: initiate onboard anticoagulation checklist & LBNP -25 mmHg.",
            *correlation_alerts,
        ]
        next_hours = 4
        adj = "Suspend HIIT for 14 days; run daily resting ECG, potassium repletion, and LBNP orthostatic conditioning."
    elif overall_status == "YELLOW":
        actions = [
            "Run 30-min LBNP at -20 mmHg to reduce cephalad venous stasis.",
            "Administer 500-750 mL electrolyte fluid load and repeat Bio-Monitor + Holter check in 12h.",
            *correlation_alerts,
        ]
        next_hours = 12
        adj = "Shift CEVIS to Zone 2 steady aerobic conditioning (4x/week), add LBNP 3x/week, and re-evaluate in 7 days."
    else:
        actions = ["Continue daily Bio-Monitor morning vitals & scheduled CEVIS Zone 2/4 cycling."]
        next_hours = 24
        adj = "Maintain current CEVIS aerobic conditioning + bi-weekly LBNP orthostatic tolerance check."

    summary_note = (
        f"Rest HR {rest_hr:.0f} bpm, BP {sbp:.0f}/{dbp:.0f}, SpO2 {spo2:.1f}%, "
        f"PVC {pvc:.1f}%, IJV '{ijv_flow}', %DeltaPV {pv_delta_pct:+.1f}%."
    )
    if correlation_alerts:
        summary_note += " | " + correlation_alerts[0]

    result = ModuleEvaluationResult(
        module_id="cardiovascular",
        body_part_tag="heart_vascular",
        crew_id=crew_id,
        mission_day=mission_day,
        status_light=overall_status,
        quality_passed=True,
        data_source=data_source,
        summary_note=summary_note,
        metrics=[MetricItem(**m) for m in metrics],
        guidance=CrewGuidance(
            how_to_measure="Wear Bio-Monitor shirt for resting HR/BP/SpO2/Resp; run 24h Holter (MIT-BIH check), CEVIS 150W test, LBNP stand test, and Ultrasound 2 GLS + neck IJV compression.",
            plain_explanation="Microgravity shifts ~2L of fluid toward the head, shrinking plasma volume (%DeltaPV), causing neck vein stasis/clots (IJV), electrolyte-driven PVCs, and orthostatic fainting.",
            action_protocol=actions,
        ),
        short_term_plan=ShortTermPlan(
            next_measurement_in_hours=next_hours,
            immediate_actions=actions,
            urgent_alert=(overall_status == "RED"),
        ),
        long_term_plan=LongTermPlan(
            days_until_red_prediction=earliest_red_days,
            routine_prescription_adjustment=adj,
        ),
        schedule_mutation=ScheduleMutation(
            next_measurement_in_hours=next_hours,
            prescription_adjustment=adj,
            urgent_alert=(overall_status == "RED"),
        ),
    )

    out = result.model_dump()
    out["overall_status"] = out["status_light"]
    out["indicators"] = out["metrics"]
    out["correlation_alerts"] = correlation_alerts
    return out


def to_schema(
    payload: Optional[dict[str, Any]] = None,
    baseline: Optional[dict[str, Any]] = None,
    manual_inputs: Optional[dict[str, Any]] = None,
) -> ModuleEvaluationResult:
    """Evaluate and return a validated Pydantic `ModuleEvaluationResult`."""
    raw = evaluate(payload=payload, baseline=baseline, manual_inputs=manual_inputs)
    return normalize_module_result(raw, module_id="cardiovascular")


# ---------------------------------------------------------------------------
# Plotting Helpers (Plotly & Matplotlib)
# ---------------------------------------------------------------------------

def plot_metric_plotly(result: dict[str, Any], metric_name: str = "rest_hr_bpm") -> Any:
    """Build an interactive Plotly longitudinal chart with Green/Yellow/Red bands."""
    import plotly.graph_objects as go

    metrics = result.get("metrics", [])
    target = next((m for m in metrics if m.get("metric_name") == metric_name), metrics[0] if metrics else None)
    fig = go.Figure()
    if not target:
        fig.update_layout(title="No cardiovascular metrics available")
        return fig

    days = target.get("history_days") or [1, 30, 60, 90, 124]
    vals = target.get("history_values") or [0.0] * len(days)
    fig.add_trace(go.Scatter(x=days, y=vals, mode="lines+markers", name=target.get("indicator", metric_name)))

    y_th = target.get("yellow_threshold")
    r_th = target.get("red_threshold")
    if y_th is not None:
        fig.add_hline(y=y_th, line_dash="dash", line_color="#eab308", annotation_text="Yellow")
    if r_th is not None:
        fig.add_hline(y=r_th, line_dash="dash", line_color="#dc2626", annotation_text="Red")

    fig.update_layout(
        title=f"{target.get('indicator', metric_name)} ({target.get('unit', '')})",
        xaxis_title="Mission Day",
        yaxis_title=target.get("unit", "Value"),
        height=320,
    )
    return fig


def plot_metric_matplotlib(result: dict[str, Any], metric_name: str = "rest_hr_bpm") -> Any:
    """Build a static Matplotlib figure for offline reports or headless export."""
    import matplotlib.pyplot as plt

    metrics = result.get("metrics", [])
    target = next((m for m in metrics if m.get("metric_name") == metric_name), metrics[0] if metrics else None)
    fig, ax = plt.subplots(figsize=(7, 3.5))
    if not target:
        ax.set_title("No cardiovascular metrics available")
        return fig

    days = target.get("history_days") or [1, 30, 60, 90, 124]
    vals = target.get("history_values") or [0.0] * len(days)
    ax.plot(days, vals, marker="o", linewidth=2, label="Measured")
    if target.get("yellow_threshold") is not None:
        ax.axhline(target["yellow_threshold"], color="orange", linestyle="--", label="Yellow")
    if target.get("red_threshold") is not None:
        ax.axhline(target["red_threshold"], color="red", linestyle="--", label="Red")
    ax.set_title(target.get("indicator", metric_name))
    ax.set_xlabel("Mission Day")
    ax.set_ylabel(target.get("unit", ""))
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# CLI Self-Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Z.O.S.M.A. Role 3: Cardiovascular & Aerobic Module Self-Test ===")
    data_info = check_data_files()
    written_files = export_demo_csvs()
    if written_files:
        print(f"Exported/upgraded {len(written_files)} template files in {data_info['local_dir']}:")
        for wf in written_files:
            print(f"  - {wf}")
    else:
        print(f"All expected CSV templates present in {data_info['local_dir']}.")

    if data_info["missing_shared"]:
        print(f"Note: Shared OSDR files not yet in {data_info['shared_dir']}: {data_info['missing_shared']} (using simulated fallback).")

    for scen in ("green", "yellow", "red", "bad_data"):
        pay = demo_payload(scen)
        res_model = to_schema(pay)
        res_dict = evaluate(pay)
        print(
            f"\nScenario [{scen.upper():8s}] -> status={res_model.status_light:6s} | "
            f"raw={res_model.raw_status:17s} | qc_ok={str(res_model.quality_passed):5s} | "
            f"metrics={len(res_model.metrics):2d} | next_h={res_model.short_term_plan.next_measurement_in_hours}h | "
            f"urgent={res_model.short_term_plan.urgent_alert} | days_to_red={res_model.long_term_plan.days_until_red_prediction}"
        )
        if res_dict.get("correlation_alerts"):
            for ca in res_dict["correlation_alerts"]:
                print(f"  Correlation: {ca}")

    # Verify manual override mode
    manual_res = to_schema(demo_payload("green"), manual_inputs={"ijv_flow": "reversed", "ijv_thrombus": True})
    assert manual_res.status_light == "RED" and manual_res.short_term_plan.urgent_alert is True
    print("\nManual override check PASSED (ijv_thrombus=True -> RED, urgent_alert=True).")
