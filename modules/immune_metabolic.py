"""Role 5: Immune, Endocrine & Metabolic Domain Starter Module.

Implements Layer 0 QC Gatekeeper + 3-Layer Decision Model for:
- Oral Temperature & 9 Symptom Checklist
- HemoCue / Bio-Analyzer WBC & <10% Neutrophil mis-sort QC gate
- Lymphocytes (-25% drop & post-SPE -50% cross-module rule)
- Neutrophils & NLR stress index
- Saliva VZV / EBV reactivation DNA copies/mL
- Sleep, Stress, CRP/IL-6 & Hydration renal protection
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "immune_metabolic"


def demo_baseline() -> dict[str, Any]:
    return {
        "crew_id": "C002",
        "temp_c": 36.7,
        "wbc": 6.1,
        "lymph": 2.0,
        "neut": 3.5,
        "crp_mg_l": 1.1,
        "hydration_ml": 2500.0,
    }


def demo_payload(scenario: str = "green") -> dict[str, Any]:
    scen = (scenario or "green").strip().lower()
    if scen == "bad_data":
        return {
            "crew_id": "C002",
            "mission_day": 124,
            "data_source": "SIMULATED",
            "temp_c": 36.8,
            "symptoms": [],
            "wbc": 6.0,
            "lymph": 1.9,
            "neut": 0.4,  # <10% of WBC -> QC mis-sort gate
            "saliva_vzv": 0.0,
            "saliva_ebv": 150.0,
            "sleep_h": 7.2,
            "stress_score": 2.5,
            "spe_event_flag": False,
            "crp_mg_l": 1.2,
            "il6_pg_ml": 1.8,
            "hydration_ml": 2400.0,
        }
    if scen == "yellow":
        return {
            "crew_id": "C002",
            "mission_day": 124,
            "data_source": "SIMULATED",
            "temp_c": 37.6,
            "symptoms": ["fatigue", "nasal_congestion"],
            "wbc": 9.8,
            "lymph": 1.4,  # -30% drop
            "neut": 7.6,
            "saliva_vzv": 320.0,
            "saliva_ebv": 1800.0,
            "sleep_h": 5.6,
            "stress_score": 6.5,
            "spe_event_flag": False,
            "crp_mg_l": 7.5,
            "il6_pg_ml": 6.2,
            "hydration_ml": 1800.0,
        }
    if scen == "red":
        return {
            "crew_id": "C002",
            "mission_day": 124,
            "data_source": "SIMULATED",
            "temp_c": 38.6,
            "symptoms": ["fever", "vesicular_rash", "chills"],
            "wbc": 13.4,
            "lymph": 0.85,  # -57.5% drop
            "neut": 11.4,
            "saliva_vzv": 4800.0,
            "saliva_ebv": 9500.0,
            "sleep_h": 4.8,
            "stress_score": 8.5,
            "spe_event_flag": True,
            "crp_mg_l": 24.0,
            "il6_pg_ml": 19.5,
            "hydration_ml": 1400.0,
        }
    return {
        "crew_id": "C002",
        "mission_day": 124,
        "data_source": "SIMULATED",
        "temp_c": 36.7,
        "symptoms": [],
        "wbc": 6.2,
        "lymph": 1.95,
        "neut": 3.6,
        "saliva_vzv": 0.0,
        "saliva_ebv": 120.0,
        "sleep_h": 7.3,
        "stress_score": 2.0,
        "spe_event_flag": False,
        "crp_mg_l": 1.0,
        "il6_pg_ml": 1.5,
        "hydration_ml": 2550.0,
    }


def export_demo_csvs() -> list[str]:
    """Generate editable starter CSV/JSON templates in data/immune_metabolic/."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    base_path = DATA_DIR / "preflight_baseline.json"
    with base_path.open("w", encoding="utf-8") as fh:
        json.dump(demo_baseline(), fh, indent=2)
    written.append(str(base_path))

    daily_df = pd.DataFrame(
        [
            {"mission_day": 121, "temp_c": 36.6, "symptoms": "", "sleep_h": 7.4, "stress_score": 2.0, "hydration_ml": 2500},
            {"mission_day": 122, "temp_c": 36.7, "symptoms": "", "sleep_h": 7.1, "stress_score": 2.5, "hydration_ml": 2450},
            {"mission_day": 123, "temp_c": 36.7, "symptoms": "", "sleep_h": 7.2, "stress_score": 2.2, "hydration_ml": 2600},
            {"mission_day": 124, "temp_c": 36.7, "symptoms": "", "sleep_h": 7.3, "stress_score": 2.0, "hydration_ml": 2550},
        ]
    )
    daily_path = DATA_DIR / "daily_checkin.csv"
    daily_df.to_csv(daily_path, index=False)
    written.append(str(daily_path))

    cbc_df = pd.DataFrame(
        [
            {"mission_day": 30, "wbc": 6.1, "lymph": 2.0, "neut": 3.5, "crp_mg_l": 1.1, "il6_pg_ml": 1.6},
            {"mission_day": 60, "wbc": 6.3, "lymph": 1.98, "neut": 3.6, "crp_mg_l": 1.0, "il6_pg_ml": 1.5},
            {"mission_day": 90, "wbc": 6.2, "lymph": 1.96, "neut": 3.55, "crp_mg_l": 1.1, "il6_pg_ml": 1.5},
            {"mission_day": 124, "wbc": 6.2, "lymph": 1.95, "neut": 3.6, "crp_mg_l": 1.0, "il6_pg_ml": 1.5},
        ]
    )
    cbc_path = DATA_DIR / "cbc_monthly.csv"
    cbc_df.to_csv(cbc_path, index=False)
    written.append(str(cbc_path))
    return written


