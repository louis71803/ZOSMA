"""Static NASA-STD-3001 thresholds, cadences, trend horizons, and explicit Rule Table for Role 6."""

from __future__ import annotations

from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cabin_environment"

CARD_IDS: tuple[str, ...] = (
    "RAD-01", "RAD-02", "RAD-03",
    "ACO-01", "ACO-02", "ACO-03",
    "ATM-01", "ATM-02", "ATM-03", "ATM-04", "ATM-05", "ATM-06", "ATM-07",
    "ISO-01", "ISO-02", "ISO-03", "ISO-04",
)

STATUS_SEVERITY: dict[str, int] = {
    "rejected": -2,
    "no_data": -1,
    "green": 0,
    "yellow": 1,
    "red": 2,
}

# Octave band center frequencies (Hz) and NASA-STD-3001 NC-50 / NC-40 dB SPL limits [V2 6078/6079]
OCTAVE_FREQS_HZ: tuple[int, ...] = (63, 125, 250, 500, 1000, 2000, 4000, 8000)
NC_50_LIMITS_DB: dict[int, float] = {63: 71.0, 125: 64.0, 250: 58.0, 500: 54.0, 1000: 51.0, 2000: 49.0, 4000: 48.0, 8000: 47.0}
NC_40_LIMITS_DB: dict[int, float] = {63: 64.0, 125: 56.0, 250: 50.0, 500: 45.0, 1000: 41.0, 2000: 39.0, 4000: 38.0, 8000: 37.0}
AUDIO_FREQS_HZ: tuple[int, ...] = (500, 1000, 2000, 3000, 4000, 6000)

# Nominal cadence (hours) per card; staleness > 3x cadence -> no_data
NOMINAL_CADENCE_HOURS: dict[str, float] = {
    "RAD-01": 1.0,
    "RAD-02": 24.0,
    "RAD-03": 5.0 / 60.0,       # 5-min cadence (additionally >30 min dropped in L0)
    "ACO-01": 720.0,            # monthly (30 d)
    "ACO-02": 1440.0,           # every 60 d
    "ACO-03": 720.0,            # periodic / monthly check
    "ATM-01": 1.0,
    "ATM-02": 1.0 / 60.0,       # 1-min cadence (or 10-min telemetry block)
    "ATM-03": 1.0,
    "ATM-04": 6.0,
    "ATM-05": 168.0,            # weekly TOCA
    "ATM-06": 2160.0,           # quarterly (90 d; monthly 720 h for water coliforms)
    "ATM-07": 1.0,
    "ISO-01": 24.0,
    "ISO-02": 96.0,             # every 4th day
    "ISO-03": 24.0,
    "ISO-04": 24.0,
}

# Layer 3 OLS trend horizons in hours
TREND_HORIZON_HOURS: dict[str, float] = {
    "RAD-01": 6.0,
    "RAD-02": 1344.0,           # remaining mission days (default 56 d * 24 h; overridden dynamically)
    "RAD-03": 1.0,
    "ACO-01": 720.0,            # next scheduled monthly session
    "ACO-02": 1440.0,           # next scheduled 60-day session
    "ACO-03": 720.0,            # next scheduled audiogram session
    "ATM-01": 24.0,
    "ATM-02": 1.0,
    "ATM-03": 12.0,
    "ATM-04": 24.0,
    "ATM-05": 720.0,            # 30 days
    "ATM-06": 2160.0,           # next scheduled quarterly session
    "ATM-07": 24.0,
    "ISO-01": 336.0,            # 14 days
    "ISO-02": 336.0,            # 14 days
    "ISO-03": 336.0,            # 14 days
    "ISO-04": 336.0,            # 14 days
}

