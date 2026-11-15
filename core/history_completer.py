"""Longitudinal History Backfill & Developer Synthetic Trajectory Completer (`core/history_completer.py`).

Role 1 exclusively owns this file.
Solves missing `history_days / history_values` on secondary indicators without touching
teammates' `modules/*.py` files:

1. Real CSV / JSON Extraction (Both Flight Mode & Developer Mode):
   - Reads multi-row CSV/JSON series already loaded in `file_payload` (e.g., `goes_integral_protons_6h.json`
     for `>=100 MeV`, `atm02_pressure_o2.csv` for `p_total_kPa` / `pio2_mmHg`, `atm03_thermal.csv` for
     `temp_C` / `rh_pct`, `iso03_mood.csv` for `stress_vas`, `atm06_microbial.csv` for `history_5_limit_ratio`,
     `e4d_sets.csv` for `e4d_s_bone_index` / `velocity_loss_pct`) and attaches genuine multi-point trajectories.
2. Flight Mode vs. Developer Mode Missing-History Behavior:
   - Flight Mode (`auto_complete_synthetic=False`): leaves genuinely single-point / missing-CSV indicators with
     `<2` points so the UI honestly displays "Missing Longitudinal History (Single-Point Reading Only)".
   - Developer Mode (`auto_complete_synthetic=True`): synthesizes smooth `[0, 30, 60, 90, mission_day]`
     trajectories from `baseline_val` -> `current_val` and tags `metric.synthetic_completed = True` so
     every indicator card can be stress-tested and inspected on the 3-Layer Trajectory Chart.
"""

from __future__ import annotations

import ast
from typing import Any, Optional

from core.checkin_tracker import METRIC_TRACKING_META
from core.schema import MetricItem, ModuleEvaluationResult


def _safe_float_list(vals: list[Any], ndigits: int = 3) -> list[float]:
    out: list[float] = []
    for v in vals:
        if v is None or isinstance(v, bool):
            continue
        try:
            out.append(round(float(v), ndigits))
        except (TypeError, ValueError):
            continue
    return out


def _recent_mission_days(count: int, mission_day: int) -> list[int]:
    if count <= 0:
        return []
    start = max(1, mission_day - count + 1)
    days = [start + i for i in range(count)]
    # Ensure strictly increasing even when mission_day < count
    if len(set(days)) < count:
        return list(range(1, count + 1))
    return days


