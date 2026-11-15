"""Role 6: Radiation, Acoustics & Closed-Habitat Module (Z.O.S.M.A.).

Implements the "Radiation, Acoustics & Closed-Habitat Module — Measurement & Data Guide" (v2):
- All 17 Measurement Cards: RAD-01..03, ACO-01..03, ATM-01..07, ISO-01..04.
- Explicit Rule Table: (rule_id, module_id, layer, comparator, value, unit, window, horizon, source_tag, ref).
- Layer 0 QC Gatekeeper (physical range, timestamp ordering, deduplication, >3x cadence staleness -> no_data,
  SAA lat/lon masking, >1000x single-detector spike rejection, stuck sensors, calibration & wear-time gates).
- Layer 1 Fixed Thresholds (STD / LIT / TEAM), Layer 2 Baselines (personal, 7-day module median, setpoint),
  Layer 3 5-point OLS Trend (R^2 >= 0.6 -> yellow only, never red), and Fast-Track immediate Red bypass.
- Decision support only: every assessment and Red action concludes with a human decision (decision_owner = "human").
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

from core.schema import ModuleEvaluationResult, normalize_module_result

from modules.cabin_env.card_helpers import (
    _check_staleness,
    _clean_time_series,
    _evaluate_personal_baseline_l2,
    _make_card_assessment,
    _make_indicator,
    _max_status,
    _notify_for_card,
    _ols_trend_layer3,
    _parse_water_val,
    is_in_saa,
)
from modules.cabin_env.demo_data import (
    _make_timestamps_utc,
    demo_baseline,
    demo_payload,
    export_demo_csvs,
)
from modules.cabin_env.measurement_rules import (
    AUDIO_FREQS_HZ,
    CARD_IDS,
    DATA_DIR,
    NC_40_LIMITS_DB,
    NC_50_LIMITS_DB,
    NOMINAL_CADENCE_HOURS,
    OCTAVE_FREQS_HZ,
    RULE_TABLE,
    STATUS_SEVERITY,
    TREND_HORIZON_HOURS,
    get_rule_table_dicts,
)


def _eval_rad03(
    pay: dict[str, Any],
    rad01_rising: bool,
    mission_day: int,
    ts_utc: str,
    location: str,
    data_source: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Evaluate RAD-03 GOES integral protons (>=10 MeV, >=100 MeV; 5-min) + DONKI SEP."""
    g = dict(pay.get("rad03_goes") or {})
    # Support flat slider override for proton_flux_10mev_pfu / spe_alert
    manual_pfu = pay.get("_override_proton_flux_10mev_pfu")
    manual_spe = pay.get("_override_spe_alert")

    q_notes: list[str] = []
    age_h = g.get("age_hours", 0.05)
    stale, stale_msg = _check_staleness("RAD-03", age_h)
    if stale and manual_pfu is None:
        q_notes.append(stale_msg or "GOES data > 30 min old.")

    records = list(g.get("primary_records") or [])
    if not records and g.get("secondary_records"):
        records = list(g["secondary_records"])
        q_notes.append("Primary GOES satellite missing; fell back to secondary GOES satellite.")

    records, clean_notes = _clean_time_series(records, ts_key="time_tag")
    q_notes.extend(clean_notes)

    if manual_pfu is not None:
        val_pfu = float(manual_pfu)
        records = [
            {"time_tag": f"t-{4-i}", "satellite": "GOES-override", "flux_10mev": val_pfu, "flux_100mev": 2.0 if val_pfu >= 100 else 0.1}
            for i in range(5)
        ]
        stale = False

    valid_recs: list[dict[str, Any]] = []
    rejected_count = 0
    for rec in records:
        f10 = rec.get("flux_10mev")
        f100 = rec.get("flux_100mev", 0.05)
        if f10 is None or float(f10) <= 0.0 or (f100 is not None and float(f100) < 0.0):
            rejected_count += 1
            continue
        valid_recs.append(rec)

    if rejected_count > 0:
        q_notes.append(f"Rejected {rejected_count} GOES reading(s) with flux <= 0.")

    if (stale and not g.get("secondary_records") and manual_pfu is None) or not valid_recs:
        if g.get("secondary_records") and stale:
            sec_recs, _ = _clean_time_series(list(g["secondary_records"]), ts_key="time_tag")
            valid_recs = [r for r in sec_recs if r.get("flux_10mev") is not None and float(r["flux_10mev"]) > 0]
            if valid_recs:
                q_notes.append("Primary GOES >30 min stale; switched to fresh secondary GOES feed.")
                stale = False

    if stale or not valid_recs:
        ind = _make_indicator(
            indicator="proton_flux_10mev_pfu",
            value=None,
            unit="pfu",
            status="rejected" if rejected_count > 0 else "no_data",
            message="; ".join(q_notes) or "No valid GOES proton flux (<30 min, flux > 0).",
            action="Check GOES primary/secondary telemetry link; hold EVA decisions pending human review.",
            decided_by="quality_check",
            rule_id="RAD-03-L0",
            source_ref="STD:NOAA-SWPC-GOES-SEP",
            data_source=data_source,
        )
        card = _make_card_assessment(
            module_id="RAD-03",
            body_part_tag="whole_body",
            crew_id=None,
            mission_day=mission_day,
            timestamp_utc=ts_utc,
            location=location,
            overall_status="no_data",
            quality_passed=False,
            quality_notes=q_notes,
            indicators=[ind],
            is_env_card=True,
            conclusion_actions=["Switch to GOES secondary satellite / DONKI backup feed; verify local RAD-01 DOSTEL/HERA."],
            routine_countermeasures=["Maintain dual GOES primary/secondary ground-to-ship telemetry and local HERA alerting."],
            how_to_measure="Ingest 5-min NOAA GOES integral proton flux (>=10 MeV & >=100 MeV) and DONKI SEP feed; drop records >30 min old.",
            plain_explanation="Solar energetic proton storms can rapidly deliver acute radiation doses during EVA or in lightly shielded modules.",
            next_hours=0,
        )
        return card, {"s1_active": False, "spe_confirmed": False, "flux_10mev": None}

    f10_series = [float(r["flux_10mev"]) for r in valid_recs]
    f100_series = [float(r.get("flux_100mev", 0.05)) for r in valid_recs]
    curr_f10 = f10_series[-1]
    curr_f100 = f100_series[-1]
    swpc_warn = bool(g.get("swpc_warning", False))

    # 3 consecutive 5-min readings above threshold required to declare SPE onset
    s1_persist = len(f10_series) >= 3 and all(x >= 10.0 for x in f10_series[-3:])
    s2_persist = len(f10_series) >= 3 and all(x >= 100.0 for x in f10_series[-3:])
    if manual_spe is True:
        s1_persist = True
        s2_persist = True
        rad01_rising = True

    # Fast-track: confirmed SPE onset (3x 5-min >= 100 pfu S2+ AND RAD-01 rising)
    if s2_persist and rad01_rising:
        status = "red"
        decided_by = "fast_track"
        rule_id = "RAD-03-L1"
        msg = f"Confirmed SPE onset: >=10 MeV flux {curr_f10:.1f} pfu (>=100 pfu S2+ for >=3x5m) with rising cabin RAD-01."
        act = "Declare SPE emergency: move crew to storm shelter, terminate EVA, notify ground & flight surgeon (human decision)."
    elif curr_f10 >= 10.0 or curr_f100 >= 1.0 or swpc_warn:
        status = "yellow"
        decided_by = "fixed_threshold"
        rule_id = "RAD-03-L1"
        persist_note = "S1 SPE persistence confirmed" if s1_persist else "awaiting 3-reading SPE persistence"
        msg = f"GOES >=10 MeV = {curr_f10:.1f} pfu, >=100 MeV = {curr_f100:.2f} pfu ({persist_note}, SWPC_warn={swpc_warn})."
        act = "Increase RAD-01 evaluation to every 5 min, review EVA schedule, pre-position shelter supplies."
    else:
        status = "green"
        decided_by = "fixed_threshold"
        rule_id = "RAD-03-L1"
        msg = f"GOES >=10 MeV = {curr_f10:.2f} pfu (<10) and >=100 MeV = {curr_f100:.2f} pfu (<1)."
        act = "Nominal space weather vigilancia."

    # Layer 3 OLS trend on log10(flux), horizon = 1 h (never produces Red)
    times_h = [i * (5.0 / 60.0) for i in range(len(f10_series))]
    ols = _ols_trend_layer3(times_h, f10_series, red_limit=100.0, horizon_h=TREND_HORIZON_HOURS["RAD-03"], lower_is_worse=False, log10_transform=True)
    if status == "green" and ols["triggered"]:
        status = "yellow"
        decided_by = "trend"
        rule_id = "RAD-03-L3"
        msg = f"log10(GOES >=10 MeV) 5-pt OLS projects 100 pfu in {ols['ttr_h']:.2f} h (<=1 h, R²={ols['r2']:.2f})."
        act = "Increase RAD-01 evaluation to every 5 min, review EVA schedule, pre-position shelter supplies."

    ind_10 = _make_indicator(
        indicator="proton_flux_10mev_pfu",
        value=round(curr_f10, 2),
        unit="pfu",
        status=status,
        message=msg,
        action=act,
        decided_by=decided_by,
        rule_id=rule_id,
        source_ref="STD:NOAA-SWPC-S1/S2-SEP",
        data_source=data_source,
        baseline_val=1.8,
        yellow_threshold=10.0,
        red_threshold=100.0,
        history_days=[max(1, mission_day - 4 + i) for i in range(min(5, len(f10_series)))],
        history_values=[round(x, 2) for x in f10_series[-5:]],
    )
    ind_100 = _make_indicator(
        indicator="proton_flux_100mev_pfu",
        value=round(curr_f100, 3),
        unit="pfu",
        status="yellow" if curr_f100 >= 1.0 and status != "red" else status,
        message=f"GOES >=100 MeV integral proton flux = {curr_f100:.3f} pfu.",
        action=act,
        decided_by=decided_by,
        rule_id=rule_id,
        source_ref="STD:NOAA-SWPC-S1/S2-SEP",
        data_source=data_source,
        baseline_val=0.05,
        yellow_threshold=1.0,
    )

    if status == "red":
        c_actions = [
            "Move crew to the most shielded storm shelter area immediately; terminate any planned/ongoing EVA.",
            "Increase RAD-01 telemetry readout to 5-min cadence and notify ground & flight surgeon for human decision.",
        ]
        next_h = 1
    elif status == "yellow":
        c_actions = [
            "Increase RAD-01 evaluation to every 5 min.",
            "Review EVA schedule and pre-position storm shelter water/stowage supplies.",
        ]
        next_h = 1
    else:
        c_actions = ["Continue routine 5-min GOES & DONKI space-weather monitoring."]
        next_h = 6

    card = _make_card_assessment(
        module_id="RAD-03",
        body_part_tag="whole_body",
        crew_id=None,
        mission_day=mission_day,
        timestamp_utc=ts_utc,
        location=location,
        overall_status=status,
        quality_passed=True,
        quality_notes=q_notes,
        indicators=[ind_10, ind_100],
        is_env_card=True,
        conclusion_actions=c_actions,
        routine_countermeasures=["Maintain automated SWPC GOES primary/secondary feed + onboard HERA local trigger for deep-space comm-delay autonomy."],
        how_to_measure="Monitor 5-min GOES >=10 MeV and >=100 MeV integral proton channels; confirm SPE onset on 3 consecutive 5-min readings.",
        plain_explanation="High-energy solar protons penetrate spacecraft hulls during solar storms, creating acute radiation sickness and lymphocyte depletion risk.",
        next_hours=next_h,
    )
    s1_or_higher = curr_f10 >= 10.0 or s1_persist
    return card, {"s1_active": s1_or_higher, "spe_confirmed": status == "red", "flux_10mev": curr_f10}


def _eval_rad01(
    pay: dict[str, Any],
    base: dict[str, Any],
    rad03_meta: dict[str, Any],
    mission_day: int,
    ts_utc: str,
    location: str,
    data_source: str,
) -> dict[str, Any]:
    """Evaluate RAD-01 Cabin area absorbed dose rate (IV-TEPC, DOSTEL, HERA), 1-h means."""
    med = float(base.get("rad01_columbus_median_uGy_h", 4.06))
    records = list(pay.get("rad01_records") or [])
    if pay.get("_override_dose_rate_uGy_h") is not None:
        ov_val = float(pay["_override_dose_rate_uGy_h"])
        ov_saa = bool(pay.get("_override_saa_pass", False))
        records = [
            {
                "timestamp_utc": f"t-{4-i}",
                "module": location,
                "dose_rate_uGy_h": ov_val,
                "lat_deg": -20.0 if ov_saa else 25.0,
                "lon_deg": -30.0 if ov_saa else 80.0,
                "second_detector_confirmed": True,
            }
            for i in range(5)
        ]

    q_notes: list[str] = []
    stale, stale_msg = _check_staleness("RAD-01", pay.get("rad01_age_hours"))
    if stale:
        q_notes.append(stale_msg or "RAD-01 stale.")

    records, clean_notes = _clean_time_series(records)
    q_notes.extend(clean_notes)

    valid_outside_saa: list[float] = []
    rejected_indicators: list[dict[str, Any]] = []
    saa_masked_count = 0
    spike_rejected_count = 0
    neg_rejected_count = 0

    for rec in records:
        val = rec.get("dose_rate_uGy_h")
        if val is None or float(val) <= 0.0:
            neg_rejected_count += 1
            continue
        fval = float(val)
        if fval > 1000.0 * med and not bool(rec.get("second_detector_confirmed", False)):
            spike_rejected_count += 1
            continue
        if is_in_saa(rec.get("lat_deg"), rec.get("lon_deg")) or bool(rec.get("saa_pass", False)):
            saa_masked_count += 1
            continue
        valid_outside_saa.append(fval)

    if neg_rejected_count:
        q_notes.append(f"Rejected {neg_rejected_count} negative/null dose-rate reading(s).")
    if spike_rejected_count:
        q_notes.append(f"Rejected {spike_rejected_count} reading(s) >1000x module median without second-detector confirmation.")
    if saa_masked_count:
        q_notes.append(f"Masked {saa_masked_count} South Atlantic Anomaly pass reading(s) (50°S–0°, 90°W–40°E).")

    if stale or not valid_outside_saa:
        rej_status = "rejected" if (neg_rejected_count or spike_rejected_count or saa_masked_count) else "no_data"
        ind = _make_indicator(
            indicator="dose_rate_uGy_h",
            value=None,
            unit="uGy/h",
            status=rej_status,
            message="; ".join(q_notes) or "No valid non-SAA RAD-01 readings available.",
            action="Await post-SAA pass readout or cross-check second DOSTEL/HERA detector in module.",
            decided_by="quality_check",
            rule_id="RAD-01-L0",
            source_ref="LIT:DOSTEL-Columbus-SAA-QC",
            data_source=data_source,
            baseline_val=med,
        )
        return _make_card_assessment(
            module_id="RAD-01",
            body_part_tag="whole_body",
            crew_id=None,
            mission_day=mission_day,
            timestamp_utc=ts_utc,
            location=location,
            overall_status="no_data",
            quality_passed=False,
            quality_notes=q_notes,
            indicators=[ind],
            is_env_card=True,
            conclusion_actions=["Verify DOSTEL/IV-TEPC detector health and await next non-SAA 1-h mean."],
            routine_countermeasures=["ALARA; missions > 6 months: >= 20 g/cm² shielding plus 10 cm water-equivalent storm shelter in crew quarters."],
            how_to_measure="Record 1-h mean absorbed dose rate from IV-TEPC/DOSTEL/HERA; mask SAA passes (50°S–0°, 90°W–40°E) and reject single-sensor >1000x spikes.",
            plain_explanation="Area dosimeters track real-time hull-penetrating galactic cosmic rays and solar particle enhancements inside each module.",
            next_hours=1,
        )

    curr = valid_outside_saa[-1]
    ratio = curr / med
    rad03_s1 = bool(rad03_meta.get("s1_active", False))

    # Layer 1 (TEAM placeholder Red: >10x median AND RAD-03 >= S1)
    l1_status = "red" if (ratio > 10.0 and rad03_s1) else "green"
    # Layer 2 (Module 7-d median: >2x median for >=1h outside SAA -> Yellow; also >10x without S1 -> Yellow)
    l2_status = "yellow" if ratio > 2.0 else "green"
    # Layer 3 (5-pt OLS, horizon = 6 h -> Yellow only)
    times_h = [float(i) for i in range(len(valid_outside_saa))]
    ols = _ols_trend_layer3(times_h, valid_outside_saa, red_limit=10.0 * med, horizon_h=TREND_HORIZON_HOURS["RAD-01"])
    l3_status = "yellow" if ols["triggered"] else "green"

    final_st = _max_status(l1_status, l2_status, l3_status)
    if l1_status == "red":
        decided_by, rule_id, src = "fixed_threshold", "RAD-01-L1", "TEAM:RAD-01-demo-red-placeholder"
        msg = f"1-h mean {curr:.2f} uGy/h ({ratio:.1f}x Columbus median {med:.2f} uGy/h; TEAM placeholder >10x) AND RAD-03 >= S1."
        act = "Move to most shielded area; in Orion, line cabin walls with stowage; terminate EVA; notify flight surgeon (human decision)."
    elif l2_status == "yellow":
        decided_by, rule_id, src = "baseline", "RAD-01-L2", "LIT:Columbus-195-360uGy/d-7d-median"
        msg = f"1-h mean {curr:.2f} uGy/h is {ratio:.1f}x (>2x) module 7-day median ({med:.2f} uGy/h) outside SAA."
        act = "Cross-check RAD-03 GOES proton flux, minimize time in lightly shielded nodes, prepare storm shelter."
    elif l3_status == "yellow":
        decided_by, rule_id, src = "trend", "RAD-01-L3", "TEAM:5pt-OLS-R2>=0.6"
        msg = f"RAD-01 5-pt OLS projects 10x median ({10*med:.1f} uGy/h) in {ols['ttr_h']:.2f} h (<=6 h, R²={ols['r2']:.2f})."
        act = "Pre-position stowage/water shielding and monitor 5-min dose-rate trend."
    else:
        decided_by, rule_id, src = "baseline", "RAD-01-L2", "LIT:Columbus-195-360uGy/d-7d-median"
        msg = f"1-h mean {curr:.2f} uGy/h within Columbus baseline ({med:.2f} uGy/h; ref 195–360 uGy/day)."
        act = "Continue nominal ALARA occupancy tracking."

    ind = _make_indicator(
        indicator="dose_rate_uGy_h",
        value=round(curr, 2),
        unit="uGy/h",
        status=final_st,
        message=msg,
        action=act,
        decided_by=decided_by,
        rule_id=rule_id,
        source_ref=src,
        data_source=data_source,
        baseline_val=med,
        slope_per_day=round(ols["slope_per_h"] * 24.0, 3) if ols["slope_per_h"] is not None else 0.0,
        yellow_threshold=round(2.0 * med, 2),
        red_threshold=round(10.0 * med, 2),
        history_days=[max(1, mission_day - len(valid_outside_saa) + 1 + i) for i in range(len(valid_outside_saa[-5:]))],
        history_values=[round(v, 2) for v in valid_outside_saa[-5:]],
    )

    if final_st == "red":
        c_actions = [
            "Move to the most shielded area; in Orion, line cabin walls with stowage.",
            "Terminate EVA immediately and notify flight surgeon (human decision).",
        ]
        next_h = 1
    elif final_st == "yellow":
        c_actions = [
            "Verify non-SAA orbital position and cross-check RAD-03 proton flux.",
            "Relocate prolonged work tasks to higher-shielding module locations.",
        ]
        next_h = 1
    else:
        c_actions = ["Continue hourly area dose-rate logging with automatic SAA pass masking."]
        next_h = 6

    return _make_card_assessment(
        module_id="RAD-01",
        body_part_tag="whole_body",
        crew_id=None,
        mission_day=mission_day,
        timestamp_utc=ts_utc,
        location=location,
        overall_status=final_st,
        quality_passed=True,
        quality_notes=q_notes,
        indicators=[ind],
        is_env_card=True,
        conclusion_actions=c_actions,
        routine_countermeasures=[
            "ALARA; missions > 6 months: >= 20 g/cm² shielding plus a 10 cm water-equivalent storm shelter in crew quarters (rearranged water containers)."
        ],
        how_to_measure="Read 1-h mean absorbed dose rate from IV-TEPC / DOSTEL / HERA; exclude SAA passes (50°S–0°, 90°W–40°E) and unconfirmed >1000x spikes.",
        plain_explanation="Tracks real-time ionizing radiation inside the cabin to trigger storm-shelter protection during solar particle events.",
        next_hours=next_h,
    )


