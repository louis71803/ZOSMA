"""Bilingual (English / Traditional Chinese) dictionaries and translator helpers (`ui/i18n.py`).

Keeping all UI labels and domain corpus translations isolated in `ui/i18n.py`
ensures future merges from Roles 2-6 can be localized without touching layout or SVG code.
"""

from __future__ import annotations

HUD_I18N_JS = r"""
  const I18N = {
    en: {
      hud_title: 'Z.O.S.M.A. FLIGHT SURGEON HUD',
      hud_sub: 'AUTONOMOUS DEEP-SPACE MEDICAL INTELLIGENCE · OFFLINE CLOSED-LOOP ENGINE',
      crew_badge: 'CREW {crew} · SOL/DAY {day}',
      scen_green: 'GREEN',
      scen_yellow: 'YELLOW',
      scen_red: 'RED',
      scen_bad: 'QC FAULT',
      drawer_btn: '⚙ SETTINGS & TELEMETRY',
      manual_on: 'MANUAL ON',
      kpi_status_lbl: 'MISSION MEDICAL STATUS',
      kpi_status_sub: '3-Layer Worst-Wins Arbitration',
      kpi_red_lbl: 'CRITICAL RED SUBSYSTEMS',
      kpi_red_sub_ok: 'All subsystems nominal/guarded',
      kpi_triage_lbl: 'NEXT MANDATORY TRIAGE',
      kpi_triage_sub: 'Automated Closed-Loop Cadence',
      kpi_proj_lbl: 'EARLIEST PROJECTED RED',
      kpi_proj_sub: 'Linear dY/dt Trajectory Forecast',
      days_unit: 'DAYS',
      none_lbl: 'NONE',
      bio_title: 'HOLOGRAPHIC BIO & HABITAT SCANNER',
      click_node: 'CLICK ORGAN TO INSPECT TREND',
      view_overview: '↺ ALL SYSTEMS',
      view_anatomy: 'SYSTEM SCAN',
      view_front: 'FRONT MUSCLE',
      view_back: 'BACK & SPINE',
      view_eye_zoom: '👁 EYE + VESTIBULAR',
      view_cns_full: 'FULL CNS',
      node_cabin: 'CABIN / RAD',
      node_neuro: 'NEURO-OCULAR',
      node_cardio: 'CARDIOVASCULAR',
      node_immune: 'IMMUNE / RENAL',
      node_musculo: 'MUSCULOSKELETAL',
      organ_rad_shield: 'RADIATION SHIELD',
      organ_atm_co2: 'CABIN CO2 / O2',
      organ_acoustics: 'ACOUSTIC SPL',
      organ_circadian: 'SLEEP / CIRCADIAN',
      organ_quads: 'THIGH QUADRICEPS',
      organ_calves: 'CALF GASTROCNEMIUS',
      organ_spine_bone: 'SPINE / PELVIS BONE',
      organ_core_pect: 'CORE / VBT LOAD',
      organ_glute_ham: 'GLUTES / HAMSTRINGS',
      organ_erector: 'ERECTOR SPINAE',
      organ_ijv: 'NECK IJV VEINS',
      organ_heart: 'HEART / MYOCARDIUM',
      organ_aorta: 'AORTA / BP (SBP)',
      organ_lower_vasc: 'LOWER VASCULAR / ΔPV',
      organ_hypothal: 'HYPOTHALAMUS (TEMP)',
      organ_thyroid: 'THYROID / METABOLIC',
      organ_thymus_lymph: 'THYMUS / LYMPH NODES',
      organ_adrenal_kidney: 'ADRENALS & KIDNEYS',
      organ_retina_trt: 'RETINA / MACULA (ΔTRT)',
      organ_onh_disc: 'OPTIC DISC (ΔV_ONH)',
      organ_onsd_sheath: 'OPTIC SHEATH (ONSD)',
      organ_vestibular: 'VESTIBULAR LABYRINTH',
      organ_cornea_lens: 'HYPEROPIC SHIFT (D)',
      organ_brain_cortex: 'BRAIN / ICP',
      organ_spinal_cord: 'SPINAL TRACT',
      traj_title: '3-LAYER LONGITUDINAL TRAJECTORY',
      leg_measured: 'Measured',
      leg_forecast: '+30d Forecast',
      guide_hdr: 'ZERO-MEDICAL-BACKGROUND 3-STEP CREW PROTOCOL',
      guide_sop: 'OFFLINE AUTONOMOUS SOP',
      tab_measure: '1. HOW TO MEASURE',
      tab_meaning: '2. WHAT IT MEANS',
      tab_action: '3. ACTION PROTOCOL',
      plan_title: 'CLOSED-LOOP PLANNING BOARD',
      auto_sync: 'AUTO-SYNC',
      bus_title: 'CROSS-MODULE TELEMETRY BUS',
      plan_short: 'SHORT-TERM TRIAGE (0–48H)',
      plan_long: 'LONG-TERM REGIMEN (7–30D)',
      tag_immediate: 'IMMEDIATE',
      tag_red_in: 'RED IN {d}D',
      tag_regimen: '7-30D REGIMEN',
      pipeline_lbl: 'DATA PIPELINE:',
      src_real: 'REAL CSV',
      src_sim: 'SIMULATED',
      src_demo: 'SYNTHETIC DEMO',
      gen_csv_btn: 'GENERATE DEMO CSV TEMPLATES IN data/',
      drawer_title: '⚙ SYSTEM SETTINGS & TELEMETRY OVERRIDES',
      close_btn: '✕ CLOSE',
      lang_label: 'INTERFACE LANGUAGE / 介面語言',
      lang_desc: 'Switch Mission Control HUD language',
      crew_id_lbl: 'CREW ID',
      mission_day_lbl: 'MISSION DAY',
      prefer_csv_lbl: 'Prefer Real CSVs in data/',
      enable_manual_lbl: 'Enable Manual Overrides',
      reset_btn: 'RESET TO SCENARIO',
      save_run_btn: '🚀 SAVE & RUN ALL 5 AGENTS',
      vs_base: 'vs base',
      layer_prefix: 'Layer:',
      status_GREEN: 'GREEN',
      status_YELLOW: 'YELLOW',
      status_RED: 'RED',
      status_WATCH: 'GREEN-WATCH',
      mod_short: {
        cabin_environment: 'Cabin & Rad',
        cardiovascular: 'Cardiovascular',
        musculoskeletal: 'Musculoskeletal',
        neuro_ocular: 'Neuro-Ocular',
        immune_metabolic: 'Immune & Renal'
      },
      mod_full: {
        cabin_environment: 'Radiation, Acoustics & Cabin Env',
        cardiovascular: 'Cardiovascular & Aerobic',
        musculoskeletal: 'Musculoskeletal (Bone & Muscle)',
        neuro_ocular: 'Neuro-Ocular & Vestibular (SANS)',
        immune_metabolic: 'Immune, Endocrine & Metabolic'
      }
    },
    zh: {
      hud_title: 'Z.O.S.M.A. 航太隨艦醫療戰情室',
      hud_sub: '深空自主醫療決策系統 · 離線三層閉環引擎',
      crew_badge: '乘員 {crew} · 任務第 {day} 天',
      scen_green: '正常綠燈',
      scen_yellow: '預警黃燈',
      scen_red: '危急紅燈',
      scen_bad: 'QC 異常',
      drawer_btn: '⚙ 設定與感測器微調',
      manual_on: '手動覆寫中',
      kpi_status_lbl: '任務整體醫療狀態',
      kpi_status_sub: '三層決策最嚴格狀態仲裁',
      kpi_red_lbl: '紅燈警示子系統',
      kpi_red_sub_ok: '全系統維持正常或觀察中',
      kpi_triage_lbl: '下次強制複檢倒數',
      kpi_triage_sub: '自動化閉環追蹤排程',
      kpi_proj_lbl: '最早預計轉紅時間',
      kpi_proj_sub: '線性斜率 dY/dt 趨勢預測',
      days_unit: '天',
      none_lbl: '無風險',
      bio_title: '全息生理與艙內環境掃描儀',
      click_node: '點擊發光器官連動趨勢圖',
      view_overview: '↺ 全身總覽',
      view_anatomy: '專屬解剖視圖',
      view_front: '正面肌群',
      view_back: '背面與脊柱',
      view_eye_zoom: '👁 眼部＋前庭特寫',
      view_cns_full: '全身中樞神經',
      node_cabin: '艙內環境 / 輻射',
      node_neuro: '神經眼壓 (SANS)',
      node_cardio: '心血管與有氧',
      node_immune: '免疫與腎臟代謝',
      node_musculo: '骨骼肌肉系統',
      organ_rad_shield: '太陽風暴與輻射護盾',
      organ_atm_co2: '艙壓與二氧化碳 (CO2)',
      organ_acoustics: '艙段聲學噪音暴露',
      organ_circadian: '睡眠與晝夜節律',
      organ_quads: '大腿股四頭肌 (CSA)',
      organ_calves: '小腿腓腸肌/比目魚肌',
      organ_spine_bone: '脊柱與骨盆骨質 (CTX)',
      organ_core_pect: '胸腹核心與發力 (VBT)',
      organ_glute_ham: '臀大肌與腿後肌群',
      organ_erector: '背部豎脊肌群',
      organ_ijv: '雙側頸內靜脈 (IJV)',
      organ_heart: '心臟心肌與心律',
      organ_aorta: '主動脈與血壓 (SBP)',
      organ_lower_vasc: '下肢血管與血漿量',
      organ_hypothal: '下視丘體溫中樞',
      organ_thyroid: '甲狀腺與代謝調節',
      organ_thymus_lymph: '胸腺與淋巴免疫節點',
      organ_adrenal_kidney: '雙側腎上腺與腎臟',
      organ_retina_trt: '視網膜黃斑厚度 (ΔTRT)',
      organ_onh_disc: '視神經盤水腫 (ΔV_ONH)',
      organ_onsd_sheath: '視神經鞘擴張 (ONSD)',
      organ_vestibular: '內耳前庭半規管 (VOR)',
      organ_cornea_lens: '眼球屈光遠視偏移',
      organ_brain_cortex: '大腦皮質與顱內壓',
      organ_spinal_cord: '脊髓中樞神經索',
      traj_title: '三層縱向趨勢軌跡',
      leg_measured: '實測趨勢',
      leg_forecast: '+30天預測',
      guide_hdr: '無醫療背景太空人 · 三步驟操作指引',
      guide_sop: '離線自主標準作業程序',
      tab_measure: '1. 如何測量',
      tab_meaning: '2. 生理意義',
      tab_action: '3. 處置步驟',
      plan_title: '閉環排程與安全仲裁看板',
      auto_sync: '自動同步',
      bus_title: '跨模組遙測連動匯流排',
      plan_short: '短期緊急處置 (0–48小時)',
      plan_long: '長期處方調整 (7–30天)',
      tag_immediate: '立即執行',
      tag_red_in: '{d}天後轉紅',
      tag_regimen: '7-30天處方',
      pipeline_lbl: '資料管線狀態：',
      src_real: '真實 CSV',
      src_sim: '模擬資料',
      src_demo: '模擬示範',
      gen_csv_btn: '在 data/ 生成範本 CSV 檔案',
      drawer_title: '⚙ 系統設定與手動遙測抽屜',
      close_btn: '✕ 關閉',
      lang_label: '介面語言 / INTERFACE LANGUAGE',
      lang_desc: '即時切換戰情室中英文介面',
      crew_id_lbl: '乘員編號 (CREW ID)',
      mission_day_lbl: '任務天數 (SOL/DAY)',
      prefer_csv_lbl: '優先讀取 data/ 真實 CSV',
      enable_manual_lbl: '啟用手動滑桿覆寫',
      reset_btn: '重設回情境預設值',
      save_run_btn: '🚀 儲存並執行全部 5 大模組',
      vs_base: '較基準值',
      layer_prefix: '決策層:',
      status_GREEN: '正常 GREEN',
      status_YELLOW: '預警 YELLOW',
      status_RED: '危急 RED',
      status_WATCH: '觀察 WATCH',
      mod_short: {
        cabin_environment: '艙內環境/輻射',
        cardiovascular: '心血管與有氧',
        musculoskeletal: '骨骼與肌肉',
        neuro_ocular: '神經眼壓 SANS',
        immune_metabolic: '免疫與代謝'
      },
      mod_full: {
        cabin_environment: '輻射、聲學與艙內環境 (Role 6)',
        cardiovascular: '心血管與有氧耐力 (Role 3)',
        musculoskeletal: '骨骼與肌肉系統 (Role 2)',
        neuro_ocular: '神經眼壓與前庭平衡 (Role 4)',
        immune_metabolic: '免疫、內分泌與代謝 (Role 5)'
      }
    }
  };

  const METRIC_ZH = {
    ppco2_1h_mmHg: '艙內 1h 二氧化碳分壓',
    proton_flux_10mev_pfu: 'GOES ≥10MeV 質子通量',
    proton_flux_100mev_pfu: 'GOES ≥100MeV 質子通量',
    dose_rate_uGy_h: 'DOSTEL 區域劑量率',
    career_dose_mSv: '累積任務輻射劑量',
    module_spl_dBA: '艙段空間聲壓級',
    crew_leq8_dBA: '乘員 8 小時噪音暴露',
    daily_noise_dose_pct: '每日噪音劑量百分比',
    audiogram_sts_max_dB: '純音聽力暫時閾移 (STS)',
    p_total_kPa: '艙內總氣壓',
    pio2_mmHg: '吸入氧分壓 (PIO2)',
    temp_C: '艙內環境溫度',
    rh_pct: '艙內相對濕度',
    max_smac_ratio: '揮發氣體最大 SMAC 比',
    water_toc_mg_L: '飲水總有機碳 (TOC)',
    water_iodine_mg_L: '飲水殘餘碘濃度',
    microbial_max_limit_ratio: '空氣/表面/水微生物比',
    particulate_max_limit_ratio: '懸浮微粒濃度上限比',
    sleep_tst_h: '腕錶睡眠總時數',
    pvt_speed_1_per_s: 'PVT-B 反應速度',
    workload_bedford: 'Bedford 工作負荷評分',
    stress_vas: '主觀壓力評分 (VAS)',
    circadian_midpoint_shift_h: '晝夜節律中點偏移',
    co2_sensor_qc: 'CO2 感測器凍結檢核',
    rest_hr_bpm: '靜息心率',
    sbp_mmHg: '收縮壓 (PTT SBP)',
    spo2_pct: '血氧飽和度 (SpO2)',
    resp_rate_bpm: '靜息呼吸頻率',
    pvc_burden_pct: '24h 心室早期收縮負荷',
    stand_hr_rise_bpm: '直立/LBNP 心率升幅',
    ijv_flow_status: '頸內靜脈血流狀態',
    steady_hr_150w_bpm: '150W 固定負荷心率',
    gls_change_pct: '左心室縱向應變變化 (GLS)',
    plasma_volume_delta_pct: '血漿容量變化 (%ΔPV)',
    potassium_mmol_l: '血清鉀離子 (K+)',
    ecg_lead_quality: '心電導極訊號品質',
    csa_thigh_cm2: '大腿肌肉截面積',
    csa_calf_cm2: '小腿肌肉截面積',
    velocity_loss_pct: '深蹲速度衰減率 (VBT)',
    e4d_s_bone_index: 'E4D 骨骼刺激指數',
    iso_peak_force_n: '等長最大肌力峰值',
    body_mass_kg: '太空微重力體重',
    ntx_bone_resorption: '骨吸收指標 NTX',
    ctx_bone_resorption: '骨吸收指標 CTX',
    p1np_bone_formation: '骨生成指標 P1NP',
    est_monthly_bone_loss_pct: '推估每月骨流失率',
    osd575_ca_alp_baseline: 'OSD-575 血清鈣/ALP基準',
    musculoskeletal_qc_gatekeeper: '骨骼肌肉 QC 閘門',
    delta_trt_um: '視網膜厚度變化 ΔTRT',
    delta_v_onh_mm3: '視神經盤體積變化',
    onsd_mm: '視神經鞘直徑 ONSD',
    sph_eq_shift_d: '遠視屈光偏移量',
    vor_gain: '前庭動眼反射增益',
    oct_scan_qc: 'Mini OCT 掃描品質',
    lymphocytes_10e9_l: '淋巴球計數',
    oral_temp_c: '口腔體溫',
    saliva_vzv_copies_ml: '唾液水痘病毒量 (VZV)',
    crp_mg_l: 'C-反應蛋白發炎指標',
    hydration_ml: '24小時飲水量',
    neutrophil_qc_ratio: '嗜中性球分選比例 QC'
  };

  const LAYER_ZH = {
    fixed_threshold: '固定臨床閾值',
    baseline: '個人基準 ±2SD',
    rule: '生理決策規則',
    spe_rule: '太陽風暴連動規則',
    fast_track: '緊急快速通道規則',
    trend: '趨勢斜率預測',
    quality_check: 'Layer 0 品質閘門'
  };

  const DRAWER_ZH = {
    ppco2_1h_mmHg: '艙內 1 小時二氧化碳分壓 (mmHg)',
    proton_flux_10mev_pfu: 'GOES ≥10MeV 質子通量 (pfu)',
    crew_leq8_dBA: '乘員 8 小時噪音暴露 (dBA)',
    sleep_tst_h: 'Actiwatch 睡眠時數 (小時)',
    spe_alert: 'SPE 太陽質子風暴警報',
    rest_hr_bpm: '靜息心率 (bpm)',
    spo2_pct: '周邊血氧飽和度 SpO2 (%)',
    pvc_burden_pct: 'Holter 24小時 PVC 負荷 (%)',
    ijv_flow: '頸內靜脈 (IJV) 超音波血流',
    ijv_thrombus: '偵測到頸內靜脈血栓',
    csa_thigh_cm2: '大腿肌肉截面積 CSA (cm²)',
    velocity_loss_pct: 'E4D 深蹲速度衰減率 (%)',
    ctx: '骨吸收指標 CTX (ng/mL)',
    body_mass_kg: 'SLAMMD 微重力體重 (kg)',
    delta_trt_um: 'Mini OCT 視網膜厚度變化 ΔTRT (µm)',
    delta_v_onh_mm3: '視神經盤體積變化 ΔV_ONH (mm³)',
    onsd_mm: '超音波視神經鞘直徑 ONSD (mm)',
    sph_eq_shift_d: '遠視屈光偏移量 (Diopters)',
    folds_foveal: '出現黃斑部/脈絡膜皺摺',
    temp_c: '口腔體溫 (°C)',
    lymph: '淋巴球計數 (10⁹/L)',
    saliva_vzv: '唾液水痘病毒 VZV DNA (copies/mL)',
    hydration_ml: '24小時飲水量 (mL)'
  };

  const FLOW_OPT_ZH = {
    forward: '順向 (FORWARD)',
    stagnant: '滯留 (STAGNANT)',
    reversed: '逆流 (REVERSED)'
  };

  const EXACT_ZH = {
    'Nominal cabin ECLSS, radiation, acoustic, and sleep telemetry.': '艙內維生環控 (ECLSS)、輻射劑量、聲學噪音與睡眠監測皆正常。',
    'Continue daily Bio-Monitor morning vitals & planned CEVIS cycling.': '維持每日晨間穿戴式生理監測與既定 CEVIS 飛輪有氧訓練。',
    'Continue daily Bio-Monitor morning vitals & scheduled CEVIS Zone 2/4 cycling.': '維持每日晨間 Bio-Monitor 生理監測與既定 CEVIS 第 2/4 區間飛輪訓練。',
    'Continue daily oral temp, hydration log, and monthly Bio-Analyzer CBC.': '維持每日口腔體溫量測、飲水紀錄與每月一次 Bio-Analyzer 血球分析。',
    'Continue nominal 6-day/week E4D resistance & CEVIS countermeasure schedule; target VBT loss 20-30%.': '維持每週 6 天 E4D 抗阻與 CEVIS 對抗訓練；目標速度衰減區間 20–30%。',
    'Continue monthly Mini OCT, Amsler grid, and VOG vestibular checks.': '維持每月一次 Mini OCT 眼底掃描、阿姆斯勒方格表與 VOG 前庭平衡檢測。',
    'Continue standard ECLSS telemetry logging and weekly dosimeter readout.': '持續記錄標準 ECLSS 環控遙測並每週讀取一次個人輻射劑量計。',
    'Maintain current CEVIS aerobic conditioning + bi-weekly LBNP tolerance check.': '維持現行 CEVIS 有氧體能訓練，並每兩週執行一次 LBNP 下半身負壓耐受測試。',
    'Maintain current CEVIS aerobic conditioning + bi-weekly LBNP orthostatic tolerance check.': '維持現行 CEVIS 有氧體能訓練，並每兩週執行一次 LBNP 下半身負壓姿勢耐受測試。',
    'Administer 500-750 mL electrolyte fluid load and repeat Bio-Monitor + Holter check in 12h.': '立即補充 500–750 mL 電解質液，並於 12 小時後複檢 Bio-Monitor 與 Holter 心電監測。',
    'Shift CEVIS to Zone 2 steady aerobic conditioning (4x/week), add LBNP 3x/week, and re-evaluate in 7 days.': '將 CEVIS 調整為第 2 區間穩態有氧訓練（每週 4 次）、加入每週 3 次 LBNP 訓練，並於 7 天後重新評估。',
    'STOP all high-intensity CEVIS & heavy E4D resistance workouts immediately.': '立即停止所有高強度 CEVIS 飛輪與高負荷 E4D 阻力訓練。',
    'Perform Ultrasound 2 bilateral IJV compression sweep + 12-lead ECG + serum K+/clotting re-check.': '立即執行 Ultrasound 2 雙側頸內靜脈壓迫掃描、12 導程心電圖與血清鉀離子/凝血功能複檢。',
    'Suspend HIIT for 14 days; run daily resting ECG, potassium repletion, and LBNP orthostatic conditioning.': '暫停高強度間歇訓練 14 天；每日執行靜息心電圖、補鉀調整與 LBNP 姿勢耐受訓練。',
    'Verify Bio-Monitor ECG strap skin contact (quality >= 0.50), keep motion < 0.50 g, and confirm weekly BP cuff calibration.': '確認 Bio-Monitor 心電胸帶與皮膚貼合良好（訊號品質 ≥ 0.50）、動作干擾 < 0.50 g，並確認每週血壓袖帶校正。',
    'Sensor dropout, dry electrodes, or impossible readings (e.g., SpO2 < 50% or null HR) cannot safely evaluate heart or clot status.': '感測器斷訊、電極乾燥或生理不可能讀數（如 SpO2 < 50% 或心率遺失）無法安全評估心臟與血栓風險。',
    'Re-wet Bio-Monitor thoracic ECG pads and tighten chest strap.': '潤濕 Bio-Monitor 胸部心電電極片並拉緊胸帶。',
    'Clean optical SpO2 fingertip/wrist sensor and eliminate cabin vibration/motion for 60 seconds.': '清潔光學指尖/腕式血氧感測器，並保持靜止 60 秒以排除艙內震動干擾。',
    'Repeat resting vitals capture immediately before running clinical evaluation.': '進行臨床判讀前，請立即重新擷取靜息生命徵象。',
    'Inspect Bio-Monitor garment conductive pads and SpO2 clip during weekly hardware check.': '於每週硬體檢核時檢查 Bio-Monitor 導電織片與 SpO2 夾具。',
    'Wear Bio-Monitor shirt for resting HR/BP/SpO2/Resp; run 24h Holter (MIT-BIH check), CEVIS 150W test, LBNP stand test, and Ultrasound 2 GLS + neck IJV compression.': '穿著 Bio-Monitor 感測衣量測靜息心率/血壓/血氧/呼吸；執行 24h Holter 心律（MIT-BIH 驗證）、CEVIS 150W 測試、LBNP 站立測試與 Ultrasound 2 心臟應變 (GLS) 及頸內靜脈壓迫掃描。',
    'Microgravity shifts ~2L of fluid toward the head, shrinking plasma volume (%DeltaPV), causing neck vein stasis/clots (IJV), electrolyte-driven PVCs, and orthostatic fainting.': '微重力會將約 2 公升體液推向頭部，造成血漿容量萎縮 (%ΔPV)、頸內靜脈血液滯留/血栓 (IJV)、電解質異常誘發心室早搏 (PVC) 與直立性暈厥風險。',
    'Maintain Vitamin D3 supplementation (2000 IU/d) and 2.5 L/d renal hydration.': '持續補充維生素 D3 (2000 IU/日) 並維持每日 2.5 公升飲水以預防腎結石。',
    'Maintain current E4D progressive resistance schedule (weekly 168h verification).': '維持現行 E4D 漸進式抗阻訓練處方（每週 168 小時定期檢核）。',
    'Maintain baseline monthly SANS imaging & pre-landing vestibular drills.': '維持基準每月 SANS 眼科影像追蹤與著陸前前庭適應訓練。',
    'Read MCA CO2 bench, DOSTEL area/crew dosimeters, acoustic SPL meter, and wrist Actiwatch sync.': '讀取 MCA 二氧化碳分析儀、DOSTEL 區域/個人輻射劑量計、聲壓計並同步腕式 Actiwatch 睡眠資料。',
    'Cross-check primary MCA IR bench against portable Drager / backup CDRA CO2 monitor.': '使用手持式 Drager 或備用 CDRA 二氧化碳監測器交叉比對主 MCA 紅外線分析儀讀數。',
    'Wear Bio-Monitor shirt for resting HR/ECG; place Ultrasound 2 linear probe laterally on neck for IJV Doppler flow.': '穿著 Bio-Monitor 感測衣量測靜息心率與心電圖；將 Ultrasound 2 線性探頭置於頸部外側量測頸內靜脈 (IJV) 都卜勒血流。',
    'Wet Bio-Monitor thoracic electrodes lightly with water, tighten chest strap, and sit quietly for 60s.': '以清水微濕 Bio-Monitor 胸部電極片、拉緊胸帶並靜坐 60 秒後重新量測。',
    '1) Attach E4D VBT linear encoder & zero the load cell; log squat peak force, loading rate, reps, and intra-set velocity loss. 2) Scan pre-marked 50% mid-thigh & 30% proximal calf landmarks with Ultrasound 2. 3) Record morning SLAMMD body mass and run Bio-Analyzer NTX/CTX/P1NP fingerstick/urine cartridge.': '1) 安裝 E4D 速度編碼器並歸零荷重元，記錄深蹲峰值力、發力率與組內速度衰減。2) 使用 Ultrasound 2 掃描預先標記的大腿中段 50% 與小腿近端 30% 位置。3) 記錄晨間 SLAMMD 體重並執行 Bio-Analyzer 骨代謝指標 (NTX/CTX/P1NP) 檢測。',
    '1) Zero the E4D load cell with no cable tension. 2) Apply acoustic gel to Ultrasound 2 linear probe at the pre-marked 30% proximal calf & 50% mid-thigh skin tattoos. 3) Verify readings sit inside physiological bounds (Calf CSA 25-200 cm^2, Thigh CSA 50-350 cm^2) before logging.': '1) 於無拉索張力下將 E4D 荷重元歸零。2) 在預先標記的小腿 30% 與大腿 50% 標記處塗抹超音波耦合劑進行掃描。3) 確認數值落於生理合理區間（小腿 25–200、大腿 50–350 cm²）再上傳紀錄。',
    'Capture registered Mini OCT macular/ONH cube, perform Amsler grid monocular test, and measure ONSD 3 mm behind globe via Ultrasound 2.': '擷取已對位基準之 Mini OCT 黃斑部/視神經盤體積掃描，執行單眼阿姆斯勒方格測試，並用 Ultrasound 2 量測眼球後 3mm 視神經鞘直徑 (ONSD)。',
    'Dim cabin light, stabilize head on Mini OCT chinrest, fixate green cross, and verify Auto-Register lock.': '調暗艙內照明，將下巴穩靠於 Mini OCT 支架，注視綠色十字並確認自動對位鎖定 (Auto-Register) 亮燈。',
    'Measure oral temp before eating/drinking; collect morning saliva swab; run Bio-Analyzer fingerstick CBC.': '於進食飲水前量測口腔體溫；採集晨間唾液拭子；執行 Bio-Analyzer 指尖採血全血球計數 (CBC)。',
    'Warm finger 60s, wipe first blood drop, fill Bio-Analyzer cartridge bubble-free, and insert within 30s.': '溫熱手指 60 秒後拭去第一滴血，確保卡匣無氣泡後於 30 秒內插入 Bio-Analyzer 判讀。',
    'Hostile closed-cabin air, CO2 buildup, noise fatigue, and solar proton storms directly impair cognition, immunity, and optic nerve health.': '封閉太空艙內的二氧化碳累積、噪音疲勞與太陽質子風暴會直接損害認知判斷力、免疫功能與視神經健康。',
    'A frozen CO2 sensor hides rising cabin ppCO2, risking headaches and SANS optic nerve swelling.': '凍結卡死的 CO2 感測器會掩蓋艙內二氧化碳升高，導致頭痛與 SANS 視神經水腫風險。',
    'Microgravity shifts ~2L of fluid toward the head, shrinking plasma volume and risking neck vein stasis/clots (IJV) or orthostatic fainting.': '微重力會使約 2 公升體液湧向頭部，導致血漿容量下降並引發頸內靜脈血流滯留/血栓 (IJV) 或姿勢性暈厥風險。',
    'Motion artifact or dry skin creates false arrhythmia alarms.': '皮膚乾燥或肢體晃動會造成心電圖假性心律不整警報。',
    "Without Earth's 1g gravity, weight-bearing leg muscles rapidly shrink and bone calcium dissolves into the bloodstream (raising fracture and kidney-stone risk before Mars landing). Tracking E4D mechanical stimulus (S_bone, VBT 20-30% zone), muscle cross-section, and bone turnover keeps countermeasures effective offline.": '在缺乏地球 1g 重力下，下肢負重肌群會快速萎縮且骨鈣溶出至血液中（大幅提高火星著陸前骨折與腎結石風險）。透過追蹤 E4D 機械刺激指數、肌肉截面積與骨代謝指標，可離線確保對抗訓練確實有效。',
    'Corrupted or implausible measurements (such as a 999 cm^2 ultrasound artifact or missing force cell) must be blocked before decision logic runs so false alarms or missed bone/muscle loss do not occur.': '異常或超出人體極限的感測器偽影（例如 999 cm² 超音波誤判或荷重元斷訊）必須在進入醫療決策前先攔截，避免誤報或漏判骨肌流失。',
    'Spaceflight Associated Neuro-ocular Syndrome (SANS) flattens the back of the eye and swells the optic nerve due to headward fluid shift and elevated CO2.': '太空飛行相關神經眼症候群 (SANS) 是因微重力體液頭向轉移加上艙內偏高的 CO2，造成眼球後壁變平與視神經盤水腫。',
    'Unregistered OCT scans can misread micron-level retinal swelling.': '未成功與基準影像對位的 OCT 掃描會導致微米級視網膜厚度變化判讀失準。',
    'Space radiation, isolation stress, and microgravity suppress T-cell immunity, reactivating latent viruses (VZV/EBV) and raising kidney stone risk.': '太空輻射、孤立壓力與微重力會抑制 T 細胞免疫力，促使體內潛伏病毒（水痘 VZV / EBV）再活化並升高腎結石風險。',
    'Clotted or micro-bubbled fingerstick samples cause false neutropenia readings.': '指尖血樣凝固或混入氣泡會造成儀器分選錯誤，產生假性嗜中性球低下警示。',
    'Run 30-min LBNP at -20 mmHg to reduce cephalad venous stasis.': '執行 30 分鐘 -20 mmHg 下半身負壓 (LBNP) 訓練，以減輕頭部靜脈血液鬱積。',
    'Hydrate +500 mL electrolyte solution and repeat resting vitals in 12h.': '立即補充 500 mL 電解質液並於 12 小時後複檢靜息生命徵象。',
    'Shift CEVIS to Zone 2 steady aerobic conditioning (4x/week) and add LBNP 3x/week.': '將 CEVIS 調整為第 2 區間穩態有氧訓練（每週 4 次）並增加每週 3 次 LBNP 訓練。',
    'STOP all strenuous E4D & high-intensity CEVIS exercise immediately.': '立即停止所有高強度 E4D 重訓與高強度 CEVIS 間歇騎乘。',
    'Perform Ultrasound 2 bilateral IJV compression sweep + 12-lead ECG capture.': '立即以 Ultrasound 2 掃描雙側頸內靜脈 (IJV) 壓迫試驗並擷取 12 導程心電圖。',
    'If IJV thrombus/reversed flow: initiate onboard anticoagulation checklist & LBNP -25 mmHg.': '若確認 IJV 血栓或逆流：啟動隨艦抗凝血處置清單並執行 -25 mmHg LBNP。',
    'Suspend HIIT for 14 days; daily resting ECG, potassium monitoring, and LBNP orthostatic conditioning.': '暫停高強度間歇訓練 14 天；每日追蹤靜息心電圖、血鉀濃度並執行 LBNP 耐受調整。',
    'Re-seat Bio-Monitor chest strap and capture clean 60s ECG.': '重新固定 Bio-Monitor 胸帶電極並擷取一段乾淨的 60 秒靜息心電圖。',
    'Re-wet Bio-Monitor ECG strap and repeat resting recording.': '潤濕 Bio-Monitor 心電胸帶電極後重新執行靜息心電圖紀錄。',
    'Inspect Bio-Monitor electrode pads during weekly maintenance.': '於每週設備維護時檢查 Bio-Monitor 電極片接觸狀況。',
    'Increase E4D squat/deadlift load +5% with faster concentric loading rate to push S_bone >= 0.90 and VBT loss into 20-30%.': '將 E4D 深蹲/硬舉負荷提升 +5% 並加快向心發力速度，使骨骼刺激指數 S_bone ≥ 0.90 且 VBT 落在 20–30%。',
    'Add 1 extra unilateral heel-raise / posterior-chain set and confirm protein >= 1.6 g/kg/day.': '增加 1 組單腳提踵與後側鏈訓練，並確保每日蛋白質攝取 ≥ 1.6 g/kg。',
    'Schedule follow-up Ultrasound 2 thigh/calf & E4D check in 72 hours.': '安排 72 小時後複檢 Ultrasound 2 大小腿截面積與 E4D 訓練數據。',
    '+5% E4D squat/deadlift load progression with higher loading rate; repeat Ultrasound CSA & bone markers in 72h–7d.': '將 E4D 深蹲/硬舉負荷漸進增加 +5% 並提高發力率；於 72 小時至 7 天內複檢超音波肌肉截面積與骨代謝指標。',
    'STOP the fatigued E4D set immediately if VBT velocity loss > 30% and alert ground Flight Surgeon.': '若 VBT 速度衰減超過 30% 請立即停止該組訓練，並通報地面航太醫師。',
    'Shift next session to controlled eccentric/hypertrophy loading (cap VBT loss <= 25%) and verify Cardio/Immune clearance.': '下次訓練改為受控離心與肌肥大負荷（速度衰減上限 ≤ 25%），並確認心血管與免疫系統已解除紅燈管制。',
    'Verify hydration >= 2.8 L/day, +20g post-workout whey/leucine, and Vitamin D3/Ca intake; repeat Ultrasound 2 scan within 24h.': '確認每日飲水 ≥ 2.8 公升、運動後補充 20g 乳清蛋白/白胺酸與維生素 D3/鈣片，並於 24 小時內複掃超音波。',
    '24h ground alert + 4-week progressive lower-limb hypertrophy block, +350 kcal/day protein surplus, and 14-day Bio-Analyzer CTX/NTX & Ultrasound CSA re-evaluation.': '發出 24 小時地面醫療通報＋啟動 4 週下肢肌肥大強化週期、每日增加 +350 kcal 高蛋白熱量盈餘，並於 14 天後重測 CTX/NTX 與肌肉截面積。',
    'Sensor QC rejected implausible value(s). Recalibrate and repeat measurement immediately.': 'Layer 0 品質閘門攔截到異常讀數，請立即重新校正並重測。',
    'Check E4D cable pin lock and Ultrasound 2 probe contact.': '檢查 E4D 拉索插銷鎖定與 Ultrasound 2 探頭貼合度。',
    'Re-measure immediately (next_measurement_in_hours = 0) before starting heavy sets.': '在進行大重量訓練前請立即重測（複檢間隔 = 0 小時）。',
    'Verify E4D & Ultrasound 2 calibration checklist prior to each session.': '每次訓練前請依檢核表確認 E4D 與 Ultrasound 2 校正狀態。',
    'Equip Space Anticipation Glasses if near-vision blur occurs (+0.75 D shift).': '若出現近距離視力模糊（遠視偏移 ≥ +0.75 D），請立即換戴太空調節眼鏡。',
    'Schedule bi-weekly Mini OCT & cross-check cabin ppCO2 levels.': '安排每兩週一次 Mini OCT 追蹤並交叉確認艙內 ppCO2 濃度。',
    'Increase Mini OCT cadence to every 14 days and add 3x/week LBNP fluid unloading.': '將 Mini OCT 檢查頻率提高至每 14 天一次，並加入每週 3 次 LBNP 體液減壓訓練。',
    'Notify Flight Surgeon immediately for Grade-2+ SANS / foveal fold protocol.': '立即通報地面航太醫師啟動 Grade-2+ SANS／黃斑皺摺處置程序。',
    'Run 45-min LBNP at -25 mmHg and keep sleeping torso slightly elevated / avoid head-down posture.': '執行 45 分鐘 -25 mmHg LBNP 減壓，睡眠時維持軀幹微墊高並避免頭低腳高姿勢。',
    'Repeat Mini OCT & Amsler grid check in 24 hours; verify cabin ppCO2 < 2.0 mmHg.': '於 24 小時後複測 Mini OCT 與阿姆斯勒方格表，並確認艙內 ppCO2 < 2.0 mmHg。',
    'Weekly Mini OCT + Ultrasound ONSD surveillance + daily LBNP fluid-shift countermeasure for 30 days.': '連續 30 天執行每週 Mini OCT ＋ 超音波 ONSD 監測 ＋ 每日 LBNP 體液轉移對抗訓練。',
    'Re-acquire registered Mini OCT scan immediately.': '請立即重新拍攝已對位基準之 Mini OCT 眼底掃描。',
    'Repeat Mini OCT scan until quality score >= 6.0 and baseline registration passes.': '重新執行 Mini OCT 掃描直到影像品質分數 ≥ 6.0 且基準對位成功。',
    'Verify optical window cleanliness on Mini OCT monthly.': '每月清潔並檢查 Mini OCT 光學鏡頭視窗。',
    'Schedule Bio-Analyzer CBC check in 48 hours (especially if SPE alert triggered).': '安排 48 小時後執行 Bio-Analyzer CBC 血球追蹤（尤其在太陽風暴警報觸發後）。',
    'Boost fluid intake to >= 2500 mL/day and prioritize >= 7.5h sleep.': '提升每日飲水量至 ≥ 2500 mL，並確保每晚睡眠 ≥ 7.5 小時。',
    'Weekly saliva viral qPCR & sleep/stress load reduction over next 14 days.': '未來 14 天每週執行一次唾液病毒 qPCR 檢測並降低睡眠/心理負荷。',
    'Isolate crew member in sleep quarters if fever >= 38.0 C or active VZV skin vesicles present.': '若發燒 ≥ 38.0°C 或出現水痘皮膚水泡，立即於個人睡眠艙進行醫療隔離。',
    'Initiate onboard Valacyclovir / broad-spectrum medical kit protocol per offline Flight Surgeon guide.': '依離線航太醫療手冊啟動隨艦抗病毒藥物 (Valacyclovir) 或廣效醫療包治療程序。',
    'Run Bio-Analyzer CBC & hydration log every 12h (mandatory 48h post-SPE if solar storm active).': '每 12 小時追蹤一次 Bio-Analyzer CBC 與飲水紀錄（若發生太陽風暴，48 小時後必須強制抽血複檢）。',
    'Suspend strenuous exercise; 14-day antiviral/recovery course + sleep optimization >= 8h/night.': '暫停劇烈體能訓練；執行 14 天抗病毒/康復療程並確保每晚睡眠 ≥ 8 小時。',
    'Re-run Bio-Analyzer CBC immediately to clear QC warning.': '請立即重測 Bio-Analyzer CBC 以排除樣本分選異常警示。',
    'Re-run Bio-Analyzer CBC with fresh cartridge.': '更換全新檢測卡匣並重新執行 Bio-Analyzer CBC。',
    'Inspect Bio-Analyzer optical reader during weekly maintenance.': '於每週設備保養時檢查 Bio-Analyzer 光學判讀頭。',
    'Hold high-load E4D squats/deadlifts until Cardiovascular & Immune return to YELLOW/GREEN.': '在心血管與免疫系統恢復至黃燈或綠燈前，持續暫停高負荷 E4D 深蹲與硬舉訓練。',

    // Role 6: 17-Card Cabin Environment corpus
    'Execute Layer-0 QC checks across DOSTEL/GOES radiation, Type-1 SLM/dosimeter/OOHA acoustics, MCA/CDRA/THC/AQM/TOCA/microbial habitat loops, and Actiwatch/PVT-B/Bedford behavioral assays.': '依序執行 Layer 0 品質檢核：DOSTEL/GOES 輻射偵測、Type-1 聲壓計/個人噪音計/OOHA 聽力測驗、MCA/CDRA/THC/AQM/TOCA 氣水微生物環控迴路，以及 Actiwatch 睡眠、PVT-B 警覺度與 Bedford 工作負荷量測。',
    'Integrates 17 closed-habitat, radiation, acoustic, and circadian-isolation cards across 3 NASA RIDGE hazards to provide autonomous offline decision support (all Red actions end with a human decision).': '整合 17 張封閉艙段環控、太空輻射、聲學噪音與生理節律監測卡（涵蓋 NASA 輻射/孤立/封閉環境三大危害），提供離線自主醫療決策支援（所有紅燈處置均保留人工最終確認）。',
    'All 17 Radiation, Acoustics, Atmosphere, and Isolation cards nominal; continue scheduled monitoring.': '全部 17 項輻射、聲學、大氣水質環控與孤立節律監測卡皆正常，請持續定期監測。',
    '[RAD-01] Verify DOSTEL/IV-TEPC detector health and await next non-SAA 1-h mean.': '[RAD-01 區域劑量] 檢查 DOSTEL/IV-TEPC 偵測器健康狀態，並等待下一個非南大西洋異常區 (non-SAA) 1 小時均值。',
    '[RAD-01] Verify non-SAA orbital position and cross-check RAD-03 proton flux.': '[RAD-01 區域劑量] 確認軌道非處於南大西洋異常區 (SAA) 並交叉比對 RAD-03 太陽質子通量。',
    '[RAD-01] Relocate prolonged work tasks to higher-shielding module locations.': '[RAD-01 區域劑量] 將長時間作業移往具較高輻射遮蔽厚度之艙段執行。',
    '[RAD-01] Move to the most shielded area; in Orion, line cabin walls with stowage.': '[RAD-01 區域劑量] 立即移動至遮蔽最完善區域；若於獵戶座艙，以儲物包覆蓋艙壁加強屏蔽。',
    '[RAD-01] Terminate EVA immediately and notify flight surgeon (human decision).': '[RAD-01 區域劑量] 立即終止艙外活動 (EVA) 並通報航太醫師進行人工決策。',
    '[RAD-01] ALARA; missions > 6 months: >= 20 g/cm² shielding plus 10 cm water-equivalent storm shelter in crew quarters.': '[RAD-01 長期處方] 落實 ALARA 最小合理暴露原則；超過 6 個月任務須維持 ≥20 g/cm² 屏蔽與睡眠區 10 cm 等效水牆避難空間。',
    '[RAD-01] ALARA; missions > 6 months: >= 20 g/cm² shielding plus a 10 cm water-equivalent storm shelter in crew quarters (rearranged water containers).': '[RAD-01 長期處方] 落實 ALARA 原則；超過 6 個月任務於乘員艙維持 ≥20 g/cm² 屏蔽與 10 cm 水箱風暴掩體。',
    '[RAD-02] Complete 24-h module location log and sync Crew Passive/Active Dosimeter.': '[RAD-02 個人劑量] 補齊 24 小時艙段停留紀錄並同步乘員主/被動輻射劑量計。',
    '[RAD-02] Increase sleep/work hours in high-shielding modules and review remaining EVA dose budget.': '[RAD-02 個人劑量] 增加高屏蔽艙段內之睡眠與工作時數，並重新審查剩餘 EVA 劑量預算。',
    '[RAD-02] Restrict unshielded module/EVA exposure immediately; flight surgeon & mission management review required (human decision).': '[RAD-02 個人劑量] 立即限制無遮蔽艙段停留與艙外活動；須經航太醫師與任務管理層人工審查。',
    '[RAD-02] Log daily module occupancy and sleep inside higher-shielded crew quarters.': '[RAD-02 長期處方] 每日記錄艙段分佈並於高屏蔽睡眠區就寢。',
    '[RAD-02] Enforce ALARA scheduling, polyethylene/water sleep-station shielding, and personal active dosimeter cross-checks.': '[RAD-02 長期處方] 執行 ALARA 排程、強化睡眠站聚乙烯/水層遮蔽並定期交叉核對主動式個人劑量計。',
    '[RAD-03] Switch to GOES secondary satellite / DONKI backup feed; verify local RAD-01 DOSTEL/HERA.': '[RAD-03 太陽風暴] 切換至 GOES 備用衛星／DONKI 備援資料源，並檢核本地 RAD-01 DOSTEL/HERA 讀數。',
    '[RAD-03] Review EVA schedule and pre-position storm shelter water/stowage supplies.': '[RAD-03 太陽風暴] 檢視艙外活動排程並預先於輻射掩體就位飲水與儲物屏蔽物資。',
    '[RAD-03] Increase RAD-01 evaluation to every 5 min.': '[RAD-03 太陽風暴] 將 RAD-01 輻射評估頻率提高至每 5 分鐘一次。',
    '[RAD-03] Move crew to the most shielded storm shelter area immediately; terminate any planned/ongoing EVA.': '[RAD-03 太陽風暴] 立即將全體乘員撤離至遮蔽最強之風暴掩體；終止任何進行中或預定之 EVA。',
    '[RAD-03] Increase RAD-01 telemetry readout to 5-min cadence and notify ground & flight surgeon for human decision.': '[RAD-03 太陽風暴] 將 RAD-01 遙測頻率提升至 5 分鐘並通報地面與航太醫師進行人工決策。',
    '[RAD-03] Maintain dual GOES primary/secondary ground-to-ship telemetry and local HERA alerting.': '[RAD-03 長期處方] 維持 GOES 主/備雙衛星地面遙測與艦上本地 HERA 自主預警系統。',
    '[RAD-03] Maintain automated SWPC GOES primary/secondary feed + onboard HERA local trigger for deep-space comm-delay autonomy.': '[RAD-03 長期處方] 維持自動化 SWPC GOES 雙通道與本地 HERA 觸發機制，確保深空通訊延遲下的自主防輻射能力。',
    '[ACO-01] Perform field acoustic calibrator check and repeat octave-band survey.': '[ACO-01 艙內噪音] 使用聲學校正器檢核測音儀後，重新執行八音度頻帶量測。',
    '[ACO-01] Inspect fan mufflers/vibration isolators and use hearing protection during extended tasks in module.': '[ACO-01 艙內噪音] 檢查風扇消音器與減震墊；於該艙段長時間作業時請配戴護耳裝備。',
    '[ACO-01] Don hearing protection immediately, isolate noisy rack/pump, notify ground & flight surgeon (human decision).': '[ACO-01 艙內噪音] 立即戴上護耳裝備、隔離高噪音機櫃或幫浦，並通報地面與航太醫師。',
    '[ACO-01] Verify SLM calibration before and after every monthly acoustic survey.': '[ACO-01 長期處方] 每月聲壓量測前後皆須執行聲壓計 (SLM) 現場校正。',
    '[ACO-01] Maintain acoustic blankets, clean fan intake screens, and enforce NC-50 work / NC-40 sleep envelopes.': '[ACO-01 長期處方] 維護隔音毯與風扇進氣濾網，落實工作區 NC-50、睡眠區 NC-40 噪音規範。',
    '[ACO-02] Repeat 24-h personal noise dosimetry session ensuring >=20 h uncovered wear.': '[ACO-02 個人噪音] 重新執行 24 小時個人噪音劑量佩戴，確保未遮蔽有效佩戴時間 ≥20 小時。',
    '[ACO-02] Use sleep earplugs / ANR headset during noisy work and inspect sleep-station ventilation.': '[ACO-02 個人噪音] 高噪音作業配戴降噪耳機/耳塞並檢查睡眠艙通風口噪音。',
    '[ACO-02] Mandate ANR hearing protection, quiet sleep quarters, schedule ACO-03 audiogram & flight surgeon review (human decision).': '[ACO-02 個人噪音] 強制配戴主動降噪護耳設備、改至安靜睡眠區休息，並安排 ACO-03 聽力檢查與醫師審查。',
    '[ACO-02] Schedule 24-h personal noise dosimetry every 60 mission days.': '[ACO-02 長期處方] 每 60 任務日定期執行一次 24 小時個人噪音劑量監測。',
    '[ACO-02] Perform 24-h personal dosimetry every 60 days; wear hearing protection for tasks >80 dBA.': '[ACO-02 長期處方] 每 60 天執行個人噪音監測；遇 >80 dBA 作業須強制配戴聽力防護。',
    '[ACO-03] Repeat pure-tone audiometry inside quiet NC-40 berth and confirm within-frequency repeatability <=10 dB.': '[ACO-03 聽力閾值] 於 NC-40 安靜睡眠艙內重測純音聽力，確認同頻率重測誤差 ≤10 dB。',
    '[ACO-03] Reduce noise exposure, verify headset volume, and schedule follow-up retest audiogram.': '[ACO-03 聽力閾值] 降低噪音暴露、檢核通訊耳機音量上限並排程複測聽力圖。',
    '[ACO-03] Enforce auditory rest + ANR hearing protection; notify ground & flight surgeon for clinical human decision.': '[ACO-03 聽力閾值] 強制執行聽覺休息與主動降噪防護，並通報地面與航太醫師進行臨床評估。',
    '[ACO-03] Perform periodic OOHA/KUDUwave hearing checks in quiet sleep station.': '[ACO-03 長期處方] 定期於安靜睡眠站內執行 OOHA/KUDUwave 聽力檢測。',
    '[ACO-03] Conduct periodic KUDUwave/OOHA audiograms and cross-reference with ACO-01/ACO-02 noise logs.': '[ACO-03 長期處方] 定期執行聽力檢查並與 ACO-01/ACO-02 噪音暴露紀錄交叉比對。',
    '[ATM-01] Cross-check primary MCA IR bench against portable CO2 meter and backup CDRA sensor immediately.': '[ATM-01 艙內 CO2] 立即以手持式 CO2 偵測器與備用 CDRA 感測器比對主 MCA 紅外線讀數。',
    '[ATM-01] Check CDRA and ventilation, prompt headache/vision self-report.': '[ATM-01 艙內 CO2] 檢查 CDRA 除碳器與通風循環，並要求乘員回報是否有頭痛或視力模糊。',
    '[ATM-01] Increase CO2 removal or move crew to a better-ventilated module; notify flight surgeon if headache is reported (human decision).': '[ATM-01 艙內 CO2] 提高除碳效率或將乘員移至通風較佳艙段；若有頭痛症狀立即通報航太醫師。',
    '[ATM-01] Perform scheduled MCA zero/span calibration and verify inter-module air mixing fans.': '[ATM-01 長期處方] 定期執行 MCA 零點/跨距校正並確認跨艙氣體混合風扇運轉正常。',
    '[ATM-01] Maintain 7-day rolling ppCO2 < 2.5 mmHg, clean air diffusers, and avoid stagnant sleep-berth CO2 pockets.': '[ATM-01 長期處方] 維持 7 日移動平均 ppCO2 < 2.5 mmHg，定期清潔風口避免睡眠艙二氧化碳積聚。',
    '[ATM-02] Verify dual cabin pressure transducers and MCA O2 partial pressure bench.': '[ATM-02 氣壓與氧氣] 檢核雙重艙壓感測器一致性與 MCA 氧分壓分析儀狀態。',
    '[ATM-02] Inspect N2/O2 pressure control assembly (PCA) valves and check hull hatch seals with ultrasonic leak detector.': '[ATM-02 氣壓與氧氣] 檢查 N2/O2 壓力控制閥 (PCA) 並以超音波測漏儀巡檢艙門氣密墊片。',
    '[ATM-02] Execute depressurization emergency procedure; notify ground and flight surgeon immediately (human decision).': '[ATM-02 氣壓與氧氣] 立即執行失壓/低氧緊急應變程序並通報地面與航太醫師。',
    '[ATM-02] Maintain redundant pressure transducers calibrated to 101.3 kPa nominal setpoint.': '[ATM-02 長期處方] 維持備援壓力感測器校正於 101.3 kPa 標準艙壓設定點。',
    '[ATM-02] Maintain 101.3 kPa total pressure, PIO2 139–168 mmHg, O2 <= 23.5%, and unobstructed hatch seals.': '[ATM-02 長期處方] 維持 101.3 kPa 總壓、PIO2 139–168 mmHg、氧濃度 ≤23.5% 與艙門密封清潔。',
    '[ATM-03] Cross-check THC sensor with portable psychrometer and verify fan airflow across sensor.': '[ATM-03 溫濕度] 使用可攜式乾濕球溫度計比對 THC 感測器，並確認探頭氣流暢通。',
    '[ATM-03] Keep cabin within 20–25 °C and 30–60% RH performance zone.': '[ATM-03 長期處方] 將艙內溫濕度維持於 20–25 °C 與 30–60% 相對濕度舒適效能區間。',
    '[ATM-03] Maintain THC performance zone (20–25 °C, 30–60% RH) to prevent heat stress and surface condensation.': '[ATM-03 長期處方] 維持 THC 溫濕度目標區間（20–25 °C、30–60% RH）以防熱壓力與艙壁結露。',
    '[ATM-04] Run AQM calibration check and verify cabin air with colorimetric Drager tubes if odor noticed.': '[ATM-04 揮發氣體] 執行 AQM 氣相層析校正檢核；若聞到異味立即以 Drager 檢知管採樣。',
    '[ATM-04] Verify TCCS charcoal bed life and AQM carrier gas supply.': '[ATM-04 長期處方] 定期確認 TCCS 活性碳濾床壽命與 AQM 載氣鋼瓶存量。',
    '[ATM-04] Enforce strict flight material off-gassing screening, log alcohol-wipe usage, and maintain TCCS beds.': '[ATM-04 長期處方] 嚴格控管酬載除氣篩檢、記錄酒精擦拭用量並維護 TCCS 除毒濾床。',
    '[ATM-04] Maintain TCCS charcoal/catalyst beds, AQM internal check standards, and accessible PBA respirators.': '[ATM-04 長期處方] 維護 TCCS 活性碳/觸媒床、AQM 內校標準與隨手可得之緊急呼吸器 (PBA)。'
  };

  function t(key, vars = {}) {
    const dict = I18N[state.lang] || I18N.en;
    let txt = dict[key] !== undefined ? dict[key] : (I18N.en[key] !== undefined ? I18N.en[key] : key);
    Object.keys(vars).forEach(k => {
      txt = String(txt).replace('{' + k + '}', vars[k]);
    });
    return txt;
  }

  function modShortName(modId, fallback) {
    const dict = I18N[state.lang] || I18N.en;
    return (dict.mod_short && dict.mod_short[modId]) || fallback || modId;
  }

  function modFullName(modId, fallback) {
    const dict = I18N[state.lang] || I18N.en;
    return (dict.mod_full && dict.mod_full[modId]) || fallback || modId;
  }

  function zhText(raw) {
    if (raw === null || raw === undefined) return '';
    const s = String(raw).trim();
    if (state.lang !== 'zh') return s;
    if (EXACT_ZH[s]) return EXACT_ZH[s];

    let out = s;
    out = out.replace(/^17-Card Status: GREEN$/, '17 項環控與輻射監測卡：全數正常 GREEN');
    out = out.replace(/^17-Card Status: (YELLOW|RED|NO_DATA) \| ([^=]+)=(.+)$/, (_, st, key, list) => {
      const lbl = st === 'RED' ? '危急 RED' : (st === 'YELLOW' ? '預警 YELLOW' : '品質檢核異常 NO_DATA/QC');
      return `17 項環控監測卡：${lbl}｜異常卡片：${list}`;
    });
    out = out.replace(/^\[(ATM-0[567]|ISO-0[1-4])\]\s*/, '[$1] ');
    out = out.replace(/^cabin_environment\.spe_alert -> immune_metabolic\.spe_event_flag$/, '艙內輻射風暴警報 (SPE) ➔ 免疫代謝模組（觸發 48h 淋巴球複檢）');
    out = out.replace(/^cabin_environment\.ppco2_1h_mmHg \(([^)]+)\) -> neuro_ocular$/, '艙內 ppCO2 濃度 ($1 mmHg) ➔ 神經眼壓 SANS 協同判讀');
    out = out.replace(/^CO2-SANS SYNERGY ALERT: Cabin ppCO2 \(([^)]+)\) elevates intracranial venous congestion risk alongside Neuro-Ocular findings\. Prioritize CDRA scrubber inspection and avoid head-down tilt or prolonged supine posture\.$/, 'CO2-SANS 協同風險警報：艙內二氧化碳分壓 ($1) 與神經眼壓異常同時發生，將顯著提高顱內靜脈鬱積風險。請優先檢查 CDRA 除碳器並避免頭低位姿勢。');
    out = out.replace(/^SAFETY OVERRIDE: Heavy E4D axial resistance loading & maximal CEVIS intervals SUSPENDED due to (.+)\. Switch to light passive ROM \/ hydration monitoring only\.$/, '安全衝突強制介入：由於 $1，系統已自動暫停高負荷 E4D 軸向抗阻與高強度 CEVIS 訓練，僅保留輕度關節活動與水分補充監測。');
    out = out.replace(/^SPE SHELTER OVERRIDE: Relocate crew to Water Wall \/ storm shelter immediately\. Defer non-essential E4D\/CEVIS sessions and schedule mandatory 48h post-SPE CBC lymphocyte check\.$/, '太陽質子風暴避難介入：立即將乘員撤離至 Water Wall 輻射掩體。延後非必要體能訓練並自動排入 48 小時後 CBC 淋巴球追蹤。');
    out = out.replace(/Cardiovascular RED \(arrhythmia \/ IJV thrombosis \/ hemodynamic alert\)/g, '心血管系統紅燈（心律不整 / 頸內靜脈血栓 / 血流動力警示）');
    out = out.replace(/Immune RED \(fever \/ acute inflammatory or viral reactivation alert\)/g, '免疫系統紅燈（發燒 / 急性發炎或病毒再活化警示）');

    out = out.replace(/^ppCO2 ([\d.]+) mmHg, Proton ([\d.]+) pfu \(SPE=(True|False)\), LEQ8 ([\d.]+) dBA, Sleep ([\d.]+)h\.$/, (_, a, b, c, d, e) => `艙內 CO2 ${a} mmHg｜質子通量 ${b} pfu (風暴=${c === 'True' ? '是' : '否'})｜8h噪音 ${d} dBA｜睡眠 ${e} 小時`);
    out = out.replace(/^Rest HR ([\d.]+) bpm, SpO2 ([\d.]+)%, IJV '([^']+)', PVC ([\d.]+)%\.$/, (_, a, b, c, d) => `靜息心率 ${a} bpm｜血氧 ${b}%｜頸靜脈血流 '${c === 'forward' ? '順向' : (c === 'stagnant' ? '滯留' : '逆流')}'｜PVC ${d}%`);
    out = out.replace(/^Rest HR ([\d.]+) bpm, BP ([\d.]+\/[\d.]+), SpO2 ([\d.]+)%, PVC ([\d.]+)%, IJV '([^']+)', %DeltaPV ([+-]?[\d.]+)%\.(?: \| (.+))?$/, (_, hr, bp, spo2, pvc, ijv, pv, corr) => {
      const ijvZh = ijv === 'forward' ? '順向' : (ijv === 'stagnant' ? '滯留' : '逆流');
      const base = `靜息心率 ${hr} bpm｜血壓 ${bp}｜血氧 ${spo2}%｜PVC ${pvc}%｜頸靜脈 '${ijvZh}'｜血漿容量 ${pv}%`;
      return corr ? `${base}｜${zhText(corr)}` : base;
    });
    out = out.replace(/^PE \/ HYPOXIA CORRELATION \(M3\+M4->M9\): Low SpO2 \+ Tachypnea \(>25\/min\) [—-] perform immediate bilateral IJV Ultrasound 2 clot check and verify cabin O2\/ppCO2\.$/, '肺栓塞 / 低血氧關聯警示 (M3+M4→M9)：低血氧併發呼吸急促 (>25次/分) — 立即執行雙側頸內靜脈 (IJV) 超音波血栓檢查並核對艙內氧氣/ppCO2。');
    out = out.replace(/^ARRHYTHMIA-ELECTROLYTE CORRELATION \(M5\+M11\): Elevated PVC burden \(([\d.]+)%\) paired with hypokalemia \(K\+=([\d.]+) mmol\/L\) [—-] administer oral KCl and repeat ECG\.$/, '心律不整-電解質關聯警示 (M5+M11)：心室早搏負荷偏高 ($1%) 併發低血鉀 (K+=$2 mmol/L) — 給予口服氯化鉀 (KCl) 並複測心電圖。');
    out = out.replace(/^RHYTHM-ELECTROLYTE CHECK \(M5->M11\): Elevated PVC burden \(([\d.]+)%\) [—-] verify serum K\+ >= 3\.5 mmol\/L before exercise\.$/, '心律-電解質檢核 (M5→M11)：心室早搏負荷偏高 ($1%) — 運動前請先確認血清鉀 K+ ≥ 3.5 mmol/L。');
    out = out.replace(/^ORTHOSTATIC-HYPOVOLEMIA CORRELATION \(M6\+M10\): Orthostatic intolerance paired with ([+-]?[\d.]+)% plasma volume loss [—-] initiate oral salt\+fluid loading\.$/, '直立不耐-低血容關聯警示 (M6+M10)：直立耐受不良併發血漿容量流失 ($1%) — 立即啟動口服鹽水與液體補充。');
    out = out.replace(/^S_bone=([\d.]+), VBT=([\d.]+)%, Thigh=([^,]+), Calf=([^,]+), CTX=([^,]+), Est Hip Loss=([^\s]+)\.$/, (_, a, b, c, d, e, f) => `骨骼刺激 S_bone=${a}｜速度衰減 ${b}%｜大腿 ${c}｜小腿 ${d}｜骨吸收 CTX ${e}｜推估髖骨流失 ${f}`);
    out = out.replace(/^(OD|OS) delta TRT \+([\d.]+) um, delta V_ONH \+([\d.]+) mm3, ONSD ([\d.]+) mm(?: \| Cross-context cabin ppCO2=([\d.]+) mmHg)?\.$/, (_, eye, trt, vonh, onsd, co2) => `${eye} 眼視網膜 ΔTRT +${trt} µm｜視神經盤 ΔV_ONH +${vonh} mm³｜ONSD ${onsd} mm` + (co2 ? `｜連動艙內 ppCO2=${co2} mmHg` : ''));
    out = out.replace(/^Temp ([\d.]+) C, Lymph ([\d.]+) \(([^)]+)\), VZV ([\d.]+), SPE=(True|False)\.$/, (_, temp, ly, dp, vzv, spe) => `體溫 ${temp}°C｜淋巴球 ${ly} (${dp})｜水痘病毒 VZV ${vzv}｜風暴警報=${spe === 'True' ? '是' : '否'}`);
    out = out.replace(/^MCA CO2 sensor flatlined for ([\d.]+)h \(>=24h stuck-sensor QC fault\)\.$/, 'MCA 二氧化碳感測器讀數已凍結 $1 小時（觸發 ≥24h 故障閘門）。');
    out = out.replace(/^Bio-Monitor ECG \/ PTT lead quality below 0\.50 threshold\.$/, 'Bio-Monitor 心電/脈搏波導極訊號品質低於 0.50 門檻，請重新貼合電極。');
    out = out.replace(/^Mini OCT QC failed for (OD|OS) \(score=([\d.]+), registered=(True|False)\)\.$/, '$1 眼 Mini OCT 品質檢核未通過（品質分=$2，對位=$3），請重新掃描。');
    out = out.replace(/^Bio-Analyzer QC failed: Neutrophil fraction ([\d.]+)% < 10% \(possible sample mis-sort\)\.$/, 'Bio-Analyzer 品質檢核失敗：嗜中性球比例僅 $1% (<10%)，疑為採血分選異常。');
    out = out.replace(/^Layer 0 QC Gatekeeper rejected telemetry:/, 'Layer 0 品質閘門已攔截異常遙測：');
    return out;
  }

  function metricLabel(name) {
    if (state.lang !== 'zh') return name;
    return METRIC_ZH[name] || name;
  }

  function layerLabel(decidedBy) {
    if (state.lang !== 'zh') return decidedBy || 'rule';
    return LAYER_ZH[decidedBy] || decidedBy || 'rule';
  }

  function ruleLabel(rule) {
    if (state.lang !== 'zh') return rule;
    const map = {
      HALT_HEAVY_EXERCISE_ON_CARDIO_OR_IMMUNE_RED: '安全衝突強制暫停重訓 (心血管/免疫紅燈)',
      SPE_SHELTER_AND_48H_LYMPHOCYTE_CHECK: '太陽風暴避難與 48h 淋巴球複檢連動',
      CO2_SANS_SYNERGY_MITIGATION: 'CO2 與 SANS 眼壓協同風險處置'
    };
    return map[rule] || rule;
  }
"""
