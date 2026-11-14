"""Role 2: Musculoskeletal (Bone & Muscle) Domain Module for Team Z.O.S.M.A.

Self-contained stateless evaluator implementing Layer 0 QC + 3-Layer Decision Model:
- Layer 0: Sensor, Missing-Field, History & Physiological Plausibility QC Gatekeeper
- Layer 1: Z.O.S.M.A. Operational & Clinical Thresholds
- Layer 2: Personal Pre-Flight Baseline (+/- 2 SD; 5% SD floor on NTX/CTX)
- Layer 3: 4-Point Trend Slope Projection (upgrades GREEN -> YELLOW if RED projected
           within the next 30-day scheduled monitoring cycle)

Scientific Literature & Threshold Provenance:
- Background literature (see REFERENCES) establishes physiological mechanisms and ISS
  benchmarks; specific Z.O.S.M.A. traffic-light cutoffs (e.g., Thigh CSA 4%/7%, Calf CSA
  5%/10%, P1NP 15%/25%, VBT >30%, S_bone 0.90/0.75) are project-defined operational
  heuristics informed by that literature rather than direct trial-derived cutoffs.
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
except ImportError:  # pragma: no cover
    go = None  # type: ignore[assignment]
    make_subplots = None  # type: ignore[assignment]

from core.schema import ModuleEvaluationResult, normalize_module_result

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "musculoskeletal"
SHARED_REAL_DIR = BASE_DIR / "data" / "shared_real"

REFERENCES: dict[str, dict[str, str]] = {
    "bone_loss_iss": {
        "citation": "LeBlanc et al. (2000), J Bone Miner Res; Sibonga et al. (2007), Bone 41(6):973-983.",
        "supports": "Background ISS BMD loss rates (~0.9%/mo lumbar spine, ~1.4-1.5%/mo proximal hip).",
        "project_heuristic_note": "est_monthly_bone_loss_pct is a Z.O.S.M.A. heuristic risk model (not direct DXA).",
    },
    "muscle_atrophy": {
        "citation": "Trappe et al. (2009), J Appl Physiol 106(4):1159-1168; Gopalakrishnan et al. (2010), Aviat Space Environ Med.",
        "supports": "Spaceflight lower-limb muscle atrophy & resistive exercise countermeasure principles.",
        "project_heuristic_note": "Thigh CSA (4%/7%), Calf CSA (5%/10%), Body mass (5%/10%), and S_bone (0.90/0.75) cutoffs are Z.O.S.M.A. operational thresholds.",
    },
    "vbt_training": {
        "citation": "Pareja-Blanco et al. (2017), Scand J Med Sci Sports 27(7):724-735.",
        "supports": "Compared 20% vs 40% intra-set velocity loss, showing 20% preserves adaptations with less neuromuscular fatigue.",
        "project_heuristic_note": "20-30% green zone and >30% acute set-fatigue cutoff are Z.O.S.M.A. interpolated operational limits.",
    },
    "bone_markers_cmp": {
        "citation": "Smith et al. (2005, 2012), J Bone Miner Res; NASA-STD-3001 Vol 2 (nutrition/hydration principles).",
        "supports": "Elevated bone resorption (NTX/CTX) in microgravity, Vitamin D3 supplementation, and hydration for renal stone risk.",
        "project_heuristic_note": "NTX/CTX +50% Red, P1NP 15%/25%, +350 kcal/d, 800-1000 IU/d Vit D3, and 2.5-2.8 L/d are Z.O.S.M.A. operational guidance targets.",
    },
}

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
        "is_demo_template",
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
        "data_source",
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
        "data_source",
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
    "s_bone": (0.05, 5.0, "index"),
    "s_bone_index": (0.05, 5.0, "index"),
}

# Core measurements required for a complete musculoskeletal evaluation
REQUIRED_GROUPS: dict[str, tuple[str, ...]] = {
    "e4d_force_or_sbone": ("peak_force_n", "s_bone", "s_bone_index"),
    "velocity_loss_pct": ("velocity_loss_pct",),
    "iso_peak_force_n": ("iso_peak_force_n",),
    "csa_thigh_cm2": ("csa_thigh_cm2",),
    "csa_calf_cm2": ("csa_calf_cm2",),
    "body_mass_kg": ("body_mass_kg",),
    "ntx": ("ntx", "ntx_nm_bce"),
    "ctx": ("ctx", "ctx_ng_ml"),
    "p1np": ("p1np", "p1np_ug_l"),
}

# Unified Serum Calcium & ALP clinical thresholds shared by evaluate() and Plotly charts
CA_RED_LOW = 8.2
CA_YELLOW_LOW = 8.5
CA_YELLOW_HIGH = 10.1
CA_RED_HIGH = 10.5
ALP_YELLOW_HIGH = 120.0
ALP_RED_HIGH = 147.0

# Synthetic fallback cohort used ONLY when real NASA OSDR OSD-575_cmp.csv is absent
SIMULATED_CMP_FALLBACK: list[dict[str, Any]] = [
    {"subject_id": "SIM_REF_01", "timepoint": "Simulated_Preflight", "calcium_mg_dl": 9.3, "alp_u_l": 64.0},
    {"subject_id": "SIM_REF_02", "timepoint": "Simulated_Preflight", "calcium_mg_dl": 9.5, "alp_u_l": 71.0},
    {"subject_id": "SIM_REF_03", "timepoint": "Simulated_Preflight", "calcium_mg_dl": 9.2, "alp_u_l": 66.0},
    {"subject_id": "SIM_REF_04", "timepoint": "Simulated_Preflight", "calcium_mg_dl": 9.6, "alp_u_l": 75.0},
]


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


def demo_baseline() -> dict[str, Any]:
    """Return simulated pre-flight personal baseline with 3 samples per metric.

    Note: Sample spread in `demo_baseline` is calibrated slightly wider than Layer 1
    fixed thresholds so standard Z.O.S.M.A. fixed thresholds (4%/5%/10%/15%) apply
    by default, while astronauts with tighter personal baseline SDs trigger Layer 2 first.
    """
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
        "is_demo_template": True,
        "preflight_samples": {
            "iso_peak_force_n": [1750.0, 1850.0, 1950.0],  # 2*SD ~ 10.8% (> 10% Layer 1)
            "csa_thigh_cm2": [144.8, 148.0, 151.2],       # 2*SD ~ 4.3%  (> 4% Layer 1)
            "csa_calf_cm2": [79.8, 82.0, 84.2],           # 2*SD ~ 5.4%  (> 5% Layer 1)
            "body_mass_kg": [72.0, 74.0, 76.0],           # 2*SD ~ 5.4%  (> 5% Layer 1)
            "ntx": [13.5, 14.0, 14.5],                    # 5% SD floor -> +10% Layer 2 Yellow
            "ctx": [0.35, 0.36, 0.37],                    # 5% SD floor -> +10% Layer 2 Yellow
            "p1np": [41.4, 45.0, 48.6],                   # 2*SD = 16.0% (> 15% Layer 1)
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
            "velocity_loss_pct": 33.5,  # > 30% Red set-fatigue limit
            "iso_peak_force_n": 1440.0,  # -22.2% strength loss (RED >= 20%)
            "csa_thigh_cm2": 136.0,     # -8.1% loss (RED >= 7%)
            "csa_calf_cm2": 73.0,      # -11.0% loss (RED >= 10%)
            "body_mass_kg": 66.0,      # -10.8% loss (RED >= 10%)
            "ntx": 22.8,               # +62.9% elevation (RED >= +50%)
            "ctx": 0.58,               # +61.1% elevation (RED >= +50%)
            "p1np": 32.5,              # -27.8% suppression (RED >= 25% drop)
            "serum_ca_mg_dl": 10.7,    # > 10.5 mg/dL hypercalcemia alert
            "serum_alp_u_l": 152.0,    # >= 147 U/L elevated ALP (RED)
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
        "velocity_loss_pct": 24.5,  # Optimal 20-30% VBT window
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
    """Compute heuristic E4D Bone Stimulus Index (S_bone) from force, loading rate, and reps."""
    force_ratio = max(peak_force_n, 0.0) / max(baseline_force_n, 1.0)
    rate_ratio = (max(loading_rate_n_s, 1.0) / max(baseline_loading_rate_n_s, 1.0)) ** 0.25
    rep_factor = 1.0 + 0.15 * math.log(max(reps, 1.0) / 8.0)
    return round(force_ratio * rate_ratio * max(rep_factor, 0.5), 3)


def export_demo_csvs() -> list[str]:
    """Generate editable SIMULATED starter CSV/JSON templates inside data/musculoskeletal/."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    base = demo_baseline()
    baseline_path = DATA_DIR / "preflight_baseline.json"
    with baseline_path.open("w", encoding="utf-8") as fh:
        json.dump(base, fh, indent=2)
    written.append(str(baseline_path))

    e4d_rows = [
        {"mission_day": 30, "exercise": "Squat", "peak_force_n": 1840.0, "loading_rate_n_s": 3300.0, "reps": 8, "velocity_loss_pct": 23.0, "sensor_qc_ok": True, "data_source": "SIMULATED"},
        {"mission_day": 60, "exercise": "Squat", "peak_force_n": 1835.0, "loading_rate_n_s": 3280.0, "reps": 8, "velocity_loss_pct": 23.8, "sensor_qc_ok": True, "data_source": "SIMULATED"},
        {"mission_day": 90, "exercise": "Squat", "peak_force_n": 1830.0, "loading_rate_n_s": 3260.0, "reps": 8, "velocity_loss_pct": 24.2, "sensor_qc_ok": True, "data_source": "SIMULATED"},
        {"mission_day": 124, "exercise": "Squat", "peak_force_n": 1825.0, "loading_rate_n_s": 3250.0, "reps": 8, "velocity_loss_pct": 24.5, "sensor_qc_ok": True, "data_source": "SIMULATED"},
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
            {"mission_day": 30, "iso_peak_force_n": 1840.0, "csa_thigh_cm2": 147.6, "csa_calf_cm2": 81.7, "body_mass_kg": 73.8, "ntx": 14.2, "ctx": 0.36, "p1np": 45.0, "serum_ca_mg_dl": 9.4, "serum_alp_u_l": 68.0, "sensor_qc_ok": True, "data_source": "SIMULATED"},
            {"mission_day": 60, "iso_peak_force_n": 1832.0, "csa_thigh_cm2": 147.2, "csa_calf_cm2": 81.4, "body_mass_kg": 73.6, "ntx": 14.4, "ctx": 0.37, "p1np": 44.8, "serum_ca_mg_dl": 9.4, "serum_alp_u_l": 69.0, "sensor_qc_ok": True, "data_source": "SIMULATED"},
            {"mission_day": 90, "iso_peak_force_n": 1822.0, "csa_thigh_cm2": 146.8, "csa_calf_cm2": 81.1, "body_mass_kg": 73.4, "ntx": 14.6, "ctx": 0.37, "p1np": 44.6, "serum_ca_mg_dl": 9.5, "serum_alp_u_l": 69.5, "sensor_qc_ok": True, "data_source": "SIMULATED"},
            {"mission_day": 124, "iso_peak_force_n": 1815.0, "csa_thigh_cm2": 146.4, "csa_calf_cm2": 80.9, "body_mass_kg": 73.2, "ntx": 14.8, "ctx": 0.38, "p1np": 44.5, "serum_ca_mg_dl": 9.5, "serum_alp_u_l": 70.0, "sensor_qc_ok": True, "data_source": "SIMULATED"},
        ]
    )
    meas_path = DATA_DIR / "measurements_long.csv"
    meas_df.to_csv(meas_path, index=False)
    written.append(str(meas_path))
    return written