def _eval_rad02(
    pay: dict[str, Any],
    base: dict[str, Any],
    crew_id: str,
    mission_day: int,
    ts_utc: str,
    location: str,
    data_source: str,
) -> dict[str, Any]:
    """Evaluate RAD-02 Personal cumulative effective dose (Q ~ 2.26; 300/480/600 mSv [V1 4030], SPE 250 mSv [V1 4031])."""
    r = dict(pay.get("rad02_daily") or {})
    q_notes: list[str] = []
    stale, stale_msg = _check_staleness("RAD-02", pay.get("rad02_age_hours"))
    if stale:
        q_notes.append(stale_msg or "RAD-02 stale.")

    occ = dict(r.get("occupancy_hours") or {"Columbus": 16.0, "Harmony": 8.0})
    rates = dict(r.get("module_dose_rates_uGy_h") or {"Columbus": 4.06, "Harmony": 4.25})
    occ_sum = sum(float(v) for v in occ.values())
    missing_h = max(0.0, 24.0 - occ_sum)

    if pay.get("_override_career_dose_mSv") is not None:
        occ_sum = 24.0
        missing_h = 0.0
        stale = False

    if stale or missing_h > 4.0 or abs(occ_sum - 24.0) > 0.5:
        if missing_h > 4.0:
            q_notes.append(f"Rejected day missing {missing_h:.1f} h (>4 h) of crew module location data.")
        elif abs(occ_sum - 24.0) > 0.5:
            q_notes.append(f"Occupancy hours sum to {occ_sum:.2f} h (outside 24 ± 0.5 h QC gate).")
        ind = _make_indicator(
            indicator="career_dose_mSv",
            value=None,
            unit="mSv",
            status="rejected" if not stale else "no_data",
            message="; ".join(q_notes),
            action="Reconcile crew module occupancy log to 24 ± 0.5 h and read personal dosimeter badge.",
            decided_by="quality_check",
            rule_id="RAD-02-L0",
            source_ref="LIT:DOSTEL-647/286-Q=2.26",
            data_source=data_source,
            baseline_val=float(base.get("career_dose_mSv", 145.0)),
        )
        return _make_card_assessment(
            module_id="RAD-02",
            body_part_tag="whole_body",
            crew_id=crew_id,
            mission_day=mission_day,
            timestamp_utc=ts_utc,
            location=location,
            overall_status="no_data",
            quality_passed=False,
            quality_notes=q_notes,
            indicators=[ind],
            is_env_card=False,
            conclusion_actions=["Complete 24-h module location log and sync Crew Passive/Active Dosimeter."],
            routine_countermeasures=["Log daily module occupancy and sleep inside higher-shielded crew quarters."],
            how_to_measure="Compute daily dose = sum(module dose rate * hours in module) * 2.26 (DOSTEL 647/286) and add to career total.",
            plain_explanation="Cumulative effective radiation dose governs lifetime cancer and degenerative tissue risk against NASA's 600 mSv career limit.",
            next_hours=24,
        )

    daily_uGy = sum(float(occ[m]) * float(rates.get(m, 4.06)) for m in occ)
    daily_mSv = (daily_uGy * 2.26) / 1000.0
    if pay.get("_override_career_dose_mSv") is not None:
        career_mSv = float(pay["_override_career_dose_mSv"])
    else:
        career_mSv = float(r.get("career_prior_mSv", 124.0)) + float(r.get("mission_cum_mSv", 28.0))
    single_spe_mSv = float(r.get("single_spe_mSv", 0.0))

    mission_len = int(pay.get("mission_length_days", base.get("mission_length_days", 180)))
    rem_days = max(1, mission_len - mission_day)
    rem_hours = float(rem_days * 24)
    projected_end_mSv = career_mSv + daily_mSv * rem_days

    # Layer 1 Fixed Thresholds (Layer 2 not used per guide)
    if career_mSv > 480.0 or single_spe_mSv >= 250.0:
        l1_st = "red"
    elif career_mSv >= 300.0 or projected_end_mSv > 480.0:
        l1_st = "yellow"
    else:
        l1_st = "green"

    # Layer 3 5-point OLS over remaining mission days horizon
    hist_vals = list(r.get("history_5d_career_mSv") or [career_mSv - (4 - i) * daily_mSv for i in range(5)])
    if pay.get("_override_career_dose_mSv") is not None:
        hist_vals = [career_mSv - (4 - i) * max(daily_mSv, 0.22) for i in range(5)]
    times_h = [float(i * 24) for i in range(len(hist_vals))]
    ols = _ols_trend_layer3(times_h, hist_vals, red_limit=480.0, horizon_h=rem_hours)
    l3_st = "yellow" if ols["triggered"] else "green"

    final_st = _max_status(l1_st, l3_st)
    if l1_st == "red":
        decided_by, rule_id = "fixed_threshold", "RAD-02-L1"
        msg = f"Career dose {career_mSv:.1f} mSv (>480 mSv; 80% of 600 mSv [V1 4030]) | single SPE {single_spe_mSv:.1f} mSv (limit 250 mSv [V1 4031])."
        act = "Restrict unshielded module/EVA exposure immediately; flight surgeon & mission management review required (human decision)."
    elif l1_st == "yellow":
        decided_by, rule_id = "fixed_threshold", "RAD-02-L1"
        msg = f"Career dose {career_mSv:.1f} mSv (300–480 mSv band; mission-end projection {projected_end_mSv:.1f} mSv)."
        act = "Increase sleep/work hours in high-shielding modules and review remaining EVA dose budget."
    elif l3_st == "yellow":
        decided_by, rule_id = "trend", "RAD-02-L3"
        msg = f"5-pt OLS projects reaching 480 mSv Red threshold in {ols['ttr_h']/24.0:.1f} d (before mission end {rem_days} d, R²={ols['r2']:.2f})."
        act = "Adjust crew module rotation to reduce daily equivalent dose rate."
    else:
        decided_by, rule_id = "fixed_threshold", "RAD-02-L1"
        msg = f"Career dose {career_mSv:.1f} mSv (<300 mSv), daily {daily_mSv:.3f} mSv/d (Q=2.26), projected end {projected_end_mSv:.1f} mSv."
        act = "Maintain standard ALARA radiation hygiene."

    days_to_red = 0 if final_st == "red" else (int(ols["ttr_h"] / 24.0) if ols["ttr_h"] is not None else None)
    ind = _make_indicator(
        indicator="career_dose_mSv",
        value=round(career_mSv, 2),
        unit="mSv",
        status=final_st,
        message=msg,
        action=act,
        decided_by=decided_by,
        rule_id=rule_id,
        source_ref="STD:NASA-STD-3001-V1-4030/4031",
        data_source=data_source,
        baseline_val=float(base.get("career_dose_mSv", 145.0)),
        slope_per_day=round(daily_mSv, 4),
        yellow_threshold=300.0,
        red_threshold=480.0,
        history_days=[max(1, mission_day - 4 + i) for i in range(5)],
        history_values=[round(v, 2) for v in hist_vals[-5:]],
    )
    return _make_card_assessment(
        module_id="RAD-02",
        body_part_tag="whole_body",
        crew_id=crew_id,
        mission_day=mission_day,
        timestamp_utc=ts_utc,
        location=location,
        overall_status=final_st,
        quality_passed=True,
        quality_notes=q_notes,
        indicators=[ind],
        is_env_card=False,
        conclusion_actions=[act],
        routine_countermeasures=["Enforce ALARA scheduling, polyethylene/water sleep-station shielding, and personal active dosimeter cross-checks."],
        how_to_measure="Sum daily (module absorbed dose rate * occupancy hours) * 2.26 equivalent factor; require 24 ± 0.5 h location coverage.",
        plain_explanation="Tracks personal cumulative effective radiation against the 600 mSv NASA career limit (Red action gate at 480 mSv / 80%).",
        next_hours=24,
        days_until_red=days_to_red,
    )


def _eval_aco01(
    pay: dict[str, Any],
    base: dict[str, Any],
    mission_day: int,
    ts_utc: str,
    location: str,
    data_source: str,
) -> dict[str, Any]:
    """Evaluate ACO-01 Module noise, dBA + octave bands 63 Hz–8 kHz, monthly survey."""
    s = dict(pay.get("aco01_survey") or {})
    if pay.get("_override_module_spl_dBA") is not None:
        s["spl_dBA"] = float(pay["_override_module_spl_dBA"])
        s["pre_cal_dB"] = 94.0
        s["post_cal_dB"] = 94.1
        s["lab_cal_age_months"] = 4

    q_notes: list[str] = []
    stale, stale_msg = _check_staleness("ACO-01", pay.get("aco01_age_hours"))
    if stale:
        q_notes.append(stale_msg or "ACO-01 stale.")

    cal_drift = abs(float(s.get("post_cal_dB", 94.0)) - float(s.get("pre_cal_dB", 94.0)))
    lab_age_mo = float(s.get("lab_cal_age_months", 4))
    spl = s.get("spl_dBA")
    peak_db = float(s.get("impulse_peak_dB", 96.0))
    if spl is None or float(spl) < 0.0 or float(spl) > 160.0:
        q_notes.append("SPL outside physical range 0–160 dBA.")
        spl_invalid = True
    else:
        spl_invalid = False

    if stale or spl_invalid or cal_drift > 0.5 or lab_age_mo > 12.0:
        if cal_drift > 0.5:
            q_notes.append(f"SLM pre/post field calibration drift {cal_drift:.2f} dB > 0.5 dB limit.")
        if lab_age_mo > 12.0:
            q_notes.append(f"SLM laboratory calibration age {lab_age_mo:.0f} months > 12 months.")
        ind = _make_indicator(
            indicator="module_spl_dBA",
            value=None,
            unit="dBA",
            status="rejected" if not stale else "no_data",
            message="; ".join(q_notes),
            action="Recalibrate Sound Level Meter with pistonphone (<=0.5 dB drift) and repeat module survey.",
            decided_by="quality_check",
            rule_id="ACO-01-L0",
            source_ref="STD:NASA-STD-3001-V2-6078-QC",
            data_source=data_source,
            baseline_val=float(base.get("aco01_work_median_dBA", 54.5)),
        )
        return _make_card_assessment(
            module_id="ACO-01",
            body_part_tag="ears",
            crew_id=None,
            mission_day=mission_day,
            timestamp_utc=ts_utc,
            location=location,
            overall_status="no_data",
            quality_passed=False,
            quality_notes=q_notes,
            indicators=[ind],
            is_env_card=True,
            conclusion_actions=["Perform field acoustic calibrator check and repeat octave-band survey."],
            routine_countermeasures=["Verify SLM calibration before and after every monthly acoustic survey."],
            how_to_measure="Measure A-weighted SPL and octave bands (63 Hz–8 kHz) with calibrated Type 1 SLM (pre/post drift <= 0.5 dB, lab cal <= 12 mo).",
            plain_explanation="Continuous cabin fan/pump noise degrades speech intelligibility, sleep recovery, and inner-ear hair cells.",
            next_hours=24,
        )

    spl_val = float(spl)
    area_type = str(s.get("area_type", "work")).lower()
    m_dur = int(s.get("mission_duration_days", 180))
    nc_curve = NC_40_LIMITS_DB if (area_type == "sleep" and m_dur > 30) else NC_50_LIMITS_DB
    dba_equiv = 49.0 if (area_type == "sleep" and m_dur > 30) else 58.1
    bands = {int(k): float(v) for k, v in (s.get("octave_bands_dB") or {}).items()}
    exceeded_bands = [hz for hz, val in bands.items() if hz in nc_curve and val > nc_curve[hz]]
    tonal_margin = float(s.get("tonal_margin_dB", 15.0))

    if spl_val >= 85.0 or peak_db >= 140.0:
        l1_st = "red"
    elif exceeded_bands or tonal_margin < 10.0 or spl_val > dba_equiv:
        l1_st = "yellow"
    else:
        l1_st = "green"

    med_dba = float(base.get("aco01_sleep_median_dBA" if area_type == "sleep" else "aco01_work_median_dBA", 54.5))
    l2_st = "yellow" if spl_val > med_dba + 3.0 else "green"

    hist_spl = list(s.get("history_5_spl_dBA") or [spl_val] * 5)
    times_h = [float(i * 720) for i in range(len(hist_spl))]
    ols = _ols_trend_layer3(times_h, hist_spl, red_limit=85.0, horizon_h=TREND_HORIZON_HOURS["ACO-01"])
    l3_st = "yellow" if ols["triggered"] else "green"

    final_st = _max_status(l1_st, l2_st, l3_st)
    if l1_st == "red":
        decided_by, rule_id, src = "fixed_threshold", "ACO-01-L1", "STD:NASA-STD-3001-V2-6078/6079/6080"
        msg = f"Module SPL {spl_val:.1f} dBA (>=85 dBA) or peak {peak_db:.1f} dB (>=140 dB)."
        act = "Don hearing protection immediately, isolate noisy rack/pump, notify ground & flight surgeon (human decision)."
    elif l1_st == "yellow":
        decided_by, rule_id, src = "fixed_threshold", "ACO-01-L1", "STD:NASA-STD-3001-V2-6078/6079"
        msg = f"SPL {spl_val:.1f} dBA; bands above {'NC-40' if area_type=='sleep' else 'NC-50'}: {exceeded_bands}; tonal margin {tonal_margin:.1f} dB."
        act = "Inspect fan mufflers/vibration isolators and use hearing protection during extended tasks in module."
    elif l2_st == "yellow":
        decided_by, rule_id, src = "baseline", "ACO-01-L2", "LIT:ISS-Acoustic-Survey-Baseline"
        msg = f"SPL {spl_val:.1f} dBA exceeds module baseline median ({med_dba:.1f} dBA) by >3 dB."
        act = "Check ECLSS air diffuser debris and rack acoustic seals."
    elif l3_st == "yellow":
        decided_by, rule_id, src = "trend", "ACO-01-L3", "TEAM:5pt-OLS-next-survey"
        msg = f"5-pt OLS projects reaching 85 dBA before next monthly survey (R²={ols['r2']:.2f})."
        act = "Schedule preventive fan bearing maintenance."
    else:
        decided_by, rule_id, src = "fixed_threshold", "ACO-01-L1", "STD:NASA-STD-3001-V2-6078/6079"
        msg = f"All octave bands within {'NC-40' if area_type=='sleep' else 'NC-50'} (SPL {spl_val:.1f} dBA <= {dba_equiv} dBA)."
        act = "Nominal module acoustic environment."

    ind = _make_indicator(
        indicator="module_spl_dBA",
        value=round(spl_val, 1),
        unit="dBA",
        status=final_st,
        message=msg,
        action=act,
        decided_by=decided_by,
        rule_id=rule_id,
        source_ref=src,
        data_source=data_source,
        baseline_val=med_dba,
        yellow_threshold=dba_equiv,
        red_threshold=85.0,
        history_days=[max(1, mission_day - 120 + 30 * i) for i in range(5)],
        history_values=[round(v, 1) for v in hist_spl[-5:]],
    )
    return _make_card_assessment(
        module_id="ACO-01",
        body_part_tag="ears",
        crew_id=None,
        mission_day=mission_day,
        timestamp_utc=ts_utc,
        location=location,
        overall_status=final_st,
        quality_passed=True,
        quality_notes=q_notes,
        indicators=[ind],
        is_env_card=True,
        conclusion_actions=[act],
        routine_countermeasures=["Maintain acoustic blankets, clean fan intake screens, and enforce NC-50 work / NC-40 sleep envelopes."],
        how_to_measure="Conduct monthly Sound Level Meter octave-band survey (63 Hz–8 kHz) across work and sleep stations.",
        plain_explanation="Ensures continuous background noise stays below NC-50 (work) and NC-40 (sleep) to prevent hearing loss and alarm masking.",
        next_hours=24 if final_st != "green" else 720,
    )


