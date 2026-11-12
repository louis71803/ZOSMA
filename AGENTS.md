# AGENTS.md - Your Workspace

Keep workspace conventions here. Personality and tone belong in `SOUL.md`.

## Session Startup

Use runtime-provided startup context first (`AGENTS.md`, `SOUL.md`, `USER.md`, `memory/YYYY-MM-DD.md`, and `MEMORY.md`). Read startup files again only when the user explicitly asks, needed context is missing, or a deeper follow-up read is needed.

## Memory & Git Hygiene (Team Collaboration Rules)

- **Daily notes:** `memory/YYYY-MM-DD.md` holds local raw logs (ignored by Git).
- **User model:** `USER.md` holds the individual developer's assigned role among the 6 team members (ignored by Git).
- **Never commit `USER.md` or `memory/` to Git** to prevent merge conflicts across the 6 developers' machines.

---

## Project Architecture: Deep-Space Astronaut Health Monitoring System

### 1. Tech Stack & Environment (100% Pure Python in Conda)
- **Language:** Python 3.10+ (Conda environment).
- **UI & Visualization:** `Streamlit` (interactive body model dashboard, color-coded status cards, gamified progress, daily timeline scheduler) + `Plotly` (longitudinal trend charts, E4D force-velocity curves, Mini OCT $\Delta\mu m$ difference heatmaps).
- **Data Validation:** `Pydantic` (strictly typed Input/Output schemas).
- **Offline Storage:** Local `sqlite3` or structured JSON files for Pre-flight Baselines and time-series logs.

### 2. Zero-Conflict Directory & File Ownership (6-Person Split)
To guarantee **zero Git merge conflicts**, each team member owns specific files. Never edit files outside the active developer's scope unless explicitly instructed by Role 1 (Core Integrator):
- **Role 1 (Core Integrator & UI):** Owns `app.py`, `core/schema.py`, `core/database.py`, `core/scheduler.py`.
- **Role 2 (Musculoskeletal Module):** Owns `modules/musculoskeletal.py`.
- **Role 3 (Cardiovascular & Aerobic Module):** Owns `modules/cardiovascular.py`.
- **Role 4 (Neuro-Ocular & Vestibular Module):** Owns `modules/neuro_ocular.py`.
- **Role 5 (Immune, Endocrine & Metabolic Module):** Owns `modules/immune_metabolic.py`.
- **Role 6 (Radiation, Acoustics & Cabin Environment Module):** Owns `modules/cabin_environment.py`.

### 3. Unified Data Contract (Standard Module Output Specification)
When the hackathon begins, Role 1 will generate `core/schema.py` using `Pydantic`. All 5 physiological/environmental modules (Roles 2–6) MUST implement pure evaluation functions that accept sensor payloads + pre-flight baselines and return a unified `ModuleEvaluationResult` containing:
- `module_id`: `"musculoskeletal"` | `"cardiovascular"` | `"neuro_ocular"` | `"immune_metabolic"` | `"cabin_environment"`
- `body_part_tag`: `"lower_limb_bone_muscle"` | `"heart_vascular"` | `"eyes_vestibular"` | `"immune_renal"` | `"whole_body_env"`
- `status_light`: `"GREEN"` | `"YELLOW"` | `"RED"`
- `quality_passed`: `bool` (True if sensor SNR/confidence passes gatekeeper; False triggers immediate re-measurement prompt)
- `metrics`: List of `{ metric_name, current_val, baseline_val, delta_pct, slope_per_day, unit, status_light }`
- `guidance`:
  - `how_to_measure`: Step-by-step measurement & calibration guide for non-medical crew.
  - `plain_explanation`: Plain-language meaning and physiological risk explanation.
  - `action_protocol`: Ordered list of concrete offline countermeasures/treatments.
- `schedule_mutation`: `{ next_measurement_in_hours: int, prescription_adjustment: str, urgent_alert: bool }`

### 4. Domain Specifications for the 5 Modules (Input -> Logic -> Output)

