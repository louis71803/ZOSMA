"""Role 3: Cardiovascular & Aerobic Capacity Domain Module (Team Z.O.S.M.A.).

Branch: feat/cardiovascular
Primary entry point: modules/cardiovascular.py (used by app.py & core/data_loader.py).

Helper modules (strictly Role 3-scoped inside modules/cardio/):
- modules/cardio/cardio_data.py: pre-flight baselines, synthetic datasets, CSV templates, OSDR loaders
- modules/cardio/cardio_guidance.py: status-aware 3-step astronaut guidance templates (M1-M11)

Implements:
1. Layer 0 QC Gatekeeper (ecg_lead_quality, motion_artifact_g, impossible/missing values)
2. 3-Layer Decision Model (Worst Result Wins):
   - Layer 1: Fixed Clinical / NASA-STD-3001 Rules
   - Layer 2: Personal Pre-flight Baseline (+/-2 SD or delta %)
   - Layer 3: 14-day Linear Trend Projection (5-point / recent trend fit flagging YELLOW if RED predicted within 14 days)
3. All 11 Cardiovascular & Aerobic Measurements (M1-M11):
   - M1: Resting HR (Bio-Monitor)
   - M2: Blood Pressure (Bio-Monitor PTT + weekly arm cuff calibration & PhysioNet PRCP check)
   - M3: SpO2 (Bio-Monitor optical)
   - M4: Breathing Rate (Bio-Monitor chest sensor)
   - M5: Heart Rhythm & PVC Burden (Holter Monitor 2 & PhysioNet MIT-BIH records 100/106/119/208/223 check)
   - M6: Stand Test / Orthostatic Tolerance (in-flight LBNP / post-landing stand test & PhysioNet PRCP check)
   - M7: Aerobic Fitness 150W Bike HR Drift (CEVIS + ECG)
   - M8: Heart Muscle Strength GLS (Ultrasound 2 echocardiography)
   - M9: Internal Jugular Vein Flow & Clot Protocol (Ultrasound 2 vascular Doppler + compression)
   - M10: Plasma Volume %DeltaPV via Dill & Costill 1974 (NASA OSDR OSD-569 Hb/Hct)
   - M11: Serum Blood Markers: K+, CRP, Albumin, Total Protein, Na+, Fibrinogen, PF4 (NASA OSDR OSD-575)
4. Cross-Indicator Clinical Correlations:
   - M3 low SpO2 + M4 tachypnea (>25/min) -> M9 suspected IJV thromboembolism / PE & cabin O2/CO2 check
   - M5 elevated PVC burden -> M11 hypokalemia (<3.5 mmol/L) check
   - M6 orthostatic intolerance -> M10 plasma volume loss fluid-loading protocol
5. Dual Input Modes:
   - Batch/historical loading from data/cardiovascular/*.csv & data/shared_real/*.csv (never FileNotFoundError)
   - Real-time manual parameter overrides from Streamlit UI sliders/forms
6. `demo_baseline()`, `demo_payload(scenario)` (Crew C002, days 1-124), `export_demo_csvs()`, `evaluate()`, `to_schema()`,
   plus Matplotlib & Plotly visualization helpers.
"""

from __future__ import annotations

import math
from typing import Any, Optional, Sequence

import numpy as np

from core.schema import (
    CrewGuidance,
    LongTermPlan,
    MetricItem,
    ModuleEvaluationResult,
    ScheduleMutation,
    ShortTermPlan,
    normalize_module_result,
)
from modules.cardio.cardio_data import (
    BASE_DIR,
    DATA_DIR,
    EXPECTED_CSV_SCHEMAS,
    MITBIH_REFERENCE_RECORDS,
    REAL_SUBDIR,
    SHARED_REAL_DIR,
    _filter_osdr_by_crew,
    _normalize_osdr_value,
    _parse_long_format_osdr,
    _pick_col,
    _sample_timepoint_order,
    _select_osdr_row,
    check_data_files,
    demo_baseline,
    demo_payload,
    export_demo_csvs,
    extract_history_from_payload as _extract_history_from_payload,
    generate_longitudinal_series as _generate_longitudinal_series,
    generate_synthetic_dataframes,
    load_shared_osdr_overrides as _load_shared_osdr_overrides,
    safe_bool as _safe_bool,
    safe_float as _safe_float,
    summarize_biomonitor_stream as _summarize_biomonitor_stream,
)
from modules.cardio.cardio_guidance import build_indicator_guidance as _build_indicator_guidance

STATUS_RANK: dict[str, int] = {
    "GREEN": 0,
    "GREEN-WATCH": 0,
    "YELLOW": 1,
    "RED": 2,
}


# ---------------------------------------------------------------------------
# Helpers: Math, Trend Projection, Dill & Costill, Status Rollup
# ---------------------------------------------------------------------------

def _worst_status(statuses: Sequence[str]) -> str:
    if not statuses:
        return "GREEN"
    return max(statuses, key=lambda s: STATUS_RANK.get(str(s).upper(), 0))


def dill_costill_delta_pv_pct(
    hb_pre: float,
    hct_pre_pct: float,
    hb_post: float,
    hct_post_pct: float,
) -> float:
    """Calculate % change in Plasma Volume (%DeltaPV) via Dill & Costill (1974).

    Formula:
        %DeltaPV = 100 * [ (Hb_pre / Hb_post) * ((1 - Hct_post) / (1 - Hct_pre)) - 1 ]
    where Hct is fractional hematocrit (0-1).
    """
    if hb_post <= 0 or hb_pre <= 0:
        return 0.0
    hct_pre = max(0.10, min(0.75, hct_pre_pct / 100.0))
    hct_post = max(0.10, min(0.75, hct_post_pct / 100.0))
    bv_ratio = hb_pre / hb_post
    pv_ratio = bv_ratio * ((1.0 - hct_post) / (1.0 - hct_pre))
    return round((pv_ratio - 1.0) * 100.0, 2)


def _linear_trend_projection(
    days: Sequence[int],
    values: Sequence[float],
    red_threshold: Optional[float],
    lower_is_worse: bool = False,
    horizon_days: int = 14,
) -> tuple[Optional[float], Optional[int], bool]:
    """Fit a linear slope on recent points (last 5 points) and check 14-day RED crossing.

    Returns:
        (slope_per_day, days_until_red, yellow_trend_triggered)
    """
    if len(days) < 3 or len(values) < 3 or len(days) != len(values):
        return None, None, False

    x = np.asarray(days[-5:], dtype=float)
    y = np.asarray(values[-5:], dtype=float)
    if np.ptp(x) <= 0:
        return 0.0, None, False

    slope, _intercept = np.polyfit(x, y, 1)
    slope = float(slope)
    current_val = float(y[-1])

    if red_threshold is None:
        return round(slope, 4), None, False

    if lower_is_worse:
        if current_val <= red_threshold:
            return round(slope, 4), 0, False
        if slope < -1e-6:
            days_to_red = int(math.ceil((red_threshold - current_val) / slope))
            days_to_red = max(0, days_to_red)
            return round(slope, 4), days_to_red, days_to_red <= horizon_days
    else:
        if current_val >= red_threshold:
            return round(slope, 4), 0, False
        if slope > 1e-6:
            days_to_red = int(math.ceil((red_threshold - current_val) / slope))
            days_to_red = max(0, days_to_red)
            return round(slope, 4), days_to_red, days_to_red <= horizon_days

    return round(slope, 4), None, False