def _eval_aco02(
    pay: dict[str, Any],
    base: dict[str, Any],
    crew_id: str,
    mission_day: int,
    ts_utc: str,
    location: str,
    data_source: str,
) -> dict[str, Any]:
    """Evaluate ACO-02 Crew noise exposure: LEQ16 (work), LEQ8 (sleep), Lmax, peak, 24-h dose D."""
    d = dict(pay.get("aco02_dosimetry") or {})
    if pay.get("_override_crew_leq8_dBA") is not None or pay.get("_override_daily_noise_dose_pct") is not None:
        if pay.get("_override_crew_leq8_dBA") is not None:
            d["leq8_sleep_dBA"] = float(pay["_override_crew_leq8_dBA"])
        if pay.get("_override_daily_noise_dose_pct") is not None:
            d["dose_24h_pct"] = float(pay["_override_daily_noise_dose_pct"])
        d["valid_hours"] = 24.0
        d["mic_covered"] = False

    q_notes: list[str] = []
    stale, stale_msg = _check_staleness("ACO-02", pay.get("aco02_age_hours"))
    if stale:
        q_notes.append(stale_msg or "ACO-02 stale.")

    valid_h = float(d.get("valid_hours", 24.0))
    mic_cov = bool(d.get("mic_covered", False))
    leq8 = d.get("leq8_sleep_dBA")
    dose_pct = d.get("dose_24h_pct")

    if stale or valid_h < 20.0 or mic_cov or leq8 is None or dose_pct is None or float(dose_pct) < 0:
        if valid_h < 20.0:
            q_notes.append(f"Dosimetry valid duration {valid_h:.1f} h < 20 h minimum.")
        if mic_cov:
            q_notes.append("Microphone-covered flag detected on crew personal dosimeter.")
        ind = _make_indicator(
            indicator="crew_leq8_dBA",
            value=None,
            unit="dBA",
            status="rejected" if not stale else "no_data",
            message="; ".join(q_notes),
            action="Re-run 24-h crew acoustic dosimetry with collar microphone uncovered (>=20 h valid).",
            decided_by="quality_check",
            rule_id="ACO-02-L0",
            source_ref="STD:NASA-STD-3001-V2-6115-QC",
            data_source=data_source,
            baseline_val=float(base.get("aco02_leq8_mean_dBA", 44.5)),
        )
        return _make_card_assessment(
            module_id="ACO-02",
            body_part_tag="ears",
            crew_id=crew_id,
            mission_day=mission_day,
            timestamp_utc=ts_utc,
            location=location,
            overall_status="no_data",
            quality_passed=False,
            quality_notes=q_notes,
            indicators=[ind],
            is_env_card=False,
            conclusion_actions=["Repeat 24-h personal noise dosimetry session ensuring >=20 h uncovered wear."],
            routine_countermeasures=["Schedule 24-h personal noise dosimetry every 60 mission days."],
            how_to_measure="Wear personal noise dosimeter at collar for 24 h (16 h work + 8 h sleep); require >=20 h valid uncovered recording.",
            plain_explanation="Measures actual ear-level noise dose D% and sleep-period LEQ8 to protect cochlear recovery during sleep.",
            next_hours=24,
        )

    leq8_val = float(leq8)
    dose_val = float(dose_pct)
    if leq8_val > 62.0 or dose_val > 100.0:
        l1_st = "red"
    elif leq8_val > 50.0 or (50.0 < dose_val <= 100.0):
        l1_st = "yellow"
    else:
        l1_st = "green"

    hist_leq8 = list(d.get("history_5_leq8_dBA") or [leq8_val] * 5)
    if pay.get("_override_crew_leq8_dBA") is not None:
        hist_leq8[-1] = leq8_val
    l2_st, l2_note = _evaluate_personal_baseline_l2(
        hist_leq8,
        mean_val=float(base.get("aco02_leq8_mean_dBA", 44.5)),
        sd_val=float(base.get("aco02_leq8_sd_dBA", 2.5)),
        lower_is_worse=False,
    )
    times_h = [float(i * 1440) for i in range(len(hist_leq8))]
    ols = _ols_trend_layer3(times_h, hist_leq8, red_limit=62.0, horizon_h=TREND_HORIZON_HOURS["ACO-02"])
    l3_st = "yellow" if ols["triggered"] else "green"

    final_st = _max_status(l1_st, l2_st, l3_st)
    if l1_st == "red":
        decided_by, rule_id, src = "fixed_threshold", "ACO-02-L1", "STD:NASA-STD-3001-V2-6115"
        msg = f"LEQ8 = {leq8_val:.1f} dBA (>62 dBA) or 24-h noise dose D = {dose_val:.1f}% (>100%)."
        act = "Mandate ANR hearing protection, quiet sleep quarters, schedule ACO-03 audiogram & flight surgeon review (human decision)."
    elif l2_st == "red":
        decided_by, rule_id, src = "baseline", "ACO-02-L2", "TEAM:Personal-Baseline-SD"
        msg = l2_note
        act = "Mandate hearing protection and flight surgeon audiometric review (human decision)."
    elif l1_st == "yellow":
        decided_by, rule_id, src = "fixed_threshold", "ACO-02-L1", "STD:NASA-STD-3001-V2-6115"
        msg = f"Sleep LEQ8 = {leq8_val:.1f} dBA (limit 50 dBA) | 24-h dose D = {dose_val:.1f}% (50–100% Yellow)."
        act = "Use sleep earplugs / ANR headset during noisy work and inspect sleep-station ventilation."
    elif l2_st == "yellow":
        decided_by, rule_id, src = "baseline", "ACO-02-L2", "TEAM:Personal-Baseline-SD"
        msg = l2_note
        act = "Reduce high-SPL equipment exposure time."
    elif l3_st == "yellow":
        decided_by, rule_id, src = "trend", "ACO-02-L3", "TEAM:5pt-OLS-next-dosimetry"
        msg = f"LEQ8 5-pt OLS projects >62 dBA by next 60-d session (R²={ols['r2']:.2f})."
        act = "Audit personal headset volume and sleep-berth acoustic seal."
    else:
        decided_by, rule_id, src = "fixed_threshold", "ACO-02-L1", "STD:NASA-STD-3001-V2-6115"
        msg = f"Sleep LEQ8 = {leq8_val:.1f} dBA (<=50) and 24-h dose D = {dose_val:.1f}% (<=50%)."
        act = "Personal acoustic exposure nominal."

    ind_leq = _make_indicator(
        indicator="crew_leq8_dBA",
        value=round(leq8_val, 1),
        unit="dBA",
        status=final_st,
        message=msg,
        action=act,
        decided_by=decided_by,
        rule_id=rule_id,
        source_ref=src,
        data_source=data_source,
        baseline_val=float(base.get("aco02_leq8_mean_dBA", 44.5)),
        yellow_threshold=50.0,
        red_threshold=62.0,
        history_days=[max(1, mission_day - 120 + 30 * i) for i in range(5)],
        history_values=[round(v, 1) for v in hist_leq8[-5:]],
    )
    ind_dose = _make_indicator(
        indicator="daily_noise_dose_pct",
        value=round(dose_val, 1),
        unit="%",
        status="red" if dose_val > 100.0 else ("yellow" if dose_val > 50.0 else "green"),
        message=f"24-h cumulative noise dose D = {dose_val:.1f}%.",
        action=act,
        decided_by="fixed_threshold",
        rule_id="ACO-02-L1",
        source_ref="STD:NASA-STD-3001-V2-6115",
        data_source=data_source,
        baseline_val=28.0,
        yellow_threshold=50.0,
        red_threshold=100.0,
    )
    return _make_card_assessment(
        module_id="ACO-02",
        body_part_tag="ears",
        crew_id=crew_id,
        mission_day=mission_day,
        timestamp_utc=ts_utc,
        location=location,
        overall_status=final_st,
        quality_passed=True,
        quality_notes=q_notes,
        indicators=[ind_leq, ind_dose],
        is_env_card=False,
        conclusion_actions=[act],
        routine_countermeasures=["Perform 24-h personal dosimetry every 60 days; wear hearing protection for tasks >80 dBA."],
        how_to_measure="Wear personal dosimeter for 24 h capturing LEQ16 (work), LEQ8 (sleep), Lmax, peak, and 24-h dose D.",
        plain_explanation="Protects auditory hair cells by ensuring quiet 8-h sleep recovery (<=50 dBA) and keeping daily dose D <= 50%.",
        next_hours=24 if final_st != "green" else 1440,
    )


def _eval_aco03(
    pay: dict[str, Any],
    base: dict[str, Any],
    crew_id: str,
    mission_day: int,
    ts_utc: str,
    location: str,
    data_source: str,
) -> dict[str, Any]:
    """Evaluate ACO-03 Hearing thresholds (OOHA/KUDUwave) 500–6000 Hz vs pre-flight audiogram."""
    a = dict(pay.get("aco03_audiogram") or {})
    q_notes: list[str] = []
    stale, stale_msg = _check_staleness("ACO-03", pay.get("aco03_age_hours"))
    if stale:
        q_notes.append(stale_msg or "ACO-03 stale.")

    amb_bad = bool(a.get("ambient_above_nc40", False))
    rep_diff = float(a.get("max_repeat_diff_dB", 5.0))
    confirmed = bool(a.get("retest_confirmed", True))
    if rep_diff > 10.0:
        q_notes.append(f"Frequency repeat response differed by {rep_diff:.1f} dB (>10 dB) -> repeat frequency required.")

    if stale or amb_bad or rep_diff > 10.0:
        if amb_bad:
            q_notes.append("Ambient background noise at test location exceeds NC-40 -> session rejected.")
        ind = _make_indicator(
            indicator="audiogram_sts_max_dB",
            value=None,
            unit="dB",
            status="rejected" if not stale else "no_data",
            message="; ".join(q_notes),
            action="Relocate crewmember to quiet crew quarters (<=NC-40) and repeat KUDUwave/OOHA audiogram.",
            decided_by="quality_check",
            rule_id="ACO-03-L0",
            source_ref="STD:OOHA-OSHA-STS-QC",
            data_source=data_source,
            baseline_val=0.0,
        )
        return _make_card_assessment(
            module_id="ACO-03",
            body_part_tag="ears",
            crew_id=crew_id,
            mission_day=mission_day,
            timestamp_utc=ts_utc,
            location=location,
            overall_status="no_data",
            quality_passed=False,
            quality_notes=q_notes,
            indicators=[ind],
            is_env_card=False,
            conclusion_actions=["Repeat pure-tone audiometry inside quiet NC-40 berth and confirm within-frequency repeatability <=10 dB."],
            routine_countermeasures=["Perform periodic OOHA/KUDUwave hearing checks in quiet sleep station."],
            how_to_measure="Test 500, 1000, 2000, 3000, 4000, 6000 Hz in <=NC-40 ambient noise; repeat any frequency differing >10 dB; confirm shifts on retest.",
            plain_explanation="Detects temporary or permanent cochlear threshold shifts early before irreversible sensorineural hearing loss occurs.",
            next_hours=24,
        )

    pre = {int(k): float(v) for k, v in (base.get("aco03_audiogram_preflight_dB") or {}).items()}
    right = {int(k): float(v) for k, v in (a.get("right_ear_dB") or {}).items()}
    left = {int(k): float(v) for k, v in (a.get("left_ear_dB") or {}).items()}

    def _ear_shifts(ear_map: dict[int, float]) -> tuple[float, float, float]:
        shifts = {f: ear_map.get(f, pre.get(f, 10.0)) - pre.get(f, 10.0) for f in AUDIO_FREQS_HZ}
        sts_avg = (shifts[2000] + shifts[3000] + shifts[4000]) / 3.0
        max_single = max(shifts.values())
        shift_500 = shifts[500]
        return sts_avg, max_single, shift_500

    r_sts, r_max, r_500 = _ear_shifts(right)
    l_sts, l_max, l_500 = _ear_shifts(left)
    worst_sts = max(r_sts, l_sts)
    worst_single = max(r_max, l_max)
    worst_500 = max(r_500, l_500)

    # Shifts count only if confirmed on retest
    if confirmed and worst_sts >= 10.0:
        l1_st = "red"
    elif confirmed and (worst_single >= 15.0 or worst_500 >= 15.0):
        l1_st = "yellow"
    else:
        if not confirmed and (worst_sts >= 10.0 or worst_single >= 15.0):
            q_notes.append("Unconfirmed threshold shift detected; retest required to confirm.")
        l1_st = "green"

    hist_sts = list(a.get("history_5_sts_dB") or [worst_sts] * 5)
    l2_st, l2_note = _evaluate_personal_baseline_l2(
        hist_sts,
        mean_val=float(base.get("aco03_sts_mean_dB", 1.0)),
        sd_val=float(base.get("aco03_sts_sd_dB", 2.5)),
        lower_is_worse=False,
    )
    times_h = [float(i * 720) for i in range(len(hist_sts))]
    ols = _ols_trend_layer3(times_h, hist_sts, red_limit=10.0, horizon_h=TREND_HORIZON_HOURS["ACO-03"])
    l3_st = "yellow" if ols["triggered"] else "green"

    final_st = _max_status(l1_st, l2_st, l3_st)
    if l1_st == "red":
        decided_by, rule_id, src = "fixed_threshold", "ACO-03-L1", "STD:OSHA-STS-NASA-OOHA"
        msg = f"Confirmed OSHA Standard Threshold Shift: 2/3/4 kHz average shift = {worst_sts:.1f} dB (>=10 dB)."
        act = "Enforce auditory rest + ANR hearing protection; notify ground & flight surgeon for clinical human decision."
    elif l2_st == "red":
        decided_by, rule_id, src = "baseline", "ACO-03-L2", "LIT:Preflight-Audiogram-Baseline"
        msg = l2_note
        act = "Enforce auditory rest and notify flight surgeon (human decision)."
    elif l1_st == "yellow":
        decided_by, rule_id, src = "fixed_threshold", "ACO-03-L1", "STD:OSHA-STS-NASA-OOHA"
        msg = f"Confirmed single-frequency shift {worst_single:.1f} dB (500 Hz shift {worst_500:.1f} dB) >= 15 dB; 2/3/4 kHz avg {worst_sts:.1f} dB."
        act = "Reduce noise exposure, verify headset volume, and schedule follow-up retest audiogram."
    elif l2_st == "yellow":
        decided_by, rule_id, src = "baseline", "ACO-03-L2", "LIT:Preflight-Audiogram-Baseline"
        msg = l2_note
        act = "Monitor hearing thresholds and minimize noisy rack exposure."
    elif l3_st == "yellow":
        decided_by, rule_id, src = "trend", "ACO-03-L3", "TEAM:5pt-OLS-next-audiogram"
        msg = f"2/3/4 kHz shift trend projects >=10 dB by next session (R²={ols['r2']:.2f})."
        act = "Increase hearing protection compliance during exercise/maintenance."
    else:
        decided_by, rule_id, src = "fixed_threshold", "ACO-03-L1", "STD:OSHA-STS-NASA-OOHA"
        msg = f"2/3/4 kHz avg shift {worst_sts:.1f} dB (<10 dB) and max single-freq shift {worst_single:.1f} dB (<15 dB)."
        act = "Hearing thresholds stable vs pre-flight baseline."

    ind = _make_indicator(
        indicator="audiogram_sts_max_dB",
        value=round(worst_sts, 2),
        unit="dB",
        status=final_st,
        message=msg,
        action=act,
        decided_by=decided_by,
        rule_id=rule_id,
        source_ref=src,
        data_source=data_source,
        baseline_val=0.0,
        yellow_threshold=6.0,
        red_threshold=10.0,
        history_days=[max(1, mission_day - 120 + 30 * i) for i in range(5)],
        history_values=[round(v, 2) for v in hist_sts[-5:]],
    )
    return _make_card_assessment(
        module_id="ACO-03",
        body_part_tag="ears",
        crew_id=crew_id,
        mission_day=mission_day,
        timestamp_utc=ts_utc,
        location=location,
        overall_status=final_st,
        quality_passed=True,
        quality_notes=q_notes,
        indicators=[ind],
        is_env_card=False,
        conclusion_actions=[act],
        routine_countermeasures=["Conduct periodic KUDUwave/OOHA audiograms and cross-reference with ACO-01/ACO-02 noise logs."],
        how_to_measure="Measure pure-tone thresholds at 500–6000 Hz in <=NC-40 background; confirm any shift on retest.",
        plain_explanation="Compares in-flight hearing sensitivity against pre-flight audiogram to catch noise-induced or CO2/fluid-shift auditory changes.",
        next_hours=24 if final_st != "green" else 720,
    )


