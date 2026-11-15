"""Day-1 Standby Masking & Progressive Check-In Activation Engine (`core/onboarding.py`).

Role 1 exclusively owns this file.
Implements Option 2 (Hardware Auto-Online vs. Crew Physiological Standby):
1. `cabin_environment`: Always online from Sol/Day 1 (spacecraft ECLSS & radiation sensors run automatically).
2. Physiological subsystems (`cardiovascular`, `musculoskeletal`, `neuro_ocular`, `immune_metabolic`):
   - In `day1_standby` mode before any check-in: enter `STANDBY` state (pre-flight baseline & thresholds
     are loaded and visible, current values await first crew check-in, no false alarms).
   - Progressive light-up: when the astronaut submits `Daily Routine Vitals` or a `Scheduled Subsystem Check-in`,
     metrics backed by logged measurements immediately light up with live evaluation and `D0 -> D1` trend lines,
     while unmeasured specialized hardware metrics remain marked `standby=True` until measured.
"""

from __future__ import annotations

from typing import Any

from core.checkin_tracker import METRIC_TRACKING_META
from core.schema import ModuleEvaluationResult, StatusLight

PHYSIOLOGICAL_MODULES: set[str] = {
    "cardiovascular",
    "musculoskeletal",
    "neuro_ocular",
    "immune_metabolic",
}

SEVERITY_RANK: dict[StatusLight, int] = {
    "GREEN": 0,
    "YELLOW": 1,
    "RED": 2,
}

# Mapping from module_id -> metric_name -> payload keys that activate (light up) that metric on Day-1 Standby
METRIC_ACTIVATION_KEYS: dict[str, dict[str, set[str]]] = {
    "cardiovascular": {
        "rest_hr_bpm": {"rest_hr_bpm"},
        "sbp_mmHg": {"sbp_mmHg", "dbp_mmHg"},
        "spo2_pct": {"spo2_pct"},
        "resp_rate_bpm": {"resp_rate_bpm"},
        "stand_hr_rise_bpm": {"stand_hr_rise_bpm", "dizzy"},
        "ijv_flow_status": {"ijv_flow"},
        "pvc_burden_pct": {"pvc_burden_pct"},
        "steady_hr_150w_bpm": {"steady_hr_150w_bpm"},
        "gls_change_pct": {"gls_change_pct"},
        "plasma_volume_delta_pct": {"hb_g_dl", "hct_pct"},
        "potassium_mmol_l": {"potassium_mmol_l"},
    },
    "musculoskeletal": {
        "body_mass_kg": {"body_mass_kg"},
        "iso_peak_force_n": {"iso_peak_force_n"},
        "velocity_loss_pct": {"velocity_loss_pct"},
        "e4d_s_bone_index": {"iso_peak_force_n", "velocity_loss_pct", "peak_force_n"},
        "csa_thigh_cm2": {"csa_thigh_cm2"},
        "csa_calf_cm2": {"csa_calf_cm2", "csa_thigh_cm2"},
        "ntx_bone_resorption": {"ntx", "ctx"},
        "ctx_bone_resorption": {"ctx"},
        "p1np_bone_formation": {"p1np", "ctx"},
        "est_monthly_bone_loss_pct": {"iso_peak_force_n", "velocity_loss_pct", "csa_thigh_cm2", "ctx"},
        "osd575_ca_alp_baseline": set(),  # Pre-flight reference is always visible
    },
    "neuro_ocular": {
        "delta_trt_um": {"delta_trt_um"},
        "delta_v_onh_mm3": {"delta_v_onh_mm3", "delta_trt_um"},
        "onsd_mm": {"onsd_mm"},
        "sph_eq_shift_d": {"sph_eq_shift_d", "amsler_result"},
        "vor_gain": {"vor_gain", "amsler_result"},
    },
    "immune_metabolic": {
        "oral_temp_c": {"temp_c"},
        "hydration_ml": {"hydration_ml"},
        "lymphocytes_10e9_l": {"lymph", "wbc"},
        "saliva_vzv_copies_ml": {"saliva_vzv"},
        "crp_mg_l": {"crp_mg_l", "wbc"},
    },
}

STANDBY_SUMMARY_NOTES: dict[str, str] = {
    "cardiovascular": "Pre-flight baseline loaded. Awaiting Day-1 Morning Vitals or LBNP/Ultrasound check-in.",
    "musculoskeletal": "Pre-flight baseline loaded. Awaiting SLAMMD body mass & E4D / Ultrasound check-in.",
    "neuro_ocular": "Pre-flight baseline loaded. Awaiting Amsler grid, refraction & Mini OCT / ONSD check-in.",
    "immune_metabolic": "Pre-flight baseline loaded. Awaiting Day-1 Oral Temp, Hydration & CBC / Saliva check-in.",
}

STANDBY_IMMEDIATE_ACTIONS: dict[str, str] = {
    "cardiovascular": "Onboarding Check-In: Log morning resting HR, BP, and SpO2 in Crew Daily Log.",
    "musculoskeletal": "Onboarding Check-In: Log morning SLAMMD body mass and initial E4D session metrics.",
    "neuro_ocular": "Onboarding Check-In: Perform baseline Amsler grid & visual acuity check-in.",
    "immune_metabolic": "Onboarding Check-In: Log morning oral temperature, 24h fluid intake, and symptoms.",
}


