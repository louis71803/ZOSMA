"""Centralized data loader, session persistence, and cross-module context router.

Role 1 exclusively owns this file. Domain modules (Roles 2-6) remain stateless
and never write to shared storage directly.
"""

from __future__ import annotations

import importlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from core.schema import ModuleEvaluationResult, normalize_module_result

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RUNTIME_SESSION_PATH = DATA_DIR / "runtime_session.json"

MODULE_ORDER: tuple[str, ...] = (
    "cabin_environment",
    "cardiovascular",
    "musculoskeletal",
    "neuro_ocular",
    "immune_metabolic",
)

MODULE_DISPLAY_NAMES: dict[str, str] = {
    "musculoskeletal": "Musculoskeletal (Bone & Muscle)",
    "cardiovascular": "Cardiovascular & Aerobic",
    "neuro_ocular": "Neuro-Ocular & Vestibular (SANS)",
    "immune_metabolic": "Immune, Endocrine & Metabolic",
    "cabin_environment": "Radiation, Acoustics & Cabin Env",
}

EXPECTED_DATA_FILES: dict[str, list[str]] = {
    "shared_real": [
        "OSD-569_inspiration4_cbc.csv",
        "OSD-575_cmp.csv",
        "OSD-575_cv_panel.csv",
    ],
    "musculoskeletal": [
        "e4d_sets.csv",
        "measurements_long.csv",
        "preflight_baseline.json",
    ],
    "cardiovascular": [
        "daily_vitals.csv",
        "bike_test.csv",
        "stand_test.csv",
        "holter_24h.csv",
        "ultrasound.csv",
        "biomonitor_stream_day124.csv",
    ],
    "neuro_ocular": [
        "mini_oct_scans.csv",
        "ultrasound_eye.csv",
        "vog_vestibular.csv",
        "preflight_baseline.json",
    ],
    "immune_metabolic": [
        "daily_checkin.csv",
        "cbc_monthly.csv",
        "saliva_virus.csv",
        "events.csv",
        "preflight_baseline.json",
    ],
    "cabin_environment": [
        "rad01_area_dose.csv",
        "rad02_crew_dose_daily.csv",
        "goes_integral_protons_6h.json",
        "aco01_module_spl.csv",
        "aco02_crew_dosimetry.csv",
        "atm01_co2.csv",
        "atm02_pressure_o2.csv",
        "atm03_thermal.csv",
        "atm04_voc.csv",
        "iso01_sleep.csv",
        "iso02_pvt.csv",
        "iso03_mood.csv",
    ],
}


