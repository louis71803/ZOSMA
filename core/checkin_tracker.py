"""Crew Daily Vitals & Scheduled Check-In Tracker (Role 1).

Provides:
1. Canonical field schemas for Flight Mode Crew Daily Vitals, Scheduled
   Subsystem Check-ins, and Developer Mode Telemetry Overrides.
2. Developer Mode recommended reference ranges (Green / Yellow / Red) and
   one-click test presets for every input field.
3. Time-series persistence helpers (`checkin_series` in runtime_session.json)
   and trajectory/slope synchronization across all 5 domain modules.
"""

from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np

from core.schema import ModuleEvaluationResult

SYMPTOM_OPTIONS: list[dict[str, str]] = [
    {"id": "fatigue", "en": "Fatigue", "zh": "疲倦"},
    {"id": "headache", "en": "Headache", "zh": "頭痛"},
    {"id": "nasal_congestion", "en": "Nasal Congestion", "zh": "鼻塞"},
    {"id": "dizziness", "en": "Dizziness", "zh": "頭暈"},
    {"id": "chills", "en": "Chills", "zh": "發冷"},
    {"id": "fever", "en": "Feverish", "zh": "發熱感"},
    {"id": "vesicular_rash", "en": "Skin Rash / Vesicles", "zh": "皮疹/水泡"},
    {"id": "nausea", "en": "Nausea / Motion", "zh": "噁心/動暈"},
    {"id": "joint_pain", "en": "Muscle / Joint Ache", "zh": "肌肉關節痠痛"},
]

# Section A: Daily Routine Vitals (Flight Mode + Developer Mode)
DAILY_VITALS_FIELDS: list[dict[str, Any]] = [
    {
        "key": "temp_c",
        "en": "Oral Temperature (°C)",
        "zh": "晨間口腔體溫 (°C)",
        "type": "number",
        "min": 35.0,
        "max": 40.5,
        "step": 0.1,
        "default": 36.7,
        "ref": {
            "green": {"range": "36.1–37.2 °C", "preset": 36.7},
            "yellow": {"range": "37.3–37.9 °C", "preset": 37.6},
            "red": {"range": "≥ 38.0 °C", "preset": 38.5},
        },
    },
    {
        "key": "rest_hr_bpm",
        "en": "Resting Heart Rate (bpm)",
        "zh": "靜息心率 (bpm)",
        "type": "number",
        "min": 35,
        "max": 150,
        "step": 1,
        "default": 65,
        "ref": {
            "green": {"range": "50–79 bpm", "preset": 65},
            "yellow": {"range": "80–99 bpm", "preset": 85},
            "red": {"range": "≥ 100 or ≤ 40 bpm", "preset": 104},
        },
    },
    {
        "key": "sbp_mmHg",
        "en": "Systolic BP (mmHg)",
        "zh": "收縮壓 SBP (mmHg)",
        "type": "number",
        "min": 70,
        "max": 200,
        "step": 1,
        "default": 119,
        "ref": {
            "green": {"range": "96–139 mmHg", "preset": 119},
            "yellow": {"range": "132–139 (≥+2.5SD)", "preset": 135},
            "red": {"range": "≥ 160 or ≥+4SD", "preset": 164},
        },
    },
    {
        "key": "dbp_mmHg",
        "en": "Diastolic BP (mmHg)",
        "zh": "舒張壓 DBP (mmHg)",
        "type": "number",
        "min": 40,
        "max": 130,
        "step": 1,
        "default": 75,
        "ref": {
            "green": {"range": "60–89 mmHg", "preset": 75},
            "yellow": {"range": "90–99 mmHg", "preset": 92},
            "red": {"range": "≥ 100 mmHg", "preset": 104},
        },
    },
    {
        "key": "spo2_pct",
        "en": "Blood Oxygen SpO2 (%)",
        "zh": "血氧飽和度 SpO2 (%)",
        "type": "number",
        "min": 80.0,
        "max": 100.0,
        "step": 0.1,
        "default": 98.2,
        "ref": {
            "green": {"range": "96.0–100%", "preset": 98.2},
            "yellow": {"range": "92.1–95.9%", "preset": 94.8},
            "red": {"range": "≤ 92.0%", "preset": 91.0},
        },
    },
    {
        "key": "sleep_tst_h",
        "en": "Sleep Duration (hours)",
        "zh": "昨晚睡眠時數 (小時)",
        "type": "number",
        "min": 2.0,
        "max": 12.0,
        "step": 0.1,
        "default": 7.3,
        "ref": {
            "green": {"range": "≥ 7.0 h", "preset": 7.3},
            "yellow": {"range": "6.5–6.9 h", "preset": 6.6},
            "red": {"range": "< 6.0 h", "preset": 5.0},
        },
    },
    {
        "key": "hydration_ml",
        "en": "24h Fluid Intake (mL)",
        "zh": "24 小時飲水量 (mL)",
        "type": "number",
        "min": 500,
        "max": 5000,
        "step": 50,
        "default": 2550,
        "ref": {
            "green": {"range": "≥ 2000 mL", "preset": 2550},
            "yellow": {"range": "1500–1999 mL", "preset": 1750},
            "red": {"range": "< 1500 mL", "preset": 1250},
        },
    },
    {
        "key": "stress_score",
        "en": "Subjective Stress / Load (1–10)",
        "zh": "主觀壓力與疲勞評分 (1–10)",
        "type": "number",
        "min": 1.0,
        "max": 10.0,
        "step": 0.5,
        "default": 2.0,
        "ref": {
            "green": {"range": "1.0–3.0 (Low)", "preset": 2.0},
            "yellow": {"range": "3.5–6.5 (Mod)", "preset": 5.0},
            "red": {"range": "≥ 7.0 (High)", "preset": 8.0},
        },
    },
    {
        "key": "symptoms",
        "en": "Today's Self-Reported Symptoms",
        "zh": "今日主觀症狀勾選",
        "type": "symptoms",
        "default": [],
        "ref": {
            "green": {"range": "None selected", "preset": []},
            "yellow": {"range": "Fatigue / Nasal", "preset": ["fatigue", "nasal_congestion"]},
            "red": {"range": "Fever / Rash / Chills", "preset": ["fever", "vesicular_rash", "chills"]},
        },
    },
]