def _load_osd575_summary() -> dict[str, Any]:
    """Load real NASA OSDR OSD-575 serum Ca & ALP if present; report explicit errors or fallback."""
    csv_path = _find_osd575_csv()
    if csv_path is not None:
        try:
            df = pd.read_csv(csv_path)
            if df.empty:
                return {
                    "data_source": "SIMULATED",
                    "load_error": f"OSD-575 file {csv_path.name} is empty.",
                    "source_file": str(csv_path),
                    "n_records": 0,
                    "ca_mean": 9.4,
                    "ca_sd": None,
                    "alp_mean": 69.0,
                    "alp_sd": None,
                    "ca_series": [r["calcium_mg_dl"] for r in SIMULATED_CMP_FALLBACK],
                    "alp_series": [r["alp_u_l"] for r in SIMULATED_CMP_FALLBACK],
                }
            cols_lower = {str(c).strip().lower(): c for c in df.columns}
            ca_col = next(
                (cols_lower[c] for c in cols_lower if c in {"ca", "calcium", "calcium_mg_dl", "serum_ca_mg_dl"} or "calc" in c),
                None,
            )
            alp_col = next(
                (cols_lower[c] for c in cols_lower if c in {"alp", "alp_u_l", "serum_alp_u_l", "alk_phos"} or "alkaline" in c or c.startswith("alp")),
                None,
            )
            if ca_col is None or alp_col is None:
                return {
                    "data_source": "SIMULATED",
                    "load_error": (
                        f"Column mismatch in {csv_path.name}: expected Calcium & ALP columns, "
                        f"found {list(df.columns)}. Falling back to clinical reference."
                    ),
                    "source_file": str(csv_path),
                    "n_records": len(df),
                    "ca_mean": 9.4,
                    "ca_sd": None,
                    "alp_mean": 69.0,
                    "alp_sd": None,
                    "ca_series": [r["calcium_mg_dl"] for r in SIMULATED_CMP_FALLBACK],
                    "alp_series": [r["alp_u_l"] for r in SIMULATED_CMP_FALLBACK],
                }
            ca_vals = pd.to_numeric(df[ca_col], errors="coerce").dropna().tolist()
            alp_vals = pd.to_numeric(df[alp_col], errors="coerce").dropna().tolist()
            if not ca_vals or not alp_vals:
                return {
                    "data_source": "SIMULATED",
                    "load_error": f"No numeric Ca/ALP values parsed from {csv_path.name}.",
                    "source_file": str(csv_path),
                    "n_records": len(df),
                    "ca_mean": 9.4,
                    "ca_sd": None,
                    "alp_mean": 69.0,
                    "alp_sd": None,
                    "ca_series": [r["calcium_mg_dl"] for r in SIMULATED_CMP_FALLBACK],
                    "alp_series": [r["alp_u_l"] for r in SIMULATED_CMP_FALLBACK],
                }
            return {
                "data_source": "REAL",
                "load_error": None,
                "source_file": str(csv_path),
                "n_records": len(df),
                "ca_mean": round(float(np.mean(ca_vals)), 2),
                "ca_sd": round(float(np.std(ca_vals, ddof=1)), 3) if len(ca_vals) >= 2 else None,
                "alp_mean": round(float(np.mean(alp_vals)), 1),
                "alp_sd": round(float(np.std(alp_vals, ddof=1)), 2) if len(alp_vals) >= 2 else None,
                "ca_series": [round(float(x), 2) for x in ca_vals],
                "alp_series": [round(float(x), 1) for x in alp_vals],
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "data_source": "SIMULATED",
                "load_error": f"Failed reading {csv_path.name}: {exc}",
                "source_file": str(csv_path),
                "n_records": 0,
                "ca_mean": 9.4,
                "ca_sd": None,
                "alp_mean": 69.0,
                "alp_sd": None,
                "ca_series": [r["calcium_mg_dl"] for r in SIMULATED_CMP_FALLBACK],
                "alp_series": [r["alp_u_l"] for r in SIMULATED_CMP_FALLBACK],
            }

    ca_ref = [r["calcium_mg_dl"] for r in SIMULATED_CMP_FALLBACK]
    alp_ref = [r["alp_u_l"] for r in SIMULATED_CMP_FALLBACK]
    return {
        "data_source": "SIMULATED",
        "load_error": None,
        "source_file": "synthetic CMP clinical fallback (OSD-575 CSV not present)",
        "n_records": len(SIMULATED_CMP_FALLBACK),
        "ca_mean": round(float(np.mean(ca_ref)), 2),
        "ca_sd": None,
        "alp_mean": round(float(np.mean(alp_ref)), 1),
        "alp_sd": None,
        "ca_series": ca_ref,
        "alp_series": alp_ref,
    }


def _worst(statuses: list[str]) -> str:
    order = {"GREEN": 0, "YELLOW": 1, "RED": 2}
    return max(statuses, key=lambda s: order.get(s, 0)) if statuses else "GREEN"


