# AGENTS.md - Your Workspace

Keep workspace conventions here. Personality and tone belong in `SOUL.md`.

## First Run

If `BOOTSTRAP.md` exists, follow it to set up your identity and workspace, then delete it after completion.

## Session Startup

Use runtime-provided startup context first. It may already include `AGENTS.md`, `SOUL.md`, `USER.md`, recent daily memory (`memory/YYYY-MM-DD.md`), and `MEMORY.md` (main session only).

Read startup files again only when:
1. The user explicitly asks.
2. Needed context is missing.
3. A deeper follow-up read is needed.

## Memory & Git Hygiene (Team Collaboration Rules)

- **Daily notes:** `memory/YYYY-MM-DD.md` holds local raw logs (ignored by Git).
- **User model:** `USER.md` holds the individual developer's assigned role among the 6 team members (ignored by Git).
- **Long-term:** `MEMORY.md` holds durable non-profile facts and decisions (main session only).
- **Never commit `USER.md` or `memory/` to Git** to prevent merge conflicts across the 6 developers' machines.

---

## Project Architecture: Z.O.S.M.A. (Deep-Space Astronaut Health Monitoring System)

### 1. Tech Stack & Environment (100% Pure Python in Conda)
- **Language:** Python 3.10+ (Conda environment).
- **Required Packages (`requirements.txt`):** `streamlit>=1.38.0`, `plotly>=5.24.0`, `pydantic>=2.9.0`, `pandas>=2.2.0`, `numpy>=1.26.0`, `scipy>=1.14.0`, `matplotlib>=3.9.0`, `pyyaml>=6.0.1`.
- **UI & Visualization:** `Streamlit` (3-column Mission Control dashboard, manual input sliders, interactive 2D human body & cabin status map, 3-step crew guidance cards, and closed-loop daily/long-term scheduler) + `Plotly` (longitudinal trend charts with green/yellow/red threshold bands and trend projection lines).
- **Data Validation:** `Pydantic` (strictly typed Input/Output schemas in `core/schema.py`).

### 2. Separation of Concerns & Zero-Conflict File Ownership
To guarantee **zero Git merge conflicts** and protect teammates who are domain researchers rather than experienced coders, responsibilities are strictly divided:

- **Role 1 (Lead System Integrator & UI Architect — `main` branch):**
  - **Owns:** `app.py`, `requirements.txt`, `core/schema.py`, `core/data_loader.py`, `core/scheduler.py`, and `data/shared_real/`.
  - **Exclusive Responsibilities:**
    1. **Frontend UI & Telemetry Input Forms:** Provides manual sliders/inputs in Streamlit for all 5 domains and passes them as clean Python `dict` payloads to each module's `evaluate()` function.
    2. **Centralized Data Persistence (Storage):** Handles all saving/appending of new measurements to local storage (`data/runtime_session.json`). **Modules 2–6 MUST NOT write to shared databases directly.**
    3. **Global Short-Term & Long-Term Schedule Aggregation & Cross-Module Context:** Collects `short_term_plan` and `long_term_plan` outputs from all 5 modules, propagates cross-module flags (`spe_alert`, `ppco2_mmHg`, `sleep_h`), resolves conflicts (e.g., halting heavy E4D resistance workouts if Cardiovascular or Immune triggers a `RED` fever/arrhythmia/clot alert), and renders the master timeline.

- **Roles 2–6 (5 Domain Evaluator Agents — `feat/*` branches):**
  - **Role 2 (Musculoskeletal):** Owns `modules/musculoskeletal.py` and `data/musculoskeletal/`.
  - **Role 3 (Cardiovascular & Aerobic):** Owns `modules/cardiovascular.py` and `data/cardiovascular/`.
  - **Role 4 (Neuro-Ocular & Vestibular):** Owns `modules/neuro_ocular.py` and `data/neuro_ocular/`.
  - **Role 5 (Immune, Endocrine & Metabolic):** Owns `modules/immune_metabolic.py` (or `modules/immune.py`) and `data/immune_metabolic/`.
  - **Role 6 (Radiation, Acoustics & Cabin Env):** Owns `modules/cabin_environment.py` and `data/cabin_environment/`.
  - **Exclusive Responsibilities:** Implement **stateless pure evaluation functions** that accept sensor/manual inputs + baselines, run the 3-layer decision model (+ Layer 0 QC Gatekeeper), and return standardized diagnostics, 3-step crew guidance, and module-specific short-term/long-term recommendations.