# Section B: Scheduled Subsystem Check-In Fields (shown per active/due module)
MODULE_CHECKIN_FIELDS: dict[str, list[dict[str, Any]]] = {
    "cabin_environment": [
        {
            "key": "ppco2_1h_mmHg",
            "en": "Cabin 1h ppCO2 Readout (mmHg)",
            "zh": "艙內 1h 二氧化碳分壓 (mmHg)",
            "type": "number",
            "min": 0.5,
            "max": 6.0,
            "step": 0.05,
            "default": 1.85,
            "ref": {
                "green": {"range": "< 2.50 mmHg", "preset": 1.85},
                "yellow": {"range": "2.50–3.00 mmHg", "preset": 2.75},
                "red": {"range": "> 3.00 mmHg", "preset": 3.45},
            },
        },
        {
            "key": "temp_C",
            "en": "Cabin Ambient Temp (°C)",
            "zh": "艙內環境溫度 (°C)",
            "type": "number",
            "min": 15.0,
            "max": 35.0,
            "step": 0.5,
            "default": 22.3,
            "ref": {
                "green": {"range": "20.0–25.0 °C", "preset": 22.3},
                "yellow": {"range": "18–19.9 or 25.1–27", "preset": 26.0},
                "red": {"range": "< 18 or > 27 °C", "preset": 28.5},
            },
        },
        {
            "key": "crew_leq8_dBA",
            "en": "Personal 8h Noise Dosimeter (dBA)",
            "zh": "個人 8h 噪音暴露劑量 (dBA)",
            "type": "number",
            "min": 40.0,
            "max": 95.0,
            "step": 0.5,
            "default": 45.0,
            "ref": {
                "green": {"range": "≤ 50.0 dBA", "preset": 45.0},
                "yellow": {"range": "50.5–62.0 dBA", "preset": 55.0},
                "red": {"range": "> 62.0 dBA", "preset": 66.0},
            },
        },
        {
            "key": "workload_bedford",
            "en": "Bedford Workload Rating (1–10)",
            "zh": "Bedford 任務負荷評分 (1–10)",
            "type": "number",
            "min": 1,
            "max": 10,
            "step": 1,
            "default": 2,
            "ref": {
                "green": {"range": "1–4", "preset": 2},
                "yellow": {"range": "5–6", "preset": 5},
                "red": {"range": "≥ 7", "preset": 8},
            },
        },
    ],
    "cardiovascular": [
        {
            "key": "resp_rate_bpm",
            "en": "Resting Resp Rate (breaths/min)",
            "zh": "靜息呼吸頻率 (次/分)",
            "type": "number",
            "min": 6.0,
            "max": 40.0,
            "step": 0.5,
            "default": 14.5,
            "ref": {
                "green": {"range": "10–18 /min", "preset": 14.5},
                "yellow": {"range": "18.5–21 /min", "preset": 20.5},
                "red": {"range": "> 21.5 or > 25 /min", "preset": 27.0},
            },
        },
        {
            "key": "stand_hr_rise_bpm",
            "en": "LBNP / Stand HR Rise (bpm)",
            "zh": "LBNP / 站立測試心率升幅 (bpm)",
            "type": "number",
            "min": 0,
            "max": 60,
            "step": 1,
            "default": 12,
            "ref": {
                "green": {"range": "< 20 bpm", "preset": 12},
                "yellow": {"range": "20–29 bpm", "preset": 24},
                "red": {"range": "≥ 30 bpm", "preset": 35},
            },
        },
        {
            "key": "ijv_flow",
            "en": "Neck IJV Ultrasound Flow",
            "zh": "頸內靜脈超音波血流 (IJV)",
            "type": "select",
            "options": ["forward", "stagnant", "reversed"],
            "default": "forward",
            "ref": {
                "green": {"range": "forward", "preset": "forward"},
                "yellow": {"range": "stagnant", "preset": "stagnant"},
                "red": {"range": "reversed", "preset": "reversed"},
            },
        },
        {
            "key": "dizzy",
            "en": "Orthostatic Dizziness During Test",
            "zh": "姿勢測試時感到頭暈",
            "type": "checkbox",
            "default": False,
            "ref": {
                "green": {"range": "No", "preset": False},
                "yellow": {"range": "No", "preset": False},
                "red": {"range": "Yes", "preset": True},
            },
        },
    ],
    "musculoskeletal": [
        {
            "key": "body_mass_kg",
            "en": "SLAMMD Body Mass (kg)",
            "zh": "SLAMMD 微重力體重 (kg)",
            "type": "number",
            "min": 45.0,
            "max": 110.0,
            "step": 0.1,
            "default": 73.2,
            "ref": {
                "green": {"range": "≥ 70.3 kg (loss <5%)", "preset": 73.2},
                "yellow": {"range": "66.7–70.2 kg (5–10%)", "preset": 69.5},
                "red": {"range": "≤ 66.6 kg (≥10%)", "preset": 66.0},
            },
        },
        {
            "key": "iso_peak_force_n",
            "en": "Isometric Mid-Thigh Peak Force (N)",
            "zh": "E4D 等長最大肌力峰值 (N)",
            "type": "number",
            "min": 900,
            "max": 2500,
            "step": 10,
            "default": 1815,
            "ref": {
                "green": {"range": "≥ 1758 N (loss <5%)", "preset": 1815},
                "yellow": {"range": "1666–1757 N (5–10%)", "preset": 1700},
                "red": {"range": "≤ 1665 N (≥10%)", "preset": 1440},
            },
        },
        {
            "key": "velocity_loss_pct",
            "en": "E4D Squat Velocity Loss (%)",
            "zh": "E4D 深蹲速度衰減率 (%)",
            "type": "number",
            "min": 0.0,
            "max": 50.0,
            "step": 0.5,
            "default": 24.5,
            "ref": {
                "green": {"range": "20.0–30.0% (Optimal)", "preset": 24.5},
                "yellow": {"range": "< 20.0% (Underload)", "preset": 16.5},
                "red": {"range": "> 30.0% (Fatigue)", "preset": 33.5},
            },
        },
        {
            "key": "csa_thigh_cm2",
            "en": "Ultrasound Thigh CSA (cm²)",
            "zh": "超音波大腿肌肉截面積 (cm²)",
            "type": "number",
            "min": 90.0,
            "max": 180.0,
            "step": 0.2,
            "default": 146.4,
            "ref": {
                "green": {"range": "≥ 142.1 cm² (<4%)", "preset": 146.4},
                "yellow": {"range": "137.7–142.0 cm²", "preset": 140.5},
                "red": {"range": "≤ 137.6 cm² (≥7%)", "preset": 136.0},
            },
        },
    ],
    "neuro_ocular": [
        {
            "key": "amsler_result",
            "en": "Amsler Grid Self-Test",
            "zh": "阿姆斯勒方格表自測",
            "type": "select",
            "options": ["normal", "metamorphopsia", "scotoma"],
            "default": "normal",
            "ref": {
                "green": {"range": "normal", "preset": "normal"},
                "yellow": {"range": "normal", "preset": "normal"},
                "red": {"range": "metamorphopsia / scotoma", "preset": "scotoma"},
            },
        },
        {
            "key": "sph_eq_shift_d",
            "en": "Hyperopic Refraction Shift (D)",
            "zh": "遠視屈光偏移量 (D)",
            "type": "number",
            "min": -0.5,
            "max": 2.5,
            "step": 0.25,
            "default": 0.25,
            "ref": {
                "green": {"range": "< +0.75 D", "preset": 0.25},
                "yellow": {"range": "≥ +0.75 D", "preset": 0.75},
                "red": {"range": "≥ +1.25 D + folds", "preset": 1.25},
            },
        },
        {
            "key": "onsd_mm",
            "en": "Ultrasound Optic Nerve Sheath ONSD (mm)",
            "zh": "超音波視神經鞘直徑 ONSD (mm)",
            "type": "number",
            "min": 3.5,
            "max": 8.0,
            "step": 0.1,
            "default": 5.1,
            "ref": {
                "green": {"range": "< 5.6 mm", "preset": 5.1},
                "yellow": {"range": "5.6–6.0 mm", "preset": 5.8},
                "red": {"range": "> 6.0 mm (Δ≥0.5)", "preset": 6.4},
            },
        },
        {
            "key": "delta_trt_um",
            "en": "Mini OCT Retinal ΔTRT (µm)",
            "zh": "Mini OCT 視網膜厚度變化 ΔTRT (µm)",
            "type": "number",
            "min": -10,
            "max": 100,
            "step": 1,
            "default": 9,
            "ref": {
                "green": {"range": "< +20 µm", "preset": 9},
                "yellow": {"range": "+20 to +54 µm", "preset": 28},
                "red": {"range": "≥ +55 µm", "preset": 62},
            },
        },
    ],
    "immune_metabolic": [
        {
            "key": "wbc",
            "en": "Bio-Analyzer WBC (10⁹/L)",
            "zh": "Bio-Analyzer 白血球總數 (10⁹/L)",
            "type": "number",
            "min": 1.0,
            "max": 25.0,
            "step": 0.1,
            "default": 6.2,
            "ref": {
                "green": {"range": "4.0–9.5", "preset": 6.2},
                "yellow": {"range": "9.6–11.5", "preset": 9.8},
                "red": {"range": "≥ 12.0", "preset": 13.4},
            },
        },
        {
            "key": "lymph",
            "en": "Lymphocyte Count (10⁹/L)",
            "zh": "淋巴球計數 (10⁹/L)",
            "type": "number",
            "min": 0.2,
            "max": 4.5,
            "step": 0.05,
            "default": 1.95,
            "ref": {
                "green": {"range": "> 1.50 (>-25%)", "preset": 1.95},
                "yellow": {"range": "1.01–1.50 (-25%)", "preset": 1.4},
                "red": {"range": "≤ 1.00 (-50%)", "preset": 0.85},
            },
        },
        {
            "key": "neut",
            "en": "Neutrophil Count (10⁹/L)",
            "zh": "嗜中性球計數 (10⁹/L)",
            "type": "number",
            "min": 0.1,
            "max": 20.0,
            "step": 0.1,
            "default": 3.6,
            "ref": {
                "green": {"range": "2.0–6.0 (≥10% WBC)", "preset": 3.6},
                "yellow": {"range": "6.1–9.0", "preset": 7.6},
                "red": {"range": "> 9.0 (<10%=QC)", "preset": 11.4},
            },
        },
        {
            "key": "saliva_vzv",
            "en": "Saliva VZV DNA (copies/mL)",
            "zh": "唾液水痘病毒 VZV (copies/mL)",
            "type": "number",
            "min": 0,
            "max": 10000,
            "step": 50,
            "default": 0,
            "ref": {
                "green": {"range": "< 100", "preset": 0},
                "yellow": {"range": "100–999", "preset": 320},
                "red": {"range": "≥ 1000", "preset": 4800},
            },
        },
    ],
}