def _eval_atm01(
    pay: dict[str, Any],
    base: dict[str, Any],
    mission_day: int,
    ts_utc: str,
    location: str,
    data_source: str,
) -> tuple[dict[str, Any], Optional[float]]:
    """Evaluate ATM-01 ppCO2, 1-h and 7-day rolling means. ppCO2 (mmHg) = ppm * 1e-6 * 760."""
    c = dict(pay.get("atm01_co2") or {})
    records = list(c.get("records_1h") or [])
    if pay.get("_override_ppco2_1h_mmHg") is not None:
        ov_mmhg = float(pay["_override_ppco2_1h_mmHg"])
        ov_ppm = ov_mmhg / (1e-6 * 760.0)
        records = [
            {"timestamp_utc": f"t-{4-i}", "co2_ppm": ov_ppm + (i % 2) * 5.0, "second_sensor_confirmed": True}
            for i in range(5)
        ]
        c["mean_7d_ppm"] = float(pay.get("_override_ppco2_7d_mmHg", min(ov_mmhg, 2.2))) / (1e-6 * 760.0)

    q_notes: list[str] = []
    stale, stale_msg = _check_staleness("ATM-01", pay.get("atm01_age_hours"))
    if stale:
        q_notes.append(stale_msg or "ATM-01 stale.")

    records, clean_notes = _clean_time_series(records)
    q_notes.extend(clean_notes)

    step_1m = float(c.get("step_change_1min_ppm", 0.0))
    step_conf = bool(c.get("step_second_sensor_confirmed", True))
    if abs(step_1m) > 1500.0 and not step_conf:
        q_notes.append(f"Unconfirmed 1-min CO2 step change {step_1m:.0f} ppm (>1500 ppm) flagged/rejected.")
        step_bad = True
    else:
        step_bad = False

    valid_ppm: list[float] = []
    out_of_range = 0
    for rec in records:
        ppm = rec.get("co2_ppm")
        if ppm is None or float(ppm) < 200.0 or float(ppm) > 20000.0:
            out_of_range += 1
            continue
        valid_ppm.append(float(ppm))
    if out_of_range:
        q_notes.append(f"Rejected {out_of_range} CO2 reading(s) outside 200–20,000 ppm.")

    # Check >= 24 identical consecutive hourly values (or explicit co2_sensor_stuck_hours >= 24)
    stuck_hours = float(pay.get("_override_co2_sensor_stuck_hours", pay.get("co2_sensor_stuck_hours", 0.0)))
    max_consec_identical = 1 if valid_ppm else 0
    cur_run = 1
    for idx in range(1, len(valid_ppm)):
        if abs(valid_ppm[idx] - valid_ppm[idx - 1]) < 1e-6:
            cur_run += 1
            max_consec_identical = max(max_consec_identical, cur_run)
        else:
            cur_run = 1
    is_stuck = max_consec_identical >= 24 or stuck_hours >= 24.0
    if is_stuck:
        q_notes.append(
            f"Stuck CO2 sensor detected: {max(max_consec_identical, int(stuck_hours))} identical consecutive hourly values (>=24 h)."
        )

    if stale or step_bad or is_stuck or not valid_ppm:
        ind = _make_indicator(
            indicator="ppco2_1h_mmHg",
            value=None,
            unit="mmHg",
            status="rejected" if (step_bad or is_stuck or out_of_range) else "no_data",
            message="; ".join(q_notes) or "No valid CO2 data.",
            action="Switch telemetry to backup CDRA/portable CO2 sensor and purge MCA sample line.",
            decided_by="quality_check",
            rule_id="ATM-01-L0",
            source_ref="LIT:ISS-MCA-RR1-Stuck-Sensor-QC",
            data_source=data_source,
            baseline_val=float(base.get("atm01_ppco2_median_mmHg", 1.82)),
        )
        card = _make_card_assessment(
            module_id="ATM-01",
            body_part_tag="lungs",
            crew_id=None,
            mission_day=mission_day,
            timestamp_utc=ts_utc,
            location=location,
            overall_status="no_data",
            quality_passed=False,
            quality_notes=q_notes,
            indicators=[ind],
            is_env_card=True,
            conclusion_actions=["Cross-check primary MCA IR bench against portable CO2 meter and backup CDRA sensor immediately."],
            routine_countermeasures=["Perform scheduled MCA zero/span calibration and verify inter-module air mixing fans."],
            how_to_measure="Convert CO2 ppm to ppCO2 (mmHg) = ppm * 1e-6 * 760; reject <200 or >20,000 ppm and >=24 h flatlined readings.",
            plain_explanation="Frozen CO2 sensors (like the ISS RR-1 152-h flatline) mask hypercapnia, causing headaches, cognitive slowing, and SANS risk.",
            next_hours=0,
        )
        return card, None

    mmhg_series = [ppm * 1e-6 * 760.0 for ppm in valid_ppm]
    curr_1h = mmhg_series[-1]
    mean_7d_ppm = float(c.get("mean_7d_ppm", np.mean(valid_ppm)))
    mean_7d_mmhg = mean_7d_ppm * 1e-6 * 760.0
    med_mmhg = float(base.get("atm01_ppco2_median_mmHg", 1.82))

    # Layer 1 Fixed Thresholds [V2 6004]
    if curr_1h > 3.0:
        l1_st = "red"
    elif mean_7d_mmhg >= 2.5 or (2.5 <= curr_1h <= 3.0):
        l1_st = "yellow"
    else:
        l1_st = "green"

    # Layer 2 7-d module median
    l2_st = "yellow" if curr_1h > med_mmhg + 0.6 else "green"

    # Layer 3 5-point OLS (horizon = 24 h -> Yellow only)
    times_h = [float(i) for i in range(len(mmhg_series))]
    ols = _ols_trend_layer3(times_h, mmhg_series, red_limit=3.0, horizon_h=TREND_HORIZON_HOURS["ATM-01"])
    l3_st = "yellow" if ols["triggered"] else "green"

    final_st = _max_status(l1_st, l2_st, l3_st)
    sev_note = " (EXCEEDS 5.3 mmHg SEVERE REF!)" if curr_1h > 5.3 else ""
    if l1_st == "red":
        decided_by, rule_id, src = "fixed_threshold", "ATM-01-L1", "STD:NASA-STD-3001-V2-6004"
        msg = f"1-h mean ppCO2 = {curr_1h:.2f} mmHg (>3.0 mmHg [V2 6004]){sev_note}; 7-d mean = {mean_7d_mmhg:.2f} mmHg."
        act = "Increase CO2 removal or move crew to a better-ventilated module; notify flight surgeon if headache is reported (human decision)."
    elif l1_st == "yellow":
        decided_by, rule_id, src = "fixed_threshold", "ATM-01-L1", "STD:NASA-STD-3001-V2-6004"
        msg = f"1-h mean ppCO2 = {curr_1h:.2f} mmHg, 7-d mean = {mean_7d_mmhg:.2f} mmHg (Yellow >=2.5 mmHg)."
        act = "Check CDRA and ventilation, prompt headache/vision self-report."
    elif l2_st == "yellow":
        decided_by, rule_id, src = "baseline", "ATM-01-L2", "LIT:ISS-CDRA-Module-Median"
        msg = f"1-h ppCO2 {curr_1h:.2f} mmHg elevated above module 7-d median ({med_mmhg:.2f} mmHg)."
        act = "Check CDRA bed cycle and portable ventilation fans."
    elif l3_st == "yellow":
        decided_by, rule_id, src = "trend", "ATM-01-L3", "TEAM:5pt-OLS-24h"
        msg = f"ppCO2 5-pt OLS projects >3.0 mmHg in {ols['ttr_h']:.1f} h (<=24 h, R²={ols['r2']:.2f})."
        act = "Check CDRA and ventilation, prompt headache/vision self-report."
    else:
        decided_by, rule_id, src = "fixed_threshold", "ATM-01-L1", "STD:NASA-STD-3001-V2-6004"
        msg = f"7-d mean ppCO2 = {mean_7d_mmhg:.2f} mmHg (<2.5) and 1-h mean = {curr_1h:.2f} mmHg."
        act = "Nominal CDRA CO2 scrubbing and inter-module ventilation."

    ind = _make_indicator(
        indicator="ppco2_1h_mmHg",
        value=round(curr_1h, 2),
        unit="mmHg",
        status=final_st,
        message=msg,
        action=act,
        decided_by=decided_by,
        rule_id=rule_id,
        source_ref=src,
        data_source=data_source,
        baseline_val=med_mmhg,
        slope_per_day=round(ols["slope_per_h"] * 24.0, 3) if ols["slope_per_h"] is not None else 0.0,
        yellow_threshold=2.5,
        red_threshold=3.0,
        history_days=[max(1, mission_day - 4 + i) for i in range(min(5, len(mmhg_series)))],
        history_values=[round(v, 2) for v in mmhg_series[-5:]],
    )
    card = _make_card_assessment(
        module_id="ATM-01",
        body_part_tag="lungs",
        crew_id=None,
        mission_day=mission_day,
        timestamp_utc=ts_utc,
        location=location,
        overall_status=final_st,
        quality_passed=True,
        quality_notes=q_notes,
        indicators=[ind],
        is_env_card=True,
        conclusion_actions=[act],
        routine_countermeasures=["Maintain 7-day rolling ppCO2 < 2.5 mmHg, clean air diffusers, and avoid stagnant sleep-berth CO2 pockets."],
        how_to_measure="Sample MCA / CDRA CO2 continuously; compute ppCO2 (mmHg) = ppm * 1e-6 * 760 over 1-h and 7-d windows.",
        plain_explanation="Elevated cabin CO2 dilates cerebral blood vessels, causing headaches, decision errors, and worsening optic disc edema (SANS).",
        next_hours=1 if final_st == "red" else (6 if final_st == "yellow" else 24),
    )
    return card, round(curr_1h, 2)


def _eval_atm02(
    pay: dict[str, Any],
    base: dict[str, Any],
    mission_day: int,
    ts_utc: str,
    location: str,
    data_source: str,
) -> dict[str, Any]:
    """Evaluate ATM-02 Cabin total pressure, dP/dt (1-m & 10-m), ppO2, PIO2 = FiO2 * (P_total - 47 mmHg)."""
    p_cfg = dict(pay.get("atm02_pressure") or {})
    records = list(p_cfg.get("records_1m") or [])
    if pay.get("_override_p_total_kPa") is not None or pay.get("_override_dpdt_kPa_per_min") is not None:
        ov_p = float(pay.get("_override_p_total_kPa", 101.3))
        ov_dpdt = float(pay.get("_override_dpdt_kPa_per_min", 0.0))
        records = [
            {"timestamp_utc": f"t-{4-i}", "p_sensor1_kPa": ov_p, "p_sensor2_kPa": ov_p, "o2_vol_pct": 21.0, "dpdt_1m_kPa_min": ov_dpdt, "dpdt_10m_kPa_min": ov_dpdt}
            for i in range(5)
        ]

    q_notes: list[str] = []
    stale, stale_msg = _check_staleness("ATM-02", pay.get("atm02_age_hours"))
    if stale:
        q_notes.append(stale_msg or "ATM-02 stale.")

    records, clean_notes = _clean_time_series(records)
    q_notes.extend(clean_notes)

    valid_recs: list[dict[str, Any]] = []
    range_rej = 0
    for rec in records:
        p1 = rec.get("p_sensor1_kPa")
        p2 = rec.get("p_sensor2_kPa", p1)
        if p1 is None or p2 is None or not (0.0 <= float(p1) <= 110.0) or not (0.0 <= float(p2) <= 110.0):
            range_rej += 1
            continue
        valid_recs.append(rec)
    if range_rej:
        q_notes.append(f"Rejected {range_rej} pressure reading(s) outside 0–110 kPa.")

    if stale or not valid_recs:
        ind = _make_indicator(
            indicator="p_total_kPa",
            value=None,
            unit="kPa",
            status="rejected" if range_rej else "no_data",
            message="; ".join(q_notes) or "No valid cabin pressure readings.",
            action="Cross-check module mechanical pressure gauge and secondary manometer immediately.",
            decided_by="quality_check",
            rule_id="ATM-02-L0",
            source_ref="STD:NASA-STD-3001-V2-6003-QC",
            data_source=data_source,
            baseline_val=101.3,
        )
        return _make_card_assessment(
            module_id="ATM-02",
            body_part_tag="lungs",
            crew_id=None,
            mission_day=mission_day,
            timestamp_utc=ts_utc,
            location=location,
            overall_status="no_data",
            quality_passed=False,
            quality_notes=q_notes,
            indicators=[ind],
            is_env_card=True,
            conclusion_actions=["Verify dual cabin pressure transducers and MCA O2 partial pressure bench."],
            routine_countermeasures=["Maintain redundant pressure transducers calibrated to 101.3 kPa nominal setpoint."],
            how_to_measure="Monitor dual pressure sensors (0–110 kPa; require <=0.5 kPa agreement for leak declaration) and compute PIO2 = FiO2 * (P_mmHg - 47).",
            plain_explanation="Protects against hypoxia (low PIO2), flammability (>23.5% O2), and hull micrometeoroid/seal depressurization.",
            next_hours=0,
        )

    last = valid_recs[-1]
    p1 = float(last["p_sensor1_kPa"])
    p2 = float(last.get("p_sensor2_kPa", p1))
    dual_agree = abs(p1 - p2) <= 0.5
    if not dual_agree:
        q_notes.append(f"Pressure sensors differ by {abs(p1-p2):.2f} kPa (>0.5 kPa) -> leak declaration suppressed pending confirmation.")

    p_kpa = 0.5 * (p1 + p2)
    p_mmhg = p_kpa * 7.50062
    o2_pct = float(last.get("o2_vol_pct", 21.0))
    fio2 = o2_pct / 100.0
    pio2 = float(pay["_override_pio2_mmHg"]) if pay.get("_override_pio2_mmHg") is not None else fio2 * (p_mmhg - 47.0)
    dpdt_1m = float(last.get("dpdt_1m_kPa_min", 0.0))
    dpdt_10m = float(last.get("dpdt_10m_kPa_min", 0.0))
    setpoint = float(base.get("atm02_setpoint_kPa", 101.3))

    rapid_leak = dual_agree and (dpdt_1m <= -0.10 or dpdt_10m <= -0.05)
    slow_decay = dual_agree and (dpdt_10m <= -0.001) and not rapid_leak

    # Fast-track: rapid depressurization
    if rapid_leak:
        final_st = "red"
        decided_by = "fast_track"
        rule_id = "ATM-02-L1"
        msg = f"FAST-TRACK RAPID DEPRESSURIZATION: P={p_kpa:.2f} kPa, dP/dt={dpdt_1m:.3f} kPa/min (dual sensors agree within {abs(p1-p2):.2f} kPa), PIO2={pio2:.1f} mmHg."
        act = "Execute depressurization emergency procedure; notify ground and flight surgeon immediately (human decision)."
    else:
        if pio2 < 127.0 or o2_pct > 23.5 or p_kpa < 34.5 or p_kpa > 103.0:
            l1_st = "red"
        elif 127.0 <= pio2 < 139.0 or pio2 > 168.0 or slow_decay:
            l1_st = "yellow"
        else:
            l1_st = "green"

        # Layer 2 Setpoint (+-1% of 101.3 kPa)
        l2_st = "yellow" if abs(p_kpa - setpoint) / setpoint > 0.01 else "green"

        # Layer 3 5-point OLS on PIO2 / Pressure (horizon = 1 h -> Yellow only)
        p_series = [0.5 * (float(r["p_sensor1_kPa"]) + float(r.get("p_sensor2_kPa", r["p_sensor1_kPa"]))) for r in valid_recs]
        times_h = [i * (1.0 / 60.0) for i in range(len(p_series))]
        ols = _ols_trend_layer3(times_h, p_series, red_limit=34.5, horizon_h=TREND_HORIZON_HOURS["ATM-02"], lower_is_worse=True)
        l3_st = "yellow" if ols["triggered"] else "green"

        final_st = _max_status(l1_st, l2_st, l3_st)
        if l1_st == "red":
            decided_by, rule_id = "fixed_threshold", "ATM-02-L1"
            msg = f"P={p_kpa:.2f} kPa, PIO2={pio2:.1f} mmHg (<127 mmHg), O2={o2_pct:.2f}% (>23.5% flammability)."
            act = "Execute depressurization / O2 emergency procedure; notify ground and flight surgeon immediately (human decision)."
        elif l1_st == "yellow":
            decided_by, rule_id = "fixed_threshold", "ATM-02-L1"
            msg = f"PIO2={pio2:.1f} mmHg (127–139 mmHg band) or slow pressure decay (P={p_kpa:.2f} kPa, dP/dt_10m={dpdt_10m:.4f} kPa/min)."
            act = "Inspect N2/O2 pressure control assembly (PCA) valves and check hull hatch seals with ultrasonic leak detector."
        elif l2_st == "yellow":
            decided_by, rule_id = "baseline", "ATM-02-L2"
            msg = f"Cabin pressure {p_kpa:.2f} kPa deviates >1% from {setpoint:.1f} kPa setpoint."
            act = "Verify PCA makeup gas feed and barometric trend."
        elif l3_st == "yellow":
            decided_by, rule_id = "trend", "ATM-02-L3"
            msg = f"5-pt OLS projects critical pressure drop within 1 h (R²={ols['r2']:.2f})."
            act = "Verify hatch seals and standby emergency O2 masks."
        else:
            decided_by, rule_id = "fixed_threshold", "ATM-02-L1"
            msg = f"Nominal cabin atmosphere: P={p_kpa:.2f} kPa (±1% of {setpoint:.1f}), PIO2={pio2:.1f} mmHg (139–168), O2={o2_pct:.1f}%."
            act = "Nominal cabin pressure and oxygen control."

    ind_p = _make_indicator(
        indicator="p_total_kPa",
        value=round(p_kpa, 2),
        unit="kPa",
        status=final_st,
        message=msg,
        action=act,
        decided_by=decided_by,
        rule_id=rule_id,
        source_ref="STD:NASA-STD-3001-V2-6003/6006",
        data_source=data_source,
        baseline_val=setpoint,
        yellow_threshold=100.2,
        red_threshold=94.0,
        lower_is_worse=True,
    )
    ind_pio2 = _make_indicator(
        indicator="pio2_mmHg",
        value=round(pio2, 1),
        unit="mmHg",
        status="red" if pio2 < 127.0 else ("yellow" if pio2 < 139.0 else "green"),
        message=f"Inspired oxygen PIO2 = {pio2:.1f} mmHg (FiO2={fio2:.3f}).",
        action=act,
        decided_by="fast_track" if decided_by == "fast_track" else "fixed_threshold",
        rule_id="ATM-02-L1",
        source_ref="STD:NASA-STD-3001-V2-6003",
        data_source=data_source,
        baseline_val=149.7,
        yellow_threshold=139.0,
        red_threshold=127.0,
        lower_is_worse=True,
    )
    return _make_card_assessment(
        module_id="ATM-02",
        body_part_tag="lungs",
        crew_id=None,
        mission_day=mission_day,
        timestamp_utc=ts_utc,
        location=location,
        overall_status=final_st,
        quality_passed=True,
        quality_notes=q_notes,
        indicators=[ind_p, ind_pio2],
        is_env_card=True,
        conclusion_actions=[act],
        routine_countermeasures=["Maintain 101.3 kPa total pressure, PIO2 139–168 mmHg, O2 <= 23.5%, and unobstructed hatch seals."],
        how_to_measure="Read dual cabin manometers (1-min/10-min dP/dt; <=0.5 kPa sensor agreement for leak) and compute PIO2 = FiO2 * (P_total - 47 mmHg).",
        plain_explanation="Prevents acute hypoxic incapacitation, cabin fire hazard (>23.5% O2), and rapid hull depressurization emergencies.",
        next_hours=0 if final_st == "red" else (1 if final_st == "yellow" else 24),
    )


