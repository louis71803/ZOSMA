"""Fault-tolerant Pydantic v2 schemas and normalizers for Z.O.S.M.A.

Guarantees seamless integration between Role 1 (UI / Integrator) and Roles 2-6
(domain evaluators) regardless of minor casing, alias, or schema differences.
"""

from __future__ import annotations

from typing import Any, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, model_validator

StatusLight = Literal["GREEN", "YELLOW", "RED"]

_QC_BAD_TOKENS = {
    "INSUFFICIENT_DATA",
    "RESCAN_REQUIRED",
    "NO_DATA",
    "BAD_DATA",
    "QC_FAIL",
    "INVALID",
}


def normalize_status_value(
    raw_status: Any,
) -> tuple[StatusLight, bool, bool, str]:
    """Normalize arbitrary status strings into (status_light, watch_flag, quality_ok, raw_label).

    Rules:
    - Case-insensitive ("green" -> "GREEN").
    - "GREEN-WATCH" / "GREEN_WATCH" -> ("GREEN", watch_flag=True, quality_ok=True).
    - "INSUFFICIENT_DATA" / "RESCAN_REQUIRED" / "NO_DATA" -> ("YELLOW", watch_flag=False, quality_ok=False).
    - Unknown strings safely default to ("YELLOW", False, True).
    """
    if raw_status is None:
        return "YELLOW", False, False, "INSUFFICIENT_DATA"

    token = str(raw_status).strip().upper().replace(" ", "_")
    if token in {"GREEN-WATCH", "GREEN_WATCH", "WATCH"}:
        return "GREEN", True, True, token
    if token in _QC_BAD_TOKENS:
        return "YELLOW", False, False, token
    if token in {"GREEN", "OK", "OPTIMAL", "NORMAL", "PASS"}:
        return "GREEN", False, True, token
    if token in {"YELLOW", "WARN", "WARNING", "AMBER", "CAUTION"}:
        return "YELLOW", False, True, token
    if token in {"RED", "CRITICAL", "ALERT", "EMERGENCY", "DANGER"}:
        return "RED", False, True, token
    return "YELLOW", False, True, token


