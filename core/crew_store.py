"""Multi-Crew Record Persistence & Mission Lifecycle Store (`core/crew_store.py`).

Role 1 exclusively owns this file.
Manages per-astronaut JSON profiles inside `data/crew_records/<crew_id>.json` so
multiple crew members (e.g., C001, C002, C003, C004+) can each maintain:
- `data_lifecycle_mode`: `"day1_standby"` (initial flight cold-start) or `"day124_showcase"` (full CSV/demo dataset)
- `onboarding_completed`: bool (whether initial UI briefing banner is collapsed)
- `mission_day`: int (default 1 for `day1_standby`, 124 for `day124_showcase`)
- `daily_vitals`, `module_checkins`, `checkin_series` (longitudinal time-series per crew)
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.checkin_tracker import default_daily_vitals, default_module_checkins

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CREW_RECORDS_DIR = DATA_DIR / "crew_records"

DEFAULT_CREW_ROSTER: list[dict[str, str]] = [
    {"crew_id": "C001", "role_en": "Commander (CDR)", "role_zh": "任務指揮官 (CDR)"},
    {"crew_id": "C002", "role_en": "Flight Engineer (FE-1)", "role_zh": "航太工程師 (FE-1)"},
    {"crew_id": "C003", "role_en": "Payload Specialist (MS-1)", "role_zh": "酬載專家 (MS-1)"},
    {"crew_id": "C004", "role_en": "Medical Officer (CMO)", "role_zh": "隨艦醫官 (CMO)"},
]


def sanitize_crew_id(raw_id: Any) -> str:
    """Normalize a crew ID token to a safe uppercase alphanumeric identifier."""
    token = re.sub(r"[^A-Za-z0-9_-]", "", str(raw_id or "C002").strip().upper())
    return token or "C002"


def ensure_crew_records_dir() -> Path:
    """Ensure `data/crew_records/` exists."""
    CREW_RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    return CREW_RECORDS_DIR


def _crew_file_path(crew_id: str) -> Path:
    ensure_crew_records_dir()
    safe_id = sanitize_crew_id(crew_id)
    return CREW_RECORDS_DIR / f"{safe_id}.json"


def build_default_crew_record(
    crew_id: str = "C002",
    data_lifecycle_mode: str = "day1_standby",
) -> dict[str, Any]:
    """Build a clean initial crew record."""
    safe_id = sanitize_crew_id(crew_id)
    mode = (
        data_lifecycle_mode
        if data_lifecycle_mode in {"day1_standby", "day124_showcase"}
        else "day1_standby"
    )
    default_day = 1 if mode == "day1_standby" else 124
    roster_match = next(
        (r for r in DEFAULT_CREW_ROSTER if r["crew_id"] == safe_id),
        {"crew_id": safe_id, "role_en": "Mission Specialist", "role_zh": "任務專家"},
    )
    return {
        "crew_id": safe_id,
        "role_en": roster_match["role_en"],
        "role_zh": roster_match["role_zh"],
        "data_lifecycle_mode": mode,
        "onboarding_completed": False,
        "mission_day": default_day,
        "anchor_mission_day": default_day,
        "daily_vitals": default_daily_vitals(),
        "module_checkins": default_module_checkins(),
        "checkin_series": {},
        "updated_at": None,
    }


def list_crew_profiles() -> list[dict[str, Any]]:
    """Return available crew profiles (merging default roster + any custom files in `data/crew_records/`)."""
    ensure_crew_records_dir()
    seen: dict[str, dict[str, Any]] = {}

    for item in DEFAULT_CREW_ROSTER:
        cid = item["crew_id"]
        seen[cid] = {
            "crew_id": cid,
            "role_en": item["role_en"],
            "role_zh": item["role_zh"],
            "has_saved_file": _crew_file_path(cid).exists(),
        }

    for p in sorted(CREW_RECORDS_DIR.glob("*.json")):
        cid = sanitize_crew_id(p.stem)
        try:
            with p.open("r", encoding="utf-8") as fh:
                doc = json.load(fh)
            if isinstance(doc, dict):
                seen[cid] = {
                    "crew_id": cid,
                    "role_en": str(doc.get("role_en", "Mission Specialist")),
                    "role_zh": str(doc.get("role_zh", "任務專家")),
                    "has_saved_file": True,
                    "data_lifecycle_mode": str(doc.get("data_lifecycle_mode", "day1_standby")),
                    "mission_day": int(doc.get("mission_day", 1)),
                }
        except Exception:  # noqa: BLE001
            continue

    return list(seen.values())


def load_crew_record(
    crew_id: str = "C002",
    default_mode: str = "day1_standby",
) -> dict[str, Any]:
    """Load a crew member's record from `data/crew_records/<crew_id>.json`, creating a default in-memory if absent."""
    safe_id = sanitize_crew_id(crew_id)
    base_doc = build_default_crew_record(safe_id, data_lifecycle_mode=default_mode)
    fpath = _crew_file_path(safe_id)
    if not fpath.exists():
        return base_doc

    try:
        with fpath.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
        if not isinstance(raw, dict):
            return base_doc

        merged = dict(base_doc)
        merged.update(raw)
        merged["crew_id"] = safe_id
        mode = str(merged.get("data_lifecycle_mode", default_mode))
        if mode not in {"day1_standby", "day124_showcase"}:
            mode = default_mode
        merged["data_lifecycle_mode"] = mode
        merged["onboarding_completed"] = bool(merged.get("onboarding_completed", False))
        merged["mission_day"] = max(1, int(merged.get("mission_day", 1 if mode == "day1_standby" else 124)))
        merged["anchor_mission_day"] = max(1, int(merged.get("anchor_mission_day", merged["mission_day"])))

        dv = default_daily_vitals()
        if isinstance(raw.get("daily_vitals"), dict):
            dv.update(raw["daily_vitals"])
        merged["daily_vitals"] = dv

        mc = default_module_checkins()
        if isinstance(raw.get("module_checkins"), dict):
            for mod_id, vals in raw["module_checkins"].items():
                if mod_id in mc and isinstance(vals, dict):
                    mc[mod_id].update(vals)
        merged["module_checkins"] = mc

        if not isinstance(merged.get("checkin_series"), dict):
            merged["checkin_series"] = {}

        return merged
    except Exception:  # noqa: BLE001
        return base_doc


