"""Role 3 Helper: Status-aware 3-step crew guidance templates for M1-M11.

Kept separate from modules/cardiovascular.py for maintainability while staying
strictly within Role 3's scope (zero impact on other modules or Streamlit UI).
"""

from __future__ import annotations

from typing import Any


def build_indicator_guidance(
    metric_key: str,
    status: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Return astronaut-friendly, status-aware 3-step guidance for M1-M11.

    Designed for zero-medical-background crew:
    - how_to_measure: clear step-by-step device & QC instructions
    - why_in_space: plain-language physiological meaning in microgravity
    - action_steps: numbered offline emergency/routine countermeasures
    """
    st = str(status).upper()
    hr = float(context.get("rest_hr", 65.0))
    base_hr = float(context.get("base_hr", 62.0))
    sbp = float(context.get("sbp", 119.0))
    dbp = float(context.get("dbp", 75.0))
    ptt_age = int(context.get("ptt_age", 3))
    spo2 = float(context.get("spo2", 98.2))
    resp = float(context.get("resp", 14.5))
    pvc = float(context.get("pvc", 0.3))
    afib = bool(context.get("afib", False))
    k_val = float(context.get("potassium", 4.15))
    stand_hr = float(context.get("stand_hr", 12.0))
    stand_sbp = float(context.get("stand_sbp", 5.0))
    dizzy = bool(context.get("dizzy", False))
    pv_delta = float(context.get("pv_delta", 0.0))
    cevis_hr = float(context.get("cevis_hr", 137.0))
    gls_chg = float(context.get("gls_change", 0.0))
    ijv_flow = str(context.get("ijv_flow", "forward"))
    ijv_thrombus = bool(context.get("ijv_thrombus", False))

    if metric_key == "rest_hr_bpm":
        if st == "RED":
            return {
                "how_to_measure": (
                    "CRITICAL RE-CHECK: Float or sit completely still for 5 minutes wearing the Bio-Monitor shirt. "
                    "Confirm ECG strap skin contact >= 0.50 and motion < 0.50 g, and check your oral temperature before repeating."
                ),
                "why_in_space": (
                    f"Your resting heart is beating very fast ({hr:.0f} bpm vs your {base_hr:.0f} bpm Earth baseline). "
                    "In space, this means your heart is working overtime because of severe fluid loss, infection/fever, low blood oxygen, or a clot."
                ),
                "action_steps": [
                    "STOP all CEVIS cycling and heavy E4D resistance workouts right away.",
                    "Record a 12-lead ECG and check your oral temperature + SpO2.",
                    "Notify the Crew Medical Officer / Flight Surgeon and repeat vitals every 4 hours.",
                ],
            }
        if st == "YELLOW":
            return {
                "how_to_measure": (
                    "GUARDED CHECK: Rest quietly for 5 minutes in the Bio-Monitor shirt (no caffeine for 2 hours prior) "
                    "and compare against your morning hydration and sleep log."
                ),
                "why_in_space": (
                    f"Your resting heart rate drifted up to {hr:.0f} bpm (baseline {base_hr:.0f} bpm). "
                    "Microgravity shrinks blood fluid volume, so your heart beats faster to keep blood flowing to your brain."
                ),
                "action_steps": [
                    "Drink 500-750 mL of water with electrolyte tablets over the next hour.",
                    "Prioritize at least 7.5 hours of sleep tonight and skip high-intensity sprints today.",
                    "Repeat your resting Bio-Monitor check in 12 hours.",
                ],
            }
        return {
            "how_to_measure": (
                "Sit or float relaxed for 5 minutes wearing the Bio-Monitor thoracic ECG shirt; "
                "confirm signal quality >= 0.50 and avoid caffeine 2 hours before testing."
            ),
            "why_in_space": (
                f"Your resting heart rate ({hr:.0f} bpm) is close to your pre-flight baseline ({base_hr:.0f} bpm). "
                "That tells us your body fluid level and heart nervous-system control are well balanced."
            ),
            "action_steps": [
                "Continue daily morning Bio-Monitor vitals logging.",
                "Maintain 2.5 L/day fluid intake.",
            ],
        }

    if metric_key == "sbp_mmHg":
        cal_msg = " (Recalibration overdue: >7 days since last arm-cuff check.)" if ptt_age > 7 else ""
        if st == "RED":
            return {
                "how_to_measure": (
                    f"URGENT VERIFICATION: Do not rely on the Bio-Monitor wrist/chest estimate alone{cal_msg}. "
                    "Measure your blood pressure manually with the upper-arm cuff at heart level on both arms."
                ),
                "why_in_space": (
                    f"Blood pressure is dangerously outside safe limits ({sbp:.0f}/{dbp:.0f} mmHg). "
                    "Too high puts extra pressure on head veins and vision (SANS); too low means blood is not reaching your brain."
                ),
                "action_steps": [
                    "Pause heavy E4D lifting and intense exercise immediately.",
                    "Check for headache, blurry vision, or dizziness and check cabin CO2 levels.",
                    "Repeat manual arm-cuff BP every 2-4 hours and alert the Flight Surgeon.",
                ],
            }
        if st == "YELLOW":
            return {
                "how_to_measure": (
                    f"VERIFY WITH ARM CUFF: Run a manual brachial arm-cuff check at heart height to confirm the "
                    f"Bio-Monitor Pulse Transit Time (PTT) reading{cal_msg}."
                ),
                "why_in_space": (
                    f"Your blood pressure ({sbp:.0f}/{dbp:.0f} mmHg) is drifting toward NASA warning limits. "
                    "Without gravity pulling blood down, shifts in salt, fluids, stress, or cabin CO2 can push pressure out of range."
                ),
                "action_steps": [
                    "Recalibrate the Bio-Monitor with the arm cuff today.",
                    "Check cabin ppCO2 (< 2.5 mmHg) and review your sodium/fluid intake.",
                    "Re-measure resting blood pressure in 12-24 hours.",
                ],
            }
        return {
            "how_to_measure": (
                "Continuous Bio-Monitor Pulse Transit Time (PTT) estimates beat-to-beat BP; "
                "calibrate once a week with the manual upper-arm cuff held at heart level."
            ),
            "why_in_space": (
                f"Your blood pressure ({sbp:.0f}/{dbp:.0f} mmHg) is steady inside NASA-STD-3001 bounds, "
                "showing your blood vessels are adapting smoothly to weightlessness."
            ),
            "action_steps": [
                "Continue weekly manual arm-cuff calibration.",
                "No blood pressure adjustment needed.",
            ],
        }

    if metric_key == "spo2_pct":
        if st == "RED":
            return {
                "how_to_measure": (
                    "EMERGENCY HYPOXIA CHECK: Warm your finger for 30 seconds, clip the optical SpO2 sensor securely, "
                    "wait 20 seconds for a steady pulse wave, and immediately check cabin O2/CO2 and neck vein (M9) ultrasound."
                ),
                "why_in_space": (
                    f"Blood oxygen dropped to a critical {spo2:.1f}% (<= 92%). "
                    "Either cabin air is low in oxygen, or a blood clot (pulmonary embolism) is blocking blood from picking up oxygen in your lungs."
                ),
                "action_steps": [
                    "Verify cabin oxygen (PIO2) and CO2 (ppCO2) readings immediately; put on supplemental O2 if low.",
                    "If breathing rate is also >25/min, treat as possible lung clot: run bilateral neck IJV Ultrasound 2 scan now.",
                    "Notify the Crew Medical Officer / Flight Surgeon immediately.",
                ],
            }
        if st == "YELLOW":
            return {
                "how_to_measure": (
                    "WARNING (<96%): Warm your fingertip, confirm snug optical sensor fit, wait 20 seconds for clean waveform lock, "
                    "and cross-check your breathing rate (M4)."
                ),
                "why_in_space": (
                    f"Oxygen saturation ({spo2:.1f}%) is slightly below normal (96-100%). "
                    "This gives an early warning of stale cabin air, mild lung congestion, or an early blood clot."
                ),
                "action_steps": [
                    "Check cabin O2 and CO2 monitors and improve local airflow.",
                    "Repeat SpO2 + breathing rate in 4-6 hours.",
                ],
            }
        return {
            "how_to_measure": (
                "Place the Bio-Monitor optical clip on a warm finger or wrist sensor pad and wait 20 seconds for a steady wave."
            ),
            "why_in_space": (
                f"SpO2 is {spo2:.1f}%, proving your lungs are delivering plenty of oxygen from the cabin air into your bloodstream."
            ),
            "action_steps": ["Continue routine Bio-Monitor oxygen logging."],
        }

    if metric_key == "resp_rate_bpm":
        if st == "RED":
            return {
                "how_to_measure": (
                    "CRITICAL BREATHING CHECK: Float or sit calmly for 60 seconds so the Bio-Monitor chest band measures true resting breaths/min, "
                    "then check SpO2 (M3) and cabin CO2 immediately."
                ),
                "why_in_space": (
                    f"You are breathing very rapidly ({resp:.1f} breaths/min, limit <= 25). "
                    "In a closed spacecraft, rapid breathing signals dangerously high CO2 buildup, low oxygen, infection, or a lung blood clot."
                ),
                "action_steps": [
                    "Check cabin ppCO2 and O2 sensors right away; move to a well-ventilated module.",
                    "Pair with M3 SpO2: if SpO2 < 95%, run immediate neck IJV Ultrasound 2 clot scan and notify CMO.",
                ],
            }
        if st == "YELLOW":
            return {
                "how_to_measure": (
                    "GUARDED (>20/min): Sit still for 60 seconds wearing the Bio-Monitor chest band and check cabin ppCO2."
                ),
                "why_in_space": (
                    f"Breathing rate is mildly elevated ({resp:.1f} breaths/min). "
                    "Pockets of trapped CO2 around sleeping quarters or early cardiopulmonary stress make you breathe faster."
                ),
                "action_steps": [
                    "Check CDRA CO2 scrubber status and turn up cabin mixing fans.",
                    "Re-check breathing rate and SpO2 in 12 hours.",
                ],
            }
        return {
            "how_to_measure": (
                "The Bio-Monitor chest strap counts resting breaths automatically while you sit or float quietly for 60 seconds."
            ),
            "why_in_space": (
                f"Resting breathing ({resp:.1f} breaths/min) is calm and steady, showing cabin air quality and lung function are normal."
            ),
            "action_steps": ["Continue standard daily Bio-Monitor tracking."],
        }

    if metric_key == "pvc_burden_pct":
        if st == "RED":
            return {
                "how_to_measure": (
                    "CRITICAL RHYTHM CHECK: Capture an immediate 12-lead ECG, keep the 5-lead Holter Monitor 2 running, "
                    "and test blood Potassium (K+) using the Bio-Analyzer fingerstick cartridge."
                ),
                "why_in_space": (
                    f"Extra heartbeats (PVCs) reached {pvc:.1f}%{' with Atrial Fibrillation' if afib else ''}, "
                    f"and blood potassium is {k_val:.2f} mmol/L. Low potassium or heart stretching in space makes the heart muscle electrically unstable."
                ),
                "action_steps": [
                    "STOP all CEVIS and E4D workouts immediately.",
                    "If K+ < 3.5 mmol/L, take oral potassium (KCl) supplement per medical kit guide.",
                    "Keep continuous ECG monitoring active and alert the Flight Surgeon immediately.",
                ],
            }
        if st == "YELLOW":
            return {
                "how_to_measure": (
                    "ELEVATED EXTRA BEATS: Continue wearing the 5-lead Holter Monitor 2 (MIT-BIH pattern check) "
                    "and run a Bio-Analyzer fingerstick test for serum Potassium (M11)."
                ),
                "why_in_space": (
                    f"PVC burden increased to {pvc:.1f}% (warning >= 1.5%). "
                    f"Stress, dehydration, or low potassium (currently {k_val:.2f} mmol/L) commonly causes extra ventricular beats in orbit."
                ),
                "action_steps": [
                    "Verify serum K+ >= 3.5 mmol/L and take electrolyte / potassium replacement if low.",
                    "Skip maximal sprints; keep CEVIS cycling in easy Zone 2 until Holter clears.",
                ],
            }
        return {
            "how_to_measure": (
                "Attach the 5-lead Holter Monitor 2 for 24 hours; onboard software checks beat shapes against MIT-BIH arrhythmia templates."
            ),
            "why_in_space": (
                f"Extra heartbeats are minimal ({pvc:.2f}%, no AFib), showing your heart's electrical wiring and mineral balance are steady."
            ),
            "action_steps": ["Continue scheduled Holter surveillance and normal CEVIS workouts."],
        }

    if metric_key == "stand_hr_rise_bpm":
        if st == "RED":
            return {
                "how_to_measure": (
                    "PRESYNCOPE ALERT: Stop the LBNP suction or Stand Test immediately if you feel dizzy, lightheaded, or tunnel-visioned. "
                    "Lie/float flat and record recovery HR and BP."
                ),
                "why_in_space": (
                    f"Your heart jumped +{stand_hr:.0f} bpm and blood pressure dropped -{stand_sbp:.0f} mmHg{' with dizziness' if dizzy else ''}. "
                    f"Because plasma blood volume shrank ({pv_delta:+.1f}% in M10), standing or gravity pulls blood away from your brain, risking fainting on landing."
                ),
                "action_steps": [
                    "Rest flat/neutral until dizziness passes; do NOT stand abruptly.",
                    "Execute NASA salt-water fluid loading (1 L isotonic electrolyte drink + salt tablets).",
                    "Wear lower-body compression garments before any re-entry or planetary G-load and schedule daily LBNP.",
                ],
            }
        if st == "YELLOW":
            return {
                "how_to_measure": (
                    "ORTHOSTATIC WARNING: Seal your waist in the LBNP chamber (-20 to -40 mmHg) or run a 3-min stand test "
                    "while logging HR rise and blood pressure drop."
                ),
                "why_in_space": (
                    f"Heart rate jumped +{stand_hr:.0f} bpm and SBP fell -{stand_sbp:.0f} mmHg. "
                    "Fluid loss in weightlessness reduces your blood volume and weakens blood-vessel reflex tightening."
                ),
                "action_steps": [
                    "Drink 500-750 mL electrolyte solution and review M10 plasma volume (%DeltaPV).",
                    "Add 30-min LBNP (-20 mmHg) sessions 3x/week to retrain blood vessels.",
                ],
            }
        return {
            "how_to_measure": (
                "Seal waist in the LBNP negative-pressure chamber (-25/-40 mmHg) or perform a 3-min post-landing stand test while recording HR and BP."
            ),
            "why_in_space": (
                f"A mild +{stand_hr:.0f} bpm HR rise with no dizziness shows your blood vessels still push blood to your brain when gravity pulls it down."
            ),
            "action_steps": ["Keep bi-weekly LBNP tolerance checks on schedule."],
        }

    if metric_key == "steady_hr_150w_bpm":
        if st == "RED":
            return {
                "how_to_measure": (
                    "DO NOT RUN MAXIMAL BIKE TEST: Pause the CEVIS 150W protocol. Check resting HR, Holter rhythm, "
                    "heart ultrasound (GLS), and neck vein (IJV) scan first."
                ),
                "why_in_space": (
                    f"Heart rate spiked to {cevis_hr:.0f} bpm at a fixed 150W workload. "
                    "Your heart is pumping less blood per beat due to severe deconditioning or fluid loss, leaving little reserve for an emergency spacewalk or egress."
                ),
                "action_steps": [
                    "Suspend HIIT and 150W fitness tests for 14 days.",
                    "Rule out IJV clot, arrhythmia, and hypovolemia before resuming gentle Zone 1/2 cycling.",
                ],
            }
        if st == "YELLOW":
            return {
                "how_to_measure": (
                    "FITNESS DRIFT CHECK: Hydrate well beforehand, cycle on CEVIS at a steady 150W for 10 minutes, "
                    "and average your ECG heart rate over the last 3 minutes."
                ),
                "why_in_space": (
                    f"Heart rate drifted up to {cevis_hr:.0f} bpm at 150W (warning >= 150 bpm). "
                    "Without daily gravity, aerobic stamina (VO2max) and stroke volume gradually fade."
                ),
                "action_steps": [
                    "Check M10 plasma volume (%DeltaPV) and hydrate before workouts.",
                    "Shift CEVIS to structured Zone 2 aerobic sessions (4x/week) and re-test in 7 days.",
                ],
            }
        return {
            "how_to_measure": (
                "Pedal CEVIS at a steady 150 Watts for 10 minutes and average your ECG heart rate over the final 3 minutes."
            ),
            "why_in_space": (
                f"Steady 150W heart rate ({cevis_hr:.0f} bpm) shows your heart pumps strongly per beat and your aerobic fitness is intact for EVA/landing."
            ),
            "action_steps": ["Continue current CEVIS Zone 2/4 aerobic schedule."],
        }

    if metric_key == "gls_change_pct":
        if st == "RED":
            return {
                "how_to_measure": (
                    "CRITICAL HEART STRAIN SCAN: Acquire clear Ultrasound 2 apical 4-, 3-, and 2-chamber heart views "
                    "and pair with blood CRP/clotting markers (M11)."
                ),
                "why_in_space": (
                    f"Heart muscle squeeze (GLS) dropped {gls_chg:+.1f}% (red limit <= -15%). "
                    "This detects early weakening or stress on the heart wall before standard pumping numbers fall."
                ),
                "action_steps": [
                    "Suspend all heavy E4D and HIIT exercise immediately.",
                    "Save ultrasound cine loops for Flight Surgeon review and repeat echocardiogram in 24-48 hours.",
                ],
            }
        if st == "YELLOW":
            return {
                "how_to_measure": (
                    "STRAIN WARNING: Re-capture Ultrasound 2 apical 4-, 3-, and 2-chamber views ensuring crisp heart-wall borders for speckle tracking."
                ),
                "why_in_space": (
                    f"GLS shifted {gls_chg:+.1f}% from pre-flight (warning <= -10%). "
                    "Lower workload in weightlessness can cause mild heart-muscle thinning over long missions."
                ),
                "action_steps": [
                    "Avoid maximal all-out sprints; maintain steady Zone 2 aerobic conditioning.",
                    "Repeat Ultrasound 2 GLS scan in 7 days.",
                ],
            }
        return {
            "how_to_measure": (
                "Use Ultrasound 2 from the chest apex to capture 4-, 3-, and 2-chamber cine loops for automated GLS tracking."
            ),
            "why_in_space": (
                f"Heart squeeze strain ({gls_chg:+.1f}%) is healthy, meaning your heart muscle hasn't weakened in microgravity."
            ),
            "action_steps": ["Maintain monthly Ultrasound 2 heart check."],
        }

    if metric_key == "ijv_flow_status":
        if st == "RED":
            return {
                "how_to_measure": (
                    "EMERGENCY NECK CLOT SCAN: Glide the Ultrasound 2 linear probe gently over left and right neck veins. "
                    "Document reversed Doppler flow or non-collapsing clot—do NOT press hard enough to dislodge a thrombus."
                ),
                "why_in_space": (
                    f"Neck vein status is CRITICAL (flow='{ijv_flow}', thrombus={ijv_thrombus}). "
                    "Weightlessness shifts ~2 L of blood into your head/neck, stalling vein drainage until a clot forms—which can travel to your lungs (fatal pulmonary embolism)."
                ),
                "action_steps": [
                    "STOP heavy E4D straining and intense CEVIS workouts immediately.",
                    "Initiate the onboard anticoagulation medication checklist per Flight Surgeon protocol.",
                    "Run controlled -25 mmHg LBNP and check SpO2 (M3) + breathing rate (M4) every 4 hours for lung-clot signs.",
                ],
            }
        if st == "YELLOW":
            return {
                "how_to_measure": (
                    "STASIS CHECK: Scan both left and right neck IJV with Ultrasound 2 color Doppler and confirm the vein still collapses flat under light probe pressure."
                ),
                "why_in_space": (
                    "Blood flow in your neck vein has stalled ('stagnant') because ~2 L of fluid shifted toward your head in zero-g. "
                    "Stagnant flow is the warning stage right before a blood clot forms."
                ),
                "action_steps": [
                    "Run 30 minutes of -20 mmHg LBNP daily to pull fluid back down toward your legs.",
                    "Avoid head-down tilt and slightly elevate your upper body while sleeping; re-scan neck in 24-48 hours.",
                ],
            }
        return {
            "how_to_measure": (
                "Place the Ultrasound 2 linear probe on the side of your neck: check that the vein collapses easily with gentle pressure and shows steady forward color Doppler flow."
            ),
            "why_in_space": (
                "Even though weightlessness pushes fluid toward your head, forward and collapsible neck vein flow confirms there is no dangerous blood pooling or clot."
            ),
            "action_steps": ["Continue routine monthly bilateral neck IJV ultrasound screening."],
        }

    if metric_key == "plasma_volume_delta_pct":
        if st == "RED":
            return {
                "how_to_measure": (
                    "RUN BIO-ANALYZER CBC: Test fingerstick Hemoglobin (Hb) and Hematocrit (Hct) immediately to track fluid depletion via Dill & Costill (1974)."
                ),
                "why_in_space": (
                    f"Plasma blood volume dropped {pv_delta:+.1f}% (red limit <= -20%). "
                    "Your blood is overly concentrated, sharply raising fainting risk (M6) and clot viscosity (M9)."
                ),
                "action_steps": [
                    "Drink 1 L of isotonic electrolyte fluid + salt tablets immediately.",
                    "Pause strenuous exercise until repeat Hb/Hct confirms volume recovery.",
                ],
            }
        if st == "YELLOW":
            return {
                "how_to_measure": (
                    "CHECK BIO-ANALYZER Hb/Hct: Insert fingerstick CBC cartridge to calculate %DeltaPV change from pre-flight baseline."
                ),
                "why_in_space": (
                    f"Plasma volume is down {pv_delta:+.1f}% (warning <= -12%). "
                    "Microgravity makes your kidneys shed extra water, shrinking total circulating blood volume."
                ),
                "action_steps": [
                    "Increase daily fluids by +750 mL with electrolytes and re-check orthostatic tolerance (M6).",
                ],
            }
        return {
            "how_to_measure": (
                "Run a fingerstick Bio-Analyzer CBC cartridge for Hemoglobin (Hb) and Hematocrit (Hct); the system computes %DeltaPV automatically."
            ),
            "why_in_space": (
                f"Plasma volume change ({pv_delta:+.1f}%) is mild and within normal spaceflight adaptation limits."
            ),
            "action_steps": ["Maintain 2.5 L/day hydration target."],
        }

    # M11: potassium_mmol_l / OSD-575 blood chemistry
    if st == "RED":
        return {
            "how_to_measure": (
                "URGENT CHEMISTRY PANEL: Run a fresh Bio-Analyzer lithium-heparin cartridge to confirm serum Potassium (K+), Fibrinogen, PF4, and CRP."
            ),
            "why_in_space": (
                f"Blood chemistry is critical (K+ {k_val:.2f} mmol/L or elevated clotting/inflammation markers). "
                "Low potassium triggers dangerous heart rhythms (M5), while high Fibrinogen/PF4 increases neck-vein clot risk (M9)."
            ),
            "action_steps": [
                "STOP high-intensity workouts; take oral KCl if K+ < 3.5 mmol/L.",
                "Run 12-lead ECG + bilateral neck IJV ultrasound; repeat chemistry panel in 12 hours.",
            ],
        }
    if st == "YELLOW":
        return {
            "how_to_measure": (
                "CHEMISTRY CHECK: Insert lithium-heparin cartridge into Bio-Analyzer and verify K+, CRP, and clotting markers."
            ),
            "why_in_space": (
                f"Borderline blood chemistry (K+ {k_val:.2f} mmol/L or rising CRP/Fibrinogen) increases heart-rhythm irritability and inflammation."
            ),
            "action_steps": [
                "Replenish potassium/electrolytes orally and hydrate well before exercise.",
                "Repeat Bio-Analyzer chemistry check in 24-48 hours.",
            ],
        }
    return {
        "how_to_measure": (
            "Insert a lithium-heparin capillary/venous cartridge into the onboard Bio-Analyzer chemistry reader."
        ),
        "why_in_space": (
            f"Serum potassium ({k_val:.2f} mmol/L), electrolytes, and clotting proteins are balanced, protecting heart rhythm and vessel health."
        ),
        "action_steps": ["Continue routine monthly Bio-Analyzer blood chemistry checks."],
    }
