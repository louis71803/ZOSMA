"""Z.O.S.M.A. — Deep-Space Astronaut Health Monitoring System (SpaceX HUD Frontend).

Role 1 (Lead System Integrator & UI Architect) owns this file.
Mounts the bespoke HTML/CSS/SVG/JS SpaceX Crew Dragon style Mission Control HUD
via Streamlit's bidirectional `st.components.v2` bridge while preserving 100% of
the Python 5-module evaluation contract, persistence, and closed-loop scheduler.
"""

from __future__ import annotations

import importlib
from typing import Any

import streamlit as st
import streamlit.components.v2 as components_v2

from core.data_loader import (
    MODULE_DISPLAY_NAMES,
    MODULE_ORDER,
    evaluate_all_modules,
    inspect_all_data_status,
    load_runtime_session,
    save_runtime_session,
)
from core.scheduler import aggregate_mission_schedule
from core.schema import ModuleEvaluationResult
from ui.hud_assets import HUD_CSS, HUD_HTML, HUD_JS

st.set_page_config(
    page_title="Z.O.S.M.A. Flight Surgeon HUD",
    page_icon="🧑‍🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MODULE_SHORT_NAMES: dict[str, str] = {
    "cabin_environment": "Cabin & Rad",
    "cardiovascular": "Cardiovascular",
    "musculoskeletal": "Musculoskeletal",
    "neuro_ocular": "Neuro-Ocular",
    "immune_metabolic": "Immune & Renal",
}

DEFAULT_MANUAL_INPUTS: dict[str, dict[str, Any]] = {
    "cabin_environment": {
        "ppco2_1h_mmHg": 1.85,
        "proton_flux_10mev_pfu": 1.8,
        "crew_leq8_dBA": 63.0,
        "sleep_tst_h": 7.1,
        "spe_alert": False,
    },
    "cardiovascular": {
        "rest_hr_bpm": 64.0,
        "spo2_pct": 98.2,
        "pvc_burden_pct": 0.3,
        "ijv_flow": "forward",
        "ijv_thrombus": False,
    },
    "musculoskeletal": {
        "csa_thigh_cm2": 146.2,
        "velocity_loss_pct": 12.5,
        "ctx": 0.39,
        "body_mass_kg": 73.1,
    },
    "neuro_ocular": {
        "delta_trt_um": 9.0,
        "delta_v_onh_mm3": 0.06,
        "onsd_mm": 5.1,
        "sph_eq_shift_d": 0.25,
        "folds_foveal": False,
    },
    "immune_metabolic": {
        "temp_c": 36.7,
        "lymph": 1.95,
        "saliva_vzv": 0.0,
        "hydration_ml": 2550.0,
    },
}

# Register bidirectional SpaceX HUD frontend component once at module import
zosma_hud_component = components_v2.component(
    "zosma_spacex_hud",
    html=HUD_HTML,
    css=HUD_CSS,
    js=HUD_JS,
    isolate_styles=True,
)


