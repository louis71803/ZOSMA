"""Cabin atmosphere, potable water, microbial, and particulate diagnostics (ATM-01..07)."""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from modules.cabin_env.card_helpers import (
    _check_staleness,
    _clean_time_series,
    _make_card_assessment,
    _make_indicator,
    _max_status,
    _ols_trend_layer3,
    _parse_water_val,
)
from modules.cabin_env.measurement_rules import TREND_HORIZON_HOURS


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