def _safe_float(val: Any) -> Optional[float]:
    if val is None or isinstance(val, (bool, np.bool_)):
        return None
    try:
        num = float(val)
        return None if (math.isnan(num) or math.isinf(num)) else num
    except (TypeError, ValueError):
        return None


def _is_qc_failed_flag(val: Any) -> bool:
    """Robustly parse bool, numpy.bool_, numeric, or string QC flags."""
    if val is None:
        return False
    if isinstance(val, (bool, np.bool_)):
        return not bool(val)
    if isinstance(val, (int, float, np.number)):
        if isinstance(val, float) and math.isnan(val):
            return True
        return float(val) == 0.0
    token = str(val).strip().lower()
    return token in {"false", "0", "no", "n", "fail", "failed", "invalid", "f", ""}


def _resolve_alias(pay: dict[str, Any], primary: str, *aliases: str) -> tuple[bool, Any]:
    """Return (is_key_present, value) checking primary key then aliases."""
    for key in (primary, *aliases):
        if key in pay:
            return True, pay[key]
    return False, None


def _infer_data_source(pay: dict[str, Any], base: dict[str, Any], payload_was_none: bool) -> str:
    """Ensure simulated demo templates or demo payloads are never mislabeled as REAL."""
    if payload_was_none:
        return "SIMULATED"
    if base.get("is_demo_template") is True or pay.get("is_demo_template") is True:
        return "SIMULATED"

    # Check if CSV rows loaded by data_loader carry explicit data_source="SIMULATED"
    for csv_key in ("csv_e4d_sets", "csv_measurements_long"):
        rows = pay.get(csv_key)
        if isinstance(rows, list) and rows:
            row_sources = {
                str(r.get("data_source", "")).strip().upper()
                for r in rows
                if isinstance(r, dict) and r.get("data_source")
            }
            if row_sources and row_sources == {"SIMULATED"}:
                return "SIMULATED"

    explicit = str(pay.get("data_source", "UNKNOWN")).strip().upper()
    return explicit if explicit in {"REAL", "SIMULATED"} else "UNKNOWN"


def _run_layer0_qc(
    pay: dict[str, Any],
    base: dict[str, Any],
) -> tuple[bool, list[dict[str, Any]]]:
    """Layer 0 QC Gatekeeper: reject False QC flags, partial payloads, nulls, bad history, or out-of-bounds readings."""
    failures: list[dict[str, Any]] = []

    if _is_qc_failed_flag(pay.get("sensor_qc_ok")):
        failures.append(
            {
                "field": "sensor_qc_ok",
                "value": 0.0,
                "unit": "flag",
                "baseline_val": 1.0,
                "message": "Device sensor_qc_ok flag reported False (probe contact / load-cell tare failure).",
            }
        )

    baseline_map = {
        "peak_force_n": base.get("peak_force_n", 1850.0),
        "loading_rate_n_s": base.get("loading_rate_n_s", 3300.0),
        "reps": 8.0,
        "velocity_loss_pct": 25.0,
        "iso_peak_force_n": base.get("iso_peak_force_n", 1850.0),
        "csa_thigh_cm2": base.get("csa_thigh_cm2", 148.0),
        "csa_calf_cm2": base.get("csa_calf_cm2", 82.0),
        "body_mass_kg": base.get("body_mass_kg", 74.0),
        "ntx": base.get("ntx_nm_bce", 14.0),
        "ctx": base.get("ctx_ng_ml", 0.36),
        "p1np": base.get("p1np_ug_l", 45.0),
        "serum_ca_mg_dl": base.get("serum_ca_mg_dl", 9.4),
        "serum_alp_u_l": base.get("serum_alp_u_l", 68.0),
        "s_bone": base.get("s_bone_target", 1.0),
        "s_bone_index": base.get("s_bone_target", 1.0),
    }

    # Check completeness of all required core musculoskeletal groups (no partial silent GREEN!)
    missing_groups: list[str] = []
    for group_name, keys in REQUIRED_GROUPS.items():
        if not any(k in pay for k in keys):
            missing_groups.append(group_name)
    if missing_groups:
        failures.append(
            {
                "field": "incomplete_telemetry",
                "value": float(len(REQUIRED_GROUPS) - len(missing_groups)),
                "unit": "metrics",
                "baseline_val": float(len(REQUIRED_GROUPS)),
                "message": f"Incomplete musculoskeletal telemetry: missing {', '.join(missing_groups)}.",
            }
        )

    # Validate every present scalar field (including None/NaN/Inf/out-of-bounds)
    alias_map = {
        "ntx": ("ntx_nm_bce",),
        "ctx": ("ctx_ng_ml",),
        "p1np": ("p1np_ug_l",),
    }
    for field, (low, high, unit) in PLAUSIBILITY_BOUNDS.items():
        present, raw = _resolve_alias(pay, field, *alias_map.get(field, ()))
        if not present:
            continue
        if raw is None:
            failures.append(
                {
                    "field": field,
                    "value": None,
                    "unit": unit,
                    "baseline_val": baseline_map.get(field),
                    "message": f"{field} is null/missing.",
                }
            )
            continue
        val = _safe_float(raw)
        if val is None:
            failures.append(
                {
                    "field": field,
                    "value": None,
                    "unit": unit,
                    "baseline_val": baseline_map.get(field),
                    "message": f"{field} is non-numeric or NaN/Inf ({raw!r}).",
                }
            )
            continue
        if val < low or val > high:
            failures.append(
                {
                    "field": field,
                    "value": round(val, 3),
                    "unit": unit,
                    "baseline_val": baseline_map.get(field),
                    "message": f"{field}={val:.2f} {unit} outside plausible range [{low}, {high}] {unit}.",
                }
            )

    # Validate history_days & history_series (prevents TypeError on None/NaN inside history!)
    h_days = pay.get("history_days")
    if h_days is not None:
        if not isinstance(h_days, list) or any(_safe_float(d) is None for d in h_days):
            failures.append(
                {
                    "field": "history_days",
                    "value": None,
                    "unit": "days",
                    "baseline_val": None,
                    "message": "history_days contains null or non-numeric mission day.",
                }
            )

    h_series = pay.get("history_series")
    if isinstance(h_series, dict):
        for s_key, s_vals in h_series.items():
            if not isinstance(s_vals, list):
                failures.append(
                    {
                        "field": f"history_{s_key}",
                        "value": None,
                        "unit": "",
                        "baseline_val": None,
                        "message": f"history_series['{s_key}'] is not a list.",
                    }
                )
                continue
            bounds = PLAUSIBILITY_BOUNDS.get(s_key)
            for idx, item in enumerate(s_vals):
                num = _safe_float(item)
                if num is None:
                    failures.append(
                        {
                            "field": f"history_{s_key}",
                            "value": None,
                            "unit": bounds[2] if bounds else "",
                            "baseline_val": baseline_map.get(s_key),
                            "message": f"history_series['{s_key}'][{idx}] is null or non-numeric ({item!r}).",
                        }
                    )
                    break
                if bounds and (num < bounds[0] or num > bounds[1]):
                    failures.append(
                        {
                            "field": f"history_{s_key}",
                            "value": round(num, 3),
                            "unit": bounds[2],
                            "baseline_val": baseline_map.get(s_key),
                            "message": f"history_series['{s_key}'][{idx}]={num:.2f} {bounds[2]} outside [{bounds[0]}, {bounds[1]}].",
                        }
                    )
                    break

    return len(failures) == 0, failures