def _eval_atm03(
    pay: dict[str, Any],
    base: dict[str, Any],
    mission_day: int,
    ts_utc: str,
    location: str,
    data_source: str,
) -> dict[str, Any]:
    """Evaluate ATM-03 Temperature & RH (THC sensors), 1-h means."""
    th = dict(pay.get("atm03_thermal") or {})
    records = list(th.get("records_1h") or [])
    if pay.get("_override_temp_C") is not None or pay.get("_override_rh_pct") is not None:
        ov_t = float(pay.get("_override_temp_C", 22.3))
        ov_rh = float(pay.get("_override_rh_pct", 45.0))
        records = [
            {"timestamp_utc": f"t-{4-i}", "temp_C": ov_t + 0.05 * (i % 2), "rh_pct": ov_rh + 0.1 * (i % 2)}
            for i in range(5)
        ]

    q_notes: list[str] = []
    stale, stale_msg = _check_staleness("ATM-03", pay.get("atm03_age_hours"))
    if stale:
        q_notes.append(stale_msg or "ATM-03 stale.")

    records, clean_notes = _clean_time_series(records)
    q_notes.extend(clean_notes)

    valid_recs: list[dict[str, Any]] = []
    range_rej = 0
    for rec in records:
        tc = rec.get("temp_C")
        rh = rec.get("rh_pct")
        if tc is None or rh is None or not (5.0 <= float(tc) <= 45.0) or not (0.0 <= float(rh) <= 100.0):
            range_rej += 1
            continue
        valid_recs.append(rec)
    if range_rej:
        q_notes.append(f"Rejected {range_rej} THC reading(s) outside 5–45 °C or 0–100% RH.")

    # Check flat-lined T or RH for > 6 h (>= 7 consecutive hourly points -> > 6 h span)
    t_run, rh_run, max_t_run, max_rh_run = 1, 1, (1 if valid_recs else 0), (1 if valid_recs else 0)
    for idx in range(1, len(valid_recs)):
        if abs(float(valid_recs[idx]["temp_C"]) - float(valid_recs[idx - 1]["temp_C"])) < 1e-6:
            t_run += 1
            max_t_run = max(max_t_run, t_run)
        else:
            t_run = 1
        if abs(float(valid_recs[idx]["rh_pct"]) - float(valid_recs[idx - 1]["rh_pct"])) < 1e-6:
            rh_run += 1
            max_rh_run = max(max_rh_run, rh_run)
        else:
            rh_run = 1
    is_flat = max_t_run > 6 or max_rh_run > 6
    if is_flat:
        q_notes.append(f"Stuck THC sensor: flat-lined T/RH for {max(max_t_run, max_rh_run)} h (>6 h limit).")

    if stale or is_flat or not valid_recs:
        ind = _make_indicator(
            indicator="temp_C",
            value=None,
            unit="C",
            status="rejected" if (is_flat or range_rej) else "no_data",
            message="; ".join(q_notes) or "No valid THC thermal data.",
            action="Switch to secondary cabin thermistor/hygrometer and inspect THC air-sampling louver.",
            decided_by="quality_check",
            rule_id="ATM-03-L0",
            source_ref="STD:THC-Sensor-QC",
            data_source=data_source,
            baseline_val=float(base.get("atm03_temp_median_C", 22.2)),
        )
        return _make_card_assessment(
            module_id="ATM-03",
            body_part_tag="whole_body",
            crew_id=None,
            mission_day=mission_day,
            timestamp_utc=ts_utc,
            location=location,
            overall_status="no_data",
            quality_passed=False,
            quality_notes=q_notes,
            indicators=[ind],
            is_env_card=True,
            conclusion_actions=["Cross-check THC sensor with portable psychrometer and verify fan airflow across sensor."],
            routine_countermeasures=["Keep cabin within 20–25 °C and 30–60% RH performance zone."],
            how_to_measure="Read 1-h mean Temperature (5–45 °C) and Relative Humidity (0–100%); reject >6 h flat-lined readings.",
            plain_explanation="Maintains thermal comfort, prevents heat strain during exercise, and suppresses condensation-driven fungal growth.",
            next_hours=1,
        )

    t_series = [float(r["temp_C"]) for r in valid_recs]
    rh_series = [float(r["rh_pct"]) for r in valid_recs]
    curr_t = t_series[-1]
    curr_rh = rh_series[-1]

    # Health envelope approximated as box 18–27 C / 25–75% RH; performance zone 20–25 C / 30–60% RH
    outside_health = not (18.0 <= curr_t <= 27.0 and 25.0 <= curr_rh <= 75.0)
    outside_perf = not (20.0 <= curr_t <= 25.0 and 30.0 <= curr_rh <= 60.0)
    if outside_health:
        l1_st = "red"
    elif outside_perf:
        l1_st = "yellow"
    else:
        l1_st = "green"

    t_med = float(base.get("atm03_temp_median_C", 22.2))
    l2_st = "yellow" if abs(curr_t - t_med) > 2.5 else "green"

    times_h = [float(i) for i in range(len(t_series))]
    ols_hi = _ols_trend_layer3(times_h, t_series, red_limit=27.0, horizon_h=TREND_HORIZON_HOURS["ATM-03"], lower_is_worse=False)
    ols_lo = _ols_trend_layer3(times_h, t_series, red_limit=18.0, horizon_h=TREND_HORIZON_HOURS["ATM-03"], lower_is_worse=True)
    l3_st = "yellow" if (ols_hi["triggered"] or ols_lo["triggered"]) else "green"

    final_st = _max_status(l1_st, l2_st, l3_st)
    if l1_st == "red":
        decided_by, rule_id, src = "fixed_threshold", "ATM-03-L1", "STD:NASA-STD-3001-V2-6012/6013"
        msg = f"T={curr_t:.1f} °C, RH={curr_rh:.1f}% outside health envelope (18–27 °C / 25–75% RH)."
        act = "Halt strenuous exercise, check CCAA condensing heat exchanger, increase hydration, notify ground & flight surgeon (human decision)."
    elif l1_st == "yellow":
        decided_by, rule_id, src = "fixed_threshold", "ATM-03-L1", "STD:NASA-STD-3001-V2-6013"
        msg = f"T={curr_t:.1f} °C, RH={curr_rh:.1f}% outside performance zone (20–25 °C / 30–60% RH) but inside health envelope."
        act = "Adjust THC temperature/humidity setpoint and inspect cold-plate condensate separator."
    elif l2_st == "yellow":
        decided_by, rule_id, src = "baseline", "ATM-03-L2", "LIT:Module-THC-7d-Median"
        msg = f"Temperature {curr_t:.1f} °C deviates >2.5 °C from 7-d median ({t_med:.1f} °C)."
        act = "Check avionics cooling loop heat load."
    elif l3_st == "yellow":
        decided_by, rule_id, src = "trend", "ATM-03-L3", "TEAM:5pt-OLS-12h"
        msg = "5-pt OLS projects exiting thermal health envelope within 12 h."
        act = "Adjust THC thermal control valve before envelope breach."
    else:
        decided_by, rule_id, src = "fixed_threshold", "ATM-03-L1", "STD:NASA-STD-3001-V2-6013"
        msg = f"T={curr_t:.1f} °C (20–25 °C) and RH={curr_rh:.1f}% (30–60%) inside nominal performance zone."
        act = "Nominal cabin thermal and humidity control."

    ind_t = _make_indicator(
        indicator="temp_C",
        value=round(curr_t, 1),
        unit="C",
        status=final_st,
        message=msg,
        action=act,
        decided_by=decided_by,
        rule_id=rule_id,
        source_ref=src,
        data_source=data_source,
        baseline_val=t_med,
        yellow_threshold=25.0,
        red_threshold=27.0,
    )
    ind_rh = _make_indicator(
        indicator="rh_pct",
        value=round(curr_rh, 1),
        unit="%",
        status="red" if not (25.0 <= curr_rh <= 75.0) else ("yellow" if not (30.0 <= curr_rh <= 60.0) else "green"),
        message=f"Cabin relative humidity = {curr_rh:.1f}%.",
        action=act,
        decided_by="fixed_threshold",
        rule_id="ATM-03-L1",
        source_ref="STD:NASA-STD-3001-V2-6012/6013",
        data_source=data_source,
        baseline_val=float(base.get("atm03_rh_median_pct", 45.0)),
        yellow_threshold=60.0,
        red_threshold=75.0,
    )
    return _make_card_assessment(
        module_id="ATM-03",
        body_part_tag="whole_body",
        crew_id=None,
        mission_day=mission_day,
        timestamp_utc=ts_utc,
        location=location,
        overall_status=final_st,
        quality_passed=True,
        quality_notes=q_notes,
        indicators=[ind_t, ind_rh],
        is_env_card=True,
        conclusion_actions=[act],
        routine_countermeasures=["Maintain THC performance zone (20–25 °C, 30–60% RH) to prevent heat stress and surface condensation."],
        how_to_measure="Monitor hourly THC temperature and relative humidity sensors across cabin modules.",
        plain_explanation="Excessive heat/humidity impairs cognitive alertness, raises cardiovascular strain, and promotes microbial biofilm growth.",
        next_hours=1 if final_st == "red" else (6 if final_st == "yellow" else 24),
    )


def _eval_atm04(
    pay: dict[str, Any],
    base: dict[str, Any],
    mission_day: int,
    ts_utc: str,
    location: str,
    data_source: str,
) -> dict[str, Any]:
    """Evaluate ATM-04 Trace contaminants (AQM VOCs, combustion products, ammonia); ratio = conc / SMAC."""
    v = dict(pay.get("atm04_voc") or {})
    if pay.get("_override_max_smac_ratio") is not None or pay.get("_override_ammonia_or_fire_alarm") is not None:
        v["internal_cal_passed"] = True
        if pay.get("_override_ammonia_or_fire_alarm") is not None:
            v["ammonia_alarm"] = bool(pay["_override_ammonia_or_fire_alarm"])
        if pay.get("_override_max_smac_ratio") is not None:
            ov_smac = float(pay["_override_max_smac_ratio"])
            v["compounds"] = [{"name": "override_voc", "conc_mg_m3": ov_smac * 10.0, "smac_mg_m3": 10.0, "duration": "7d"}]

    q_notes: list[str] = []
    stale, stale_msg = _check_staleness("ATM-04", pay.get("atm04_age_hours"))
    if stale:
        q_notes.append(stale_msg or "ATM-04 stale.")

    cal_ok = bool(v.get("internal_cal_passed", True))
    comb_alarm = bool(v.get("combustion_alarm", False))
    nh3_alarm = bool(v.get("ammonia_alarm", False))

    # Fast-track emergency overrides normal run QC if hardware alarm fires
    if comb_alarm or nh3_alarm:
        alarm_type = "COMBUSTION / FIRE" if comb_alarm else "AMMONIA LEAK"
        msg = f"FAST-TRACK {alarm_type} ALARM TRIGGERED!"
        act = (
            "Alert everyone first, then don masks/respirators (portable breathing apparatus -> emergency masks during fire); "
            "increase trace-contaminant scrubbing; notify ground and flight surgeon (human decision)."
        )
        ind = _make_indicator(
            indicator="max_smac_ratio",
            value=round(max(float(pay.get("max_smac_ratio", 1.0)), 1.0), 2),
            unit="SMAC_ratio",
            status="red",
            message=msg,
            action=act,
            decided_by="fast_track",
            rule_id="ATM-04-L1",
            source_ref="STD:NASA-STD-3001-V2-6050-SMAC",
            data_source=data_source,
            baseline_val=float(base.get("atm04_smac_ratio_median", 0.14)),
            yellow_threshold=0.5,
            red_threshold=1.0,
        )
        return _make_card_assessment(
            module_id="ATM-04",
            body_part_tag="lungs",
            crew_id=None,
            mission_day=mission_day,
            timestamp_utc=ts_utc,
            location=location,
            overall_status="red",
            quality_passed=True,
            quality_notes=q_notes,
            indicators=[ind],
            is_env_card=True,
            conclusion_actions=[act],
            routine_countermeasures=["Maintain TCCS charcoal/catalyst beds, AQM internal check standards, and accessible PBA respirators."],
            how_to_measure="Run AQM GC-MS trace gas sweeps and continuous combustion/NH3 electrochemical detectors; compute max(conc / SMAC).",
            plain_explanation="Toxic trace gases, battery/wire pyrolysis products, or cooling-loop ammonia leaks cause rapid airway injury or asphyxiation.",
            next_hours=0,
        )

    compounds = list(v.get("compounds") or [])
    valid_ratios: list[tuple[str, float]] = []
    neg_count = 0
    for comp in compounds:
        conc = comp.get("conc_mg_m3")
        smac = comp.get("smac_mg_m3", 1.0)
        if conc is None or float(conc) < 0.0 or float(smac) <= 0.0:
            neg_count += 1
            continue
        valid_ratios.append((str(comp.get("name", "voc")), float(conc) / float(smac)))

    if not cal_ok:
        q_notes.append("AQM run failed internal calibration check -> rejected.")
    if neg_count:
        q_notes.append(f"Rejected {neg_count} negative compound concentration(s).")

    if stale or not cal_ok or not valid_ratios:
        ind = _make_indicator(
            indicator="max_smac_ratio",
            value=None,
            unit="SMAC_ratio",
            status="rejected" if (not cal_ok or neg_count) else "no_data",
            message="; ".join(q_notes) or "No valid AQM compound ratios.",
            action="Re-run AQM internal calibration standard and verify grab-sample canister / Drager tube backup.",
            decided_by="quality_check",
            rule_id="ATM-04-L0",
            source_ref="STD:AQM-GCMS-QC",
            data_source=data_source,
            baseline_val=float(base.get("atm04_smac_ratio_median", 0.14)),
        )
        return _make_card_assessment(
            module_id="ATM-04",
            body_part_tag="lungs",
            crew_id=None,
            mission_day=mission_day,
            timestamp_utc=ts_utc,
            location=location,
            overall_status="no_data",
            quality_passed=False,
            quality_notes=q_notes,
            indicators=[ind],
            is_env_card=True,
            conclusion_actions=["Run AQM calibration check and verify cabin air with colorimetric Drager tubes if odor noticed."],
            routine_countermeasures=["Verify TCCS charcoal bed life and AQM carrier gas supply."],
            how_to_measure="Verify AQM internal calibration check; reject negative concentrations; report max(conc / SMAC) across compounds.",
            plain_explanation="Monitors off-gassing solvents, siloxanes, CO, and NH3 against Spacecraft Maximum Allowable Concentrations (SMAC).",
            next_hours=1,
        )

    worst_name, max_ratio = max(valid_ratios, key=lambda x: x[1])
    med_ratio = float(base.get("atm04_smac_ratio_median", 0.14))

    if max_ratio >= 1.0:
        l1_st = "red"
    elif max_ratio >= 0.5:
        l1_st = "yellow"
    else:
        l1_st = "green"

    l2_st = "yellow" if max_ratio > max(0.35, 2.0 * med_ratio) else "green"
    hist_r = list(v.get("history_5_smac_ratio") or [max_ratio] * 5)
    times_h = [float(i * 6) for i in range(len(hist_r))]
    ols = _ols_trend_layer3(times_h, hist_r, red_limit=1.0, horizon_h=TREND_HORIZON_HOURS["ATM-04"])
    l3_st = "yellow" if ols["triggered"] else "green"

    final_st = _max_status(l1_st, l2_st, l3_st)
    if l1_st == "red":
        decided_by, rule_id, src = "fixed_threshold", "ATM-04-L1", "STD:NASA-STD-3001-V2-6050-SMAC"
        msg = f"Max trace contaminant {worst_name} = {max_ratio*100:.0f}% SMAC (>=100% SMAC)."
        act = (
            "Alert everyone first, then masks/respirators (portable breathing apparatus -> emergency masks during fire); "
            "increase trace-contaminant scrubbing; notify ground and flight surgeon (human decision)."
        )
    elif l1_st == "yellow":
        decided_by, rule_id, src = "fixed_threshold", "ATM-04-L1", "STD:NASA-STD-3001-V2-6050-SMAC"
        msg = f"Max trace contaminant {worst_name} = {max_ratio*100:.0f}% SMAC (50–100% SMAC Yellow band)."
        act = "Inspect payload/stowage off-gassing source and increase TCCS trace-contaminant scrubbing."
    elif l2_st == "yellow":
        decided_by, rule_id, src = "baseline", "ATM-04-L2", "LIT:AQM-Trace-Gas-Baseline"
        msg = f"Max SMAC ratio {max_ratio:.2f} > 2x module 7-d median ({med_ratio:.2f})."
        act = "Check recent wet-wipe / solvent usage and TCCS flow rate."
    elif l3_st == "yellow":
        decided_by, rule_id, src = "trend", "ATM-04-L3", "TEAM:5pt-OLS-24h"
        msg = f"SMAC ratio 5-pt OLS projects >=1.0 SMAC in {ols['ttr_h']:.1f} h (<=24 h, R²={ols['r2']:.2f})."
        act = "Increase TCCS scrubbing and isolate suspected off-gassing source."
    else:
        decided_by, rule_id, src = "fixed_threshold", "ATM-04-L1", "STD:NASA-STD-3001-V2-6050-SMAC"
        msg = f"All trace compounds < 50% SMAC (max: {worst_name} at {max_ratio*100:.0f}% SMAC)."
        act = "Nominal TCCS trace-contaminant control."

    ind = _make_indicator(
        indicator="max_smac_ratio",
        value=round(max_ratio, 2),
        unit="SMAC_ratio",
        status=final_st,
        message=msg,
        action=act,
        decided_by=decided_by,
        rule_id=rule_id,
        source_ref=src,
        data_source=data_source,
        baseline_val=med_ratio,
        yellow_threshold=0.5,
        red_threshold=1.0,
        history_days=[max(1, mission_day - 4 + i) for i in range(5)],
        history_values=[round(x, 2) for x in hist_r[-5:]],
    )
    return _make_card_assessment(
        module_id="ATM-04",
        body_part_tag="lungs",
        crew_id=None,
        mission_day=mission_day,
        timestamp_utc=ts_utc,
        location=location,
        overall_status=final_st,
        quality_passed=True,
        quality_notes=q_notes,
        indicators=[ind],
        is_env_card=True,
        conclusion_actions=[act],
        routine_countermeasures=["Enforce strict flight material off-gassing screening, log alcohol-wipe usage, and maintain TCCS beds."],
        how_to_measure="Compute conc / SMAC for each AQM compound at relevant duration; report maximum ratio.",
        plain_explanation="Prevents neurotoxic, hepatotoxic, or irritant buildup inside sealed spacecraft air loops.",
        next_hours=0 if final_st == "red" else (6 if final_st == "yellow" else 24),
    )