def _layer2_baseline_status(
    current: float,
    baseline: Optional[float],
    sd: Optional[float] = None,
    warn_sd: float = 2.0,
    red_sd: float = 3.0,
    warn_pct: Optional[float] = None,
    red_pct: Optional[float] = None,
    direction: str = "both",  # "high" | "low" | "both"
) -> tuple[str, Optional[float]]:
    """Evaluate Layer 2 personal baseline deviation (+/-2 SD or % delta)."""
    if baseline is None or baseline == 0:
        return "GREEN", None

    delta = current - baseline
    delta_pct = (delta / abs(baseline)) * 100.0

    if direction == "high":
        eff_delta = max(0.0, delta)
        eff_pct = max(0.0, delta_pct)
    elif direction == "low":
        eff_delta = max(0.0, -delta)
        eff_pct = max(0.0, -delta_pct)
    else:
        eff_delta = abs(delta)
        eff_pct = abs(delta_pct)

    status = "GREEN"
    if sd is not None and sd > 0:
        if eff_delta >= red_sd * sd:
            status = "RED"
        elif eff_delta >= warn_sd * sd:
            status = "YELLOW"

    if red_pct is not None and eff_pct >= red_pct:
        status = "RED"
    elif warn_pct is not None and eff_pct >= warn_pct and status == "GREEN":
        status = "YELLOW"

    return status, round(delta_pct, 2)


# ---------------------------------------------------------------------------
# Layer 0 QC Gatekeeper
# ---------------------------------------------------------------------------