# Full Developer Mode Manual Override Fields (with G/Y/R Reference Values)
DEV_OVERRIDE_FIELDS: dict[str, list[dict[str, Any]]] = {
    "cabin_environment": [
        {
            "key": "ppco2_1h_mmHg",
            "en": "Cabin ppCO2 1h (mmHg)",
            "zh": "艙內 1 小時二氧化碳分壓 (mmHg)",
            "type": "range",
            "min": 0.5,
            "max": 5.0,
            "step": 0.05,
            "default": 1.85,
            "ref": {
                "green": {"range": "< 2.50", "preset": 1.85},
                "yellow": {"range": "2.50–3.00", "preset": 2.75},
                "red": {"range": "> 3.00", "preset": 3.45},
            },
        },
        {
            "key": "proton_flux_10mev_pfu",
            "en": "GOES >=10MeV Proton Flux (pfu)",
            "zh": "GOES ≥10MeV 質子通量 (pfu)",
            "type": "range",
            "min": 0,
            "max": 300,
            "step": 1,
            "default": 1.8,
            "ref": {
                "green": {"range": "< 10 pfu", "preset": 1.8},
                "yellow": {"range": "10–99 pfu", "preset": 24},
                "red": {"range": "≥ 100 pfu", "preset": 240},
            },
        },
        {
            "key": "crew_leq8_dBA",
            "en": "Crew 8h Noise Exposure (dBA)",
            "zh": "乘員 8 小時噪音暴露 (dBA)",
            "type": "range",
            "min": 40,
            "max": 95,
            "step": 0.5,
            "default": 45.0,
            "ref": {
                "green": {"range": "≤ 50.0", "preset": 45.0},
                "yellow": {"range": "50.5–62.0", "preset": 54.0},
                "red": {"range": "> 62.0", "preset": 65.0},
            },
        },
        {
            "key": "sleep_tst_h",
            "en": "Actiwatch Sleep Duration (h)",
            "zh": "Actiwatch 睡眠時數 (小時)",
            "type": "range",
            "min": 3.0,
            "max": 10.0,
            "step": 0.1,
            "default": 7.3,
            "ref": {
                "green": {"range": "≥ 7.0 h", "preset": 7.3},
                "yellow": {"range": "6.5–6.9 h", "preset": 6.6},
                "red": {"range": "< 6.0 h", "preset": 5.1},
            },
        },
        {
            "key": "spe_alert",
            "en": "SPE Solar Radiation Storm Alert",
            "zh": "SPE 太陽質子風暴警報",
            "type": "checkbox",
            "default": False,
            "ref": {
                "green": {"range": "False", "preset": False},
                "yellow": {"range": "False", "preset": False},
                "red": {"range": "True", "preset": True},
            },
        },
    ],
    "cardiovascular": [
        {
            "key": "rest_hr_bpm",
            "en": "Resting Heart Rate (bpm)",
            "zh": "靜息心率 (bpm)",
            "type": "range",
            "min": 40,
            "max": 130,
            "step": 1,
            "default": 65.0,
            "ref": {
                "green": {"range": "50–79", "preset": 65.0},
                "yellow": {"range": "80–99", "preset": 84.0},
                "red": {"range": "≥ 100", "preset": 102.0},
            },
        },
        {
            "key": "spo2_pct",
            "en": "Peripheral SpO2 (%)",
            "zh": "周邊血氧飽和度 SpO2 (%)",
            "type": "range",
            "min": 85,
            "max": 100,
            "step": 0.1,
            "default": 98.2,
            "ref": {
                "green": {"range": "96.0–100", "preset": 98.2},
                "yellow": {"range": "92.1–95.9", "preset": 95.0},
                "red": {"range": "≤ 92.0", "preset": 91.2},
            },
        },
        {
            "key": "pvc_burden_pct",
            "en": "Holter 24h PVC Burden (%)",
            "zh": "Holter 24小時 PVC 負荷 (%)",
            "type": "range",
            "min": 0,
            "max": 15,
            "step": 0.1,
            "default": 0.3,
            "ref": {
                "green": {"range": "< 1.5%", "preset": 0.3},
                "yellow": {"range": "1.5–4.9%", "preset": 2.6},
                "red": {"range": "≥ 5.0%", "preset": 6.4},
            },
        },
        {
            "key": "ijv_flow",
            "en": "IJV Ultrasound Flow",
            "zh": "頸內靜脈 (IJV) 超音波血流",
            "type": "select",
            "options": ["forward", "stagnant", "reversed"],
            "default": "forward",
            "ref": {
                "green": {"range": "forward", "preset": "forward"},
                "yellow": {"range": "stagnant", "preset": "stagnant"},
                "red": {"range": "reversed", "preset": "reversed"},
            },
        },
        {
            "key": "ijv_thrombus",
            "en": "IJV Thrombus Detected",
            "zh": "偵測到頸內靜脈血栓",
            "type": "checkbox",
            "default": False,
            "ref": {
                "green": {"range": "False", "preset": False},
                "yellow": {"range": "False", "preset": False},
                "red": {"range": "True", "preset": True},
            },
        },
    ],
    "musculoskeletal": [
        {
            "key": "csa_thigh_cm2",
            "en": "Thigh Muscle CSA (cm²)",
            "zh": "大腿肌肉截面積 CSA (cm²)",
            "type": "range",
            "min": 115,
            "max": 165,
            "step": 0.5,
            "default": 146.4,
            "ref": {
                "green": {"range": "≥ 142.1", "preset": 146.4},
                "yellow": {"range": "137.7–142.0", "preset": 140.5},
                "red": {"range": "≤ 137.6", "preset": 136.0},
            },
        },
        {
            "key": "velocity_loss_pct",
            "en": "E4D VBT Velocity Loss (%)",
            "zh": "E4D 深蹲速度衰減率 (%)",
            "type": "range",
            "min": 0,
            "max": 45,
            "step": 0.5,
            "default": 24.5,
            "ref": {
                "green": {"range": "20.0–30.0%", "preset": 24.5},
                "yellow": {"range": "< 20.0%", "preset": 16.5},
                "red": {"range": "> 30.0%", "preset": 33.5},
            },
        },
        {
            "key": "ctx",
            "en": "CTX Bone Resorption (ng/mL)",
            "zh": "骨吸收指標 CTX (ng/mL)",
            "type": "range",
            "min": 0.20,
            "max": 0.80,
            "step": 0.01,
            "default": 0.38,
            "ref": {
                "green": {"range": "< 0.40", "preset": 0.38},
                "yellow": {"range": "0.40–0.53", "preset": 0.49},
                "red": {"range": "≥ 0.54 (+50%)", "preset": 0.58},
            },
        },
        {
            "key": "body_mass_kg",
            "en": "SLAMMD Body Mass (kg)",
            "zh": "SLAMMD 微重力體重 (kg)",
            "type": "range",
            "min": 55,
            "max": 90,
            "step": 0.2,
            "default": 73.2,
            "ref": {
                "green": {"range": "≥ 70.3", "preset": 73.2},
                "yellow": {"range": "66.7–70.2", "preset": 69.8},
                "red": {"range": "≤ 66.6", "preset": 66.0},
            },
        },
    ],
    "neuro_ocular": [
        {
            "key": "delta_trt_um",
            "en": "Mini OCT ΔTRT (µm)",
            "zh": "Mini OCT 視網膜厚度變化 ΔTRT (µm)",
            "type": "range",
            "min": -10,
            "max": 90,
            "step": 1,
            "default": 9.0,
            "ref": {
                "green": {"range": "< +20", "preset": 9.0},
                "yellow": {"range": "+20 to +54", "preset": 28.0},
                "red": {"range": "≥ +55", "preset": 62.0},
            },
        },
        {
            "key": "delta_v_onh_mm3",
            "en": "Optic Nerve Head ΔV_ONH (mm³)",
            "zh": "視神經盤體積變化 ΔV_ONH (mm³)",
            "type": "range",
            "min": 0.0,
            "max": 0.50,
            "step": 0.01,
            "default": 0.06,
            "ref": {
                "green": {"range": "< 0.15", "preset": 0.06},
                "yellow": {"range": "0.15–0.29", "preset": 0.17},
                "red": {"range": "≥ 0.30", "preset": 0.34},
            },
        },
        {
            "key": "onsd_mm",
            "en": "Ultrasound ONSD (mm)",
            "zh": "超音波視神經鞘直徑 ONSD (mm)",
            "type": "range",
            "min": 4.0,
            "max": 7.5,
            "step": 0.1,
            "default": 5.1,
            "ref": {
                "green": {"range": "< 5.6 mm", "preset": 5.1},
                "yellow": {"range": "5.6–6.0 mm", "preset": 5.8},
                "red": {"range": "> 6.0 (Δ≥0.5)", "preset": 6.4},
            },
        },
        {
            "key": "sph_eq_shift_d",
            "en": "Hyperopic Shift (Diopters)",
            "zh": "遠視屈光偏移量 (Diopters)",
            "type": "range",
            "min": -0.5,
            "max": 2.0,
            "step": 0.25,
            "default": 0.25,
            "ref": {
                "green": {"range": "< +0.75 D", "preset": 0.25},
                "yellow": {"range": "≥ +0.75 D", "preset": 0.75},
                "red": {"range": "≥ +1.25 D", "preset": 1.25},
            },
        },
        {
            "key": "folds_foveal",
            "en": "Chorioretinal Foveal Folds",
            "zh": "出現黃斑部/脈絡膜皺摺",
            "type": "checkbox",
            "default": False,
            "ref": {
                "green": {"range": "False", "preset": False},
                "yellow": {"range": "False", "preset": False},
                "red": {"range": "True", "preset": True},
            },
        },
    ],
    "immune_metabolic": [
        {
            "key": "temp_c",
            "en": "Oral Temperature (°C)",
            "zh": "口腔體溫 (°C)",
            "type": "range",
            "min": 35.5,
            "max": 40.0,
            "step": 0.1,
            "default": 36.7,
            "ref": {
                "green": {"range": "< 37.3", "preset": 36.7},
                "yellow": {"range": "37.3–37.9", "preset": 37.6},
                "red": {"range": "≥ 38.0", "preset": 38.6},
            },
        },
        {
            "key": "lymph",
            "en": "Lymphocyte Count (10⁹/L)",
            "zh": "淋巴球計數 (10⁹/L)",
            "type": "range",
            "min": 0.4,
            "max": 3.5,
            "step": 0.05,
            "default": 1.95,
            "ref": {
                "green": {"range": "> 1.50", "preset": 1.95},
                "yellow": {"range": "1.01–1.50", "preset": 1.40},
                "red": {"range": "≤ 1.00", "preset": 0.85},
            },
        },
        {
            "key": "saliva_vzv",
            "en": "Saliva VZV DNA (copies/mL)",
            "zh": "唾液水痘病毒 VZV DNA (copies/mL)",
            "type": "range",
            "min": 0,
            "max": 10000,
            "step": 50,
            "default": 0,
            "ref": {
                "green": {"range": "< 100", "preset": 0},
                "yellow": {"range": "100–999", "preset": 320},
                "red": {"range": "≥ 1000", "preset": 4800},
            },
        },
        {
            "key": "hydration_ml",
            "en": "24h Fluid Intake (mL)",
            "zh": "24小時飲水量 (mL)",
            "type": "range",
            "min": 800,
            "max": 4000,
            "step": 50,
            "default": 2550,
            "ref": {
                "green": {"range": "≥ 2000", "preset": 2550},
                "yellow": {"range": "1500–1999", "preset": 1800},
                "red": {"range": "< 1500", "preset": 1400},
            },
        },
    ],
}