class MetricItem(BaseModel):
    """Normalized single physiological or environmental indicator."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    metric_name: str = Field(..., description="Canonical metric name.")
    current_val: Optional[Union[float, int, str, bool]] = Field(
        default=None, description="Latest measured value."
    )
    baseline_val: Optional[Union[float, int, str, bool]] = Field(
        default=None, description="Pre-flight or module baseline value."
    )
    delta_pct: Optional[float] = Field(
        default=None, description="Percentage change from baseline."
    )
    slope_per_day: Optional[float] = Field(
        default=None, description="Linear rate of change per mission day."
    )
    unit: str = Field(default="", description="Measurement unit.")
    status_light: StatusLight = Field(default="GREEN")
    watch_flag: bool = Field(
        default=False, description="True when raw status was GREEN-WATCH."
    )
    raw_status: str = Field(
        default="GREEN", description="Original unnormalized status token."
    )
    quality_passed: bool = Field(default=True)
    decided_by: str = Field(
        default="fixed_threshold",
        description="Layer that decided status: quality_check | fixed_threshold | rule | baseline | trend | spe_rule | fast_track.",
    )
    data_source: str = Field(default="SIMULATED")
    message: str = Field(default="")
    action: str = Field(default="")

    # Optional thresholds for plotting trend bands
    yellow_threshold: Optional[float] = Field(default=None)
    red_threshold: Optional[float] = Field(default=None)
    lower_is_worse: bool = Field(default=False)
    history_days: list[int] = Field(default_factory=list)
    history_values: list[float] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_aliases(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out = dict(data)

        if "metric_name" not in out or out["metric_name"] is None:
            out["metric_name"] = out.get("indicator") or out.get("name") or "unknown_metric"
        if "current_val" not in out and "value" in out:
            out["current_val"] = out["value"]

        raw_status = out.get("status_light", out.get("status", "GREEN"))
        norm_status, watch_flag, qc_ok, raw_label = normalize_status_value(raw_status)
        out["status_light"] = norm_status
        out["watch_flag"] = bool(out.get("watch_flag", False) or watch_flag)
        out["raw_status"] = str(out.get("raw_status") or raw_label)
        if "quality_passed" in out:
            out["quality_passed"] = bool(out["quality_passed"]) and qc_ok
        else:
            out["quality_passed"] = qc_ok

        if out.get("data_source"):
            out["data_source"] = str(out["data_source"]).upper()
        if out.get("unit") is None:
            out["unit"] = ""
        if out.get("message") is None:
            out["message"] = ""
        if out.get("action") is None:
            out["action"] = ""
        return out


class CrewGuidance(BaseModel):
    """3-Step Non-Medical Crew Guide required by SOUL.md and AGENTS.md."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    how_to_measure: str = Field(
        default="Follow standard device checklist and confirm sensor contact/calibration."
    )
    plain_explanation: str = Field(
        default="Monitors mission-critical physiological adaptation in deep space."
    )
    action_protocol: list[str] = Field(
        default_factory=lambda: ["Continue nominal scheduled monitoring."]
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_aliases(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        if "how_to_measure" not in out and "measurement_guide" in out:
            out["how_to_measure"] = out["measurement_guide"]
        if "action_protocol" not in out and "actionable_protocol" in out:
            out["action_protocol"] = out["actionable_protocol"]

        actions = out.get("action_protocol")
        if isinstance(actions, str):
            out["action_protocol"] = [line.strip() for line in actions.splitlines() if line.strip()]
        elif actions is None:
            out["action_protocol"] = ["Continue nominal scheduled monitoring."]
        return out


class ShortTermPlan(BaseModel):
    """0-48 Hours Immediate Triage Plan."""

    model_config = ConfigDict(extra="allow")

    next_measurement_in_hours: int = Field(default=24, ge=0)
    immediate_actions: list[str] = Field(default_factory=list)
    urgent_alert: bool = Field(default=False)

    @model_validator(mode="before")
    @classmethod
    def _coerce_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        actions = out.get("immediate_actions")
        if isinstance(actions, str):
            out["immediate_actions"] = [actions]
        elif actions is None:
            out["immediate_actions"] = []
        if out.get("next_measurement_in_hours") is None:
            out["next_measurement_in_hours"] = 24
        return out


class LongTermPlan(BaseModel):
    """7-30 Days Regimen & Trend Forecast Plan."""

    model_config = ConfigDict(extra="allow")

    days_until_red_prediction: Optional[int] = Field(default=None, ge=0)
    routine_prescription_adjustment: Union[str, list[str]] = Field(
        default="Maintain baseline deep-space countermeasure protocol."
    )

    @property
    def adjustment_list(self) -> list[str]:
        if isinstance(self.routine_prescription_adjustment, list):
            return [str(x) for x in self.routine_prescription_adjustment if str(x).strip()]
        text = str(self.routine_prescription_adjustment or "").strip()
        return [text] if text else []


class ScheduleMutation(BaseModel):
    """Legacy schedule override compatibility object."""

    model_config = ConfigDict(extra="allow")

    next_measurement_in_hours: int = Field(default=24, ge=0)
    prescription_adjustment: str = Field(default="Maintain baseline schedule.")
    urgent_alert: bool = Field(default=False)


class ModuleEvaluationResult(BaseModel):
    """Standardized output contract for all 5 Z.O.S.M.A. domain modules."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    module_id: str
    body_part_tag: Union[str, list[str]] = Field(default="whole_body")
    crew_id: str = Field(default="C002")
    mission_day: int = Field(default=124)
    status_light: StatusLight = Field(default="GREEN")
    watch_flag: bool = Field(
        default=False, description="True when module status was GREEN-WATCH."
    )
    raw_status: str = Field(default="GREEN")
    quality_passed: bool = Field(default=True)
    data_source: str = Field(default="SIMULATED")
    metrics: list[MetricItem] = Field(default_factory=list)
    guidance: CrewGuidance = Field(default_factory=CrewGuidance)
    short_term_plan: ShortTermPlan = Field(default_factory=ShortTermPlan)
    long_term_plan: LongTermPlan = Field(default_factory=LongTermPlan)
    schedule_mutation: Optional[ScheduleMutation] = Field(default=None)
    summary_note: str = Field(default="")
    trend_series: dict[str, Any] = Field(default_factory=dict)

    @property
    def overall_status(self) -> StatusLight:
        return self.status_light

    @property
    def indicators(self) -> list[MetricItem]:
        return self.metrics

    @property
    def body_part_tags(self) -> list[str]:
        if isinstance(self.body_part_tag, list):
            return [str(x) for x in self.body_part_tag]
        return [str(self.body_part_tag)]

    @model_validator(mode="before")
    @classmethod
    def _normalize_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out = dict(data)

        # Normalize status_light / overall_status
        raw_status = out.get("status_light", out.get("overall_status", "GREEN"))
        norm_status, watch_flag, qc_ok, raw_label = normalize_status_value(raw_status)
        out["status_light"] = norm_status
        out["watch_flag"] = bool(out.get("watch_flag", False) or watch_flag)
        out["raw_status"] = str(out.get("raw_status") or raw_label)

        if "quality_passed" in out:
            out["quality_passed"] = bool(out["quality_passed"]) and qc_ok
        else:
            out["quality_passed"] = qc_ok

        # Support both metrics and indicators
        raw_metrics = out.get("metrics")
        if raw_metrics is None and "indicators" in out:
            raw_metrics = out["indicators"]
        if raw_metrics is None:
            raw_metrics = []
        out["metrics"] = raw_metrics

        # Normalize body_part_tag (str or list[str])
        tag = out.get("body_part_tag", "whole_body")
        if isinstance(tag, list):
            out["body_part_tag"] = [str(item) for item in tag]
        elif tag is None:
            out["body_part_tag"] = "whole_body"
        else:
            out["body_part_tag"] = str(tag)

        # Normalize data_source
        if out.get("data_source"):
            out["data_source"] = str(out["data_source"]).upper()
        elif isinstance(raw_metrics, list) and raw_metrics:
            sources = {
                str(m.get("data_source", "SIMULATED")).upper()
                for m in raw_metrics
                if isinstance(m, dict)
            }
            out["data_source"] = "REAL" if "REAL" in sources else "SIMULATED"

        # Synthesize schedule_mutation if omitted
        if out.get("schedule_mutation") is None:
            stp = out.get("short_term_plan") or {}
            ltp = out.get("long_term_plan") or {}
            if isinstance(stp, ShortTermPlan):
                stp_hours = stp.next_measurement_in_hours
                stp_urgent = stp.urgent_alert
            else:
                stp_hours = stp.get("next_measurement_in_hours", 24) if isinstance(stp, dict) else 24
                stp_urgent = stp.get("urgent_alert", False) if isinstance(stp, dict) else False

            if isinstance(ltp, LongTermPlan):
                adj = "; ".join(ltp.adjustment_list)
            elif isinstance(ltp, dict):
                raw_adj = ltp.get("routine_prescription_adjustment", "Maintain baseline schedule.")
                adj = "; ".join(raw_adj) if isinstance(raw_adj, list) else str(raw_adj)
            else:
                adj = "Maintain baseline schedule."

            out["schedule_mutation"] = {
                "next_measurement_in_hours": stp_hours if stp_hours is not None else 24,
                "prescription_adjustment": adj,
                "urgent_alert": bool(stp_urgent),
            }

        return out


def normalize_module_result(
    raw: Union[ModuleEvaluationResult, dict[str, Any]],
    module_id: Optional[str] = None,
) -> ModuleEvaluationResult:
    """Coerce a raw module output dict or model into a validated ModuleEvaluationResult."""
    if isinstance(raw, ModuleEvaluationResult):
        return raw
    if hasattr(raw, "to_schema") and callable(raw.to_schema):
        raw = raw.to_schema()
    if hasattr(raw, "model_dump") and callable(raw.model_dump):
        raw = raw.model_dump()
    if not isinstance(raw, dict):
        raise TypeError(f"Unsupported module evaluation result type: {type(raw)!r}")

    payload = dict(raw)
    if module_id and not payload.get("module_id"):
        payload["module_id"] = module_id
    return ModuleEvaluationResult.model_validate(payload)
