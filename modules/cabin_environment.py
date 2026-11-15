"""Role 6: Radiation, Acoustics & Closed-Habitat Module (Z.O.S.M.A.).

Top-level orchestrator ("Chief Medical Officer") for the 17 Measurement Cards:
- Hydrates CSV/JSON file inputs (`_ingest_loaded_csv_payload`) and HUD slider overrides (`_detect_flat_overrides`).
- Dispatches domain diagnostics across `radiation`, `acoustics`, `atmosphere`, and `isolation`.
- Aggregates 17 card assessments into a unified `ModuleEvaluationResult` (`evaluate`, `to_schema`)
  and propagates cross-module flags (`spe_alert`, `ppco2_1h_mmHg`, `sleep_h`).
- Re-exports `demo_baseline`, `demo_payload`, and `export_demo_csvs` for zero-conflict integration.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from core.schema import ModuleEvaluationResult, normalize_module_result

from modules.cabin_env.acoustics import (
    _eval_aco01,
    _eval_aco02,
    _eval_aco03,
)
from modules.cabin_env.atmosphere import (
    _eval_atm01,
    _eval_atm02,
    _eval_atm03,
    _eval_atm04,
    _eval_atm05,
    _eval_atm06,
    _eval_atm07,
)
from modules.cabin_env.card_helpers import is_in_saa
from modules.cabin_env.demo_data import (
    _make_timestamps_utc,
    demo_baseline,
    demo_payload,
    export_demo_csvs,
)
from modules.cabin_env.isolation import (
    _eval_iso01,
    _eval_iso02,
    _eval_iso03,
    _eval_iso04,
)
from modules.cabin_env.measurement_rules import (
    AUDIO_FREQS_HZ,
    CARD_IDS,
    DATA_DIR,
    OCTAVE_FREQS_HZ,
    RULE_TABLE,
    get_rule_table_dicts,
)
from modules.cabin_env.radiation import (
    _eval_rad01,
    _eval_rad02,
    _eval_rad03,
)


def _ingest_loaded_csv_payload(pay: dict[str, Any], default_green: dict[str, Any]) -> None:
    """When core/data_loader.py loads CSVs/JSONs (`csv_<stem>`), hydrate structured card inputs."""
    if not pay.get("_loaded_files"):
        return
    if "csv_rad01_area_dose" in pay and "rad01_records" not in pay:
        pay["rad01_records"] = pay["csv_rad01_area_dose"]
    if "csv_rad02_crew_dose_daily" in pay and "rad02_daily" not in pay:
        rows = pay["csv_rad02_crew_dose_daily"]
        if rows:
            last = rows[-1]
            c_h = float(last.get("columbus_hours", 16.0))
            h_h = float(last.get("harmony_hours", 8.0))
            c_r = float(last.get("columbus_dose_rate_uGy_h", 4.10))
            h_r = float(last.get("harmony_dose_rate_uGy_h", 4.25))
            tot_msv = float(last.get("career_dose_mSv", 152.0))
            pay["rad02_daily"] = {
                "timestamp_utc": str(last.get("timestamp_utc", default_green["timestamp_utc"])),
                "career_prior_mSv": tot_msv - 28.0,
                "mission_cum_mSv": 28.0,
                "single_spe_mSv": float(last.get("single_spe_mSv", 0.0)),
                "occupancy_hours": {"Columbus": c_h, "Harmony": h_h},
                "module_dose_rates_uGy_h": {"Columbus": c_r, "Harmony": h_r},
                "history_5d_career_mSv": [float(r.get("career_dose_mSv", tot_msv)) for r in rows[-5:]],
            }
    if "csv_aco01_module_spl" in pay and "aco01_survey" not in pay:
        rows = pay["csv_aco01_module_spl"]
        if rows:
            r0 = dict(rows[-1])
            bands = {hz: float(r0.get(f"hz_{hz}_dB", 45.0)) for hz in OCTAVE_FREQS_HZ if f"hz_{hz}_dB" in r0}
            r0["octave_bands_dB"] = bands
            pay["aco01_survey"] = r0
    if "csv_aco02_crew_dosimetry" in pay and "aco02_dosimetry" not in pay:
        rows = pay["csv_aco02_crew_dosimetry"]
        if rows:
            pay["aco02_dosimetry"] = dict(rows[-1])
    if "csv_aco03_audiogram" in pay and "aco03_audiogram" not in pay:
        rows = pay["csv_aco03_audiogram"]
        if rows:
            right_map, left_map = {}, {}
            meta = dict(rows[-1])
            for r in rows:
                ear_d = {hz: float(r.get(f"hz_{hz}_dB", 10.0)) for hz in AUDIO_FREQS_HZ}
                if str(r.get("ear", "")).lower() == "left":
                    left_map = ear_d
                else:
                    right_map = ear_d
            pay["aco03_audiogram"] = {
                "timestamp_utc": str(meta.get("timestamp_utc", default_green["timestamp_utc"])),
                "ambient_above_nc40": bool(meta.get("ambient_above_nc40", False)),
                "max_repeat_diff_dB": float(meta.get("max_repeat_diff_dB", 5.0)),
                "retest_confirmed": bool(meta.get("retest_confirmed", True)),
                "right_ear_dB": right_map or default_green["aco03_audiogram"]["right_ear_dB"],
                "left_ear_dB": left_map or default_green["aco03_audiogram"]["left_ear_dB"],
            }
    if "csv_atm01_co2" in pay and "atm01_co2" not in pay:
        rows = pay["csv_atm01_co2"]
        if rows:
            pay["atm01_co2"] = {
                "records_1h": rows,
                "step_change_1min_ppm": 20.0,
                "step_second_sensor_confirmed": True,
                "mean_7d_ppm": float(rows[-1].get("ppco2_7d_mmHg", 1.80)) / (1e-6 * 760.0),
            }
    if "csv_atm02_pressure_o2" in pay and "atm02_pressure" not in pay:
        pay["atm02_pressure"] = {"records_1m": pay["csv_atm02_pressure_o2"]}
    if "csv_atm03_thermal" in pay and "atm03_thermal" not in pay:
        pay["atm03_thermal"] = {"records_1h": pay["csv_atm03_thermal"]}
    if "csv_atm04_voc" in pay and "atm04_voc" not in pay:
        rows = pay["csv_atm04_voc"]
        if rows:
            r0 = rows[-1]
            pay["atm04_voc"] = {
                "timestamp_utc": str(r0.get("timestamp_utc", default_green["timestamp_utc"])),
                "internal_cal_passed": bool(r0.get("internal_cal_passed", True)),
                "combustion_alarm": bool(r0.get("combustion_alarm", False)),
                "ammonia_alarm": bool(r0.get("ammonia_alarm", False)),
                "compounds": [
                    {
                        "name": str(r.get("compound", "voc")),
                        "conc_mg_m3": float(r.get("conc_mg_m3", 0.1)),
                        "smac_mg_m3": float(r.get("smac_mg_m3", 10.0)),
                        "duration": str(r.get("duration", "7d")),
                    }
                    for r in rows
                ],
            }
    if "csv_atm05_water_chem" in pay and "atm05_water" not in pay:
        rows = pay["csv_atm05_water_chem"]
        if rows:
            pay["atm05_water"] = dict(rows[-1])
    if "csv_atm06_microbial" in pay and "atm06_microbial" not in pay:
        rows = pay["csv_atm06_microbial"]
        if rows:
            r0 = dict(rows[-1])
            # Safety check to avoid ValueError on literal string list parsing from CSV
            if isinstance(r0.get("history_5_limit_ratio"), str):
                import ast
                try:
                    r0["history_5_limit_ratio"] = ast.literal_eval(r0["history_5_limit_ratio"])
                except Exception:
                    r0["history_5_limit_ratio"] = [float(r0.get("air_bacteria_cfu_m3", 140.0))/1000.0] * 5
            
            if isinstance(r0.get("history_5_timestamps"), str):
                import ast
                try:
                    r0["history_5_timestamps"] = ast.literal_eval(r0["history_5_timestamps"])
                except Exception:
                    r0["history_5_timestamps"] = _make_timestamps_utc(r0.get("timestamp_utc", "2026-11-14T12:00:00Z"), 5, 129600.0)

            pay["atm06_microbial"] = r0
    if "csv_atm07_particulates" in pay and "atm07_particulates" not in pay:
        pay["atm07_particulates"] = {"records_1h": pay["csv_atm07_particulates"]}
    if "csv_iso01_sleep" in pay and "iso01_sleep" not in pay:
        pay["iso01_sleep"] = {"nights": pay["csv_iso01_sleep"]}
    if "csv_iso02_pvt" in pay and "iso02_pvt" not in pay:
        pay["iso02_pvt"] = {"sessions": pay["csv_iso02_pvt"]}
    if "csv_iso03_mood" in pay and "iso03_mood" not in pay:
        pay["iso03_mood"] = {"entries": pay["csv_iso03_mood"]}
    if "csv_iso04_light" in pay and "iso04_light" not in pay:
        pay["iso04_light"] = {"days": pay["csv_iso04_light"]}


def _detect_flat_overrides(raw_payload: Optional[dict[str, Any]], merged_pay: dict[str, Any]) -> None:
    """Detect when a caller/UI slider overrides flat scalar keys without updating structured card dicts."""
    if not raw_payload:
        return
    scen = str(raw_payload.get("scenario", "green")).strip().lower()
    ref_scen = demo_payload(scen if scen in {"green", "yellow", "red", "bad_data"} else "green")
    flat_keys = (
        "proton_flux_10mev_pfu",
        "spe_alert",
        "dose_rate_uGy_h",
        "saa_pass",
        "career_dose_mSv",
        "module_spl_dBA",
        "crew_leq8_dBA",
        "daily_noise_dose_pct",
        "ppco2_1h_mmHg",
        "ppco2_7d_mmHg",
        "co2_sensor_stuck_hours",
        "p_total_kPa",
        "pio2_mmHg",
        "dpdt_kPa_per_min",
        "temp_C",
        "rh_pct",
        "max_smac_ratio",
        "ammonia_or_fire_alarm",
        "sleep_tst_h",
        "pvt_speed_1_per_s",
        "workload_bedford",
        "stress_vas",
    )
    has_structured = any(
        k in raw_payload
        for k in (
            "rad01_records", "rad02_daily", "rad03_goes",
            "aco01_survey", "aco02_dosimetry", "aco03_audiogram",
            "atm01_co2", "atm02_pressure", "atm03_thermal", "atm04_voc",
            "iso01_sleep", "iso02_pvt", "iso03_mood", "iso04_light",
        )
    )
    for k in flat_keys:
        if k in raw_payload:
            # Apply override if caller didn't supply structured card dicts OR value differs from preset
            if (not has_structured and not raw_payload.get("_loaded_files")) or raw_payload[k] != ref_scen.get(k):
                merged_pay[f"_override_{k}"] = raw_payload[k]


def evaluate(
    payload: Optional[dict[str, Any]] = None,
    baseline: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Stateless evaluation across all 17 Measurement Cards (RAD-01..03, ACO-01..03, ATM-01..07, ISO-01..04).

    Returns a top-level dict compatible with `core/schema.py` (`ModuleEvaluationResult`),
    plus `cards` (dict of 17 individual `ModuleAssessment` objects), `assessments` (ordered list),
    `rule_table`, `notify`, `decision_owner = "human"`, and cross-module flags.
    """
    base = {**demo_baseline(), **(baseline or {})}
    default_green = demo_payload("green")
    raw_pay = dict(payload or {})
    _ingest_loaded_csv_payload(raw_pay, default_green)
    pay = {**default_green, **raw_pay}
    _detect_flat_overrides(payload, pay)

    crew_id = str(pay.get("crew_id") or base.get("crew_id") or "C002")
    mission_day = int(pay.get("mission_day", 124))
    ts_utc = str(pay.get("timestamp_utc", "2026-11-14T12:00:00Z"))
    location = str(pay.get("location", "Columbus"))
    data_source = str(pay.get("data_source", "SIMULATED")).upper()
    if data_source not in {"REAL", "SIMULATED"}:
        data_source = "SIMULATED"

    # Pre-check whether RAD-01 non-SAA series is rising (needed by RAD-03 S2+ Red rule)
    r01_recs = list(pay.get("rad01_records") or [])
    r01_non_saa = [
        float(r["dose_rate_uGy_h"])
        for r in r01_recs
        if r.get("dose_rate_uGy_h") is not None
        and float(r["dose_rate_uGy_h"]) > 0
        and not is_in_saa(r.get("lat_deg"), r.get("lon_deg"))
    ]
    rad01_rising = (
        len(r01_non_saa) >= 2 and r01_non_saa[-1] > r01_non_saa[0]
    ) or (
        pay.get("_override_dose_rate_uGy_h") is not None
        and float(pay["_override_dose_rate_uGy_h"]) > 2.0 * float(base.get("rad01_columbus_median_uGy_h", 4.06))
    )

    # Evaluate all 17 cards
    card_rad03, rad03_meta = _eval_rad03(pay, rad01_rising, mission_day, ts_utc, location, data_source)
    card_rad01 = _eval_rad01(pay, base, rad03_meta, mission_day, ts_utc, location, data_source)
    card_rad02 = _eval_rad02(pay, base, crew_id, mission_day, ts_utc, location, data_source)

    card_aco01 = _eval_aco01(pay, base, mission_day, ts_utc, location, data_source)
    card_aco02 = _eval_aco02(pay, base, crew_id, mission_day, ts_utc, location, data_source)
    card_aco03 = _eval_aco03(pay, base, crew_id, mission_day, ts_utc, location, data_source)

    card_atm01, ppco2_val = _eval_atm01(pay, base, mission_day, ts_utc, location, data_source)
    card_atm02 = _eval_atm02(pay, base, mission_day, ts_utc, location, data_source)
    card_atm03 = _eval_atm03(pay, base, mission_day, ts_utc, location, data_source)
    card_atm04 = _eval_atm04(pay, base, mission_day, ts_utc, location, data_source)
    card_atm05 = _eval_atm05(pay, base, mission_day, ts_utc, location, data_source)
    card_atm06 = _eval_atm06(pay, base, mission_day, ts_utc, location, data_source)
    card_atm07 = _eval_atm07(pay, base, mission_day, ts_utc, location, data_source)

    card_iso01, sleep_val = _eval_iso01(pay, base, crew_id, mission_day, ts_utc, location, data_source)
    card_iso02 = _eval_iso02(pay, base, crew_id, mission_day, ts_utc, location, data_source)
    card_iso03 = _eval_iso03(pay, base, crew_id, mission_day, ts_utc, location, data_source)
    card_iso04 = _eval_iso04(pay, base, card_iso01["overall_status"], crew_id, mission_day, ts_utc, location, data_source)

    ordered_cards = [
        card_rad01, card_rad02, card_rad03,
        card_aco01, card_aco02, card_aco03,
        card_atm01, card_atm02, card_atm03, card_atm04, card_atm05, card_atm06, card_atm07,
        card_iso01, card_iso02, card_iso03, card_iso04,
    ]
    cards_by_id = {c["module_id"]: c for c in ordered_cards}

    card_statuses = [c["overall_status"] for c in ordered_cards]
    any_qc_fail = any(not c["quality_passed"] for c in ordered_cards)
    all_no_data = all(st == "no_data" for st in card_statuses)

    if "red" in card_statuses:
        overall_guide_status = "red"
        schema_status_light = "RED"
    elif "yellow" in card_statuses:
        overall_guide_status = "yellow"
        schema_status_light = "YELLOW"
    elif all_no_data or any_qc_fail:
        overall_guide_status = "no_data"
        schema_status_light = "NO_DATA"
    else:
        overall_guide_status = "green"
        schema_status_light = "GREEN"

    quality_passed = not any_qc_fail

    # Flatten primary indicator from each of the 17 cards (plus extra key indicators) into unified list
    unified_indicators: list[dict[str, Any]] = []
    for c in ordered_cards:
        # Propagate the card's 3-step guidance text down to each indicator so the UI can bind to it
        card_how_to = c.get("guidance", {}).get("how_to_measure", "")
        card_plain = c.get("guidance", {}).get("plain_explanation", "")
        card_steps = c.get("guidance", {}).get("action_protocol", [])
        for ind in c["indicators"]:
            ind_copy = dict(ind)
            if card_how_to:
                ind_copy["how_to_measure"] = card_how_to
            if card_plain:
                ind_copy["plain_explanation"] = card_plain
            if card_steps:
                ind_copy["action_steps"] = card_steps
            elif ind_copy.get("action"):
                ind_copy["action_steps"] = [ind_copy["action"]]
            unified_indicators.append(ind_copy)

    # Aggregate short_term_plan (Conclusion & actions for current status) and long_term_plan (Routine protection & countermeasures)
    short_actions: list[str] = []
    routine_actions: list[str] = []
    for c in ordered_cards:
        if c["overall_status"] in {"red", "yellow", "no_data"}:
            for act in c["short_term_plan"]["immediate_actions"]:
                tagged = f"[{c['module_id']}] {act}"
                if tagged not in short_actions:
                    short_actions.append(tagged)
        for r_act in c["long_term_plan"]["routine_prescription_adjustment"]:
            tagged_r = f"[{c['module_id']}] {r_act}"
            if tagged_r not in routine_actions:
                routine_actions.append(tagged_r)

    if not short_actions:
        short_actions = ["All 17 Radiation, Acoustics, Atmosphere, and Isolation cards nominal; continue scheduled monitoring."]
    if overall_guide_status == "red":
        short_actions.append("Decision support notice: all Red actions require final human decision (decision_owner = 'human').")

    next_hours = min(c["short_term_plan"]["next_measurement_in_hours"] for c in ordered_cards)
    pred_days = [
        c["long_term_plan"]["days_until_red_prediction"]
        for c in ordered_cards
        if c["long_term_plan"]["days_until_red_prediction"] is not None
    ]
    earliest_days = 0 if overall_guide_status == "red" else (min(pred_days) if pred_days else None)

    agg_notify = {
        "crew": any(c["notify"]["crew"] for c in ordered_cards),
        "ground": any(c["notify"]["ground"] for c in ordered_cards),
        "flight_surgeon": any(c["notify"]["flight_surgeon"] for c in ordered_cards),
        "iso03_private_conference_crew_choice": bool(card_iso03["notify"].get("private_conference_crew_choice", False)),
    }

    red_cards = [c["module_id"] for c in ordered_cards if c["overall_status"] == "red"]
    yel_cards = [c["module_id"] for c in ordered_cards if c["overall_status"] == "yellow"]
    nod_cards = [c["module_id"] for c in ordered_cards if c["overall_status"] == "no_data"]
    summary_parts = [f"17-Card Status: {overall_guide_status.upper()}"]
    if red_cards:
        summary_parts.append(f"RED={','.join(red_cards)}")
    if yel_cards:
        summary_parts.append(f"YELLOW={','.join(yel_cards)}")
    if nod_cards:
        summary_parts.append(f"NO_DATA/QC={','.join(nod_cards)}")

    spe_flag = bool(rad03_meta.get("spe_confirmed") or rad03_meta.get("s1_active"))

    return {
        "module_id": "cabin_environment",
        "body_part_tag": ["whole_body", "lungs", "brain", "ears"],
        "crew_id": crew_id,
        "mission_day": mission_day,
        "timestamp_utc": ts_utc,
        "location": location,
        "overall_status": overall_guide_status,
        "status_light": schema_status_light,
        "quality_passed": quality_passed,
        "quality_notes": [f"{c['module_id']}: {n}" for c in ordered_cards for n in c["quality_notes"]],
        "data_source": data_source,
        "decision_owner": "human",
        "notify": agg_notify,
        "summary_note": " | ".join(summary_parts),
        "indicators": unified_indicators,
        "metrics": unified_indicators,
        "guidance": {
            "how_to_measure": (
                "Execute Layer-0 QC checks across DOSTEL/GOES radiation, Type-1 SLM/dosimeter/OOHA acoustics, "
                "MCA/CDRA/THC/AQM/TOCA/microbial habitat loops, and Actiwatch/PVT-B/Bedford behavioral assays."
            ),
            "plain_explanation": (
                "Integrates 17 closed-habitat, radiation, acoustic, and circadian-isolation cards across 3 NASA RIDGE hazards "
                "to provide autonomous offline decision support (all Red actions end with a human decision)."
            ),
            "action_protocol": short_actions[:8],
        },
        "short_term_plan": {
            "next_measurement_in_hours": next_hours,
            "immediate_actions": short_actions[:10],
            "urgent_alert": overall_guide_status == "red",
        },
        "long_term_plan": {
            "days_until_red_prediction": earliest_days,
            "routine_prescription_adjustment": routine_actions[:10],
        },
        # Card-level assessments and Rule Table required by v2 Guide
        "cards": cards_by_id,
        "assessments": ordered_cards,
        "rule_table": get_rule_table_dicts(),
        # Cross-module context flags for Role 4 (Neuro-Ocular) & Role 5 (Immune)
        "spe_event_flag": spe_flag,
        "spe_alert": spe_flag,
        "ppco2_mmhg": ppco2_val,
        "ppco2_1h_mmHg": ppco2_val,
        "sleep_h": sleep_val,
    }