### 3. Data Folder Checklist & Proactive Missing-CSV Handling
Teammates may not have placed their CSV/JSON files into `data/` yet. **NO module is allowed to crash with `FileNotFoundError`.**
- **`data/shared_real/`:** `OSD-569_inspiration4_cbc.csv` (or `osd569_cbc_transformed.csv`), `OSD-575_cmp.csv` (or `osd575_cmp.csv`), `OSD-575_cv_panel.csv`.
- **`data/musculoskeletal/`:** `e4d_sets.csv`, `measurements_long.csv`, `preflight_baseline.json`.
- **`data/cardiovascular/`:** `daily_vitals.csv`, `bike_test.csv`, `stand_test.csv`, `holter_24h.csv`, `ultrasound.csv`, `biomonitor_stream_day124.csv`, plus optional `real/` (PRCP & MIT-BIH).
- **`data/neuro_ocular/`:** `mini_oct_scans.csv`, `ultrasound_eye.csv`, `vog_vestibular.csv`, `preflight_baseline.json`.
- **`data/immune_metabolic/`:** `daily_checkin.csv`, `cbc_monthly.csv`, `saliva_virus.csv`, `events.csv`, `preflight_baseline.json`.
- **`data/cabin_environment/`:** `rad01_area_dose.csv`, `rad02_crew_dose_daily.csv`, `goes_integral_protons_6h.json`, `aco01_module_spl.csv`, `aco02_crew_dosimetry.csv`, `atm01_co2.csv`, `atm02_pressure_o2.csv`, `atm03_thermal.csv`, `atm04_voc.csv`, `iso01_sleep.csv`, `iso02_pvt.csv`, `iso03_mood.csv`.

**MANDATORY AGENT BEHAVIOR FOR DATA FILES:**
1. Every module (`modules/*.py`) MUST implement `demo_baseline()`, `demo_payload(scenario="green"|"yellow"|"red"|"bad_data")`, and `export_demo_csvs()` (which auto-generates sample CSVs inside `data/<module_name>/` if the folder is empty).
2. Whenever assisting a teammate (Roles 2–6), inspect their `data/<module_name>/` directory. If files are missing, proactively remind them of the exact folder path, filenames, and column headers, and offer to run `export_demo_csvs()` so they have ready-to-edit CSV templates.

### 4. Unified Data Contract (`core/schema.py` Input & Output Specification)

#### A. Module Input Payload (`payload: dict`)
Each module's `evaluate(payload: dict = None, baseline: dict = None)` must accept either historical time-series arrays (from CSVs/`demo_payload`) OR live manual override values from Role 1's UI sliders:
- **Role 2 Inputs (`musculoskeletal`):** `peak_force_n`, `loading_rate_n_s`, `reps`, `velocity_loss_pct`, `iso_peak_force_n`, `csa_thigh_cm2`, `csa_calf_cm2`, `body_mass_kg`, `ntx`, `ctx`, `p1np`.
- **Role 3 Inputs (`cardiovascular`):** `rest_hr_bpm`, `sbp_mmHg`, `dbp_mmHg`, `spo2_pct`, `resp_rate_bpm`, `steady_hr_150w_bpm`, `stand_hr_rise_bpm`, `stand_sbp_drop_mmHg`, `dizzy`, `pvc_burden_pct`, `afib_detected`, `gls_change_pct`, `ijv_flow` (`"forward"`|`"stagnant"`|`"reversed"`), `ijv_thrombus`, `hb_g_dl`, `hct_pct`, `potassium_mmol_l`, `crp_change_pct`.
- **Role 4 Inputs (`neuro_ocular`):** `eye` (`"OD"`|`"OS"`), `oct_snr_score` / `quality_score`, `registered_to_baseline`, `delta_trt_um`, `delta_v_onh_mm3`, `bmo_mrw_um`, `delta_rnfl_um`, `rnfl_slope_um_day`, `sph_eq_shift_d`, `folds_foveal`, `amsler_result`, `onsd_mm`, `delta_onsd_mm`, `axial_length_mm`, `vor_gain`, `ocr_deg`, `ms_score`, `g_phase`, `days_since_transition`, `tandem_correct_steps`.
- **Role 5 Inputs (`immune_metabolic`):** `temp_c`, `symptoms` (list/semicolon string), `wbc`, `lymph`, `neut`, `saliva_vzv`, `saliva_ebv`, `sleep_h`, `stress_score`, `spe_event_flag`, `crp_mg_l`, `il6_pg_ml`, `hydration_ml`.
- **Role 6 Inputs (`cabin_environment`):** `dose_rate_uGy_h`, `saa_pass` (bool), `career_dose_mSv`, `proton_flux_10mev_pfu`, `spe_alert` (bool), `module_spl_dBA`, `crew_leq8_dBA`, `daily_noise_dose_pct`, `ppco2_1h_mmHg`, `ppco2_7d_mmHg`, `p_total_kPa`, `pio2_mmHg`, `dpdt_kPa_per_min`, `temp_C`, `rh_pct`, `max_smac_ratio`, `ammonia_or_fire_alarm` (bool), `sleep_tst_h`, `pvt_speed_1_per_s`, `workload_bedford`, `stress_vas`.