# Mapping between module MetricItem.metric_name and logged check-in payload key + threshold defaults
METRIC_TRACKING_META: dict[str, dict[str, Any]] = {
    "oral_temp_c": {
        "payload_key": "temp_c",
        "yellow_threshold": 37.3,
        "red_threshold": 38.0,
        "lower_is_worse": False,
        "baseline_default": 36.7,
    },
    "lymphocytes_10e9_l": {
        "payload_key": "lymph",
        "yellow_threshold": 1.5,
        "red_threshold": 1.0,
        "lower_is_worse": True,
        "baseline_default": 2.0,
    },
    "saliva_vzv_copies_ml": {
        "payload_key": "saliva_vzv",
        "yellow_threshold": 100.0,
        "red_threshold": 1000.0,
        "lower_is_worse": False,
        "baseline_default": 0.0,
    },
    "hydration_ml": {
        "payload_key": "hydration_ml",
        "yellow_threshold": 2000.0,
        "red_threshold": 1500.0,
        "lower_is_worse": True,
        "baseline_default": 2500.0,
    },
    "rest_hr_bpm": {
        "payload_key": "rest_hr_bpm",
        "yellow_threshold": 80.0,
        "red_threshold": 100.0,
        "lower_is_worse": False,
        "baseline_default": 62.0,
    },
    "sbp_mmHg": {
        "payload_key": "sbp_mmHg",
        "yellow_threshold": 140.0,
        "red_threshold": 160.0,
        "lower_is_worse": False,
        "baseline_default": 116.0,
    },
    "spo2_pct": {
        "payload_key": "spo2_pct",
        "yellow_threshold": 96.0,
        "red_threshold": 92.0,
        "lower_is_worse": True,
        "baseline_default": 98.4,
    },
    "resp_rate_bpm": {
        "payload_key": "resp_rate_bpm",
        "yellow_threshold": 20.0,
        "red_threshold": 25.0,
        "lower_is_worse": False,
        "baseline_default": 14.0,
    },
    "stand_hr_rise_bpm": {
        "payload_key": "stand_hr_rise_bpm",
        "yellow_threshold": 20.0,
        "red_threshold": 30.0,
        "lower_is_worse": False,
        "baseline_default": 11.0,
    },
    "body_mass_kg": {
        "payload_key": "body_mass_kg",
        "yellow_threshold": 70.3,
        "red_threshold": 66.6,
        "lower_is_worse": True,
        "baseline_default": 74.0,
    },
    "iso_peak_force_n": {
        "payload_key": "iso_peak_force_n",
        "yellow_threshold": 1757.5,
        "red_threshold": 1665.0,
        "lower_is_worse": True,
        "baseline_default": 1850.0,
    },
    "velocity_loss_pct": {
        "payload_key": "velocity_loss_pct",
        "yellow_threshold": 20.0,
        "red_threshold": 30.0,
        "lower_is_worse": False,
        "baseline_default": 24.0,
    },
    "csa_thigh_cm2": {
        "payload_key": "csa_thigh_cm2",
        "yellow_threshold": 142.08,
        "red_threshold": 137.64,
        "lower_is_worse": True,
        "baseline_default": 148.0,
    },
    "delta_trt_um": {
        "payload_key": "delta_trt_um",
        "yellow_threshold": 20.0,
        "red_threshold": 55.0,
        "lower_is_worse": False,
        "baseline_default": 0.0,
    },
    "delta_v_onh_mm3": {
        "payload_key": "delta_v_onh_mm3",
        "yellow_threshold": 0.15,
        "red_threshold": 0.30,
        "lower_is_worse": False,
        "baseline_default": 0.0,
    },
    "onsd_mm": {
        "payload_key": "onsd_mm",
        "yellow_threshold": 5.6,
        "red_threshold": 6.0,
        "lower_is_worse": False,
        "baseline_default": 4.9,
    },
    "sph_eq_shift_d": {
        "payload_key": "sph_eq_shift_d",
        "yellow_threshold": 0.75,
        "red_threshold": 1.25,
        "lower_is_worse": False,
        "baseline_default": 0.0,
    },
    "ppco2_1h_mmHg": {
        "payload_key": "ppco2_1h_mmHg",
        "yellow_threshold": 2.5,
        "red_threshold": 3.0,
        "lower_is_worse": False,
        "baseline_default": 1.82,
    },
    "temp_C": {
        "payload_key": "temp_C",
        "yellow_threshold": 25.0,
        "red_threshold": 27.0,
        "lower_is_worse": False,
        "baseline_default": 22.2,
    },
    "crew_leq8_dBA": {
        "payload_key": "crew_leq8_dBA",
        "yellow_threshold": 50.0,
        "red_threshold": 62.0,
        "lower_is_worse": False,
        "baseline_default": 44.5,
    },
    "sleep_tst_h": {
        "payload_key": "sleep_tst_h",
        "yellow_threshold": 7.0,
        "red_threshold": 6.0,
        "lower_is_worse": True,
        "baseline_default": 7.35,
    },
    "workload_bedford": {
        "payload_key": "workload_bedford",
        "yellow_threshold": 4.0,
        "red_threshold": 6.0,
        "lower_is_worse": False,
        "baseline_default": 2.0,
    },
}