def to_schema(
    evaluation_or_payload: Optional[dict[str, Any]] = None,
    baseline: Optional[dict[str, Any]] = None,
    card_id: Optional[str] = None,
) -> ModuleEvaluationResult:
    """Map an evaluation result (top-level or individual card) into `core/schema.py` ModuleEvaluationResult.

    - `short_term_plan` = the card's Conclusion & actions for the current status.
    - `long_term_plan` = the card's Routine protection & countermeasures.
    """
    if (
        isinstance(evaluation_or_payload, dict)
        and "cards" in evaluation_or_payload
        and "assessments" in evaluation_or_payload
    ):
        ev = evaluation_or_payload
    elif (
        isinstance(evaluation_or_payload, dict)
        and evaluation_or_payload.get("module_id") in CARD_IDS
        and "indicators" in evaluation_or_payload
    ):
        card_doc = dict(evaluation_or_payload)
        if card_doc.get("crew_id") is None:
            card_doc["crew_id"] = "ENV_MODULE"
        return normalize_module_result(card_doc, module_id=str(card_doc["module_id"]))
    else:
        ev = evaluate(payload=evaluation_or_payload, baseline=baseline)

    if card_id is not None:
        cid = card_id.strip().upper()
        card_doc = dict(ev["cards"][cid])
        if card_doc.get("crew_id") is None:
            card_doc["crew_id"] = "ENV_MODULE"
        return normalize_module_result(card_doc, module_id=cid)

    return normalize_module_result(ev, module_id="cabin_environment")