def _extract_history(
    pay: dict[str, Any],
    history_keys: tuple[str, ...],
    current_val: float,
    baseline_val: float,
    mission_day: int,
) -> tuple[list[int], list[float], str]:
    """Extract historical points from CSV rows or payload history_series; fallback to linear interpolation."""
    is_e4d = any(k in {"peak_force_n", "loading_rate_n_s", "velocity_loss_pct", "s_bone_index"} for k in history_keys)
    csv_rows = pay.get("csv_e4d_sets") if is_e4d else pay.get("csv_measurements_long")

    if isinstance(csv_rows, list) and len(csv_rows) >= 2:
        pts: list[tuple[int, float]] = []
        for row in csv_rows:
            if not isinstance(row, dict):
                continue
            d = _safe_float(row.get("mission_day"))
            v = None
            for hk in history_keys:
                if hk in row:
                    v = _safe_float(row.get(hk))
                    if v is not None:
                        break
            if d is not None and v is not None:
                pts.append((int(d), float(v)))
        if len(pts) >= 2:
            pts = pts[-4:]
            days = [p[0] for p in pts]
            vals = [round(p[1], 3) for p in pts]
            if days[-1] == mission_day:
                vals[-1] = round(current_val, 3)
            else:
                days.append(mission_day)
                vals.append(round(current_val, 3))
                days = days[-4:]
                vals = vals[-4:]
            return days, vals, "csv"

    h_days = pay.get("history_days")
    h_series = pay.get("history_series", {})
    if isinstance(h_days, list) and isinstance(h_series, dict):
        for hk in history_keys:
            raw_list = h_series.get(hk)
            if isinstance(raw_list, list) and len(raw_list) >= 2:
                vals_clean = [_safe_float(x) for x in raw_list[-4:]]
                days_clean = [_safe_float(d) for d in h_days[-len(vals_clean):]]
                if all(v is not None for v in vals_clean) and all(d is not None for d in days_clean):
                    vals = [round(float(v), 3) for v in vals_clean if v is not None]
                    days = [int(float(d)) for d in days_clean if d is not None]
                    if vals and days:
                        vals[-1] = round(current_val, 3)
                        days[-1] = mission_day
                        return days, vals, "series"

    days = [max(1, int(mission_day * f)) for f in (0.25, 0.50, 0.75)] + [mission_day]
    vals = [
        round(baseline_val + (current_val - baseline_val) * frac, 3)
        for frac in (0.25, 0.50, 0.75, 1.0)
    ]
    return days, vals, "interpolated"


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
    min_floor_pct: float = 0.015,
) -> tuple[float, float]:
    """Return (effective_sd, personal_mean) using 3 preflight samples and a percentage SD floor."""
    samples = (baseline.get("preflight_samples") or {}).get(sample_key)
    sample_sd = 0.0
    mean_val = baseline_val
    if isinstance(samples, list) and len(samples) >= 2:
        clean = [v for v in (_safe_float(x) for x in samples) if v is not None]
        if len(clean) >= 2:
            arr = np.asarray(clean, dtype=float)
            sample_sd = float(np.std(arr, ddof=1))
            mean_val = float(np.mean(arr))
    return max(sample_sd, baseline_val * min_floor_pct), mean_val


