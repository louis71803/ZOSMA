"""Role 3 Helper: Baselines, synthetic datasets, CSV templates, and OSDR loaders.

Kept separate from modules/cardiovascular.py for maintainability while staying
strictly within Role 3's scope (zero impact on other modules or Streamlit UI).
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Optional, Sequence

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "cardiovascular"
SHARED_REAL_DIR = BASE_DIR / "data" / "shared_real"
REAL_SUBDIR = DATA_DIR / "real"

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


def safe_float(val: Any, default: Optional[float] = None) -> Optional[float]:
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


def safe_bool(val: Any, default: bool = False) -> bool:
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


def generate_longitudinal_series(scenario: str = "green", mission_day: int = 124) -> dict[str, dict[str, list[Any]]]:
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
    series = generate_longitudinal_series(scen, mission_day=124)

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
    series = generate_longitudinal_series(scenario=scenario, mission_day=124)
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


def _pick_col(cols_lower: dict[str, str], exact_aliases: Sequence[str], fuzzy_substrings: Sequence[str] = ()) -> Optional[str]:
    """Find matching DataFrame column name using exact aliases first, then fuzzy substrings."""
    for alias in exact_aliases:
        if alias in cols_lower:
            return cols_lower[alias]
    for sub in fuzzy_substrings:
        for col_low, col_orig in cols_lower.items():
            if sub in col_low:
                return col_orig
    return None


def _sample_timepoint_order(sample_name: str) -> tuple[int, int]:
    """Sort Inspiration4 `Sample Name` chronologically: L-92 < L-44 < L-3 < R+1 < R+45 < R+82 < R+194."""
    m = re.search(r"_([LR])([+-]?\d+)", str(sample_name), re.IGNORECASE)
    if not m:
        return (9, 0)
    phase = m.group(1).upper()
    day = int(m.group(2))
    return (0, day) if phase == "L" else (1, abs(day))


def _filter_osdr_by_crew(df: pd.DataFrame, crew_id: Optional[str] = None) -> pd.DataFrame:
    """Filter an OSDR DataFrame to the requested crew_id (supports `Sample Name` prefix like `C002_...`)."""
    if df.empty or not crew_id:
        return df
    cols_lower = {str(c).strip().lower(): str(c) for c in df.columns}
    target = str(crew_id).strip().upper()
    for id_col in ("crew_id", "subject_id", "subject", "id", "participant_id", "sample name", "sample_name"):
        if id_col in cols_lower:
            col_name = cols_lower[id_col]
            series = df[col_name].astype(str).str.strip().str.upper()
            if "sample" in id_col:
                matched = df[series.str.startswith(target + "_") | (series == target)]
            else:
                matched = df[series == target]
            if not matched.empty:
                return matched
    return df


def _select_osdr_row(df: pd.DataFrame, crew_id: Optional[str] = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return `(latest_row, preflight_baseline_means)` from an OSDR CSV for the matching crew_id."""
    if df.empty:
        return {}, {}
    subset = _filter_osdr_by_crew(df, crew_id=crew_id).copy()
    cols_lower = {str(c).strip().lower(): str(c) for c in subset.columns}
    sample_col = cols_lower.get("sample name") or cols_lower.get("sample_name")
    if sample_col:
        subset["_tp_ord"] = subset[sample_col].map(_sample_timepoint_order)
        subset = subset.sort_values("_tp_ord")
        pre_df = subset[subset[sample_col].astype(str).str.contains("_L-", case=False, na=False)]
    else:
        pre_df = pd.DataFrame()

    latest = {str(k).strip().lower(): v for k, v in subset.iloc[-1].to_dict().items() if k != "_tp_ord"}
    pre_means: dict[str, Any] = {}
    if not pre_df.empty:
        for col in pre_df.columns:
            if col == "_tp_ord":
                continue
            nums = pd.to_numeric(pre_df[col], errors="coerce").dropna()
            if not nums.empty:
                pre_means[str(col).strip().lower()] = float(nums.mean())
    return latest, pre_means


