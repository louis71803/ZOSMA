"""Acoustics & audiometry diagnostics and countermeasure prescriptions (ACO-01, ACO-02, ACO-03)."""

from __future__ import annotations

from typing import Any

from modules.cabin_env.card_helpers import (
    _check_staleness,
    _evaluate_personal_baseline_l2,
    _make_card_assessment,
    _make_indicator,
    _max_status,
    _ols_trend_layer3,
)
from modules.cabin_env.measurement_rules import (
    AUDIO_FREQS_HZ,
    NC_40_LIMITS_DB,
    NC_50_LIMITS_DB,
    TREND_HORIZON_HOURS,
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