def default_daily_vitals() -> dict[str, Any]:
    """Return initial default dictionary for the Daily Routine Vitals form."""
    return {f["key"]: f["default"] for f in DAILY_VITALS_FIELDS}


def default_module_checkins() -> dict[str, dict[str, Any]]:
    """Return initial default dictionary for per-module Scheduled Check-in fields."""
    return {
        mod_id: {f["key"]: f["default"] for f in fields}
        for mod_id, fields in MODULE_CHECKIN_FIELDS.items()
    }


def build_frontend_checkin_spec() -> dict[str, Any]:
    """Export unified field schemas, symptoms, and Dev reference ranges for HUD JS."""
    return {
        "symptoms": SYMPTOM_OPTIONS,
        "daily_fields": DAILY_VITALS_FIELDS,
        "module_checkin_fields": MODULE_CHECKIN_FIELDS,
        "dev_override_fields": DEV_OVERRIDE_FIELDS,
    }


def record_checkin_entry(
    checkin_series: dict[str, dict[str, Any]],
    crew_id: str,
    mission_day: int,
    daily_vitals: dict[str, Any],
    module_values: Optional[dict[str, Any]] = None,
    checked_modules: Optional[list[str]] = None,
    recorded_at_iso: Optional[str] = None,
) -> dict[str, dict[str, Any]]:
    """Insert or update a mission_day check-in point inside `checkin_series`."""
    series = {k: dict(v) for k, v in (checkin_series or {}).items()}
    crew_map = dict(series.get(crew_id, {}))
    day_key = str(max(1, int(mission_day)))

    existing_entry = dict(crew_map.get(day_key, {}))
    merged_vals = dict(existing_entry.get("values", {}))

    for k, v in (daily_vitals or {}).items():
        if v is not None:
            merged_vals[k] = v

    for k, v in (module_values or {}).items():
        if v is not None:
            merged_vals[k] = v

    # Cross-module sync keys
    if "sleep_tst_h" in merged_vals and merged_vals["sleep_tst_h"] is not None:
        merged_vals["sleep_h"] = float(merged_vals["sleep_tst_h"])
    if "stress_score" in merged_vals and merged_vals["stress_score"] is not None:
        try:
            merged_vals.setdefault("stress_vas", round(float(merged_vals["stress_score"]) * 10.0, 1))
        except (TypeError, ValueError):
            pass

    prev_mods = list(existing_entry.get("checked_modules", []))
    for mod_id in checked_modules or []:
        if mod_id not in prev_mods:
            prev_mods.append(mod_id)

    crew_map[day_key] = {
        "mission_day": int(day_key),
        "updated_at": recorded_at_iso,
        "checked_modules": prev_mods,
        "values": merged_vals,
    }
    series[crew_id] = crew_map
    return series


