"""Role 2: Musculoskeletal (Bone & Muscle) Domain Module for Team Z.O.S.M.A.

Self-contained stateless evaluator implementing:
- Layer 0: Sensor & Physiological Plausibility QC Gatekeeper (rejects e.g. 999 cm^2 CSA)
- Layer 1: Literature-backed Fixed Clinical / NASA-STD-3001 Thresholds
- Layer 2: Personal Pre-Flight Baseline (+/- 2 SD with 5% SD floor on NTX/CTX)
- Layer 3: 4-Point Trend Slope Projection (upgrades GREEN -> YELLOW if RED imminent)

Covers:
1. E4D Bone Stimulus Index (S_bone) & Loading Rate
2. Isometric Peak Force Strength Retention Index (SRI delta %)
3. Velocity-Based Training (VBT) Squat Velocity Loss (20-30% Green, <20% Yellow, >30% Red)
4. Ultrasound 2 Thigh CSA (4% Yellow / 7% Red) & Calf CSA (5% Yellow / 10% Red)
5. SLAMMD Body Mass (5% Yellow / 10% Red)
6. Bio-Analyzer Bone Markers: NTX, CTX (+50% Red, bone-loss direction only), P1NP
7. Estimated Monthly Bone Loss Rate (anchored to ISS spine ~0.9%/mo, hip ~1.4-1.5%/mo)
8. NASA OSDR OSD-575 Serum Calcium & Alkaline Phosphatase (ALP) baseline validation
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Optional, Union

import numpy as np
import pandas as pd

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ImportError:  # pragma: no cover - optional only if plotly missing
    go = None  # type: ignore[assignment]
    make_subplots = None  # type: ignore[assignment]

from core.schema import ModuleEvaluationResult, normalize_module_result

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "musculoskeletal"
SHARED_REAL_DIR = BASE_DIR / "data" / "shared_real"

EXPECTED_FILES: dict[str, list[str]] = {
    "preflight_baseline.json": [
        "crew_id",
        "iso_peak_force_n",
        "peak_force_n",
        "loading_rate_n_s",
        "csa_thigh_cm2",
        "csa_calf_cm2",
        "body_mass_kg",
        "ntx_nm_bce",
        "ctx_ng_ml",
        "p1np_ug_l",
        "s_bone_target",
        "serum_ca_mg_dl",
        "serum_alp_u_l",
        "preflight_samples",
    ],
    "e4d_sets.csv": [
        "mission_day",
        "exercise",
        "peak_force_n",
        "loading_rate_n_s",
        "reps",
        "velocity_loss_pct",
        "s_bone_index",
        "sensor_qc_ok",
    ],
    "measurements_long.csv": [
        "mission_day",
        "iso_peak_force_n",
        "csa_thigh_cm2",
        "csa_calf_cm2",
        "body_mass_kg",
        "ntx",
        "ctx",
        "p1np",
        "serum_ca_mg_dl",
        "serum_alp_u_l",
        "sensor_qc_ok",
    ],
}

# Physiological plausibility bounds for Layer 0 QC Gatekeeper
PLAUSIBILITY_BOUNDS: dict[str, tuple[float, float, str]] = {
    "peak_force_n": (100.0, 6000.0, "N"),
    "loading_rate_n_s": (100.0, 25000.0, "N/s"),
    "reps": (1.0, 100.0, "reps"),
    "velocity_loss_pct": (0.0, 100.0, "%"),
    "iso_peak_force_n": (150.0, 6000.0, "N"),
    "csa_thigh_cm2": (50.0, 350.0, "cm^2"),
    "csa_calf_cm2": (25.0, 200.0, "cm^2"),
    "body_mass_kg": (35.0, 160.0, "kg"),
    "ntx": (1.0, 200.0, "nM BCE"),
    "ctx": (0.05, 10.0, "ng/mL"),
    "p1np": (5.0, 500.0, "ug/L"),
    "serum_ca_mg_dl": (5.0, 16.0, "mg/dL"),
    "serum_alp_u_l": (10.0, 600.0, "U/L"),
}

# Built-in NASA OSDR OSD-575 reference CMP values (Calcium mg/dL, ALP U/L)
# Used seamlessly when external data/shared_real/OSD-575_cmp.csv is absent.
OSD575_REFERENCE_COHORT: list[dict[str, Any]] = [
    {"subject_id": "OSD575_REF_01", "timepoint": "Preflight", "calcium_mg_dl": 9.3, "alp_u_l": 64.0},
    {"subject_id": "OSD575_REF_02", "timepoint": "Preflight", "calcium_mg_dl": 9.5, "alp_u_l": 71.0},
    {"subject_id": "OSD575_REF_03", "timepoint": "Preflight", "calcium_mg_dl": 9.2, "alp_u_l": 66.0},
    {"subject_id": "OSD575_REF_04", "timepoint": "Postflight", "calcium_mg_dl": 9.7, "alp_u_l": 79.0},
]


def inspect_data_folder() -> dict[str, Any]:
    """Check data/musculoskeletal/ and report present/missing files with expected columns."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    present = sorted(p.name for p in DATA_DIR.iterdir() if p.is_file())
    missing = [fname for fname in EXPECTED_FILES if fname not in present]
    osd_file = _find_osd575_csv()
    return {
        "data_dir": str(DATA_DIR),
        "present_files": present,
        "missing_files": missing,
        "expected_schema": EXPECTED_FILES,
        "osd575_real_csv": str(osd_file) if osd_file else None,
        "is_empty": len(present) == 0,
    }


def _find_osd575_csv() -> Optional[Path]:
    """Locate NASA OSDR OSD-575 CMP CSV in shared_real or musculoskeletal/real if available."""
    candidates = [
        SHARED_REAL_DIR / "OSD-575_cmp.csv",
        SHARED_REAL_DIR / "osd575_cmp.csv",
        DATA_DIR / "real" / "osd575_cmp.csv",
        DATA_DIR / "real" / "OSD-575_cmp.csv",
    ]
    for path in candidates:
        if path.exists() and path.is_file():
            return path
    return None


def demo_baseline() -> dict[str, Any]:
    """Return pre-flight personal baseline with 3 baseline samples for +/- 2 SD rules."""
    return {
        "crew_id": "C002",
        "iso_peak_force_n": 1850.0,
        "peak_force_n": 1850.0,
        "loading_rate_n_s": 3300.0,
        "csa_thigh_cm2": 148.0,
        "csa_calf_cm2": 82.0,
        "body_mass_kg": 74.0,
        "ntx_nm_bce": 14.0,
        "ctx_ng_ml": 0.36,
        "p1np_ug_l": 45.0,
        "s_bone_target": 1.0,
        "serum_ca_mg_dl": 9.4,
        "serum_alp_u_l": 68.0,
        "preflight_samples": {
            "iso_peak_force_n": [1835.0, 1850.0, 1865.0],
            "csa_thigh_cm2": [147.2, 148.0, 148.8],
            "csa_calf_cm2": [81.5, 82.0, 82.5],
            "body_mass_kg": [73.7, 74.0, 74.3],
            "ntx": [13.5, 14.0, 14.5],
            "ctx": [0.35, 0.36, 0.37],
            "p1np": [44.0, 45.0, 46.0],
        },
    }


