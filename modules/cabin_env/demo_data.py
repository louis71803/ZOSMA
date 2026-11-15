"""Demo baselines, synthetic 4-scenario payloads, and CSV/JSON template exporter."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

from modules.cabin_env.measurement_rules import DATA_DIR


def demo_baseline() -> dict[str, Any]:
    """Module 7-day medians and personal pre-flight baselines (e.g. RAD-01 Columbus ~ 4.06 uGy/h)."""
    return {
        "crew_id": "C002",
        "mission_length_days": 180,
        # Module 7-day rolling medians
        "rad01_columbus_median_uGy_h": 4.06,     # ~97.4 uGy/d absorbed (~220 uSv/d eq with Q=2.26; Columbus ref 195-360 uGy/d)
        "aco01_work_median_dBA": 54.5,
        "aco01_sleep_median_dBA": 45.0,
        "atm01_ppco2_median_mmHg": 1.82,
        "atm02_setpoint_kPa": 101.3,
        "atm03_temp_median_C": 22.2,
        "atm03_rh_median_pct": 45.0,
        "atm04_smac_ratio_median": 0.14,
        "atm05_toc_median_mg_L": {"WPA_dispenser": 0.65, "potable_bus": 0.70},
        "atm06_limit_ratio_median": 0.12,
        "atm07_limit_ratio_median": 0.15,
        # Personal pre-flight / days 1-14 baselines (mean & SD)
        "aco02_leq8_mean_dBA": 44.5,
        "aco02_leq8_sd_dBA": 2.5,
        "aco03_audiogram_preflight_dB": {500: 10.0, 1000: 10.0, 2000: 10.0, 3000: 12.0, 4000: 12.0, 6000: 15.0},
        "aco03_sts_mean_dB": 1.0,
        "aco03_sts_sd_dB": 2.5,
        "iso01_sleep_mean_h": 7.35,
        "iso01_sleep_sd_h": 0.45,
        "iso02_pvt_speed_mean": 4.25,
        "iso02_pvt_speed_sd": 0.30,
        "iso03_vas_stress_mean": 24.0,
        "iso03_vas_stress_sd": 7.0,
        "iso04_midpoint_shift_mean_h": 0.15,
        "iso04_midpoint_shift_sd_h": 0.30,
        # Legacy flat aliases for backward compatibility with Role 1 UI
        "dose_rate_uGy_h": 4.06,
        "career_dose_mSv": 145.0,
        "ppco2_1h_mmHg": 1.82,
        "p_total_kPa": 101.3,
        "pio2_mmHg": 159.8,
        "temp_C": 22.2,
        "rh_pct": 45.0,
        "sleep_tst_h": 7.35,
    }


def _make_timestamps_utc(base_iso: str, count: int, step_minutes: float) -> list[str]:
    dt0 = datetime.fromisoformat(base_iso.replace("Z", "+00:00"))
    out = []
    for i in range(count):
        dt = dt0 - timedelta(minutes=step_minutes * (count - 1 - i))
        out.append(dt.strftime("%Y-%m-%dT%H:%M:%SZ"))
    return out


def demo_payload(scenario: str = "green") -> dict[str, Any]:
    """Generate complete 17-card payloads for 'green', 'yellow', 'red', and 'bad_data'."""
    scen = (scenario or "green").strip().lower()
    now_iso = "2026-11-14T12:00:00Z"
    ts_1h_5 = _make_timestamps_utc(now_iso, 5, 60.0)
    ts_1h_26 = _make_timestamps_utc(now_iso, 26, 60.0)
    ts_1h_8 = _make_timestamps_utc(now_iso, 8, 60.0)
    ts_5m_5 = _make_timestamps_utc(now_iso, 5, 5.0)
    ts_1m_5 = _make_timestamps_utc(now_iso, 5, 1.0)
    ts_1d_7 = _make_timestamps_utc(now_iso, 7, 1440.0)
    ts_7d_5 = _make_timestamps_utc(now_iso, 5, 10080.0)
    ts_30d_5 = _make_timestamps_utc(now_iso, 5, 43200.0)
    ts_60d_5 = _make_timestamps_utc(now_iso, 5, 86400.0)
    ts_90d_5 = _make_timestamps_utc(now_iso, 5, 129600.0)
    ts_4d_5 = _make_timestamps_utc(now_iso, 5, 5760.0)

    if scen == "bad_data":
        # Exercises:
        # 1) SAA-masked RAD-01 (all readings inside 50S-0, 90W-40E + unconfirmed >1000x spike)
        # 2) Stuck CO2 (>= 24 identical consecutive hourly values, e.g., 26h like RR-1)
        # 3) Flat T/RH > 6 h (8 identical hourly values)
        # 4) Failed SLM pre/post field calibration (> 0.5 dB drift)
        # 5) Actigraphy wear < 80%
        # Plus QC failures across remaining cards so bad_data is rejected / no_data (never Green).
        return {
            "scenario": "bad_data",
            "crew_id": "C002",
            "mission_day": 124,
            "mission_length_days": 180,
            "timestamp_utc": now_iso,
            "location": "Columbus",
            "data_source": "SIMULATED",
            # Flat Role-1 compatibility keys
            "co2_sensor_stuck_hours": 26.0,
            "dose_rate_uGy_h": 48.0,
            "saa_pass": True,
            "career_dose_mSv": 152.0,
            "proton_flux_10mev_pfu": -1.0,
            "spe_alert": False,
            "module_spl_dBA": 54.0,
            "crew_leq8_dBA": 45.0,
            "daily_noise_dose_pct": 30.0,
            "ppco2_1h_mmHg": 1.82,
            "ppco2_7d_mmHg": 1.82,
            "p_total_kPa": 125.0,
            "pio2_mmHg": 159.0,
            "dpdt_kPa_per_min": 0.0,
            "temp_C": 22.4,
            "rh_pct": 45.0,
            "max_smac_ratio": 0.20,
            "ammonia_or_fire_alarm": False,
            "sleep_tst_h": 7.2,
            "pvt_speed_1_per_s": 4.2,
            "workload_bedford": 3.0,
            "stress_vas": 25.0,
            # Card-level structured inputs
            "rad01_records": [
                {"timestamp_utc": ts_1h_5[0], "module": "Columbus", "dose_rate_uGy_h": 42.0, "lat_deg": -25.0, "lon_deg": -45.0, "second_detector_confirmed": True},
                {"timestamp_utc": ts_1h_5[1], "module": "Columbus", "dose_rate_uGy_h": 55.0, "lat_deg": -18.0, "lon_deg": -30.0, "second_detector_confirmed": True},
                {"timestamp_utc": ts_1h_5[2], "module": "Columbus", "dose_rate_uGy_h": 48.0, "lat_deg": -12.0, "lon_deg": -15.0, "second_detector_confirmed": True},
                {"timestamp_utc": ts_1h_5[3], "module": "Columbus", "dose_rate_uGy_h": 6500.0, "lat_deg": 22.0, "lon_deg": 110.0, "second_detector_confirmed": False},
                {"timestamp_utc": ts_1h_5[4], "module": "Columbus", "dose_rate_uGy_h": 51.0, "lat_deg": -30.0, "lon_deg": 10.0, "second_detector_confirmed": True},
            ],
            "rad02_daily": {
                "timestamp_utc": now_iso,
                "career_prior_mSv": 120.0,
                "mission_cum_mSv": 32.0,
                "single_spe_mSv": 0.0,
                "occupancy_hours": {"Columbus": 12.0, "Harmony": 6.0},  # 18 h -> missing 6 h (> 4 h missing)
                "module_dose_rates_uGy_h": {"Columbus": 4.06, "Harmony": 4.50},
            },
            "rad03_goes": {
                "age_hours": 0.75,  # 45 min old (> 30 min drop rule)
                "swpc_warning": False,
                "primary_records": [
                    {"time_tag": ts_5m_5[i], "satellite": "GOES-18", "flux_10mev": -2.0, "flux_100mev": 0.0}
                    for i in range(5)
                ],
                "secondary_records": [],
            },
            "aco01_survey": {
                "timestamp_utc": now_iso,
                "area_type": "work",
                "mission_duration_days": 180,
                "pre_cal_dB": 94.0,
                "post_cal_dB": 94.8,  # 0.8 dB drift (> 0.5 dB -> reject)
                "lab_cal_age_months": 6,
                "spl_dBA": 54.0,
                "impulse_peak_dB": 98.0,
                "tonal_margin_dB": 14.0,
                "octave_bands_dB": {63: 62.0, 125: 56.0, 250: 52.0, 500: 49.0, 1000: 47.0, 2000: 44.0, 4000: 41.0, 8000: 38.0},
            },
            "aco02_dosimetry": {
                "timestamp_utc": now_iso,
                "valid_hours": 16.5,  # < 20 h -> reject
                "mic_covered": True,
                "leq16_work_dBA": 56.0,
                "leq8_sleep_dBA": 45.0,
                "lmax_dBA": 78.0,
                "peak_dB": 110.0,
                "dose_24h_pct": 32.0,
            },
            "aco03_audiogram": {
                "timestamp_utc": now_iso,
                "ambient_above_nc40": True,  # -> reject
                "max_repeat_diff_dB": 15.0,
                "retest_confirmed": False,
                "right_ear_dB": {500: 10.0, 1000: 10.0, 2000: 10.0, 3000: 12.0, 4000: 12.0, 6000: 15.0},
                "left_ear_dB": {500: 10.0, 1000: 10.0, 2000: 10.0, 3000: 12.0, 4000: 12.0, 6000: 15.0},
            },
            "atm01_co2": {
                "records_1h": [
                    {"timestamp_utc": ts, "co2_ppm": 2400.0, "second_sensor_confirmed": True}
                    for ts in ts_1h_26  # 26 identical consecutive hourly readings (>= 24h stuck sensor)
                ],
                "step_change_1min_ppm": 0.0,
                "step_second_sensor_confirmed": True,
                "mean_7d_ppm": 2400.0,
            },
            "atm02_pressure": {
                "records_1m": [
                    {"timestamp_utc": ts, "p_sensor1_kPa": 118.0, "p_sensor2_kPa": 118.0, "o2_vol_pct": 21.0, "dpdt_1m_kPa_min": 0.0, "dpdt_10m_kPa_min": 0.0}
                    for ts in ts_1m_5  # > 110 kPa physical range check -> reject
                ],
            },
            "atm03_thermal": {
                "records_1h": [
                    {"timestamp_utc": ts, "temp_C": 22.40, "rh_pct": 45.00}
                    for ts in ts_1h_8  # 8h identical (> 6h flat-lined stuck sensor -> reject)
                ],
            },
            "atm04_voc": {
                "timestamp_utc": now_iso,
                "internal_cal_passed": False,  # -> reject
                "combustion_alarm": False,
                "ammonia_alarm": False,
                "compounds": [
                    {"name": "methanol", "conc_mg_m3": -0.2, "smac_mg_m3": 9.0, "duration": "7d"},
                ],
            },
            "atm05_water": {
                "timestamp_utc": now_iso,
                "water_source": "WPA_dispenser",
                "std_cal_passed": False,  # -> reject
                "toc_mg_L": 0.7,
                "iodine_mg_L": "< DL",
                "silver_ug_L": 250.0,
            },
            "atm06_microbial": {
                "timestamp_utc": now_iso,
                "incubation_complete": False,  # -> reject
                "condensation_spread": True,
                "blank_present": False,
                "air_bacteria_cfu_m3": 120.0,
                "air_fungi_cfu_m3": 15.0,
                "surface_bacteria_cfu_100cm2": 800.0,
                "surface_fungi_cfu_100cm2": 10.0,
                "water_heterotrophic_cfu_mL": 5.0,
                "water_coliform_100mL_detected": False,
                "water_fungi_100mL_detected": False,
            },
            "atm07_particulates": {
                "records_1h": [
                    {"timestamp_utc": ts, "total_dust_mg_m3": 0.2, "respirable_pm25_mg_m3": 0.08, "lunar_dust_twa_mg_m3": 0.0, "self_clean_active": True, "sensor_rated_max_mg_m3": 10.0}
                    for ts in ts_1h_5  # self_clean_active -> reject
                ],
            },
            "iso01_sleep": {
                "nights": [
                    {"timestamp_utc": ts_1d_7[i], "tst_h": 7.2, "self_report_h": 7.4, "wear_time_pct": 62.0}  # < 80% wear -> reject
                    for i in range(7)
                ],
            },
            "iso02_pvt": {
                "sessions": [
                    {"timestamp_utc": ts_4d_5[i], "response_speed_1_s": 4.2, "lapses": 1, "false_starts": 14, "missed_stimuli_pct": 25.0, "pre_eva": False}
                    for i in range(5)  # false_starts > 10 & missed > 20% -> reject
                ],
            },
            "iso03_mood": {
                "entries": [
                    {"timestamp_utc": ts_1d_7[i], "vas_stress": 50.0, "bedford_workload": 3, "poms37_tmd": 12.0, "hopelessness_flag": False, "straight_lined": True, "complete": False, "journal_text": "Private crew diary note - never store centrally"}
                    for i in range(7)  # straight_lined & incomplete -> reject
                ],
            },
            "iso04_light": {
                "days": [
                    {"timestamp_utc": ts_1d_7[i], "morning_lux": 320.0, "presleep_lux": 14.0, "midpoint_shift_h": 0.2, "off_wrist": True, "sleeve_covered": True}
                    for i in range(7)  # off_wrist / sleeve_covered -> reject
                ],
            },
        }

    if scen == "yellow":
        return {
            "scenario": "yellow",
            "crew_id": "C002",
            "mission_day": 124,
            "mission_length_days": 180,
            "timestamp_utc": now_iso,
            "location": "Columbus",
            "data_source": "SIMULATED",
            # Flat Role-1 compatibility keys
            "co2_sensor_stuck_hours": 0.0,
            "dose_rate_uGy_h": 9.6,
            "saa_pass": False,
            "career_dose_mSv": 365.0,
            "proton_flux_10mev_pfu": 24.0,
            "spe_alert": False,
            "module_spl_dBA": 60.2,
            "crew_leq8_dBA": 54.0,
            "daily_noise_dose_pct": 72.0,
            "ppco2_1h_mmHg": 2.70,
            "ppco2_7d_mmHg": 2.58,
            "p_total_kPa": 99.6,
            "pio2_mmHg": 134.0,
            "dpdt_kPa_per_min": -0.002,
            "temp_C": 26.0,
            "rh_pct": 65.0,
            "max_smac_ratio": 0.68,
            "ammonia_or_fire_alarm": False,
            "sleep_tst_h": 6.3,
            "pvt_speed_1_per_s": 3.80,
            "workload_bedford": 5.0,
            "stress_vas": 34.0,
            # Structured 17-card inputs (all Yellow)
            "rad01_records": [
                {"timestamp_utc": ts_1h_5[0], "module": "Columbus", "dose_rate_uGy_h": 8.5, "lat_deg": 15.0, "lon_deg": 45.0, "second_detector_confirmed": True},
                {"timestamp_utc": ts_1h_5[1], "module": "Columbus", "dose_rate_uGy_h": 8.8, "lat_deg": 28.0, "lon_deg": 72.0, "second_detector_confirmed": True},
                {"timestamp_utc": ts_1h_5[2], "module": "Columbus", "dose_rate_uGy_h": 9.1, "lat_deg": 42.0, "lon_deg": 105.0, "second_detector_confirmed": True},
                {"timestamp_utc": ts_1h_5[3], "module": "Columbus", "dose_rate_uGy_h": 9.4, "lat_deg": 35.0, "lon_deg": 140.0, "second_detector_confirmed": True},
                {"timestamp_utc": ts_1h_5[4], "module": "Columbus", "dose_rate_uGy_h": 9.6, "lat_deg": 12.0, "lon_deg": 170.0, "second_detector_confirmed": True},
            ],
            "rad02_daily": {
                "timestamp_utc": now_iso,
                "career_prior_mSv": 290.0,
                "mission_cum_mSv": 75.0,  # Total 365 mSv -> Yellow (300-480 mSv)
                "single_spe_mSv": 0.0,
                "occupancy_hours": {"Columbus": 16.0, "Harmony": 8.0},
                "module_dose_rates_uGy_h": {"Columbus": 9.6, "Harmony": 8.2},
                "history_5d_career_mSv": [362.5, 363.1, 363.7, 364.3, 365.0],
                "history_5d_timestamps": ts_1d_7[-5:],
            },
            "rad03_goes": {
                "age_hours": 0.08,
                "swpc_warning": True,
                "primary_records": [
                    {"time_tag": ts_5m_5[0], "satellite": "GOES-18", "flux_10mev": 14.0, "flux_100mev": 0.4},
                    {"time_tag": ts_5m_5[1], "satellite": "GOES-18", "flux_10mev": 16.5, "flux_100mev": 0.5},
                    {"time_tag": ts_5m_5[2], "satellite": "GOES-18", "flux_10mev": 19.0, "flux_100mev": 0.6},
                    {"time_tag": ts_5m_5[3], "satellite": "GOES-18", "flux_10mev": 21.5, "flux_100mev": 0.7},
                    {"time_tag": ts_5m_5[4], "satellite": "GOES-18", "flux_10mev": 24.0, "flux_100mev": 0.8},
                ],
                "secondary_records": [],
            },
            "aco01_survey": {
                "timestamp_utc": now_iso,
                "area_type": "work",
                "mission_duration_days": 180,
                "pre_cal_dB": 94.0,
                "post_cal_dB": 94.2,
                "lab_cal_age_months": 5,
                "spl_dBA": 60.2,
                "impulse_peak_dB": 108.0,
                "tonal_margin_dB": 8.0,  # < 10 dB tonal margin AND 1000 Hz > NC-50 (51 dB) -> Yellow
                "octave_bands_dB": {63: 66.0, 125: 60.0, 250: 56.0, 500: 53.0, 1000: 54.0, 2000: 48.0, 4000: 45.0, 8000: 42.0},
                "history_5_spl_dBA": [55.0, 56.2, 57.5, 58.8, 60.2],
                "history_5_timestamps": ts_30d_5,
            },
            "aco02_dosimetry": {
                "timestamp_utc": now_iso,
                "valid_hours": 23.5,
                "mic_covered": False,
                "leq16_work_dBA": 63.0,
                "leq8_sleep_dBA": 54.0,  # > 50 dBA -> Yellow
                "lmax_dBA": 82.0,
                "peak_dB": 116.0,
                "dose_24h_pct": 72.0,    # 50 < D <= 100 -> Yellow
                "history_5_leq8_dBA": [45.0, 46.5, 48.0, 49.0, 54.0],
                "history_5_timestamps": ts_60d_5,
            },
            "aco03_audiogram": {
                "timestamp_utc": now_iso,
                "ambient_above_nc40": False,
                "max_repeat_diff_dB": 5.0,
                "retest_confirmed": True,
                # Single-freq 6000 Hz shift = 30 - 15 = 15 dB (>=15 dB), avg 2/3/4 kHz shift = (5+3+3)/3 = 3.67 dB (<10 dB) -> Yellow
                "right_ear_dB": {500: 15.0, 1000: 15.0, 2000: 15.0, 3000: 15.0, 4000: 15.0, 6000: 30.0},
                "left_ear_dB": {500: 10.0, 1000: 10.0, 2000: 10.0, 3000: 12.0, 4000: 12.0, 6000: 15.0},
                "history_5_sts_dB": [1.0, 1.5, 2.0, 2.8, 3.67],
                "history_5_timestamps": ts_30d_5,
            },
            "atm01_co2": {
                "records_1h": [
                    {"timestamp_utc": ts_1h_5[0], "co2_ppm": 3350.0, "second_sensor_confirmed": True},
                    {"timestamp_utc": ts_1h_5[1], "co2_ppm": 3400.0, "second_sensor_confirmed": True},
                    {"timestamp_utc": ts_1h_5[2], "co2_ppm": 3450.0, "second_sensor_confirmed": True},
                    {"timestamp_utc": ts_1h_5[3], "co2_ppm": 3500.0, "second_sensor_confirmed": True},
                    {"timestamp_utc": ts_1h_5[4], "co2_ppm": 3553.0, "second_sensor_confirmed": True},  # ~2.70 mmHg (2.5-3.0 -> Yellow)
                ],
                "step_change_1min_ppm": 120.0,
                "step_second_sensor_confirmed": True,
                "mean_7d_ppm": 3395.0,  # ~2.58 mmHg (>=2.5 -> Yellow)
            },
            "atm02_pressure": {
                "records_1m": [
                    {"timestamp_utc": ts_1m_5[i], "p_sensor1_kPa": 99.8 - 0.05 * i, "p_sensor2_kPa": 99.7 - 0.05 * i, "o2_vol_pct": 19.8, "dpdt_1m_kPa_min": -0.002, "dpdt_10m_kPa_min": -0.002}
                    for i in range(5)  # P=99.6 kPa (< 100.28 kPa -1% setpoint), FiO2=0.198 -> PIO2 = 0.198*(747-47) = 138.6 mmHg (127-139 -> Yellow)
                ],
            },
            "atm03_thermal": {
                "records_1h": [
                    {"timestamp_utc": ts_1h_5[0], "temp_C": 24.8, "rh_pct": 58.0},
                    {"timestamp_utc": ts_1h_5[1], "temp_C": 25.2, "rh_pct": 60.0},
                    {"timestamp_utc": ts_1h_5[2], "temp_C": 25.5, "rh_pct": 62.0},
                    {"timestamp_utc": ts_1h_5[3], "temp_C": 25.8, "rh_pct": 64.0},
                    {"timestamp_utc": ts_1h_5[4], "temp_C": 26.0, "rh_pct": 65.0},  # Outside 20-25C / 30-60%, inside 18-27C / 25-75% -> Yellow
                ],
            },
            "atm04_voc": {
                "timestamp_utc": now_iso,
                "internal_cal_passed": True,
                "combustion_alarm": False,
                "ammonia_alarm": False,
                "compounds": [
                    {"name": "methanol", "conc_mg_m3": 6.12, "smac_mg_m3": 9.0, "duration": "7d"},  # 68% SMAC -> Yellow
                    {"name": "acetone", "conc_mg_m3": 12.0, "smac_mg_m3": 52.0, "duration": "7d"},
                ],
                "history_5_smac_ratio": [0.32, 0.41, 0.50, 0.59, 0.68],
                "history_5_timestamps": _make_timestamps_utc(now_iso, 5, 360.0),
            },
            "atm05_water": {
                "timestamp_utc": now_iso,
                "water_source": "WPA_dispenser",
                "std_cal_passed": True,
                "toc_mg_L": 2.1,      # 1.5-3.0 mg/L -> Yellow
                "iodine_mg_L": 0.12,
                "silver_ug_L": 85.0,  # < 100 ug/L -> Yellow
                "history_5_toc_mg_L": [1.1, 1.35, 1.6, 1.85, 2.1],
                "history_5_timestamps": ts_7d_5,
            },
            "atm06_microbial": {
                "timestamp_utc": now_iso,
                "incubation_complete": True,
                "condensation_spread": False,
                "blank_present": True,
                "air_bacteria_cfu_m3": 680.0,         # 68% of 1000 limit -> Yellow
                "air_fungi_cfu_m3": 45.0,
                "surface_bacteria_cfu_100cm2": 4200.0,
                "surface_fungi_cfu_100cm2": 35.0,
                "water_heterotrophic_cfu_mL": 22.0,
                "water_coliform_100mL_detected": False,
                "water_fungi_100mL_detected": False,
                "history_5_limit_ratio": [0.25, 0.35, 0.45, 0.56, 0.68],
                "history_5_timestamps": ts_90d_5,
            },
            "atm07_particulates": {
                "records_1h": [
                    {"timestamp_utc": ts_1h_5[i], "total_dust_mg_m3": 1.2 + 0.15 * i, "respirable_pm25_mg_m3": 0.45 + 0.05 * i, "lunar_dust_twa_mg_m3": 0.12, "self_clean_active": False, "sensor_rated_max_mg_m3": 10.0}
                    for i in range(5)  # PM2.5 = 0.65 mg/m3 (65% of 1.0 limit), Total = 1.8 mg/m3 (60% of 3.0) -> Yellow
                ],
            },
            "iso01_sleep": {
                "nights": [
                    {"timestamp_utc": ts_1d_7[0], "tst_h": 7.2, "self_report_h": 7.3, "wear_time_pct": 94.0},
                    {"timestamp_utc": ts_1d_7[1], "tst_h": 7.1, "self_report_h": 7.0, "wear_time_pct": 95.0},
                    {"timestamp_utc": ts_1d_7[2], "tst_h": 7.0, "self_report_h": 7.1, "wear_time_pct": 93.0},
                    {"timestamp_utc": ts_1d_7[3], "tst_h": 6.8, "self_report_h": 6.9, "wear_time_pct": 96.0},
                    {"timestamp_utc": ts_1d_7[4], "tst_h": 6.6, "self_report_h": 6.7, "wear_time_pct": 92.0},
                    {"timestamp_utc": ts_1d_7[5], "tst_h": 6.5, "self_report_h": 6.6, "wear_time_pct": 94.0},
                    {"timestamp_utc": ts_1d_7[6], "tst_h": 6.3, "self_report_h": 6.5, "wear_time_pct": 95.0},  # 6-7 h -> Yellow
                ],
            },
            "iso02_pvt": {
                "sessions": [
                    {"timestamp_utc": ts_4d_5[0], "response_speed_1_s": 4.20, "lapses": 1, "false_starts": 2, "missed_stimuli_pct": 2.0, "pre_eva": False},
                    {"timestamp_utc": ts_4d_5[1], "response_speed_1_s": 4.10, "lapses": 2, "false_starts": 2, "missed_stimuli_pct": 3.0, "pre_eva": False},
                    {"timestamp_utc": ts_4d_5[2], "response_speed_1_s": 4.02, "lapses": 2, "false_starts": 3, "missed_stimuli_pct": 3.0, "pre_eva": False},
                    {"timestamp_utc": ts_4d_5[3], "response_speed_1_s": 3.98, "lapses": 3, "false_starts": 3, "missed_stimuli_pct": 4.0, "pre_eva": False},
                    {"timestamp_utc": ts_4d_5[4], "response_speed_1_s": 3.80, "lapses": 4, "false_starts": 3, "missed_stimuli_pct": 5.0, "pre_eva": False},  # < 4.25 - 0.30 (3.95), > 3.65 -> Yellow
                ],
            },
            "iso03_mood": {
                "entries": [
                    {"timestamp_utc": ts_1d_7[0], "vas_stress": 25.0, "bedford_workload": 3, "poms37_tmd": 8.0, "hopelessness_flag": False, "straight_lined": False, "complete": True},
                    {"timestamp_utc": ts_1d_7[1], "vas_stress": 26.0, "bedford_workload": 3, "poms37_tmd": 8.0, "hopelessness_flag": False, "straight_lined": False, "complete": True},
                    {"timestamp_utc": ts_1d_7[2], "vas_stress": 28.0, "bedford_workload": 3, "poms37_tmd": 9.0, "hopelessness_flag": False, "straight_lined": False, "complete": True},
                    {"timestamp_utc": ts_1d_7[3], "vas_stress": 30.0, "bedford_workload": 4, "poms37_tmd": 10.0, "hopelessness_flag": False, "straight_lined": False, "complete": True},
                    {"timestamp_utc": ts_1d_7[4], "vas_stress": 33.0, "bedford_workload": 4, "poms37_tmd": 11.0, "hopelessness_flag": False, "straight_lined": False, "complete": True},
                    {"timestamp_utc": ts_1d_7[5], "vas_stress": 34.0, "bedford_workload": 5, "poms37_tmd": 12.0, "hopelessness_flag": False, "straight_lined": False, "complete": True},
                    {"timestamp_utc": ts_1d_7[6], "vas_stress": 35.0, "bedford_workload": 5, "poms37_tmd": 12.0, "hopelessness_flag": False, "straight_lined": False, "complete": True},  # Bedford 5 (4-6) & 3d VAS > 31 -> Yellow
                ],
            },
            "iso04_light": {
                "days": [
                    {"timestamp_utc": ts_1d_7[0], "morning_lux": 350.0, "presleep_lux": 15.0, "midpoint_shift_h": 0.2, "off_wrist": False, "sleeve_covered": False},
                    {"timestamp_utc": ts_1d_7[1], "morning_lux": 340.0, "presleep_lux": 18.0, "midpoint_shift_h": 0.3, "off_wrist": False, "sleeve_covered": False},
                    {"timestamp_utc": ts_1d_7[2], "morning_lux": 330.0, "presleep_lux": 125.0, "midpoint_shift_h": 0.5, "off_wrist": False, "sleeve_covered": False},
                    {"timestamp_utc": ts_1d_7[3], "morning_lux": 340.0, "presleep_lux": 16.0, "midpoint_shift_h": 0.6, "off_wrist": False, "sleeve_covered": False},
                    {"timestamp_utc": ts_1d_7[4], "morning_lux": 320.0, "presleep_lux": 19.0, "midpoint_shift_h": 0.45, "off_wrist": False, "sleeve_covered": False},
                    {"timestamp_utc": ts_1d_7[5], "morning_lux": 310.0, "presleep_lux": 135.0, "midpoint_shift_h": 0.65, "off_wrist": False, "sleeve_covered": False},
                    {"timestamp_utc": ts_1d_7[6], "morning_lux": 300.0, "presleep_lux": 18.0, "midpoint_shift_h": 1.15, "off_wrist": False, "sleeve_covered": False},  # 2 of 7 nights > 100 lux (not 3 consecutive) & shift 1.15 h (1-2 h) -> Yellow
                ],
            },
        }

    if scen == "red":
        # Includes Fast-Track emergencies: rapid depressurization (ATM-02), ammonia/combustion alarm (ATM-04), and confirmed SPE onset (RAD-03).
        return {
            "scenario": "red",
            "crew_id": "C002",
            "mission_day": 124,
            "mission_length_days": 180,
            "timestamp_utc": now_iso,
            "location": "Columbus",
            "data_source": "SIMULATED",
            # Flat Role-1 compatibility keys
            "co2_sensor_stuck_hours": 0.0,
            "dose_rate_uGy_h": 58.0,
            "saa_pass": False,
            "career_dose_mSv": 512.0,
            "proton_flux_10mev_pfu": 240.0,
            "spe_alert": True,
            "module_spl_dBA": 87.5,
            "crew_leq8_dBA": 65.0,
            "daily_noise_dose_pct": 135.0,
            "ppco2_1h_mmHg": 3.45,
            "ppco2_7d_mmHg": 2.95,
            "p_total_kPa": 84.0,
            "pio2_mmHg": 118.0,
            "dpdt_kPa_per_min": -1.25,
            "temp_C": 28.5,
            "rh_pct": 78.0,
            "max_smac_ratio": 1.45,
            "ammonia_or_fire_alarm": True,
            "sleep_tst_h": 5.1,
            "pvt_speed_1_per_s": 3.40,
            "workload_bedford": 8.0,
            "stress_vas": 68.0,
            # Structured 17-card inputs (all Red)
            "rad01_records": [
                {"timestamp_utc": ts_1h_5[0], "module": "Columbus", "dose_rate_uGy_h": 18.0, "lat_deg": 20.0, "lon_deg": 50.0, "second_detector_confirmed": True},
                {"timestamp_utc": ts_1h_5[1], "module": "Columbus", "dose_rate_uGy_h": 28.0, "lat_deg": 32.0, "lon_deg": 80.0, "second_detector_confirmed": True},
                {"timestamp_utc": ts_1h_5[2], "module": "Columbus", "dose_rate_uGy_h": 39.0, "lat_deg": 45.0, "lon_deg": 112.0, "second_detector_confirmed": True},
                {"timestamp_utc": ts_1h_5[3], "module": "Columbus", "dose_rate_uGy_h": 49.0, "lat_deg": 38.0, "lon_deg": 145.0, "second_detector_confirmed": True},
                {"timestamp_utc": ts_1h_5[4], "module": "Columbus", "dose_rate_uGy_h": 58.0, "lat_deg": 18.0, "lon_deg": 175.0, "second_detector_confirmed": True},  # >10x 4.06 median (40.6) AND RAD-03 >= S1 -> Red
            ],
            "rad02_daily": {
                "timestamp_utc": now_iso,
                "career_prior_mSv": 410.0,
                "mission_cum_mSv": 102.0,  # Total 512 mSv > 480 mSv -> Red
                "single_spe_mSv": 255.0,   # Approaching/exceeding 250 mSv [V1 4031]
                "occupancy_hours": {"Columbus": 16.0, "Harmony": 8.0},
                "module_dose_rates_uGy_h": {"Columbus": 58.0, "Harmony": 45.0},
                "history_5d_career_mSv": [498.0, 501.0, 504.5, 508.0, 512.0],
                "history_5d_timestamps": ts_1d_7[-5:],
            },
            "rad03_goes": {
                "age_hours": 0.05,
                "swpc_warning": True,
                "primary_records": [
                    {"time_tag": ts_5m_5[0], "satellite": "GOES-18", "flux_10mev": 95.0, "flux_100mev": 2.1},
                    {"time_tag": ts_5m_5[1], "satellite": "GOES-18", "flux_10mev": 125.0, "flux_100mev": 3.4},
                    {"time_tag": ts_5m_5[2], "satellite": "GOES-18", "flux_10mev": 160.0, "flux_100mev": 4.8},
                    {"time_tag": ts_5m_5[3], "satellite": "GOES-18", "flux_10mev": 205.0, "flux_100mev": 6.2},
                    {"time_tag": ts_5m_5[4], "satellite": "GOES-18", "flux_10mev": 240.0, "flux_100mev": 7.5},  # 4 consecutive >= 100 pfu + RAD-01 rising -> Confirmed SPE Fast-Track Red
                ],
                "secondary_records": [],
            },
            "aco01_survey": {
                "timestamp_utc": now_iso,
                "area_type": "work",
                "mission_duration_days": 180,
                "pre_cal_dB": 94.0,
                "post_cal_dB": 94.1,
                "lab_cal_age_months": 4,
                "spl_dBA": 87.5,          # >= 85 dBA -> Red
                "impulse_peak_dB": 142.0,  # >= 140 dB peak -> Red
                "tonal_margin_dB": 6.0,
                "octave_bands_dB": {63: 82.0, 125: 80.0, 250: 81.0, 500: 83.0, 1000: 84.0, 2000: 81.0, 4000: 78.0, 8000: 74.0},
                "history_5_spl_dBA": [58.0, 64.0, 72.0, 80.0, 87.5],
                "history_5_timestamps": ts_30d_5,
            },
            "aco02_dosimetry": {
                "timestamp_utc": now_iso,
                "valid_hours": 24.0,
                "mic_covered": False,
                "leq16_work_dBA": 78.0,
                "leq8_sleep_dBA": 65.0,   # > 62 dBA -> Red
                "lmax_dBA": 96.0,
                "peak_dB": 132.0,
                "dose_24h_pct": 135.0,    # D > 100% -> Red
                "history_5_leq8_dBA": [48.0, 52.0, 56.0, 61.0, 65.0],
                "history_5_timestamps": ts_60d_5,
            },
            "aco03_audiogram": {
                "timestamp_utc": now_iso,
                "ambient_above_nc40": False,
                "max_repeat_diff_dB": 5.0,
                "retest_confirmed": True,
                # Right ear 2/3/4 kHz shifts: (25-10)=15, (25-12)=13, (25-12)=13 -> avg 13.67 dB >= 10 dB confirmed -> Red
                "right_ear_dB": {500: 15.0, 1000: 15.0, 2000: 25.0, 3000: 25.0, 4000: 25.0, 6000: 30.0},
                "left_ear_dB": {500: 10.0, 1000: 12.0, 2000: 14.0, 3000: 15.0, 4000: 15.0, 6000: 18.0},
                "history_5_sts_dB": [2.0, 4.5, 7.0, 10.5, 13.67],
                "history_5_timestamps": ts_30d_5,
            },
            "atm01_co2": {
                "records_1h": [
                    {"timestamp_utc": ts_1h_5[0], "co2_ppm": 3800.0, "second_sensor_confirmed": True},
                    {"timestamp_utc": ts_1h_5[1], "co2_ppm": 4000.0, "second_sensor_confirmed": True},
                    {"timestamp_utc": ts_1h_5[2], "co2_ppm": 4200.0, "second_sensor_confirmed": True},
                    {"timestamp_utc": ts_1h_5[3], "co2_ppm": 4380.0, "second_sensor_confirmed": True},
                    {"timestamp_utc": ts_1h_5[4], "co2_ppm": 4540.0, "second_sensor_confirmed": True},  # ~3.45 mmHg > 3.0 mmHg -> Red
                ],
                "step_change_1min_ppm": 250.0,
                "step_second_sensor_confirmed": True,
                "mean_7d_ppm": 3880.0,
            },
            "atm02_pressure": {
                "records_1m": [
                    {"timestamp_utc": ts_1m_5[i], "p_sensor1_kPa": 89.0 - 1.25 * i, "p_sensor2_kPa": 88.9 - 1.25 * i, "o2_vol_pct": 20.2, "dpdt_1m_kPa_min": -1.25, "dpdt_10m_kPa_min": -0.95}
                    for i in range(5)  # Dual sensors agree within 0.1 kPa (<=0.5 kPa) + rapid dP/dt -1.25 kPa/min + PIO2 < 127 mmHg -> Fast-Track Red
                ],
            },
            "atm03_thermal": {
                "records_1h": [
                    {"timestamp_utc": ts_1h_5[0], "temp_C": 25.5, "rh_pct": 66.0},
                    {"timestamp_utc": ts_1h_5[1], "temp_C": 26.4, "rh_pct": 70.0},
                    {"timestamp_utc": ts_1h_5[2], "temp_C": 27.2, "rh_pct": 73.0},
                    {"timestamp_utc": ts_1h_5[3], "temp_C": 27.9, "rh_pct": 76.0},
                    {"timestamp_utc": ts_1h_5[4], "temp_C": 28.5, "rh_pct": 78.0},  # Outside 18-27 C & 25-75% health envelope -> Red
                ],
            },
            "atm04_voc": {
                "timestamp_utc": now_iso,
                "internal_cal_passed": True,
                "combustion_alarm": False,
                "ammonia_alarm": True,    # Ammonia alarm -> Fast-Track Red
                "compounds": [
                    {"name": "ammonia", "conc_mg_m3": 31.9, "smac_mg_m3": 22.0, "duration": "24h"},  # 1.45 SMAC -> Red
                    {"name": "carbon_monoxide", "conc_mg_m3": 14.0, "smac_mg_m3": 17.0, "duration": "24h"},
                ],
                "history_5_smac_ratio": [0.30, 0.55, 0.85, 1.15, 1.45],
                "history_5_timestamps": _make_timestamps_utc(now_iso, 5, 360.0),
            },
            "atm05_water": {
                "timestamp_utc": now_iso,
                "water_source": "WPA_dispenser",
                "std_cal_passed": True,
                "toc_mg_L": 3.8,          # > 3.0 mg/L -> Red
                "iodine_mg_L": 0.28,      # > 0.2 mg/L -> Red
                "silver_ug_L": 560.0,     # > 500 ug/L -> Red
                "history_5_toc_mg_L": [1.4, 2.0, 2.6, 3.2, 3.8],
                "history_5_timestamps": ts_7d_5,
            },
            "atm06_microbial": {
                "timestamp_utc": now_iso,
                "incubation_complete": True,
                "condensation_spread": False,
                "blank_present": True,
                "air_bacteria_cfu_m3": 1250.0,         # >= 1000 CFU/m3 -> Red
                "air_fungi_cfu_m3": 115.0,             # >= 100 CFU/m3 -> Red
                "surface_bacteria_cfu_100cm2": 11200.0,
                "surface_fungi_cfu_100cm2": 105.0,
                "water_heterotrophic_cfu_mL": 62.0,    # >= 50 CFU/mL -> Red
                "water_coliform_100mL_detected": True, # Coliform detected -> Red
                "water_fungi_100mL_detected": False,
                "history_5_limit_ratio": [0.30, 0.55, 0.80, 1.02, 1.25],
                "history_5_timestamps": ts_90d_5,
            },
            "atm07_particulates": {
                "records_1h": [
                    {"timestamp_utc": ts_1h_5[i], "total_dust_mg_m3": 2.0 + 0.35 * i, "respirable_pm25_mg_m3": 0.7 + 0.12 * i, "lunar_dust_twa_mg_m3": 0.36, "self_clean_active": False, "sensor_rated_max_mg_m3": 10.0}
                    for i in range(5)  # Total = 3.4 mg/m3 (>=3), PM2.5 = 1.18 (>=1), Lunar = 0.36 (>=0.3) -> Red
                ],
            },
            "iso01_sleep": {
                "nights": [
                    {"timestamp_utc": ts_1d_7[0], "tst_h": 7.0, "self_report_h": 7.1, "wear_time_pct": 95.0},
                    {"timestamp_utc": ts_1d_7[1], "tst_h": 6.8, "self_report_h": 6.9, "wear_time_pct": 94.0},
                    {"timestamp_utc": ts_1d_7[2], "tst_h": 6.4, "self_report_h": 6.5, "wear_time_pct": 93.0},
                    {"timestamp_utc": ts_1d_7[3], "tst_h": 5.9, "self_report_h": 6.0, "wear_time_pct": 95.0},
                    {"timestamp_utc": ts_1d_7[4], "tst_h": 5.5, "self_report_h": 5.7, "wear_time_pct": 96.0},
                    {"timestamp_utc": ts_1d_7[5], "tst_h": 5.3, "self_report_h": 5.5, "wear_time_pct": 94.0},
                    {"timestamp_utc": ts_1d_7[6], "tst_h": 5.1, "self_report_h": 5.2, "wear_time_pct": 95.0},  # < 6 h for 4 consecutive nights (>=3) -> Red
                ],
            },
            "iso02_pvt": {
                "sessions": [
                    {"timestamp_utc": ts_4d_5[0], "response_speed_1_s": 4.15, "lapses": 1, "false_starts": 2, "missed_stimuli_pct": 2.0, "pre_eva": False},
                    {"timestamp_utc": ts_4d_5[1], "response_speed_1_s": 3.95, "lapses": 3, "false_starts": 3, "missed_stimuli_pct": 3.0, "pre_eva": False},
                    {"timestamp_utc": ts_4d_5[2], "response_speed_1_s": 3.80, "lapses": 4, "false_starts": 3, "missed_stimuli_pct": 4.0, "pre_eva": False},
                    {"timestamp_utc": ts_4d_5[3], "response_speed_1_s": 3.55, "lapses": 7, "false_starts": 4, "missed_stimuli_pct": 6.0, "pre_eva": False},
                    {"timestamp_utc": ts_4d_5[4], "response_speed_1_s": 3.40, "lapses": 9, "false_starts": 5, "missed_stimuli_pct": 8.0, "pre_eva": True},  # 2 consecutive < mean-2SD (3.65) AND pre_eva -> Red
                ],
            },
            "iso03_mood": {
                "entries": [
                    {"timestamp_utc": ts_1d_7[i], "vas_stress": 45.0 + 3.5 * i, "bedford_workload": 8 if i == 6 else 6, "poms37_tmd": 28.0, "hopelessness_flag": i == 6, "straight_lined": False, "complete": True}
                    for i in range(7)  # Bedford 8 (>6), 7 consecutive days VAS worse than baseline, hopelessness_flag -> Red (private conf crew choice)
                ],
            },
            "iso04_light": {
                "days": [
                    {"timestamp_utc": ts_1d_7[0], "morning_lux": 220.0, "presleep_lux": 25.0, "midpoint_shift_h": 0.6, "off_wrist": False, "sleeve_covered": False},
                    {"timestamp_utc": ts_1d_7[1], "morning_lux": 200.0, "presleep_lux": 30.0, "midpoint_shift_h": 0.9, "off_wrist": False, "sleeve_covered": False},
                    {"timestamp_utc": ts_1d_7[2], "morning_lux": 180.0, "presleep_lux": 40.0, "midpoint_shift_h": 1.2, "off_wrist": False, "sleeve_covered": False},
                    {"timestamp_utc": ts_1d_7[3], "morning_lux": 150.0, "presleep_lux": 120.0, "midpoint_shift_h": 1.5, "off_wrist": False, "sleeve_covered": False},
                    {"timestamp_utc": ts_1d_7[4], "morning_lux": 120.0, "presleep_lux": 140.0, "midpoint_shift_h": 1.8, "off_wrist": False, "sleeve_covered": False},
                    {"timestamp_utc": ts_1d_7[5], "morning_lux": 100.0, "presleep_lux": 155.0, "midpoint_shift_h": 2.1, "off_wrist": False, "sleeve_covered": False},
                    {"timestamp_utc": ts_1d_7[6], "morning_lux": 90.0, "presleep_lux": 165.0, "midpoint_shift_h": 2.4, "off_wrist": False, "sleeve_covered": False},  # >= 3 consecutive Yellow nights + ISO-01 Red + shift 2.4 h (> 2 h) -> Red
                ],
            },
        }

    # Default: "green" scenario
    return {
        "scenario": "green",
        "crew_id": "C002",
        "mission_day": 124,
        "mission_length_days": 180,
        "timestamp_utc": now_iso,
        "location": "Columbus",
        "data_source": "SIMULATED",
        # Flat Role-1 compatibility keys
        "co2_sensor_stuck_hours": 0.0,
        "dose_rate_uGy_h": 4.10,
        "saa_pass": False,
        "career_dose_mSv": 152.0,
        "proton_flux_10mev_pfu": 1.8,
        "spe_alert": False,
        "module_spl_dBA": 54.2,
        "crew_leq8_dBA": 45.0,
        "daily_noise_dose_pct": 28.0,
        "ppco2_1h_mmHg": 1.85,
        "ppco2_7d_mmHg": 1.80,
        "p_total_kPa": 101.3,
        "pio2_mmHg": 159.8,
        "dpdt_kPa_per_min": 0.0,
        "temp_C": 22.3,
        "rh_pct": 45.0,
        "max_smac_ratio": 0.18,
        "ammonia_or_fire_alarm": False,
        "sleep_tst_h": 7.3,
        "pvt_speed_1_per_s": 4.28,
        "workload_bedford": 2.0,
        "stress_vas": 22.0,
        # Structured 17-card inputs (all Green)
        "rad01_records": [
            {"timestamp_utc": ts_1h_5[0], "module": "Columbus", "dose_rate_uGy_h": 4.02, "lat_deg": 18.0, "lon_deg": 40.0, "second_detector_confirmed": True},
            {"timestamp_utc": ts_1h_5[1], "module": "Columbus", "dose_rate_uGy_h": 4.08, "lat_deg": 32.0, "lon_deg": 75.0, "second_detector_confirmed": True},
            {"timestamp_utc": ts_1h_5[2], "module": "Columbus", "dose_rate_uGy_h": 4.05, "lat_deg": 46.0, "lon_deg": 110.0, "second_detector_confirmed": True},
            {"timestamp_utc": ts_1h_5[3], "module": "Columbus", "dose_rate_uGy_h": 4.12, "lat_deg": 34.0, "lon_deg": 145.0, "second_detector_confirmed": True},
            {"timestamp_utc": ts_1h_5[4], "module": "Columbus", "dose_rate_uGy_h": 4.10, "lat_deg": 10.0, "lon_deg": 175.0, "second_detector_confirmed": True},
        ],
        "rad02_daily": {
            "timestamp_utc": now_iso,
            "career_prior_mSv": 124.0,
            "mission_cum_mSv": 28.0,   # Total 152 mSv < 300 mSv -> Green
            "single_spe_mSv": 0.0,
            "occupancy_hours": {"Columbus": 16.0, "Harmony": 8.0},
            "module_dose_rates_uGy_h": {"Columbus": 4.10, "Harmony": 4.25},
            "history_5d_career_mSv": [151.1, 151.3, 151.5, 151.8, 152.0],
            "history_5d_timestamps": ts_1d_7[-5:],
        },
        "rad03_goes": {
            "age_hours": 0.05,
            "swpc_warning": False,
            "primary_records": [
                {"time_tag": ts_5m_5[0], "satellite": "GOES-18", "flux_10mev": 1.7, "flux_100mev": 0.05},
                {"time_tag": ts_5m_5[1], "satellite": "GOES-18", "flux_10mev": 1.8, "flux_100mev": 0.05},
                {"time_tag": ts_5m_5[2], "satellite": "GOES-18", "flux_10mev": 1.7, "flux_100mev": 0.04},
                {"time_tag": ts_5m_5[3], "satellite": "GOES-18", "flux_10mev": 1.8, "flux_100mev": 0.05},
                {"time_tag": ts_5m_5[4], "satellite": "GOES-18", "flux_10mev": 1.8, "flux_100mev": 0.05},
            ],
            "secondary_records": [],
        },
        "aco01_survey": {
            "timestamp_utc": now_iso,
            "area_type": "work",
            "mission_duration_days": 180,
            "pre_cal_dB": 94.0,
            "post_cal_dB": 94.1,
            "lab_cal_age_months": 4,
            "spl_dBA": 54.2,
            "impulse_peak_dB": 96.0,
            "tonal_margin_dB": 15.0,
            "octave_bands_dB": {63: 63.0, 125: 57.0, 250: 52.0, 500: 49.0, 1000: 47.0, 2000: 44.0, 4000: 41.0, 8000: 38.0},
            "history_5_spl_dBA": [54.1, 54.3, 54.0, 54.2, 54.2],
            "history_5_timestamps": ts_30d_5,
        },
        "aco02_dosimetry": {
            "timestamp_utc": now_iso,
            "valid_hours": 23.8,
            "mic_covered": False,
            "leq16_work_dBA": 55.5,
            "leq8_sleep_dBA": 45.0,
            "lmax_dBA": 76.0,
            "peak_dB": 108.0,
            "dose_24h_pct": 28.0,
            "history_5_leq8_dBA": [44.8, 45.1, 44.9, 45.2, 45.0],
            "history_5_timestamps": ts_60d_5,
        },
        "aco03_audiogram": {
            "timestamp_utc": now_iso,
            "ambient_above_nc40": False,
            "max_repeat_diff_dB": 5.0,
            "retest_confirmed": True,
            "right_ear_dB": {500: 10.0, 1000: 10.0, 2000: 10.0, 3000: 12.0, 4000: 12.0, 6000: 15.0},
            "left_ear_dB": {500: 10.0, 1000: 10.0, 2000: 10.0, 3000: 12.0, 4000: 12.0, 6000: 15.0},
            "history_5_sts_dB": [0.0, 0.5, 0.0, 0.5, 0.0],
            "history_5_timestamps": ts_30d_5,
        },
        "atm01_co2": {
            "records_1h": [
                {"timestamp_utc": ts_1h_5[0], "co2_ppm": 2410.0, "second_sensor_confirmed": True},
                {"timestamp_utc": ts_1h_5[1], "co2_ppm": 2425.0, "second_sensor_confirmed": True},
                {"timestamp_utc": ts_1h_5[2], "co2_ppm": 2420.0, "second_sensor_confirmed": True},
                {"timestamp_utc": ts_1h_5[3], "co2_ppm": 2435.0, "second_sensor_confirmed": True},
                {"timestamp_utc": ts_1h_5[4], "co2_ppm": 2434.0, "second_sensor_confirmed": True},  # ~1.85 mmHg
            ],
            "step_change_1min_ppm": 35.0,
            "step_second_sensor_confirmed": True,
            "mean_7d_ppm": 2368.0,  # ~1.80 mmHg < 2.5 mmHg
        },
        "atm02_pressure": {
            "records_1m": [
                {"timestamp_utc": ts_1m_5[i], "p_sensor1_kPa": 101.3, "p_sensor2_kPa": 101.3, "o2_vol_pct": 21.0, "dpdt_1m_kPa_min": 0.0, "dpdt_10m_kPa_min": 0.0}
                for i in range(5)  # PIO2 = 0.21 * (759.8 - 47) = 149.7 mmHg (139-168 mmHg) & P within +-1% -> Green
            ],
        },
        "atm03_thermal": {
            "records_1h": [
                {"timestamp_utc": ts_1h_5[0], "temp_C": 22.1, "rh_pct": 44.5},
                {"timestamp_utc": ts_1h_5[1], "temp_C": 22.2, "rh_pct": 44.8},
                {"timestamp_utc": ts_1h_5[2], "temp_C": 22.4, "rh_pct": 45.2},
                {"timestamp_utc": ts_1h_5[3], "temp_C": 22.2, "rh_pct": 44.9},
                {"timestamp_utc": ts_1h_5[4], "temp_C": 22.3, "rh_pct": 45.0},
            ],
        },
        "atm04_voc": {
            "timestamp_utc": now_iso,
            "internal_cal_passed": True,
            "combustion_alarm": False,
            "ammonia_alarm": False,
            "compounds": [
                {"name": "methanol", "conc_mg_m3": 1.62, "smac_mg_m3": 9.0, "duration": "7d"},  # 0.18 SMAC < 0.5
                {"name": "acetone", "conc_mg_m3": 4.5, "smac_mg_m3": 52.0, "duration": "7d"},
            ],
            "history_5_smac_ratio": [0.16, 0.17, 0.18, 0.17, 0.18],
            "history_5_timestamps": _make_timestamps_utc(now_iso, 5, 360.0),
        },
        "atm05_water": {
            "timestamp_utc": now_iso,
            "water_source": "WPA_dispenser",
            "std_cal_passed": True,
            "toc_mg_L": 0.68,
            "iodine_mg_L": 0.12,
            "silver_ug_L": 260.0,
            "history_5_toc_mg_L": [0.65, 0.67, 0.66, 0.69, 0.68],
            "history_5_timestamps": ts_7d_5,
        },
        "atm06_microbial": {
            "timestamp_utc": now_iso,
            "incubation_complete": True,
            "condensation_spread": False,
            "blank_present": True,
            "air_bacteria_cfu_m3": 140.0,
            "air_fungi_cfu_m3": 12.0,
            "surface_bacteria_cfu_100cm2": 950.0,
            "surface_fungi_cfu_100cm2": 10.0,
            "water_heterotrophic_cfu_mL": 6.0,
            "water_coliform_100mL_detected": False,
            "water_fungi_100mL_detected": False,
            "history_5_limit_ratio": [0.12, 0.13, 0.14, 0.13, 0.14],
            "history_5_timestamps": ts_90d_5,
        },
        "atm07_particulates": {
            "records_1h": [
                {"timestamp_utc": ts_1h_5[i], "total_dust_mg_m3": 0.28 + 0.01 * (i % 2), "respirable_pm25_mg_m3": 0.11, "lunar_dust_twa_mg_m3": 0.02, "self_clean_active": False, "sensor_rated_max_mg_m3": 10.0}
                for i in range(5)
            ],
        },
        "iso01_sleep": {
            "nights": [
                {"timestamp_utc": ts_1d_7[i], "tst_h": 7.3 + 0.05 * (i % 2), "self_report_h": 7.4, "wear_time_pct": 95.0}
                for i in range(7)
            ],
        },
        "iso02_pvt": {
            "sessions": [
                {"timestamp_utc": ts_4d_5[i], "response_speed_1_s": 4.26 + 0.02 * (i % 2), "lapses": 1, "false_starts": 2, "missed_stimuli_pct": 2.0, "pre_eva": False}
                for i in range(5)
            ],
        },
        "iso03_mood": {
            "entries": [
                {"timestamp_utc": ts_1d_7[i], "vas_stress": 22.0 + (i % 3), "bedford_workload": 2, "poms37_tmd": 4.0, "hopelessness_flag": False, "straight_lined": False, "complete": True}
                for i in range(7)
            ],
        },
        "iso04_light": {
            "days": [
                {"timestamp_utc": ts_1d_7[i], "morning_lux": 380.0, "presleep_lux": 14.0, "midpoint_shift_h": 0.15, "off_wrist": False, "sleeve_covered": False}
                for i in range(7)
            ],
        },
    }


def export_demo_csvs(target_dir: Optional[Path] = None) -> list[str]:
    """Write all 17 guide CSV/JSON templates to data/cabin_environment/."""
    out_dir = Path(target_dir) if target_dir is not None else DATA_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    green = demo_payload("green")
    written: list[str] = []

    def _save_csv(filename: str, rows: list[dict[str, Any]]) -> None:
        p = out_dir / filename
        pd.DataFrame(rows).to_csv(p, index=False)
        written.append(str(p))

    # 1. rad01_area_dose.csv
    _save_csv("rad01_area_dose.csv", green["rad01_records"])

    # 2. rad02_crew_dose_daily.csv
    r02 = green["rad02_daily"]
    _save_csv(
        "rad02_crew_dose_daily.csv",
        [
            {
                "timestamp_utc": ts,
                "crew_id": "C002",
                "mission_day": 120 + idx,
                "columbus_hours": 16.0,
                "harmony_hours": 8.0,
                "columbus_dose_rate_uGy_h": 4.10,
                "harmony_dose_rate_uGy_h": 4.25,
                "daily_eq_dose_mSv": round(((16.0 * 4.10 + 8.0 * 4.25) * 2.26) / 1000.0, 4),
                "career_dose_mSv": r02["history_5d_career_mSv"][idx],
                "single_spe_mSv": 0.0,
            }
            for idx, ts in enumerate(r02["history_5d_timestamps"])
        ],
    )

    # 3. goes_integral_protons.json (time_tag, satellite, flux, energy)
    goes_rows: list[dict[str, Any]] = []
    for rec in green["rad03_goes"]["primary_records"]:
        goes_rows.append(
            {
                "time_tag": rec["time_tag"],
                "satellite": rec["satellite"],
                "flux": rec["flux_10mev"],
                "energy": ">=10 MeV",
            }
        )
        goes_rows.append(
            {
                "time_tag": rec["time_tag"],
                "satellite": rec["satellite"],
                "flux": rec["flux_100mev"],
                "energy": ">=100 MeV",
            }
        )
    goes_path = out_dir / "goes_integral_protons.json"
    with goes_path.open("w", encoding="utf-8") as fh:
        json.dump(goes_rows, fh, indent=2)
    written.append(str(goes_path))

    # 4. aco01_module_spl.csv
    a01 = green["aco01_survey"]
    aco01_row = {
        "timestamp_utc": a01["timestamp_utc"],
        "location": "Columbus",
        "area_type": a01["area_type"],
        "pre_cal_dB": a01["pre_cal_dB"],
        "post_cal_dB": a01["post_cal_dB"],
        "lab_cal_age_months": a01["lab_cal_age_months"],
        "spl_dBA": a01["spl_dBA"],
        "impulse_peak_dB": a01["impulse_peak_dB"],
        "tonal_margin_dB": a01["tonal_margin_dB"],
    }
    for f_hz, val_db in a01["octave_bands_dB"].items():
        aco01_row[f"hz_{f_hz}_dB"] = val_db
    _save_csv("aco01_module_spl.csv", [aco01_row])

    # 5. aco02_crew_dosimetry.csv
    a02 = green["aco02_dosimetry"]
    _save_csv(
        "aco02_crew_dosimetry.csv",
        [
            {
                "timestamp_utc": a02["timestamp_utc"],
                "crew_id": "C002",
                "valid_hours": a02["valid_hours"],
                "mic_covered": a02["mic_covered"],
                "leq16_work_dBA": a02["leq16_work_dBA"],
                "leq8_sleep_dBA": a02["leq8_sleep_dBA"],
                "lmax_dBA": a02["lmax_dBA"],
                "peak_dB": a02["peak_dB"],
                "dose_24h_pct": a02["dose_24h_pct"],
            }
        ],
    )

    # 6. aco03_audiogram.csv
    a03 = green["aco03_audiogram"]
    aco03_rows = []
    for ear_label, ear_dict in (("right", a03["right_ear_dB"]), ("left", a03["left_ear_dB"])):
        row = {
            "timestamp_utc": a03["timestamp_utc"],
            "crew_id": "C002",
            "ear": ear_label,
            "ambient_above_nc40": a03["ambient_above_nc40"],
            "max_repeat_diff_dB": a03["max_repeat_diff_dB"],
            "retest_confirmed": a03["retest_confirmed"],
        }
        for f_hz, val_db in ear_dict.items():
            row[f"hz_{f_hz}_dB"] = val_db
        aco03_rows.append(row)
    _save_csv("aco03_audiogram.csv", aco03_rows)

    # 7. atm01_co2.csv
    _save_csv(
        "atm01_co2.csv",
        [
            {
                "timestamp_utc": rec["timestamp_utc"],
                "location": "Columbus",
                "co2_ppm": rec["co2_ppm"],
                "ppco2_1h_mmHg": round(rec["co2_ppm"] * 1e-6 * 760.0, 3),
                "ppco2_7d_mmHg": 1.80,
                "second_sensor_confirmed": rec["second_sensor_confirmed"],
            }
            for rec in green["atm01_co2"]["records_1h"]
        ],
    )

    # 8. atm02_pressure_o2.csv
    _save_csv("atm02_pressure_o2.csv", green["atm02_pressure"]["records_1m"])

    # 9. atm03_thermal.csv
    _save_csv("atm03_thermal.csv", green["atm03_thermal"]["records_1h"])

    # 10. atm04_voc.csv
    a04 = green["atm04_voc"]
    _save_csv(
        "atm04_voc.csv",
        [
            {
                "timestamp_utc": a04["timestamp_utc"],
                "location": "Columbus",
                "compound": c["name"],
                "conc_mg_m3": c["conc_mg_m3"],
                "smac_mg_m3": c["smac_mg_m3"],
                "duration": c["duration"],
                "internal_cal_passed": a04["internal_cal_passed"],
                "combustion_alarm": a04["combustion_alarm"],
                "ammonia_alarm": a04["ammonia_alarm"],
            }
            for c in a04["compounds"]
        ],
    )

    # 11. atm05_water_chem.csv (note: below-DL values stored as "< DL", never 0)
    a05 = green["atm05_water"]
    _save_csv(
        "atm05_water_chem.csv",
        [
            {
                "timestamp_utc": a05["timestamp_utc"],
                "water_source": a05["water_source"],
                "std_cal_passed": a05["std_cal_passed"],
                "toc_mg_L": a05["toc_mg_L"],
                "iodine_mg_L": "< DL",
                "silver_ug_L": a05["silver_ug_L"],
            }
        ],
    )

    # 12. atm06_microbial.csv
    a06 = green["atm06_microbial"]
    _save_csv("atm06_microbial.csv", [a06])

    # 13. atm07_particulates.csv
    _save_csv("atm07_particulates.csv", green["atm07_particulates"]["records_1h"])

    # 14. iso01_sleep.csv — simulate N(6.09 h, 0.67 h) reference column + crew nights
    rng = np.random.default_rng(42)
    sim_sleep = rng.normal(6.09, 0.67, size=len(green["iso01_sleep"]["nights"]))
    _save_csv(
        "iso01_sleep.csv",
        [
            {
                "timestamp_utc": n["timestamp_utc"],
                "crew_id": "C002",
                "tst_h": n["tst_h"],
                "iss_ref_sim_tst_h": round(float(sim_sleep[idx]), 2),
                "self_report_h": n["self_report_h"],
                "wear_time_pct": n["wear_time_pct"],
            }
            for idx, n in enumerate(green["iso01_sleep"]["nights"])
        ],
    )

    # 15. iso02_pvt.csv
    _save_csv(
        "iso02_pvt.csv",
        [{"crew_id": "C002", **s} for s in green["iso02_pvt"]["sessions"]],
    )

    # 16. iso03_mood.csv (never store journal text centrally)
    _save_csv(
        "iso03_mood.csv",
        [
            {
                "timestamp_utc": e["timestamp_utc"],
                "crew_id": "C002",
                "vas_stress": e["vas_stress"],
                "bedford_workload": e["bedford_workload"],
                "poms37_tmd": e["poms37_tmd"],
                "hopelessness_flag": e["hopelessness_flag"],
                "straight_lined": e["straight_lined"],
                "complete": e["complete"],
            }
            for e in green["iso03_mood"]["entries"]
        ],
    )

    # 17. iso04_light.csv
    _save_csv(
        "iso04_light.csv",
        [{"crew_id": "C002", **d} for d in green["iso04_light"]["days"]],
    )

    return written