def _run_self_verification() -> None:
    """Proactively inspect data/cabin_environment/, export templates if empty, and assert all v2 rules."""
    import re

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted([p.name for p in DATA_DIR.iterdir() if p.is_file()])
    if not existing:
        print(f"[INFO] {DATA_DIR} was empty -> exporting 17 starter CSV/JSON templates...")
        written = export_demo_csvs()
        print(f"[INFO] Exported {len(written)} template files into {DATA_DIR}.")
    else:
        print(f"[INFO] Found {len(existing)} file(s) in {DATA_DIR}: {existing}")

    card_pattern = re.compile(r"^(RAD|ACO|ATM|ISO)-[0-9]{2}$")
    valid_decided_by = {"quality_check", "fixed_threshold", "baseline", "trend", "fast_track"}

    # 1. Assert Rule Table integrity
    rules = get_rule_table_dicts()
    assert len(rules) >= 50, "Rule table must include L0..L3 rules across the 17 cards."
    rule_id_pat = re.compile(r"^(RAD|ACO|ATM|ISO)-[0-9]{2}-L[0-3]$")
    for r in rules:
        assert rule_id_pat.match(r["rule_id"]), f"Invalid rule_id format: {r['rule_id']}"
        assert r["source_tag"] in {"STD", "LIT", "TEAM"}, f"Invalid source_tag: {r['source_tag']}"

    # 2. Assert every scenario returns the expected status for all 17 cards + schema validation
    expected_map = {
        "green": "green",
        "yellow": "yellow",
        "red": "red",
        "bad_data": "no_data",
    }
    for scen, exp_status in expected_map.items():
        ev = evaluate(demo_payload(scen), demo_baseline())
        assert ev["overall_status"] == exp_status, f"Scenario {scen}: expected overall {exp_status}, got {ev['overall_status']}"
        assert ev["decision_owner"] == "human", "decision_owner must always be 'human'"
        assert len(ev["cards"]) == 17, f"Expected 17 cards, got {len(ev['cards'])}"

        # Validate top-level schema conversion
        top_schema = to_schema(ev)
        assert isinstance(top_schema, ModuleEvaluationResult)

        for cid in CARD_IDS:
            card = ev["cards"][cid]
            assert card_pattern.match(card["module_id"]), f"Bad card id {card['module_id']}"
            assert card["decision_owner"] == "human"
            assert set(card["notify"].keys()) >= {"crew", "ground", "flight_surgeon"}
            assert card["overall_status"] == exp_status, (
                f"Scenario '{scen}' card {cid}: expected '{exp_status}', got '{card['overall_status']}' ({card['indicators'][0]['message']})"
            )
            # Env cards have crew_id=None; crew cards have crew_id="C002"
            if cid in {"RAD-01", "RAD-03", "ACO-01", "ATM-01", "ATM-02", "ATM-03", "ATM-04", "ATM-05", "ATM-06", "ATM-07"}:
                assert card["crew_id"] is None, f"{cid} is module-level environment data -> crew_id must be None"
            else:
                assert card["crew_id"] == "C002", f"{cid} is personal crew data -> crew_id must be set"

            # Per-card schema conversion check
            c_schema = to_schema(ev, card_id=cid)
            assert isinstance(c_schema, ModuleEvaluationResult)

            for ind in card["indicators"]:
                assert ind["decided_by"] in valid_decided_by, f"Invalid decided_by: {ind['decided_by']}"
                assert ind["data_source"] in {"REAL", "SIMULATED"}
                assert any(ind["source_ref"].startswith(tag + ":") for tag in ("STD", "LIT", "TEAM")), (
                    f"Missing STD/LIT/TEAM tag in source_ref: {ind['source_ref']}"
                )
                if scen == "bad_data":
                    assert ind["status"] in {"rejected", "no_data"}, f"bad_data indicator {ind['indicator']} must not be Green: {ind['status']}"
                    assert ind["decided_by"] == "quality_check"

    # 3. Assert fast-track cases in "red" are Red with decided_by="fast_track"
    red_ev = evaluate(demo_payload("red"), demo_baseline())
    ft_cards = [
        cid for cid, c in red_ev["cards"].items()
        if any(i["decided_by"] == "fast_track" and i["status"] == "red" for i in c["indicators"])
    ]
    assert {"ATM-02", "ATM-04", "RAD-03"}.issubset(set(ft_cards)), f"Expected fast-track Red in ATM-02, ATM-04, RAD-03; got {ft_cards}"

    # 4. Assert ISO-03 Red preserves crew choice for private medical conference and strips journal text
    assert red_ev["cards"]["ISO-03"]["notify"].get("private_conference_crew_choice") is True
    assert red_ev["cards"]["ISO-03"]["notify"]["flight_surgeon"] is False
    bad_ev = evaluate(demo_payload("bad_data"), demo_baseline())
    serialized_bad = json.dumps(bad_ev)
    assert "Private crew diary note" not in serialized_bad, "Journal text must never be stored/returned!"

    # 5. Assert Layer 3 trend alone produces Yellow and NEVER Red
    trend_pay = demo_payload("green")
    now_iso = trend_pay["timestamp_utc"]
    ts_5 = _make_timestamps_utc(now_iso, 5, 60.0)
    # Construct steep rising CO2 still in Green (<2.5 mmHg) that projects >3.0 mmHg within 24 h with R^2 >= 0.6
    # 1.50, 1.65, 1.80, 1.95, 2.10 mmHg -> slope = +0.15 mmHg/h -> TTR to 3.0 = (3.0 - 2.10)/0.15 = 6.0 h <= 24 h, R^2 = 1.0
    trend_pay["atm01_co2"] = {
        "records_1h": [
            {"timestamp_utc": ts_5[i], "co2_ppm": (1.50 + 0.15 * i) / (1e-6 * 760.0), "second_sensor_confirmed": True}
            for i in range(5)
        ],
        "step_change_1min_ppm": 20.0,
        "step_second_sensor_confirmed": True,
        "mean_7d_ppm": 1.80 / (1e-6 * 760.0),
    }
    trend_ev = evaluate(trend_pay, demo_baseline())
    atm01_trend_card = trend_ev["cards"]["ATM-01"]
    assert atm01_trend_card["overall_status"] == "yellow", (
        f"Steep L3 trend from Green must produce 'yellow' (never 'red'), got {atm01_trend_card['overall_status']}"
    )
    assert atm01_trend_card["indicators"][0]["decided_by"] == "trend"

    print("[PASS] All 17 Measurement Cards verified across green, yellow, red, bad_data, trend-only, and fast_track!")
    for scen in ("green", "yellow", "red", "bad_data"):
        ev_s = evaluate(demo_payload(scen), demo_baseline())
        counts: dict[str, int] = {}
        for c in ev_s["assessments"]:
            counts[c["overall_status"]] = counts.get(c["overall_status"], 0) + 1
        print(f"  - scenario={scen:<8} -> overall={ev_s['overall_status']:<7} | card_counts={counts}")


if __name__ == "__main__":
    _run_self_verification()
