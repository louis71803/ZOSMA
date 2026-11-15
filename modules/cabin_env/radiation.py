"""Radiation diagnostics & countermeasure prescriptions (RAD-01, RAD-02, RAD-03)."""

from __future__ import annotations

from typing import Any

from modules.cabin_env.card_helpers import (
    _check_staleness,
    _clean_time_series,
    _make_card_assessment,
    _make_indicator,
    _max_status,
    _ols_trend_layer3,
    is_in_saa,
)
from modules.cabin_env.measurement_rules import TREND_HORIZON_HOURS


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