def _sorted_crew_entries(
    checkin_series: dict[str, Any],
    crew_id: str,
    max_mission_day: Optional[int] = None,
) -> list[tuple[int, dict[str, Any]]]:
    crew_map = (checkin_series or {}).get(crew_id, {})
    if not isinstance(crew_map, dict):
        return []
    entries: list[tuple[int, dict[str, Any]]] = []
    for k, entry in crew_map.items():
        if not isinstance(entry, dict):
            continue
        try:
            day_num = int(entry.get("mission_day", k))
        except (TypeError, ValueError):
            continue
        if max_mission_day is not None and day_num > max_mission_day:
            continue
        vals = entry.get("values")
        if isinstance(vals, dict):
            entries.append((day_num, vals))
    entries.sort(key=lambda item: item[0])
    return entries


def get_active_checkin_payload(
    checkin_series: dict[str, Any],
    crew_id: str,
    mission_day: int,
) -> dict[str, dict[str, Any]]:
    """Build per-module override dicts from the latest recorded check-in <= mission_day."""
    entries = _sorted_crew_entries(checkin_series, crew_id, max_mission_day=mission_day)
    if not entries:
        return {}

    # Merge chronologically up to mission_day so daily vitals and earlier module check-ins persist
    combined: dict[str, Any] = {}
    for _day, vals in entries:
        for k, v in vals.items():
            if v is not None:
                combined[k] = v

    per_module: dict[str, dict[str, Any]] = {
        "cabin_environment": {},
        "cardiovascular": {},
        "musculoskeletal": {},
        "neuro_ocular": {},
        "immune_metabolic": {},
    }

    cabin_keys = {"sleep_tst_h", "stress_vas", "ppco2_1h_mmHg", "temp_C", "crew_leq8_dBA", "workload_bedford"}
    cardio_keys = {"rest_hr_bpm", "sbp_mmHg", "dbp_mmHg", "spo2_pct", "resp_rate_bpm", "stand_hr_rise_bpm", "ijv_flow", "dizzy"}
    musculo_keys = {"body_mass_kg", "iso_peak_force_n", "velocity_loss_pct", "csa_thigh_cm2"}
    neuro_keys = {"amsler_result", "sph_eq_shift_d", "onsd_mm", "delta_trt_um"}
    immune_keys = {"temp_c", "symptoms", "hydration_ml", "sleep_h", "stress_score", "wbc", "lymph", "neut", "saliva_vzv"}

    for k, v in combined.items():
        if k in cabin_keys:
            per_module["cabin_environment"][k] = v
        if k in cardio_keys:
            per_module["cardiovascular"][k] = v
        if k in musculo_keys:
            per_module["musculoskeletal"][k] = v
        if k in neuro_keys:
            per_module["neuro_ocular"][k] = v
        if k in immune_keys:
            per_module["immune_metabolic"][k] = v

    return {m: d for m, d in per_module.items() if d}