def attach_existing_file_histories(
    module_id: str,
    result: ModuleEvaluationResult,
    file_payload: dict[str, Any],
    mission_day: int,
) -> None:
    """Attach genuine multi-row CSV/JSON series from `data/<module_id>/` onto metrics lacking `history_days`."""
    if not file_payload or not result.quality_passed:
        return

    metrics_by_name: dict[str, MetricItem] = {m.metric_name: m for m in result.metrics}

    if module_id == "cabin_environment":
        # 1) proton_flux_100mev_pfu from goes_integral_protons_6h.json
        goes_recs = file_payload.get("json_goes_integral_protons_6h")
        m_100 = metrics_by_name.get("proton_flux_100mev_pfu")
        if m_100 and len(m_100.history_days) < 2 and isinstance(goes_recs, list):
            flux_100 = _safe_float_list(
                [r.get("flux") for r in goes_recs if isinstance(r, dict) and "100" in str(r.get("energy", ""))],
                ndigits=3,
            )
            if len(flux_100) >= 2:
                pts = flux_100[-5:]
                m_100.history_days = _recent_mission_days(len(pts), mission_day)
                m_100.history_values = pts

        # 2) p_total_kPa & pio2_mmHg from atm02_pressure_o2.csv
        atm02 = file_payload.get("csv_atm02_pressure_o2")
        if isinstance(atm02, list) and len(atm02) >= 2:
            p_vals: list[float] = []
            pio2_vals: list[float] = []
            for r in atm02[-5:]:
                if not isinstance(r, dict):
                    continue
                p1 = r.get("p_sensor1_kPa")
                p2 = r.get("p_sensor2_kPa")
                o2_pct = r.get("o2_vol_pct")
                try:
                    p_mean = (float(p1) + float(p2)) / 2.0 if (p1 is not None and p2 is not None) else float(p1 or p2)
                    p_vals.append(round(p_mean, 2))
                    if o2_pct is not None:
                        p_mmhg = p_mean * 7.50062
                        pio2 = (float(o2_pct) / 100.0) * (p_mmhg - 47.0)
                        pio2_vals.append(round(pio2, 1))
                except (TypeError, ValueError):
                    continue
            m_ptot = metrics_by_name.get("p_total_kPa")
            if m_ptot and len(m_ptot.history_days) < 2 and len(p_vals) >= 2:
                m_ptot.history_days = _recent_mission_days(len(p_vals), mission_day)
                m_ptot.history_values = p_vals
            m_pio2 = metrics_by_name.get("pio2_mmHg")
            if m_pio2 and len(m_pio2.history_days) < 2 and len(pio2_vals) >= 2:
                m_pio2.history_days = _recent_mission_days(len(pio2_vals), mission_day)
                m_pio2.history_values = pio2_vals

        # 3) temp_C & rh_pct from atm03_thermal.csv
        atm03 = file_payload.get("csv_atm03_thermal")
        if isinstance(atm03, list) and len(atm03) >= 2:
            t_vals = _safe_float_list([r.get("temp_C") for r in atm03[-5:] if isinstance(r, dict)], ndigits=2)
            rh_vals = _safe_float_list([r.get("rh_pct") for r in atm03[-5:] if isinstance(r, dict)], ndigits=1)
            m_t = metrics_by_name.get("temp_C")
            if m_t and len(m_t.history_days) < 2 and len(t_vals) >= 2:
                m_t.history_days = _recent_mission_days(len(t_vals), mission_day)
                m_t.history_values = t_vals
            m_rh = metrics_by_name.get("rh_pct")
            if m_rh and len(m_rh.history_days) < 2 and len(rh_vals) >= 2:
                m_rh.history_days = _recent_mission_days(len(rh_vals), mission_day)
                m_rh.history_values = rh_vals

        # 4) stress_vas from iso03_mood.csv
        iso03 = file_payload.get("csv_iso03_mood")
        m_vas = metrics_by_name.get("stress_vas")
        if m_vas and len(m_vas.history_days) < 2 and isinstance(iso03, list) and len(iso03) >= 2:
            vas_vals = _safe_float_list(
                [
                    r.get("vas_stress")
                    for r in iso03[-7:]
                    if isinstance(r, dict) and not r.get("straight_lined") and r.get("complete", True)
                ],
                ndigits=1,
            )
            if len(vas_vals) >= 2:
                pts = vas_vals[-5:]
                m_vas.history_days = _recent_mission_days(len(pts), mission_day)
                m_vas.history_values = pts

        # 5) microbial_max_limit_ratio from atm06_microbial.csv (`history_5_limit_ratio`)
        atm06 = file_payload.get("csv_atm06_microbial")
        m_mic = metrics_by_name.get("microbial_max_limit_ratio")
        if m_mic and len(m_mic.history_days) < 2 and isinstance(atm06, list) and atm06:
            raw_hist = atm06[-1].get("history_5_limit_ratio") if isinstance(atm06[-1], dict) else None
            if isinstance(raw_hist, str) and raw_hist.strip().startswith("["):
                try:
                    parsed_list = ast.literal_eval(raw_hist)
                    if isinstance(parsed_list, list):
                        mic_vals = _safe_float_list(parsed_list, ndigits=3)
                        if len(mic_vals) >= 2:
                            # Quarterly / monthly cadence up to mission_day
                            step_d = max(1, mission_day // max(1, len(mic_vals)))
                            days_q = [max(1, mission_day - step_d * (len(mic_vals) - 1 - i)) for i in range(len(mic_vals))]
                            if len(set(days_q)) == len(mic_vals):
                                m_mic.history_days = days_q
                                m_mic.history_values = mic_vals
                except Exception:  # noqa: BLE001
                    pass

    elif module_id == "musculoskeletal":
        # e4d_s_bone_index & velocity_loss_pct from e4d_sets.csv
        e4d = file_payload.get("csv_e4d_sets")
        if isinstance(e4d, list) and len(e4d) >= 2:
            d_list: list[int] = []
            sb_list: list[float] = []
            vl_list: list[float] = []
            for r in e4d:
                if not isinstance(r, dict):
                    continue
                try:
                    md = int(float(r["mission_day"]))
                    sb = float(r["s_bone_index"])
                    vl = float(r["velocity_loss_pct"])
                    d_list.append(md)
                    sb_list.append(round(sb, 3))
                    vl_list.append(round(vl, 1))
                except (KeyError, TypeError, ValueError):
                    continue
            if len(d_list) >= 2:
                m_sb = metrics_by_name.get("e4d_s_bone_index")
                if m_sb and len(m_sb.history_days) < 2:
                    m_sb.history_days = list(d_list)
                    m_sb.history_values = list(sb_list)
                m_vl = metrics_by_name.get("velocity_loss_pct")
                if m_vl and len(m_vl.history_days) < 2:
                    m_vl.history_days = list(d_list)
                    m_vl.history_values = list(vl_list)


def complete_missing_histories_for_dev(
    results: dict[str, ModuleEvaluationResult],
    mission_day: int,
    auto_complete_synthetic: bool = False,
) -> dict[str, ModuleEvaluationResult]:
    """Ensure thresholds are populated and, when `auto_complete_synthetic=True` (Dev Mode),
    synthesize smooth longitudinal curves for indicators lacking multi-day CSV history.
    """
    for _mod_id, res in results.items():
        if not res.quality_passed or getattr(res, "standby", False):
            continue

        for metric in res.metrics:
            if getattr(metric, "standby", False):
                continue

            meta = METRIC_TRACKING_META.get(metric.metric_name)
            if meta:
                if metric.yellow_threshold is None and meta.get("yellow_threshold") is not None:
                    metric.yellow_threshold = float(meta["yellow_threshold"])
                if metric.red_threshold is None and meta.get("red_threshold") is not None:
                    metric.red_threshold = float(meta["red_threshold"])
                if "lower_is_worse" in meta:
                    metric.lower_is_worse = bool(meta["lower_is_worse"])

            if len(metric.history_days) >= 2 or not auto_complete_synthetic:
                continue

            # Skip non-numeric current values (e.g., categorical strings unless convertible)
            cur_raw = metric.current_val
            if cur_raw is None or isinstance(cur_raw, bool):
                continue
            try:
                cur_num = float(cur_raw)
            except (TypeError, ValueError):
                continue

            base_raw: Optional[Any] = metric.baseline_val
            base_num: float
            try:
                if base_raw is not None and not isinstance(base_raw, bool):
                    base_num = float(base_raw)
                elif meta and meta.get("baseline_default") is not None:
                    base_num = float(meta["baseline_default"])
                else:
                    base_num = cur_num
            except (TypeError, ValueError):
                base_num = cur_num

            target_day = max(2, int(mission_day))
            if target_day >= 90:
                synth_days = [0, 30, 60, 90, target_day]
                if synth_days[-1] == 90:
                    synth_days = [0, 20, 45, 70, 90]
            else:
                n_pts = min(5, target_day + 1)
                synth_days = sorted({int(round(i * target_day / max(1, n_pts - 1))) for i in range(n_pts)})
                if len(synth_days) < 2:
                    synth_days = [0, target_day]

            span = max(1, synth_days[-1] - synth_days[0])
            synth_vals = [
                round(base_num + (cur_num - base_num) * ((d - synth_days[0]) / span), 3)
                for d in synth_days
            ]
            metric.history_days = synth_days
            metric.history_values = synth_vals
            metric.synthetic_completed = True
            if metric.slope_per_day is None and span > 0:
                metric.slope_per_day = round((synth_vals[-1] - synth_vals[0]) / span, 4)

    return results