def _eval_atm05(
    pay: dict[str, Any],
    base: dict[str, Any],
    mission_day: int,
    ts_utc: str,
    location: str,
    data_source: str,
) -> dict[str, Any]:
    """Evaluate ATM-05 Potable water (TOCA weekly): TOC, iodine, silver."""
    w = dict(pay.get("atm05_water") or {})
    q_notes: list[str] = []
    stale, stale_msg = _check_staleness("ATM-05", pay.get("atm05_age_hours"))
    if stale:
        q_notes.append(stale_msg or "ATM-05 stale.")

    cal_ok = bool(w.get("std_cal_passed", True))
    if not cal_ok:
        q_notes.append("TOCA run failed standard/calibration check -> rejected.")

    toc_num, toc_str, toc_bdl = _parse_water_val(w.get("toc_mg_L", 0.68), detection_limit=0.10)
    iod_num, iod_str, iod_bdl = _parse_water_val(w.get("iodine_mg_L", 0.12), detection_limit=0.05)
    ag_num, ag_str, ag_bdl = _parse_water_val(w.get("silver_ug_L", 260.0), detection_limit=10.0)
    if toc_bdl or iod_bdl or ag_bdl:
        q_notes.append("Below-detection-limit water analyte stored as '< DL' (never 0).")

    if stale or not cal_ok or toc_num is None or iod_num is None or ag_num is None:
        ind = _make_indicator(
            indicator="water_toc_mg_L",
            value=None,
            unit="mg/L",
            status="rejected" if not cal_ok else "no_data",
            message="; ".join(q_notes) or "Invalid TOCA water chemistry run.",
            action="Re-run TOCA calibration standard check; use contingency iodinated/silvered potable water bag until verified.",
            decided_by="quality_check",
            rule_id="ATM-05-L0",
            source_ref="STD:TOCA-Water-QC",
            data_source=data_source,
            baseline_val=0.65,
        )
        return _make_card_assessment(
            module_id="ATM-05",
            body_part_tag="whole_body",
            crew_id=None,
            mission_day=mission_day,
            timestamp_utc=ts_utc,
            location=location,
            overall_status="no_data",
            quality_passed=False,
            quality_notes=q_notes,
            indicators=[ind],
            is_env_card=True,
            conclusion_actions=["Repeat TOCA water quality run with fresh check standard."],
            routine_countermeasures=["Conduct weekly TOCA analysis and biocide check per potable water dispenser."],
            how_to_measure="Run weekly TOCA for TOC, residual iodine (at dispenser), and silver; store below-DL values as '< DL', never 0.",
            plain_explanation="Protects recycled WPA drinking water against organic chemical breakthrough, thyroid iodine excess, or biocide loss.",
            next_hours=24,
        )

    src_name = str(w.get("water_source", "WPA_dispenser"))
    src_medians = dict(base.get("atm05_toc_median_mg_L") or {})
    src_med = float(src_medians.get(src_name, 0.65))

    # Layer 1 Fixed Thresholds:
    # G: TOC < 1.5 mg/L; iodine <= 0.2 mg/L; silver 100-500 ug/L
    # Y: TOC 1.5-3.0 mg/L or rising trend; silver < 100 ug/L
    # R: TOC > 3.0 mg/L; iodine > 0.2 mg/L; silver > 500 ug/L
    if toc_num > 3.0 or iod_num > 0.2 or ag_num > 500.0:
        l1_st = "red"
    elif (1.5 <= toc_num <= 3.0) or ag_num < 100.0:
        l1_st = "yellow"
    else:
        l1_st = "green"

    l2_st = "yellow" if toc_num > src_med + 0.8 else "green"
    hist_toc = list(w.get("history_5_toc_mg_L") or [toc_num] * 5)
    times_h = [float(i * 168) for i in range(len(hist_toc))]
    ols = _ols_trend_layer3(times_h, hist_toc, red_limit=3.0, horizon_h=TREND_HORIZON_HOURS["ATM-05"])
    l3_st = "yellow" if ols["triggered"] else "green"

    final_st = _max_status(l1_st, l2_st, l3_st)
    if l1_st == "red":
        decided_by, rule_id, src_ref = "fixed_threshold", "ATM-05-L1", "STD:NASA-STD-3001-V2-6026-Potable-Water"
        msg = f"Potable water ({src_name}): TOC={toc_str} mg/L (>3.0), I2={iod_str} mg/L (>0.2), Ag={ag_str} ug/L (>500)."
        act = "Halt consumption from affected dispenser, switch to reserve potable water, replace WPA multifiltration/ACTEX bed, notify flight surgeon (human decision)."
    elif l1_st == "yellow":
        decided_by, rule_id, src_ref = "fixed_threshold", "ATM-05-L1", "STD:NASA-STD-3001-V2-6026-Potable-Water"
        msg = f"Potable water ({src_name}): TOC={toc_str} mg/L (1.5–3.0) or Ag={ag_str} ug/L (<100 ug/L biocide floor)."
        act = "Flush dispenser line, inspect WPA catalytic reactor / silver dosing bed, and schedule 48-h TOCA recheck."
    elif l2_st == "yellow":
        decided_by, rule_id, src_ref = "baseline", "ATM-05-L2", "LIT:WPA-Potable-Source-Baseline"
        msg = f"TOC {toc_str} mg/L elevated above {src_name} baseline ({src_med:.2f} mg/L)."
        act = "Monitor WPA multifiltration bed breakthrough."
    elif l3_st == "yellow":
        decided_by, rule_id, src_ref = "trend", "ATM-05-L3", "TEAM:5pt-OLS-30d"
        msg = f"TOC 5-pt OLS projects >3.0 mg/L within 30 days (R²={ols['r2']:.2f})."
        act = "Prepare spare WPA multifiltration bed for scheduled swap."
    else:
        decided_by, rule_id, src_ref = "fixed_threshold", "ATM-05-L1", "STD:NASA-STD-3001-V2-6026-Potable-Water"
        msg = f"Potable water ({src_name}) nominal: TOC={toc_str} mg/L (<1.5), I2={iod_str} mg/L (<=0.2), Ag={ag_str} ug/L (100–500)."
        act = "Potable water safe for crew consumption."

    ind_toc = _make_indicator(
        indicator="water_toc_mg_L",
        value="< DL" if toc_bdl else round(toc_num, 2),
        unit="mg/L",
        status=final_st,
        message=msg,
        action=act,
        decided_by=decided_by,
        rule_id=rule_id,
        source_ref=src_ref,
        data_source=data_source,
        baseline_val=src_med,
        yellow_threshold=1.5,
        red_threshold=3.0,
    )
    ind_i2 = _make_indicator(
        indicator="water_iodine_mg_L",
        value="< DL" if iod_bdl else round(iod_num, 3),
        unit="mg/L",
        status="red" if iod_num > 0.2 else "green",
        message=f"Dispenser iodine = {iod_str} mg/L (limit <=0.2 mg/L).",
        action=act,
        decided_by="fixed_threshold",
        rule_id="ATM-05-L1",
        source_ref="STD:NASA-STD-3001-V2-6026-Potable-Water",
        data_source=data_source,
        baseline_val="< DL",
        red_threshold=0.2,
    )
    return _make_card_assessment(
        module_id="ATM-05",
        body_part_tag="whole_body",
        crew_id=None,
        mission_day=mission_day,
        timestamp_utc=ts_utc,
        location=location,
        overall_status=final_st,
        quality_passed=True,
        quality_notes=q_notes,
        indicators=[ind_toc, ind_i2],
        is_env_card=True,
        conclusion_actions=[act],
        routine_countermeasures=["Perform weekly TOCA water analysis and maintain residual biocide (silver 100–500 ug/L or I2 removal ACTEX)."],
        how_to_measure="Analyze TOC, iodine, and silver weekly per water source; record values below detection limit as '< DL' (never 0).",
        plain_explanation="Closed-loop urine/condensate water recovery requires strict organic carbon and biocide bounds to prevent toxicity and biofilm.",
        next_hours=24 if final_st != "green" else 168,
    )


def _eval_atm06(
    pay: dict[str, Any],
    base: dict[str, Any],
    mission_day: int,
    ts_utc: str,
    location: str,
    data_source: str,
) -> dict[str, Any]:
    """Evaluate ATM-06 Microbial (quarterly air/surface/water; water coliforms monthly)."""
    m = dict(pay.get("atm06_microbial") or {})
    q_notes: list[str] = []
    stale, stale_msg = _check_staleness("ATM-06", pay.get("atm06_age_hours"))
    if stale:
        q_notes.append(stale_msg or "ATM-06 stale.")

    inc_ok = bool(m.get("incubation_complete", True))
    cond_bad = bool(m.get("condensation_spread", False))
    blank_ok = bool(m.get("blank_present", True))
    if not inc_ok:
        q_notes.append("Plate incubation incomplete -> rejected.")
    if cond_bad:
        q_notes.append("Plate condensation colony spread detected -> rejected.")
    if not blank_ok:
        q_notes.append("Negative control blank missing -> rejected.")

    if stale or not inc_ok or cond_bad or not blank_ok:
        ind = _make_indicator(
            indicator="microbial_max_limit_ratio",
            value=None,
            unit="limit_ratio",
            status="rejected" if (not inc_ok or cond_bad or not blank_ok) else "no_data",
            message="; ".join(q_notes),
            action="Re-sample air/surface/water using fresh contact slides/media with negative blank and full incubation.",
            decided_by="quality_check",
            rule_id="ATM-06-L0",
            source_ref="STD:ISS-Microbial-Assay-QC",
            data_source=data_source,
            baseline_val=float(base.get("atm06_limit_ratio_median", 0.12)),
        )
        return _make_card_assessment(
            module_id="ATM-06",
            body_part_tag="whole_body",
            crew_id=None,
            mission_day=mission_day,
            timestamp_utc=ts_utc,
            location=location,
            overall_status="no_data",
            quality_passed=False,
            quality_notes=q_notes,
            indicators=[ind],
            is_env_card=True,
            conclusion_actions=["Repeat microbial sampling with negative control blank and complete incubation."],
            routine_countermeasures=["Perform quarterly air/surface/water microbial assays and monthly water coliform checks."],
            how_to_measure="Incubate air/surface/water culture plates with negative blank; reject incomplete incubation or condensation spread.",
            plain_explanation="Spaceflight immune dysregulation heightens opportunistic bacterial/fungal infection risk from cabin surfaces, air, or water.",
            next_hours=24,
        )

    ratios = {
        "air_bacteria": float(m.get("air_bacteria_cfu_m3", 140.0)) / 1000.0,
        "air_fungi": float(m.get("air_fungi_cfu_m3", 12.0)) / 100.0,
        "surface_bacteria": float(m.get("surface_bacteria_cfu_100cm2", 950.0)) / 10000.0,
        "surface_fungi": float(m.get("surface_fungi_cfu_100cm2", 10.0)) / 100.0,
        "water_hpc": float(m.get("water_heterotrophic_cfu_mL", 6.0)) / 50.0,
    }
    coliform = bool(m.get("water_coliform_100mL_detected", False))
    w_fungi = bool(m.get("water_fungi_100mL_detected", False))
    worst_key, max_ratio = max(ratios.items(), key=lambda x: x[1])
    if coliform or w_fungi:
        max_ratio = max(max_ratio, 1.0)

    if max_ratio >= 1.0 or coliform or w_fungi:
        l1_st = "red"
    elif max_ratio >= 0.5:
        l1_st = "yellow"
    else:
        l1_st = "green"

    med_r = float(base.get("atm06_limit_ratio_median", 0.12))
    l2_st = "yellow" if max_ratio > max(0.35, 2.0 * med_r) else "green"
    hist_r = list(m.get("history_5_limit_ratio") or [max_ratio] * 5)
    times_h = [float(i * 2160) for i in range(len(hist_r))]
    ols = _ols_trend_layer3(times_h, hist_r, red_limit=1.0, horizon_h=TREND_HORIZON_HOURS["ATM-06"])
    l3_st = "yellow" if ols["triggered"] else "green"

    final_st = _max_status(l1_st, l2_st, l3_st)
    if l1_st == "red":
        decided_by, rule_id, src = "fixed_threshold", "ATM-06-L1", "STD:NASA-STD-3001-V2-6059-Microbial"
        msg = f"Microbial exceedance ({worst_key}={max_ratio*100:.0f}% limit; coliform={coliform}, water_fungi={w_fungi})."
        act = "Isolate contaminated water dispenser / disinfect surfaces with approved biocide wipes, inspect HEPA filters, notify flight surgeon (human decision)."
    elif l1_st == "yellow":
        decided_by, rule_id, src = "fixed_threshold", "ATM-06-L1", "STD:NASA-STD-3001-V2-6059-Microbial"
        msg = f"Microbial load {worst_key} at {max_ratio*100:.0f}% of NASA limit (50–100% Yellow)."
        act = "Perform targeted surface disinfection, vacuum HEPA return grilles, and schedule re-sampling."
    elif l2_st == "yellow":
        decided_by, rule_id, src = "baseline", "ATM-06-L2", "LIT:ISS-Microbial-Baseline"
        msg = f"Microbial ratio {max_ratio:.2f} > 2x module baseline ({med_r:.2f})."
        act = "Increase weekly housekeeping wet-wipe schedule."
    elif l3_st == "yellow":
        decided_by, rule_id, src = "trend", "ATM-06-L3", "TEAM:5pt-OLS-next-quarterly"
        msg = f"Microbial 5-pt OLS projects >=100% limit by next quarterly assay (R²={ols['r2']:.2f})."
        act = "Inspect condensate zones behind panels and clean air return grilles."
    else:
        decided_by, rule_id, src = "fixed_threshold", "ATM-06-L1", "STD:NASA-STD-3001-V2-6059-Microbial"
        msg = f"All microbial counts <50% of limit (max {worst_key} = {max_ratio*100:.0f}%, coliforms/fungi absent)."
        act = "Continue routine housekeeping disinfection and HEPA filtration."

    ind = _make_indicator(
        indicator="microbial_max_limit_ratio",
        value=round(max_ratio, 2),
        unit="limit_ratio",
        status=final_st,
        message=msg,
        action=act,
        decided_by=decided_by,
        rule_id=rule_id,
        source_ref=src,
        data_source=data_source,
        baseline_val=med_r,
        yellow_threshold=0.5,
        red_threshold=1.0,
    )
    return _make_card_assessment(
        module_id="ATM-06",
        body_part_tag="whole_body",
        crew_id=None,
        mission_day=mission_day,
        timestamp_utc=ts_utc,
        location=location,
        overall_status=final_st,
        quality_passed=True,
        quality_notes=q_notes,
        indicators=[ind],
        is_env_card=True,
        conclusion_actions=[act],
        routine_countermeasures=["Maintain HEPA filtration, weekly antimicrobial surface wipe-downs, and monthly potable water coliform tests."],
        how_to_measure="Compare air (1000/100 CFU/m³), surface (10,000/100 CFU/100 cm²), and water (50 CFU/mL; 0 coliform/fungi per 100 mL) to limits.",
        plain_explanation="Prevents cabin fungal blooms, waterborne GI illness, and respiratory allergens in microgravity.",
        next_hours=24 if final_st != "green" else 720,
    )