#### B. Standardized Module Output (`ModuleEvaluationResult` / `to_schema()`)
Every module MUST evaluate metrics through the **Layer 0 QC Gatekeeper + 3-Layer Decision Model** (`Layer 1: Fixed Clinical/NASA-STD-3001 Rules`, `Layer 2: Personal or Module Baseline ±2 SD / Δ%`, `Layer 3: Recent Trend Slope / Time-to-Red Projection — Worst Result Wins`) and return:
- `module_id`: `"musculoskeletal"` | `"cardiovascular"` | `"neuro_ocular"` | `"immune_metabolic"` | `"cabin_environment"`
- `body_part_tag`: `str` or `list[str]` (e.g., `"lower_limb_bone_muscle"`, `"heart_vascular"`, `"eyes_vestibular"`, `"immune_renal"`, or `["whole_body", "lungs", "brain", "ears"]`)
- `crew_id`: str (default `"C002"`)
- `mission_day`: int (default `124` or `180`)
- `status_light` (alias `overall_status`): `"GREEN"` | `"YELLOW"` | `"RED"` (case-insensitive; `"GREEN-WATCH"` maps to `"GREEN"` with watch flag; `"INSUFFICIENT_DATA"`/`"no_data"` maps to `quality_passed=False`)
- `quality_passed`: `bool`
- `metrics` (alias `indicators`): List of dicts containing:
  - `metric_name` (or `indicator`), `current_val` (or `value`), `baseline_val`, `delta_pct`, `slope_per_day`, `unit`, `status_light` (or `status`), `decided_by` (`"quality_check"`|`"fixed_threshold"`|`"rule"`|`"baseline"`|`"trend"`|`"spe_rule"`|`"fast_track"`), `data_source` (`"REAL"`|`"SIMULATED"`), `message`, `action`.
- `guidance` (3-Step Non-Medical Crew Guide):
  - `how_to_measure`: Step-by-step device operation & calibration check.
  - `plain_explanation`: Plain-language physiological meaning in space.
  - `action_protocol`: Ordered list of immediate clinical/operational steps.
- `short_term_plan` (0–48 Hours Immediate Triage):
  - `next_measurement_in_hours`: `int` (e.g., `0` for immediate re-test on bad data, `1`–`24` for Red, `24`–`72` for Yellow, `168` for Green).
  - `immediate_actions`: List of urgent interventions.
  - `urgent_alert`: `bool` (`True` notifies Crew Medical Officer / Flight Surgeon immediately).
- `long_term_plan` (7–30 Days Regimen & Trend Forecast):
  - `days_until_red_prediction`: `Optional[int]` (estimated days until metric crosses Red threshold based on linear trend slope).
  - `routine_prescription_adjustment`: String/list describing multi-week adjustments.
- `schedule_mutation`: Legacy compatibility dict `{ next_measurement_in_hours, prescription_adjustment, urgent_alert }`.

