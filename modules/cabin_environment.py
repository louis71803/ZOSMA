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


from modules.cabin_env.acoustics import (
    _eval_aco01,
    _eval_aco02,
    _eval_aco03,
)
from modules.cabin_env.radiation import (
    _eval_rad01,
    _eval_rad02,
    _eval_rad03,
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