def demo_payload(scenario: str = "green") -> dict[str, Any]:
    """Generate simulated payload + 4-point history for green, yellow, red, or bad_data."""
    scen = (scenario or "green").strip().lower()

    if scen == "bad_data":
        return {
            "crew_id": "C002",
            "mission_day": 124,
            "data_source": "SIMULATED",
            "sensor_qc_ok": False,
            "peak_force_n": 1810.0,
            "loading_rate_n_s": 3100.0,
            "reps": 8,
            "velocity_loss_pct": 22.0,
            "iso_peak_force_n": 1810.0,
            "csa_thigh_cm2": 146.0,
            "csa_calf_cm2": 999.0,  # Implausible Ultrasound 2 reading rejected by Layer 0 QC
            "body_mass_kg": 73.2,
            "ntx": 15.0,
            "ctx": 0.39,
            "p1np": 44.0,
            "serum_ca_mg_dl": 9.5,
            "serum_alp_u_l": 70.0,
        }

    if scen == "yellow":
        return {
            "crew_id": "C002",
            "mission_day": 124,
            "data_source": "SIMULATED",
            "sensor_qc_ok": True,
            "peak_force_n": 1630.0,
            "loading_rate_n_s": 2550.0,
            "reps": 8,
            "velocity_loss_pct": 16.5,  # < 20% under-stimulus (YELLOW)
            "iso_peak_force_n": 1645.0,  # -11.1% strength loss (YELLOW >= 10%)
            "csa_thigh_cm2": 140.5,      # -5.1% loss (YELLOW >= 4%)
            "csa_calf_cm2": 77.2,       # -5.9% loss (YELLOW >= 5%)
            "body_mass_kg": 69.8,       # -5.7% loss (YELLOW >= 5%)
            "ntx": 18.6,                # +32.9% elevation (YELLOW)
            "ctx": 0.49,                # +36.1% elevation (YELLOW)
            "p1np": 37.5,               # -16.7% suppression (YELLOW)
            "serum_ca_mg_dl": 10.2,
            "serum_alp_u_l": 92.0,
            "history_days": [30, 60, 90, 124],
            "history_series": {
                "csa_thigh_cm2": [146.5, 144.8, 142.6, 140.5],
                "csa_calf_cm2": [81.0, 79.8, 78.5, 77.2],
                "iso_peak_force_n": [1800.0, 1750.0, 1700.0, 1645.0],
                "body_mass_kg": [73.0, 72.0, 70.9, 69.8],
                "ntx": [15.0, 16.2, 17.4, 18.6],
                "ctx": [0.38, 0.42, 0.45, 0.49],
                "p1np": [43.5, 41.8, 39.6, 37.5],
            },
        }

    if scen == "red":
        return {
            "crew_id": "C002",
            "mission_day": 124,
            "data_source": "SIMULATED",
            "sensor_qc_ok": True,
            "peak_force_n": 1310.0,
            "loading_rate_n_s": 1650.0,
            "reps": 5,
            "velocity_loss_pct": 33.5,  # > 30% Red fatigue limit
            "iso_peak_force_n": 1440.0,  # -22.2% strength loss (RED >= 20%)
            "csa_thigh_cm2": 136.0,     # -8.1% loss (RED >= 7%)
            "csa_calf_cm2": 73.0,      # -11.0% loss (RED >= 10%)
            "body_mass_kg": 66.0,      # -10.8% loss (RED >= 10%)
            "ntx": 22.8,               # +62.9% elevation (RED >= +50%)
            "ctx": 0.58,               # +61.1% elevation (RED >= +50%)
            "p1np": 32.5,              # -27.8% suppression (RED >= 25% drop)
            "serum_ca_mg_dl": 10.7,    # > 10.5 mg/dL hypercalcemia warning
            "serum_alp_u_l": 128.0,
            "history_days": [30, 60, 90, 124],
            "history_series": {
                "csa_thigh_cm2": [145.5, 142.2, 139.0, 136.0],
                "csa_calf_cm2": [80.2, 77.9, 75.3, 73.0],
                "iso_peak_force_n": [1760.0, 1650.0, 1545.0, 1440.0],
                "body_mass_kg": [72.2, 70.1, 68.0, 66.0],
                "ntx": [15.8, 18.0, 20.5, 22.8],
                "ctx": [0.40, 0.46, 0.52, 0.58],
                "p1np": [42.0, 38.8, 35.6, 32.5],
            },
        }

    # Default nominal GREEN scenario
    return {
        "crew_id": "C002",
        "mission_day": 124,
        "data_source": "SIMULATED",
        "sensor_qc_ok": True,
        "peak_force_n": 1825.0,
        "loading_rate_n_s": 3250.0,
        "reps": 8,
        "velocity_loss_pct": 24.5,  # Optimal 20-30% VBT mechanical/metabolic stimulus window
        "iso_peak_force_n": 1815.0,  # -1.9%
        "csa_thigh_cm2": 146.4,      # -1.1%
        "csa_calf_cm2": 80.9,       # -1.3%
        "body_mass_kg": 73.2,       # -1.1%
        "ntx": 14.8,                # +5.7%
        "ctx": 0.38,                # +5.6%
        "p1np": 44.5,               # -1.1%
        "serum_ca_mg_dl": 9.5,
        "serum_alp_u_l": 70.0,
        "history_days": [30, 60, 90, 124],
        "history_series": {
            "csa_thigh_cm2": [147.6, 147.2, 146.8, 146.4],
            "csa_calf_cm2": [81.7, 81.4, 81.1, 80.9],
            "iso_peak_force_n": [1840.0, 1832.0, 1822.0, 1815.0],
            "body_mass_kg": [73.8, 73.6, 73.4, 73.2],
            "ntx": [14.2, 14.4, 14.6, 14.8],
            "ctx": [0.36, 0.37, 0.37, 0.38],
            "p1np": [45.0, 44.8, 44.6, 44.5],
        },
    }


def _compute_s_bone(
    peak_force_n: float,
    loading_rate_n_s: float,
    reps: float,
    baseline_force_n: float,
    baseline_loading_rate_n_s: float,
) -> float:
    """Compute E4D Bone Stimulus Index (S_bone) from force, loading rate, and repetitions."""
    force_ratio = max(peak_force_n, 0.0) / max(baseline_force_n, 1.0)
    rate_ratio = (max(loading_rate_n_s, 1.0) / max(baseline_loading_rate_n_s, 1.0)) ** 0.25
    rep_factor = 1.0 + 0.15 * math.log(max(reps, 1.0) / 8.0)
    return round(force_ratio * rate_ratio * max(rep_factor, 0.5), 3)