def collect_logged_keys_for_crew(
    checkin_series: dict[str, Any],
    crew_id: str,
    max_mission_day: int,
) -> tuple[set[str], set[str]]:
    """Return (logged_value_keys, checked_module_ids) recorded for `crew_id` up to `max_mission_day`."""
    crew_map = (checkin_series or {}).get(crew_id, {})
    if not isinstance(crew_map, dict):
        return set(), set()

    logged_keys: set[str] = set()
    checked_mods: set[str] = set()
    for day_key, entry in crew_map.items():
        if not isinstance(entry, dict):
            continue
        try:
            d_num = int(entry.get("mission_day", day_key))
        except (TypeError, ValueError):
            continue
        if d_num > max_mission_day:
            continue
        vals = entry.get("values")
        if isinstance(vals, dict):
            for k, v in vals.items():
                if v is not None:
                    logged_keys.add(str(k))
        for m in entry.get("checked_modules", []):
            checked_mods.add(str(m))
    return logged_keys, checked_mods


def apply_day1_standby_mask(
    results: dict[str, ModuleEvaluationResult],
    data_lifecycle_mode: str,
    checkin_series: dict[str, Any],
    crew_id: str,
    mission_day: int,
    use_manual_overrides: bool = False,
    scenario: str = "green",
) -> dict[str, ModuleEvaluationResult]:
    """Apply Hardware-Auto vs. Crew-Physiological Standby masking when in `day1_standby` mode."""
    if data_lifecycle_mode != "day1_standby" or use_manual_overrides or scenario != "green":
        return results

    logged_keys, checked_mods = collect_logged_keys_for_crew(
        checkin_series=checkin_series,
        crew_id=crew_id,
        max_mission_day=mission_day,
    )

    for mod_id, res in results.items():
        if mod_id not in PHYSIOLOGICAL_MODULES:
            # Cabin & Radiation sensors run automatically on spacecraft power-up
            res.standby = False
            continue

        mod_act_map = METRIC_ACTIVATION_KEYS.get(mod_id, {})
        active_statuses: list[StatusLight] = []
        active_count = 0

        for metric in res.metrics:
            is_ref = (
                metric.raw_status == "REFERENCE"
                or metric.metric_name in {"osd575_ca_alp_baseline", "p1np_bone_formation"}
            )
            req_keys = mod_act_map.get(metric.metric_name)
            if req_keys is None:
                is_measured = mod_id in checked_mods
            elif len(req_keys) == 0:
                is_measured = True
            else:
                is_measured = bool(req_keys & logged_keys)

            if is_measured:
                metric.standby = False
                if not is_ref:
                    active_count += 1
                    active_statuses.append(metric.status_light)
                # Ensure clean D0 -> D_now trajectory rather than Day-124 demo history in day1_standby mode
                meta = METRIC_TRACKING_META.get(metric.metric_name)
                if meta and metric.history_days and max(metric.history_days) > mission_day:
                    base_v = metric.baseline_val if isinstance(metric.baseline_val, (int, float)) else meta.get("baseline_default", 0.0)
                    cur_v = metric.current_val if isinstance(metric.current_val, (int, float)) else base_v
                    metric.history_days = [0, mission_day]
                    metric.history_values = [float(base_v), float(cur_v)]
            else:
                metric.standby = True
                metric.status_light = "GREEN"
                metric.raw_status = "STANDBY"
                metric.watch_flag = False
                metric.delta_pct = None
                metric.slope_per_day = None
                base_num = metric.baseline_val
                meta = METRIC_TRACKING_META.get(metric.metric_name)
                if meta:
                    if metric.yellow_threshold is None and meta.get("yellow_threshold") is not None:
                        metric.yellow_threshold = float(meta["yellow_threshold"])
                    if metric.red_threshold is None and meta.get("red_threshold") is not None:
                        metric.red_threshold = float(meta["red_threshold"])
                    if base_num is None and meta.get("baseline_default") is not None:
                        base_num = float(meta["baseline_default"])
                        metric.baseline_val = base_num
                if isinstance(base_num, (int, float)):
                    metric.history_days = [0]
                    metric.history_values = [float(base_num)]
                else:
                    metric.history_days = []
                    metric.history_values = []
                base_str = f"{base_num} {metric.unit}".strip() if base_num is not None else "loaded"
                metric.message = f"Pre-flight baseline ({base_str}) ready. Awaiting crew check-in."
                metric.action = "Open Crew Daily Log to record initial in-orbit measurement."

        if active_count == 0:
            res.standby = True
            res.status_light = "GREEN"
            res.raw_status = "STANDBY"
            res.watch_flag = False
            res.summary_note = STANDBY_SUMMARY_NOTES.get(mod_id, "Pre-flight baseline loaded. Awaiting first check-in.")
            res.short_term_plan.next_measurement_in_hours = 0
            res.short_term_plan.urgent_alert = False
            res.short_term_plan.immediate_actions = [
                STANDBY_IMMEDIATE_ACTIONS.get(mod_id, "Log initial check-in values in Crew Daily Log.")
            ]
            res.long_term_plan.days_until_red_prediction = None
        else:
            res.standby = False
            worst_active = max(active_statuses, key=lambda s: SEVERITY_RANK.get(s, 0)) if active_statuses else "GREEN"
            res.status_light = worst_active
            res.raw_status = worst_active
            if worst_active == "GREEN":
                res.short_term_plan.urgent_alert = False
                if res.short_term_plan.next_measurement_in_hours == 0:
                    res.short_term_plan.next_measurement_in_hours = 24

    return results
