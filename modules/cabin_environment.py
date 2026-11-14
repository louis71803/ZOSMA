"""Role 6: Radiation, Acoustics & Cabin Environment Domain Starter Module.

Implements Layer 0 QC Gatekeeper + 3-Layer Decision Model for NASA-STD-3001:
- RAD-01..03: DOSTEL area dose rate (with SAA pass flag), Career dose (480/600 mSv), GOES proton flux (>=10/100 pfu)
- ACO-01..02: Module SPL (NC-50 / 72 dBA) & Crew 8h LEQ / daily noise dose
- ATM-01..04: MCA/CDRA ppCO2 (2.5 / 3.0 mmHg) + stuck-sensor check, Cabin Pressure & dP/dt depressurization fast-track, Thermal T/RH, VOC SMAC / Ammonia
- ISO-01..03: Actiwatch Sleep TST, PVT-B alertness, Bedford Workload
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "cabin_environment"


def demo_baseline() -> dict[str, Any]:
    return {
        "crew_id": "C002",
        "dose_rate_uGy_h": 18.0,
        "career_dose_mSv": 145.0,
        "ppco2_1h_mmHg": 1.8,
        "p_total_kPa": 101.3,
        "pio2_mmHg": 159.0,
        "temp_C": 22.2,
        "rh_pct": 44.0,
        "sleep_tst_h": 7.2,
    }


def demo_payload(scenario: str = "green") -> dict[str, Any]:
    scen = (scenario or "green").strip().lower()
    if scen == "bad_data":
        return {
            "crew_id": "C002",
            "mission_day": 124,
            "data_source": "SIMULATED",
            "co2_sensor_stuck_hours": 28.0,  # >=24h stuck sensor QC gate
            "dose_rate_uGy_h": 19.0,
            "saa_pass": False,
            "career_dose_mSv": 152.0,
            "proton_flux_10mev_pfu": 2.1,
            "spe_alert": False,
            "module_spl_dBA": 62.0,
            "crew_leq8_dBA": 64.0,
            "daily_noise_dose_pct": 22.0,
            "ppco2_1h_mmHg": 1.80,
            "ppco2_7d_mmHg": 1.80,
            "p_total_kPa": 101.3,
            "pio2_mmHg": 159.0,
            "dpdt_kPa_per_min": 0.0,
            "temp_C": 22.4,
            "rh_pct": 45.0,
            "max_smac_ratio": 0.25,
            "ammonia_or_fire_alarm": False,
            "sleep_tst_h": 7.1,
            "pvt_speed_1_per_s": 4.2,
            "workload_bedford": 3.0,
            "stress_vas": 2.5,
        }
    if scen == "yellow":
        return {
            "crew_id": "C002",
            "mission_day": 124,
            "data_source": "SIMULATED",
            "co2_sensor_stuck_hours": 0.0,
            "dose_rate_uGy_h": 42.0,
            "saa_pass": False,
            "career_dose_mSv": 495.0,  # >= 480 mSv Yellow
            "proton_flux_10mev_pfu": 25.0,  # >= 10 pfu Yellow
            "spe_alert": False,
            "module_spl_dBA": 71.0,
            "crew_leq8_dBA": 74.0,
            "daily_noise_dose_pct": 85.0,
            "ppco2_1h_mmHg": 2.65,  # >= 2.5 mmHg Yellow
            "ppco2_7d_mmHg": 2.40,
            "p_total_kPa": 98.5,
            "pio2_mmHg": 152.0,
            "dpdt_kPa_per_min": -0.05,
            "temp_C": 25.8,
            "rh_pct": 63.0,
            "max_smac_ratio": 0.78,
            "ammonia_or_fire_alarm": False,
            "sleep_tst_h": 5.8,
            "pvt_speed_1_per_s": 3.4,
            "workload_bedford": 6.0,
            "stress_vas": 6.0,
        }
    if scen == "red":
        return {
            "crew_id": "C002",
            "mission_day": 124,
            "data_source": "SIMULATED",
            "co2_sensor_stuck_hours": 0.0,
            "dose_rate_uGy_h": 280.0,
            "saa_pass": False,
            "career_dose_mSv": 615.0,  # >= 600 mSv Red
            "proton_flux_10mev_pfu": 185.0,  # >= 100 pfu Red SPE
            "spe_alert": True,
            "module_spl_dBA": 82.0,
            "crew_leq8_dBA": 86.0,
            "daily_noise_dose_pct": 140.0,
            "ppco2_1h_mmHg": 3.45,  # >= 3.0 mmHg Red
            "ppco2_7d_mmHg": 2.95,
            "p_total_kPa": 91.0,
            "pio2_mmHg": 135.0,
            "dpdt_kPa_per_min": -0.60,
            "temp_C": 28.0,
            "rh_pct": 72.0,
            "max_smac_ratio": 1.35,
            "ammonia_or_fire_alarm": False,
            "sleep_tst_h": 4.9,
            "pvt_speed_1_per_s": 2.6,
            "workload_bedford": 8.0,
            "stress_vas": 8.5,
        }
    return {
        "crew_id": "C002",
        "mission_day": 124,
        "data_source": "SIMULATED",
        "co2_sensor_stuck_hours": 0.0,
        "dose_rate_uGy_h": 18.5,
        "saa_pass": False,
        "career_dose_mSv": 152.0,
        "proton_flux_10mev_pfu": 1.8,
        "spe_alert": False,
        "module_spl_dBA": 61.5,
        "crew_leq8_dBA": 63.0,
        "daily_noise_dose_pct": 20.0,
        "ppco2_1h_mmHg": 1.85,
        "ppco2_7d_mmHg": 1.80,
        "p_total_kPa": 101.3,
        "pio2_mmHg": 159.0,
        "dpdt_kPa_per_min": 0.0,
        "temp_C": 22.3,
        "rh_pct": 45.0,
        "max_smac_ratio": 0.22,
        "ammonia_or_fire_alarm": False,
        "sleep_tst_h": 7.1,
        "pvt_speed_1_per_s": 4.2,
        "workload_bedford": 3.0,
        "stress_vas": 2.5,
    }


def export_demo_csvs() -> list[str]:
    """Generate editable starter CSV/JSON templates in data/cabin_environment/."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    goes_path = DATA_DIR / "goes_integral_protons_6h.json"
    with goes_path.open("w", encoding="utf-8") as fh:
        json.dump({"proton_flux_10mev_pfu": 1.8, "spe_alert": False}, fh, indent=2)
    written.append(str(goes_path))

    co2_df = pd.DataFrame(
        [
            {"mission_day": 121, "ppco2_1h_mmHg": 1.80, "ppco2_7d_mmHg": 1.78, "co2_sensor_stuck_hours": 0.0},
            {"mission_day": 122, "ppco2_1h_mmHg": 1.82, "ppco2_7d_mmHg": 1.79, "co2_sensor_stuck_hours": 0.0},
            {"mission_day": 123, "ppco2_1h_mmHg": 1.84, "ppco2_7d_mmHg": 1.80, "co2_sensor_stuck_hours": 0.0},
            {"mission_day": 124, "ppco2_1h_mmHg": 1.85, "ppco2_7d_mmHg": 1.80, "co2_sensor_stuck_hours": 0.0},
        ]
    )
    co2_path = DATA_DIR / "atm01_co2.csv"
    co2_df.to_csv(co2_path, index=False)
    written.append(str(co2_path))

    rad_df = pd.DataFrame(
        [
            {"mission_day": 122, "dose_rate_uGy_h": 18.2, "saa_pass": False, "career_dose_mSv": 150.2},
            {"mission_day": 123, "dose_rate_uGy_h": 18.4, "saa_pass": False, "career_dose_mSv": 151.1},
            {"mission_day": 124, "dose_rate_uGy_h": 18.5, "saa_pass": False, "career_dose_mSv": 152.0},
        ]
    )
    rad_path = DATA_DIR / "rad02_crew_dose_daily.csv"
    rad_df.to_csv(rad_path, index=False)
    written.append(str(rad_path))
    return written