#### Module A: Musculoskeletal (`modules/musculoskeletal.py`)
- **Devices & Inputs:** E4D (Peak force $F_{peak}$, loading rate $dF/dt$, repetitions $n$, Isometric Peak Force $F_{iso}$, Mean Propulsive Velocity MPV), SLAMMD (body mass via Hooke's law), Ultrasound 2 (muscle cross-sectional area CSA, pennation angle), Bio-Analyzer (NTX, CTX, P1NP).
- **Core Logic:**
  - Bone Stimulus Index: $S_{bone} = \sum (F_{peak,i} \cdot (dF/dt)_i^\alpha \cdot n_i^\beta)$ vs. Weekly Target Impulse (Green $\ge 90\%$, Yellow $75\text{--}90\%$, Red $<75\%$ or $<80\%$ for 2 consecutive weeks).
  - Strength Retention Index (SRI): $\Delta\text{Strength}(\%) = ((F_{current} - F_{baseline}) / F_{baseline}) \times 100\%$ (Green $> -5\%$, Yellow $-5\% \text{ to } -10\%$, Red $< -10\%$).
  - Velocity-Based Training (VBT): Intra-set velocity loss $>20\%$ = target stimulus reached; $>35\%$ = excessive fatigue (stop set); inter-set initial velocity drop $>15\%$ = CNS fatigue.
- **Output Countermeasures:** Auto-adjust E4D motor resistance (+5% load or high-loading-rate squats/deadlifts on Red/Yellow, or insert active recovery on fatigue).

#### Module B: Cardiovascular & Aerobic (`modules/cardiovascular.py`)
- **Devices & Inputs:** Bio-Monitor smart garment (continuous ECG, cuffless PTT blood pressure, $SpO_2$, respiratory rate, skin temp), E4D/CEVIS/T2 (150W submaximal fixed-wattage heart rate), Holter Monitor 2 (24h arrhythmia/QT interval), Ultrasound 2 (myocardial strain, Internal Jugular Vein IJV flow stasis/retrograde flow for thrombosis risk).
- **Core Logic:**
  - Submaximal Aerobic Efficiency Drift: Compare steady-state HR at fixed 150W against pre-flight $HR_{base}$ (Green $< +5\text{ bpm}$, Yellow $+5 \text{ to } +12\text{ bpm}$, Red $> +15\text{ bpm}$ drift).
  - Screen ECG for arrhythmias and IJV ultrasound for venous thromboembolism (VTE) risk.
- **Output Countermeasures:** Adjust E4D/CEVIS HIIT (85–95% HRmax) vs. Steady-State (70–80% HRmax) ratio; trigger medical protocol if chest pain, arrhythmia, or IJV stasis is detected.

#### Module C: Neuro-Ocular & Vestibular (`modules/neuro_ocular.py`)
- **Devices & Inputs:** Mini OCT (SNR quality score, Segmentation Confidence %, Total Retinal Volume at ONH $V_{ONH}$ in $\text{mm}^3$, BMO-MRW in $\mu\text{m}$, Global & TSNIT quadrant RNFL thickness in $\mu\text{m}$, posterior scleral radius of curvature $R_c$ in $\text{mm}$), Ultrasound 2 (Optic Nerve Sheath Diameter ONSD at 3mm behind globe, Axial Length AL), VOG (200–500Hz infrared eye tracking for VOR and ocular torsion).
- **Core Logic:**
  - Quality Gatekeeper: Reject scan if Mini OCT $\text{SNR} < 7/10$ or BMO segmentation confidence $< 85\%$.
  - SANS Thresholds (vs. Pre-flight Baseline):
    - Green: $\Delta V_{ONH} < 0.10\text{ mm}^3$ and elevation $< 20\text{ }\mu\text{m}$.
    - Yellow: $\Delta V_{ONH} \ge 0.15\text{ mm}^3$ or elevation $+30\text{--}50\text{ }\mu\text{m}$, or acute RNFL thickening $> 10\text{--}15\text{ }\mu\text{m}$ ($>2\text{ SD}$), or 7-day slope $> +2\text{ }\mu\text{m/day}$.
    - Red: $\Delta V_{ONH} > 0.30\text{ mm}^3$ (Frisen Stage 1+), chronic RNFL thinning $> 8\text{ }\mu\text{m}$ (axonal loss), scleral $\Delta R_c > +15\%$ (flattening $> 150\text{ }\mu\text{m}$), or Ultrasound ONSD $> 6.0\text{ mm}$ (elevated ICP).
- **Output Countermeasures:** Shorten scan interval (biweekly -> weekly -> daily); deploy Lower Body Negative Pressure (LBNP at $-20\text{ to }-50\text{ mmHg}$); initiate intracranial pressure medication protocol.

#### Module D: Immune, Endocrine & Metabolic (`modules/immune_metabolic.py`)
- **Devices & Inputs:** Bio-Analyzer (fingerstick capillary blood 5-part WBC differential, cytokines IL-6, TNF-$\alpha$, IFN-$\gamma$), stress hormones (cortisol, catecholamines), renal stone panel (urinary calcium hypercalciuria, oxalate, phosphate, urine pH, daily hydration volume), Vitamin D status.
- **Core Logic:** Detect T-cell/NK-cell suppression (latent herpesvirus EBV/VZV/CMV reactivation risk), HPA-axis chronic stress elevation, and calcium oxalate/phosphate renal stone crystallization risk.
- **Output Countermeasures:** Prescribe daily Vitamin D3 (800–2000 IU), enforce hydration targets, schedule anti-inflammatory moderate exercise (myokine IL-6 release), and circadian rhythm/sleep hygiene interventions.

#### Module E: Radiation, Acoustics & Cabin Environment (`modules/cabin_environment.py`)
- **Devices & Inputs:** HERA / DOSIS 3D (real-time dose rate $dE/dx$, LET spectrum, solar particle event SPE flux), Acoustic Dosimeter (24h $L_{eq}\text{ dBA}$, $L_{peak}$, daily Noise Dose %), ANITA-2 FTIR analyzer (6-min cycle, 37 trace contaminant gases in ppm/ppb: CO, $\text{NH}_3$ ammonia, benzene, formaldehyde, HF, HCN).
- **Core Logic & Offline Emergency Protocols:**
  1. **Radiation (HERA SPE Alert):** Step 1: Immediate evacuation to Water Wall Storm Shelter (high-hydrogen shielding to prevent secondary neutron scatter). Step 2: Medical countermeasures for acute exposure — subcutaneous G-CSF (Filgrastim) for bone marrow rescue, high-dose antioxidants (NAC, Vitamin C/E) against ROS/DNA double-strand breaks, and Ondansetron (5-HT3 antagonist) for nausea.
  2. **Trace Gas Leak (ANITA-2 SMAC Exceeded):** Step 1: Don Quick-Don Emergency Mask / PBBA and isolate module hatch/valves. Step 2: Maximize ECLSS Trace Contaminant Control System (TCCS high-temp catalytic oxidizer HTCO at $400^\circ\text{C}$ + charcoal beds), or execute ultimate Venting to Vacuum & Repressurization for catastrophic ammonia/coolant leaks. Step 3: Administer antidotes — intravenous Hydroxocobalamin for cyanide (HCN) inhalation; 100% positive-pressure $\text{O}_2$ for CO poisoning.
  3. **Acoustics (Dosimeter Alert):** Daily Dose $> 100\%$ triggers mandatory dual hearing protection (custom earplugs + ANC headset) and rotation to $< \text{NC-40}$ acoustic sleep compartment to prevent TTS turning into permanent PTS. Acute acoustic trauma (blast/rupture) triggers immediate oral corticosteroids (Prednisone/Dexamethasone) + Vitamin E and Magnesium.

## Red Lines

- Confirm destructive or irreversible actions the user didn't ask for.
- Prefer `trash` over `rm`.