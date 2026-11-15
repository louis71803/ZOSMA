"""Frontend Check-In & Developer Reference Schema Generator (`ui/checkin_spec.py`).

Serializes `core/checkin_tracker.py` field definitions, symptom chips, and
Green/Yellow/Red reference bands into a single JS constant block so UI forms
and backend evaluation stay 100% synchronized.
"""

from __future__ import annotations

import json

from core.checkin_tracker import build_frontend_checkin_spec


def build_checkin_spec_js() -> str:
    """Return JS constant declarations for Daily Check-In and Dev Overrides."""
    spec_json = json.dumps(build_frontend_checkin_spec(), ensure_ascii=False)
    return f"  const CHECKIN_SPEC = {spec_json};\n"