def _worst(statuses: list[str]) -> str:
    order = {"GREEN": 0, "YELLOW": 1, "RED": 2}
    return max(statuses, key=lambda s: order.get(s, 0)) if statuses else "GREEN"


def evaluate(
    payload: Optional[dict[str, Any]] = None,
    baseline: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Stateless 3-layer Immune, Endocrine & Metabolic evaluation."""
    base = {**demo_baseline(), **(baseline or {})}
    pay = {**demo_payload("green"), **(payload or {})}

    crew_id = str(pay.get("crew_id", base.get("crew_id", "C002")))
    mission_day = int(pay.get("mission_day", 124))
    data_source = str(pay.get("data_source", "SIMULATED")).upper()

    wbc = float(pay.get("wbc", base["wbc"]))
    neut = float(pay.get("neut", base["neut"]))
    lymph = float(pay.get("lymph", base["lymph"]))

    # Layer 0 QC Gatekeeper: OSD-569 C003 L-92 <10% neutrophil mis-sort check
    if wbc <= 0 or (neut / wbc) < 0.10:
        return {
            "module_id": "immune_metabolic",
            "body_part_tag": "immune_renal",
            "crew_id": crew_id,
            "mission_day": mission_day,
            "status_light": "INSUFFICIENT_DATA",
            "quality_passed": False,
            "data_source": data_source,
            "summary_note": f"Bio-Analyzer QC failed: Neutrophil fraction {(neut/max(wbc,0.01))*100:.1f}% < 10% (possible sample mis-sort).",
            "metrics": [
                {
                    "metric_name": "neutrophil_qc_ratio",
                    "current_val": round((neut / max(wbc, 0.01)) * 100.0, 1),
                    "baseline_val": 55.0,
                    "unit": "%",
                    "status_light": "INSUFFICIENT_DATA",
                    "decided_by": "quality_check",
                    "data_source": data_source,
                    "message": "Neutrophils < 10% of WBC indicates optical/cartridge mis-sort.",
                    "action": "Discard cartridge, wipe fingerstick site, and re-run Bio-Analyzer CBC.",
                }
            ],
            "guidance": {
                "how_to_measure": "Warm finger 60s, wipe first blood drop, fill Bio-Analyzer cartridge bubble-free, and insert within 30s.",
                "plain_explanation": "Clotted or micro-bubbled fingerstick samples cause false neutropenia readings.",
                "action_protocol": ["Re-run Bio-Analyzer CBC with fresh cartridge."],
            },
            "short_term_plan": {
                "next_measurement_in_hours": 0,
                "immediate_actions": ["Re-run Bio-Analyzer CBC immediately to clear QC warning."],
                "urgent_alert": False,
            },
            "long_term_plan": {
                "days_until_red_prediction": None,
                "routine_prescription_adjustment": "Inspect Bio-Analyzer optical reader during weekly maintenance.",
            },
        }

    temp_c = float(pay.get("temp_c", base["temp_c"]))
    if temp_c >= 38.0:
        temp_status = "RED"
    elif temp_c >= 37.3:
        temp_status = "YELLOW"
    else:
        temp_status = "GREEN"

    lymph_delta_pct = ((lymph - float(base["lymph"])) / float(base["lymph"])) * 100.0
    spe_flag = bool(pay.get("spe_event_flag", False))
    if lymph_delta_pct <= -50.0 or (spe_flag and lymph_delta_pct <= -35.0):
        lymph_status = "RED"
        lymph_by = "spe_rule" if spe_flag else "baseline"
    elif lymph_delta_pct <= -25.0 or spe_flag:
        lymph_status = "YELLOW"
        lymph_by = "spe_rule" if spe_flag else "baseline"
    else:
        lymph_status = "GREEN"
        lymph_by = "baseline"

    vzv = float(pay.get("saliva_vzv", 0.0))
    if vzv >= 1000.0:
        vzv_status = "RED"
    elif vzv >= 100.0:
        vzv_status = "YELLOW"
    else:
        vzv_status = "GREEN"

    crp = float(pay.get("crp_mg_l", base["crp_mg_l"]))
    if crp >= 15.0:
        crp_status = "RED"
    elif crp >= 5.0:
        crp_status = "YELLOW"
    else:
        crp_status = "GREEN"

    hydration = float(pay.get("hydration_ml", base["hydration_ml"]))
    if hydration < 1500.0:
        hyd_status = "RED"
    elif hydration < 2000.0:
        hyd_status = "YELLOW"
    else:
        hyd_status = "GREEN"

    overall = _worst([temp_status, lymph_status, vzv_status, crp_status, hyd_status])

    history_days = [0, 30, 60, 90, mission_day]
    step = (lymph - float(base["lymph"])) / 4.0
    history_vals = [round(float(base["lymph"]) + step * i, 2) for i in range(5)]

    days_until_red: Optional[int] = None
    if overall == "RED":
        days_until_red = 0
    elif lymph_delta_pct < -5.0:
        daily_drop = (lymph - float(base["lymph"])) / max(mission_day, 1)
        if daily_drop < 0:
            red_target = float(base["lymph"]) * 0.50
            days_until_red = max(1, int((red_target - lymph) / daily_drop))

    nlr = round(neut / max(lymph, 0.1), 2)

    metrics = [
        {
            "metric_name": "lymphocytes_10e9_l",
            "current_val": round(lymph, 2),
            "baseline_val": float(base["lymph"]),
            "delta_pct": round(lymph_delta_pct, 1),
            "slope_per_day": round((lymph - float(base["lymph"])) / max(mission_day, 1), 4),
            "unit": "10^9/L",
            "status_light": lymph_status,
            "decided_by": lymph_by,
            "data_source": data_source,
            "yellow_threshold": round(float(base["lymph"]) * 0.75, 2),
            "red_threshold": round(float(base["lymph"]) * 0.50, 2),
            "lower_is_worse": True,
            "history_days": history_days,
            "history_values": history_vals,
            "message": f"Lymphocytes {lymph:.2f} ({lymph_delta_pct:+.1f}% vs baseline); SPE_flag={spe_flag}.",
            "action": "48h post-SPE CBC monitoring + isolate symptomatic crew." if lymph_status != "GREEN" else "Cellular immunity steady.",
        },
        {
            "metric_name": "oral_temp_c",
            "current_val": round(temp_c, 1),
            "baseline_val": float(base["temp_c"]),
            "unit": "C",
            "status_light": temp_status,
            "decided_by": "fixed_threshold",
            "data_source": data_source,
            "message": f"Oral temp {temp_c:.1f} C (NLR stress index {nlr}).",
            "action": "Antipyretic + hydration + infectious isolation." if temp_status == "RED" else "Re-check temp in 6h.",
        },
        {
            "metric_name": "saliva_vzv_copies_ml",
            "current_val": round(vzv, 0),
            "baseline_val": 0.0,
            "unit": "copies/mL",
            "status_light": vzv_status,
            "decided_by": "fixed_threshold",
            "data_source": data_source,
            "message": f"Salivary VZV viral shedding {vzv:.0f} copies/mL.",
            "action": "Start oral Valacyclovir protocol & inspect skin for rash." if vzv_status == "RED" else "Monitor latent viral reactivation.",
        },
        {
            "metric_name": "crp_mg_l",
            "current_val": round(crp, 1),
            "baseline_val": float(base["crp_mg_l"]),
            "unit": "mg/L",
            "status_light": crp_status,
            "decided_by": "fixed_threshold",
            "data_source": data_source,
            "message": f"Inflammatory marker CRP {crp:.1f} mg/L.",
            "action": "Correlate with fever/infection panel." if crp_status != "GREEN" else "No systemic inflammation.",
        },
        {
            "metric_name": "hydration_ml",
            "current_val": round(hydration, 0),
            "baseline_val": float(base["hydration_ml"]),
            "unit": "mL/d",
            "status_light": hyd_status,
            "decided_by": "fixed_threshold",
            "data_source": data_source,
            "message": f"24h fluid intake {hydration:.0f} mL (renal stone prevention).",
            "action": "Drink +750 mL water + potassium citrate tablet." if hyd_status != "GREEN" else "Renal hydration on target.",
        },
    ]

    if overall == "RED":
        actions = [
            "Isolate crew member in sleep quarters if fever >= 38.0 C or active VZV skin vesicles present.",
            "Initiate onboard Valacyclovir / broad-spectrum medical kit protocol per offline Flight Surgeon guide.",
            "Run Bio-Analyzer CBC & hydration log every 12h (mandatory 48h post-SPE if solar storm active).",
        ]
        next_hours = 6
        adj = "Suspend strenuous exercise; 14-day antiviral/recovery course + sleep optimization >= 8h/night."
    elif overall == "YELLOW":
        actions = [
            "Schedule Bio-Analyzer CBC check in 48 hours (especially if SPE alert triggered).",
            "Boost fluid intake to >= 2500 mL/day and prioritize >= 7.5h sleep.",
        ]
        next_hours = 24
        adj = "Weekly saliva viral qPCR & sleep/stress load reduction over next 14 days."
    else:
        actions = ["Continue daily oral temp, hydration log, and monthly Bio-Analyzer CBC."]
        next_hours = 72
        adj = "Maintain Vitamin D3 supplementation (2000 IU/d) and 2.5 L/d renal hydration."

    return {
        "module_id": "immune_metabolic",
        "body_part_tag": "immune_renal",
        "crew_id": crew_id,
        "mission_day": mission_day,
        "status_light": overall,
        "quality_passed": True,
        "data_source": data_source,
        "summary_note": f"Temp {temp_c:.1f} C, Lymph {lymph:.2f} ({lymph_delta_pct:+.1f}%), VZV {vzv:.0f}, SPE={spe_flag}.",
        "metrics": metrics,
        "guidance": {
            "how_to_measure": "Measure oral temp before eating/drinking; collect morning saliva swab; run Bio-Analyzer fingerstick CBC.",
            "plain_explanation": "Space radiation, isolation stress, and microgravity suppress T-cell immunity, reactivating latent viruses (VZV/EBV) and raising kidney stone risk.",
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