def _eval_atm07(
    pay: dict[str, Any],
    base: dict[str, Any],
    mission_day: int,
    ts_utc: str,
    location: str,
    data_source: str,
) -> dict[str, Any]:
    """Evaluate ATM-07 Particulates (SIMULATED low-cost sensor, 1-h means)."""
    # Guide explicitly notes ATM-07 is a SIMULATED low-cost sensor (ISS has no operational monitor)
    part_source = "SIMULATED"
    p = dict(pay.get("atm07_particulates") or {})
    records = list(p.get("records_1h") or [])
    q_notes: list[str] = []
    stale, stale_msg = _check_staleness("ATM-07", pay.get("atm07_age_hours"))
    if stale:
        q_notes.append(stale_msg or "ATM-07 stale.")

    records, clean_notes = _clean_time_series(records)
    q_notes.extend(clean_notes)

    valid_recs: list[dict[str, Any]] = []
    self_clean_cnt = 0
    over_range_cnt = 0
    for rec in records:
        if bool(rec.get("self_clean_active", False)):
            self_clean_cnt += 1
            continue
        tot = float(rec.get("total_dust_mg_m3", 0.0))
        pm25 = float(rec.get("respirable_pm25_mg_m3", 0.0))
        lunar = float(rec.get("lunar_dust_twa_mg_m3", 0.0))
        rated_max = float(rec.get("sensor_rated_max_mg_m3", 10.0))
        if tot < 0 or pm25 < 0 or lunar < 0:
            continue
        if tot > rated_max or pm25 > rated_max:
            over_range_cnt += 1
            q_notes.append(f"Particulate reading {tot:.2f} mg/m³ exceeds sensor rated range ({rated_max:.1f} mg/m³).")
        valid_recs.append(rec)

    if self_clean_cnt:
        q_notes.append(f"Rejected {self_clean_cnt} particulate reading(s) during sensor self-clean purge.")

    if stale or not valid_recs:
        ind = _make_indicator(
            indicator="particulate_max_limit_ratio",
            value=None,
            unit="limit_ratio",
            status="rejected" if self_clean_cnt else "no_data",
            message="; ".join(q_notes) or "No valid particulate readings outside self-clean window.",
            action="Await completion of optical dust sensor zero-air self-clean cycle.",
            decided_by="quality_check",
            rule_id="ATM-07-L0",
            source_ref="TEAM:Simulated-Optical-Dust-QC",
            data_source=part_source,
            baseline_val=float(base.get("atm07_limit_ratio_median", 0.15)),
        )
        return _make_card_assessment(
            module_id="ATM-07",
            body_part_tag="lungs",
            crew_id=None,
            mission_day=mission_day,
            timestamp_utc=ts_utc,
            location=location,
            overall_status="no_data",
            quality_passed=False,
            quality_notes=q_notes,
            indicators=[ind],
            is_env_card=True,
            conclusion_actions=["Wait for optical particulate sensor self-clean cycle to finish and inspect inlet."],
            routine_countermeasures=["Vacuum HEPA return screens weekly and run airlock dust mitigation post-EVA."],
            how_to_measure="Read 1-h optical particulate sensor means (total dust, PM2.5 respirable, lunar dust TWA); reject self-clean intervals.",
            plain_explanation="Floating particulates and sharp lunar regolith dust do not settle in microgravity/hypogravity, risking corneal and alveolar injury.",
            next_hours=1,
        )

    ratio_series = [
        max(
            float(r.get("total_dust_mg_m3", 0.0)) / 3.0,
            float(r.get("respirable_pm25_mg_m3", 0.0)) / 1.0,
            float(r.get("lunar_dust_twa_mg_m3", 0.0)) / 0.3,
        )
        for r in valid_recs
    ]
    last = valid_recs[-1]
    curr_r = ratio_series[-1]
    med_r = float(base.get("atm07_limit_ratio_median", 0.15))

    if curr_r >= 1.0:
        l1_st = "red"
    elif curr_r >= 0.5:
        l1_st = "yellow"
    else:
        l1_st = "green"

    l2_st = "yellow" if curr_r > max(0.35, 2.0 * med_r) else "green"
    times_h = [float(i) for i in range(len(ratio_series))]
    ols = _ols_trend_layer3(times_h, ratio_series, red_limit=1.0, horizon_h=TREND_HORIZON_HOURS["ATM-07"])
    l3_st = "yellow" if ols["triggered"] else "green"

    final_st = _max_status(l1_st, l2_st, l3_st)
    if l1_st == "red":
        decided_by, rule_id, src = "fixed_threshold", "ATM-07-L1", "STD:NASA-STD-3001-V2-6052-Lunar-Dust"
        msg = (
            f"Particulate limit reached: total={float(last['total_dust_mg_m3']):.2f}/3.0, "
            f"PM2.5={float(last['respirable_pm25_mg_m3']):.2f}/1.0, lunar={float(last['lunar_dust_twa_mg_m3']):.2f}/0.3 mg/m³."
        )
        act = "Don N95/P100 respiratory & eye protection, maximize HEPA air scrubbing, isolate dusty EVA suits, notify flight surgeon (human decision)."
    elif l1_st == "yellow":
        decided_by, rule_id, src = "fixed_threshold", "ATM-07-L1", "STD:NASA-STD-3001-V2-6052-Lunar-Dust"
        msg = f"Particulates at {curr_r*100:.0f}% of limit (50–100% Yellow)."
        act = "Vacuum HEPA intake screens, wipe airlock surfaces, and wear eye/dust protection during cleanup."
    elif l2_st == "yellow":
        decided_by, rule_id, src = "baseline", "ATM-07-L2", "TEAM:Simulated-Particulate-7d-Median"
        msg = f"Particulate ratio {curr_r:.2f} > 2x 7-d median ({med_r:.2f})."
        act = "Check cabin HEPA filter differential pressure."
    elif l3_st == "yellow":
        decided_by, rule_id, src = "trend", "ATM-07-L3", "TEAM:5pt-OLS-24h"
        msg = f"Particulate 5-pt OLS projects reaching limit in {ols['ttr_h']:.1f} h (<=24 h, R²={ols['r2']:.2f})."
        act = "Increase HEPA fan flow and inspect cargo transfer dust."
    else:
        decided_by, rule_id, src = "fixed_threshold", "ATM-07-L1", "STD:NASA-STD-3001-V2-6052-Lunar-Dust"
        msg = f"Airborne particulates <50% of limits (max ratio = {curr_r*100:.0f}%)."
        act = "Nominal cabin HEPA particulate filtration."

    ind = _make_indicator(
        indicator="particulate_max_limit_ratio",
        value=round(curr_r, 2),
        unit="limit_ratio",
        status=final_st,
        message=msg,
        action=act,
        decided_by=decided_by,
        rule_id=rule_id,
        source_ref=src,
        data_source=part_source,
        baseline_val=med_r,
        yellow_threshold=0.5,
        red_threshold=1.0,
        history_days=[max(1, mission_day - 4 + i) for i in range(min(5, len(ratio_series)))],
        history_values=[round(x, 2) for x in ratio_series[-5:]],
    )
    return _make_card_assessment(
        module_id="ATM-07",
        body_part_tag="lungs",
        crew_id=None,
        mission_day=mission_day,
        timestamp_utc=ts_utc,
        location=location,
        overall_status=final_st,
        quality_passed=True,
        quality_notes=q_notes,
        indicators=[ind],
        is_env_card=True,
        conclusion_actions=[act],
        routine_countermeasures=["Maintain HEPA filters and enforce strict post-EVA suit vacuuming / airlock isolation."],
        how_to_measure="Monitor simulated 1-h optical dust sensor against total (3 mg/m³), respirable <2.5 um (1 mg/m³), and lunar dust TWA (0.3 mg/m³) limits.",
        plain_explanation="Prevents ocular foreign-body injury and lunar dust pneumoconiosis in reduced-gravity habitats.",
        next_hours=1 if final_st == "red" else (6 if final_st == "yellow" else 24),
    )


def _eval_iso01(
    pay: dict[str, Any],
    base: dict[str, Any],
    crew_id: str,
    mission_day: int,
    ts_utc: str,
    location: str,
    data_source: str,
) -> tuple[dict[str, Any], Optional[float]]:
    """Evaluate ISO-01 Sleep (Actiwatch + morning log); simulate N(6.09 h, 0.67 h)."""
    s = dict(pay.get("iso01_sleep") or {})
    nights = list(s.get("nights") or [])
    if pay.get("_override_sleep_tst_h") is not None:
        ov_slp = float(pay["_override_sleep_tst_h"])
        nights = [
            {"timestamp_utc": f"d-{6-i}", "tst_h": ov_slp, "self_report_h": ov_slp, "wear_time_pct": 95.0}
            for i in range(7)
        ]

    q_notes: list[str] = []
    stale, stale_msg = _check_staleness("ISO-01", pay.get("iso01_age_hours"))
    if stale:
        q_notes.append(stale_msg or "ISO-01 stale.")

    nights, clean_notes = _clean_time_series(nights)
    q_notes.extend(clean_notes)

    valid_tst: list[float] = []
    low_wear = 0
    for n in nights:
        wear = float(n.get("wear_time_pct", 95.0))
        tst = n.get("tst_h")
        if wear < 80.0 or tst is None or not (0.0 <= float(tst) <= 24.0):
            low_wear += 1
            continue
        sr = n.get("self_report_h")
        if sr is not None and abs(float(sr) - float(tst)) > 2.0:
            q_notes.append(f"Flagged self-report vs actigraphy discrepancy of {abs(float(sr)-float(tst)):.1f} h (>2 h).")
        valid_tst.append(float(tst))

    if low_wear:
        q_notes.append(f"Rejected {low_wear} night(s) with <80% Actiwatch wear time or invalid range.")

    if stale or not valid_tst:
        ind = _make_indicator(
            indicator="sleep_tst_h",
            value=None,
            unit="h",
            status="rejected" if low_wear else "no_data",
            message="; ".join(q_notes) or "No valid Actiwatch sleep nights (>=80% wear).",
            action="Ensure wrist Actiwatch snug contact (>=80% nightly wear) and complete morning sleep log.",
            decided_by="quality_check",
            rule_id="ISO-01-L0",
            source_ref="LIT:Actiwatch-Sleep-QC-N(6.09,0.67)",
            data_source=data_source,
            baseline_val=float(base.get("iso01_sleep_mean_h", 7.35)),
        )
        card = _make_card_assessment(
            module_id="ISO-01",
            body_part_tag="brain",
            crew_id=crew_id,
            mission_day=mission_day,
            timestamp_utc=ts_utc,
            location=location,
            overall_status="no_data",
            quality_passed=False,
            quality_notes=q_notes,
            indicators=[ind],
            is_env_card=False,
            conclusion_actions=["Verify Actiwatch wrist strap fit (>=80% wear time) and re-sync tomorrow morning."],
            routine_countermeasures=["Protect an uninterrupted 8.5-h sleep opportunity and cool/quiet sleep berth."],
            how_to_measure="Wear Actiwatch overnight (>=80% wear time) + morning sleep log; flag >2 h log discrepancy.",
            plain_explanation="Chronic spaceflight sleep restriction (ISS average ~6.09 h) degrades vigilance, immune defense, and mood stability.",
            next_hours=24,
        )
        return card, None

    curr_tst = valid_tst[-1]
    consec_under_6 = 0
    for val in reversed(valid_tst):
        if val < 6.0:
            consec_under_6 += 1
        else:
            break

    # Layer 1 Fixed Thresholds: G >= 7 h; Y 6-7 h or single night < 6 h; R < 6 h for >= 3 consecutive nights
    if consec_under_6 >= 3:
        l1_st = "red"
    elif curr_tst < 7.0:
        l1_st = "yellow"
    else:
        l1_st = "green"

    l2_st, l2_note = _evaluate_personal_baseline_l2(
        valid_tst,
        mean_val=float(base.get("iso01_sleep_mean_h", 7.35)),
        sd_val=float(base.get("iso01_sleep_sd_h", 0.45)),
        lower_is_worse=True,
    )
    times_h = [float(i * 24) for i in range(len(valid_tst))]
    ols = _ols_trend_layer3(times_h, valid_tst, red_limit=6.0, horizon_h=TREND_HORIZON_HOURS["ISO-01"], lower_is_worse=True)
    l3_st = "yellow" if ols["triggered"] else "green"

    final_st = _max_status(l1_st, l2_st, l3_st)
    if l1_st == "red":
        decided_by, rule_id, src = "fixed_threshold", "ISO-01-L1", "STD:NASA-STD-3001-V1-5001-Sleep"
        msg = f"Total sleep time {curr_tst:.2f} h (<6 h for {consec_under_6} consecutive nights >=3)."
        act = "Defer high-risk EVA/robotics, enforce protected sleep recovery block, check ISO-04 light/ACO-02 noise, flight surgeon review (human decision)."
    elif l2_st == "red":
        decided_by, rule_id, src = "baseline", "ISO-01-L2", "LIT:Personal-Sleep-Baseline"
        msg = l2_note
        act = "Enforce protected sleep recovery block and flight surgeon fatigue review (human decision)."
    elif l1_st == "yellow":
        decided_by, rule_id, src = "fixed_threshold", "ISO-01-L1", "STD:NASA-STD-3001-V1-5001-Sleep"
        msg = f"Total sleep time {curr_tst:.2f} h (<7.0 h; consecutive <6 h nights = {consec_under_6})."
        act = "Eliminate evening schedule slam-shifts, dim pre-sleep cabin lighting (<=20 lux), and verify berth noise/temperature."
    elif l2_st == "yellow":
        decided_by, rule_id, src = "baseline", "ISO-01-L2", "LIT:Personal-Sleep-Baseline"
        msg = l2_note
        act = "Protect upcoming 8.5-h sleep window."
    elif l3_st == "yellow":
        decided_by, rule_id, src = "trend", "ISO-01-L3", "TEAM:5pt-OLS-14d"
        msg = f"5-pt OLS projects sleep dropping below 6.0 h within 14 days (R²={ols['r2']:.2f})."
        act = "Review crew timeline workload and circadian light hygiene."
    else:
        decided_by, rule_id, src = "fixed_threshold", "ISO-01-L1", "STD:NASA-STD-3001-V1-5001-Sleep"
        msg = f"Total sleep time {curr_tst:.2f} h (>=7.0 h optimal)."
        act = "Maintain consistent circadian wake/sleep schedule."

    ind = _make_indicator(
        indicator="sleep_tst_h",
        value=round(curr_tst, 2),
        unit="h",
        status=final_st,
        message=msg,
        action=act,
        decided_by=decided_by,
        rule_id=rule_id,
        source_ref=src,
        data_source=data_source,
        baseline_val=float(base.get("iso01_sleep_mean_h", 7.35)),
        yellow_threshold=7.0,
        red_threshold=6.0,
        lower_is_worse=True,
        history_days=[max(1, mission_day - len(valid_tst[-5:]) + 1 + i) for i in range(len(valid_tst[-5:]))],
        history_values=[round(x, 2) for x in valid_tst[-5:]],
    )
    card = _make_card_assessment(
        module_id="ISO-01",
        body_part_tag="brain",
        crew_id=crew_id,
        mission_day=mission_day,
        timestamp_utc=ts_utc,
        location=location,
        overall_status=final_st,
        quality_passed=True,
        quality_notes=q_notes,
        indicators=[ind],
        is_env_card=False,
        conclusion_actions=[act],
        routine_countermeasures=["Enforce >=8.5 h scheduled sleep window, morning blue-enriched light, and quiet NC-40 sleep berth."],
        how_to_measure="Record nightly Actiwatch TST (>=80% wear) + morning subjective sleep log.",
        plain_explanation="Adequate sleep (>=7 h) preserves reaction speed, emotional regulation, and antiviral T-cell immunity.",
        next_hours=24,
    )
    return card, round(curr_tst, 2)


def _eval_iso02(
    pay: dict[str, Any],
    base: dict[str, Any],
    crew_id: str,
    mission_day: int,
    ts_utc: str,
    location: str,
    data_source: str,
) -> dict[str, Any]:
    """Evaluate ISO-02 PVT-B (3-min; am/pm every 4th day): response speed and lapses (>500 ms)."""
    p = dict(pay.get("iso02_pvt") or {})
    sessions = list(p.get("sessions") or [])
    if pay.get("_override_pvt_speed_1_per_s") is not None:
        ov_spd = float(pay["_override_pvt_speed_1_per_s"])
        sessions = [
            {"timestamp_utc": f"s-{4-i}", "response_speed_1_s": ov_spd, "lapses": 2, "false_starts": 2, "missed_stimuli_pct": 2.0, "pre_eva": False}
            for i in range(5)
        ]

    q_notes: list[str] = []
    stale, stale_msg = _check_staleness("ISO-02", pay.get("iso02_age_hours"))
    if stale:
        q_notes.append(stale_msg or "ISO-02 stale.")

    sessions, clean_notes = _clean_time_series(sessions)
    q_notes.extend(clean_notes)

    valid_sess: list[dict[str, Any]] = []
    rej_cnt = 0
    for s in sessions:
        fs = int(s.get("false_starts", 0))
        miss = float(s.get("missed_stimuli_pct", 0.0))
        spd = s.get("response_speed_1_s")
        if fs > 10 or miss > 20.0 or spd is None or float(spd) <= 0.0 or float(spd) > 10.0:
            rej_cnt += 1
            continue
        valid_sess.append(s)

    if rej_cnt:
        q_notes.append(f"Rejected {rej_cnt} PVT-B session(s) with false starts >10 or >20% missed stimuli.")

    if stale or not valid_sess:
        ind = _make_indicator(
            indicator="pvt_speed_1_per_s",
            value=None,
            unit="1/s",
            status="rejected" if rej_cnt else "no_data",
            message="; ".join(q_notes) or "No valid 3-min PVT-B session.",
            action="Repeat 3-min PVT-B in distraction-free posture without anticipatory button presses.",
            decided_by="quality_check",
            rule_id="ISO-02-L0",
            source_ref="LIT:PVT-B-Basner-Dinges-QC",
            data_source=data_source,
            baseline_val=float(base.get("iso02_pvt_speed_mean", 4.25)),
        )
        return _make_card_assessment(
            module_id="ISO-02",
            body_part_tag="brain",
            crew_id=crew_id,
            mission_day=mission_day,
            timestamp_utc=ts_utc,
            location=location,
            overall_status="no_data",
            quality_passed=False,
            quality_notes=q_notes,
            indicators=[ind],
            is_env_card=False,
            conclusion_actions=["Repeat 3-min PVT-B ensuring <=10 false starts and <=20% missed stimuli."],
            routine_countermeasures=["Administer am/pm 3-min PVT-B every 4th mission day and prior to EVA/docking."],
            how_to_measure="Run 3-min Psychomotor Vigilance Test (PVT-B); reject if false starts >10 or >20% stimuli missed.",
            plain_explanation="Objective neurobehavioral assay sensitive to sleep debt, cabin hypercapnia (ppCO2), and circadian misalignment.",
            next_hours=12,
        )

    spd_series = [float(s["response_speed_1_s"]) for s in valid_sess]
    curr_spd = spd_series[-1]
    curr_lapses = int(valid_sess[-1].get("lapses", 0))
    pre_eva = bool(valid_sess[-1].get("pre_eva", False))
    mean_spd = float(base.get("iso02_pvt_speed_mean", 4.25))
    sd_spd = float(base.get("iso02_pvt_speed_sd", 0.30))

    thresh_1sd = mean_spd - 1.0 * sd_spd
    thresh_2sd = mean_spd - 2.0 * sd_spd
    two_consec_2sd = len(spd_series) >= 2 and spd_series[-1] < thresh_2sd and spd_series[-2] < thresh_2sd

    if two_consec_2sd or (pre_eva and curr_spd < thresh_2sd):
        l1_st = "red"
    elif curr_spd < thresh_1sd:
        l1_st = "yellow"
    else:
        l1_st = "green"

    l2_st, l2_note = _evaluate_personal_baseline_l2(spd_series, mean_spd, sd_spd, lower_is_worse=True)
    times_h = [float(i * 96) for i in range(len(spd_series))]
    ols = _ols_trend_layer3(times_h, spd_series, red_limit=thresh_2sd, horizon_h=TREND_HORIZON_HOURS["ISO-02"], lower_is_worse=True)
    l3_st = "yellow" if ols["triggered"] else "green"

    final_st = _max_status(l1_st, l2_st, l3_st)
    if l1_st == "red" or l2_st == "red":
        decided_by = "fixed_threshold" if l1_st == "red" else "baseline"
        rule_id = "ISO-02-L1" if l1_st == "red" else "ISO-02-L2"
        msg = f"PVT-B speed {curr_spd:.2f} 1/s (<baseline-2SD {thresh_2sd:.2f}; lapses={curr_lapses}, pre_EVA={pre_eva})."
        act = "Hold safety-critical EVA/robotics until rested; cross-check ISO-01 sleep & ATM-01 CO2; flight surgeon review (human decision)."
    elif l1_st == "yellow" or l2_st == "yellow":
        decided_by = "baseline"
        rule_id = "ISO-02-L2"
        msg = f"PVT-B speed {curr_spd:.2f} 1/s (<baseline-1SD {thresh_1sd:.2f}; lapses={curr_lapses})."
        act = "Schedule nap/recovery sleep opportunity and check cabin ppCO2 ventilation."
    elif l3_st == "yellow":
        decided_by, rule_id = "trend", "ISO-02-L3"
        msg = f"PVT-B 5-pt OLS projects crossing -2 SD within 14 days (R²={ols['r2']:.2f})."
        act = "Reduce timeline task density and protect sleep window."
    else:
        decided_by, rule_id = "baseline", "ISO-02-L1"
        msg = f"PVT-B response speed {curr_spd:.2f} 1/s within personal baseline ({mean_spd:.2f} ± {sd_spd:.2f}); lapses={curr_lapses}."
        act = "Vigilance and reaction speed nominal."

    ind = _make_indicator(
        indicator="pvt_speed_1_per_s",
        value=round(curr_spd, 2),
        unit="1/s",
        status=final_st,
        message=msg,
        action=act,
        decided_by=decided_by,
        rule_id=rule_id,
        source_ref="LIT:PVT-B-Alertness-Thresholds",
        data_source=data_source,
        baseline_val=mean_spd,
        yellow_threshold=round(thresh_1sd, 2),
        red_threshold=round(thresh_2sd, 2),
        lower_is_worse=True,
        history_days=[max(1, mission_day - 16 + 4 * i) for i in range(min(5, len(spd_series)))],
        history_values=[round(x, 2) for x in spd_series[-5:]],
    )
    return _make_card_assessment(
        module_id="ISO-02",
        body_part_tag="brain",
        crew_id=crew_id,
        mission_day=mission_day,
        timestamp_utc=ts_utc,
        location=location,
        overall_status=final_st,
        quality_passed=True,
        quality_notes=q_notes,
        indicators=[ind],
        is_env_card=False,
        conclusion_actions=[act],
        routine_countermeasures=["Perform am/pm 3-min PVT-B every 4th day and pre-EVA to verify neurobehavioral readiness."],
        how_to_measure="Complete 3-min PVT-B recording reciprocal RT speed (1/s) and >500 ms lapses.",
        plain_explanation="Detects subtle cognitive slowing before operational errors occur during docking, robotics, or EVA.",
        next_hours=24 if final_st != "green" else 96,
    )