def ensure_data_directories() -> None:
    """Create standard data directories if they do not exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for folder in EXPECTED_DATA_FILES:
        (DATA_DIR / folder).mkdir(parents=True, exist_ok=True)


def _import_domain_module(module_id: str) -> Any:
    """Safely import a domain module, supporting immune_metabolic or immune alias."""
    candidates = [f"modules.{module_id}"]
    if module_id == "immune_metabolic":
        candidates.append("modules.immune")

    last_err: Optional[Exception] = None
    for mod_path in candidates:
        try:
            return importlib.import_module(mod_path)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
    raise ImportError(f"Could not import domain module for '{module_id}': {last_err}")


def inspect_module_data_status(module_id: str) -> dict[str, Any]:
    """Check whether real CSV/JSON files exist under data/<module_id>/."""
    ensure_data_directories()
    folder = DATA_DIR / module_id
    if module_id == "immune_metabolic" and not any(folder.iterdir()):
        alt_folder = DATA_DIR / "immune"
        if alt_folder.exists() and any(alt_folder.iterdir()):
            folder = alt_folder

    present_files = sorted(
        [
            p.name
            for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in {".csv", ".json"}
        ]
    )
    expected = EXPECTED_DATA_FILES.get(module_id, [])
    missing = [name for name in expected if name not in present_files]
    has_real_files = len(present_files) > 0
    return {
        "module_id": module_id,
        "folder": str(folder),
        "has_real_files": has_real_files,
        "source_mode": "REAL_CSV" if has_real_files else "SIMULATED_DEMO",
        "present_files": present_files,
        "missing_files": missing,
    }


def inspect_all_data_status() -> dict[str, dict[str, Any]]:
    """Return file availability metadata across all 5 modules plus shared_real."""
    statuses = {mod_id: inspect_module_data_status(mod_id) for mod_id in MODULE_ORDER}
    statuses["shared_real"] = inspect_module_data_status("shared_real")
    return statuses


def _coerce_scalar(val: Any) -> Any:
    if pd.isna(val):
        return None
    if hasattr(val, "item"):
        val = val.item()
    if isinstance(val, str):
        low = val.strip().lower()
        if low == "true":
            return True
        if low == "false":
            return False
    return val


def load_module_files_into_payload(module_id: str) -> tuple[dict[str, Any], Optional[dict[str, Any]], str]:
    """Read CSV/JSON files from data/<module_id>/ into a payload + optional baseline.

    Returns (payload_dict, baseline_dict_or_none, data_source_tag).
    Never raises FileNotFoundError.
    """
    ensure_data_directories()
    folder = DATA_DIR / module_id
    if module_id == "immune_metabolic" and not any(folder.iterdir()):
        alt_folder = DATA_DIR / "immune"
        if alt_folder.exists():
            folder = alt_folder

    files = sorted([p for p in folder.iterdir() if p.is_file()]) if folder.exists() else []
    csv_files = [p for p in files if p.suffix.lower() == ".csv"]
    json_files = [p for p in files if p.suffix.lower() == ".json"]

    if not csv_files and not json_files:
        return {}, None, "SIMULATED"

    payload: dict[str, Any] = {"_loaded_files": [p.name for p in csv_files + json_files]}
    baseline: Optional[dict[str, Any]] = None

    for jf in json_files:
        try:
            with jf.open("r", encoding="utf-8") as fh:
                parsed = json.load(fh)
            if "baseline" in jf.stem.lower() and isinstance(parsed, dict):
                baseline = parsed
            elif isinstance(parsed, dict):
                for k, v in parsed.items():
                    payload[k] = v
        except Exception:  # noqa: BLE001
            continue

    for cf in csv_files:
        try:
            df = pd.read_csv(cf)
            if df.empty:
                continue
            payload[f"csv_{cf.stem}"] = df.to_dict(orient="records")
            last_row = df.iloc[-1].to_dict()
            for col, val in last_row.items():
                coerced = _coerce_scalar(val)
                if coerced is not None:
                    payload[str(col)] = coerced
        except Exception:  # noqa: BLE001
            continue

    return payload, baseline, "REAL"


def load_runtime_session() -> dict[str, Any]:
    """Load persisted manual telemetry & session metadata from data/runtime_session.json."""
    ensure_data_directories()
    default_session: dict[str, Any] = {
        "crew_id": "C002",
        "mission_day": 124,
        "scenario": "green",
        "lang": "en",
        "updated_at": None,
        "manual_overrides": {mod: {} for mod in MODULE_ORDER},
        "history": [],
    }
    if not RUNTIME_SESSION_PATH.exists():
        return default_session

    try:
        with RUNTIME_SESSION_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return default_session
        merged = dict(default_session)
        merged.update(data)
        overrides = dict(default_session["manual_overrides"])
        if isinstance(data.get("manual_overrides"), dict):
            for mod in MODULE_ORDER:
                if isinstance(data["manual_overrides"].get(mod), dict):
                    overrides[mod] = dict(data["manual_overrides"][mod])
        merged["manual_overrides"] = overrides
        if not isinstance(merged.get("history"), list):
            merged["history"] = []
        return merged
    except Exception:  # noqa: BLE001
        return default_session


def save_runtime_session(
    manual_overrides: dict[str, dict[str, Any]],
    crew_id: str = "C002",
    mission_day: int = 124,
    scenario: str = "green",
    results: Optional[dict[str, ModuleEvaluationResult]] = None,
    lang: str = "en",
) -> dict[str, Any]:
    """Persist manual input overrides and a compact summary snapshot to runtime_session.json."""
    ensure_data_directories()
    existing = load_runtime_session()
    timestamp = datetime.now(timezone.utc).isoformat()

    history = list(existing.get("history", []))
    if results:
        history.append(
            {
                "timestamp": timestamp,
                "crew_id": crew_id,
                "mission_day": mission_day,
                "scenario": scenario,
                "statuses": {k: v.status_light for k, v in results.items()},
                "manual_overrides": manual_overrides,
            }
        )
        history = history[-50:]

    session_doc = {
        "crew_id": crew_id,
        "mission_day": mission_day,
        "scenario": scenario,
        "lang": lang if lang in {"en", "zh"} else "en",
        "updated_at": timestamp,
        "manual_overrides": manual_overrides,
        "history": history,
    }
    with RUNTIME_SESSION_PATH.open("w", encoding="utf-8") as fh:
        json.dump(session_doc, fh, indent=2, ensure_ascii=False)
    return session_doc


def _build_safe_fallback_result(
    module_id: str,
    crew_id: str,
    mission_day: int,
    error_message: str,
) -> ModuleEvaluationResult:
    """Emergency fallback result when a domain module fails unexpectedly."""
    body_map = {
        "musculoskeletal": "lower_limb_bone_muscle",
        "cardiovascular": "heart_vascular",
        "neuro_ocular": "eyes_vestibular",
        "immune_metabolic": "immune_renal",
        "cabin_environment": ["whole_body", "lungs", "brain", "ears"],
    }
    return normalize_module_result(
        {
            "module_id": module_id,
            "body_part_tag": body_map.get(module_id, "whole_body"),
            "crew_id": crew_id,
            "mission_day": mission_day,
            "status_light": "YELLOW",
            "quality_passed": False,
            "data_source": "SIMULATED",
            "summary_note": f"Fallback safe mode active due to module error: {error_message}",
            "metrics": [
                {
                    "metric_name": f"{module_id}_module_health",
                    "current_val": 0.0,
                    "baseline_val": 1.0,
                    "unit": "status",
                    "status_light": "INSUFFICIENT_DATA",
                    "decided_by": "quality_check",
                    "data_source": "SIMULATED",
                    "message": f"Module fallback activated: {error_message}",
                    "action": "Inspect module code or input payload; re-run evaluation.",
                }
            ],
            "guidance": {
                "how_to_measure": "Verify sensor files in data/ and ensure module evaluate() returns valid contract.",
                "plain_explanation": "This subsystem is running in protected fallback mode so Mission Control remains operational.",
                "action_protocol": [
                    "Check data folder CSVs or run export_demo_csvs().",
                    "Inspect terminal traceback for the module developer.",
                ],
            },
            "short_term_plan": {
                "next_measurement_in_hours": 1,
                "immediate_actions": [f"Review {module_id} module fallback warning."],
                "urgent_alert": False,
            },
            "long_term_plan": {
                "days_until_red_prediction": None,
                "routine_prescription_adjustment": "Restore normal module evaluation before next scheduled check.",
            },
        },
        module_id=module_id,
    )


def _extract_metric_value(result: ModuleEvaluationResult, candidates: set[str]) -> Optional[Any]:
    for item in result.metrics:
        if item.metric_name.lower() in candidates:
            return item.current_val
    return None


def evaluate_all_modules(
    manual_overrides: Optional[dict[str, dict[str, Any]]] = None,
    scenario: str = "green",
    crew_id: str = "C002",
    mission_day: int = 124,
    prefer_real_csv: bool = True,
) -> tuple[dict[str, ModuleEvaluationResult], dict[str, Any]]:
    """Run all 5 domain modules with CSV/demo fallback and cross-module context propagation.

    Execution order runs `cabin_environment` first so `spe_alert`, `ppco2_1h_mmHg`,
    and `sleep_tst_h` are propagated to `immune_metabolic` and `neuro_ocular`.
    """
    overrides = manual_overrides or {}
    results: dict[str, ModuleEvaluationResult] = {}
    cross_context: dict[str, Any] = {
        "spe_alert": False,
        "ppco2_1h_mmHg": 1.8,
        "sleep_tst_h": 7.1,
        "propagated_flags": [],
    }

    for module_id in MODULE_ORDER:
        try:
            mod = _import_domain_module(module_id)

            baseline = mod.demo_baseline() if hasattr(mod, "demo_baseline") else {}
            demo_pay = (
                mod.demo_payload(scenario=scenario)
                if hasattr(mod, "demo_payload")
                else {}
            )

            file_payload: dict[str, Any] = {}
            file_baseline: Optional[dict[str, Any]] = None
            data_source = "SIMULATED"

            if prefer_real_csv:
                file_payload, file_baseline, data_source = load_module_files_into_payload(module_id)

            if file_baseline:
                baseline = {**baseline, **file_baseline}

            payload = dict(demo_pay)
            if file_payload:
                payload.update(file_payload)
                payload["data_source"] = "REAL"
            else:
                payload.setdefault("data_source", data_source)

            payload["crew_id"] = crew_id
            payload["mission_day"] = mission_day

            # Apply cross-module context from Role 6 -> Role 5 & Role 4
            if module_id == "immune_metabolic":
                if cross_context.get("spe_alert"):
                    payload["spe_event_flag"] = True
                    cross_context["propagated_flags"].append(
                        "cabin_environment.spe_alert -> immune_metabolic.spe_event_flag"
                    )
                if "sleep_h" not in overrides.get(module_id, {}) and cross_context.get("sleep_tst_h") is not None:
                    payload.setdefault("sleep_h", cross_context["sleep_tst_h"])

            if module_id == "neuro_ocular":
                if cross_context.get("ppco2_1h_mmHg") is not None:
                    payload["ppco2_1h_mmHg"] = cross_context["ppco2_1h_mmHg"]
                    cross_context["propagated_flags"].append(
                        f"cabin_environment.ppco2_1h_mmHg ({cross_context['ppco2_1h_mmHg']}) -> neuro_ocular"
                    )

            # Manual UI slider overrides take final precedence
            mod_override = overrides.get(module_id) or {}
            for k, v in mod_override.items():
                if v is not None:
                    payload[k] = v

            # Also keep cross-module context synced if cabin_environment had manual overrides
            raw_result = mod.evaluate(payload=payload, baseline=baseline)
            norm_result = normalize_module_result(raw_result, module_id=module_id)

            if not norm_result.data_source:
                norm_result.data_source = data_source

            results[module_id] = norm_result

            # Update cross-module context after cabin_environment runs
            if module_id == "cabin_environment":
                spe_val = payload.get("spe_alert")
                if spe_val is None:
                    spe_val = _extract_metric_value(norm_result, {"spe_alert", "rad_03_spe_alert", "proton_flux_10mev_pfu"})
                if isinstance(spe_val, (int, float)) and not isinstance(spe_val, bool):
                    spe_flag = float(spe_val) >= 10.0
                else:
                    spe_flag = bool(spe_val)
                cross_context["spe_alert"] = spe_flag

                co2_val = payload.get("ppco2_1h_mmHg")
                if co2_val is None:
                    co2_val = _extract_metric_value(norm_result, {"ppco2_1h_mmhg", "atm_01_ppco2_1h"})
                if co2_val is not None:
                    try:
                        cross_context["ppco2_1h_mmHg"] = float(co2_val)
                    except (TypeError, ValueError):
                        pass

                sleep_val = payload.get("sleep_tst_h")
                if sleep_val is None:
                    sleep_val = _extract_metric_value(norm_result, {"sleep_tst_h", "iso_01_sleep_tst"})
                if sleep_val is not None:
                    try:
                        cross_context["sleep_tst_h"] = float(sleep_val)
                    except (TypeError, ValueError):
                        pass

        except Exception as exc:  # noqa: BLE001
            results[module_id] = _build_safe_fallback_result(
                module_id=module_id,
                crew_id=crew_id,
                mission_day=mission_day,
                error_message=str(exc),
            )

    return results, cross_context