def _recompute_slope_and_ttr(
    days: list[int],
    vals: list[float],
    yellow_thresh: Optional[float],
    red_thresh: Optional[float],
    lower_is_worse: bool,
) -> tuple[Optional[float], Optional[int]]:
    if len(days) < 2 or len(vals) < 2 or len(days) != len(vals):
        return None, None
    x = np.asarray(days[-5:], dtype=float)
    y = np.asarray(vals[-5:], dtype=float)
    if np.ptp(x) <= 0:
        return 0.0, None
    slope = float(np.polyfit(x, y, 1)[0])
    cur = float(y[-1])
    if red_thresh is None:
        return round(slope, 4), None

    if lower_is_worse:
        if cur <= red_thresh:
            return round(slope, 4), 0
        if slope < -1e-6:
            return round(slope, 4), max(1, int(math.ceil((red_thresh - cur) / slope)))
    else:
        if cur >= red_thresh:
            return round(slope, 4), 0
        if slope > 1e-6:
            return round(slope, 4), max(1, int(math.ceil((red_thresh - cur) / slope)))
    return round(slope, 4), None


def apply_checkin_history_to_results(
    results: dict[str, ModuleEvaluationResult],
    checkin_series: dict[str, Any],
    crew_id: str,
    mission_day: int,
) -> dict[str, ModuleEvaluationResult]:
    """Merge logged check-in series points into module metric trajectories & projections."""
    entries = _sorted_crew_entries(checkin_series, crew_id, max_mission_day=mission_day)
    if not entries:
        return results

    # Collect per-key chronological series from checkin_series
    key_series: dict[str, list[tuple[int, float]]] = {}
    for d_num, vals in entries:
        for k, raw_v in vals.items():
            if isinstance(raw_v, bool) or isinstance(raw_v, (list, dict, str)):
                continue
            try:
                num_v = float(raw_v)
            except (TypeError, ValueError):
                continue
            key_series.setdefault(k, []).append((d_num, round(num_v, 3)))

    for _mod_id, res in results.items():
        if not res.quality_passed:
            continue

        red_candidates: list[int] = []
        if res.long_term_plan.days_until_red_prediction is not None:
            red_candidates.append(int(res.long_term_plan.days_until_red_prediction))

        for metric in res.metrics:
            meta = METRIC_TRACKING_META.get(metric.metric_name)
            if not meta:
                continue

            if metric.yellow_threshold is None and meta.get("yellow_threshold") is not None:
                metric.yellow_threshold = float(meta["yellow_threshold"])
            if metric.red_threshold is None and meta.get("red_threshold") is not None:
                metric.red_threshold = float(meta["red_threshold"])
            if "lower_is_worse" in meta:
                metric.lower_is_worse = bool(meta["lower_is_worse"])

            pts = key_series.get(meta["payload_key"], [])
            if not pts:
                continue

            # Build merged day -> value map preserving prior historical points
            day_map: dict[int, float] = {}
            if len(metric.history_days) == len(metric.history_values) and len(metric.history_days) >= 1:
                for hd, hv in zip(metric.history_days, metric.history_values):
                    day_map[int(hd)] = float(hv)
            else:
                base_val = metric.baseline_val
                try:
                    base_num = float(base_val) if base_val is not None else float(meta["baseline_default"])
                except (TypeError, ValueError):
                    base_num = float(meta["baseline_default"])
                first_logged_day = pts[0][0]
                if first_logged_day > 0:
                    day_map[0] = round(base_num, 3)

            for ld, lv in pts:
                day_map[int(ld)] = float(lv)

            sorted_days = sorted(day_map.keys())
            sorted_vals = [day_map[d] for d in sorted_days]

            metric.history_days = sorted_days
            metric.history_values = sorted_vals

            slope, ttr_days = _recompute_slope_and_ttr(
                sorted_days,
                sorted_vals,
                metric.yellow_threshold,
                metric.red_threshold,
                metric.lower_is_worse,
            )
            if slope is not None:
                metric.slope_per_day = slope
            if ttr_days is not None:
                red_candidates.append(ttr_days)

        if res.status_light == "RED":
            res.long_term_plan.days_until_red_prediction = 0
        elif red_candidates:
            res.long_term_plan.days_until_red_prediction = min(red_candidates)

    return results