def _normalize_osdr_value(raw_val: Optional[float], col_name_lower: str, target_key: str) -> Optional[float]:
    """Normalize NASA OSDR long-column values into cardiovascular module units."""
    if raw_val is None:
        return None
    if target_key == "hb_g_dl":
        if ("gram_per_liter" in col_name_lower or "g_per_l" in col_name_lower) and raw_val > 50.0:
            return round(raw_val / 10.0, 3)
        return raw_val
    if target_key == "hct_pct":
        return raw_val * 100.0 if raw_val <= 1.0 else raw_val
    if target_key == "crp_mg_l":
        if "picogram_per_milliliter" in col_name_lower or "pg_per_ml" in col_name_lower or "pg_ml" in col_name_lower:
            return round(raw_val / 1_000_000.0, 4)
        if "nanogram_per_milliliter" in col_name_lower or "ng_per_ml" in col_name_lower or "ng_ml" in col_name_lower:
            return round(raw_val / 1_000.0, 4)
        if "microgram_per_milliliter" in col_name_lower or "ug_per_ml" in col_name_lower or "ug_ml" in col_name_lower:
            return round(raw_val, 4)
        return raw_val
    if target_key == "fibrinogen_mg_dl":
        if "nanogram_per_milliliter" in col_name_lower or "ng_per_ml" in col_name_lower or "ng_ml" in col_name_lower:
            if raw_val >= 100_000.0:
                return round(raw_val / 10_000.0, 2)
            return round(raw_val, 2)
        if "microgram_per_milliliter" in col_name_lower or "ug_per_ml" in col_name_lower or "ug_ml" in col_name_lower:
            return round(raw_val / 10.0, 2)
        if "milligram_per_milliliter" in col_name_lower or "mg_per_ml" in col_name_lower or "mg_ml" in col_name_lower:
            return round(raw_val * 100.0, 2)
        if "gram_per_liter" in col_name_lower or "g_per_l" in col_name_lower or "g_l" in col_name_lower:
            return round(raw_val * 100.0, 2)
        return raw_val
    if target_key == "pf4_ng_ml":
        if "picogram_per_milliliter" in col_name_lower or "pg_per_ml" in col_name_lower or "pg_ml" in col_name_lower:
            return round(raw_val / 1_000.0, 3)
        if "microgram_per_milliliter" in col_name_lower or "ug_per_ml" in col_name_lower or "ug_ml" in col_name_lower:
            return round(raw_val * 1_000.0, 3)
        return raw_val
    return raw_val


def _parse_long_format_osdr(df: pd.DataFrame, crew_id: Optional[str] = None) -> dict[str, Any]:
    """Support raw OSDR long-format tables (ANALYTE/VALUE/UNITS or Analyte/Concentration/Unit)."""
    updates: dict[str, Any] = {}
    cols_lower = {str(c).strip().lower(): str(c) for c in df.columns}
    analyte_col = _pick_col(cols_lower, ("analyte", "test_name", "biomarker"))
    value_col = _pick_col(cols_lower, ("value", "concentration", "result"))
    unit_col = _pick_col(cols_lower, ("units", "unit"))
    if not analyte_col or not value_col:
        return updates

    subset = df
    if crew_id:
        id_col = _pick_col(cols_lower, ("crew_id", "subject_id", "id", "subject"))
        if id_col:
            matched = df[df[id_col].astype(str).str.strip().str.upper() == str(crew_id).strip().upper()]
            if not matched.empty:
                subset = matched

    analyte_map = {
        "hb_g_dl": ("hemoglobin", "hgb"),
        "hct_pct": ("hematocrit", "hct"),
        "potassium_mmol_l": ("potassium",),
        "sodium_mmol_l": ("sodium",),
        "albumin_g_dl": ("albumin",),
        "total_protein_g_dl": ("total protein", "total_protein"),
        "crp_mg_l": ("crp", "c-reactive protein"),
        "fibrinogen_mg_dl": ("fibrinogen",),
        "pf4_ng_ml": ("pf4", "platelet factor 4", "cxcl4"),
    }
    for _, r in subset.iterrows():
        a_name = str(r.get(analyte_col, "")).strip().lower()
        val = safe_float(r.get(value_col))
        if not a_name or val is None:
            continue
        unit_str = str(r.get(unit_col, "")).strip().lower() if unit_col else ""
        unit_hint = unit_str.replace("/", "_per_").replace(" ", "_")
        for target_key, patterns in analyte_map.items():
            if any(p == a_name or p in a_name for p in patterns):
                norm_val = _normalize_osdr_value(val, unit_hint, target_key)
                if norm_val is not None:
                    updates[target_key] = norm_val
                break
    return updates