def export_demo_csvs() -> list[str]:
    """Generate editable CSV/JSON starter templates inside data/musculoskeletal/."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    base = demo_baseline()
    baseline_path = DATA_DIR / "preflight_baseline.json"
    with baseline_path.open("w", encoding="utf-8") as fh:
        json.dump(base, fh, indent=2)
    written.append(str(baseline_path))

    e4d_rows = [
        {"mission_day": 30, "exercise": "Squat", "peak_force_n": 1840.0, "loading_rate_n_s": 3300.0, "reps": 8, "velocity_loss_pct": 23.0, "sensor_qc_ok": True},
        {"mission_day": 60, "exercise": "Squat", "peak_force_n": 1835.0, "loading_rate_n_s": 3280.0, "reps": 8, "velocity_loss_pct": 23.8, "sensor_qc_ok": True},
        {"mission_day": 90, "exercise": "Squat", "peak_force_n": 1830.0, "loading_rate_n_s": 3260.0, "reps": 8, "velocity_loss_pct": 24.2, "sensor_qc_ok": True},
        {"mission_day": 124, "exercise": "Squat", "peak_force_n": 1825.0, "loading_rate_n_s": 3250.0, "reps": 8, "velocity_loss_pct": 24.5, "sensor_qc_ok": True},
    ]
    for row in e4d_rows:
        row["s_bone_index"] = _compute_s_bone(
            row["peak_force_n"],
            row["loading_rate_n_s"],
            row["reps"],
            float(base["peak_force_n"]),
            float(base["loading_rate_n_s"]),
        )
    e4d_path = DATA_DIR / "e4d_sets.csv"
    pd.DataFrame(e4d_rows).to_csv(e4d_path, index=False)
    written.append(str(e4d_path))

    meas_df = pd.DataFrame(
        [
            {"mission_day": 30, "iso_peak_force_n": 1840.0, "csa_thigh_cm2": 147.6, "csa_calf_cm2": 81.7, "body_mass_kg": 73.8, "ntx": 14.2, "ctx": 0.36, "p1np": 45.0, "serum_ca_mg_dl": 9.4, "serum_alp_u_l": 68.0, "sensor_qc_ok": True},
            {"mission_day": 60, "iso_peak_force_n": 1832.0, "csa_thigh_cm2": 147.2, "csa_calf_cm2": 81.4, "body_mass_kg": 73.6, "ntx": 14.4, "ctx": 0.37, "p1np": 44.8, "serum_ca_mg_dl": 9.4, "serum_alp_u_l": 69.0, "sensor_qc_ok": True},
            {"mission_day": 90, "iso_peak_force_n": 1822.0, "csa_thigh_cm2": 146.8, "csa_calf_cm2": 81.1, "body_mass_kg": 73.4, "ntx": 14.6, "ctx": 0.37, "p1np": 44.6, "serum_ca_mg_dl": 9.5, "serum_alp_u_l": 69.5, "sensor_qc_ok": True},
            {"mission_day": 124, "iso_peak_force_n": 1815.0, "csa_thigh_cm2": 146.4, "csa_calf_cm2": 80.9, "body_mass_kg": 73.2, "ntx": 14.8, "ctx": 0.38, "p1np": 44.5, "serum_ca_mg_dl": 9.5, "serum_alp_u_l": 70.0, "sensor_qc_ok": True},
        ]
    )
    meas_path = DATA_DIR / "measurements_long.csv"
    meas_df.to_csv(meas_path, index=False)
    written.append(str(meas_path))
    return written


def _load_osd575_summary() -> dict[str, Any]:
    """Load real NASA OSDR OSD-575 serum Calcium & ALP baseline if available; else built-in reference."""
    csv_path = _find_osd575_csv()
    if csv_path is not None:
        try:
            df = pd.read_csv(csv_path)
            cols_lower = {c.lower(): c for c in df.columns}
            ca_col = next((cols_lower[c] for c in cols_lower if "calc" in c or c == "ca"), None)
            alp_col = next((cols_lower[c] for c in cols_lower if "alp" in c or "alkaline" in c), None)
            ca_vals = pd.to_numeric(df[ca_col], errors="coerce").dropna().tolist() if ca_col else []
            alp_vals = pd.to_numeric(df[alp_col], errors="coerce").dropna().tolist() if alp_col else []
            if ca_vals or alp_vals:
                return {
                    "data_source": "REAL",
                    "source_file": str(csv_path),
                    "n_records": len(df),
                    "ca_mean": round(float(np.mean(ca_vals)), 2) if ca_vals else 9.4,
                    "alp_mean": round(float(np.mean(alp_vals)), 1) if alp_vals else 68.0,
                    "ca_series": [round(float(x), 2) for x in ca_vals],
                    "alp_series": [round(float(x), 1) for x in alp_vals],
                }
        except Exception:  # noqa: BLE001
            pass

    ca_ref = [r["calcium_mg_dl"] for r in OSD575_REFERENCE_COHORT]
    alp_ref = [r["alp_u_l"] for r in OSD575_REFERENCE_COHORT]
    return {
        "data_source": "SIMULATED",
        "source_file": "built-in OSD-575 reference cohort",
        "n_records": len(OSD575_REFERENCE_COHORT),
        "ca_mean": round(float(np.mean(ca_ref)), 2),
        "alp_mean": round(float(np.mean(alp_ref)), 1),
        "ca_series": ca_ref,
        "alp_series": alp_ref,
    }


def _worst(statuses: list[str]) -> str:
    order = {"GREEN": 0, "YELLOW": 1, "RED": 2}
    return max(statuses, key=lambda s: order.get(s, 0)) if statuses else "GREEN"


def _safe_float(val: Any) -> Optional[float]:
    if val is None or isinstance(val, bool):
        return None
    try:
        num = float(val)
        return None if (math.isnan(num) or math.isinf(num)) else num
    except (TypeError, ValueError):
        return None


def _run_layer0_qc(pay: dict[str, Any]) -> tuple[bool, list[str]]:
    """Layer 0 QC Gatekeeper: reject missing flags or physiologically implausible sensor values."""
    issues: list[str] = []

    if pay.get("sensor_qc_ok") is False:
        issues.append("Device sensor_qc_ok flag reported False (probe contact / load-cell tare failure).")

    for field, (low, high, unit) in PLAUSIBILITY_BOUNDS.items():
        if field not in pay:
            continue
        raw = pay.get(field)
        if raw is None:
            if field in {"peak_force_n", "csa_thigh_cm2", "csa_calf_cm2", "body_mass_kg", "iso_peak_force_n"}:
                issues.append(f"{field} is null/missing.")
            continue
        val = _safe_float(raw)
        if val is None:
            issues.append(f"{field} is non-numeric or NaN/Inf ({raw!r}).")
            continue
        if val < low or val > high:
            issues.append(
                f"{field}={val:.2f} {unit} outside plausible range [{low}, {high}] {unit}."
            )

    return len(issues) == 0, issues


def _extract_history(
    pay: dict[str, Any],
    metric_key: str,
    current_val: float,
    baseline_val: float,
    mission_day: int,
) -> tuple[list[int], list[float]]:
    """Extract 4-point history from CSV rows, payload history_series, or linear interpolation."""
    csv_rows = pay.get("csv_measurements_long")
    if metric_key in {"peak_force_n", "loading_rate_n_s", "velocity_loss_pct"}:
        csv_rows = pay.get("csv_e4d_sets")

    if isinstance(csv_rows, list) and len(csv_rows) >= 2:
        pts: list[tuple[int, float]] = []
        for row in csv_rows:
            if not isinstance(row, dict):
                continue
            d = _safe_float(row.get("mission_day"))
            v = _safe_float(row.get(metric_key))
            if d is not None and v is not None:
                pts.append((int(d), float(v)))
        if len(pts) >= 2:
            pts = pts[-4:]
            days = [p[0] for p in pts]
            vals = [round(p[1], 3) for p in pts]
            # Ensure latest UI/override value updates the final point
            if days[-1] == mission_day:
                vals[-1] = round(current_val, 3)
            else:
                days.append(mission_day)
                vals.append(round(current_val, 3))
                days = days[-4:]
                vals = vals[-4:]
            return days, vals

    h_days = pay.get("history_days")
    h_series = pay.get("history_series", {})
    if isinstance(h_days, list) and isinstance(h_series, dict) and isinstance(h_series.get(metric_key), list):
        vals = [round(float(x), 3) for x in h_series[metric_key][-4:]]
        days = [int(d) for d in h_days[-len(vals):]]
        if vals:
            vals[-1] = round(current_val, 3)
            if days:
                days[-1] = mission_day
            return days, vals

    # Smooth 4-point fallback trajectory from baseline -> current_val
    days = [max(1, int(mission_day * f)) for f in (0.25, 0.50, 0.75)] + [mission_day]
    vals = [
        round(baseline_val + (current_val - baseline_val) * frac, 3)
        for frac in (0.25, 0.50, 0.75, 1.0)
    ]
    return days, vals


def _compute_slope(days: list[int], values: list[float]) -> float:
    """Compute linear regression slope per mission day over recent points."""
    if len(days) < 2 or len(values) < 2 or len(set(days)) < 2:
        return 0.0
    x = np.asarray(days, dtype=float)
    y = np.asarray(values, dtype=float)
    slope = float(np.polyfit(x, y, 1)[0])
    return round(slope, 5)


def _baseline_sd_with_floor(
    baseline: dict[str, Any],
    sample_key: str,
    baseline_val: float,
    min_floor_pct: float = 0.03,
) -> float:
    """Compute personal baseline SD with optional minimum percentage floor (5% for NTX/CTX)."""
    samples = (baseline.get("preflight_samples") or {}).get(sample_key)
    sample_sd = 0.0
    if isinstance(samples, list) and len(samples) >= 2:
        arr = np.asarray([float(v) for v in samples], dtype=float)
        sample_sd = float(np.std(arr, ddof=1))
    return max(sample_sd, baseline_val * min_floor_pct)


def _evaluate_loss_metric(
    *,
    metric_name: str,
    current_val: float,
    baseline_val: float,
    yellow_loss_pct: float,
    red_loss_pct: float,
    unit: str,
    mission_day: int,
    data_source: str,
    pay: dict[str, Any],
    base: dict[str, Any],
    sample_key: str,
    horizon_days: int = 7,
    action_nominal: str,
    action_abnormal: str,
) -> tuple[dict[str, Any], Optional[int]]:
    """3-Layer evaluation for metrics where loss below baseline is worse."""
    delta_pct = ((current_val - baseline_val) / max(baseline_val, 1e-6)) * 100.0
    loss_pct = -delta_pct
    days, vals = _extract_history(pay, metric_name, current_val, baseline_val, mission_day)
    slope = _compute_slope(days, vals)

    yellow_thresh = round(baseline_val * (1.0 - yellow_loss_pct / 100.0), 2)
    red_thresh = round(baseline_val * (1.0 - red_loss_pct / 100.0), 2)

    # Layer 1: Fixed Clinical Thresholds
    l1_status = "GREEN"
    if loss_pct >= red_loss_pct:
        l1_status = "RED"
    elif loss_pct >= yellow_loss_pct:
        l1_status = "YELLOW"

    # Layer 2: Personal Baseline -2 SD
    sd = _baseline_sd_with_floor(base, sample_key, baseline_val, min_floor_pct=0.015)
    l2_status = "YELLOW" if current_val <= (baseline_val - 2.0 * sd) and l1_status == "GREEN" else "GREEN"

    # Layer 3: Trend Projection (flag GREEN -> YELLOW if projected to cross RED within horizon)
    l3_status = "GREEN"
    days_to_red: Optional[int] = 0 if l1_status == "RED" else None
    if slope < -1e-5 and current_val > red_thresh:
        est_days = max(1, int(math.ceil((current_val - red_thresh) / abs(slope))))
        days_to_red = est_days
        if est_days <= horizon_days and l1_status == "GREEN" and l2_status == "GREEN":
            l3_status = "YELLOW"

    final_status = _worst([l1_status, l2_status, l3_status])
    if l1_status != "GREEN":
        decided_by = "fixed_threshold"
    elif l2_status != "GREEN":
        decided_by = "baseline"
    elif l3_status != "GREEN":
        decided_by = "trend"
    else:
        decided_by = "baseline"

    item = {
        "metric_name": metric_name,
        "current_val": round(current_val, 2),
        "baseline_val": round(baseline_val, 2),
        "delta_pct": round(delta_pct, 2),
        "slope_per_day": slope,
        "unit": unit,
        "status_light": final_status,
        "decided_by": decided_by,
        "data_source": data_source,
        "yellow_threshold": yellow_thresh,
        "red_threshold": red_thresh,
        "lower_is_worse": True,
        "history_days": days,
        "history_values": vals,
        "message": (
            f"{metric_name}: {current_val:.1f} {unit} ({delta_pct:+.1f}% vs baseline {baseline_val:.1f}; "
            f"Yellow -{yellow_loss_pct:.0f}%, Red -{red_loss_pct:.0f}%)."
        ),
        "action": action_abnormal if final_status != "GREEN" else action_nominal,
    }
    return item, days_to_red


def _evaluate_resorption_marker(
    *,
    metric_name: str,
    payload_key: str,
    current_val: float,
    baseline_val: float,
    unit: str,
    mission_day: int,
    data_source: str,
    pay: dict[str, Any],
    base: dict[str, Any],
    horizon_days: int = 14,
) -> tuple[dict[str, Any], Optional[int]]:
    """Evaluate NTX/CTX only in the bone-loss (increase) direction with 5% SD floor & +50% Red."""
    delta_pct = ((current_val - baseline_val) / max(baseline_val, 1e-6)) * 100.0
    days, vals = _extract_history(pay, payload_key, current_val, baseline_val, mission_day)
    slope = _compute_slope(days, vals)

    # 5% minimum SD floor for +2 SD personal baseline rule (bone-loss direction only)
    sd_floor = _baseline_sd_with_floor(base, payload_key, baseline_val, min_floor_pct=0.05)
    two_sd_upper = baseline_val + 2.0 * sd_floor
    yellow_pct_val = baseline_val * 1.25
    yellow_thresh = round(min(two_sd_upper, yellow_pct_val), 3)
    red_thresh = round(baseline_val * 1.50, 3)

    # Layer 1: Fixed +50% Red / +25% Yellow
    l1_status = "GREEN"
    if delta_pct >= 50.0:
        l1_status = "RED"
    elif delta_pct >= 25.0:
        l1_status = "YELLOW"

    # Layer 2: Personal +2 SD (with 5% SD floor) — flagged ONLY on elevation
    l2_status = "YELLOW" if current_val >= two_sd_upper and l1_status == "GREEN" else "GREEN"

    # Layer 3: Trend projection
    l3_status = "GREEN"
    days_to_red: Optional[int] = 0 if l1_status == "RED" else None
    if slope > 1e-5 and current_val < red_thresh:
        est_days = max(1, int(math.ceil((red_thresh - current_val) / slope)))
        days_to_red = est_days
        if est_days <= horizon_days and l1_status == "GREEN" and l2_status == "GREEN":
            l3_status = "YELLOW"

    final_status = _worst([l1_status, l2_status, l3_status])
    if l1_status != "GREEN":
        decided_by = "fixed_threshold"
    elif l2_status != "GREEN":
        decided_by = "baseline"
    elif l3_status != "GREEN":
        decided_by = "trend"
    else:
        decided_by = "baseline"

    item = {
        "metric_name": metric_name,
        "current_val": round(current_val, 3),
        "baseline_val": round(baseline_val, 3),
        "delta_pct": round(delta_pct, 1),
        "slope_per_day": slope,
        "unit": unit,
        "status_light": final_status,
        "decided_by": decided_by,
        "data_source": data_source,
        "yellow_threshold": yellow_thresh,
        "red_threshold": red_thresh,
        "lower_is_worse": False,
        "history_days": days,
        "history_values": vals,
        "message": (
            f"{payload_key.upper()} bone resorption {current_val:.2f} {unit} ({delta_pct:+.1f}% vs baseline; "
            f"+2 SD floor={two_sd_upper:.2f}, Red >= +50%)."
        ),
        "action": (
            "Increase axial E4D resistance load +5%, confirm Vitamin D3 (800-1000 IU) & Ca intake."
            if final_status != "GREEN"
            else "Bone resorption marker within nominal limits."
        ),
    }
    return item, days_to_red


def evaluate(
    payload: Optional[dict[str, Any]] = None,
    baseline: Optional[dict[str, Any]] = None,
    manual_overrides: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Stateless Layer 0 + 3-Layer Musculoskeletal evaluation returning standardized dict."""
    base = {**demo_baseline(), **(baseline or {})}
    pay = {**demo_payload("green"), **(payload or {})}
    if manual_overrides:
        for k, v in manual_overrides.items():
            if v is not None:
                pay[k] = v

    crew_id = str(pay.get("crew_id", base.get("crew_id", "C002")))
    mission_day = int(pay.get("mission_day", 124))
    data_source = str(pay.get("data_source", "SIMULATED")).upper()

    # ---------------- LAYER 0: QC GATEKEEPER ----------------
    qc_passed, qc_issues = _run_layer0_qc(pay)
    if not qc_passed:
        bad_calf = _safe_float(pay.get("csa_calf_cm2"))
        qc_val = bad_calf if bad_calf is not None else 0.0
        qc_unit = "cm^2" if bad_calf is not None else "N"
        return {
            "module_id": "musculoskeletal",
            "body_part_tag": "lower_limb_bone_muscle",
            "crew_id": crew_id,
            "mission_day": mission_day,
            "status_light": "INSUFFICIENT_DATA",
            "quality_passed": False,
            "data_source": data_source,
            "summary_note": f"Layer 0 QC Gatekeeper rejected telemetry: {' '.join(qc_issues)}",
            "metrics": [
                {
                    "metric_name": "musculoskeletal_qc_gatekeeper",
                    "current_val": qc_val,
                    "baseline_val": float(base["csa_calf_cm2"]),
                    "unit": qc_unit,
                    "status_light": "INSUFFICIENT_DATA",
                    "decided_by": "quality_check",
                    "data_source": data_source,
                    "message": " ".join(qc_issues),
                    "action": "Re-zero E4D load cell / verify Ultrasound 2 landmark & probe gel; repeat scan immediately.",
                }
            ],
            "guidance": {
                "how_to_measure": (
                    "1) Zero the E4D load cell with no cable tension. 2) Apply acoustic gel to Ultrasound 2 linear probe "
                    "at the pre-marked 30% proximal calf & 50% mid-thigh skin tattoos. 3) Verify readings sit inside "
                    "physiological bounds (Calf CSA 25-200 cm^2, Thigh CSA 50-350 cm^2) before logging."
                ),
                "plain_explanation": (
                    "Corrupted or implausible measurements (such as a 999 cm^2 ultrasound artifact or missing force cell) "
                    "must be blocked before decision logic runs so false alarms or missed bone/muscle loss do not occur."
                ),
                "action_protocol": [
                    "Check E4D cable pin lock and Ultrasound 2 probe contact.",
                    "Re-measure immediately (next_measurement_in_hours = 0) before starting heavy sets.",
                ],
            },
            "short_term_plan": {
                "next_measurement_in_hours": 0,
                "immediate_actions": [
                    "Sensor QC rejected implausible value(s). Recalibrate and repeat measurement immediately."
                ],
                "urgent_alert": False,
            },
            "long_term_plan": {
                "days_until_red_prediction": None,
                "routine_prescription_adjustment": "Verify E4D & Ultrasound 2 calibration checklist prior to each session.",
            },
            "schedule_mutation": {
                "next_measurement_in_hours": 0,
                "prescription_adjustment": "Hold automated load progression until valid QC measurement is logged.",
                "urgent_alert": False,
            },
        }

    # ---------------- LAYER 1-3: DOMAIN INDICATORS ----------------
    peak_force = float(pay.get("peak_force_n", base["peak_force_n"]))
    loading_rate = float(pay.get("loading_rate_n_s", base["loading_rate_n_s"]))
    reps = float(pay.get("reps", 8))
    s_bone = float(
        pay["s_bone"]
        if pay.get("s_bone") is not None
        else _compute_s_bone(
            peak_force,
            loading_rate,
            reps,
            float(base["peak_force_n"]),
            float(base["loading_rate_n_s"]),
        )
    )
    if s_bone < 0.75:
        s_bone_status = "RED"
    elif s_bone < 0.90:
        s_bone_status = "YELLOW"
    else:
        s_bone_status = "GREEN"

    # 1. E4D Bone Stimulus Index (S_bone)
    s_bone_metric = {
        "metric_name": "e4d_s_bone_index",
        "current_val": round(s_bone, 3),
        "baseline_val": float(base["s_bone_target"]),
        "delta_pct": round((s_bone - float(base["s_bone_target"])) * 100.0, 1),
        "slope_per_day": 0.0,
        "unit": "index",
        "status_light": s_bone_status,
        "decided_by": "fixed_threshold",
        "data_source": data_source,
        "yellow_threshold": 0.90,
        "red_threshold": 0.75,
        "lower_is_worse": True,
        "message": (
            f"E4D Bone Stimulus Index S_bone={s_bone:.2f} (force={peak_force:.0f} N, "
            f"loading rate={loading_rate:.0f} N/s, reps={int(reps)})."
        ),
        "action": (
            "Increase E4D squat/deadlift load +5% and execute faster concentric drive to raise loading rate."
            if s_bone_status != "GREEN"
            else "Osteogenic bone stimulus meets NASA target (>= 0.90)."
        ),
    }

    # 2. Isometric Peak Force SRI
    iso_force = float(pay.get("iso_peak_force_n", base["iso_peak_force_n"]))
    iso_metric, iso_dtr = _evaluate_loss_metric(
        metric_name="iso_peak_force_n",
        current_val=iso_force,
        baseline_val=float(base["iso_peak_force_n"]),
        yellow_loss_pct=10.0,
        red_loss_pct=20.0,
        unit="N",
        mission_day=mission_day,
        data_source=data_source,
        pay=pay,
        base=base,
        sample_key="iso_peak_force_n",
        horizon_days=7,
        action_nominal="Strength retention index within normal operational envelope.",
        action_abnormal="Prioritize heavy E4D isometric mid-thigh pulls & squats (+5% load if form clean).",
    )

    # 3. VBT Squat Velocity Loss (20-30% Green, <20% Yellow under-stimulus, >30% Red fatigue)
    vbt_loss = float(pay.get("velocity_loss_pct", 24.5))
    if vbt_loss > 30.0:
        vbt_status = "RED"
        vbt_msg = f"E4D VBT squat velocity loss {vbt_loss:.1f}% EXCEEDS 30% Red fatigue limit."
        vbt_act = "STOP fatigued set immediately, rest 3 min, and drop working load 10%."
    elif vbt_loss < 20.0:
        vbt_status = "YELLOW"
        vbt_msg = f"E4D VBT velocity loss {vbt_loss:.1f}% < 20% optimal zone (under-stimulus)."
        vbt_act = "Increase E4D squat/deadlift load +5% or add 1-2 reps to reach 20-30% velocity loss."
    else:
        vbt_status = "GREEN"
        vbt_msg = f"E4D VBT velocity loss {vbt_loss:.1f}% inside optimal 20-30% osteogenic/hypertrophy window."
        vbt_act = "Maintain current E4D load and intra-set velocity target."

    vbt_metric = {
        "metric_name": "velocity_loss_pct",
        "current_val": round(vbt_loss, 1),
        "baseline_val": 25.0,
        "delta_pct": round(vbt_loss - 25.0, 1),
        "slope_per_day": 0.0,
        "unit": "%",
        "status_light": vbt_status,
        "decided_by": "fixed_threshold",
        "data_source": data_source,
        "yellow_threshold": 20.0,
        "red_threshold": 30.0,
        "lower_is_worse": False,
        "message": vbt_msg,
        "action": vbt_act,
    }

    # 4. Ultrasound 2 Thigh CSA (4% Yellow / 7% Red)
    csa_thigh = float(pay.get("csa_thigh_cm2", base["csa_thigh_cm2"]))
    thigh_metric, thigh_dtr = _evaluate_loss_metric(
        metric_name="csa_thigh_cm2",
        current_val=csa_thigh,
        baseline_val=float(base["csa_thigh_cm2"]),
        yellow_loss_pct=4.0,
        red_loss_pct=7.0,
        unit="cm^2",
        mission_day=mission_day,
        data_source=data_source,
        pay=pay,
        base=base,
        sample_key="csa_thigh_cm2",
        horizon_days=7,
        action_nominal="Thigh quadriceps/hamstring cross-sectional area preserved.",
        action_abnormal="Add +5% E4D squat/deadlift load & extra posterior-chain set every 48h.",
    )

    # 5. Ultrasound 2 Calf CSA (5% Yellow / 10% Red)
    csa_calf = float(pay.get("csa_calf_cm2", base["csa_calf_cm2"]))
    calf_metric, calf_dtr = _evaluate_loss_metric(
        metric_name="csa_calf_cm2",
        current_val=csa_calf,
        baseline_val=float(base["csa_calf_cm2"]),
        yellow_loss_pct=5.0,
        red_loss_pct=10.0,
        unit="cm^2",
        mission_day=mission_day,
        data_source=data_source,
        pay=pay,
        base=base,
        sample_key="csa_calf_cm2",
        horizon_days=7,
        action_nominal="Calf soleus/gastrocnemius CSA preserved.",
        action_abnormal="Add unilateral heavy E4D calf raises (4x10) & eccentric lowering.",
    )

    # 6. SLAMMD Body Mass (5% Yellow / 10% Red)
    body_mass = float(pay.get("body_mass_kg", base["body_mass_kg"]))
    mass_metric, mass_dtr = _evaluate_loss_metric(
        metric_name="body_mass_kg",
        current_val=body_mass,
        baseline_val=float(base["body_mass_kg"]),
        yellow_loss_pct=5.0,
        red_loss_pct=10.0,
        unit="kg",
        mission_day=mission_day,
        data_source=data_source,
        pay=pay,
        base=base,
        sample_key="body_mass_kg",
        horizon_days=7,
        action_nominal="SLAMMD body mass & caloric balance on target.",
        action_abnormal="Add +350 kcal/day protein-enriched ration (>= 1.6 g/kg/day protein).",
    )

    # 7 & 8. Bio-Analyzer Bone Resorption: NTX & CTX (bone-loss direction only, 5% SD floor, +50% Red)
    ntx_val = float(pay.get("ntx", base["ntx_nm_bce"]))
    ntx_metric, ntx_dtr = _evaluate_resorption_marker(
        metric_name="ntx_bone_resorption",
        payload_key="ntx",
        current_val=ntx_val,
        baseline_val=float(base["ntx_nm_bce"]),
        unit="nM BCE",
        mission_day=mission_day,
        data_source=data_source,
        pay=pay,
        base=base,
        horizon_days=14,
    )

    ctx_val = float(pay.get("ctx", base["ctx_ng_ml"]))
    ctx_metric, ctx_dtr = _evaluate_resorption_marker(
        metric_name="ctx_bone_resorption",
        payload_key="ctx",
        current_val=ctx_val,
        baseline_val=float(base["ctx_ng_ml"]),
        unit="ng/mL",
        mission_day=mission_day,
        data_source=data_source,
        pay=pay,
        base=base,
        horizon_days=14,
    )

    # 9. Bio-Analyzer Bone Formation: P1NP
    p1np_val = float(pay.get("p1np", base["p1np_ug_l"]))
    p1np_metric, p1np_dtr = _evaluate_loss_metric(
        metric_name="p1np_bone_formation",
        current_val=p1np_val,
        baseline_val=float(base["p1np_ug_l"]),
        yellow_loss_pct=15.0,
        red_loss_pct=25.0,
        unit="ug/L",
        mission_day=mission_day,
        data_source=data_source,
        pay=pay,
        base=base,
        sample_key="p1np",
        horizon_days=14,
        action_nominal="Osteoblast bone formation marker P1NP stable.",
        action_abnormal="Combine high-impact E4D axial loading with Vitamin D3 & protein intake.",
    )

    # 10. Estimated Monthly Bone Loss Rate (ISS benchmarks: spine ~0.9%/mo, hip ~1.4-1.5%/mo)
    ctx_ratio = ctx_val / max(float(base["ctx_ng_ml"]), 1e-6)
    resorption_factor = max(0.25, ctx_ratio - 0.70)
    unloading_factor = max(0.35, 1.45 - s_bone)
    est_hip_loss_mo = round(min(2.4, 0.75 * resorption_factor * unloading_factor * 1.45), 2)
    est_spine_loss_mo = round(est_hip_loss_mo * (0.9 / 1.45), 2)
    if est_hip_loss_mo >= 1.4:
        bone_rate_status = "RED"
    elif est_hip_loss_mo >= 0.9:
        bone_rate_status = "YELLOW"
    else:
        bone_rate_status = "GREEN"

    bone_rate_metric = {
        "metric_name": "est_monthly_bone_loss_pct",
        "current_val": est_hip_loss_mo,
        "baseline_val": 0.4,
        "delta_pct": round((est_hip_loss_mo - 0.4) * 100.0, 1),
        "slope_per_day": round(-est_hip_loss_mo / 30.0, 4),
        "unit": "%/mo",
        "status_light": bone_rate_status,
        "decided_by": "rule",
        "data_source": data_source,
        "yellow_threshold": 0.9,
        "red_threshold": 1.4,
        "lower_is_worse": False,
        "message": (
            f"Estimated monthly bone loss: Hip ~{est_hip_loss_mo:.2f}%/mo, Spine ~{est_spine_loss_mo:.2f}%/mo "
            "(ISS unmitigated benchmark: Spine ~0.9%/mo, Hip ~1.4-1.5%/mo)."
        ),
        "action": (
            "Increase axial E4D resistance load & verify anti-resorptive/nutrition protocol."
            if bone_rate_status != "GREEN"
            else "Countermeasure suppresses bone loss well below ISS unmitigated rate."
        ),
    }

    # 11. NASA OSDR OSD-575 Serum Calcium & ALP Baseline Validation
    osd_summary = _load_osd575_summary()
    ca_val = float(pay.get("serum_ca_mg_dl", osd_summary["ca_mean"]))
    alp_val = float(pay.get("serum_alp_u_l", osd_summary["alp_mean"]))
    if ca_val > 10.5 or ca_val < 8.2:
        osd_status = "RED"
        osd_msg = (
            f"Serum Ca={ca_val:.2f} mg/dL (OSD-575 ref {osd_summary['ca_mean']:.2f}), ALP={alp_val:.0f} U/L: "
            "Hypercalcemia/demineralization alert — elevated renal stone risk."
        )
        osd_act = "Force hydration >= 2.8 L/day, verify Ca excretion, and notify Flight Surgeon."
    elif ca_val >= 10.1 or alp_val >= 115.0:
        osd_status = "YELLOW"
        osd_msg = (
            f"Serum Ca={ca_val:.2f} mg/dL, ALP={alp_val:.0f} U/L trending high vs OSD-575 cohort "
            f"(mean Ca {osd_summary['ca_mean']:.2f} mg/dL, ALP {osd_summary['alp_mean']:.0f} U/L)."
        )
        osd_act = "Increase hydration >= 2.5 L/day and repeat Bio-Analyzer CMP panel in 72h."
    else:
        osd_status = "GREEN"
        osd_msg = (
            f"Serum Ca={ca_val:.2f} mg/dL & ALP={alp_val:.0f} U/L aligned with NASA OSD-575 baseline "
            f"(mean Ca {osd_summary['ca_mean']:.2f} mg/dL, ALP {osd_summary['alp_mean']:.0f} U/L)."
        )
        osd_act = "Serum Calcium and ALP stable."

    osd_metric = {
        "metric_name": "osd575_ca_alp_baseline",
        "current_val": round(ca_val, 2),
        "baseline_val": osd_summary["ca_mean"],
        "delta_pct": round(((ca_val - osd_summary["ca_mean"]) / max(osd_summary["ca_mean"], 1e-6)) * 100.0, 1),
        "slope_per_day": 0.0,
        "unit": "mg/dL",
        "status_light": osd_status,
        "decided_by": "rule",
        "data_source": osd_summary["data_source"],
        "yellow_threshold": 10.1,
        "red_threshold": 10.5,
        "lower_is_worse": False,
        "message": osd_msg,
        "action": osd_act,
    }

    metrics = [
        thigh_metric,
        calf_metric,
        vbt_metric,
        s_bone_metric,
        iso_metric,
        mass_metric,
        ntx_metric,
        ctx_metric,
        p1np_metric,
        bone_rate_metric,
        osd_metric,
    ]

    overall = _worst([m["status_light"] for m in metrics])
    dtr_candidates = [d for d in (iso_dtr, thigh_dtr, calf_dtr, mass_dtr, ntx_dtr, ctx_dtr, p1np_dtr) if d is not None]
    days_until_red: Optional[int] = 0 if overall == "RED" else (min(dtr_candidates) if dtr_candidates else None)

    # Closed-loop schedule mutation per USER.md & AGENTS.md
    if overall == "RED":
        next_hours = 24
        immediate_actions = [
            "STOP the fatigued E4D set immediately if VBT velocity loss > 30% and alert ground Flight Surgeon.",
            "Shift next session to controlled eccentric/hypertrophy loading (cap VBT loss <= 25%) and verify Cardio/Immune clearance.",
            "Verify hydration >= 2.8 L/day, +20g post-workout whey/leucine, and Vitamin D3/Ca intake; repeat Ultrasound 2 scan within 24h.",
        ]
        long_adj = (
            "24h ground alert + 4-week progressive lower-limb hypertrophy block, +350 kcal/day protein surplus, "
            "and 14-day Bio-Analyzer CTX/NTX & Ultrasound CSA re-evaluation."
        )
    elif overall == "YELLOW":
        next_hours = 72
        immediate_actions = [
            "Increase E4D squat/deadlift load +5% with faster concentric loading rate to push S_bone >= 0.90 and VBT loss into 20-30%.",
            "Add 1 extra unilateral heel-raise / posterior-chain set and confirm protein >= 1.6 g/kg/day.",
            "Schedule follow-up Ultrasound 2 thigh/calf & E4D check in 72 hours.",
        ]
        long_adj = "+5% E4D squat/deadlift load progression with higher loading rate; repeat Ultrasound CSA & bone markers in 72h–7d."
    else:
        next_hours = 168
        immediate_actions = [
            "Continue nominal 6-day/week E4D resistance & CEVIS countermeasure schedule; target VBT loss 20-30%."
        ]
        long_adj = "Maintain current E4D progressive resistance schedule (weekly 168h verification)."

    return {
        "module_id": "musculoskeletal",
        "body_part_tag": "lower_limb_bone_muscle",
        "crew_id": crew_id,
        "mission_day": mission_day,
        "status_light": overall,
        "quality_passed": True,
        "data_source": data_source,
        "summary_note": (
            f"S_bone={s_bone:.2f}, VBT={vbt_loss:.1f}%, Thigh={thigh_metric['delta_pct']:+.1f}%, "
            f"Calf={calf_metric['delta_pct']:+.1f}%, CTX={ctx_metric['delta_pct']:+.1f}%, "
            f"Est Hip Loss={est_hip_loss_mo:.2f}%/mo."
        ),
        "metrics": metrics,
        "guidance": {
            "how_to_measure": (
                "1) Attach E4D VBT linear encoder & zero the load cell; log squat peak force, loading rate, reps, "
                "and intra-set velocity loss. 2) Scan pre-marked 50% mid-thigh & 30% proximal calf landmarks with "
                "Ultrasound 2. 3) Record morning SLAMMD body mass and run Bio-Analyzer NTX/CTX/P1NP fingerstick/urine cartridge."
            ),
            "plain_explanation": (
                "Without Earth's 1g gravity, weight-bearing leg muscles rapidly shrink and bone calcium dissolves into "
                "the bloodstream (raising fracture and kidney-stone risk before Mars landing). Tracking E4D mechanical "
                "stimulus (S_bone, VBT 20-30% zone), muscle cross-section, and bone turnover keeps countermeasures effective offline."
            ),
            "action_protocol": immediate_actions,
        },
        "short_term_plan": {
            "next_measurement_in_hours": next_hours,
            "immediate_actions": immediate_actions,
            "urgent_alert": overall == "RED",
        },
        "long_term_plan": {
            "days_until_red_prediction": days_until_red,
            "routine_prescription_adjustment": long_adj,
        },
        "schedule_mutation": {
            "next_measurement_in_hours": next_hours,
            "prescription_adjustment": long_adj,
            "urgent_alert": overall == "RED",
        },
        "trend_series": {
            "days": thigh_metric["history_days"],
            "csa_thigh_cm2": thigh_metric["history_values"],
            "csa_calf_cm2": calf_metric["history_values"],
            "ntx": ntx_metric["history_values"],
            "ctx": ctx_metric["history_values"],
            "est_monthly_bone_loss_hip_pct": est_hip_loss_mo,
            "est_monthly_bone_loss_spine_pct": est_spine_loss_mo,
        },
    }