# Rule Table: (rule_id, module_id, layer, comparator, value, unit, window, horizon, source_tag, ref)
RULE_TABLE: tuple[tuple[str, str, str, str, Any, str, str, str, str, str], ...] = (
    # RAD-01
    ("RAD-01-L0", "RAD-01", "L0", "range_saa_spike", "dose>0; <=1000x_med_unconfirmed; exclude_SAA(-50..0,-90..40)", "uGy/h", "1h", "3h_stale", "LIT", "LIT:DOSTEL-Columbus-SAA-QC"),
    ("RAD-01-L1", "RAD-01", "L1", ">", "10x_median_AND_RAD03>=S1", "ratio", "1h", "immediate", "TEAM", "TEAM:RAD-01-demo-red-placeholder"),
    ("RAD-01-L2", "RAD-01", "L2", ">", 2.0, "x_7d_median", "1h_outside_SAA", "none", "LIT", "LIT:Columbus-195-360uGy/d-7d-median"),
    ("RAD-01-L3", "RAD-01", "L3", "ols_ttr<=", 6.0, "h", "5_pts", "6h", "TEAM", "TEAM:5pt-OLS-R2>=0.6"),
    # RAD-02
    ("RAD-02-L0", "RAD-02", "L0", "occupancy_sum", "24+-0.5h; missing<=4h", "h", "24h", "72h_stale", "LIT", "LIT:DOSTEL-647/286-Q=2.26"),
    ("RAD-02-L1", "RAD-02", "L1", ">", "300_Y_480_R_600_limit_250_SPE", "mSv", "career/SPE", "mission", "STD", "STD:NASA-STD-3001-V1-4030/4031"),
    ("RAD-02-L3", "RAD-02", "L3", "ols_ttr<=", "remaining_mission_days", "d", "5_pts", "mission_end", "STD", "STD:NASA-STD-3001-V1-4030-projection"),
    # RAD-03
    ("RAD-03-L0", "RAD-03", "L0", "flux_fresh_persist", "flux>0; age<=30m; secondary_fallback; 3x5m_SPE", "pfu", "5m", "30m_stale", "STD", "STD:NOAA-SWPC-GOES-SEP"),
    ("RAD-03-L1", "RAD-03", "L1", ">=", "10_pfu_S1_Y; 100_pfu_S2_AND_RAD01_rising_R", "pfu", "3x5m", "immediate", "STD", "STD:NOAA-SWPC-S1/S2-SEP"),
    ("RAD-03-L3", "RAD-03", "L3", "log10_ols_ttr<=", 1.0, "h", "5_pts", "1h", "LIT", "LIT:GOES-log10-flux-OLS"),
    # ACO-01
    ("ACO-01-L0", "ACO-01", "L0", "slm_cal", "drift<=0.5dB; lab_cal<=12mo", "dB", "survey", "90d_stale", "STD", "STD:NASA-STD-3001-V2-6078-QC"),
    ("ACO-01-L1", "ACO-01", "L1", ">=", "NC50_work/NC40_sleep_Y; 85dBA_or_140dB_peak_R", "dBA/dB", "survey", "next_session", "STD", "STD:NASA-STD-3001-V2-6078/6079/6080"),
    ("ACO-01-L2", "ACO-01", "L2", ">", "7d_or_prev_survey_median", "dBA", "7d", "next_session", "LIT", "LIT:ISS-Acoustic-Survey-Baseline"),
    ("ACO-01-L3", "ACO-01", "L3", "ols_ttr<=", 720.0, "h", "5_pts", "next_session", "TEAM", "TEAM:5pt-OLS-next-survey"),
    # ACO-02
    ("ACO-02-L0", "ACO-02", "L0", "dosimeter_qc", "valid_h>=20; mic_covered==False", "h", "24h", "180d_stale", "STD", "STD:NASA-STD-3001-V2-6115-QC"),
    ("ACO-02-L1", "ACO-02", "L1", ">", "LEQ8>50_or_D>50_Y; LEQ8>62_or_D>100_R", "dBA/%", "24h", "next_session", "STD", "STD:NASA-STD-3001-V2-6115"),
    ("ACO-02-L2", "ACO-02", "L2", ">", "mean+1SD_Y; 2x_mean+2SD_R", "dBA", "preflight", "next_session", "TEAM", "TEAM:Personal-Baseline-SD"),
    ("ACO-02-L3", "ACO-02", "L3", "ols_ttr<=", 1440.0, "h", "5_pts", "next_session", "TEAM", "TEAM:5pt-OLS-next-dosimetry"),
    # ACO-03
    ("ACO-03-L0", "ACO-03", "L0", "audiogram_qc", "ambient<=NC-40; repeat_diff<=10dB; retest_confirmed", "dB", "session", "90d_stale", "STD", "STD:OOHA-OSHA-STS-QC"),
    ("ACO-03-L1", "ACO-03", "L1", ">=", "single>=15dB_Y; avg_2_3_4kHz>=10dB_confirmed_R", "dB", "session", "next_session", "STD", "STD:OSHA-STS-NASA-OOHA"),
    ("ACO-03-L2", "ACO-03", "L2", ">", "mean+1SD_Y; 2x_mean+2SD_R", "dB", "preflight", "next_session", "LIT", "LIT:Preflight-Audiogram-Baseline"),
    ("ACO-03-L3", "ACO-03", "L3", "ols_ttr<=", 720.0, "h", "5_pts", "next_session", "TEAM", "TEAM:5pt-OLS-next-audiogram"),
    # ATM-01
    ("ATM-01-L0", "ATM-01", "L0", "co2_qc", "200..20000ppm; step<=1500ppm/m_unconfirmed; stuck<24h", "ppm", "1h", "3h_stale", "LIT", "LIT:ISS-MCA-RR1-Stuck-Sensor-QC"),
    ("ATM-01-L1", "ATM-01", "L1", ">", "7d>=2.5_or_1h_2.5..3.0_Y; 1h>3.0_R", "mmHg", "1h/7d", "24h", "STD", "STD:NASA-STD-3001-V2-6004"),
    ("ATM-01-L2", "ATM-01", "L2", ">", "7d_module_median+0.5", "mmHg", "7d", "24h", "LIT", "LIT:ISS-CDRA-Module-Median"),
    ("ATM-01-L3", "ATM-01", "L3", "ols_ttr<=", 24.0, "h", "5_pts", "24h", "TEAM", "TEAM:5pt-OLS-24h"),
    # ATM-02
    ("ATM-02-L0", "ATM-02", "L0", "pressure_qc", "0..110kPa; dual_sensor_diff<=0.5kPa_for_leak", "kPa", "1m", "3m_stale", "STD", "STD:NASA-STD-3001-V2-6003-QC"),
    ("ATM-02-L1", "ATM-02", "L1", "bounds", "PIO2_127..139_Y; PIO2<127_or_O2>23.5%_or_P_out_34.5..103_or_rapid_dPdt_R", "mmHg/kPa", "1m/10m", "1h", "STD", "STD:NASA-STD-3001-V2-6003/6006"),
    ("ATM-02-L2", "ATM-02", "L2", "setpoint_dev", "P_outside_+-1%_of_101.3kPa_or_slow_decay", "kPa", "10m", "1h", "STD", "STD:Nominal-101.3kPa-Setpoint"),
    ("ATM-02-L3", "ATM-02", "L3", "ols_ttr<=", 1.0, "h", "5_pts", "1h", "TEAM", "TEAM:5pt-OLS-1h"),
    # ATM-03
    ("ATM-03-L0", "ATM-03", "L0", "thc_qc", "T_5..45C; RH_0..100%; flatline<=6h", "C/%", "1h", "3h_stale", "STD", "STD:THC-Sensor-QC"),
    ("ATM-03-L1", "ATM-03", "L1", "envelope", "outside_20..25C_30..60%_Y; outside_18..27C_25..75%_R", "C/%", "1h", "12h", "STD", "STD:NASA-STD-3001-V2-6012/6013"),
    ("ATM-03-L2", "ATM-03", "L2", "median_dev", "dev_from_7d_median", "C/%", "7d", "12h", "LIT", "LIT:Module-THC-7d-Median"),
    ("ATM-03-L3", "ATM-03", "L3", "ols_ttr<=", 12.0, "h", "5_pts", "12h", "TEAM", "TEAM:5pt-OLS-12h"),
    # ATM-04
    ("ATM-04-L0", "ATM-04", "L0", "aqm_qc", "internal_cal==True; conc>=0", "SMAC_ratio", "6h", "18h_stale", "STD", "STD:AQM-GCMS-QC"),
    ("ATM-04-L1", "ATM-04", "L1", ">=", "0.5_SMAC_Y; 1.0_SMAC_or_fire_NH3_alarm_R", "SMAC_ratio", "duration", "24h", "STD", "STD:NASA-STD-3001-V2-6050-SMAC"),
    ("ATM-04-L2", "ATM-04", "L2", ">", "2x_7d_module_median", "SMAC_ratio", "7d", "24h", "LIT", "LIT:AQM-Trace-Gas-Baseline"),
    ("ATM-04-L3", "ATM-04", "L3", "ols_ttr<=", 24.0, "h", "5_pts", "24h", "TEAM", "TEAM:5pt-OLS-24h"),
    # ATM-05
    ("ATM-05-L0", "ATM-05", "L0", "toca_qc", "std_cal==True; below_DL_stored_as_<DL_never_0", "mg/L", "weekly", "21d_stale", "STD", "STD:TOCA-Water-QC"),
    ("ATM-05-L1", "ATM-05", "L1", "bounds", "TOC_1.5..3_or_Ag<100_Y; TOC>3_or_I2>0.2_or_Ag>500_R", "mg/L_ug/L", "weekly", "30d", "STD", "STD:NASA-STD-3001-V2-6026-Potable-Water"),
    ("ATM-05-L2", "ATM-05", "L2", ">", "source_7d_median_shift", "mg/L", "source", "30d", "LIT", "LIT:WPA-Potable-Source-Baseline"),
    ("ATM-05-L3", "ATM-05", "L3", "ols_ttr<=", 720.0, "h", "5_pts", "30d", "TEAM", "TEAM:5pt-OLS-30d"),
    # ATM-06
    ("ATM-06-L0", "ATM-06", "L0", "plate_qc", "incubation_complete; no_condensation_spread; blank_present", "CFU", "quarterly", "270d_stale", "STD", "STD:ISS-Microbial-Assay-QC"),
    ("ATM-06-L1", "ATM-06", "L1", ">=", "0.5_limit_Y; 1.0_limit_or_any_coliform_fungi_100mL_R", "limit_ratio", "sample", "next_session", "STD", "STD:NASA-STD-3001-V2-6059-Microbial"),
    ("ATM-06-L2", "ATM-06", "L2", ">", "2x_module_median_ratio", "limit_ratio", "7d/hist", "next_session", "LIT", "LIT:ISS-Microbial-Baseline"),
    ("ATM-06-L3", "ATM-06", "L3", "ols_ttr<=", 2160.0, "h", "5_pts", "next_session", "TEAM", "TEAM:5pt-OLS-next-quarterly"),
    # ATM-07
    ("ATM-07-L0", "ATM-07", "L0", "particulate_qc", "self_clean==False; <=sensor_rated_range", "mg/m3", "1h", "3h_stale", "TEAM", "TEAM:Simulated-Optical-Dust-QC"),
    ("ATM-07-L1", "ATM-07", "L1", ">=", "0.5_limit_Y; total>=3_or_PM2.5>=1_or_lunar>=0.3_R", "mg/m3", "1h/TWA", "24h", "STD", "STD:NASA-STD-3001-V2-6052-Lunar-Dust"),
    ("ATM-07-L2", "ATM-07", "L2", ">", "2x_7d_module_median", "limit_ratio", "7d", "24h", "TEAM", "TEAM:Simulated-Particulate-7d-Median"),
    ("ATM-07-L3", "ATM-07", "L3", "ols_ttr<=", 24.0, "h", "5_pts", "24h", "TEAM", "TEAM:5pt-OLS-24h"),
    # ISO-01
    ("ISO-01-L0", "ISO-01", "L0", "actiwatch_qc", "wear_pct>=80%; flag_log_diff>2h", "h", "24h", "72h_stale", "LIT", "LIT:Actiwatch-Sleep-QC-N(6.09,0.67)"),
    ("ISO-01-L1", "ISO-01", "L1", "<", "6..7h_or_1night<6h_Y; <6h_for_>=3_consec_nights_R", "h", "nightly", "14d", "STD", "STD:NASA-STD-3001-V1-5001-Sleep"),
    ("ISO-01-L2", "ISO-01", "L2", "<", "mean-1SD_Y; 2_consec_mean-2SD_R", "h", "preflight", "14d", "LIT", "LIT:Personal-Sleep-Baseline"),
    ("ISO-01-L3", "ISO-01", "L3", "ols_ttr<=", 336.0, "h", "5_pts", "14d", "TEAM", "TEAM:5pt-OLS-14d"),
    # ISO-02
    ("ISO-02-L0", "ISO-02", "L0", "pvt_qc", "false_starts<=10; missed_pct<=20%", "1/s", "3m_test", "12d_stale", "LIT", "LIT:PVT-B-Basner-Dinges-QC"),
    ("ISO-02-L1", "ISO-02", "L1", "<", "speed<base-1SD_Y; 2_consec_<base-2SD_or_preEVA_R", "1/s", "test", "14d", "LIT", "LIT:PVT-B-Alertness-Thresholds"),
    ("ISO-02-L2", "ISO-02", "L2", "<", "mean-1SD_Y; 2_consec_mean-2SD_R", "1/s", "preflight", "14d", "LIT", "LIT:Personal-PVT-Baseline"),
    ("ISO-02-L3", "ISO-02", "L3", "ols_ttr<=", 336.0, "h", "5_pts", "14d", "TEAM", "TEAM:5pt-OLS-14d"),
    # ISO-03
    ("ISO-03-L0", "ISO-03", "L0", "survey_qc", "not_straight_lined; complete; strip_journal_text", "score", "daily", "72h_stale", "LIT", "LIT:Behavioral-Survey-Privacy-QC"),
    ("ISO-03-L1", "ISO-03", "L1", ">", "Bedford_4..6_or_3d_VAS_Y; Bedford>6_or_7d_VAS_or_hopeless_R", "Bedford/VAS", "daily", "14d", "STD", "STD:NASA-STD-3001-V2-5007-Bedford"),
    ("ISO-03-L2", "ISO-03", "L2", ">", "mean+1SD_Y; 2_consec_mean+2SD_R", "VAS", "preflight", "14d", "LIT", "LIT:Personal-Mood-Stress-Baseline"),
    ("ISO-03-L3", "ISO-03", "L3", "ols_ttr<=", 336.0, "h", "5_pts", "14d", "TEAM", "TEAM:5pt-OLS-14d"),
    # ISO-04
    ("ISO-04-L0", "ISO-04", "L0", "light_qc", "off_wrist==False; sleeve_covered==False", "lux", "24h", "72h_stale", "LIT", "LIT:Actiwatch-Light-Sensor-QC"),
    ("ISO-04-L1", "ISO-04", "L1", ">", "presleep>100lux_>=2/7d_or_shift>1h_Y; >=3d_with_ISO01_YR_or_shift>2h_R", "lux/h", "7d", "14d", "STD", "STD:NASA-STD-3001-V2-6086-Lighting"),
    ("ISO-04-L2", "ISO-04", "L2", ">", "mean+1SD_Y; 2_consec_mean+2SD_R", "h", "preflight", "14d", "LIT", "LIT:Personal-Circadian-Phase-Baseline"),
    ("ISO-04-L3", "ISO-04", "L3", "ols_ttr<=", 336.0, "h", "5_pts", "14d", "TEAM", "TEAM:5pt-OLS-14d"),
)


def get_rule_table_dicts() -> list[dict[str, Any]]:
    """Return RULE_TABLE as a list of structured dictionaries."""
    keys = ("rule_id", "module_id", "layer", "comparator", "value", "unit", "window", "horizon", "source_tag", "ref")
    return [dict(zip(keys, row)) for row in RULE_TABLE]
