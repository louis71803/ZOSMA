"""Role 2: Musculoskeletal (Bone & Muscle) Domain Module for Team Z.O.S.M.A.

Self-contained stateless evaluator implementing Layer 0 QC + 3-Layer Decision Model:
- Layer 0: Sensor, Missing-Field, History & Physiological Plausibility QC Gatekeeper
- Layer 1: Z.O.S.M.A. Operational & Clinical Thresholds
- Layer 2: Personal Pre-Flight Baseline (+/- 2 SD; 5% SD floor on NTX/CTX)
- Layer 3: 4-Point Trend Slope Projection (upgrades GREEN -> YELLOW if RED projected
           within the next 30-day scheduled monitoring cycle)

Hardware Context:
- European multi-purpose exercise device E4D, launched to the ISS for testing in April 2026.

Scientific Literature & Threshold Provenance:
- Tagged strictly using four provenance categories: `NASA`, `ISS_study`, `other_literature`, `team_spec`.
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

# Provenance tags strictly restricted to four labels:
# "NASA" | "ISS_study" | "other_literature" | "team_spec"
REFERENCES: dict[str, dict[str, Any]] = {
    "e4d_hardware": {
        "provenance": "NASA",
        "description": "European multi-purpose exercise device E4D, launched to the ISS for testing in April 2026.",
    },
    "bone_loss_iss_avg": {
        "provenance": "NASA",
        "citation": "NASA Human Research Program / Spaceflight Bone Loss Overview",
        "covers": "Average spaceflight bone mineral density loss 1.0-1.5%/month.",
    },
    "strength_avg_loss": {
        "provenance": "NASA",
        "covers": "Average strength loss under microgravity 10-12%.",
    },
    "nutrition_hydration": {
        "provenance": "NASA",
        "citation": "NASA-STD-3001 Vol 2",
        "covers": "Vitamin D 35-90 ng/mL reference range, protein 1.2-1.8 g/kg/day, Vitamin D 1000 IU/day, daily urine output >= 2 L/day.",
    },
    "iss_site_bone_muscle_resorption": {
        "provenance": "ISS_study",
        "citation": "LeBlanc et al. (2000), JBMR; Sibonga et al. (2007), Bone 41(6):973-983; Trappe et al. (2009), J Appl Physiol; Smith et al. (2005, 2012), JBMR.",
        "covers": "Thigh CSA 4%/7%, Calf CSA 5%/10%, isometric strength thresholds (<5%/5-10%/>10%), bone resorption +50%, lumbar spine 0.9%/mo and proximal hip 1.4-1.5%/mo.",
    },
    "vbt_and_body_mass": {
        "provenance": "other_literature",
        "citation": "Pareja-Blanco et al. (2017), Scand J Med Sci Sports 27(7):724-735; clinical nutritional anthropometry.",
        "covers": "Intra-set velocity loss 30% upper fatigue limit; SLAMMD body mass loss 5%/10%.",
    },
    "team_operational_specs": {
        "provenance": "team_spec",
        "covers": (
            "E4D Bone Stimulus Index (S_bone) and 0.90/0.75 thresholds; VBT 20% lower stimulus limit; "
            "modeled monthly bone loss risk formula (0.30 + 1.45*resorption_excess + 1.35*unloading_deficit) "
            "and <1.0 / 1.0-1.5 / >1.5%/mo thresholds; +5% E4D load progression; recheck intervals "
            "(168h/72h/24h for E4D/isometric/body mass, minimum 7d for ultrasound CSA, minimum 14d for bone markers); "
            "isometric mid-thigh pull 3-rep max protocol."
        ),
    },
    "osd575_limitation": {
        "provenance": "NASA",
        "citation": "NASA OSDR OSD-575 (Inspiration4 CMP).",
        "covers": "OSD-575 is blood chemistry from the 3-day Inspiration4 mission; it serves only as baseline blood reference and cannot validate long-duration musculoskeletal loss.",
    },
}

# Re-test minimum intervals (team_spec)
RETEST_MIN_INTERVALS_HOURS: dict[str, int] = {
    "e4d_isometric_mass": 24,
    "ultrasound_csa_min_days": 7,
    "bone_markers_min_days": 14,
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

# Built-in reference CMP cohort used ONLY when real NASA OSDR OSD-575_cmp.csv is absent
SIMULATED_CMP_FALLBACK: list[dict[str, Any]] = [
    {"subject_id": "REF_01", "timepoint": "Reference_Preflight", "calcium_mg_dl": 9.3, "alp_u_l": 64.0},
    {"subject_id": "REF_02", "timepoint": "Reference_Preflight", "calcium_mg_dl": 9.5, "alp_u_l": 71.0},
    {"subject_id": "REF_03", "timepoint": "Reference_Preflight", "calcium_mg_dl": 9.2, "alp_u_l": 66.0},
    {"subject_id": "REF_04", "timepoint": "Reference_Preflight", "calcium_mg_dl": 9.6, "alp_u_l": 75.0},
]

# Fixed canonical UI-matched strings (kept static for exact dictionary matching)
QC_INVALID_GUIDANCE_TEXT = (
    "Invalid measurement. Check probe contact and load-cell zeroing, then re-measure immediately."
)
URGENT_REPORT_LINE = "Urgent escalation: Report to ground at the next communication pass."
SERUM_CA_REFERENCE_MSG = (
    "Serum calcium remains stable during flight; basic check only and does not reflect bone loss severity."
)
P1NP_REFERENCE_MSG = "Reference value only; not used for status light evaluation."
RECHECK_IMMEDIATE_ULTRASOUND_LINE = (
    "Re-measure once immediately to rule out measurement error; then follow up during weekly routine checks."
)
REF_TEXT_VBT = "Target range 20-30%"
REF_TEXT_SBONE = "Target >= 0.90"
REF_TEXT_BONE_LOSS = "ISS average 1.0-1.5%/mo"

# 4-group 3-step Crew Guidance templates (strictly matching specification numbers & units)
GUIDANCE_GROUPS: dict[str, dict[str, Any]] = {
    "training": {
        "how_to_measure": (
            "1) Push with maximum effort on every repetition during resistance training; E4D automatically records force and velocity for each rep. "
            "2) Velocity loss equals the percentage drop in mean velocity from the fastest rep to the last rep in each set. "
            "3) Isometric strength: once per week, pull maximally against the fixed bar for 3 repetitions and take the maximum value."
        ),
        "plain_explanation": (
            "In microgravity, muscle strength drops by an average of 10%-12%, and about 12%-38% of crewmembers lose more than 20%, "
            "impairing EVA capability and post-landing mobility. Resistance training is the primary countermeasure, "
            "and intensity matters more than repetition count."
        ),
        "actions": {
            "yellow": "Complete full range of motion, push every rep maximally, and finish any incomplete sets for this week.",
            "red": "Starting from the next workout, increase squat, deadlift, and calf-raise load by approximately +5%.",
            "vbt_over_30": "Stop the fatigued set immediately today and switch to recovery training.",
            "iso_over_20": "Report to ground at the next communication pass.",
        },
    },
    "csa": {
        "how_to_measure": (
            "1) Once per week, scan the quadriceps and gastrocnemius using Ultrasound 2 in panoramic mode. "
            "2) Use the pre-flight positioning template selected by leg length and sweep the probe smoothly along the template in one pass. "
            "3) Repeat 3 times at the same site and average the values. Calf readings have higher variance; follow the trend rather than a single scan."
        ),
        "plain_explanation": (
            "After about 6 months on the ISS, crew lost 10%-16% of calf muscle volume and 4%-7% of thigh volume (MRI study of 4 crewmembers). "
            "Lower-limb muscle loss increases the risk of falls and injury after landing."
        ),
        "actions": {
            "yellow": "Confirm training targets are met; consume 1.2-1.8 g protein per kg body mass daily with adequate calories.",
            "red": "Starting from the next workout, increase lower-limb load by approximately +5% and add 1 set of calf raises.",
            "sudden_change": "Re-measure once immediately to rule out measurement error; then follow up during weekly routine checks.",
        },
    },
    "body_mass": {
        "how_to_measure": (
            "1) Measure at the same time of day each session. "
            "2) Wrap legs and torso securely around the SLAMMD mount and remain still. "
            "3) Record the spring-driven readout and average consecutive measurements."
        ),
        "plain_explanation": (
            "Body mass loss is usually caused by insufficient caloric intake. "
            "A 5%-10% loss requires attention, and over 10% is critical."
        ),
        "actions": {
            "yellow": "Log dietary intake for 3 days and add high-calorie foods.",
            "red": "Report to ground at the next communication pass so the medical team can adjust nutrition.",
        },
    },
    "bone_metabolism": {
        "how_to_measure": (
            "1) Draw fasting blood in the morning; sample at the same time of day each session for comparability. "
            "2) Bone loss rate is a modeled estimate: BMD cannot be measured directly in flight and is confirmed post-flight by DXA. "
            "3) Note: On the ISS, samples are frozen and returned to Earth for analysis; onboard real-time testing is a planned feature of this system."
        ),
        "plain_explanation": (
            "In microgravity, bone resorption increases by about 50% and bone mineral density declines by an average of 1%-1.5% per month, "
            "most prominently at the hip. Lost bone calcium is excreted in urine (serum calcium remains normal), increasing kidney stone risk."
        ),
        "actions": {
            "yellow": "Confirm resistance training targets are met; take Vitamin D 1000 IU daily; hydrate to maintain daily urine output above 2 L.",
            "red": "Report to ground at the next communication pass for flight surgeon medication decision; increase monitoring frequency.",
        },
    },
}

COMBINED_HOW_TO_MEASURE = (
    "[Training] " + GUIDANCE_GROUPS["training"]["how_to_measure"] + " | "
    "[Muscle CSA] " + GUIDANCE_GROUPS["csa"]["how_to_measure"] + " | "
    "[Body Mass] " + GUIDANCE_GROUPS["body_mass"]["how_to_measure"] + " | "
    "[Bone Metabolism] " + GUIDANCE_GROUPS["bone_metabolism"]["how_to_measure"]
)

COMBINED_PLAIN_EXPLANATION = (
    "[Training] " + GUIDANCE_GROUPS["training"]["plain_explanation"] + " | "
    "[Muscle CSA] " + GUIDANCE_GROUPS["csa"]["plain_explanation"] + " | "
    "[Body Mass] " + GUIDANCE_GROUPS["body_mass"]["plain_explanation"] + " | "
    "[Bone Metabolism] " + GUIDANCE_GROUPS["bone_metabolism"]["plain_explanation"]
)


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
            "iso_peak_force_n": 1700.0,  # -8.11% strength loss (YELLOW 5-10%)
            "csa_thigh_cm2": 140.5,      # -5.1% loss (YELLOW >= 4%)
            "csa_calf_cm2": 77.2,       # -5.9% loss (YELLOW >= 5%)
            "body_mass_kg": 69.8,       # -5.7% loss (YELLOW >= 5%)
            "ntx": 18.6,                # +32.9% elevation (YELLOW)
            "ctx": 0.49,                # +36.1% elevation (YELLOW)
            "p1np": 37.5,               # -16.7% (REFERENCE only)
            "serum_ca_mg_dl": 9.5,
            "serum_alp_u_l": 70.0,
            "history_days": [30, 60, 90, 124],
            "history_series": {
                "csa_thigh_cm2": [146.5, 144.8, 142.6, 140.5],
                "csa_calf_cm2": [81.0, 79.8, 78.5, 77.2],
                "iso_peak_force_n": [1810.0, 1775.0, 1735.0, 1700.0],
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
            "iso_peak_force_n": 1440.0,  # -22.16% strength loss (RED > 10%, triggers urgent report > 20%)
            "csa_thigh_cm2": 136.0,     # -8.1% loss (RED >= 7%)
            "csa_calf_cm2": 73.0,      # -11.0% loss (RED >= 10%)
            "body_mass_kg": 66.0,      # -10.81% loss (RED > 10%, triggers urgent report)
            "ntx": 22.8,               # +62.9% elevation (RED >= +50%)
            "ctx": 0.58,               # +61.1% elevation (RED >= +50%)
            "p1np": 32.5,              # -27.8% (REFERENCE only)
            "serum_ca_mg_dl": 9.6,
            "serum_alp_u_l": 72.0,
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
        "source_file": "Built-in reference (non-NASA data)",
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
                "how_to_measure": QC_INVALID_GUIDANCE_TEXT,
                "plain_explanation": QC_INVALID_GUIDANCE_TEXT,
                "action_protocol": [QC_INVALID_GUIDANCE_TEXT],
            },
            "short_term_plan": {
                "next_measurement_in_hours": 0,
                "immediate_actions": [QC_INVALID_GUIDANCE_TEXT],
                "urgent_alert": False,
            },
            "long_term_plan": {
                "days_until_red_prediction": None,
                "routine_prescription_adjustment": QC_INVALID_GUIDANCE_TEXT,
            },
            "schedule_mutation": {
                "next_measurement_in_hours": 0,
                "prescription_adjustment": QC_INVALID_GUIDANCE_TEXT,
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
            "baseline_val": None,
            "delta_pct": None,
            "slope_per_day": 0.0,
            "unit": "index",
            "status_light": s_bone_status,
            "decided_by": "fixed_threshold",
            "data_source": data_source,
            "yellow_threshold": 0.90,
            "red_threshold": 0.75,
            "lower_is_worse": True,
            "message": REF_TEXT_SBONE,
            "action": (
                GUIDANCE_GROUPS["training"]["actions"]["red"]
                if s_bone_status == "RED"
                else (
                    GUIDANCE_GROUPS["training"]["actions"]["yellow"]
                    if s_bone_status == "YELLOW"
                    else "Follow current prescription."
                )
            ),
        }
    )

    # 2. Isometric Peak Force SRI (<5% Green, 5-10% Yellow, >10% Red)
    iso_metric, iso_dtr = _evaluate_loss_metric(
        metric_name="iso_peak_force_n",
        history_keys=("iso_peak_force_n",),
        current_val=float(pay["iso_peak_force_n"]),
        baseline_val=float(base["iso_peak_force_n"]),
        yellow_loss_pct=5.0,
        red_loss_pct=10.0,
        unit="N",
        mission_day=mission_day,
        data_source=data_source,
        pay=pay,
        base=base,
        sample_key="iso_peak_force_n",
        horizon_days=30,
        action_nominal="Follow current prescription.",
        action_abnormal=GUIDANCE_GROUPS["training"]["actions"]["red"],
    )
    metrics.append(iso_metric)
    clinical_statuses.append(iso_metric["status_light"])
    if iso_dtr is not None:
        dtr_candidates.append(iso_dtr)

    # 3. VBT Squat Velocity Loss (20-30% Green, <20% Yellow under-stimulus, >30% Red set-fatigue limit)
    vbt_loss = float(pay["velocity_loss_pct"])
    if vbt_loss > 30.0:
        vbt_status = "RED"
        vbt_act = GUIDANCE_GROUPS["training"]["actions"]["vbt_over_30"]
    elif vbt_loss < 20.0:
        vbt_status = "YELLOW"
        vbt_act = GUIDANCE_GROUPS["training"]["actions"]["yellow"]
    else:
        vbt_status = "GREEN"
        vbt_act = "Follow current prescription."

    metrics.append(
        {
            "metric_name": "velocity_loss_pct",
            "current_val": round(vbt_loss, 1),
            "baseline_val": None,
            "delta_pct": None,
            "slope_per_day": 0.0,
            "unit": "%",
            "status_light": vbt_status,
            "decided_by": "fixed_threshold",
            "data_source": data_source,
            "yellow_threshold": 20.0,
            "red_threshold": 30.0,
            "lower_is_worse": False,
            "message": REF_TEXT_VBT,
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

    # 9. Bio-Analyzer Bone Formation: P1NP (A8: preserve value & delta_pct, REFERENCE only, never affects status_light)
    _, raw_p1np = _resolve_alias(pay, "p1np", "p1np_ug_l")
    p1np_val = float(raw_p1np)
    p1np_base = float(base["p1np_ug_l"])
    p1np_delta_pct = round(((p1np_val - p1np_base) / max(p1np_base, 1e-6)) * 100.0, 2)
    p1np_days, p1np_vals, p1np_hist_src = _extract_history(
        pay, ("p1np", "p1np_ug_l", "p1np_bone_formation"), p1np_val, p1np_base, mission_day
    )
    p1np_slope = _compute_slope(p1np_days, p1np_vals)
    p1np_metric = {
        "metric_name": "p1np_bone_formation",
        "current_val": round(p1np_val, 2),
        "baseline_val": round(p1np_base, 2),
        "delta_pct": p1np_delta_pct,
        "slope_per_day": p1np_slope,
        "unit": "ug/L",
        "status_light": "GREEN",
        "raw_status": "REFERENCE",
        "decided_by": "rule",
        "data_source": data_source,
        "yellow_threshold": None,
        "red_threshold": None,
        "lower_is_worse": False,
        "history_days": p1np_days,
        "history_values": p1np_vals,
        "history_source": p1np_hist_src,
        "message": P1NP_REFERENCE_MSG,
        "action": P1NP_REFERENCE_MSG,
    }
    metrics.append(p1np_metric)

    # 10. Modeled Monthly Bone Loss Risk Estimate (heuristic from CTX & S_bone; <1.0 Green, 1.0-1.5 Yellow, >1.5 Red)
    ctx_ratio = ctx_val / max(float(base["ctx_ng_ml"]), 1e-6)
    resorption_excess = max(0.0, ctx_ratio - 1.0)
    unloading_deficit = max(0.0, 1.0 - s_bone)
    est_hip_loss_mo = round(min(2.5, 0.30 + 1.45 * resorption_excess + 1.35 * unloading_deficit), 2)
    est_spine_loss_mo = round(est_hip_loss_mo * (0.90 / 1.45), 2)

    if est_hip_loss_mo > 1.5:
        bone_rate_status = "RED"
    elif est_hip_loss_mo >= 1.0:
        bone_rate_status = "YELLOW"
    else:
        bone_rate_status = "GREEN"
    clinical_statuses.append(bone_rate_status)

    metrics.append(
        {
            "metric_name": "est_monthly_bone_loss_pct",
            "current_val": est_hip_loss_mo,
            "baseline_val": None,
            "delta_pct": None,
            "slope_per_day": round(-est_hip_loss_mo / 30.0, 4),
            "unit": "%/mo",
            "status_light": bone_rate_status,
            "decided_by": "rule",
            "data_source": data_source,
            "yellow_threshold": 1.0,
            "red_threshold": 1.5,
            "lower_is_worse": False,
            "message": REF_TEXT_BONE_LOSS,
            "action": (
                GUIDANCE_GROUPS["bone_metabolism"]["actions"]["red"]
                if bone_rate_status == "RED"
                else (
                    GUIDANCE_GROUPS["bone_metabolism"]["actions"]["yellow"]
                    if bone_rate_status == "YELLOW"
                    else "Follow current prescription."
                )
            ),
        }
    )

    # 11. Serum Calcium & ALP (A6: reference only, never affects status_light; A7: label real OSD-575 only when CSV exists)
    has_ca, raw_ca = _resolve_alias(pay, "serum_ca_mg_dl")
    has_alp, raw_alp = _resolve_alias(pay, "serum_alp_u_l")
    osd_summary = _load_osd575_summary()
    ca_val = float(raw_ca) if has_ca else osd_summary["ca_mean"]
    alp_val = float(raw_alp) if has_alp else osd_summary["alp_mean"]
    ref_display_name = (
        "NASA OSDR OSD-575"
        if osd_summary["data_source"] == "REAL"
        else "Built-in reference (non-NASA data)"
    )

    metrics.append(
        {
            "metric_name": "osd575_ca_alp_baseline",
            "display_name": ref_display_name,
            "current_val": round(ca_val, 2),
            "baseline_val": osd_summary["ca_mean"],
            "delta_pct": round(((ca_val - osd_summary["ca_mean"]) / max(osd_summary["ca_mean"], 1e-6)) * 100.0, 1),
            "slope_per_day": 0.0,
            "unit": "mg/dL",
            "status_light": "GREEN",
            "raw_status": "REFERENCE",
            "decided_by": "rule",
            "data_source": data_source,
            "ref_data_source": osd_summary["data_source"],
            "ref_display_name": ref_display_name,
            "ref_load_error": osd_summary.get("load_error"),
            "alp_val": round(alp_val, 1),
            "yellow_threshold": None,
            "red_threshold": None,
            "lower_is_worse": False,
            "message": SERUM_CA_REFERENCE_MSG,
            "action": SERUM_CA_REFERENCE_MSG,
        }
    )

    # ---------------- OVERALL STATUS & CLOSED-LOOP SCHEDULE ----------------
    # A3: Yellow = form/ROM/completeness + Vit D & nutrition (NO load increase), 72h.
    #     Red    = +5% load starting next workout (NOT stop training), 24h, report to ground.
    #     VBT > 30% = STOP this set TODAY, switch to recovery; load increase starts NEXT workout.
    # A4: 168h / 72h / 24h apply to E4D, isometric force, body mass; Ultrasound CSA min 7d; bone markers min 14d.
    # A5: Urgent escalation triggers ONLY when isometric strength loss > 20% OR body mass loss > 10%.
    clinical_worst = _worst(clinical_statuses)
    iso_loss_pct = -(float(iso_metric["delta_pct"]))
    mass_loss_pct = -(float(mass_metric["delta_pct"]))
    urgent_escalation = (iso_loss_pct > 20.0) or (mass_loss_pct > 10.0)

    training_worst = _worst([s_bone_status, iso_metric["status_light"], vbt_status])
    csa_worst = _worst([thigh_metric["status_light"], calf_metric["status_light"]])
    mass_status = mass_metric["status_light"]
    bone_worst = _worst([ntx_metric["status_light"], ctx_metric["status_light"], bone_rate_status])

    if clinical_worst == "RED":
        overall = "RED"
        next_hours = 24
        long_adj = (
            "Starting from the next workout, increase E4D load by approximately +5% or add sets; "
            "recheck E4D, isometric strength, and body mass in 24h, Ultrasound CSA >= 7 days, bone markers >= 14 days."
        )
    elif clinical_worst == "YELLOW" or vbt_status == "YELLOW":
        overall = "YELLOW"
        next_hours = 72
        long_adj = (
            "Complete full range of motion and slow eccentric control without increasing load; "
            "recheck E4D, isometric strength, and body mass in 72h, Ultrasound CSA >= 7 days, bone markers >= 14 days."
        )
    elif vbt_status == "RED":
        overall = "YELLOW"
        next_hours = 72
        long_adj = (
            "Stop fatigued set today and switch to recovery training; "
            "recheck E4D, isometric strength, and body mass in 72h, Ultrasound CSA >= 7 days, bone markers >= 14 days."
        )
    else:
        overall = "GREEN"
        next_hours = 168
        long_adj = (
            "Follow current prescription; weekly (168h) E4D, isometric strength, body mass, and Ultrasound CSA checks; "
            "bone markers >= 14 days."
        )

    immediate_actions: list[str] = []
    if urgent_escalation:
        immediate_actions.append(URGENT_REPORT_LINE)

    if vbt_status == "RED":
        immediate_actions.append(GUIDANCE_GROUPS["training"]["actions"]["vbt_over_30"])
    if overall == "RED":
        immediate_actions.append(GUIDANCE_GROUPS["training"]["actions"]["red"])
        if csa_worst == "RED":
            immediate_actions.append(GUIDANCE_GROUPS["csa"]["actions"]["red"])
        elif csa_worst == "YELLOW":
            immediate_actions.append(GUIDANCE_GROUPS["csa"]["actions"]["yellow"])
        if mass_status == "RED":
            immediate_actions.append(GUIDANCE_GROUPS["body_mass"]["actions"]["red"])
        elif mass_status == "YELLOW":
            immediate_actions.append(GUIDANCE_GROUPS["body_mass"]["actions"]["yellow"])
        if bone_worst == "RED":
            immediate_actions.append(GUIDANCE_GROUPS["bone_metabolism"]["actions"]["red"])
        elif bone_worst == "YELLOW":
            immediate_actions.append(GUIDANCE_GROUPS["bone_metabolism"]["actions"]["yellow"])
    elif overall == "YELLOW":
        if training_worst == "YELLOW" or vbt_status == "YELLOW":
            immediate_actions.append(GUIDANCE_GROUPS["training"]["actions"]["yellow"])
        if csa_worst in {"YELLOW", "RED"}:
            immediate_actions.append(GUIDANCE_GROUPS["csa"]["actions"]["yellow"])
        if mass_status in {"YELLOW", "RED"}:
            immediate_actions.append(GUIDANCE_GROUPS["body_mass"]["actions"]["yellow"])
        if bone_worst in {"YELLOW", "RED"}:
            immediate_actions.append(GUIDANCE_GROUPS["bone_metabolism"]["actions"]["yellow"])
        if not immediate_actions:
            immediate_actions.append(GUIDANCE_GROUPS["training"]["actions"]["yellow"])
    else:
        immediate_actions.append("Follow current prescription.")

    # Deduplicate while preserving order
    seen_acts: set[str] = set()
    immediate_actions = [a for a in immediate_actions if not (a in seen_acts or seen_acts.add(a))]

    urgent_alert = bool(urgent_escalation)
    days_until_red: Optional[int] = 0 if overall == "RED" else (min(dtr_candidates) if dtr_candidates else None)

    return {
        "module_id": "musculoskeletal",
        "body_part_tag": "lower_limb_bone_muscle",
        "crew_id": crew_id,
        "mission_day": mission_day,
        "status_light": overall,
        "quality_passed": True,
        "data_source": data_source,
        "urgent_escalation": urgent_escalation,
        "recheck_intervals_hours": {
            "e4d_isometric_mass": next_hours,
            "ultrasound_csa": max(next_hours, 7 * 24),
            "bone_markers": max(next_hours, 14 * 24),
        },
        "summary_note": (
            f"S_bone={s_bone:.2f}, VBT={vbt_loss:.1f}%, Thigh={thigh_metric['delta_pct']:+.1f}%, "
            f"Calf={calf_metric['delta_pct']:+.1f}%, CTX={ctx_metric['delta_pct']:+.1f}%, "
            f"Modeled Hip Loss={est_hip_loss_mo:.2f}%/mo."
            + (" [URGENT ESCALATION]" if urgent_escalation else "")
        ),
        "metrics": metrics,
        "guidance": {
            "how_to_measure": COMBINED_HOW_TO_MEASURE,
            "plain_explanation": COMBINED_PLAIN_EXPLANATION,
            "action_protocol": immediate_actions,
            "groups": {
                "training": {
                    "how_to_measure": GUIDANCE_GROUPS["training"]["how_to_measure"],
                    "plain_explanation": GUIDANCE_GROUPS["training"]["plain_explanation"],
                    "action_protocol": [
                        a
                        for a in (
                            [GUIDANCE_GROUPS["training"]["actions"]["vbt_over_30"]] if vbt_status == "RED" else []
                        )
                        + (
                            [GUIDANCE_GROUPS["training"]["actions"]["red"]]
                            if overall == "RED"
                            else (
                                [GUIDANCE_GROUPS["training"]["actions"]["yellow"]]
                                if training_worst == "YELLOW"
                                else []
                            )
                        )
                        + (
                            [GUIDANCE_GROUPS["training"]["actions"]["iso_over_20"]]
                            if iso_loss_pct > 20.0
                            else []
                        )
                    ] or ["Follow current prescription."],
                },
                "csa": {
                    "how_to_measure": GUIDANCE_GROUPS["csa"]["how_to_measure"],
                    "plain_explanation": GUIDANCE_GROUPS["csa"]["plain_explanation"],
                    "action_protocol": (
                        [GUIDANCE_GROUPS["csa"]["actions"]["red"]]
                        if csa_worst == "RED"
                        else (
                            [GUIDANCE_GROUPS["csa"]["actions"]["yellow"]]
                            if csa_worst == "YELLOW"
                            else ["Follow current prescription."]
                        )
                    ),
                },
                "body_mass": {
                    "how_to_measure": GUIDANCE_GROUPS["body_mass"]["how_to_measure"],
                    "plain_explanation": GUIDANCE_GROUPS["body_mass"]["plain_explanation"],
                    "action_protocol": (
                        [GUIDANCE_GROUPS["body_mass"]["actions"]["red"]]
                        if mass_status == "RED"
                        else (
                            [GUIDANCE_GROUPS["body_mass"]["actions"]["yellow"]]
                            if mass_status == "YELLOW"
                            else ["Follow current prescription."]
                        )
                    ),
                },
                "bone_metabolism": {
                    "how_to_measure": GUIDANCE_GROUPS["bone_metabolism"]["how_to_measure"],
                    "plain_explanation": GUIDANCE_GROUPS["bone_metabolism"]["plain_explanation"],
                    "action_protocol": (
                        [GUIDANCE_GROUPS["bone_metabolism"]["actions"]["red"]]
                        if bone_worst == "RED"
                        else (
                            [GUIDANCE_GROUPS["bone_metabolism"]["actions"]["yellow"]]
                            if bone_worst == "YELLOW"
                            else ["Follow current prescription."]
                        )
                    ),
                },
            },
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


def build_trajectory_figure(eval_result: Optional[dict[str, Any]] = None) -> Any:
    """Return interactive Plotly figure of 3-scenario Calf CSA & NTX trajectories with matching thresholds.

    A10: If an evaluation result with invalid/bad_data points is provided, any non-plausible
    or failed QC point is omitted from plotting so only prior valid points are drawn.
    """
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

    calf_low, calf_high, _ = PLAUSIBILITY_BOUNDS["csa_calf_cm2"]
    ntx_low, ntx_high, _ = PLAUSIBILITY_BOUNDS["ntx"]

    for scen in ("green", "yellow", "red"):
        pay = demo_payload(scen)
        days = pay["history_days"]
        calf_pairs = [
            (d, v)
            for d, v in zip(days, pay["history_series"]["csa_calf_cm2"])
            if _safe_float(v) is not None and calf_low <= float(v) <= calf_high
        ]
        ntx_pairs = [
            (d, v)
            for d, v in zip(days, pay["history_series"]["ntx"])
            if _safe_float(v) is not None and ntx_low <= float(v) <= ntx_high
        ]
        fig.add_trace(
            go.Scatter(
                x=[p[0] for p in calf_pairs],
                y=[p[1] for p in calf_pairs],
                mode="lines+markers",
                name=f"Calf CSA ({scen.upper()})",
                line=dict(color=colors[scen], width=2.5),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=[p[0] for p in ntx_pairs],
                y=[p[1] for p in ntx_pairs],
                mode="lines+markers",
                name=f"NTX ({scen.upper()})",
                line=dict(color=colors[scen], width=2.5, dash="dot"),
            ),
            row=1,
            col=2,
        )

    if eval_result and not eval_result.get("quality_passed", True):
        # Overlay only prior valid historical points if present; invalid point is never plotted
        hist = eval_result.get("prior_valid_history") or {}
        if isinstance(hist, dict) and hist.get("days") and hist.get("csa_calf_cm2"):
            valid_calf = [
                (d, v)
                for d, v in zip(hist["days"], hist["csa_calf_cm2"])
                if _safe_float(v) is not None and calf_low <= float(v) <= calf_high
            ]
            if valid_calf:
                fig.add_trace(
                    go.Scatter(
                        x=[p[0] for p in valid_calf],
                        y=[p[1] for p in valid_calf],
                        mode="lines+markers",
                        name="Prior Valid Calf CSA",
                        line=dict(color="#38bdf8", width=2.0),
                    ),
                    row=1,
                    col=1,
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
    """Plot Serum Calcium & ALP against real NASA OSDR OSD-575 (if CSV present) or Built-in reference (non-NASA data)."""
    if go is None or make_subplots is None:
        raise ImportError("plotly is required to build musculoskeletal figures.")

    osd = _load_osd575_summary()
    idx = list(range(1, len(osd["ca_series"]) + 1))
    src_label = "NASA OSDR OSD-575" if osd["data_source"] == "REAL" else "Built-in reference (non-NASA data)"

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
    fig.add_trace(
        go.Bar(x=idx, y=osd["alp_series"], name="ALP (U/L)", marker_color="#a855f7"),
        row=1,
        col=2,
    )
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

    # 1. Core 4 scenarios (A13 assertions)
    for scen in ("green", "yellow", "red", "bad_data"):
        raw = evaluate(demo_payload(scen))
        validated = to_schema(raw)
        assert validated.module_id == "musculoskeletal"
        assert validated.body_part_tag == "lower_limb_bone_muscle"
        if scen == "bad_data":
            assert validated.quality_passed is False
            assert validated.raw_status == "INSUFFICIENT_DATA"
            assert validated.short_term_plan.next_measurement_in_hours == 0
            assert validated.long_term_plan.days_until_red_prediction is None
            assert "trend_series" not in raw
            assert any(m.metric_name == "qc_csa_calf_cm2" for m in validated.metrics)
        elif scen == "green":
            assert validated.status_light == "GREEN"
            assert validated.quality_passed is True
            assert validated.short_term_plan.next_measurement_in_hours == 168
            assert validated.short_term_plan.urgent_alert is False
            bone_m = next(m for m in validated.metrics if m.metric_name == "est_monthly_bone_loss_pct")
            assert float(bone_m.current_val) < 1.0 and bone_m.status_light == "GREEN"
            assert bone_m.delta_pct is None and bone_m.message == REF_TEXT_BONE_LOSS
        elif scen == "yellow":
            assert validated.status_light == "YELLOW"
            assert validated.quality_passed is True
            assert validated.short_term_plan.next_measurement_in_hours == 72
            assert validated.short_term_plan.urgent_alert is False
            iso_m = next(m for m in validated.metrics if m.metric_name == "iso_peak_force_n")
            assert abs(float(iso_m.delta_pct) - (-8.11)) < 0.05 and iso_m.status_light == "YELLOW"
            bone_m = next(m for m in validated.metrics if m.metric_name == "est_monthly_bone_loss_pct")
            assert 1.0 <= float(bone_m.current_val) <= 1.5 and bone_m.status_light == "YELLOW"
            actions_joined = " ".join(validated.short_term_plan.immediate_actions).lower()
            assert "increase" not in actions_joined and "+5%" not in actions_joined
        elif scen == "red":
            assert validated.status_light == "RED"
            assert validated.quality_passed is True
            assert validated.short_term_plan.next_measurement_in_hours == 24
            assert validated.short_term_plan.urgent_alert is True
            assert raw.get("urgent_escalation") is True
            iso_m = next(m for m in validated.metrics if m.metric_name == "iso_peak_force_n")
            assert abs(float(iso_m.delta_pct) - (-22.16)) < 0.05 and iso_m.status_light == "RED"
            mass_m = next(m for m in validated.metrics if m.metric_name == "body_mass_kg")
            assert abs(float(mass_m.delta_pct) - (-10.81)) < 0.05 and mass_m.status_light == "RED"
            bone_m = next(m for m in validated.metrics if m.metric_name == "est_monthly_bone_loss_pct")
            assert float(bone_m.current_val) > 1.5 and bone_m.status_light == "RED"
            assert validated.short_term_plan.immediate_actions[0] == URGENT_REPORT_LINE
            assert any("starting from the next workout" in a.lower() and "5%" in a.lower() for a in validated.short_term_plan.immediate_actions)
            assert not any("stop training" in a.lower() for a in validated.short_term_plan.immediate_actions)
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

    # 3. Serum Ca, ALP, and P1NP NEVER change module status_light in any scenario (A6 & A8)
    for scen_name in ("green", "yellow", "red"):
        base_scen = demo_payload(scen_name)
        base_res = to_schema(evaluate(base_scen))
        extreme_ref = to_schema(
            evaluate({**base_scen, "serum_ca_mg_dl": 12.0, "serum_alp_u_l": 250.0, "p1np": 10.0})
        )
        assert extreme_ref.status_light == base_res.status_light
        ca_m = next(m for m in extreme_ref.metrics if m.metric_name == "osd575_ca_alp_baseline")
        p1np_m = next(m for m in extreme_ref.metrics if m.metric_name == "p1np_bone_formation")
        assert ca_m.status_light == "GREEN" and ca_m.raw_status == "REFERENCE"
        assert p1np_m.status_light == "GREEN" and p1np_m.raw_status == "REFERENCE"

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

    # 8. Plotly figure helpers (including bad_data filtering check)
    assert build_trajectory_figure(evaluate(demo_payload("bad_data"))) is not None
    assert build_iss_comparison_figure() is not None
    assert build_osd575_baseline_figure() is not None

    print("ALL EXPANDED MUSCULOSKELETAL TESTS PASSED.")
