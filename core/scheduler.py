"""Global closed-loop scheduler & cross-module safety conflict resolver.

Role 1 exclusively owns this file. Collects short_term_plan and long_term_plan
from all 5 domain evaluations and enforces cross-system medical safety overrides.
"""

from __future__ import annotations

from typing import Any, Optional

from core.schema import ModuleEvaluationResult, StatusLight

SEVERITY_RANK: dict[StatusLight, int] = {
    "GREEN": 0,
    "YELLOW": 1,
    "RED": 2,
}


def _worst_status(statuses: list[StatusLight]) -> StatusLight:
    if not statuses:
        return "GREEN"
    return max(statuses, key=lambda s: SEVERITY_RANK.get(s, 0))


def aggregate_mission_schedule(
    results: dict[str, ModuleEvaluationResult],
    cross_context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Aggregate 0-48h triage plans and 7-30d regimen plans with safety conflict resolution."""
    ctx = cross_context or {}

    overall_status = _worst_status([res.status_light for res in results.values()])
    urgent_modules = [
        mod_id
        for mod_id, res in results.items()
        if res.short_term_plan.urgent_alert or res.status_light == "RED"
    ]

    short_term_items: list[dict[str, Any]] = []
    long_term_items: list[dict[str, Any]] = []
    conflicts_resolved: list[dict[str, str]] = []

    for mod_id, res in results.items():
        stp = res.short_term_plan
        ltp = res.long_term_plan

        for act in stp.immediate_actions:
            short_term_items.append(
                {
                    "module_id": mod_id,
                    "status_light": res.status_light,
                    "next_hours": stp.next_measurement_in_hours,
                    "urgent_alert": stp.urgent_alert,
                    "action": act,
                }
            )

        for adj in ltp.adjustment_list:
            long_term_items.append(
                {
                    "module_id": mod_id,
                    "status_light": res.status_light,
                    "days_until_red": ltp.days_until_red_prediction,
                    "adjustment": adj,
                }
            )

    # --- Cross-System Conflict Resolution Rules ---
    cardio = results.get("cardiovascular")
    immune = results.get("immune_metabolic")
    musculo = results.get("musculoskeletal")
    neuro = results.get("neuro_ocular")
    cabin = results.get("cabin_environment")

    # Conflict Rule 1: Halt heavy E4D resistance workouts if Cardiovascular or Immune is RED
    cardio_red = cardio is not None and cardio.status_light == "RED"
    immune_red = immune is not None and immune.status_light == "RED"
    if cardio_red or immune_red:
        reasons = []
        if cardio_red:
            reasons.append("Cardiovascular RED (arrhythmia / IJV thrombosis / hemodynamic alert)")
        if immune_red:
            reasons.append("Immune RED (fever / acute inflammatory or viral reactivation alert)")

        conflict_msg = (
            "SAFETY OVERRIDE: Heavy E4D axial resistance loading & maximal CEVIS intervals SUSPENDED "
            f"due to {' & '.join(reasons)}. Switch to light passive ROM / hydration monitoring only."
        )
        conflicts_resolved.append(
            {
                "rule": "HALT_HEAVY_EXERCISE_ON_CARDIO_OR_IMMUNE_RED",
                "affected_module": "musculoskeletal",
                "resolution": conflict_msg,
            }
        )
        short_term_items.insert(
            0,
            {
                "module_id": "scheduler_override",
                "status_light": "RED",
                "next_hours": 1,
                "urgent_alert": True,
                "action": conflict_msg,
            },
        )
        if musculo is not None:
            long_term_items.insert(
                0,
                {
                    "module_id": "scheduler_override",
                    "status_light": "RED",
                    "days_until_red": musculo.long_term_plan.days_until_red_prediction,
                    "adjustment": "Hold high-load E4D squats/deadlifts until Cardiovascular & Immune return to YELLOW/GREEN.",
                },
            )

    # Conflict Rule 2: SPE Radiation Shelter-in-Place overrides scheduled exercise & triggers 48h lymphocyte check
    spe_active = bool(ctx.get("spe_alert", False))
    if not spe_active and cabin is not None:
        for m in cabin.metrics:
            if m.metric_name.lower() in {"spe_alert", "proton_flux_10mev_pfu"} and m.status_light == "RED":
                spe_active = True
                break

    if spe_active:
        spe_msg = (
            "SPE SHELTER OVERRIDE: Relocate crew to Water Wall / storm shelter immediately. "
            "Defer non-essential E4D/CEVIS sessions and schedule mandatory 48h post-SPE CBC lymphocyte check."
        )
        conflicts_resolved.append(
            {
                "rule": "SPE_SHELTER_AND_48H_LYMPHOCYTE_CHECK",
                "affected_module": "cabin_environment -> immune_metabolic & musculoskeletal",
                "resolution": spe_msg,
            }
        )
        short_term_items.insert(
            0,
            {
                "module_id": "scheduler_override",
                "status_light": "RED",
                "next_hours": 0,
                "urgent_alert": True,
                "action": spe_msg,
            },
        )

    # Conflict Rule 3: Elevated cabin ppCO2 (>2.5 mmHg) + SANS Yellow/Red -> prioritize CDRA/MCA scrubbing
    co2_val = ctx.get("ppco2_1h_mmHg")
    try:
        co2_high = co2_val is not None and float(co2_val) >= 2.5
    except (TypeError, ValueError):
        co2_high = False

    if co2_high and neuro is not None and neuro.status_light in {"YELLOW", "RED"}:
        co2_msg = (
            f"CO2-SANS SYNERGY ALERT: Cabin ppCO2 ({float(co2_val):.2f} mmHg) elevates intracranial "
            "venous congestion risk alongside Neuro-Ocular findings. Prioritize CDRA scrubber inspection "
            "and avoid head-down tilt or prolonged supine posture."
        )
        conflicts_resolved.append(
            {
                "rule": "CO2_SANS_SYNERGY_MITIGATION",
                "affected_module": "cabin_environment -> neuro_ocular",
                "resolution": co2_msg,
            }
        )
        short_term_items.insert(
            0,
            {
                "module_id": "scheduler_override",
                "status_light": "YELLOW" if neuro.status_light == "YELLOW" else "RED",
                "next_hours": 6,
                "urgent_alert": neuro.status_light == "RED",
                "action": co2_msg,
            },
        )

    # Sort short-term items by severity then shortest next measurement hours
    short_term_items.sort(
        key=lambda item: (
            -SEVERITY_RANK.get(item["status_light"], 0),
            item.get("next_hours", 999),
        )
    )

    # Sort long-term items by shortest days_until_red_prediction then severity
    long_term_items.sort(
        key=lambda item: (
            item["days_until_red"] if item["days_until_red"] is not None else 9999,
            -SEVERITY_RANK.get(item["status_light"], 0),
        )
    )

    next_check_hours = min(
        [res.short_term_plan.next_measurement_in_hours for res in results.values()],
        default=24,
    )
    earliest_red_days_candidates = [
        res.long_term_plan.days_until_red_prediction
        for res in results.values()
        if res.long_term_plan.days_until_red_prediction is not None
    ]
    earliest_red_days = min(earliest_red_days_candidates) if earliest_red_days_candidates else None

    return {
        "overall_status": overall_status,
        "urgent_modules": urgent_modules,
        "next_check_hours": next_check_hours,
        "earliest_red_days": earliest_red_days,
        "conflicts_resolved": conflicts_resolved,
        "short_term_board": short_term_items,
        "long_term_board": long_term_items,
    }