def to_schema(
    result_or_payload: Optional[Union[dict[str, Any], ModuleEvaluationResult]] = None,
    baseline: Optional[dict[str, Any]] = None,
    manual_overrides: Optional[dict[str, Any]] = None,
) -> ModuleEvaluationResult:
    """Validate and return a strict Pydantic ModuleEvaluationResult contract object."""
    if isinstance(result_or_payload, ModuleEvaluationResult):
        return result_or_payload
    if isinstance(result_or_payload, dict) and "module_id" in result_or_payload and "metrics" in result_or_payload:
        return normalize_module_result(result_or_payload, module_id="musculoskeletal")
    raw = evaluate(payload=result_or_payload, baseline=baseline, manual_overrides=manual_overrides)
    return normalize_module_result(raw, module_id="musculoskeletal")


# ==============================================================================
# Plotly Visualization Helpers for Role 1 Streamlit Dashboard (app.py)
# ==============================================================================


def build_trajectory_figure() -> Any:
    """Return interactive Plotly figure of 3-scenario Calf CSA & NTX trajectories with threshold bands."""
    if go is None or make_subplots is None:
        raise ImportError("plotly is required to build musculoskeletal figures.")

    base = demo_baseline()
    calf_base = float(base["csa_calf_cm2"])
    ntx_base = float(base["ntx_nm_bce"])

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Ultrasound 2 Calf CSA Trajectory (cm^2)", "Bone Resorption NTX Trajectory (nM BCE)"),
    )
    colors = {"green": "#22c55e", "yellow": "#eab308", "red": "#ef4444"}

    for scen in ("green", "yellow", "red"):
        pay = demo_payload(scen)
        days = pay["history_days"]
        calf_vals = pay["history_series"]["csa_calf_cm2"]
        ntx_vals = pay["history_series"]["ntx"]
        fig.add_trace(
            go.Scatter(x=days, y=calf_vals, mode="lines+markers", name=f"Calf CSA ({scen.upper()})", line=dict(color=colors[scen], width=2.5)),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=days, y=ntx_vals, mode="lines+markers", name=f"NTX ({scen.upper()})", line=dict(color=colors[scen], width=2.5, dash="dot")),
            row=1,
            col=2,
        )

    fig.add_hline(y=calf_base * 0.95, line_dash="dash", line_color="#eab308", annotation_text="-5% Yellow", row=1, col=1)
    fig.add_hline(y=calf_base * 0.90, line_dash="dash", line_color="#ef4444", annotation_text="-10% Red", row=1, col=1)
    fig.add_hline(y=ntx_base * 1.25, line_dash="dash", line_color="#eab308", annotation_text="+25% Yellow", row=1, col=2)
    fig.add_hline(y=ntx_base * 1.50, line_dash="dash", line_color="#ef4444", annotation_text="+50% Red", row=1, col=2)

    fig.update_layout(
        template="plotly_dark",
        height=380,
        title="Musculoskeletal 3-Scenario Countermeasure Trajectories",
        legend=dict(orientation="h", y=-0.2),
    )
    return fig