def _eval_iso03(
    pay: dict[str, Any],
    base: dict[str, Any],
    crew_id: str,
    mission_day: int,
    ts_utc: str,
    location: str,
    data_source: str,
) -> dict[str, Any]:
    """Evaluate ISO-03 Mood/stress/workload: daily VAS 0–100, monthly POMS-37, Bedford workload."""
    m = dict(pay.get("iso03_mood") or {})
    entries = list(m.get("entries") or [])
    if pay.get("_override_workload_bedford") is not None or pay.get("_override_stress_vas") is not None:
        ov_bed = float(pay.get("_override_workload_bedford", 3.0))
        ov_vas = float(pay.get("_override_stress_vas", 22.0))
        # Scale legacy 0-10 slider input if small
        if ov_vas <= 10.0 and ov_bed > 5.0:
            ov_vas = ov_vas * 10.0
        entries = [
            {"timestamp_utc": f"d-{6-i}", "vas_stress": ov_vas, "bedford_workload": ov_bed, "poms37_tmd": 8.0, "hopelessness_flag": False, "straight_lined": False, "complete": True}
            for i in range(7)
        ]

    q_notes: list[str] = []
    stale, stale_msg = _check_staleness("ISO-03", pay.get("iso03_age_hours"))
    if stale:
        q_notes.append(stale_msg or "ISO-03 stale.")

    # Privacy rule: strip any free-text journal field immediately so it is never stored or echoed
    sanitized_entries: list[dict[str, Any]] = []
    stripped_journal = False
    for raw_e in entries:
        e_copy = {k: v for k, v in raw_e.items() if k != "journal_text"}
        if "journal_text" in raw_e:
            stripped_journal = True
        sanitized_entries.append(e_copy)
    if stripped_journal:
        q_notes.append("Privacy guard: free-text journal entry stripped locally (never stored centrally).")

    sanitized_entries, clean_notes = _clean_time_series(sanitized_entries)
    q_notes.extend(clean_notes)

    valid_entries: list[dict[str, Any]] = []
    rej_cnt = 0
    for e in sanitized_entries:
        vas = e.get("vas_stress")
        bed = e.get("bedford_workload")
        if (
            bool(e.get("straight_lined", False))
            or not bool(e.get("complete", True))
            or vas is None
            or bed is None
            or not (0.0 <= float(vas) <= 100.0)
            or not (1.0 <= float(bed) <= 10.0)
        ):
            rej_cnt += 1
            continue
        valid_entries.append(e)

    if rej_cnt:
        q_notes.append(f"Rejected {rej_cnt} straight-lined, incomplete, or out-of-range survey entry/entries.")

    if stale or not valid_entries:
        ind = _make_indicator(
            indicator="workload_bedford",
            value=None,
            unit="Bedford_1_10",
            status="rejected" if rej_cnt else "no_data",
            message="; ".join(q_notes) or "No valid ISO-03 mood/workload check-in.",
            action="Prompt brief non-intrusive Bedford & VAS check-in at crew convenience.",
            decided_by="quality_check",
            rule_id="ISO-03-L0",
            source_ref="LIT:Behavioral-Survey-Privacy-QC",
            data_source=data_source,
            baseline_val=2.0,
        )
        return _make_card_assessment(
            module_id="ISO-03",
            body_part_tag="brain",
            crew_id=crew_id,
            mission_day=mission_day,
            timestamp_utc=ts_utc,
            location=location,
            overall_status="no_data",
            quality_passed=False,
            quality_notes=q_notes,
            indicators=[ind],
            is_env_card=False,
            conclusion_actions=["Re-administer brief daily VAS & post-task Bedford rating (never storing journal text centrally)."],
            routine_countermeasures=["Maintain reasonable timeline margins and weekly family/leisure time."],
            how_to_measure="Collect daily 0–100 VAS mood/stress, post-task Bedford (1–10), and monthly POMS-37; reject straight-lined/incomplete.",
            plain_explanation="Monitors cognitive overload and confinement stress while strictly protecting crew diary privacy.",
            next_hours=24,
        )

    vas_series = [float(e["vas_stress"]) for e in valid_entries]
    bed_series = [float(e["bedford_workload"]) for e in valid_entries]
    curr_vas = vas_series[-1]
    curr_bed = bed_series[-1]
    hopeless = bool(valid_entries[-1].get("hopelessness_flag", False))

    vas_mean = float(base.get("iso03_vas_stress_mean", 24.0))
    vas_sd = float(base.get("iso03_vas_stress_sd", 7.0))
    vas_worse_thresh = vas_mean + 1.0 * vas_sd

    consec_worse_vas = 0
    for val in reversed(vas_series):
        if val > vas_worse_thresh:
            consec_worse_vas += 1
        else:
            break

    if curr_bed > 6.0 or consec_worse_vas >= 7 or hopeless:
        l1_st = "red"
    elif (4.0 <= curr_bed <= 6.0) or consec_worse_vas >= 3:
        l1_st = "yellow"
    else:
        l1_st = "green"

    l2_st, l2_note = _evaluate_personal_baseline_l2(vas_series, vas_mean, vas_sd, lower_is_worse=False)
    times_h = [float(i * 24) for i in range(len(vas_series))]
    ols = _ols_trend_layer3(times_h, bed_series, red_limit=6.0, horizon_h=TREND_HORIZON_HOURS["ISO-03"], lower_is_worse=False)
    l3_st = "yellow" if ols["triggered"] else "green"

    final_st = _max_status(l1_st, l2_st, l3_st)
    if l1_st == "red" or l2_st == "red":
        decided_by = "fixed_threshold" if l1_st == "red" else "baseline"
        rule_id = "ISO-03-L1" if l1_st == "red" else "ISO-03-L2"
        msg = f"Bedford={curr_bed:.0f} (>6), VAS={curr_vas:.0f} ({consec_worse_vas} d > baseline), hopelessness={hopeless}."
        act = (
            "Shed non-essential timeline tasks immediately; offer optional private medical/psychological conference "
            "(crewmember chooses whether to request private conference; human decision)."
        )
    elif l1_st == "yellow" or l2_st == "yellow":
        decided_by = "fixed_threshold" if l1_st == "yellow" else "baseline"
        rule_id = "ISO-03-L1" if l1_st == "yellow" else "ISO-03-L2"
        msg = f"Bedford workload={curr_bed:.0f} (4–6) or VAS stress={curr_vas:.0f} ({consec_worse_vas} consecutive days > baseline)."
        act = "Rebalance crew task schedule at next planning conference and protect personal off-duty downtime."
    elif l3_st == "yellow":
        decided_by, rule_id = "trend", "ISO-03-L3"
        msg = f"Bedford workload 5-pt OLS projects >6 within 14 days (R²={ols['r2']:.2f})."
        act = "Trim upcoming discretionary payload tasks."
    else:
        decided_by, rule_id = "fixed_threshold", "ISO-03-L1"
        msg = f"Bedford workload={curr_bed:.0f} (<=3) and VAS stress={curr_vas:.0f} within personal baseline."
        act = "Workload and behavioral health nominal."

    ind_bed = _make_indicator(
        indicator="workload_bedford",
        value=round(curr_bed, 1),
        unit="score",
        status=final_st,
        message=msg,
        action=act,
        decided_by=decided_by,
        rule_id=rule_id,
        source_ref="STD:NASA-STD-3001-V2-5007-Bedford",
        data_source=data_source,
        baseline_val=2.0,
        yellow_threshold=4.0,
        red_threshold=6.0,
        history_days=[max(1, mission_day - len(bed_series[-5:]) + 1 + i) for i in range(len(bed_series[-5:]))],
        history_values=[round(x, 1) for x in bed_series[-5:]],
    )
    ind_vas = _make_indicator(
        indicator="stress_vas",
        value=round(curr_vas, 1),
        unit="VAS_0_100",
        status=final_st if consec_worse_vas >= 3 else "green",
        message=f"Daily VAS stress = {curr_vas:.1f} (baseline {vas_mean:.1f} ± {vas_sd:.1f}).",
        action=act,
        decided_by=decided_by,
        rule_id=rule_id,
        source_ref="LIT:Personal-Mood-Stress-Baseline",
        data_source=data_source,
        baseline_val=vas_mean,
        yellow_threshold=round(vas_worse_thresh, 1),
        red_threshold=round(vas_mean + 2.0 * vas_sd, 1),
    )
    return _make_card_assessment(
        module_id="ISO-03",
        body_part_tag="brain",
        crew_id=crew_id,
        mission_day=mission_day,
        timestamp_utc=ts_utc,
        location=location,
        overall_status=final_st,
        quality_passed=True,
        quality_notes=q_notes,
        indicators=[ind_bed, ind_vas],
        is_env_card=False,
        conclusion_actions=[act],
        routine_countermeasures=["Keep Bedford workload <=3 on routine days, protect private crew communications, never centralize journal text."],
        how_to_measure="Administer daily 0–100 VAS, post-major-task Bedford scale (1–10), and monthly POMS-37.",
        plain_explanation="Prevents task saturation and isolation burnout on long-duration transit without infringing crew autonomy or privacy.",
        next_hours=24,
    )


def _eval_iso04(
    pay: dict[str, Any],
    base: dict[str, Any],
    iso01_status: str,
    crew_id: str,
    mission_day: int,
    ts_utc: str,
    location: str,
    data_source: str,
) -> dict[str, Any]:
    """Evaluate ISO-04 Light & circadian timing: morning lux (2 h), pre-sleep lux (3 h), sleep-midpoint shift."""
    l_cfg = dict(pay.get("iso04_light") or {})
    days = list(l_cfg.get("days") or [])
    q_notes: list[str] = []
    stale, stale_msg = _check_staleness("ISO-04", pay.get("iso04_age_hours"))
    if stale:
        q_notes.append(stale_msg or "ISO-04 stale.")

    days, clean_notes = _clean_time_series(days)
    q_notes.extend(clean_notes)

    valid_days: list[dict[str, Any]] = []
    rej_cnt = 0
    for d in days:
        if (
            bool(d.get("off_wrist", False))
            or bool(d.get("sleeve_covered", False))
            or d.get("presleep_lux") is None
            or float(d.get("presleep_lux", 0.0)) < 0.0
        ):
            rej_cnt += 1
            continue
        valid_days.append(d)

    if rej_cnt:
        q_notes.append(f"Rejected {rej_cnt} light-sensor period(s) due to off-wrist or sleeve-covered flag.")

    if stale or not valid_days:
        ind = _make_indicator(
            indicator="circadian_midpoint_shift_h",
            value=None,
            unit="h",
            status="rejected" if rej_cnt else "no_data",
            message="; ".join(q_notes) or "No valid uncovered wrist light exposure data.",
            action="Keep Actiwatch light sensor uncovered outside flight-suit cuff during wake hours.",
            decided_by="quality_check",
            rule_id="ISO-04-L0",
            source_ref="LIT:Actiwatch-Light-Sensor-QC",
            data_source=data_source,
            baseline_val=0.15,
        )
        return _make_card_assessment(
            module_id="ISO-04",
            body_part_tag="brain",
            crew_id=crew_id,
            mission_day=mission_day,
            timestamp_utc=ts_utc,
            location=location,
            overall_status="no_data",
            quality_passed=False,
            quality_notes=q_notes,
            indicators=[ind],
            is_env_card=False,
            conclusion_actions=["Wear wrist photometer uncovered during first 2 h after waking and 3 h before sleep."],
            routine_countermeasures=["Program SSLAs: bright blue-enriched morning light and <=20 lux warm pre-sleep lighting."],
            how_to_measure="Measure photopic/melanopic lux in first 2 h post-wake, 3 h pre-sleep, and sleep-midpoint phase shift.",
            plain_explanation="Without a 24-h planetary sunrise, improper evening light suppresses melatonin and desynchronizes circadian clocks.",
            next_hours=24,
        )

    window7 = valid_days[-7:]
    nights_over_100 = sum(1 for d in window7 if float(d["presleep_lux"]) > 100.0)
    shifts = [abs(float(d.get("midpoint_shift_h", 0.0))) for d in valid_days]
    curr_shift = shifts[-1]
    curr_pre_lux = float(valid_days[-1]["presleep_lux"])
    curr_morn_lux = float(valid_days[-1].get("morning_lux", 300.0))

    # Count consecutive day-level Yellow conditions (pre-sleep > 100 lux or midpoint shift > 1 h or missing morning light < 50 lux)
    consec_yellow_days = 0
    for d in reversed(valid_days):
        day_is_yel = float(d["presleep_lux"]) > 100.0 or abs(float(d.get("midpoint_shift_h", 0.0))) > 1.0 or float(d.get("morning_lux", 300.0)) < 50.0
        if day_is_yel:
            consec_yellow_days += 1
        else:
            break

    # Layer 1 Fixed Thresholds:
    # G: pre-sleep <= ~20 lux and morning light present (>=100 lux) and shift <= 1 h
    # Y: pre-sleep > 100 lux on >= 2 of 7 nights, or midpoint shift > 1 h (or pre-sleep > 20 lux / low morning light)
    # R: Yellow on >= 3 consecutive nights together with ISO-01 Yellow/Red, or midpoint shift > 2 h
    if curr_shift > 2.0 or (consec_yellow_days >= 3 and iso01_status in {"yellow", "red"}):
        l1_st = "red"
    elif nights_over_100 >= 2 or curr_shift > 1.0 or curr_pre_lux > 20.0 or curr_morn_lux < 100.0:
        l1_st = "yellow"
    else:
        l1_st = "green"

    l2_st, l2_note = _evaluate_personal_baseline_l2(
        shifts,
        mean_val=float(base.get("iso04_midpoint_shift_mean_h", 0.15)),
        sd_val=float(base.get("iso04_midpoint_shift_sd_h", 0.30)),
        lower_is_worse=False,
    )
    times_h = [float(i * 24) for i in range(len(shifts))]
    ols = _ols_trend_layer3(times_h, shifts, red_limit=2.0, horizon_h=TREND_HORIZON_HOURS["ISO-04"], lower_is_worse=False)
    l3_st = "yellow" if ols["triggered"] else "green"

    final_st = _max_status(l1_st, l2_st, l3_st)
    if l1_st == "red" or l2_st == "red":
        decided_by = "fixed_threshold" if l1_st == "red" else "baseline"
        rule_id = "ISO-04-L1" if l1_st == "red" else "ISO-04-L2"
        msg = f"Sleep-midpoint shift {curr_shift:.2f} h (>2 h) or {consec_yellow_days} consec light-Yellow nights with ISO-01={iso01_status}."
        act = "Deploy timed Solid-State Lighting Assembly (SSLA) phase-reset protocol, screen-dimming filters, flight surgeon circadian consult (human decision)."
    elif l1_st == "yellow" or l2_st == "yellow":
        decided_by = "fixed_threshold" if l1_st == "yellow" else "baseline"
        rule_id = "ISO-04-L1" if l1_st == "yellow" else "ISO-04-L2"
        msg = f"Pre-sleep={curr_pre_lux:.0f} lux ({nights_over_100}/7 nights >100 lux), midpoint shift={curr_shift:.2f} h."
        act = "Switch cabin SSLAs to pre-sleep depleted-blue mode (<=20 lux) 3 h before bedtime and boost 2-h morning bright light."
    elif l3_st == "yellow":
        decided_by, rule_id = "trend", "ISO-04-L3"
        msg = f"Midpoint drift 5-pt OLS projects >2.0 h phase shift within 14 days (R²={ols['r2']:.2f})."
        act = "Anchor daily wake time with 2-h morning high-melanopic SSLA exposure."
    else:
        decided_by, rule_id = "fixed_threshold", "ISO-04-L1"
        msg = f"Pre-sleep {curr_pre_lux:.0f} lux (<=20 lux), morning {curr_morn_lux:.0f} lux, midpoint shift {curr_shift:.2f} h (<=1 h)."
        act = "Circadian light exposure and phase alignment nominal."

    ind = _make_indicator(
        indicator="circadian_midpoint_shift_h",
        value=round(curr_shift, 2),
        unit="h",
        status=final_st,
        message=msg,
        action=act,
        decided_by=decided_by,
        rule_id=rule_id,
        source_ref="STD:NASA-STD-3001-V2-6086-Lighting",
        data_source=data_source,
        baseline_val=0.15,
        yellow_threshold=1.0,
        red_threshold=2.0,
        history_days=[max(1, mission_day - len(shifts[-5:]) + 1 + i) for i in range(len(shifts[-5:]))],
        history_values=[round(x, 2) for x in shifts[-5:]],
    )
    return _make_card_assessment(
        module_id="ISO-04",
        body_part_tag="brain",
        crew_id=crew_id,
        mission_day=mission_day,
        timestamp_utc=ts_utc,
        location=location,
        overall_status=final_st,
        quality_passed=True,
        quality_notes=q_notes,
        indicators=[ind],
        is_env_card=False,
        conclusion_actions=[act],
        routine_countermeasures=["Enforce NASA dynamic SSLA schedule: high morning melanopic lux (first 2 h) and <=20 lux in 3 h pre-sleep."],
        how_to_measure="Track wrist photometer lux (first 2 h post-wake & 3 h pre-sleep) and sleep-midpoint shift; reject sleeve-covered periods.",
        plain_explanation="Entrains the hypothalamic suprachiasmatic nucleus to prevent free-running circadian desynchrony.",
        next_hours=24,
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
        for ind in c["indicators"]:
            unified_indicators.append(ind)

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