def save_crew_record(
    crew_id: str,
    data_lifecycle_mode: Optional[str] = None,
    onboarding_completed: Optional[bool] = None,
    mission_day: Optional[int] = None,
    anchor_mission_day: Optional[int] = None,
    daily_vitals: Optional[dict[str, Any]] = None,
    module_checkins: Optional[dict[str, dict[str, Any]]] = None,
    checkin_series: Optional[dict[str, Any]] = None,
    role_en: Optional[str] = None,
    role_zh: Optional[str] = None,
) -> dict[str, Any]:
    """Persist a crew member's longitudinal record to `data/crew_records/<crew_id>.json`."""
    safe_id = sanitize_crew_id(crew_id)
    existing = load_crew_record(safe_id)
    now_iso = datetime.now(timezone.utc).isoformat()

    if data_lifecycle_mode in {"day1_standby", "day124_showcase"}:
        existing["data_lifecycle_mode"] = data_lifecycle_mode
    if onboarding_completed is not None:
        existing["onboarding_completed"] = bool(onboarding_completed)
    if mission_day is not None:
        existing["mission_day"] = max(1, int(mission_day))
    if anchor_mission_day is not None:
        existing["anchor_mission_day"] = max(1, int(anchor_mission_day))
    if isinstance(daily_vitals, dict):
        existing["daily_vitals"] = dict(daily_vitals)
    if isinstance(module_checkins, dict):
        existing["module_checkins"] = dict(module_checkins)
    if isinstance(checkin_series, dict):
        existing["checkin_series"] = dict(checkin_series)
    if role_en:
        existing["role_en"] = str(role_en)
    if role_zh:
        existing["role_zh"] = str(role_zh)

    existing["updated_at"] = now_iso
    fpath = _crew_file_path(safe_id)
    with fpath.open("w", encoding="utf-8") as fh:
        json.dump(existing, fh, indent=2, ensure_ascii=False)
    return existing


def reset_crew_to_day1_standby(crew_id: str) -> dict[str, Any]:
    """Reset a crew member to Day-1 Cold-Start Standby mode (clearing logged check-ins)."""
    safe_id = sanitize_crew_id(crew_id)
    fresh = build_default_crew_record(safe_id, data_lifecycle_mode="day1_standby")
    fresh["updated_at"] = datetime.now(timezone.utc).isoformat()
    fpath = _crew_file_path(safe_id)
    with fpath.open("w", encoding="utf-8") as fh:
        json.dump(fresh, fh, indent=2, ensure_ascii=False)
    return fresh


def switch_crew_to_day124_showcase(crew_id: str) -> dict[str, Any]:
    """Switch a crew member to Day-124 Full Mission Dataset mode while preserving any custom profile info."""
    safe_id = sanitize_crew_id(crew_id)
    return save_crew_record(
        crew_id=safe_id,
        data_lifecycle_mode="day124_showcase",
        onboarding_completed=True,
        mission_day=124,
        anchor_mission_day=124,
    )