def build_iss_comparison_figure(eval_result: Optional[dict[str, Any]] = None) -> Any:
    """Compare evaluated monthly bone loss rate against published ISS Spine (~0.9%/mo) & Hip (~1.45%/mo) benchmarks."""
    if go is None:
        raise ImportError("plotly is required to build musculoskeletal figures.")

    res = eval_result or evaluate(demo_payload("green"))
    trend = res.get("trend_series", {})
    hip_rate = float(trend.get("est_monthly_bone_loss_hip_pct", 0.38))
    spine_rate = float(trend.get("est_monthly_bone_loss_spine_pct", 0.24))

    fig = go.Figure(
        data=[
            go.Bar(
                name="Current Z.O.S.M.A. Estimate",
                x=["Lumbar Spine (%/mo)", "Proximal Hip (%/mo)"],
                y=[spine_rate, hip_rate],
                marker_color="#38bdf8",
            ),
            go.Bar(
                name="Published ISS Unmitigated Loss",
                x=["Lumbar Spine (%/mo)", "Proximal Hip (%/mo)"],
                y=[0.90, 1.45],
                marker_color="#f97316",
            ),
        ]
    )
    fig.update_layout(
        barmode="group",
        template="plotly_dark",
        height=340,
        title="Estimated Monthly Bone Loss vs. Published ISS Spaceflight Benchmarks",
        yaxis_title="Bone Mineral Loss Rate (%/month)",
    )
    return fig