def load_shared_osdr_overrides(crew_id: Optional[str] = None) -> tuple[dict[str, Any], bool]:
    """Safely inspect data/shared_real/ for OSD-569 and OSD-575 CSVs. Never crashes."""
    updates: dict[str, Any] = {}
    base_overrides: dict[str, Any] = {}
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
                    long_parsed = _parse_long_format_osdr(df, crew_id=crew_id)
                    for k in ("hb_g_dl", "hct_pct"):
                        if k in long_parsed:
                            updates[k] = long_parsed[k]
                            found_real = True

                    row, pre_means = _select_osdr_row(df, crew_id=crew_id)
                    cols_lower = {k: k for k in row}
                    hb_col = _pick_col(cols_lower, ("hb_g_dl", "hgb", "hemoglobin", "hemoglobin_value_percent"), ("hemoglobin",))
                    if hb_col:
                        val = _normalize_osdr_value(safe_float(row.get(hb_col)), hb_col, "hb_g_dl")
                        if val is not None:
                            updates["hb_g_dl"] = val
                            found_real = True
                        if hb_col in pre_means:
                            pre_val = _normalize_osdr_value(safe_float(pre_means.get(hb_col)), hb_col, "hb_g_dl")
                            if pre_val is not None:
                                base_overrides["hb_g_dl"] = round(pre_val, 2)

                    hct_col = _pick_col(cols_lower, ("hct_pct", "hct", "hematocrit", "hematocrit_value_percent"), ("hematocrit",))
                    if hct_col:
                        val = _normalize_osdr_value(safe_float(row.get(hct_col)), hct_col, "hct_pct")
                        if val is not None:
                            updates["hct_pct"] = val
                            found_real = True
                        if hct_col in pre_means:
                            pre_val = _normalize_osdr_value(safe_float(pre_means.get(hct_col)), hct_col, "hct_pct")
                            if pre_val is not None:
                                base_overrides["hct_pct"] = round(pre_val, 2)
            except Exception:
                pass
            if found_real:
                break

    for fname in ("OSD-575_cmp.csv", "osd575_cmp.csv", "OSD-575_cv_panel.csv", "osd575_cv_panel.csv"):
        path = SHARED_REAL_DIR / fname
        if path.exists():
            try:
                df = pd.read_csv(path)
                if not df.empty:
                    long_parsed = _parse_long_format_osdr(df, crew_id=crew_id)
                    if long_parsed:
                        updates.update(long_parsed)
                        found_real = True

                    row, pre_means = _select_osdr_row(df, crew_id=crew_id)
                    cols_lower = {k: k for k in row}
                    mapping: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
                        "potassium_mmol_l": (
                            ("potassium_mmol_l", "potassium", "k", "k_mmol_l", "potassium_value_millimol_per_liter"),
                            ("potassium",),
                        ),
                        "sodium_mmol_l": (
                            ("sodium_mmol_l", "sodium", "na", "na_mmol_l", "sodium_value_millimol_per_liter"),
                            ("sodium",),
                        ),
                        "albumin_g_dl": (
                            ("albumin_g_dl", "albumin", "albumin_value_gram_per_deciliter"),
                            ("albumin",),
                        ),
                        "total_protein_g_dl": (
                            ("total_protein_g_dl", "total_protein", "total_protein_value_gram_per_deciliter"),
                            ("total_protein",),
                        ),
                        "fibrinogen_mg_dl": (
                            ("fibrinogen_mg_dl", "fibrinogen", "fibrinogen_concentration_nanogram_per_milliliter"),
                            ("fibrinogen",),
                        ),
                        "pf4_ng_ml": (
                            ("pf4_ng_ml", "pf4", "pf4_concentration_nanogram_per_milliliter"),
                            ("pf4",),
                        ),
                        "crp_mg_l": (
                            ("crp_mg_l", "crp", "crp_concentration_picogram_per_milliliter"),
                            ("crp",),
                        ),
                    }
                    for target, (aliases, fuzzy) in mapping.items():
                        matched_col = _pick_col(cols_lower, aliases, fuzzy)
                        if matched_col:
                            norm_val = _normalize_osdr_value(safe_float(row.get(matched_col)), matched_col, target)
                            if norm_val is not None:
                                updates[target] = norm_val
                                found_real = True
                            if matched_col in pre_means:
                                pre_val = _normalize_osdr_value(safe_float(pre_means.get(matched_col)), matched_col, target)
                                if pre_val is not None:
                                    base_overrides[target] = round(pre_val, 3)
            except Exception:
                pass

    if base_overrides:
        updates["_osdr_baseline_overrides"] = base_overrides
    return updates, found_real


def extract_history_from_payload(payload: dict[str, Any], scenario: str, mission_day: int) -> dict[str, dict[str, list[Any]]]:
    """Extract time-series history from CSV records in payload or fall back to synthetic history."""
    fallback = generate_longitudinal_series(scenario=scenario, mission_day=mission_day)
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
                    d = safe_float(r.get("mission_day"), float(idx * 30))
                    days.append(int(d) if d is not None else idx * 30)
            for col in cols:
                vals = []
                valid_days = []
                for d, r in zip(days, records):
                    if isinstance(r, dict):
                        v = safe_float(r.get(col))
                        if v is not None:
                            valid_days.append(d)
                            vals.append(v)
                if len(vals) >= 2:
                    fallback[col] = {"days": valid_days, "values": vals}

    return fallback
