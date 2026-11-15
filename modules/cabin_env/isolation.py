"""Isolation, sleep, neurobehavioral vigilance, mood/workload, and circadian lighting diagnostics (ISO-01..04)."""

from __future__ import annotations

from typing import Any, Optional

from modules.cabin_env.card_helpers import (
    _check_staleness,
    _clean_time_series,
    _evaluate_personal_baseline_l2,
    _make_card_assessment,
    _make_indicator,
    _max_status,
    _ols_trend_layer3,
)
from modules.cabin_env.measurement_rules import TREND_HORIZON_HOURS


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