def build_osd575_baseline_figure() -> Any:
    """Plot NASA OSDR OSD-575 Serum Calcium & ALP baseline reference check."""
    if go is None or make_subplots is None:
        raise ImportError("plotly is required to build musculoskeletal figures.")

    osd = _load_osd575_summary()
    idx = list(range(1, len(osd["ca_series"]) + 1))

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            f"OSD-575 Serum Calcium ({osd['data_source']})",
            f"OSD-575 Alkaline Phosphatase ({osd['data_source']})",
        ),
    )
    fig.add_trace(
        go.Bar(x=idx, y=osd["ca_series"], name="Calcium (mg/dL)", marker_color="#38bdf8"),
        row=1,
        col=1,
    )
    fig.add_hline(y=10.5, line_dash="dash", line_color="#ef4444", annotation_text="Upper Limit 10.5", row=1, col=1)
    fig.add_hline(y=8.5, line_dash="dash", line_color="#eab308", annotation_text="Lower Limit 8.5", row=1, col=1)

    fig.add_trace(
        go.Bar(x=idx, y=osd["alp_series"], name="ALP (U/L)", marker_color="#a855f7"),
        row=1,
        col=2,
    )
    fig.add_hline(y=147.0, line_dash="dash", line_color="#ef4444", annotation_text="Upper Limit 147", row=1, col=2)
    fig.update_layout(template="plotly_dark", height=340, title="NASA OSDR OSD-575 Serum Ca & ALP Baseline Check")
    return fig