def _evaluate_loss_metric(
    *,
    metric_name: str,
    history_keys: tuple[str, ...],
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
    horizon_days: int = 30,
    action_nominal: str,
    action_abnormal: str,
) -> tuple[dict[str, Any], Optional[int]]:
    """3-Layer evaluation for metrics where loss below baseline is worse.

    - Layer 1: Fixed clinical/operational thresholds (`yellow_loss_pct`, `red_loss_pct`).
    - Layer 2: Personal pre-flight mean - 2 * SD (with 1.5% measurement precision floor).
               Triggers when an astronaut's personal preflight repeatability is tighter
               than the population threshold or their personal mean is elevated/shifted.
    - Layer 3: 4-point linear slope projection over the upcoming `horizon_days` (30 days,
               matching the monthly Ultrasound/SLAMMD/Bio-Analyzer monitoring cycle).
    """
    delta_pct = ((current_val - baseline_val) / max(baseline_val, 1e-6)) * 100.0
    loss_pct = -delta_pct
    days, vals, hist_src = _extract_history(pay, history_keys, current_val, baseline_val, mission_day)
    slope = _compute_slope(days, vals)

    yellow_thresh = round(baseline_val * (1.0 - yellow_loss_pct / 100.0), 2)
    red_thresh = round(baseline_val * (1.0 - red_loss_pct / 100.0), 2)

    # Layer 1: Fixed Thresholds
    l1_status = "GREEN"
    if loss_pct >= red_loss_pct:
        l1_status = "RED"
    elif loss_pct >= yellow_loss_pct:
        l1_status = "YELLOW"

    # Layer 2: Personal Baseline - 2 SD (1.5% precision floor, independent of Layer 1)
    sd_eff, p_mean = _baseline_sd_with_floor(base, sample_key, baseline_val, min_floor_pct=0.015)
    l2_lower = p_mean - 2.0 * sd_eff
    l2_status = "YELLOW" if (current_val <= l2_lower and l1_status == "GREEN") else "GREEN"

    # Layer 3: 30-day Trend Projection
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
        "history_source": hist_src,
        "message": (
            f"{metric_name}: {current_val:.1f} {unit} ({delta_pct:+.1f}% vs baseline {baseline_val:.1f}; "
            f"Yellow -{yellow_loss_pct:.0f}%, Red -{red_loss_pct:.0f}%)."
            + (f" Trend predicts RED in ~{days_to_red}d." if l3_status == "YELLOW" and days_to_red else "")
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
    horizon_days: int = 30,
) -> tuple[dict[str, Any], Optional[int]]:
    """Evaluate NTX/CTX ONLY in the bone-loss (increase) direction.

    Uses a 5% minimum SD floor for the +2 SD personal baseline Yellow rule (+10% minimum)
    plus an absolute Red threshold at >= +50% above baseline.
    """
    delta_pct = ((current_val - baseline_val) / max(baseline_val, 1e-6)) * 100.0
    days, vals, hist_src = _extract_history(
        pay, (payload_key, metric_name), current_val, baseline_val, mission_day
    )
    slope = _compute_slope(days, vals)

    sd_floor, p_mean = _baseline_sd_with_floor(base, payload_key, baseline_val, min_floor_pct=0.05)
    two_sd_upper = round(p_mean + 2.0 * sd_floor, 3)
    red_thresh = round(baseline_val * 1.50, 3)
    yellow_thresh = min(two_sd_upper, red_thresh)

    # Layer 1: Absolute Red threshold >= +50%
    l1_status = "RED" if delta_pct >= 50.0 else "GREEN"

    # Layer 2: Personal +2 SD (5% SD floor) — bone-loss (increase) direction ONLY
    l2_status = "YELLOW" if (current_val >= two_sd_upper and l1_status == "GREEN") else "GREEN"

    # Layer 3: 30-day Trend projection toward +50% Red
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
        "history_source": hist_src,
        "message": (
            f"{payload_key.upper()} bone resorption {current_val:.2f} {unit} ({delta_pct:+.1f}% vs baseline; "
            f"Yellow +2 SD w/ 5% floor={two_sd_upper:.2f}, Red >= +50%)."
            + (f" Trend predicts RED in ~{days_to_red}d." if l3_status == "YELLOW" and days_to_red else "")
        ),
        "action": (
            "Increase axial E4D resistance load +5%, verify Vitamin D3 (800-1000 IU/d target) & Ca intake."
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
    """Stateless Layer 0 + 3-Layer Musculoskeletal evaluation returning standardized dict.

    - If `payload` is None, falls back to `demo_payload("green")`.
    - If `payload` is explicitly provided (even `{}` or partial), missing core fields
      trigger Layer 0 QC (`INSUFFICIENT_DATA`, `quality_passed=False`, `next=0h`) instead
      of being silently filled with healthy values.
    """
    payload_was_none = payload is None
    base = {**demo_baseline(), **(baseline or {})}
    pay = demo_payload("green") if payload_was_none else dict(payload)  # type: ignore[arg-type]

    if manual_overrides:
        for k, v in manual_overrides.items():
            if v is not None:
                pay[k] = v

    crew_id = str(pay.get("crew_id", base.get("crew_id", "C002")))
    mission_day = int(_safe_float(pay.get("mission_day")) or 124)
    data_source = _infer_data_source(pay, base, payload_was_none)

    # ---------------- LAYER 0: QC GATEKEEPER ----------------
    qc_passed, qc_failures = _run_layer0_qc(pay, base)
    if not qc_passed:
        qc_metrics = []
        for idx, fail in enumerate(qc_failures):
            qc_metrics.append(
                {
                    "metric_name": f"qc_{fail['field']}" if idx > 0 or fail["field"] != "sensor_qc_ok" else "sensor_qc_ok",
                    "current_val": fail["value"] if fail["value"] is not None else 0.0,
                    "baseline_val": fail["baseline_val"],
                    "unit": fail["unit"],
                    "status_light": "INSUFFICIENT_DATA",
                    "decided_by": "quality_check",
                    "data_source": data_source,
                    "message": fail["message"],
                    "action": f"Verify and re-measure '{fail['field']}' immediately.",
                }
            )
        issue_summary = " ".join(f["message"] for f in qc_failures)
        return {
            "module_id": "musculoskeletal",
            "body_part_tag": "lower_limb_bone_muscle",
            "crew_id": crew_id,
            "mission_day": mission_day,
            "status_light": "INSUFFICIENT_DATA",
            "quality_passed": False,
            "data_source": data_source,
            "summary_note": f"Layer 0 QC Gatekeeper rejected telemetry: {issue_summary}",
            "metrics": qc_metrics,
            "guidance": {
                "how_to_measure": (
                    "1) Zero the E4D load cell with no cable tension. 2) Apply acoustic gel to Ultrasound 2 linear probe "
                    "at the pre-marked 30% proximal calf & 50% mid-thigh skin landmarks. 3) Log all required musculoskeletal "
                    "fields and verify readings sit inside physiological bounds (Calf CSA 25-200 cm^2, Thigh CSA 50-350 cm^2)."
                ),
                "plain_explanation": (
                    "Incomplete, corrupted, or implausible measurements (e.g., partial payload, 999 cm^2 ultrasound artifact, "
                    "or null biomarker/history) are blocked before evaluation so false green clearance cannot occur."
                ),
                "action_protocol": [
                    "Inspect E4D cable/load-cell connector, Ultrasound 2 probe contact, or Bio-Analyzer cartridge.",
                    "Complete missing fields and re-measure immediately (next_measurement_in_hours = 0).",
                ],
            },
            "short_term_plan": {
                "next_measurement_in_hours": 0,
                "immediate_actions": [f"Sensor QC failure: {issue_summary} Recalibrate and complete measurement immediately."],
                "urgent_alert": False,
            },
            "long_term_plan": {
                "days_until_red_prediction": None,
                "routine_prescription_adjustment": "Verify E4D, Ultrasound 2, and Bio-Analyzer calibration checklist prior to each session.",
            },
            "schedule_mutation": {
                "next_measurement_in_hours": 0,
                "prescription_adjustment": "Hold automated load progression until valid complete telemetry is logged.",
                "urgent_alert": False,
            },
        }

    # ---------------- LAYER 1-3: EVALUATE INDICATORS ----------------
    metrics: list[dict[str, Any]] = []
    dtr_candidates: list[int] = []
    clinical_statuses: list[str] = []

    # 1. E4D Bone Stimulus Index (S_bone)
    has_force, raw_pf = _resolve_alias(pay, "peak_force_n")
    has_lr, raw_lr = _resolve_alias(pay, "loading_rate_n_s")
    has_reps, raw_reps = _resolve_alias(pay, "reps")
    has_sbone, raw_sbone = _resolve_alias(pay, "s_bone", "s_bone_index")
    s_bone: float
    if has_sbone and _safe_float(raw_sbone) is not None:
        s_bone = float(raw_sbone)
    else:
        s_bone = _compute_s_bone(
            float(raw_pf),
            float(raw_lr) if has_lr and _safe_float(raw_lr) is not None else float(base["loading_rate_n_s"]),
            float(raw_reps) if has_reps and _safe_float(raw_reps) is not None else 8.0,
            float(base["peak_force_n"]),
            float(base["loading_rate_n_s"]),
        )

    if s_bone < 0.75:
        s_bone_status = "RED"
    elif s_bone < 0.90:
        s_bone_status = "YELLOW"
    else:
        s_bone_status = "GREEN"
    clinical_statuses.append(s_bone_status)
    pf_txt = f"{float(raw_pf):.0f} N" if has_force else "N/A"
    lr_txt = f"{float(raw_lr):.0f} N/s" if has_lr else "N/A"
    rep_txt = f"{int(float(raw_reps))}" if has_reps else "N/A"
    metrics.append(
        {
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
                f"Heuristic E4D Bone Stimulus Index S_bone={s_bone:.2f} "
                f"(force={pf_txt}, loading rate={lr_txt}, reps={rep_txt})."
            ),
            "action": (
                "Increase E4D squat/deadlift load +5% and use crisp concentric drive to raise loading rate."
                if s_bone_status != "GREEN"
                else "E4D osteogenic stimulus index within Z.O.S.M.A. target zone (>= 0.90)."
            ),
        }
    )

    # 2. Isometric Peak Force SRI
    iso_metric, iso_dtr = _evaluate_loss_metric(
        metric_name="iso_peak_force_n",
        history_keys=("iso_peak_force_n",),
        current_val=float(pay["iso_peak_force_n"]),
        baseline_val=float(base["iso_peak_force_n"]),
        yellow_loss_pct=10.0,
        red_loss_pct=20.0,
        unit="N",
        mission_day=mission_day,
        data_source=data_source,
        pay=pay,
        base=base,
        sample_key="iso_peak_force_n",
        horizon_days=30,
        action_nominal="Strength retention index within normal operational envelope.",
        action_abnormal="Prioritize heavy E4D isometric mid-thigh pulls & squats (+5% load if form clean).",
    )
    metrics.append(iso_metric)
    clinical_statuses.append(iso_metric["status_light"])
    if iso_dtr is not None:
        dtr_candidates.append(iso_dtr)

    # 3. VBT Squat Velocity Loss (20-30% Green, <20% Yellow under-stimulus, >30% Red set-fatigue limit)
    vbt_loss = float(pay["velocity_loss_pct"])
    if vbt_loss > 30.0:
        vbt_status = "RED"
        vbt_msg = f"E4D VBT intra-set velocity loss {vbt_loss:.1f}% EXCEEDS 30% operational set-fatigue limit."
        vbt_act = "STOP current fatigued set immediately, rest 3 min, and reduce working load 10% for remaining sets."
    elif vbt_loss < 20.0:
        vbt_status = "YELLOW"
        vbt_msg = f"E4D VBT intra-set velocity loss {vbt_loss:.1f}% < 20% optimal zone (under-stimulus)."
        vbt_act = "Increase E4D squat/deadlift load +5% or add 1-2 reps on next workout to reach 20-30% velocity loss."
    else:
        vbt_status = "GREEN"
        vbt_msg = f"E4D VBT velocity loss {vbt_loss:.1f}% inside optimal 20-30% operational window."
        vbt_act = "Maintain current E4D load and intra-set velocity target."

    metrics.append(
        {
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
    )

    # 4. Ultrasound 2 Thigh CSA (4% Yellow / 7% Red)
    thigh_metric, thigh_dtr = _evaluate_loss_metric(
        metric_name="csa_thigh_cm2",
        history_keys=("csa_thigh_cm2",),
        current_val=float(pay["csa_thigh_cm2"]),
        baseline_val=float(base["csa_thigh_cm2"]),
        yellow_loss_pct=4.0,
        red_loss_pct=7.0,
        unit="cm^2",
        mission_day=mission_day,
        data_source=data_source,
        pay=pay,
        base=base,
        sample_key="csa_thigh_cm2",
        horizon_days=30,
        action_nominal="Thigh quadriceps/hamstring cross-sectional area preserved.",
        action_abnormal="Add +5% E4D squat/deadlift load & extra posterior-chain set every 48h.",
    )
    metrics.append(thigh_metric)
    clinical_statuses.append(thigh_metric["status_light"])
    if thigh_dtr is not None:
        dtr_candidates.append(thigh_dtr)

    # 5. Ultrasound 2 Calf CSA (5% Yellow / 10% Red)
    calf_metric, calf_dtr = _evaluate_loss_metric(
        metric_name="csa_calf_cm2",
        history_keys=("csa_calf_cm2",),
        current_val=float(pay["csa_calf_cm2"]),
        baseline_val=float(base["csa_calf_cm2"]),
        yellow_loss_pct=5.0,
        red_loss_pct=10.0,
        unit="cm^2",
        mission_day=mission_day,
        data_source=data_source,
        pay=pay,
        base=base,
        sample_key="csa_calf_cm2",
        horizon_days=30,
        action_nominal="Calf soleus/gastrocnemius CSA preserved.",
        action_abnormal="Add unilateral heavy E4D calf raises (4x10) & eccentric lowering.",
    )
    metrics.append(calf_metric)
    clinical_statuses.append(calf_metric["status_light"])
    if calf_dtr is not None:
        dtr_candidates.append(calf_dtr)

    # 6. SLAMMD Body Mass (5% Yellow / 10% Red)
    mass_metric, mass_dtr = _evaluate_loss_metric(
        metric_name="body_mass_kg",
        history_keys=("body_mass_kg",),
        current_val=float(pay["body_mass_kg"]),
        baseline_val=float(base["body_mass_kg"]),
        yellow_loss_pct=5.0,
        red_loss_pct=10.0,
        unit="kg",
        mission_day=mission_day,
        data_source=data_source,
        pay=pay,
        base=base,
        sample_key="body_mass_kg",
        horizon_days=30,
        action_nominal="SLAMMD body mass & caloric balance on target.",
        action_abnormal="Increase daily caloric ration (+350 kcal/d operational target) & protein (1.4-1.7 g/kg/d).",
    )
    metrics.append(mass_metric)
    clinical_statuses.append(mass_metric["status_light"])
    if mass_dtr is not None:
        dtr_candidates.append(mass_dtr)

    # 7 & 8. Bio-Analyzer Bone Resorption: NTX & CTX
    _, raw_ntx = _resolve_alias(pay, "ntx", "ntx_nm_bce")
    ntx_metric, ntx_dtr = _evaluate_resorption_marker(
        metric_name="ntx_bone_resorption",
        payload_key="ntx",
        current_val=float(raw_ntx),
        baseline_val=float(base["ntx_nm_bce"]),
        unit="nM BCE",
        mission_day=mission_day,
        data_source=data_source,
        pay=pay,
        base=base,
        horizon_days=30,
    )
    metrics.append(ntx_metric)
    clinical_statuses.append(ntx_metric["status_light"])
    if ntx_dtr is not None:
        dtr_candidates.append(ntx_dtr)

    _, raw_ctx = _resolve_alias(pay, "ctx", "ctx_ng_ml")
    ctx_val = float(raw_ctx)
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
        horizon_days=30,
    )
    metrics.append(ctx_metric)
    clinical_statuses.append(ctx_metric["status_light"])
    if ctx_dtr is not None:
        dtr_candidates.append(ctx_dtr)

    # 9. Bio-Analyzer Bone Formation: P1NP
    _, raw_p1np = _resolve_alias(pay, "p1np", "p1np_ug_l")
    p1np_metric, p1np_dtr = _evaluate_loss_metric(
        metric_name="p1np_bone_formation",
        history_keys=("p1np", "p1np_ug_l", "p1np_bone_formation"),
        current_val=float(raw_p1np),
        baseline_val=float(base["p1np_ug_l"]),
        yellow_loss_pct=15.0,
        red_loss_pct=25.0,
        unit="ug/L",
        mission_day=mission_day,
        data_source=data_source,
        pay=pay,
        base=base,
        sample_key="p1np",
        horizon_days=30,
        action_nominal="Osteoblast bone formation marker P1NP stable.",
        action_abnormal="Combine high-impact E4D axial loading with Vitamin D3 & adequate protein intake.",
    )
    metrics.append(p1np_metric)
    clinical_statuses.append(p1np_metric["status_light"])
    if p1np_dtr is not None:
        dtr_candidates.append(p1np_dtr)

    # 10. Modeled Monthly Bone Loss Risk Estimate (heuristic from CTX & S_bone)
    ctx_ratio = ctx_val / max(float(base["ctx_ng_ml"]), 1e-6)
    resorption_excess = max(0.0, ctx_ratio - 1.0)
    unloading_deficit = max(0.0, 1.0 - s_bone)
    est_hip_loss_mo = round(min(2.5, 0.30 + 1.45 * resorption_excess + 1.35 * unloading_deficit), 2)
    est_spine_loss_mo = round(est_hip_loss_mo * (0.90 / 1.45), 2)

    if est_hip_loss_mo >= 1.4:
        bone_rate_status = "RED"
    elif est_hip_loss_mo >= 0.9:
        bone_rate_status = "YELLOW"
    else:
        bone_rate_status = "GREEN"
    clinical_statuses.append(bone_rate_status)

    metrics.append(
        {
            "metric_name": "est_monthly_bone_loss_pct",
            "current_val": est_hip_loss_mo,
            "baseline_val": 0.40,
            "delta_pct": round((est_hip_loss_mo - 0.40) * 100.0, 1),
            "slope_per_day": round(-est_hip_loss_mo / 30.0, 4),
            "unit": "%/mo",
            "status_light": bone_rate_status,
            "decided_by": "rule",
            "data_source": data_source,
            "yellow_threshold": 0.90,
            "red_threshold": 1.40,
            "lower_is_worse": False,
            "message": (
                f"Modeled bone loss risk (heuristic from CTX & S_bone, not direct DXA): "
                f"Hip ~{est_hip_loss_mo:.2f}%/mo, Spine ~{est_spine_loss_mo:.2f}%/mo "
                "(ISS reference: Spine ~0.9%/mo, Hip ~1.4-1.5%/mo; Sibonga et al.)."
            ),
            "action": (
                "Increase axial E4D resistance load & verify anti-resorptive/nutrition protocol."
                if bone_rate_status != "GREEN"
                else "Modeled bone loss risk well below ISS unmitigated benchmark."
            ),
        }
    )

    # 11. Serum Calcium & ALP vs Clinical CMP / NASA OSDR OSD-575 Reference
    # Clinical Ca/ALP evaluation ALWAYS runs first so file-load issues NEVER mask hypercalcemia or ALP >= 147 RED!
    has_ca, raw_ca = _resolve_alias(pay, "serum_ca_mg_dl")
    has_alp, raw_alp = _resolve_alias(pay, "serum_alp_u_l")
    osd_summary = _load_osd575_summary()
    ca_val = float(raw_ca) if has_ca else osd_summary["ca_mean"]
    alp_val = float(raw_alp) if has_alp else osd_summary["alp_mean"]

    if ca_val > CA_RED_HIGH:
        osd_status, osd_by = "RED", "fixed_threshold"
        osd_msg = (
            f"HYPERCALCEMIA ALERT: Serum Ca={ca_val:.2f} mg/dL (> {CA_RED_HIGH:.1f} mg/dL), ALP={alp_val:.0f} U/L "
            "— elevated renal stone & bone demineralization risk."
        )
        osd_act = "Ensure hydration >= 2.5-2.8 L/day, audit Ca/Vit D3 intake, and notify Flight Surgeon."
    elif ca_val < CA_RED_LOW:
        osd_status, osd_by = "RED", "fixed_threshold"
        osd_msg = (
            f"HYPOCALCEMIA ALERT: Serum Ca={ca_val:.2f} mg/dL (< {CA_RED_LOW:.1f} mg/dL), ALP={alp_val:.0f} U/L "
            "— neuromuscular irritability / tetany risk."
        )
        osd_act = "Evaluate Chvostek/Trousseau symptoms, check Mg/Vit D3/PTH status, and notify Flight Surgeon immediately."
    elif alp_val >= ALP_RED_HIGH:
        osd_status, osd_by = "RED", "fixed_threshold"
        osd_msg = (
            f"ELEVATED ALP ALERT: Serum ALP={alp_val:.0f} U/L (>= {ALP_RED_HIGH:.0f} U/L Red limit), "
            f"Ca={ca_val:.2f} mg/dL — high bone turnover / hepatobiliary stress."
        )
        osd_act = "Repeat full CMP & liver/bone isoenzyme check within 24h and notify Flight Surgeon."
    elif ca_val >= CA_YELLOW_HIGH or ca_val < CA_YELLOW_LOW or alp_val >= ALP_YELLOW_HIGH:
        osd_status, osd_by = "YELLOW", "fixed_threshold"
        direction = "low" if ca_val < CA_YELLOW_LOW else "elevated"
        osd_msg = (
            f"Serum Ca={ca_val:.2f} mg/dL ({direction}), ALP={alp_val:.0f} U/L outside optimal CMP envelope "
            f"(Ca {CA_YELLOW_LOW:.1f}-{CA_YELLOW_HIGH:.1f} mg/dL, ALP < {ALP_YELLOW_HIGH:.0f} U/L)."
        )
        osd_act = "Maintain hydration >= 2.5 L/day and repeat Bio-Analyzer CMP panel in 72h."
    elif (
        osd_summary["data_source"] == "REAL"
        and osd_summary.get("ca_sd")
        and abs(ca_val - osd_summary["ca_mean"]) > 2.0 * float(osd_summary["ca_sd"])
    ):
        osd_status, osd_by = "YELLOW", "baseline"
        osd_msg = (
            f"Serum Ca={ca_val:.2f} mg/dL deviates >2 SD from real OSD-575 cohort "
            f"({osd_summary['ca_mean']:.2f} +/- {osd_summary['ca_sd']:.2f} mg/dL)."
        )
        osd_act = "Repeat Bio-Analyzer CMP panel in 72h to verify trend against OSD-575 baseline."
    else:
        osd_status, osd_by = "GREEN", "rule"
        osd_msg = (
            f"Serum Ca={ca_val:.2f} mg/dL & ALP={alp_val:.0f} U/L within clinical CMP range "
            f"({osd_summary['source_file']}: mean Ca {osd_summary['ca_mean']:.2f} mg/dL, ALP {osd_summary['alp_mean']:.0f} U/L)."
        )
        osd_act = "Serum Calcium and ALP stable."

    if osd_summary.get("load_error"):
        osd_msg += f" [Note: OSD-575 reference file warning: {osd_summary['load_error']}]"

    clinical_statuses.append(osd_status)
    metrics.append(
        {
            "metric_name": "osd575_ca_alp_baseline",
            "current_val": round(ca_val, 2),
            "baseline_val": osd_summary["ca_mean"],
            "delta_pct": round(((ca_val - osd_summary["ca_mean"]) / max(osd_summary["ca_mean"], 1e-6)) * 100.0, 1),
            "slope_per_day": 0.0,
            "unit": "mg/dL",
            "status_light": osd_status,
            "decided_by": osd_by,
            "data_source": data_source,
            "ref_data_source": osd_summary["data_source"],
            "ref_load_error": osd_summary.get("load_error"),
            "yellow_threshold": CA_YELLOW_HIGH,
            "red_threshold": CA_RED_HIGH,
            "lower_is_worse": False,
            "message": osd_msg,
            "action": osd_act,
        }
    )

    # ---------------- OVERALL STATUS & CLOSED-LOOP SCHEDULE ----------------
    # Isolated single-set VBT fatigue (>30% or <20%) produces coaching feedback without
    # turning the entire body-map HUD RED or paging Flight Surgeon when clinical/structural metrics are intact.
    clinical_worst = _worst(clinical_statuses)
    isolated_vbt_red = (vbt_status == "RED" and clinical_worst != "RED")
    isolated_vbt_yellow = (vbt_status == "YELLOW" and clinical_worst == "GREEN")

    if clinical_worst == "RED":
        overall = "RED"
        next_hours = 24
        urgent_alert = True
        immediate_actions = [
            "Alert Flight Surgeon / ground medical team and log acute musculoskeletal red-flag event.",
            "STOP any E4D set exceeding 30% VBT velocity loss; shift to controlled hypertrophy (cap VBT <= 25%) after Cardio/Immune clearance.",
            "Verify hydration >= 2.5-2.8 L/day, protein >= 1.6 g/kg/day, and Vitamin D3 (800-1000 IU/d target); repeat Ultrasound 2 scan within 24h.",
        ]
        long_adj = (
            "24h medical alert + 4-week progressive lower-limb hypertrophy block, caloric/protein support, "
            "and 14-day Bio-Analyzer CTX/NTX & Ultrasound CSA re-evaluation."
        )
    elif isolated_vbt_red:
        overall = "YELLOW"  # Single-set coaching caution on dashboard; velocity_loss_pct metric itself remains RED
        next_hours = 48
        urgent_alert = False
        immediate_actions = [
            "STOP current fatigued E4D set immediately (VBT > 30%), rest 3 min, and drop working load 10% for remaining sets.",
            "Structural CSA and bone biomarkers remain non-RED; re-verify VBT on next scheduled E4D session (48h).",
        ]
        long_adj = "Reduce E4D working load 5-10% next session to keep intra-set velocity loss inside 20-30%."
    elif clinical_worst == "YELLOW":
        overall = "YELLOW"
        next_hours = 72
        urgent_alert = False
        immediate_actions = [
            "Increase E4D squat/deadlift load +5% with faster concentric loading rate to push S_bone >= 0.90 and VBT loss into 20-30%.",
            "Add 1 extra unilateral heel-raise / posterior-chain set and confirm protein >= 1.4-1.7 g/kg/day.",
            "Schedule follow-up Ultrasound 2 thigh/calf & E4D check in 72 hours.",
        ]
        long_adj = "+5% E4D squat/deadlift load progression with higher loading rate; repeat Ultrasound CSA & bone markers in 72h-7d."
    elif isolated_vbt_yellow:
        overall = "YELLOW"
        next_hours = 168
        urgent_alert = False
        immediate_actions = [
            "Increase E4D squat/deadlift load +5% on next scheduled workout to lift intra-set VBT loss from <20% into the 20-30% target zone.",
            "Structural CSA and bone biomarkers remain GREEN; keep standard 168h diagnostic cadence.",
        ]
        long_adj = "Progress E4D working load +5% on next workout while keeping weekly (168h) Ultrasound/biomarker schedule."
    else:
        overall = "GREEN"
        next_hours = 168
        urgent_alert = False
        immediate_actions = [
            "Continue nominal 6-day/week E4D resistance & CEVIS countermeasure schedule; keep VBT loss in 20-30% window."
        ]
        long_adj = "Maintain current E4D progressive resistance schedule (weekly 168h verification)."

    days_until_red: Optional[int] = 0 if overall == "RED" else (min(dtr_candidates) if dtr_candidates else None)

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
            f"Modeled Hip Loss={est_hip_loss_mo:.2f}%/mo."
            + (" [Single-set VBT >30% coaching caution]" if isolated_vbt_red else "")
        ),
        "metrics": metrics,
        "guidance": {
            "how_to_measure": (
                "1) Attach E4D VBT linear encoder & zero the load cell; log squat peak force, loading rate, reps, "
                "and intra-set velocity loss. 2) Scan pre-marked 50% mid-thigh & 30% proximal calf landmarks with "
                "Ultrasound 2. 3) Record morning SLAMMD body mass and run Bio-Analyzer NTX/CTX/P1NP cartridge."
            ),
            "plain_explanation": (
                "Without Earth's 1g gravity, weight-bearing leg muscles rapidly atrophy and bone calcium leaches into "
                "blood (raising fracture and kidney-stone risk before landing). Tracking E4D mechanical loading, "
                "muscle CSA, and bone turnover keeps countermeasures effective offline."
            ),
            "action_protocol": immediate_actions,
        },
        "short_term_plan": {
            "next_measurement_in_hours": next_hours,
            "immediate_actions": immediate_actions,
            "urgent_alert": urgent_alert,
        },
        "long_term_plan": {
            "days_until_red_prediction": days_until_red,
            "routine_prescription_adjustment": long_adj,
        },
        "schedule_mutation": {
            "next_measurement_in_hours": next_hours,
            "prescription_adjustment": long_adj,
            "urgent_alert": urgent_alert,
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
    """Return interactive Plotly figure of 3-scenario Calf CSA & NTX trajectories with matching thresholds."""
    if go is None or make_subplots is None:
        raise ImportError("plotly is required to build musculoskeletal figures.")

    base = demo_baseline()
    calf_base = float(base["csa_calf_cm2"])
    ntx_base = float(base["ntx_nm_bce"])
    ntx_sd_eff, ntx_mean = _baseline_sd_with_floor(base, "ntx", ntx_base, min_floor_pct=0.05)
    ntx_yellow = round(ntx_mean + 2.0 * ntx_sd_eff, 2)

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
    fig.add_hline(y=ntx_yellow, line_dash="dash", line_color="#eab308", annotation_text=f"+2 SD Yellow ({ntx_yellow:.1f})", row=1, col=2)
    fig.add_hline(y=ntx_base * 1.50, line_dash="dash", line_color="#ef4444", annotation_text="+50% Red", row=1, col=2)

    fig.update_layout(
        template="plotly_dark",
        height=380,
        title="Musculoskeletal 3-Scenario Simulated Trajectories",
        legend=dict(orientation="h", y=-0.2),
    )
    return fig


def build_iss_comparison_figure(eval_result: Optional[dict[str, Any]] = None) -> Any:
    """Compare modeled bone-loss risk estimate against published ISS Spine & Hip reference benchmarks."""
    if go is None:
        raise ImportError("plotly is required to build musculoskeletal figures.")

    res = eval_result or evaluate(demo_payload("green"))
    trend = res.get("trend_series", {})
    hip_rate = float(trend.get("est_monthly_bone_loss_hip_pct") or 0.40)
    spine_rate = float(trend.get("est_monthly_bone_loss_spine_pct") or 0.25)

    fig = go.Figure(
        data=[
            go.Bar(
                name="Modeled Risk Estimate (from CTX & S_bone)",
                x=["Lumbar Spine (%/mo)", "Proximal Hip (%/mo)"],
                y=[spine_rate, hip_rate],
                marker_color="#38bdf8",
            ),
            go.Bar(
                name="Published ISS Unmitigated Ref (Sibonga et al.)",
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
        title="Modeled Monthly Bone Loss Risk vs. Published ISS Reference Rates (Not Direct DXA)",
        yaxis_title="Bone Mineral Loss Rate (%/month)",
    )
    return fig


def build_osd575_baseline_figure() -> Any:
    """Plot Serum Calcium & ALP against OSD-575 (if present) or synthetic CMP clinical fallback."""
    if go is None or make_subplots is None:
        raise ImportError("plotly is required to build musculoskeletal figures.")

    osd = _load_osd575_summary()
    idx = list(range(1, len(osd["ca_series"]) + 1))
    src_label = "REAL OSD-575" if osd["data_source"] == "REAL" else "SIMULATED CMP FALLBACK"

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            f"Serum Calcium ({src_label})",
            f"Alkaline Phosphatase ({src_label})",
        ),
    )
    fig.add_trace(
        go.Bar(x=idx, y=osd["ca_series"], name="Calcium (mg/dL)", marker_color="#38bdf8"),
        row=1,
        col=1,
    )
    fig.add_hline(y=CA_RED_HIGH, line_dash="dash", line_color="#ef4444", annotation_text=f"Red High {CA_RED_HIGH}", row=1, col=1)
    fig.add_hline(y=CA_YELLOW_HIGH, line_dash="dot", line_color="#eab308", annotation_text=f"Yellow High {CA_YELLOW_HIGH}", row=1, col=1)
    fig.add_hline(y=CA_YELLOW_LOW, line_dash="dot", line_color="#eab308", annotation_text=f"Yellow Low {CA_YELLOW_LOW}", row=1, col=1)
    fig.add_hline(y=CA_RED_LOW, line_dash="dash", line_color="#ef4444", annotation_text=f"Red Low {CA_RED_LOW}", row=1, col=1)

    fig.add_trace(
        go.Bar(x=idx, y=osd["alp_series"], name="ALP (U/L)", marker_color="#a855f7"),
        row=1,
        col=2,
    )
    fig.add_hline(y=ALP_YELLOW_HIGH, line_dash="dot", line_color="#eab308", annotation_text=f"Yellow {ALP_YELLOW_HIGH:.0f}", row=1, col=2)
    fig.add_hline(y=ALP_RED_HIGH, line_dash="dash", line_color="#ef4444", annotation_text=f"Red {ALP_RED_HIGH:.0f}", row=1, col=2)
    fig.update_layout(template="plotly_dark", height=340, title=f"Serum Ca & ALP Baseline Check ({src_label})")
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
        for p in export_demo_csvs():
            print(f"  Exported: {p}")
    else:
        print(f"Present files: {folder_info['present_files']}")

    # 1. Core 4 scenarios
    for scen in ("green", "yellow", "red", "bad_data"):
        raw = evaluate(demo_payload(scen))
        validated = to_schema(raw)
        assert validated.module_id == "musculoskeletal"
        assert validated.body_part_tag == "lower_limb_bone_muscle"
        if scen == "bad_data":
            assert validated.quality_passed is False
            assert validated.short_term_plan.next_measurement_in_hours == 0
            assert any(m.metric_name == "qc_csa_calf_cm2" for m in validated.metrics)
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
            bone_m = next(m for m in validated.metrics if m.metric_name == "est_monthly_bone_loss_pct")
            assert bone_m.status_light == "RED"
        print(
            f"[{scen.upper():8s}] status={validated.status_light:6s} | raw={validated.raw_status:17s} | "
            f"qc={str(validated.quality_passed):5s} | next={validated.short_term_plan.next_measurement_in_hours:3d}h | "
            f"urgent={str(validated.short_term_plan.urgent_alert):5s} | {raw['summary_note']}"
        )

    # 2. Partial payloads & None/NaN history tests
    empty_res = to_schema(evaluate({}))
    assert empty_res.quality_passed is False and empty_res.raw_status == "INSUFFICIENT_DATA"

    partial_res = to_schema(evaluate({"body_mass_kg": 73.5}))
    assert partial_res.quality_passed is False and partial_res.short_term_plan.next_measurement_in_hours == 0

    partial_vbt = to_schema(evaluate({"velocity_loss_pct": 24.0}))
    assert partial_vbt.quality_passed is False and partial_vbt.short_term_plan.next_measurement_in_hours == 0

    bad_hist = demo_payload("green")
    bad_hist["history_series"]["csa_thigh_cm2"] = [147.6, None, 146.8, 146.4]
    bad_hist_res = to_schema(evaluate(bad_hist))
    assert bad_hist_res.quality_passed is False

    # 3. ALP >= 147 RED & Hypercalcemia NOT masked by OSD-575 load error
    alp_red_res = to_schema(evaluate({**demo_payload("green"), "serum_alp_u_l": 200.0}))
    assert alp_red_res.status_light == "RED"

    # 4. Layer 2 personal baseline trigger (tight personal SD) vs Layer 1 fixed thresholds
    tight_base = demo_baseline()
    tight_base["preflight_samples"]["csa_thigh_cm2"] = [147.8, 148.0, 148.2]  # SD=0.2, 1.5% floor => -3.0% Yellow
    l2_res = to_schema(evaluate({**demo_payload("green"), "csa_thigh_cm2": 143.5}, baseline=tight_base))  # -3.04%
    thigh_l2 = next(m for m in l2_res.metrics if m.metric_name == "csa_thigh_cm2")
    assert thigh_l2.status_light == "YELLOW" and thigh_l2.decided_by == "baseline"

    # 5. Layer 3 Trend Projection on realistic 30-day cadence (<=5%/mo loss)
    trend_30d = demo_payload("green")
    trend_30d["mission_day"] = 120
    trend_30d["history_days"] = [30, 60, 90, 120]
    trend_30d["history_series"]["csa_thigh_cm2"] = [160.0, 154.5, 148.8, 142.8]  # -3.5% current (L1/L2 GREEN), ~-3.9%/mo slope -> RED in 27d
    trend_30d["csa_thigh_cm2"] = 142.8
    trend_30d_res = to_schema(evaluate(trend_30d))
    thigh_l3 = next(m for m in trend_30d_res.metrics if m.metric_name == "csa_thigh_cm2")
    assert thigh_l3.status_light == "YELLOW" and thigh_l3.decided_by == "trend"

    # 6. Isolated VBT >30% set fatigue: metric is RED, module HUD stays YELLOW & urgent_alert=False
    vbt_only = to_schema(evaluate(demo_payload("green"), manual_overrides={"velocity_loss_pct": 34.0}))
    vbt_m = next(m for m in vbt_only.metrics if m.metric_name == "velocity_loss_pct")
    assert vbt_m.status_light == "RED"
    assert vbt_only.status_light == "YELLOW" and vbt_only.short_term_plan.urgent_alert is False

    # 7. Demo CSVs loaded through data_loader remain labeled SIMULATED (never falsely REAL)
    from core.data_loader import load_module_files_into_payload
    csv_pay, csv_base, _ = load_module_files_into_payload("musculoskeletal")
    csv_res = to_schema(evaluate(csv_pay, baseline=csv_base))
    assert csv_res.quality_passed is True and csv_res.data_source == "SIMULATED"

    # 8. Plotly figure helpers
    assert build_trajectory_figure() is not None
    assert build_iss_comparison_figure() is not None
    assert build_osd575_baseline_figure() is not None

    print("ALL EXPANDED MUSCULOSKELETAL TESTS PASSED.")