def _inject_shell_dark_css() -> None:
    """Eliminate Streamlit default white/light chrome & excessive outer margins."""
    st.markdown(
        """
        <style>
        html, body, [data-testid="stAppViewContainer"], .stApp {
            background-color: #04070f !important;
            color: #e2e8f0 !important;
        }
        [data-testid="stHeader"] {
            background: transparent !important;
            height: 1.5rem !important;
        }
        .block-container {
            padding-top: 0.75rem !important;
            padding-bottom: 1rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 100% !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_hud_session_state() -> None:
    if "hud_initialized" in st.session_state:
        return

    disk_session = load_runtime_session()
    st.session_state["crew_id"] = str(disk_session.get("crew_id", "C002"))
    st.session_state["mission_day"] = int(disk_session.get("mission_day", 124))
    scen = str(disk_session.get("scenario", "green"))
    st.session_state["scenario"] = scen if scen in {"green", "yellow", "red", "bad_data"} else "green"
    st.session_state["prefer_real_csv"] = True
    st.session_state["use_manual_overrides"] = False
    st.session_state["selected_module"] = "neuro_ocular"
    st.session_state["last_action_ts"] = 0

    merged_inputs: dict[str, dict[str, Any]] = {}
    saved_ov = disk_session.get("manual_overrides", {})
    for mod_id in MODULE_ORDER:
        base_dict = dict(DEFAULT_MANUAL_INPUTS.get(mod_id, {}))
        if isinstance(saved_ov.get(mod_id), dict):
            base_dict.update(saved_ov[mod_id])
        merged_inputs[mod_id] = base_dict

    st.session_state["manual_inputs"] = merged_inputs
    st.session_state["hud_initialized"] = True


def _serialize_hud_payload(
    results: dict[str, ModuleEvaluationResult],
    schedule: dict[str, Any],
    cross_context: dict[str, Any],
    data_statuses: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Pack validated Pydantic outputs into a clean JSON dict for the frontend HUD."""
    modules_json: dict[str, Any] = {}
    for mod_id in MODULE_ORDER:
        res = results[mod_id]
        dumped = res.model_dump()
        dumped["display_name"] = MODULE_DISPLAY_NAMES.get(mod_id, mod_id)
        dumped["short_name"] = MODULE_SHORT_NAMES.get(mod_id, mod_id)
        modules_json[mod_id] = dumped

    folder_summary = [
        {
            "module_id": mod_id,
            "short_name": MODULE_SHORT_NAMES.get(mod_id, mod_id),
            "has_real_files": bool(data_statuses[mod_id]["has_real_files"]),
        }
        for mod_id in MODULE_ORDER
    ]

    return {
        "crew_id": st.session_state["crew_id"],
        "mission_day": st.session_state["mission_day"],
        "scenario": st.session_state["scenario"],
        "prefer_real_csv": st.session_state["prefer_real_csv"],
        "use_manual_overrides": st.session_state["use_manual_overrides"],
        "default_module": st.session_state["selected_module"],
        "manual_inputs": st.session_state["manual_inputs"],
        "module_order": list(MODULE_ORDER),
        "modules": modules_json,
        "schedule": schedule,
        "propagated_flags": cross_context.get("propagated_flags", []),
        "data_statuses": folder_summary,
    }


def _apply_hud_event(action: dict[str, Any]) -> None:
    """Process bidirectional action events sent from the JS SpaceX HUD."""
    ts = int(action.get("ts", 0))
    if ts and ts == st.session_state.get("last_action_ts"):
        return
    st.session_state["last_action_ts"] = ts

    act_type = str(action.get("type", ""))
    if action.get("selected_module") in MODULE_ORDER:
        st.session_state["selected_module"] = action["selected_module"]
    if action.get("crew_id"):
        st.session_state["crew_id"] = str(action["crew_id"])
    if action.get("mission_day") is not None:
        st.session_state["mission_day"] = max(1, int(action["mission_day"]))
    if action.get("scenario") in {"green", "yellow", "red", "bad_data"}:
        st.session_state["scenario"] = str(action["scenario"])
    if "prefer_real_csv" in action:
        st.session_state["prefer_real_csv"] = bool(action["prefer_real_csv"])
    if "use_manual_overrides" in action:
        st.session_state["use_manual_overrides"] = bool(action["use_manual_overrides"])
    if isinstance(action.get("manual_inputs"), dict):
        st.session_state["manual_inputs"] = action["manual_inputs"]

    if act_type == "generate_demo_csvs":
        generated = []
        for mod_id in MODULE_ORDER:
            mod = importlib.import_module(f"modules.{mod_id}")
            if hasattr(mod, "export_demo_csvs"):
                generated.extend(mod.export_demo_csvs())
        st.toast(f"Generated {len(generated)} starter CSV/JSON files inside data/!", icon="📡")
        st.rerun()

    elif act_type == "save_and_run":
        active_ov = st.session_state["manual_inputs"] if st.session_state["use_manual_overrides"] else {}
        new_results, _ = evaluate_all_modules(
            manual_overrides=active_ov,
            scenario=st.session_state["scenario"],
            crew_id=st.session_state["crew_id"],
            mission_day=st.session_state["mission_day"],
            prefer_real_csv=st.session_state["prefer_real_csv"],
        )
        save_runtime_session(
            manual_overrides=st.session_state["manual_inputs"],
            crew_id=st.session_state["crew_id"],
            mission_day=st.session_state["mission_day"],
            scenario=st.session_state["scenario"],
            results=new_results,
        )
        st.toast("Saved telemetry to data/runtime_session.json & executed all 5 agents!", icon="🚀")
        st.rerun()

    elif act_type in {"switch_scenario", "reset_overrides"}:
        st.rerun()


def main() -> None:
    _inject_shell_dark_css()
    _init_hud_session_state()

    active_overrides = (
        st.session_state["manual_inputs"]
        if st.session_state["use_manual_overrides"]
        else {}
    )
    results, cross_context = evaluate_all_modules(
        manual_overrides=active_overrides,
        scenario=st.session_state["scenario"],
        crew_id=st.session_state["crew_id"],
        mission_day=st.session_state["mission_day"],
        prefer_real_csv=st.session_state["prefer_real_csv"],
    )
    schedule = aggregate_mission_schedule(results=results, cross_context=cross_context)
    data_statuses = inspect_all_data_status()

    hud_payload = _serialize_hud_payload(
        results=results,
        schedule=schedule,
        cross_context=cross_context,
        data_statuses=data_statuses,
    )

    event_result = zosma_hud_component(
        key="zosma_main_hud",
        data=hud_payload,
        width="stretch",
        height="content",
        on_hud_action_change=lambda: None,
    )

    if event_result and getattr(event_result, "hud_action", None):
        _apply_hud_event(event_result.hud_action)


if __name__ == "__main__":
    main()