# ==============================================================================
# CLI Self-Test Entrypoint (`python -m modules.musculoskeletal`)
# ==============================================================================


if __name__ == "__main__":
    folder_info = inspect_data_folder()
    print("=== Z.O.S.M.A. Role 2: Musculoskeletal Module Self-Test ===")
    print(f"Data directory: {folder_info['data_dir']}")
    if folder_info["is_empty"] or folder_info["missing_files"]:
        print(f"Missing files detected: {folder_info['missing_files']} -> exporting starter templates...")
        exported = export_demo_csvs()
        for p in exported:
            print(f"  Exported: {p}")
    else:
        print(f"Present files: {folder_info['present_files']}")

    for scen in ("green", "yellow", "red", "bad_data"):
        raw = evaluate(demo_payload(scen))
        validated = to_schema(raw)
        assert validated.module_id == "musculoskeletal"
        assert validated.body_part_tag == "lower_limb_bone_muscle"
        if scen == "bad_data":
            assert validated.quality_passed is False
            assert validated.short_term_plan.next_measurement_in_hours == 0
        elif scen == "green":
            assert validated.status_light == "GREEN"
            assert validated.quality_passed is True
            assert validated.short_term_plan.next_measurement_in_hours == 168
        elif scen == "yellow":
            assert validated.status_light == "YELLOW"
            assert validated.quality_passed is True
            assert validated.short_term_plan.next_measurement_in_hours == 72
        elif scen == "red":
            assert validated.status_light == "RED"
            assert validated.quality_passed is True
            assert validated.short_term_plan.next_measurement_in_hours == 24
            assert validated.short_term_plan.urgent_alert is True

        print(
            f"[{scen.upper():8s}] status={validated.status_light:6s} | "
            f"raw={validated.raw_status:17s} | qc={str(validated.quality_passed):5s} | "
            f"next={validated.short_term_plan.next_measurement_in_hours:3d}h | "
            f"metrics={len(validated.metrics):2d} | {raw['summary_note']}"
        )

    # Verify manual_overrides transition (GREEN -> RED on VBT > 30%)
    ov_res = to_schema(evaluate(demo_payload("green"), manual_overrides={"velocity_loss_pct": 34.0}))
    assert ov_res.status_light == "RED"
    print(f"[OVERRIDE] VBT=34.0% -> status={ov_res.status_light} | urgent={ov_res.short_term_plan.urgent_alert}")

    # Verify Plotly figure helpers execute cleanly
    fig1 = build_trajectory_figure()
    fig2 = build_iss_comparison_figure()
    fig3 = build_osd575_baseline_figure()
    assert fig1 is not None and fig2 is not None and fig3 is not None
    print("Plotly figures (trajectory, ISS comparison, OSD-575 baseline) built successfully.")
    print("ALL MUSCULOSKELETAL CHECKS PASSED.")