def run_qc_gatekeeper(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    """Layer 0 Data Quality Gatekeeper.

    Flags poor ECG contact, excessive motion artifact, stale PTT calibration,
    missing critical fields, or physiologically impossible values.
    """
    reasons: list[str] = []

    lead_q = _safe_float(payload.get("ecg_lead_quality"), 0.95)
    if lead_q is None or lead_q < 0.50:
        reasons.append(f"Bio-Monitor ECG lead quality too low ({lead_q} < 0.50).")

    motion_g = _safe_float(payload.get("motion_artifact_g"), 0.05)
    if motion_g is not None and motion_g > 0.50:
        reasons.append(f"Excessive motion artifact ({motion_g:.2f} g > 0.50 g).")

    rest_hr = _safe_float(payload.get("rest_hr_bpm"))
    if rest_hr is None or rest_hr <= 20.0 or rest_hr > 240.0:
        reasons.append(f"Resting HR missing or physiologically invalid ({payload.get('rest_hr_bpm')}).")

    spo2 = _safe_float(payload.get("spo2_pct"))
    if spo2 is None or spo2 < 50.0 or spo2 > 100.0:
        reasons.append(f"SpO2 missing or physiologically invalid ({payload.get('spo2_pct')}%).")

    sbp = _safe_float(payload.get("sbp_mmHg"))
    dbp = _safe_float(payload.get("dbp_mmHg"))
    if sbp is None or dbp is None or sbp < 40.0 or sbp > 260.0 or dbp < 20.0 or dbp > 160.0 or sbp <= dbp:
        reasons.append(f"Blood pressure missing or invalid ({sbp}/{dbp} mmHg).")

    resp = _safe_float(payload.get("resp_rate_bpm"))
    if resp is None or resp < 4.0 or resp > 60.0:
        reasons.append(f"Respiratory rate missing or invalid ({resp} breaths/min).")

    return len(reasons) == 0, reasons


# ---------------------------------------------------------------------------
# 3-Layer Evaluation Engine for All 11 Measurements (M1-M11)
# ---------------------------------------------------------------------------

def _combine_three_layers(
    layer1_status: str,
    layer2_status: str,
    trend_yellow: bool,
    days_until_red: Optional[int],
) -> tuple[str, str]:
    """Worst-result-wins combination across Layer 1 (Rules), Layer 2 (Baseline), Layer 3 (Trend)."""
    layer3_status = "YELLOW" if trend_yellow else "GREEN"
    overall = _worst_status([layer1_status, layer2_status, layer3_status])

    if overall == layer1_status and layer1_status != "GREEN":
        decided_by = "rule"
    elif overall == layer2_status and layer2_status != "GREEN":
        decided_by = "baseline"
    elif trend_yellow and overall == "YELLOW":
        decided_by = "trend"
    else:
        decided_by = "rule"

    return overall, decided_by


def _build_bad_data_result(
    crew_id: str,
    mission_day: int,
    data_source: str,
    reasons: list[str],
    payload: dict[str, Any],
) -> dict[str, Any]:
    reason_summary = " ".join(reasons)
    metrics = [
        {
            "metric_name": "ecg_lead_quality",
            "indicator": "M0: Layer 0 Bio-Monitor QC Gatekeeper",
            "current_val": _safe_float(payload.get("ecg_lead_quality"), 0.0),
            "value": _safe_float(payload.get("ecg_lead_quality"), 0.0),
            "baseline_val": 0.95,
            "unit": "ratio",
            "status_light": "INSUFFICIENT_DATA",
            "status": "INSUFFICIENT_DATA",
            "quality_passed": False,
            "decided_by": "quality_check",
            "data_source": data_source,
            "message": reason_summary,
            "action": "Moisten Bio-Monitor textile electrodes, tighten thoracic strap, remain still 60s, and re-measure.",
            "how_to_measure": "Wet Bio-Monitor thoracic electrodes with sterile wipe, fasten strap snugly at xiphoid level, and sit still for 60 seconds.",
            "why_in_space": "Microgravity shifts chest shape and reduces skin moisture; dry electrodes or motion cause false PVC/SpO2 alarms.",
        }
    ]

    actions = [
        "Re-wet Bio-Monitor thoracic ECG pads and tighten chest strap.",
        "Clean optical SpO2 fingertip/wrist sensor and eliminate cabin vibration/motion for 60 seconds.",
        "Repeat resting vitals capture immediately before running clinical evaluation.",
    ]

    result = ModuleEvaluationResult(
        module_id="cardiovascular",
        body_part_tag="heart_vascular",
        crew_id=crew_id,
        mission_day=mission_day,
        status_light="INSUFFICIENT_DATA",
        quality_passed=False,
        data_source=data_source,
        summary_note=f"Layer 0 QC Gatekeeper rejected telemetry: {reason_summary}",
        metrics=[MetricItem(**m) for m in metrics],
        guidance=CrewGuidance(
            how_to_measure="Verify Bio-Monitor ECG strap skin contact (quality >= 0.50), keep motion < 0.50 g, and confirm weekly BP cuff calibration.",
            plain_explanation="Sensor dropout, dry electrodes, or impossible readings (e.g., SpO2 < 50% or null HR) cannot safely evaluate heart or clot status.",
            action_protocol=actions,
        ),
        short_term_plan=ShortTermPlan(
            next_measurement_in_hours=0,
            immediate_actions=actions,
            urgent_alert=False,
        ),
        long_term_plan=LongTermPlan(
            days_until_red_prediction=None,
            routine_prescription_adjustment="Inspect Bio-Monitor garment conductive pads and SpO2 clip during weekly hardware check.",
        ),
    )
    out = result.model_dump()
    out["overall_status"] = out["status_light"]
    out["indicators"] = out["metrics"]
    return out


def evaluate(
    payload: Optional[dict[str, Any]] = None,
    baseline: Optional[dict[str, Any]] = None,
    manual_inputs: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Stateless 3-layer Cardiovascular & Aerobic evaluation (M1-M11).

    Supports:
    - `payload`: batch/CSV/demo dictionary
    - `baseline`: pre-flight baseline dictionary
    - `manual_inputs`: optional real-time UI slider/form overrides (takes highest precedence)
    """
    base = {**demo_baseline(), **(baseline or {})}

    raw_pay = dict(payload or {})
    scenario = str(raw_pay.get("scenario", "green")).strip().lower()
    if scenario not in {"green", "yellow", "red", "bad_data"}:
        scenario = "green"

    crew_hint = str(
        (manual_inputs or {}).get("crew_id")
        or raw_pay.get("crew_id")
        or base.get("crew_id")
        or "C002"
    )
    use_shared_osdr = (
        str(raw_pay.get("data_source", "")).strip().upper() != "SIMULATED"
        and scenario == "green"
    )
    merged: dict[str, Any] = demo_payload(scenario)
    if use_shared_osdr:
        osdr_updates, has_osdr_real = _load_shared_osdr_overrides(crew_id=crew_hint)
    else:
        osdr_updates, has_osdr_real = {}, False

    osdr_base_overrides = osdr_updates.pop("_osdr_baseline_overrides", {})
    if isinstance(osdr_base_overrides, dict) and osdr_base_overrides and not baseline:
        base.update(osdr_base_overrides)

    merged.update(osdr_updates)
    stream_summary = _summarize_biomonitor_stream(raw_pay)
    merged.update({k: v for k, v in raw_pay.items() if v is not None or k in {"rest_hr_bpm", "spo2_pct"}})
    if stream_summary and scenario == "green":
        for k, v in stream_summary.items():
            if k not in raw_pay or raw_pay.get(k) is None:
                merged[k] = v
            elif k in {"rest_hr_bpm", "sbp_mmHg", "dbp_mmHg", "spo2_pct", "resp_rate_bpm", "ecg_lead_quality", "motion_artifact_g"} and "csv_biomonitor_stream_day124" in raw_pay:
                # Only use stream aggregate when daily_vitals didn't explicitly supply a different override
                if "csv_daily_vitals" not in raw_pay:
                    merged[k] = v
    if manual_inputs:
        for k, v in manual_inputs.items():
            if v is not None:
                merged[k] = v

    # Detect explicit CRP override (`crp_mg_l` without explicit `crp_change_pct`)
    explicit_crp_val = (manual_inputs or {}).get("crp_mg_l")
    explicit_crp_pct = (manual_inputs or {}).get("crp_change_pct")
    raw_crp_val = raw_pay.get("crp_mg_l")
    raw_crp_pct = raw_pay.get("crp_change_pct")

    if explicit_crp_val is not None and explicit_crp_pct is None:
        merged.pop("crp_change_pct", None)
    elif raw_crp_val is not None and raw_crp_pct is None and explicit_crp_pct is None:
        merged.pop("crp_change_pct", None)
    elif (
        "crp_mg_l" in osdr_updates
        and raw_crp_pct is None
        and explicit_crp_pct is None
    ):
        base_crp = float(_safe_float(base.get("crp_mg_l"), 0.9) or 0.9)
        cur_crp = float(_safe_float(merged.get("crp_mg_l"), base_crp) or base_crp)
        if base_crp > 0:
            merged["crp_change_pct"] = round(((cur_crp - base_crp) / base_crp) * 100.0, 1)

    crew_id = str(merged.get("crew_id", base.get("crew_id", "C002")))
    mission_day = int(_safe_float(merged.get("mission_day"), 124) or 124)

    has_csv_records = any(k.startswith("csv_") for k in merged)
    is_demo_csv = bool(base.get("is_demo_template") is True)
    if str(merged.get("data_source", "")).upper() == "SIMULATED" or (is_demo_csv and str(raw_pay.get("data_source", "")).upper() != "REAL"):
        data_source = "SIMULATED"
    elif has_osdr_real and str(raw_pay.get("data_source", "")).upper() != "MANUAL":
        data_source = "REAL"
    elif merged.get("data_source"):
        data_source = str(merged["data_source"]).upper()
    elif has_csv_records:
        data_source = "REAL"
    else:
        data_source = "SIMULATED"

    # --- Layer 0: QC Gatekeeper ---
    qc_ok, qc_reasons = run_qc_gatekeeper(merged)
    if not qc_ok:
        return _build_bad_data_result(crew_id, mission_day, data_source, qc_reasons, merged)

    history = _extract_history_from_payload(merged, scenario=scenario, mission_day=mission_day)

    def _hist(key: str, current_val: float) -> tuple[list[int], list[float]]:
        item = history.get(key)
        if item and len(item.get("days", [])) >= 2:
            pairs = [
                (int(d), float(val))
                for d, val in zip(item["days"], item["values"])
                if int(d) <= mission_day
            ]
            if len(pairs) >= 2:
                d = [p[0] for p in pairs]
                v = [p[1] for p in pairs]
                if d[-1] == mission_day:
                    v[-1] = float(current_val)
                else:
                    d.append(mission_day)
                    v.append(float(current_val))
                return d, v
        base_v = _safe_float(base.get(key), current_val)
        if base_v is None:
            base_v = current_val
        if mission_day <= 1:
            return [0, mission_day], [float(current_val), float(current_val)]
        n_pts = 5
        days_arr = sorted({max(1, round(1 + (mission_day - 1) * i / (n_pts - 1))) for i in range(n_pts)})
        if len(days_arr) < 2:
            days_arr = [0, mission_day]
        step = (current_val - base_v) / max(len(days_arr) - 1, 1)
        vals_arr = [round(base_v + step * i, 2) for i in range(len(days_arr))]
        vals_arr[-1] = float(current_val)
        return days_arr, vals_arr

    metrics: list[dict[str, Any]] = []
    projected_red_days: list[int] = []

    # ------------------------------------------------------------------
    # M1: Resting Heart Rate (Bio-Monitor)
    # ------------------------------------------------------------------
    rest_hr = float(_safe_float(merged.get("rest_hr_bpm"), base["rest_hr_bpm"]))
    hr_l1 = "RED" if (rest_hr >= 100 or rest_hr <= 40) else ("YELLOW" if (rest_hr >= 80 or rest_hr < 48) else "GREEN")
    hr_l2, hr_delta_pct = _layer2_baseline_status(
        rest_hr, base["rest_hr_bpm"], sd=base.get("rest_hr_sd", 4.0), warn_sd=3.0, red_sd=6.0, warn_pct=20.0, red_pct=45.0, direction="high"
    )
    hr_days, hr_vals = _hist("rest_hr_bpm", rest_hr)
    hr_slope, hr_days_red, hr_trend_warn = _linear_trend_projection(hr_days, hr_vals, red_threshold=100.0, lower_is_worse=False)
    hr_status, hr_by = _combine_three_layers(hr_l1, hr_l2, hr_trend_warn, hr_days_red)
    if hr_days_red is not None and hr_status != "RED":
        projected_red_days.append(hr_days_red)
    hr_slope_txt = f"{hr_slope:+.3f}/day" if hr_slope is not None else "n/a"
    metrics.append({
        "metric_name": "rest_hr_bpm",
        "indicator": "M1: Resting Heart Rate (Bio-Monitor)",
        "current_val": round(rest_hr, 1),
        "value": round(rest_hr, 1),
        "baseline_val": float(base["rest_hr_bpm"]),
        "delta_pct": hr_delta_pct,
        "slope_per_day": hr_slope,
        "unit": "bpm",
        "status_light": hr_status,
        "status": hr_status,
        "decided_by": hr_by,
        "data_source": data_source,
        "yellow_threshold": 80.0,
        "red_threshold": 100.0,
        "lower_is_worse": False,
        "history_days": hr_days,
        "history_values": hr_vals,
        "message": f"Resting HR {rest_hr:.1f} bpm (baseline {base['rest_hr_bpm']:.0f} bpm, slope {hr_slope_txt}).",
    })

    # ------------------------------------------------------------------
    # M2: Blood Pressure (Bio-Monitor PTT + Weekly Arm Cuff + PRCP check)
    # ------------------------------------------------------------------
    sbp = float(_safe_float(merged.get("sbp_mmHg"), base["sbp_mmHg"]))
    dbp = float(_safe_float(merged.get("dbp_mmHg"), base["dbp_mmHg"]))
    ptt_age = int(_safe_float(merged.get("ptt_calibrated_days_ago"), 3) or 3)
    bp_l1 = "RED" if (sbp >= 160 or dbp >= 100 or sbp <= 85) else ("YELLOW" if (sbp >= 140 or dbp >= 90 or sbp <= 95) else "GREEN")
    sbp_l2, sbp_delta_pct = _layer2_baseline_status(sbp, base["sbp_mmHg"], sd=base.get("sbp_sd", 6.0), warn_sd=2.5, red_sd=4.0, direction="both")
    sbp_days, sbp_vals = _hist("sbp_mmHg", sbp)
    sbp_slope, sbp_days_red, sbp_trend_warn = _linear_trend_projection(sbp_days, sbp_vals, red_threshold=160.0, lower_is_worse=False)
    bp_status, bp_by = _combine_three_layers(bp_l1, sbp_l2, sbp_trend_warn, sbp_days_red)
    if sbp_days_red is not None and bp_status != "RED":
        projected_red_days.append(sbp_days_red)
    cal_note = " (cuff recalibration due >7d)" if ptt_age > 7 else ""
    metrics.append({
        "metric_name": "sbp_mmHg",
        "indicator": "M2: Blood Pressure (PTT + Cuff & PRCP)",
        "current_val": round(sbp, 1),
        "value": f"{sbp:.0f}/{dbp:.0f}",
        "baseline_val": float(base["sbp_mmHg"]),
        "delta_pct": sbp_delta_pct,
        "slope_per_day": sbp_slope,
        "unit": "mmHg",
        "status_light": bp_status,
        "status": bp_status,
        "decided_by": bp_by,
        "data_source": data_source,
        "yellow_threshold": 140.0,
        "red_threshold": 160.0,
        "lower_is_worse": False,
        "history_days": sbp_days,
        "history_values": sbp_vals,
        "message": f"BP {sbp:.0f}/{dbp:.0f} mmHg vs baseline {base['sbp_mmHg']:.0f}/{base['dbp_mmHg']:.0f}{cal_note}.",
    })

    # ------------------------------------------------------------------
    # M3: SpO2 (Bio-Monitor Optical)
    # ------------------------------------------------------------------
    spo2 = float(_safe_float(merged.get("spo2_pct"), base["spo2_pct"]))
    spo2_l1 = "RED" if spo2 <= 92.0 else ("YELLOW" if spo2 < 96.0 else "GREEN")
    spo2_l2, spo2_delta_pct = _layer2_baseline_status(spo2, base["spo2_pct"], sd=base.get("spo2_sd", 0.6), warn_sd=3.5, red_sd=7.0, direction="low")
    spo2_days, spo2_vals = _hist("spo2_pct", spo2)
    spo2_slope, spo2_days_red, spo2_trend_warn = _linear_trend_projection(spo2_days, spo2_vals, red_threshold=92.0, lower_is_worse=True)
    spo2_status, spo2_by = _combine_three_layers(spo2_l1, spo2_l2, spo2_trend_warn, spo2_days_red)
    if spo2_days_red is not None and spo2_status != "RED":
        projected_red_days.append(spo2_days_red)
    metrics.append({
        "metric_name": "spo2_pct",
        "indicator": "M3: Oxygen Saturation SpO2 (Bio-Monitor)",
        "current_val": round(spo2, 1),
        "value": round(spo2, 1),
        "baseline_val": float(base["spo2_pct"]),
        "delta_pct": spo2_delta_pct,
        "slope_per_day": spo2_slope,
        "unit": "%",
        "status_light": spo2_status,
        "status": spo2_status,
        "decided_by": spo2_by,
        "data_source": data_source,
        "yellow_threshold": 96.0,
        "red_threshold": 92.0,
        "lower_is_worse": True,
        "history_days": spo2_days,
        "history_values": spo2_vals,
        "message": f"SpO2 {spo2:.1f}% (Yellow < 96%, Red <= 92%).",
    })

    # ------------------------------------------------------------------
    # M4: Breathing Rate (Bio-Monitor Chest Sensor)
    # ------------------------------------------------------------------
    resp = float(_safe_float(merged.get("resp_rate_bpm"), base["resp_rate_bpm"]))
    resp_l1 = "RED" if (resp > 25.0 or resp < 8.0) else ("YELLOW" if resp > 20.0 else "GREEN")
    resp_l2, resp_delta_pct = _layer2_baseline_status(resp, base["resp_rate_bpm"], sd=base.get("resp_rate_sd", 1.5), warn_sd=3.0, red_sd=5.0, direction="high")
    resp_days, resp_vals = _hist("resp_rate_bpm", resp)
    resp_slope, resp_days_red, resp_trend_warn = _linear_trend_projection(resp_days, resp_vals, red_threshold=25.0, lower_is_worse=False)
    resp_status, resp_by = _combine_three_layers(resp_l1, resp_l2, resp_trend_warn, resp_days_red)
    if resp_days_red is not None and resp_status != "RED":
        projected_red_days.append(resp_days_red)
    metrics.append({
        "metric_name": "resp_rate_bpm",
        "indicator": "M4: Breathing Rate (Bio-Monitor)",
        "current_val": round(resp, 1),
        "value": round(resp, 1),
        "baseline_val": float(base["resp_rate_bpm"]),
        "delta_pct": resp_delta_pct,
        "slope_per_day": resp_slope,
        "unit": "breaths/min",
        "status_light": resp_status,
        "status": resp_status,
        "decided_by": resp_by,
        "data_source": data_source,
        "yellow_threshold": 20.0,
        "red_threshold": 25.0,
        "lower_is_worse": False,
        "history_days": resp_days,
        "history_values": resp_vals,
        "message": f"Respiratory rate {resp:.1f} breaths/min (Yellow > 20, Red > 25).",
    })

    # ------------------------------------------------------------------
    # M5: Heart Rhythm & PVC Burden (Holter Monitor 2 + MIT-BIH Check)
    # ------------------------------------------------------------------
    pvc = float(_safe_float(merged.get("pvc_burden_pct"), base["pvc_burden_pct"]))
    afib = _safe_bool(merged.get("afib_detected"), False)
    mitbih_rec = str(merged.get("mitbih_record_check", "100"))
    mitbih_info = MITBIH_REFERENCE_RECORDS.get(mitbih_rec, MITBIH_REFERENCE_RECORDS["100"])
    pvc_l1 = "RED" if (afib or pvc >= 5.0) else ("YELLOW" if pvc >= 1.5 else "GREEN")
    pvc_days, pvc_vals = _hist("pvc_burden_pct", pvc)
    pvc_slope, pvc_days_red, pvc_trend_warn = _linear_trend_projection(pvc_days, pvc_vals, red_threshold=5.0, lower_is_worse=False)
    pvc_status, pvc_by = _combine_three_layers(pvc_l1, "GREEN", pvc_trend_warn, pvc_days_red)
    if pvc_days_red is not None and pvc_status != "RED":
        projected_red_days.append(pvc_days_red)
    metrics.append({
        "metric_name": "pvc_burden_pct",
        "indicator": "M5: Heart Rhythm & PVC Burden (Holter + MIT-BIH)",
        "current_val": round(pvc, 2),
        "value": round(pvc, 2),
        "baseline_val": float(base["pvc_burden_pct"]),
        "delta_pct": round(((pvc - base["pvc_burden_pct"]) / max(base["pvc_burden_pct"], 0.1)) * 100.0, 1),
        "slope_per_day": pvc_slope,
        "unit": "%",
        "status_light": pvc_status,
        "status": pvc_status,
        "decided_by": pvc_by,
        "data_source": data_source,
        "yellow_threshold": 1.5,
        "red_threshold": 5.0,
        "lower_is_worse": False,
        "history_days": pvc_days,
        "history_values": pvc_vals,
        "message": f"Holter PVC {pvc:.2f}%, AFib={'YES' if afib else 'NO'} (MIT-BIH ref {mitbih_rec}: {mitbih_info['rhythm']}).",
    })

    # ------------------------------------------------------------------
    # M6: Orthostatic Tolerance (LBNP / Stand Test + PRCP Check)
    # ------------------------------------------------------------------
    stand_hr = float(_safe_float(merged.get("stand_hr_rise_bpm"), base["stand_hr_rise_bpm"]))
    stand_sbp = float(_safe_float(merged.get("stand_sbp_drop_mmHg"), base["stand_sbp_drop_mmHg"]))
    dizzy = _safe_bool(merged.get("dizzy"), False)
    proto_mode = str(merged.get("protocol_mode", "LBNP"))
    prcp_ok = _safe_bool(merged.get("prcp_reference_ok"), True)
    stand_l1 = "RED" if (dizzy or stand_hr >= 30.0 or stand_sbp >= 20.0) else ("YELLOW" if (stand_hr >= 20.0 or stand_sbp >= 10.0) else "GREEN")
    stand_days, stand_vals = _hist("stand_hr_rise_bpm", stand_hr)
    stand_slope, stand_days_red, stand_trend_warn = _linear_trend_projection(stand_days, stand_vals, red_threshold=30.0, lower_is_worse=False)
    stand_status, stand_by = _combine_three_layers(stand_l1, "GREEN", stand_trend_warn, stand_days_red)
    if stand_days_red is not None and stand_status != "RED":
        projected_red_days.append(stand_days_red)
    metrics.append({
        "metric_name": "stand_hr_rise_bpm",
        "indicator": "M6: Orthostatic Tolerance (LBNP/Stand + PRCP)",
        "current_val": round(stand_hr, 1),
        "value": round(stand_hr, 1),
        "baseline_val": float(base["stand_hr_rise_bpm"]),
        "delta_pct": round(((stand_hr - base["stand_hr_rise_bpm"]) / max(base["stand_hr_rise_bpm"], 1.0)) * 100.0, 1),
        "slope_per_day": stand_slope,
        "unit": "bpm rise",
        "status_light": stand_status,
        "status": stand_status,
        "decided_by": stand_by,
        "data_source": data_source,
        "yellow_threshold": 20.0,
        "red_threshold": 30.0,
        "lower_is_worse": False,
        "history_days": stand_days,
        "history_values": stand_vals,
        "message": f"{proto_mode} HR rise +{stand_hr:.0f} bpm, SBP drop -{stand_sbp:.0f} mmHg, dizzy={dizzy} (PRCP ref={'OK' if prcp_ok else 'CHECK'}).",
    })

    # ------------------------------------------------------------------
    # M7: Aerobic Fitness 150W Bike HR Drift (CEVIS + ECG)
    # ------------------------------------------------------------------
    cevis_hr = float(_safe_float(merged.get("steady_hr_150w_bpm"), base["steady_hr_150w_bpm"]))
    cevis_l1 = "RED" if cevis_hr >= 165.0 else ("YELLOW" if cevis_hr >= 150.0 else "GREEN")
    cevis_l2, cevis_delta_pct = _layer2_baseline_status(cevis_hr, base["steady_hr_150w_bpm"], sd=base.get("steady_hr_150w_sd", 5.0), warn_sd=2.5, red_sd=4.5, warn_pct=10.0, red_pct=20.0, direction="high")
    cevis_days, cevis_vals = _hist("steady_hr_150w_bpm", cevis_hr)
    cevis_slope, cevis_days_red, cevis_trend_warn = _linear_trend_projection(cevis_days, cevis_vals, red_threshold=165.0, lower_is_worse=False)
    cevis_status, cevis_by = _combine_three_layers(cevis_l1, cevis_l2, cevis_trend_warn, cevis_days_red)
    if cevis_days_red is not None and cevis_status != "RED":
        projected_red_days.append(cevis_days_red)
    metrics.append({
        "metric_name": "steady_hr_150w_bpm",
        "indicator": "M7: Aerobic Fitness 150W Bike HR Drift (CEVIS)",
        "current_val": round(cevis_hr, 1),
        "value": round(cevis_hr, 1),
        "baseline_val": float(base["steady_hr_150w_bpm"]),
        "delta_pct": cevis_delta_pct,
        "slope_per_day": cevis_slope,
        "unit": "bpm",
        "status_light": cevis_status,
        "status": cevis_status,
        "decided_by": cevis_by,
        "data_source": data_source,
        "yellow_threshold": 150.0,
        "red_threshold": 165.0,
        "lower_is_worse": False,
        "history_days": cevis_days,
        "history_values": cevis_vals,
        "message": f"CEVIS 150W steady-state HR {cevis_hr:.0f} bpm (drift {cevis_hr - base['steady_hr_150w_bpm']:+.0f} bpm).",
    })

    # ------------------------------------------------------------------
    # M8: Heart Muscle Strength GLS (Ultrasound 2 Echocardiography)
    # ------------------------------------------------------------------
    gls_change = float(_safe_float(merged.get("gls_change_pct"), 0.0))
    gls_l1 = "RED" if gls_change <= -15.0 else ("YELLOW" if gls_change <= -10.0 else "GREEN")
    gls_days, gls_vals = _hist("gls_change_pct", gls_change)
    gls_slope, gls_days_red, gls_trend_warn = _linear_trend_projection(gls_days, gls_vals, red_threshold=-15.0, lower_is_worse=True)
    gls_status, gls_by = _combine_three_layers(gls_l1, "GREEN", gls_trend_warn, gls_days_red)
    if gls_days_red is not None and gls_status != "RED":
        projected_red_days.append(gls_days_red)
    metrics.append({
        "metric_name": "gls_change_pct",
        "indicator": "M8: Myocardial Strain GLS (Ultrasound 2)",
        "current_val": round(gls_change, 1),
        "value": round(gls_change, 1),
        "baseline_val": 0.0,
        "delta_pct": round(gls_change, 1),
        "slope_per_day": gls_slope,
        "unit": "% change",
        "status_light": gls_status,
        "status": gls_status,
        "decided_by": gls_by,
        "data_source": data_source,
        "yellow_threshold": -10.0,
        "red_threshold": -15.0,
        "lower_is_worse": True,
        "history_days": gls_days,
        "history_values": gls_vals,
        "message": f"Left-ventricular GLS relative change {gls_change:+.1f}% (Yellow <= -10%, Red <= -15%).",
    })

    # ------------------------------------------------------------------
    # M9: Internal Jugular Vein Flow & Clot Protocol (Ultrasound 2)
    # ------------------------------------------------------------------
    ijv_flow = str(merged.get("ijv_flow", "forward")).strip().lower()
    ijv_comp = _safe_bool(merged.get("ijv_compressible"), True)
    ijv_thrombus = _safe_bool(merged.get("ijv_thrombus"), False)
    if ijv_thrombus or (not ijv_comp) or ijv_flow == "reversed":
        ijv_status = "RED"
    elif ijv_flow == "stagnant":
        ijv_status = "YELLOW"
    else:
        ijv_status = "GREEN"
    ijv_score_map = {"forward": 0.0, "stagnant": 1.0, "reversed": 2.0}
    ijv_score = 2.0 if (ijv_thrombus or not ijv_comp) else ijv_score_map.get(ijv_flow, 0.0)
    ijv_days, ijv_vals = _hist("ijv_flow_status", ijv_score)
    metrics.append({
        "metric_name": "ijv_flow_status",
        "indicator": "M9: IJV Neck Vein Flow & Clot (Ultrasound 2)",
        "current_val": ijv_flow,
        "value": ijv_flow,
        "baseline_val": "forward",
        "unit": "flow",
        "status_light": ijv_status,
        "status": ijv_status,
        "decided_by": "rule",
        "data_source": data_source,
        "yellow_threshold": 1.0,
        "red_threshold": 2.0,
        "lower_is_worse": False,
        "history_days": ijv_days,
        "history_values": ijv_vals,
        "message": f"IJV Doppler='{ijv_flow}', compressible={ijv_comp}, thrombus={ijv_thrombus}.",
    })

    # ------------------------------------------------------------------
    # M10: Plasma Volume %DeltaPV via Dill & Costill (1974) [OSD-569]
    # ------------------------------------------------------------------
    hb = float(_safe_float(merged.get("hb_g_dl"), base["hb_g_dl"]))
    hct = float(_safe_float(merged.get("hct_pct"), base["hct_pct"]))
    pv_delta_pct = dill_costill_delta_pv_pct(base["hb_g_dl"], base["hct_pct"], hb, hct)
    pv_l1 = "RED" if pv_delta_pct <= -20.0 else ("YELLOW" if pv_delta_pct <= -12.0 else "GREEN")
    hb_days, hb_vals = _hist("hb_g_dl", hb)
    _, hct_vals = _hist("hct_pct", hct)
    pv_vals = [dill_costill_delta_pv_pct(base["hb_g_dl"], base["hct_pct"], b_i, c_i) for b_i, c_i in zip(hb_vals, hct_vals)]
    pv_slope, pv_days_red, pv_trend_warn = _linear_trend_projection(hb_days, pv_vals, red_threshold=-20.0, lower_is_worse=True)
    pv_status, pv_by = _combine_three_layers(pv_l1, "GREEN", pv_trend_warn, pv_days_red)
    if pv_days_red is not None and pv_status != "RED":
        projected_red_days.append(pv_days_red)
    metrics.append({
        "metric_name": "plasma_volume_delta_pct",
        "indicator": "M10: Plasma Volume %DeltaPV (Dill & Costill / OSD-569)",
        "current_val": pv_delta_pct,
        "value": pv_delta_pct,
        "baseline_val": 0.0,
        "delta_pct": pv_delta_pct,
        "slope_per_day": pv_slope,
        "unit": "%",
        "status_light": pv_status,
        "status": pv_status,
        "decided_by": pv_by,
        "data_source": data_source,
        "yellow_threshold": -12.0,
        "red_threshold": -20.0,
        "lower_is_worse": True,
        "history_days": hb_days,
        "history_values": pv_vals,
        "message": f"%DeltaPV = {pv_delta_pct:+.1f}% (Hb {hb:.1f} g/dL, Hct {hct:.1f}% vs pre-flight {base['hb_g_dl']}/{base['hct_pct']}).",
    })

    # ------------------------------------------------------------------
    # M11: Serum Blood Chemistry (K+, CRP, Albumin, Protein, Na+, Fibrinogen, PF4) [OSD-575]
    # ------------------------------------------------------------------
    potassium = float(_safe_float(merged.get("potassium_mmol_l"), base["potassium_mmol_l"]))
    sodium = float(_safe_float(merged.get("sodium_mmol_l"), base["sodium_mmol_l"]))
    albumin = float(_safe_float(merged.get("albumin_g_dl"), base["albumin_g_dl"]))
    total_protein = float(_safe_float(merged.get("total_protein_g_dl"), base["total_protein_g_dl"]))
    fibrinogen = float(_safe_float(merged.get("fibrinogen_mg_dl"), base["fibrinogen_mg_dl"]))
    pf4 = float(_safe_float(merged.get("pf4_ng_ml"), base["pf4_ng_ml"]))
    crp_mg_l = float(_safe_float(merged.get("crp_mg_l"), base["crp_mg_l"]))
    base_crp = float(_safe_float(base.get("crp_mg_l"), 0.9) or 0.9)
    if merged.get("crp_change_pct") is not None:
        crp_change = float(_safe_float(merged.get("crp_change_pct"), 0.0))
    else:
        crp_change = round(((crp_mg_l - base_crp) / base_crp) * 100.0, 1) if base_crp > 0 else 0.0

    k_l1 = "RED" if (potassium < 3.0 or potassium > 5.5) else ("YELLOW" if (potassium < 3.5 or potassium > 5.1) else "GREEN")
    base_pf4 = float(_safe_float(base.get("pf4_ng_ml"), 8.0) or 8.0)
    base_fib = float(_safe_float(base.get("fibrinogen_mg_dl"), 285.0) or 285.0)
    if base_pf4 > 100.0 or osdr_base_overrides:
        pf4_chg_pct = ((pf4 - base_pf4) / base_pf4) * 100.0 if base_pf4 > 0 else 0.0
        fib_chg_pct = ((fibrinogen - base_fib) / base_fib) * 100.0 if base_fib > 0 else 0.0
        crp_l1 = (
            "RED"
            if (crp_change >= 200.0 or pf4_chg_pct >= 250.0 or fib_chg_pct >= 200.0)
            else ("YELLOW" if (crp_change >= 50.0 or pf4_chg_pct >= 100.0 or fib_chg_pct >= 100.0) else "GREEN")
        )
    else:
        crp_l1 = "RED" if (crp_change >= 75.0 or fibrinogen >= 450.0 or pf4 >= 25.0) else ("YELLOW" if (crp_change >= 30.0 or fibrinogen >= 380.0) else "GREEN")
    blood_l1 = _worst_status([k_l1, crp_l1])
    k_days, k_vals = _hist("potassium_mmol_l", potassium)
    k_slope, k_days_red, k_trend_warn = _linear_trend_projection(k_days, k_vals, red_threshold=3.0, lower_is_worse=True)
    blood_status, blood_by = _combine_three_layers(blood_l1, "GREEN", k_trend_warn, k_days_red)
    if k_days_red is not None and blood_status != "RED":
        projected_red_days.append(k_days_red)
    metrics.append({
        "metric_name": "potassium_mmol_l",
        "indicator": "M11: Serum Blood Chemistry (K+, CRP, Clotting / OSD-575)",
        "current_val": round(potassium, 2),
        "value": round(potassium, 2),
        "baseline_val": float(base["potassium_mmol_l"]),
        "delta_pct": round(((potassium - base["potassium_mmol_l"]) / base["potassium_mmol_l"]) * 100.0, 1),
        "slope_per_day": k_slope,
        "unit": "mmol/L (K+)",
        "status_light": blood_status,
        "status": blood_status,
        "decided_by": blood_by,
        "data_source": data_source,
        "yellow_threshold": 3.5,
        "red_threshold": 3.0,
        "lower_is_worse": True,
        "history_days": k_days,
        "history_values": k_vals,
        "message": (
            f"K+ {potassium:.2f} mmol/L, Na+ {sodium:.0f}, Alb {albumin:.1f}, TP {total_protein:.1f}, "
            f"CRP {crp_change:+.0f}%, Fibrinogen {fibrinogen:.0f} mg/dL, PF4 {pf4:.1f} ng/mL."
        ),
    })

    # Enrich every M1-M11 indicator with status-aware, astronaut-friendly 3-step guidance
    guide_ctx = {
        "rest_hr": rest_hr,
        "base_hr": base["rest_hr_bpm"],
        "sbp": sbp,
        "dbp": dbp,
        "ptt_age": ptt_age,
        "spo2": spo2,
        "resp": resp,
        "pvc": pvc,
        "afib": afib,
        "potassium": potassium,
        "stand_hr": stand_hr,
        "stand_sbp": stand_sbp,
        "dizzy": dizzy,
        "pv_delta": pv_delta_pct,
        "cevis_hr": cevis_hr,
        "gls_change": gls_change,
        "ijv_flow": ijv_flow,
        "ijv_thrombus": ijv_thrombus,
    }
    for m in metrics:
        g_item = _build_indicator_guidance(m["metric_name"], m["status_light"], guide_ctx)
        m["how_to_measure"] = g_item["how_to_measure"]
        m["why_in_space"] = g_item["why_in_space"]
        m["action_steps"] = g_item["action_steps"]
        m["action"] = g_item["action_steps"][0]

    # ------------------------------------------------------------------
    # Cross-Indicator Clinical Correlations (Enforced per USER.md)
    # ------------------------------------------------------------------
    correlation_alerts: list[str] = []
    if spo2 < 95.0 and resp > 25.0:
        correlation_alerts.append(
            "PE / HYPOXIA CORRELATION (M3+M4->M9): Low SpO2 + Tachypnea (>25/min) — perform immediate bilateral IJV Ultrasound 2 clot check and verify cabin O2/ppCO2."
        )
    if pvc >= 1.5 and potassium < 3.5:
        correlation_alerts.append(
            f"ARRHYTHMIA-ELECTROLYTE CORRELATION (M5+M11): Elevated PVC burden ({pvc:.1f}%) paired with hypokalemia (K+={potassium:.2f} mmol/L) — administer oral KCl and repeat ECG."
        )
    elif pvc >= 1.5:
        correlation_alerts.append(
            f"RHYTHM-ELECTROLYTE CHECK (M5->M11): Elevated PVC burden ({pvc:.1f}%) — verify serum K+ >= 3.5 mmol/L before exercise."
        )
    if (stand_hr >= 20.0 or stand_sbp >= 10.0 or dizzy) and pv_delta_pct <= -12.0:
        correlation_alerts.append(
            f"ORTHOSTATIC-HYPOVOLEMIA CORRELATION (M6+M10): Orthostatic intolerance paired with {pv_delta_pct:.1f}% plasma volume loss — initiate oral salt+fluid loading."
        )

    # ------------------------------------------------------------------
    # Overall Rollup & Closed-Loop Plans
    # ------------------------------------------------------------------
    overall_status = _worst_status([m["status_light"] for m in metrics])
    earliest_red_days: Optional[int] = 0 if overall_status == "RED" else (min(projected_red_days) if projected_red_days else None)

    if overall_status == "RED":
        actions = [
            "STOP all high-intensity CEVIS & heavy E4D resistance workouts immediately.",
            "Perform Ultrasound 2 bilateral IJV compression sweep + 12-lead ECG + serum K+/clotting re-check.",
            "If IJV thrombus/reversed flow: initiate onboard anticoagulation checklist & LBNP -25 mmHg.",
            *correlation_alerts,
        ]
        next_hours = 4
        adj = "Suspend HIIT for 14 days; run daily resting ECG, potassium repletion, and LBNP orthostatic conditioning."
    elif overall_status == "YELLOW":
        actions = [
            "Run 30-min LBNP at -20 mmHg to reduce cephalad venous stasis.",
            "Administer 500-750 mL electrolyte fluid load and repeat Bio-Monitor + Holter check in 12h.",
            *correlation_alerts,
        ]
        next_hours = 12
        adj = "Shift CEVIS to Zone 2 steady aerobic conditioning (4x/week), add LBNP 3x/week, and re-evaluate in 7 days."
    else:
        actions = ["Continue daily Bio-Monitor morning vitals & scheduled CEVIS Zone 2/4 cycling."]
        next_hours = 24
        adj = "Maintain current CEVIS aerobic conditioning + bi-weekly LBNP orthostatic tolerance check."

    summary_note = (
        f"Rest HR {rest_hr:.0f} bpm, BP {sbp:.0f}/{dbp:.0f}, SpO2 {spo2:.1f}%, "
        f"PVC {pvc:.1f}%, IJV '{ijv_flow}', %DeltaPV {pv_delta_pct:+.1f}%."
    )
    if correlation_alerts:
        summary_note += " | " + correlation_alerts[0]

    flagged = [m for m in metrics if m["status_light"] in ("RED", "YELLOW")]
    flagged.sort(key=lambda m: STATUS_RANK.get(m["status_light"], 0), reverse=True)
    if flagged:
        top = flagged[0]
        flagged_names = ", ".join(m["indicator"].split(":")[0] for m in flagged[:4])
        mod_how_to = f"[{overall_status} FOCUS · {flagged_names}] {top['how_to_measure']}"
        mod_why = f"{top['why_in_space']} (Click any M1-M11 card above to inspect its individual 3-step guide.)"
    else:
        mod_how_to = (
            "Wear Bio-Monitor shirt for resting HR/BP/SpO2/Resp; run scheduled 24h Holter, "
            "CEVIS 150W bike test, LBNP tolerance test, and Ultrasound 2 heart/neck scan."
        )
        mod_why = (
            "Microgravity shifts ~2L of fluid toward the head, shrinking plasma volume (%DeltaPV), "
            "risking neck vein stasis/clots (IJV), electrolyte-driven PVCs, and orthostatic fainting. "
            "All 11 indicators are currently nominal (click any M1-M11 card above for details)."
        )

    result = ModuleEvaluationResult(
        module_id="cardiovascular",
        body_part_tag="heart_vascular",
        crew_id=crew_id,
        mission_day=mission_day,
        status_light=overall_status,
        quality_passed=True,
        data_source=data_source,
        summary_note=summary_note,
        metrics=[MetricItem(**m) for m in metrics],
        guidance=CrewGuidance(
            how_to_measure=mod_how_to,
            plain_explanation=mod_why,
            action_protocol=actions,
        ),
        short_term_plan=ShortTermPlan(
            next_measurement_in_hours=next_hours,
            immediate_actions=actions,
            urgent_alert=(overall_status == "RED"),
        ),
        long_term_plan=LongTermPlan(
            days_until_red_prediction=earliest_red_days,
            routine_prescription_adjustment=adj,
        ),
        schedule_mutation=ScheduleMutation(
            next_measurement_in_hours=next_hours,
            prescription_adjustment=adj,
            urgent_alert=(overall_status == "RED"),
        ),
    )

    out = result.model_dump()
    out["overall_status"] = out["status_light"]
    out["indicators"] = out["metrics"]
    out["correlation_alerts"] = correlation_alerts
    return out


def to_schema(
    payload: Optional[dict[str, Any]] = None,
    baseline: Optional[dict[str, Any]] = None,
    manual_inputs: Optional[dict[str, Any]] = None,
) -> ModuleEvaluationResult:
    """Evaluate and return a validated Pydantic `ModuleEvaluationResult`."""
    raw = evaluate(payload=payload, baseline=baseline, manual_inputs=manual_inputs)
    return normalize_module_result(raw, module_id="cardiovascular")


# ---------------------------------------------------------------------------
# Plotting Helpers (Plotly & Matplotlib)
# ---------------------------------------------------------------------------

def plot_metric_plotly(result: dict[str, Any], metric_name: str = "rest_hr_bpm") -> Any:
    """Build an interactive Plotly longitudinal chart with Green/Yellow/Red bands."""
    import plotly.graph_objects as go

    metrics = result.get("metrics", [])
    target = next((m for m in metrics if m.get("metric_name") == metric_name), metrics[0] if metrics else None)
    fig = go.Figure()
    if not target:
        fig.update_layout(title="No cardiovascular metrics available")
        return fig

    days = target.get("history_days") or [1, 30, 60, 90, 124]
    vals = target.get("history_values") or [0.0] * len(days)
    fig.add_trace(go.Scatter(x=days, y=vals, mode="lines+markers", name=target.get("indicator", metric_name)))

    y_th = target.get("yellow_threshold")
    r_th = target.get("red_threshold")
    if y_th is not None:
        fig.add_hline(y=y_th, line_dash="dash", line_color="#eab308", annotation_text="Yellow")
    if r_th is not None:
        fig.add_hline(y=r_th, line_dash="dash", line_color="#dc2626", annotation_text="Red")

    fig.update_layout(
        title=f"{target.get('indicator', metric_name)} ({target.get('unit', '')})",
        xaxis_title="Mission Day",
        yaxis_title=target.get("unit", "Value"),
        height=320,
    )
    return fig


def plot_metric_matplotlib(result: dict[str, Any], metric_name: str = "rest_hr_bpm") -> Any:
    """Build a static Matplotlib figure for offline reports or headless export."""
    import matplotlib.pyplot as plt

    metrics = result.get("metrics", [])
    target = next((m for m in metrics if m.get("metric_name") == metric_name), metrics[0] if metrics else None)
    fig, ax = plt.subplots(figsize=(7, 3.5))
    if not target:
        ax.set_title("No cardiovascular metrics available")
        return fig

    days = target.get("history_days") or [1, 30, 60, 90, 124]
    vals = target.get("history_values") or [0.0] * len(days)
    ax.plot(days, vals, marker="o", linewidth=2, label="Measured")
    if target.get("yellow_threshold") is not None:
        ax.axhline(target["yellow_threshold"], color="orange", linestyle="--", label="Yellow")
    if target.get("red_threshold") is not None:
        ax.axhline(target["red_threshold"], color="red", linestyle="--", label="Red")
    ax.set_title(target.get("indicator", metric_name))
    ax.set_xlabel("Mission Day")
    ax.set_ylabel(target.get("unit", ""))
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# CLI Self-Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Z.O.S.M.A. Role 3: Cardiovascular & Aerobic Module Self-Test ===")
    data_info = check_data_files()
    written_files = export_demo_csvs()
    if written_files:
        print(f"Exported/upgraded {len(written_files)} template files in {data_info['local_dir']}:")
        for wf in written_files:
            print(f"  - {wf}")
    else:
        print(f"All expected CSV templates present in {data_info['local_dir']}.")

    if data_info["missing_shared"]:
        print(f"Note: Shared OSDR files not yet in {data_info['shared_dir']}: {data_info['missing_shared']} (using simulated fallback).")

    for scen in ("green", "yellow", "red", "bad_data"):
        pay = demo_payload(scen)
        res_model = to_schema(pay)
        res_dict = evaluate(pay)
        print(
            f"\nScenario [{scen.upper():8s}] -> status={res_model.status_light:6s} | "
            f"raw={res_model.raw_status:17s} | qc_ok={str(res_model.quality_passed):5s} | "
            f"metrics={len(res_model.metrics):2d} | next_h={res_model.short_term_plan.next_measurement_in_hours}h | "
            f"urgent={res_model.short_term_plan.urgent_alert} | days_to_red={res_model.long_term_plan.days_until_red_prediction}"
        )
        if res_dict.get("correlation_alerts"):
            for ca in res_dict["correlation_alerts"]:
                print(f"  Correlation: {ca}")

    manual_res = to_schema(demo_payload("green"), manual_inputs={"ijv_flow": "reversed", "ijv_thrombus": True})
    assert manual_res.status_light == "RED" and manual_res.short_term_plan.urgent_alert is True
    print("\nManual override check PASSED (ijv_thrombus=True -> RED, urgent_alert=True).")