### 5. Domain Specifications for the 5 Modules
- **Module A (`modules/musculoskeletal.py`):** E4D Bone Stimulus Index ($S_{bone}$), Isometric Peak Force (SRI $\Delta\text{Strength}\%$), VBT squat velocity loss ($30\%$ red limit), Ultrasound 2 thigh ($4\%/7\%$) & calf ($5\%/10\%$) CSA, SLAMMD body mass ($5\%/10\%$), Bio-Analyzer bone markers (NTX, CTX $+50\%$ red, P1NP), plus NASA OSD-575 Ca/ALP baseline validation[cite: 56, 57, 58].
- **Module B (`modules/cardiovascular.py`):** M1–M11 indicators (Resting HR, PTT Blood Pressure, $SpO_2$, Resp Rate, Holter 24h PVC burden & MIT-BIH validation, LBNP/Stand test orthostatic tolerance & PRCP validation, CEVIS 150W HR drift, Ultrasound 2 GLS cardiac strain & IJV stasis/clot protocol, OSD-569 Dill & Costill plasma volume $\% \Delta PV$, OSD-575 serum K+/CRP/clotting)[cite: 40, 41, 42, 43, 44, 45, 46].
- **Module C (`modules/neuro_ocular.py`):** Per-eye (OD/OS) SANS & Vestibular evaluation: Mini OCT QC (`quality_score` & `registered_to_baseline`), $\Delta\text{TRT}$ ($+20\text{ }\mu\text{m}$ Yellow / $+55\text{ }\mu\text{m}$ Red), $\Delta V_{\text{ONH}}$ ($0.10\text{–}0.15\text{ mm}^3$ `GREEN-WATCH`, $\ge 0.15$ Yellow, $\ge 0.30$ Red), $\Delta\text{RNFL}$ ($10\text{–}15\text{ }\mu\text{m}$ `GREEN-WATCH`, $>15$ Yellow), hyperopic shift ($\ge +0.75\text{ D}$ Yellow $\rightarrow$ Space Anticipation Glasses), foveal folds / Amsler scotoma (Red), combined ONSD ($\text{ONSD} > 6.0\text{ mm}$ AND $\Delta\text{ONSD} \ge +0.5\text{ mm}$ Red), gravity-transition-aware `vor_gain` / `ocr_deg` / `ms_score` / tandem walk, plus DS-0 saturating exponential generator[cite: 87, 88, 89, 97, 98].
- **Module D (`modules/immune_metabolic.py`):** I1–I10 indicators (Oral Temp, 9 Symptoms & skin photo guide, HemoCue/Bio-Analyzer WBC & $<10\%$ neutrophil mis-sort quality gate validated on OSD-569 C003 L-92, Lymphocytes with $-25\%$ drop & post-SPE $-50\%$ rule, Neutrophils & NLR stress index, Saliva VZV/EBV DNA copies/mL, Sleep & Stress risk factors, HERA SPE cross-module trigger, CRP/IL-6, Vitamin D3 & hydration renal protection)[cite: 69, 70, 71, 72, 73, 74, 76].
- **Module E (`modules/cabin_environment.py`):** 12 NASA-STD-3001 cards (`RAD-01..03`, `ACO-01..02`, `ATM-01..04`, `ISO-01..03`): RadLab DOSTEL area dose rate with South Atlantic Anomaly (SAA $50^\circ\text{S–}0^\circ, 90^\circ\text{W–}40^\circ\text{E}$) masking, personal cumulative dose ($480/600\text{ mSv}$), NOAA GOES-18 proton flux ($\ge 10\text{ MeV} \ge 10/100\text{ pfu}$), acoustics NC-50/NC-40 & LEQ8/24h dose, MCA/CDRA $ppCO_2$ ($2.5/3.0\text{ mmHg}$) & stuck-sensor ($\ge 24\text{h}$) rule, cabin total pressure & rapid depressurization fast-track, THC $T/RH$ envelope ($20\text{–}25^\circ\text{C}, 30\text{–}60\%$), AQM VOCs/ammonia SMAC ratios, and Actiwatch sleep / PVT-B alertness / Bedford workload[cite: 108, 112, 115, 116, 118, 119, 120, 122, 123, 125, 126, 127, 128].

## Red Lines

- Don't share private data with people or services the user didn't ask for.
- Confirm destructive or irreversible actions the user didn't ask for.
- Prefer `trash` over `rm` - recoverable beats gone forever.