def _worst(statuses: list[str]) -> str:
    order = {"GREEN": 0, "YELLOW": 1, "RED": 2}
    return max(statuses, key=lambda s: order.get(s, 0)) if statuses else "GREEN"


def evaluate(
    payload: Optional[dict[str, Any]] = None,
    baseline: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Stateless 3-layer Cabin Environment & Radiation evaluation."""
    base = {**demo_baseline(), **(baseline or {})}
    pay = {**demo_payload("green"), **(payload or {})}

    crew_id = str(pay.get("crew_id", base.get("crew_id", "C002")))
    mission_day = int(pay.get("mission_day", 124))
    data_source = str(pay.get("data_source", "SIMULATED")).upper()

    # Layer 0 QC Gatekeeper: Stuck CO2 sensor >= 24h
    stuck_h = float(pay.get("co2_sensor_stuck_hours", 0.0))
    if stuck_h >= 24.0:
        return {
            "module_id": "cabin_environment",
            "body_part_tag": ["whole_body", "lungs", "brain", "ears"],
            "crew_id": crew_id,
            "mission_day": mission_day,
            "status_light": "INSUFFICIENT_DATA",
            "quality_passed": False,
            "data_source": data_source,
            "summary_note": f"MCA CO2 sensor flatlined for {stuck_h:.0f}h (>=24h stuck-sensor QC fault).",
            "metrics": [
                {
                    "metric_name": "co2_sensor_qc",
                    "current_val": round(stuck_h, 1),
                    "baseline_val": 0.0,
                    "unit": "hours_stuck",
                    "status_light": "INSUFFICIENT_DATA",
                    "decided_by": "quality_check",
                    "data_source": data_source,
                    "message": "MCA CO2 reading invariant for >= 24h; sensor drift/freeze suspected.",
                    "action": "Switch to backup CDRA optical CO2 sensor and purge MCA sample line.",
                }
            ],
            "guidance": {
                "how_to_measure": "Cross-check primary MCA IR bench against portable Drager / backup CDRA CO2 monitor.",
                "plain_explanation": "A frozen CO2 sensor hides rising cabin ppCO2, risking headaches and SANS optic nerve swelling.",
                "action_protocol": ["Switch telemetry to backup CO2 sensor and clean MCA inlet filter."],
            },
            "short_term_plan": {
                "next_measurement_in_hours": 0,
                "immediate_actions": ["Verify cabin CO2 with handheld backup detector immediately."],
                "urgent_alert": False,
            },
            "long_term_plan": {
                "days_until_red_prediction": None,
                "routine_prescription_adjustment": "Calibrate MCA zero-gas reference monthly.",
            },
        }

    # RAD-03 GOES SPE & RAD-02 Career Dose (with SAA masking on RAD-01)
    pfu = float(pay.get("proton_flux_10mev_pfu", 1.8))
    spe_alert = bool(pay.get("spe_alert", False)) or pfu >= 100.0
    career_msv = float(pay.get("career_dose_mSv", base["career_dose_mSv"]))
    saa_pass = bool(pay.get("saa_pass", False))
    dose_rate = float(pay.get("dose_rate_uGy_h", base["dose_rate_uGy_h"]))

    if spe_alert or pfu >= 100.0:
        rad_status = "RED"
    elif pfu >= 10.0 or (dose_rate >= 35.0 and not saa_pass):
        rad_status = "YELLOW"
    else:
        rad_status = "GREEN"

    if career_msv >= 600.0:
        career_status = "RED"
    elif career_msv >= 480.0:
        career_status = "YELLOW"
    else:
        career_status = "GREEN"

    # ATM-01 CO2
    ppco2 = float(pay.get("ppco2_1h_mmHg", base["ppco2_1h_mmHg"]))
    if ppco2 >= 3.0:
        co2_status = "RED"
    elif ppco2 >= 2.5:
        co2_status = "YELLOW"
    else:
        co2_status = "GREEN"

    # ATM-02 Pressure & Rapid Depressurization Fast-Track + ATM-04 Ammonia/Fire
    dpdt = float(pay.get("dpdt_kPa_per_min", 0.0))
    p_total = float(pay.get("p_total_kPa", 101.3))
    alarm = bool(pay.get("ammonia_or_fire_alarm", False))
    smac = float(pay.get("max_smac_ratio", 0.22))
    if alarm or dpdt <= -0.5 or p_total < 94.0 or smac >= 1.0:
        atm_status = "RED"
    elif p_total < 99.0 or smac >= 0.7:
        atm_status = "YELLOW"
    else:
        atm_status = "GREEN"

    # ACO-01/02 Acoustics
    leq8 = float(pay.get("crew_leq8_dBA", 63.0))
    if leq8 >= 85.0:
        aco_status = "RED"
    elif leq8 >= 72.0:
        aco_status = "YELLOW"
    else:
        aco_status = "GREEN"

    # ISO-01 Sleep
    sleep_h = float(pay.get("sleep_tst_h", 7.1))
    if sleep_h < 5.5:
        sleep_status = "RED"
    elif sleep_h < 6.5:
        sleep_status = "YELLOW"
    else:
        sleep_status = "GREEN"

    overall = _worst([rad_status, career_status, co2_status, atm_status, aco_status, sleep_status])

    history_days = [0, 30, 60, 90, mission_day]
    step = (ppco2 - float(base["ppco2_1h_mmHg"])) / 4.0
    history_vals = [round(float(base["ppco2_1h_mmHg"]) + step * i, 2) for i in range(5)]

    days_until_red: Optional[int] = None
    if overall == "RED":
        days_until_red = 0
    elif ppco2 > float(base["ppco2_1h_mmHg"]):
        slope = (ppco2 - float(base["ppco2_1h_mmHg"])) / max(mission_day, 1)
        if slope > 0:
            days_until_red = max(1, int((3.0 - ppco2) / slope))

    metrics = [
        {
            "metric_name": "ppco2_1h_mmHg",
            "current_val": round(ppco2, 2),
            "baseline_val": float(base["ppco2_1h_mmHg"]),
            "slope_per_day": round((ppco2 - float(base["ppco2_1h_mmHg"])) / max(mission_day, 1), 4),
            "unit": "mmHg",
            "status_light": co2_status,
            "decided_by": "fixed_threshold",
            "data_source": data_source,
            "yellow_threshold": 2.5,
            "red_threshold": 3.0,
            "lower_is_worse": False,
            "history_days": history_days,
            "history_values": history_vals,
            "message": f"Cabin 1h ppCO2 = {ppco2:.2f} mmHg (Yellow >= 2.5, Red >= 3.0).",
            "action": "Switch to backup CDRA desiccant/sorbent bed immediately." if co2_status != "GREEN" else "Air scrubbing nominal.",
        },
        {
            "metric_name": "proton_flux_10mev_pfu",
            "current_val": round(pfu, 1),
            "baseline_val": 2.0,
            "unit": "pfu",
            "status_light": rad_status,
            "decided_by": "spe_rule" if spe_alert else "fixed_threshold",
            "data_source": data_source,
            "message": f"GOES >=10 MeV flux {pfu:.1f} pfu | SPE_alert={spe_alert} | SAA={saa_pass}.",
            "action": "EVACUATE TO WATER WALL STORM SHELTER." if rad_status == "RED" else "Monitor NOAA GOES proton trend.",
        },
        {
            "metric_name": "career_dose_mSv",
            "current_val": round(career_msv, 1),
            "baseline_val": 145.0,
            "unit": "mSv",
            "status_light": career_status,
            "decided_by": "fixed_threshold",
            "data_source": data_source,
            "message": f"Cumulative mission/career dose {career_msv:.1f} mSv (NASA limit 600 mSv).",
            "action": "Maximize polyethylene/water shielding hours." if career_status != "GREEN" else "Dose budget nominal.",
        },
        {
            "metric_name": "crew_leq8_dBA",
            "current_val": round(leq8, 1),
            "baseline_val": 63.0,
            "unit": "dBA",
            "status_light": aco_status,
            "decided_by": "fixed_threshold",
            "data_source": data_source,
            "message": f"Crew 8h noise exposure {leq8:.1f} dBA.",
            "action": "Don ANR hearing protection & inspect fan mounts." if aco_status != "GREEN" else "Acoustic load safe.",
        },
        {
            "metric_name": "sleep_tst_h",
            "current_val": round(sleep_h, 1),
            "baseline_val": float(base["sleep_tst_h"]),
            "unit": "h",
            "status_light": sleep_status,
            "decided_by": "fixed_threshold",
            "data_source": data_source,
            "message": f"Actiwatch total sleep time {sleep_h:.1f} h.",
            "action": "Protect 8h sleep window & dim cabin blue light." if sleep_status != "GREEN" else "Circadian sleep adequate.",
        },
    ]

    if overall == "RED":
        actions = [
            "If SPE_alert or pfu >= 100: relocate crew to Water Wall radiation storm shelter immediately.",
            "If ppCO2 >= 3.0 mmHg: activate backup CDRA scrubber and verify cabin airflow fans.",
            "If rapid depressurization/alarm: don emergency masks & isolate affected hatch.",
        ]
        next_hours = 1
        adj = "Enforce shielded sleep-station occupancy, daily CDRA sorbent regeneration, and post-SPE CBC follow-up."
    elif overall == "YELLOW":
        actions = [
            "Cycle CDRA bed regeneration and verify portable fan mixing to clear CO2 pockets.",
            "Wear acoustic ear protection in high-SPL equipment modules.",
        ]
        next_hours = 6
        adj = "Monitor GOES solar weather every 6h and maintain sleep hygiene schedule >= 7h/night."
    else:
        actions = ["Nominal cabin ECLSS, radiation, acoustic, and sleep telemetry."]
        next_hours = 24
        adj = "Continue standard ECLSS telemetry logging and weekly dosimeter readout."

    return {
        "module_id": "cabin_environment",
        "body_part_tag": ["whole_body", "lungs", "brain", "ears"],
        "crew_id": crew_id,
        "mission_day": mission_day,
        "status_light": overall,
        "quality_passed": True,
        "data_source": data_source,
        "summary_note": f"ppCO2 {ppco2:.2f} mmHg, Proton {pfu:.1f} pfu (SPE={spe_alert}), LEQ8 {leq8:.1f} dBA, Sleep {sleep_h:.1f}h.",
        "metrics": metrics,
        "guidance": {
            "how_to_measure": "Read MCA CO2 bench, DOSTEL area/crew dosimeters, acoustic SPL meter, and wrist Actiwatch sync.",
            "plain_explanation": "Hostile closed-cabin air, CO2 buildup, noise fatigue, and solar proton storms directly impair cognition, immunity, and optic nerve health.",
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
