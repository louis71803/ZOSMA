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
      dev_mode_label: 'DEVELOPER MODE',
      dev_mode_desc: 'Show simulation presets, RTC fast-forward & manual overrides',
      dev_mode_on: 'DEV MODE ON',
      dev_mode_off: 'FLIGHT MODE',
      drawer_btn: '⚙ SETTINGS & TELEMETRY',
      manual_on: 'MANUAL ON',
      rtc_offline_tag: 'OFFLINE RTC',
      rtc_due_now: 'DUE NOW',
      rtc_due_in: 'DUE IN {t}',
      rem_banner_title: 'SCHEDULED MEDICAL CHECK DUE:',
      rem_mark_done: '✓ MARK CHECKED & RESET TIMER',
      rem_mute: '🔇 MUTE',
      rem_unmute: '🔔 SOUND ON',
      clk_section_title: 'OFFLINE SPACECRAFT RTC & TRIAGE TIMERS',
      clk_section_desc: 'Autonomous onboard clock (zero network dependency). Adjust date/time or fast-forward to test triage reminders.',
      clk_date_lbl: 'SHIP DATE (YYYY-MM-DD)',
      clk_time_lbl: 'SHIP TIME (HH:MM:SS)',
      clk_apply_btn: 'SYNC CLOCK',
      clk_now_btn: '⟳ SET TO EARTH NOW',
      clk_speed_lbl: 'TIME RATE:',
      clk_jump_lbl: 'SIMULATE ELAPSED:',
      clk_sound_lbl: 'Reminder Chime',
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
      cross_link_title: 'CROSS-INDICATOR CLINICAL LINK',
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
      src_partial: 'PARTIAL CSV',
      src_sim: 'SIMULATED',
      src_demo: 'SYNTHETIC DEMO',
      shared_real_lbl: 'Shared OSDR',
      missing_files_lbl: 'Missing {n} file(s)',
      gen_csv_btn: 'GENERATE DEMO CSV TEMPLATES IN data/',
      sim_disclaimer: 'Displayed values are simulated data generated from published ISS loss rates, not actual astronaut measurements.',
      urgent_escalation_banner: '🚨 URGENT ESCALATION: Report to ground at the next communication pass.',
      qc_trend_blocked: 'Invalid / insufficient measurement (Layer 0 QC). Trend points and 30-day projection are withheld until re-measured.',
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
      dev_mode_label: '開發者模式 / DEVELOPER MODE',
      dev_mode_desc: '開啟模擬情境切換、RTC 時鐘快轉與手動感測器微調',
      dev_mode_on: '開發者模式',
      dev_mode_off: '航太執勤模式',
      drawer_btn: '⚙ 設定與感測器微調',
      manual_on: '手動覆寫中',
      rtc_offline_tag: '離線時鐘 RTC',
      rtc_due_now: '立即複檢！',
      rtc_due_in: '倒數 {t}',
      rem_banner_title: '排程時間已到 · 應執行醫療檢測：',
      rem_mark_done: '✓ 已完成檢測（重設倒數）',
      rem_mute: '🔇 靜音',
      rem_unmute: '🔔 開啟提示音',
      clk_section_title: '離線太空站主時鐘 (RTC) 與定時提醒校正',
      clk_section_desc: '無須網路連線之隨艦本地時間系統；可手動校準日期時間，或加速時間測試到時提醒。',
      clk_date_lbl: '艦上日期 (YYYY-MM-DD)',
      clk_time_lbl: '艦上時間 (HH:MM:SS)',
      clk_apply_btn: '套用離線校時',
      clk_now_btn: '⟳ 設定為目前時間',
      clk_speed_lbl: '時間流速：',
      clk_jump_lbl: '快轉測試：',
      clk_sound_lbl: '到期提示音效',
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
      cross_link_title: '跨指標臨床關聯警示',
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
      src_partial: '部分 CSV',
      src_sim: '模擬資料',
      src_demo: '模擬示範',
      shared_real_lbl: '共享 OSDR',
      missing_files_lbl: '缺 {n} 檔',
      gen_csv_btn: '在 data/ 生成範本 CSV 檔案',
      sim_disclaimer: '展示數值為模擬數據，依已發表的太空站流失率產生，並非真實太空人測量值。',
      urgent_escalation_banner: '🚨 緊急上報：下次通訊立即回報地面。',
      qc_trend_blocked: '測量無效（Layer 0 品質檢核未通過）：不繪製無效點與 30 天趨勢預測線，請立即重測。',
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
    osd575_ca_alp_baseline: '血清鈣/ALP 參考基準',
    musculoskeletal_qc_gatekeeper: '骨骼肌肉 QC 閘門',
    sensor_qc_ok: '感測器品質檢核 (QC)',
    qc_csa_calf_cm2: '小腿截面積 QC 檢核',
    qc_csa_thigh_cm2: '大腿截面積 QC 檢核',
    qc_incomplete_telemetry: '遙測欄位完整性檢核',
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

    // Role 2: Updated Musculoskeletal fixed reference & 4-group 3-step guidance corpus
    'Target >= 0.90': '目標 ≥ 0.90',
    'Target range 20-30%': '目標區間 20–30%',
    'ISS average 1.0-1.5%/mo': '太空站平均 1.0–1.5%/月',
    'Serum calcium remains stable during flight; basic check only and does not reflect bone loss severity.': '血鈣在飛行中維持穩定，僅作基本檢查，不代表骨流失程度。',
    'Reference value only; not used for status light evaluation.': '僅供參考，不參與燈號判定。',
    'Invalid measurement. Check probe contact and load-cell zeroing, then re-measure immediately.': '測量無效，請檢查探頭接觸與荷重元歸零後立即重測。',
    'Urgent escalation: Report to ground at the next communication pass.': '緊急上報：下次通訊立即回報地面。',
    'Follow current prescription.': '照原處方。',
    'Built-in reference (non-NASA data)': '內建參考值（非 NASA 資料）',
    'NASA OSDR OSD-575': 'NASA OSDR OSD-575 血清鈣/ALP',
    '1) Push with maximum effort on every repetition during resistance training; E4D automatically records force and velocity for each rep. 2) Velocity loss equals the percentage drop in mean velocity from the fastest rep to the last rep in each set. 3) Isometric strength: once per week, pull maximally against the fixed bar for 3 repetitions and take the maximum value.': '1) 阻力訓練時每一下都盡全力推起，E4D 自動記錄每下的力量與速度。2) 速度衰減＝每組最快一下到最後一下的平均速度下降百分比。3) 等長肌力：每週一次，對固定桿全力拉，重複 3 次取最大值。',
    'In microgravity, muscle strength drops by an average of 10%-12%, and about 12%-38% of crewmembers lose more than 20%, impairing EVA capability and post-landing mobility. Resistance training is the primary countermeasure, and intensity matters more than repetition count.': '失重下肌力平均下降 10%–12%，約 12%–38% 的組員下降超過 20%，會影響出艙與著陸後的行動能力。阻力訓練是最主要的對策，重點在強度而不是次數。',
    '1) Once per week, scan the quadriceps and gastrocnemius using Ultrasound 2 in panoramic mode. 2) Use the pre-flight positioning template selected by leg length and sweep the probe smoothly along the template in one pass. 3) Repeat 3 times at the same site and average the values. Calf readings have higher variance; follow the trend rather than a single scan.': '1) 每週一次，以 Ultrasound 2 全景模式掃描股四頭肌與腓腸肌。2) 使用發射前依腿長選定的定位模板，探頭沿模板一次掃完。3) 同一位置連測 3 次取平均。小腿數值誤差較大，請看趨勢、不看單次。',
    'After about 6 months on the ISS, crew lost 10%-16% of calf muscle volume and 4%-7% of thigh volume (MRI study of 4 crewmembers). Lower-limb muscle loss increases the risk of falls and injury after landing.': '在太空站約 6 個月後，組員小腿肌肉體積減少 10%–16%，大腿減少 4%–7%（4 名組員的 MRI 研究）。下肢肌肉流失會讓著陸後更容易跌倒或受傷。',
    '1) Measure at the same time of day each session. 2) Wrap legs and torso securely around the SLAMMD mount and remain still. 3) Record the spring-driven readout and average consecutive measurements.': '1) 每次都在同一時段測量。2) 雙腿與身體環抱 SLAMMD 支架，保持不動。3) 彈簧推動後由系統讀數，連測取平均。',
    'Body mass loss is usually caused by insufficient caloric intake. A 5%-10% loss requires attention, and over 10% is critical.': '體質量下降多半是因為吃得不夠。下降 5%–10% 需要關注，超過 10% 屬嚴重。',
    '1) Draw fasting blood in the morning; sample at the same time of day each session for comparability. 2) Bone loss rate is a modeled estimate: BMD cannot be measured directly in flight and is confirmed post-flight by DXA. 3) Note: On the ISS, samples are frozen and returned to Earth for analysis; onboard real-time testing is a planned feature of this system.': '1) 晨間空腹採血；每次都在同一時段採樣，結果才能互相比較。2) 骨流失率為推估值：飛行中無法直接測骨密度，返回後以 DXA 確認。3) 註：太空站目前是將樣本冷凍送回地面分析；船上即時檢測為本系統的規劃功能。',
    'In microgravity, bone resorption increases by about 50% and bone mineral density declines by an average of 1%-1.5% per month, most prominently at the hip. Lost bone calcium is excreted in urine (serum calcium remains normal), increasing kidney stone risk.': '失重下骨吸收約增加 50%，骨密度平均每月流失 1%–1.5%，髖部最明顯。流失的鈣由尿液排出（血鈣維持正常），會提高腎結石風險。',
    '[Training] 1) Push with maximum effort on every repetition during resistance training; E4D automatically records force and velocity for each rep. 2) Velocity loss equals the percentage drop in mean velocity from the fastest rep to the last rep in each set. 3) Isometric strength: once per week, pull maximally against the fixed bar for 3 repetitions and take the maximum value. | [Muscle CSA] 1) Once per week, scan the quadriceps and gastrocnemius using Ultrasound 2 in panoramic mode. 2) Use the pre-flight positioning template selected by leg length and sweep the probe smoothly along the template in one pass. 3) Repeat 3 times at the same site and average the values. Calf readings have higher variance; follow the trend rather than a single scan. | [Body Mass] 1) Measure at the same time of day each session. 2) Wrap legs and torso securely around the SLAMMD mount and remain still. 3) Record the spring-driven readout and average consecutive measurements. | [Bone Metabolism] 1) Draw fasting blood in the morning; sample at the same time of day each session for comparability. 2) Bone loss rate is a modeled estimate: BMD cannot be measured directly in flight and is confirmed post-flight by DXA. 3) Note: On the ISS, samples are frozen and returned to Earth for analysis; onboard real-time testing is a planned feature of this system.': '【訓練指標】1) 阻力訓練時每一下都盡全力推起，E4D 自動記錄每下的力量與速度。2) 速度衰減＝每組最快一下到最後一下的平均速度下降百分比。3) 等長肌力：每週一次，對固定桿全力拉，重複 3 次取最大值。\n【肌肉截面積】1) 每週一次，以 Ultrasound 2 全景模式掃描股四頭肌與腓腸肌。2) 使用發射前依腿長選定的定位模板，探頭沿模板一次掃完。3) 同一位置連測 3 次取平均。小腿數值誤差較大，請看趨勢、不看單次。\n【體質量】1) 每次都在同一時段測量。2) 雙腿與身體環抱 SLAMMD 支架，保持不動。3) 彈簧推動後由系統讀數，連測取平均。\n【骨代謝】1) 晨間空腹採血；每次都在同一時段採樣，結果才能互相比較。2) 骨流失率為推估值：飛行中無法直接測骨密度，返回後以 DXA 確認。3) 註：太空站目前是將樣本冷凍送回地面分析；船上即時檢測為本系統的規劃功能。',
    '[Training] In microgravity, muscle strength drops by an average of 10%-12%, and about 12%-38% of crewmembers lose more than 20%, impairing EVA capability and post-landing mobility. Resistance training is the primary countermeasure, and intensity matters more than repetition count. | [Muscle CSA] After about 6 months on the ISS, crew lost 10%-16% of calf muscle volume and 4%-7% of thigh volume (MRI study of 4 crewmembers). Lower-limb muscle loss increases the risk of falls and injury after landing. | [Body Mass] Body mass loss is usually caused by insufficient caloric intake. A 5%-10% loss requires attention, and over 10% is critical. | [Bone Metabolism] In microgravity, bone resorption increases by about 50% and bone mineral density declines by an average of 1%-1.5% per month, most prominently at the hip. Lost bone calcium is excreted in urine (serum calcium remains normal), increasing kidney stone risk.': '【訓練指標】失重下肌力平均下降 10%–12%，約 12%–38% 的組員下降超過 20%，會影響出艙與著陸後的行動能力。阻力訓練是最主要的對策，重點在強度而不是次數。\n【肌肉截面積】在太空站約 6 個月後，組員小腿肌肉體積減少 10%–16%，大腿減少 4%–7%（4 名組員的 MRI 研究）。下肢肌肉流失會讓著陸後更容易跌倒或受傷。\n【體質量】體質量下降多半是因為吃得不夠。下降 5%–10% 需要關注，超過 10% 屬嚴重。\n【骨代謝】失重下骨吸收約增加 50%，骨密度平均每月流失 1%–1.5%，髖部最明顯。流失的鈣由尿液排出（血鈣維持正常），會提高腎結石風險。',
    'Complete full range of motion, push every rep maximally, and finish any incomplete sets for this week.': '動作幅度做完整、每下全力推，補足本週未完成的組數。',
    'Starting from the next workout, increase squat, deadlift, and calf-raise load by approximately +5%.': '下次訓練起提高深蹲、硬舉、提踵負荷約 5%。',
    'Stop the fatigued set immediately today and switch to recovery training.': '今天立即停止該組，改做恢復訓練。',
    'Report to ground at the next communication pass.': '下次通訊上報地面。',
    'Confirm training targets are met; consume 1.2-1.8 g protein per kg body mass daily with adequate calories.': '確認訓練達標；每日蛋白質達每公斤體重 1.2–1.8 g，熱量吃足。',
    'Starting from the next workout, increase lower-limb load by approximately +5% and add 1 set of calf raises.': '下次訓練起提高下肢負荷約 5%，並增加 1 組提踵訓練。',
    'Re-measure once immediately to rule out measurement error; then follow up during weekly routine checks.': '立即重測一次以排除測量誤差；之後於每週例行檢查時追蹤。',
    'Log dietary intake for 3 days and add high-calorie foods.': '記錄飲食 3 天並補充高熱量食物。',
    'Report to ground at the next communication pass so the medical team can adjust nutrition.': '下次通訊上報地面，由醫療團隊調整營養處方。',
    'Confirm resistance training targets are met; take Vitamin D 1000 IU daily; hydrate to maintain daily urine output above 2 L.': '確認阻力訓練達標；每日補充維生素 D 1000 IU；多喝水維持每日尿量 > 2 公升。',
    'Report to ground at the next communication pass for flight surgeon medication decision; increase monitoring frequency.': '下次通訊上報地面，由航太醫師評估藥物處置並提高監測頻率。',
    'Follow current prescription; weekly (168h) E4D, isometric strength, body mass, and Ultrasound CSA checks; bone markers >= 14 days.': '照原處方執行；每週 (168h) 進行 E4D、等長肌力、體質量與超音波肌肉截面積檢查；骨代謝指標間隔 ≥ 14 天。',
    'Complete full range of motion and slow eccentric control without increasing load; recheck E4D, isometric strength, and body mass in 72h, Ultrasound CSA >= 7 days, bone markers >= 14 days.': '維持原負荷並確實做好完整動作幅度與離心控制；72 小時後複檢 E4D、等長肌力與體質量（超音波 ≥ 7 天、骨代謝指標 ≥ 14 天）。',
    'Stop fatigued set today and switch to recovery training; recheck E4D, isometric strength, and body mass in 72h, Ultrasound CSA >= 7 days, bone markers >= 14 days.': '今日立即停止疲勞組並改為恢復訓練；72 小時後複檢 E4D、等長肌力與體質量（超音波 ≥ 7 天、骨代謝指標 ≥ 14 天）。',
    'Starting from the next workout, increase E4D load by approximately +5% or add sets; recheck E4D, isometric strength, and body mass in 24h, Ultrasound CSA >= 7 days, bone markers >= 14 days.': '下次訓練起提高 E4D 負荷約 +5% 或增加組數；24 小時後複檢 E4D、等長肌力與體質量（超音波 ≥ 7 天、骨代謝指標 ≥ 14 天）。',

    // Role 3: M0-M11 indicator titles & per-metric 3-step guidance (GREEN / YELLOW / RED / BAD_DATA)
    'M0: Layer 0 Bio-Monitor QC Gatekeeper': 'M0：Layer 0 感測器品質閘門',
    'M1: Resting Heart Rate (Bio-Monitor)': 'M1：靜息心率 (Bio-Monitor)',
    'M2: Blood Pressure (PTT + Cuff & PRCP)': 'M2：血壓 PTT 與袖帶校正',
    'M3: Oxygen Saturation SpO2 (Bio-Monitor)': 'M3：血氧飽和度 SpO2',
    'M4: Breathing Rate (Bio-Monitor)': 'M4：靜息呼吸頻率',
    'M5: Heart Rhythm & PVC Burden (Holter + MIT-BIH)': 'M5：心律與 PVC 早搏負荷 (Holter)',
    'M6: Orthostatic Tolerance (LBNP/Stand + PRCP)': 'M6：直立耐受性 (LBNP / 站立測試)',
    'M7: Aerobic Fitness 150W Bike HR Drift (CEVIS)': 'M7：CEVIS 150W 有氧心率飄移',
    'M8: Myocardial Strain GLS (Ultrasound 2)': 'M8：心肌應變 GLS (Ultrasound 2)',
    'M9: IJV Neck Vein Flow & Clot (Ultrasound 2)': 'M9：頸內靜脈血流與血栓 (Ultrasound 2)',
    'M10: Plasma Volume %DeltaPV (Dill & Costill / OSD-569)': 'M10：血漿容量變化 %ΔPV (OSD-569)',
    'M11: Serum Blood Chemistry (K+, CRP, Clotting / OSD-575)': 'M11：血清生化鉀/CRP/凝血 (OSD-575)',

    // M1-M11 how_to_measure
    'Wet Bio-Monitor thoracic electrodes with sterile wipe, fasten strap snugly at xiphoid level, and sit still for 60 seconds.': '以無菌濕巾潤濕 Bio-Monitor 胸部電極，將胸帶貼緊劍突高度並靜坐 60 秒。',
    'Sit or float relaxed for 5 minutes wearing the Bio-Monitor thoracic ECG shirt; confirm signal quality >= 0.50 and avoid caffeine 2 hours before testing.': '穿著 Bio-Monitor 心電感測衣靜坐或飄浮放鬆 5 分鐘；確認訊號品質 ≥ 0.50，且測前 2 小時勿攝取咖啡因。',
    'Continuous Bio-Monitor Pulse Transit Time (PTT) estimates beat-to-beat BP; calibrate once a week with the manual upper-arm cuff held at heart level.': '由 Bio-Monitor 脈搏波傳導時間 (PTT) 連續估算血壓；每週使用手動上臂袖帶於與心臟同高位置校正一次。',
    'Place the Bio-Monitor optical clip on a warm finger or wrist sensor pad and wait 20 seconds for a steady wave.': '將 Bio-Monitor 光學血氧夾置於溫暖的手指或腕部感測墊，等待 20 秒取得穩定波形。',
    'The Bio-Monitor chest strap counts resting breaths automatically while you sit or float quietly for 60 seconds.': '靜坐或飄浮安靜休息 60 秒時，Bio-Monitor 胸帶會自動計算靜息呼吸次數。',
    'Attach the 5-lead Holter Monitor 2 for 24 hours; onboard software checks beat shapes against MIT-BIH arrhythmia templates.': '配戴 5 導程 Holter Monitor 2 連續記錄 24 小時；隨艦軟體將自動比對 MIT-BIH 心律不整樣板。',
    'Seal waist in the LBNP negative-pressure chamber (-25/-40 mmHg) or perform a 3-min post-landing stand test while recording HR and BP.': '腰部密封進入 LBNP 下半身負壓艙 (-25/-40 mmHg)，或於著陸後執行 3 分鐘站立測試並同步記錄心率與血壓。',
    'Pedal CEVIS at a steady 150 Watts for 10 minutes and average your ECG heart rate over the final 3 minutes.': '在 CEVIS 飛輪以固定 150 瓦踩踏 10 分鐘，取最後 3 分鐘的心電心率平均值。',
    'Use Ultrasound 2 from the chest apex to capture 4-, 3-, and 2-chamber cine loops for automated GLS tracking.': '使用 Ultrasound 2 自心尖位置擷取心室 4 腔、3 腔與 2 腔動態影像，由系統自動計算 GLS 心肌應變。',
    'Place the Ultrasound 2 linear probe on the side of your neck: check that the vein collapses easily with gentle pressure and shows steady forward color Doppler flow.': '將 Ultrasound 2 線性探頭輕置於頸部外側：確認輕壓探頭時靜脈能完全壓扁，且彩色都卜勒呈穩定順向血流。',
    'Run a fingerstick Bio-Analyzer CBC cartridge for Hemoglobin (Hb) and Hematocrit (Hct); the system computes %DeltaPV automatically.': '以指尖採血執行 Bio-Analyzer CBC 卡匣測得血紅素 (Hb) 與血比容 (Hct)，系統將自動計算 %ΔPV。',
    'Insert a lithium-heparin capillary/venous cartridge into the onboard Bio-Analyzer chemistry reader.': '將肝素鋰微血管／靜脈採血卡匣插入隨艦 Bio-Analyzer 生化判讀儀。',
    'GUARDED CHECK: Rest quietly for 5 minutes in the Bio-Monitor shirt (no caffeine for 2 hours prior) and compare against your morning hydration and sleep log.': '警戒複檢：穿著 Bio-Monitor 感測衣安靜休息 5 分鐘（2 小時內勿喝咖啡），並對照今早飲水與睡眠紀錄。',
    'VERIFY WITH ARM CUFF: Run a manual brachial arm-cuff check at heart height to confirm the Bio-Monitor Pulse Transit Time (PTT) reading.': '袖帶複核：在與心臟同高位置以手動上臂血壓計量測一次，驗證 Bio-Monitor PTT 血壓讀數。',
    'WARNING (<96%): Warm your fingertip, confirm snug optical sensor fit, wait 20 seconds for clean waveform lock, and cross-check your breathing rate (M4).': '血氧偏低 (<96%)：先溫熱指尖、確認光學夾具貼合並等待 20 秒鎖定波形，同時比對呼吸頻率 (M4)。',
    'GUARDED (>20/min): Sit still for 60 seconds wearing the Bio-Monitor chest band and check cabin ppCO2.': '呼吸偏快 (>20次/分)：穿著 Bio-Monitor 胸帶靜坐 60 秒重測，並立即檢視艙內 ppCO2。',
    'ELEVATED EXTRA BEATS: Continue wearing the 5-lead Holter Monitor 2 (MIT-BIH pattern check) and run a Bio-Analyzer fingerstick test for serum Potassium (M11).': '心室早搏增加：繼續配戴 5 導程 Holter（MIT-BIH 型態分析），並立即以 Bio-Analyzer 指尖採血確認血鉀濃度 (M11)。',
    'ORTHOSTATIC WARNING: Seal your waist in the LBNP chamber (-20 to -40 mmHg) or run a 3-min stand test while logging HR rise and blood pressure drop.': '直立耐受預警：進入 LBNP 負壓艙 (-20 至 -40 mmHg) 或執行 3 分鐘站立測試，同步記錄心率升幅與血壓降幅。',
    'FITNESS DRIFT CHECK: Hydrate well beforehand, cycle on CEVIS at a steady 150W for 10 minutes, and average your ECG heart rate over the last 3 minutes.': '體能飄移檢核：測前充分補水後，於 CEVIS 以固定 150W 踩踏 10 分鐘，取最後 3 分鐘平均心率。',
    'STRAIN WARNING: Re-capture Ultrasound 2 apical 4-, 3-, and 2-chamber views ensuring crisp heart-wall borders for speckle tracking.': '心肌應變預警：重新擷取清晰的 Ultrasound 2 心尖 4/3/2 腔影像，確保心壁邊緣清楚以利應變追蹤。',
    'STASIS CHECK: Scan both left and right neck IJV with Ultrasound 2 color Doppler and confirm the vein still collapses flat under light probe pressure.': '血流滯留檢查：以 Ultrasound 2 彩色都卜勒掃描左右兩側頸內靜脈，確認輕壓下血管仍可完全扁塌。',
    'CHECK BIO-ANALYZER Hb/Hct: Insert fingerstick CBC cartridge to calculate %DeltaPV change from pre-flight baseline.': '檢核 Hb/Hct：插入 Bio-Analyzer 指尖採血 CBC 卡匣，計算相較發射前基準之血漿容量變化 %ΔPV。',
    'CHEMISTRY CHECK: Insert lithium-heparin cartridge into Bio-Analyzer and verify K+, CRP, and clotting markers.': '生化檢核：插入肝素鋰生化卡匣至 Bio-Analyzer，確認血鉀 K+、CRP 與凝血指標。',
    'CRITICAL RE-CHECK: Float or sit completely still for 5 minutes wearing the Bio-Monitor shirt. Confirm ECG strap skin contact >= 0.50 and motion < 0.50 g, and check your oral temperature before repeating.': '危急複檢：穿著 Bio-Monitor 感測衣完全靜止 5 分鐘，確認心電接觸品質 ≥ 0.50、動作干擾 < 0.50 g，並先量測口腔體溫再重測。',
    'URGENT VERIFICATION: Do not rely on the Bio-Monitor wrist/chest estimate alone. Measure your blood pressure manually with the upper-arm cuff at heart level on both arms.': '緊急人工複核：勿僅依賴穿戴式估算值，請立即在心臟同高位置以手動袖帶分別量測雙臂血壓。',
    'EMERGENCY HYPOXIA CHECK: Warm your finger for 30 seconds, clip the optical SpO2 sensor securely, wait 20 seconds for a steady pulse wave, and immediately check cabin O2/CO2 and neck vein (M9) ultrasound.': '緊急低血氧處置：溫熱手指 30 秒並夾緊 SpO2 感測器取得穩定脈搏波，立即核對艙內 O2/CO2 並掃描頸內靜脈 (M9)。',
    'CRITICAL BREATHING CHECK: Float or sit calmly for 60 seconds so the Bio-Monitor chest band measures true resting breaths/min, then check SpO2 (M3) and cabin CO2 immediately.': '危急呼吸檢核：保持靜止 60 秒取得真實靜息呼吸頻率，並立即聯動檢視血氧 SpO2 (M3) 與艙內 CO2。',
    'CRITICAL RHYTHM CHECK: Capture an immediate 12-lead ECG, keep the 5-lead Holter Monitor 2 running, and test blood Potassium (K+) using the Bio-Analyzer fingerstick cartridge.': '危急心律檢核：立即擷取 12 導程心電圖、保持 5 導程 Holter 持續記錄，並以 Bio-Analyzer 立即測血鉀 K+。',
    'PRESYNCOPE ALERT: Stop the LBNP suction or Stand Test immediately if you feel dizzy, lightheaded, or tunnel-visioned. Lie/float flat and record recovery HR and BP.': '昏厥前兆警報：若感到頭暈、眼花或視野變窄，立即停止 LBNP 負壓或站立測試，平躺/平浮並記錄恢復期心率與血壓。',
    'DO NOT RUN MAXIMAL BIKE TEST: Pause the CEVIS 150W protocol. Check resting HR, Holter rhythm, heart ultrasound (GLS), and neck vein (IJV) scan first.': '禁止執行高負荷飛輪測試：立即暫停 CEVIS 150W 測試，優先檢查靜息心率、Holter 心律、心臟超音波 (GLS) 與頸靜脈 (IJV)。',
    'CRITICAL HEART STRAIN SCAN: Acquire clear Ultrasound 2 apical 4-, 3-, and 2-chamber heart views and pair with blood CRP/clotting markers (M11).': '危急心肌應變掃描：擷取清晰的 Ultrasound 2 心尖 4/3/2 腔切面，並對照血液 CRP 與凝血指標 (M11)。',
    'EMERGENCY NECK CLOT SCAN: Glide the Ultrasound 2 linear probe gently over left and right neck veins. Document reversed Doppler flow or non-collapsing clot—do NOT press hard enough to dislodge a thrombus.': '緊急頸部血栓掃描：將 Ultrasound 2 線性探頭輕滑過左右頸部靜脈，記錄都卜勒逆流或無法壓扁之血栓影像——切勿用力按壓以免血栓脫落。',
    'RUN BIO-ANALYZER CBC: Test fingerstick Hemoglobin (Hb) and Hematocrit (Hct) immediately to track fluid depletion via Dill & Costill (1974).': '立即執行 Bio-Analyzer CBC：以指尖採血量測 Hb 與 Hct，依 Dill & Costill (1974) 公式計算體液流失率。',
    'URGENT CHEMISTRY PANEL: Run a fresh Bio-Analyzer lithium-heparin cartridge to confirm serum Potassium (K+), Fibrinogen, PF4, and CRP.': '緊急血液生化檢驗：使用全新肝素鋰卡匣上機確認血鉀 K+、纖維蛋白原 (Fibrinogen)、PF4 與 CRP。',

    // M1-M11 why_in_space
    'Microgravity shifts chest shape and reduces skin moisture; dry electrodes or motion cause false PVC/SpO2 alarms.': '微重力會改變胸廓形狀並使皮膚較乾燥；電極乾燥或晃動容易造成心室早搏與血氧假警報。',
    "Extra heartbeats are minimal (0.30%, no AFib), showing your heart's electrical wiring and mineral balance are steady.": '心室早搏極少 (0.30%，無心房顫動)，代表心臟電生理傳導與礦物質平衡十分穩定。',
    'Even though weightlessness pushes fluid toward your head, forward and collapsible neck vein flow confirms there is no dangerous blood pooling or clot.': '雖然失重會將體液推向頭部，但頸內靜脈維持順向血流且可輕易壓扁，證實目前無危險血液鬱積或血栓。',
    'Plasma volume change (-5.0%) is mild and within normal spaceflight adaptation limits.': '血漿容量變化 (-5.0%) 屬輕微範圍，符合正常的太空飛行生理適應。',
    'Serum potassium (4.15 mmol/L), electrolytes, and clotting proteins are balanced, protecting heart rhythm and vessel health.': '血清鉀 (4.15 mmol/L)、電解質與凝血蛋白均在平衡範圍，有助維持心律穩定與血管健康。',
    'Plasma volume is down -15.8% (warning <= -12%). Microgravity makes your kidneys shed extra water, shrinking total circulating blood volume.': '血漿容量下降 -15.8%（預警 ≤ -12%）。微重力會促使腎臟排出較多水分，使總循環血量縮減。',
    'Borderline blood chemistry (K+ 3.45 mmol/L or rising CRP/Fibrinogen) increases heart-rhythm irritability and inflammation.': '血液生化逼近臨界（K+ 3.45 mmol/L 或 CRP/纖維蛋白原上升），會增加心肌電位不穩與血管發炎風險。',
    "Neck vein status is CRITICAL (flow='reversed', thrombus=True). Weightlessness shifts ~2 L of blood into your head/neck, stalling vein drainage until a clot forms—which can travel to your lungs (fatal pulmonary embolism).": '頸靜脈狀態危急（血流逆流、疑似血栓）。失重使約 2 公升血液湧入頭頸部，靜脈回流停滯容易形成血栓，進而有飄移至肺部造成致命肺栓塞之風險。',
    'Plasma blood volume dropped -22.1% (red limit <= -20%). Your blood is overly concentrated, sharply raising fainting risk (M6) and clot viscosity (M9).': '血漿容量驟降 -22.1%（紅線 ≤ -20%）。血液過度濃縮會大幅提高直立暈厥 (M6) 與血栓黏稠度風險 (M9)。',
    'Blood chemistry is critical (K+ 3.05 mmol/L or elevated clotting/inflammation markers). Low potassium triggers dangerous heart rhythms (M5), while high Fibrinogen/PF4 increases neck-vein clot risk (M9).': '血液生化達危急警戒（K+ 3.05 mmol/L 或凝血/發炎指標過高）。低血鉀會誘發危險心律不整 (M5)，高纖維蛋白原/PF4 則升高頸靜脈血栓風險 (M9)。',

    // M1-M11 action_steps
    'Continue daily morning Bio-Monitor vitals logging.': '持續每日晨間 Bio-Monitor 基礎生命徵象記錄。',
    'Maintain 2.5 L/day fluid intake.': '維持每日 2.5 公升足量飲水。',
    'Continue weekly manual arm-cuff calibration.': '維持每週一次手動上臂血壓袖帶校正。',
    'No blood pressure adjustment needed.': '血壓正常，無需額外處置調整。',
    'Continue routine Bio-Monitor oxygen logging.': '維持常規 Bio-Monitor 血氧監測記錄。',
    'Continue standard daily Bio-Monitor tracking.': '維持標準每日 Bio-Monitor 呼吸追蹤。',
    'Continue scheduled Holter surveillance and normal CEVIS workouts.': '維持排程 Holter 監測與正常 CEVIS 飛輪訓練。',
    'Keep bi-weekly LBNP tolerance checks on schedule.': '依原訂排程每兩週執行一次 LBNP 負壓耐受測試。',
    'Continue current CEVIS Zone 2/4 aerobic schedule.': '維持現行 CEVIS 第 2/4 區間有氧體能訓練課表。',
    'Maintain monthly Ultrasound 2 heart check.': '維持每月一次 Ultrasound 2 心臟超音波檢查。',
    'Continue routine monthly bilateral neck IJV ultrasound screening.': '維持每月例行雙側頸內靜脈超音波篩檢。',
    'Maintain 2.5 L/day hydration target.': '維持每日 2.5 公升補水目標。',
    'Continue routine monthly Bio-Analyzer blood chemistry checks.': '維持每月例行 Bio-Analyzer 血液生化追蹤。',
    'Drink 500-750 mL of water with electrolyte tablets over the next hour.': '於未來 1 小時內分次飲用 500–750 mL 含電解質錠之飲水。',
    'Prioritize at least 7.5 hours of sleep tonight and skip high-intensity sprints today.': '今晚確保至少 7.5 小時睡眠，今日暫停高強度衝刺訓練。',
    'Repeat your resting Bio-Monitor check in 12 hours.': '12 小時後複檢一次靜息 Bio-Monitor 量測。',
    'Recalibrate the Bio-Monitor with the arm cuff today.': '今日使用上臂血壓袖帶重新校正 Bio-Monitor。',
    'Check cabin ppCO2 (< 2.5 mmHg) and review your sodium/fluid intake.': '檢查艙內 ppCO2（需 < 2.5 mmHg）並檢視鈉與水分攝取量。',
    'Re-measure resting blood pressure in 12-24 hours.': '12–24 小時後複測靜息血壓。',
    'Check cabin O2 and CO2 monitors and improve local airflow.': '檢查艙內 O2 與 CO2 監測讀數，並加強所在艙段空氣對流。',
    'Repeat SpO2 + breathing rate in 4-6 hours.': '4–6 小時後複測血氧 SpO2 與呼吸頻率。',
    'Check CDRA CO2 scrubber status and turn up cabin mixing fans.': '檢查 CDRA 二氧化碳吸附器狀態並調高艙內循環風扇風速。',
    'Re-check breathing rate and SpO2 in 12 hours.': '12 小時後複測呼吸頻率與血氧。',
    'Verify serum K+ >= 3.5 mmol/L and take electrolyte / potassium replacement if low.': '確認血清鉀 K+ ≥ 3.5 mmol/L；若偏低立即補充電解質與口服鉀。',
    'Skip maximal sprints; keep CEVIS cycling in easy Zone 2 until Holter clears.': '暫停最大衝刺課表；維持輕鬆第 2 區間飛輪直到 Holter 恢復正常。',
    'Drink 500-750 mL electrolyte solution and review M10 plasma volume (%DeltaPV).': '飲用 500–750 mL 電解質液並同步檢視 M10 血漿容量 (%ΔPV)。',
    'Add 30-min LBNP (-20 mmHg) sessions 3x/week to retrain blood vessels.': '每週加入 3 次 30 分鐘 LBNP (-20 mmHg) 訓練以強化血管收縮反射。',
    'Check M10 plasma volume (%DeltaPV) and hydrate before workouts.': '檢視 M10 血漿容量 (%ΔPV) 並於運動前確實補水。',
    'Shift CEVIS to structured Zone 2 aerobic sessions (4x/week) and re-test in 7 days.': '將 CEVIS 轉為第 2 區間穩態有氧訓練（每週 4 次）並於 7 天後複測。',
    'Avoid maximal all-out sprints; maintain steady Zone 2 aerobic conditioning.': '避免全力衝刺；維持穩定的第 2 區間有氧體能訓練。',
    'Repeat Ultrasound 2 GLS scan in 7 days.': '7 天後複檢 Ultrasound 2 心肌應變 GLS 掃描。',
    'Run 30 minutes of -20 mmHg LBNP daily to pull fluid back down toward your legs.': '每日執行 30 分鐘 -20 mmHg LBNP 將體液導向下半身。',
    'Avoid head-down tilt and slightly elevate your upper body while sleeping; re-scan neck in 24-48 hours.': '避免頭低腳高姿勢，睡眠時微墊高上半身；24–48 小時後複掃頸部靜脈。',
    'Increase daily fluids by +750 mL with electrolytes and re-check orthostatic tolerance (M6).': '每日額外增加 +750 mL 含電解質飲水，並複檢直立耐受性 (M6)。',
    'Replenish potassium/electrolytes orally and hydrate well before exercise.': '口服補充鉀離子與電解質，運動前務必充分補水。',
    'Repeat Bio-Analyzer chemistry check in 24-48 hours.': '24–48 小時後複檢 Bio-Analyzer 生化指標。',
    'STOP all CEVIS cycling and heavy E4D resistance workouts right away.': '立即停止所有 CEVIS 飛輪與高負荷 E4D 抗阻訓練。',
    'Record a 12-lead ECG and check your oral temperature + SpO2.': '立即記錄 12 導程心電圖，並量測口腔體溫與血氧 SpO2。',
    'Notify the Crew Medical Officer / Flight Surgeon and repeat vitals every 4 hours.': '通報隨艦醫療官／航太醫師，並每 4 小時追蹤一次生命徵象。',
    'Pause heavy E4D lifting and intense exercise immediately.': '立即暫停大重量 E4D 訓練與劇烈運動。',
    'Check for headache, blurry vision, or dizziness and check cabin CO2 levels.': '確認是否有頭痛、視力模糊或頭暈症狀，並核對艙內 CO2 濃度。',
    'Repeat manual arm-cuff BP every 2-4 hours and alert the Flight Surgeon.': '每 2–4 小時以手動袖帶複測血壓並通知航太醫師。',
    'Verify cabin oxygen (PIO2) and CO2 (ppCO2) readings immediately; put on supplemental O2 if low.': '立即核對艙內氧分壓 (PIO2) 與二氧化碳 (ppCO2)；若氧氣偏低立即使用備援供氧。',
    'If breathing rate is also >25/min, treat as possible lung clot: run bilateral neck IJV Ultrasound 2 scan now.': '若呼吸頻率同時 >25次/分，視為疑似肺栓塞警訊：立即執行雙側頸內靜脈超音波掃描。',
    'Notify the Crew Medical Officer / Flight Surgeon immediately.': '立即通報隨艦醫療官與地面航太醫師。',
    'Check cabin ppCO2 and O2 sensors right away; move to a well-ventilated module.': '立即檢查艙內 ppCO2 與氧氣感測器，必要時移往通風良好艙段。',
    'Pair with M3 SpO2: if SpO2 < 95%, run immediate neck IJV Ultrasound 2 clot scan and notify CMO.': '配合 M3 血氧判斷：若 SpO2 < 95%，立即掃描頸靜脈血栓並通報醫療官。',
    'STOP all CEVIS and E4D workouts immediately.': '立即全面停止所有 CEVIS 與 E4D 訓練。',
    'If K+ < 3.5 mmol/L, take oral potassium (KCl) supplement per medical kit guide.': '若 K+ < 3.5 mmol/L，依醫療手冊指引服用口服氯化鉀 (KCl) 補充劑。',
    'Keep continuous ECG monitoring active and alert the Flight Surgeon immediately.': '保持連續心電圖監測並立即通報航太醫師。',
    'Rest flat/neutral until dizziness passes; do NOT stand abruptly.': '保持平躺／中性飄浮休息直到頭暈消退；切勿突然起身。',
    'Execute NASA salt-water fluid loading (1 L isotonic electrolyte drink + salt tablets).': '執行 NASA 鹽水體液負荷處方（1 公升等張電解質飲＋鹽錠）。',
    'Wear lower-body compression garments before any re-entry or planetary G-load and schedule daily LBNP.': '於再入大氣層或承受重力負荷前穿戴下肢加壓褲，並排定每日 LBNP 訓練。',
    'Suspend HIIT and 150W fitness tests for 14 days.': '暫停高強度間歇訓練與 150W 體能測試 14 天。',
    'Rule out IJV clot, arrhythmia, and hypovolemia before resuming gentle Zone 1/2 cycling.': '確認排除頸靜脈血栓、心律不整與低血容後，方可恢復輕度第 1/2 區間踩踏。',
    'Suspend all heavy E4D and HIIT exercise immediately.': '立即暫停所有大重量 E4D 與高強度間歇運動。',
    'Save ultrasound cine loops for Flight Surgeon review and repeat echocardiogram in 24-48 hours.': '儲存心臟超音波動態影像供航太醫師判讀，並於 24–48 小時後複檢心超。',
    'STOP heavy E4D straining and intense CEVIS workouts immediately.': '立即停止 E4D 閉氣用力訓練與高強度 CEVIS 飛輪。',
    'Initiate the onboard anticoagulation medication checklist per Flight Surgeon protocol.': '依航太醫師標準程序啟動隨艦抗凝血藥物治療檢核表。',
    'Run controlled -25 mmHg LBNP and check SpO2 (M3) + breathing rate (M4) every 4 hours for lung-clot signs.': '執行受控 -25 mmHg LBNP，並每 4 小時追蹤血氧 (M3) 與呼吸 (M4) 以排除肺栓塞徵兆。',
    'Drink 1 L of isotonic electrolyte fluid + salt tablets immediately.': '立即飲用 1 公升等張電解質液並補充鹽錠。',
    'Pause strenuous exercise until repeat Hb/Hct confirms volume recovery.': '暫停劇烈運動，直到複測 Hb/Hct 證實血漿容量已恢復。',
    'STOP high-intensity workouts; take oral KCl if K+ < 3.5 mmol/L.': '停止高強度運動；若 K+ < 3.5 mmol/L 立即口服補充氯化鉀。',
    'Run 12-lead ECG + bilateral neck IJV ultrasound; repeat chemistry panel in 12 hours.': '執行 12 導程心電圖與雙側頸內靜脈超音波；12 小時後複測血液生化。',

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

    // Role 3 M1-M11 dynamic why_in_space patterns
    out = out.replace(/^Your resting heart rate \(([\d.]+) bpm\) is close to your pre-flight baseline \(([\d.]+) bpm\)\. That tells us your body fluid level and heart nervous-system control are well balanced\.$/, '您的靜息心率 ($1 bpm) 接近發射前個人基準 ($2 bpm)，顯示體液容積與心臟自主神經調控維持良好平衡。');
    out = out.replace(/^Your resting heart rate drifted up to ([\d.]+) bpm \(baseline ([\d.]+) bpm\)\. Microgravity shrinks blood fluid volume, so your heart beats faster to keep blood flowing to your brain\.$/, '靜息心率上升至 $1 bpm（基準 $2 bpm）。微重力會縮減血液容積，使心臟必須加快跳動以維持腦部供血。');
    out = out.replace(/^Your resting heart is beating very fast \(([\d.]+) bpm vs your ([\d.]+) bpm Earth baseline\)\. In space, this means your heart is working overtime because of severe fluid loss, infection\/fever, low blood oxygen, or a clot\.$/, '靜息心率過快（$1 bpm，地球基準 $2 bpm），代表心臟因嚴重脫水、發燒感染、低血氧或血栓風險而過度代償負荷。');
    out = out.replace(/^Your blood pressure \(([\d.]+\/[\d.]+) mmHg\) is steady inside NASA-STD-3001 bounds, showing your blood vessels are adapting smoothly to weightlessness\.$/, '血壓 ($1 mmHg) 穩定落於 NASA-STD-3001 安全範圍內，顯示血管正平順適應失重環境。');
    out = out.replace(/^Your blood pressure \(([\d.]+\/[\d.]+) mmHg\) is drifting toward NASA warning limits\. Without gravity pulling blood down, shifts in salt, fluids, stress, or cabin CO2 can push pressure out of range\.$/, '血壓 ($1 mmHg) 正趨近 NASA 預警上限。失重環境下，鹽分、體液轉移、壓力或艙內 CO2 升高皆可能推高血壓。');
    out = out.replace(/^Blood pressure is dangerously outside safe limits \(([\d.]+\/[\d.]+) mmHg\)\. Too high puts extra pressure on head veins and vision \(SANS\); too low means blood is not reaching your brain\.$/, '血壓 ($1 mmHg) 已超出安全紅線：過高會加劇頭部靜脈鬱積與視神經水腫 (SANS)；過低則導致腦部灌流不足。');
    out = out.replace(/^SpO2 is ([\d.]+)%, proving your lungs are delivering plenty of oxygen from the cabin air into your bloodstream\.$/, '血氧飽和度為 $1%，證實肺部正穩定將艙內氧氣輸送至血液循環。');
    out = out.replace(/^Oxygen saturation \(([\d.]+)%\) is slightly below normal \(96-100%\)\. This gives an early warning of stale cabin air, mild lung congestion, or an early blood clot\.$/, '血氧飽和度 ($1%) 略低於正常值 (96–100%)，可能為艙內空氣滯留、輕微肺鬱血或早期血栓之預警。');
    out = out.replace(/^Blood oxygen dropped to a critical ([\d.]+)% \(<= 92%\)\. Either cabin air is low in oxygen, or a blood clot \(pulmonary embolism\) is blocking blood from picking up oxygen in your lungs\.$/, '血氧驟降至危急值 $1% (≤92%)：可能為艙內缺氧，或血栓阻塞肺部血流（肺栓塞）導致無法換氣。');
    out = out.replace(/^Resting breathing \(([\d.]+) breaths\/min\) is calm and steady, showing cabin air quality and lung function are normal\.$/, '靜息呼吸頻率 ($1 次/分) 平穩正常，顯示艙內空氣品質與肺功能良好。');
    out = out.replace(/^Breathing rate is mildly elevated \(([\d.]+) breaths\/min\)\. Pockets of trapped CO2 around sleeping quarters or early cardiopulmonary stress make you breathe faster\.$/, '呼吸頻率輕度偏快 ($1 次/分)，睡眠區局部 CO2 累積或早期心肺負荷皆會加快呼吸。');
    out = out.replace(/^You are breathing very rapidly \(([\d.]+) breaths\/min, limit <= 25\)\. In a closed spacecraft, rapid breathing signals dangerously high CO2 buildup, low oxygen, infection, or a lung blood clot\.$/, '呼吸急促 ($1 次/分，上限 ≤25)：在封閉太空艙內代表危險 CO2 累積、缺氧、感染或疑似肺栓塞。');
    out = out.replace(/^PVC burden increased to ([\d.]+)% \(warning >= 1\.5%\)\. Stress, dehydration, or low potassium \(currently ([\d.]+) mmol\/L\) commonly causes extra ventricular beats in orbit\.$/, '心室早搏負荷升至 $1%（預警 ≥1.5%）。壓力、脫水或低血鉀（目前 $2 mmol/L）常在軌道上誘發早搏。');
    out = out.replace(/^Extra heartbeats \(PVCs\) reached ([\d.]+)%([^,]*), and blood potassium is ([\d.]+) mmol\/L\. Low potassium or heart stretching in space makes the heart muscle electrically unstable\.$/, (_, pvc, af, k) => `心室早搏達 ${pvc}%${af.includes('Atrial') ? '（合併心房顫動）' : ''}，血鉀為 ${k} mmol/L；低血鉀或心房牽張會造成心肌電位極度不穩。`);
    out = out.replace(/^A mild \+([\d.]+) bpm HR rise with no dizziness shows your blood vessels still push blood to your brain when gravity pulls it down\.$/, '心率僅溫和上升 +$1 bpm 且無頭暈，顯示重力牽引下血管仍能有效將血液送往腦部。');
    out = out.replace(/^Heart rate jumped \+([\d.]+) bpm and SBP fell ([+-]?[\d.]+) mmHg\. Fluid loss in weightlessness reduces your blood volume and weakens blood-vessel reflex tightening\.$/, '心率躍升 +$1 bpm 且收縮壓下降 $2 mmHg：失重體液流失降低了血容量並減弱血管收縮反射。');
    out = out.replace(/^Your heart jumped \+([\d.]+) bpm and blood pressure dropped ([+-]?[\d.]+) mmHg with dizziness\. Because plasma blood volume shrank \(([+-]?[\d.]+)% in M10\), standing or gravity pulls blood away from your brain, risking fainting on landing\.$/, '心率躍升 +$1 bpm、血壓驟降 $2 mmHg 並伴隨頭暈：因血漿容量縮減 ($3%)，著陸重力將導致腦部缺血暈厥高風險。');
    out = out.replace(/^Steady 150W heart rate \(([\d.]+) bpm\) shows your heart pumps strongly per beat and your aerobic fitness is intact for EVA\/landing\.$/, '150W 穩定負荷心率 ($1 bpm) 顯示每跳輸出量強健，有氧體能足以應付艙外活動與著陸。');
    out = out.replace(/^Heart rate drifted up to ([\d.]+) bpm at 150W \(warning >= 150 bpm\)\. Without daily gravity, aerobic stamina \(VO2max\) and stroke volume gradually fade\.$/, '150W 負荷下心率飄移至 $1 bpm（預警 ≥150 bpm），反映長期失重下心輸出量與最大攝氧量逐漸衰退。');
    out = out.replace(/^Heart rate spiked to ([\d.]+) bpm at a fixed 150W workload\. Your heart is pumping less blood per beat due to severe deconditioning or fluid loss, leaving little reserve for an emergency spacewalk or egress\.$/, '150W 固定負荷下心率飆升至 $1 bpm：嚴重體能退化或體液流失使每跳輸出量下降，緊急出艙/撤離儲備不足。');
    out = out.replace(/^Heart squeeze strain \(([+-]?[\d.]+)%\) is healthy, meaning your heart muscle hasn't weakened in microgravity\.$/, '心肌縱向應變 ($1%) 維持健康，代表心肌收縮力未因微重力而減弱。');
    out = out.replace(/^GLS shifted ([+-]?[\d.]+)% from pre-flight \(warning <= -10%\)\. Lower workload in weightlessness can cause mild heart-muscle thinning over long missions\.$/, '心肌應變 GLS 較發射前偏移 $1%（預警 ≤-10%），反映長期失重低負荷可能導致輕度心肌萎縮。');
    out = out.replace(/^Heart muscle squeeze \(GLS\) dropped ([+-]?[\d.]+)% \(red limit <= -15%\)\. This detects early weakening or stress on the heart wall before standard pumping numbers fall\.$/, '心肌應變 GLS 惡化至 $1%（紅線 ≤-15%），顯示心壁收縮功能已出現明顯壓力或衰退。');
    out = out.replace(/^S_bone=([\d.]+), VBT=([\d.]+)%, (?:Strength=([^,]+), )?Thigh=([^,]+), Calf=([^,]+), CTX=([^,]+), (?:Est|Modeled) Hip Loss=([^\s.]+%?\/mo)\.(?:\s*\[URGENT ESCALATION\])?$/, (_, a, b, str, c, d, e, f) => {
      const strPart = str ? `｜肌力 ${str}` : '';
      return `骨骼刺激 S_bone=${a}｜速度衰減 ${b}%${strPart}｜大腿 ${c}｜小腿 ${d}｜骨吸收 CTX ${e}｜推估髖骨流失 ${f}`;
    });
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
