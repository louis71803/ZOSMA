"""Z.O.S.M.A. — Deep-Space Astronaut Health Monitoring System (Mission Control UI).

Role 1 (Lead System Integrator & UI Architect) owns this file.
Layout:
1. Top: Telemetry & 5-Module Manual Input Drawer ("Save & Run All 5 Agents")
2. Left: Interactive 2D Human Body & Cabin Traffic-Light Status Map
3. Center: 3-Step Non-Medical Crew Guidance Cards + 3-Layer Plotly Trend Chart
4. Right: Closed-Loop Short-Term (0-48h) & Long-Term (7-30d) Planning Board

Includes responsive CSS media queries (auto-adapting to window width / DPI scaling)
and distinct bordered Mission Control panels with generous spacing.
"""

from __future__ import annotations

import importlib
from typing import Any

import plotly.graph_objects as go
import streamlit as st

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

st.set_page_config(
    page_title="Z.O.S.M.A. Deep-Space Medical Mission Control",
    page_icon="🧑‍🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

STATUS_COLORS = {
    "GREEN": "#16a34a",
    "YELLOW": "#eab308",
    "RED": "#dc2626",
}

STATUS_EMOJI = {
    "GREEN": "🟢",
    "YELLOW": "🟡",
    "RED": "🔴",
}

MODULE_SHORT_NAMES: dict[str, str] = {
    "cabin_environment": "Cabin & Rad",
    "cardiovascular": "Cardiovascular",
    "musculoskeletal": "Musculoskeletal",
    "neuro_ocular": "Neuro-Ocular",
    "immune_metabolic": "Immune & Renal",
}


def _inject_responsive_css() -> None:
    """Inject responsive CSS for clean panel separation, card spacing, and viewport adaptation."""
    st.markdown(
        """
        <style>
        /* Main container breathing room */
        .block-container {
            padding-top: 1.6rem !important;
            padding-bottom: 2.5rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 100% !important;
        }

        /* Add clear horizontal & vertical gaps between Streamlit columns and allow responsive wrapping */
        div[data-testid="stHorizontalBlock"] {
            gap: 1.35rem !important;
            flex-wrap: wrap !important;
            align-items: stretch;
        }

        /* Prevent columns from getting squished too narrow on medium/laptop screens */
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            min-width: 280px !important;
            flex: 1 1 280px;
        }

        /* Distinct card styling for bordered containers */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 14px !important;
            border: 1px solid rgba(148, 163, 184, 0.28) !important;
            background: rgba(15, 23, 42, 0.35);
            padding: 0.35rem !important;
            margin-bottom: 0.85rem !important;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.16);
        }

        /* Metric KPI cards separation */
        div[data-testid="stMetric"] {
            background: rgba(30, 41, 59, 0.55);
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 12px;
            padding: 0.9rem 1.1rem !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
        }
        div[data-testid="stMetricLabel"] p {
            white-space: normal !important;
            line-height: 1.3 !important;
        }

        /* Tabs spacing so tab titles never crowd together */
        button[data-baseweb="tab"] {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            padding-top: 0.55rem !important;
            padding-bottom: 0.55rem !important;
            margin-right: 0.35rem !important;
        }

        /* Widget vertical spacing inside forms/drawers */
        div[data-testid="stSlider"],
        div[data-testid="stNumberInput"],
        div[data-testid="stSelectbox"],
        div[data-testid="stTextInput"],
        div[data-testid="stCheckbox"] {
            margin-bottom: 0.55rem !important;
        }

        /* Subsystem selector buttons */
        div.stButton > button {
            border-radius: 10px !important;
            padding: 0.52rem 0.85rem !important;
            margin-bottom: 0.25rem !important;
            text-align: left !important;
        }

        /* Responsive breakpoints for medium/smaller browser windows or 150% DPI laptops */
        @media (max-width: 1360px) {
            .block-container {
                padding-left: 1.2rem !important;
                padding-right: 1.2rem !important;
            }
            div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
            div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                min-width: 340px !important;
            }
        }

        @media (max-width: 960px) {
            div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
            div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                min-width: 100% !important;
                flex: 1 1 100% !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _status_badge_text(res: ModuleEvaluationResult) -> str:
    emoji = STATUS_EMOJI.get(res.status_light, "🟡")
    if not res.quality_passed:
        return f"⚠️ {res.raw_status} (QC FAIL)"
    if res.watch_flag:
        return f"{emoji} GREEN-WATCH"
    return f"{emoji} {res.status_light}"


def _build_body_cabin_map(
    results: dict[str, ModuleEvaluationResult],
    selected_module: str,
) -> go.Figure:
    """Interactive 2D Human Body Silhouette & Cabin Environment Traffic-Light Map."""
    fig = go.Figure()

    # Cabin habitat frame around the astronaut silhouette
    cabin_res = results.get("cabin_environment")
    cabin_color = STATUS_COLORS.get(cabin_res.status_light if cabin_res else "GREEN", "#16a34a")
    fig.add_shape(
        type="rect",
        x0=-1.55,
        y0=-0.20,
        x1=1.55,
        y1=2.48,
        line=dict(color=cabin_color, width=3, dash="dot"),
        fillcolor="rgba(30, 41, 59, 0.25)",
    )

    # Stylized 2D astronaut body silhouette (shifted slightly left so right-side labels never crowd)
    bx = -0.22
    # Head
    fig.add_shape(
        type="circle",
        x0=bx - 0.22,
        y0=1.74,
        x1=bx + 0.22,
        y1=2.16,
        line=dict(color="#94a3b8", width=2),
        fillcolor="rgba(148,163,184,0.18)",
    )
    # Torso
    fig.add_shape(
        type="rect",
        x0=bx - 0.33,
        y0=0.92,
        x1=bx + 0.33,
        y1=1.70,
        line=dict(color="#94a3b8", width=2),
        fillcolor="rgba(148,163,184,0.15)",
    )
    # Left & Right Arms
    fig.add_shape(
        type="rect",
        x0=bx - 0.56,
        y0=1.02,
        x1=bx - 0.35,
        y1=1.65,
        line=dict(color="#94a3b8", width=1.5),
        fillcolor="rgba(148,163,184,0.12)",
    )
    fig.add_shape(
        type="rect",
        x0=bx + 0.35,
        y0=1.02,
        x1=bx + 0.56,
        y1=1.65,
        line=dict(color="#94a3b8", width=1.5),
        fillcolor="rgba(148,163,184,0.12)",
    )
    # Left & Right Legs
    fig.add_shape(
        type="rect",
        x0=bx - 0.29,
        y0=0.08,
        x1=bx - 0.05,
        y1=0.90,
        line=dict(color="#94a3b8", width=2),
        fillcolor="rgba(148,163,184,0.15)",
    )
    fig.add_shape(
        type="rect",
        x0=bx + 0.05,
        y0=0.08,
        x1=bx + 0.29,
        y1=0.90,
        line=dict(color="#94a3b8", width=2),
        fillcolor="rgba(148,163,184,0.15)",
    )

    # Well-separated node coordinates & text positions so labels never overlap
    nodes = [
        ("cabin_environment", "Cabin & Rad", -1.05, 2.22, "middle right"),
        ("neuro_ocular", "Neuro-Ocular", bx + 0.02, 1.95, "middle right"),
        ("cardiovascular", "Cardiovascular", bx + 0.02, 1.46, "middle right"),
        ("immune_metabolic", "Immune & Renal", bx + 0.02, 1.06, "middle right"),
        ("musculoskeletal", "Musculoskeletal", bx + 0.02, 0.48, "middle right"),
    ]

    xs, ys, colors, sizes, texts, text_pos, hovers, line_widths = [], [], [], [], [], [], [], []
    for mod_id, label, x, y, pos in nodes:
        res = results.get(mod_id)
        st_light = res.status_light if res else "GREEN"
        color = STATUS_COLORS.get(st_light, "#16a34a")
        if res and not res.quality_passed:
            color = "#f97316"
        xs.append(x)
        ys.append(y)
        colors.append(color)
        is_sel = mod_id == selected_module
        sizes.append(26 if is_sel else 20)
        line_widths.append(4 if is_sel else 1.5)
        badge = _status_badge_text(res) if res else st_light
        texts.append(f"  <b>{label}</b>")
        text_pos.append(pos)
        hovers.append(
            f"<b>{MODULE_DISPLAY_NAMES.get(mod_id, label)}</b><br>Status: {badge}<br>"
            f"Source: {res.data_source if res else 'SIMULATED'}<br>"
            f"{res.summary_note if res else ''}"
        )

    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="markers+text",
            text=texts,
            textposition=text_pos,
            textfont=dict(size=12, color="#f1f5f9"),
            hovertext=hovers,
            hoverinfo="text",
            cliponaxis=False,
            marker=dict(
                size=sizes,
                color=colors,
                line=dict(color="#ffffff", width=line_widths),
            ),
            showlegend=False,
        )
    )

    fig.update_layout(
        autosize=True,
        height=410,
        margin=dict(l=14, r=14, t=36, b=14),
        paper_bgcolor="rgba(15, 23, 42, 0.9)",
        plot_bgcolor="rgba(15, 23, 42, 0.9)",
        xaxis=dict(range=[-1.68, 1.68], visible=False, fixedrange=True),
        yaxis=dict(range=[-0.28, 2.58], visible=False, fixedrange=True),
        title=dict(text="2D Crew & Habitat Traffic-Light Map", font=dict(size=14, color="#f8fafc")),
    )
    return fig


def _build_trend_chart(res: ModuleEvaluationResult) -> go.Figure:
    """Build 3-Layer Plotly Longitudinal Trend Chart with Green/Yellow/Red zones."""
    target_metric = None
    for m in res.metrics:
        if m.history_days and m.history_values:
            target_metric = m
            break
    if target_metric is None and res.metrics:
        target_metric = res.metrics[0]

    fig = go.Figure()
    if target_metric is None:
        fig.update_layout(height=300, title="No metric telemetry available")
        return fig

    days = target_metric.history_days or [0, 30, 60, 90, res.mission_day]
    if target_metric.history_values:
        vals = target_metric.history_values
    else:
        try:
            cur = float(target_metric.current_val)
        except (TypeError, ValueError):
            cur = 0.0
        try:
            base = float(target_metric.baseline_val)
        except (TypeError, ValueError):
            base = cur
        step = (cur - base) / 4.0
        vals = [round(base + step * i, 3) for i in range(5)]

    y_thresh = target_metric.yellow_threshold
    r_thresh = target_metric.red_threshold
    lower_worse = target_metric.lower_is_worse

    all_nums = list(vals)
    if y_thresh is not None:
        all_nums.append(y_thresh)
    if r_thresh is not None:
        all_nums.append(r_thresh)

    y_min = min(all_nums) * 0.9 if min(all_nums) >= 0 else min(all_nums) * 1.1
    y_max = max(all_nums) * 1.1 if max(all_nums) >= 0 else max(all_nums) * 0.9
    if y_min == y_max:
        y_min -= 1.0
        y_max += 1.0

    # Green / Yellow / Red horizontal threshold bands
    if y_thresh is not None and r_thresh is not None:
        if lower_worse:
            fig.add_hrect(y0=y_thresh, y1=y_max, fillcolor="rgba(22,163,74,0.12)", line_width=0)
            fig.add_hrect(y0=r_thresh, y1=y_thresh, fillcolor="rgba(234,179,8,0.15)", line_width=0)
            fig.add_hrect(y0=y_min, y1=r_thresh, fillcolor="rgba(220,38,38,0.16)", line_width=0)
        else:
            fig.add_hrect(y0=y_min, y1=y_thresh, fillcolor="rgba(22,163,74,0.12)", line_width=0)
            fig.add_hrect(y0=y_thresh, y1=r_thresh, fillcolor="rgba(234,179,8,0.15)", line_width=0)
            fig.add_hrect(y0=r_thresh, y1=y_max, fillcolor="rgba(220,38,38,0.16)", line_width=0)

        fig.add_hline(y=y_thresh, line_dash="dash", line_color="#eab308", annotation_text="Yellow")
        fig.add_hline(y=r_thresh, line_dash="dash", line_color="#dc2626", annotation_text="Red")

    # Measured trajectory
    fig.add_trace(
        go.Scatter(
            x=days,
            y=vals,
            mode="lines+markers",
            name="Measured",
            line=dict(color="#38bdf8", width=3),
            marker=dict(size=8, color=STATUS_COLORS.get(target_metric.status_light, "#38bdf8")),
        )
    )

    # Linear 30-day trend projection
    if len(days) >= 2 and days[-1] > days[0]:
        slope = (vals[-1] - vals[0]) / (days[-1] - days[0])
        proj_days = [days[-1], days[-1] + 15, days[-1] + 30]
        proj_vals = [round(vals[-1] + slope * (d - days[-1]), 3) for d in proj_days]
        fig.add_trace(
            go.Scatter(
                x=proj_days,
                y=proj_vals,
                mode="lines",
                name="30d Projection",
                line=dict(color="#f472b6", width=2, dash="dot"),
            )
        )

    fig.update_layout(
        autosize=True,
        height=320,
        margin=dict(l=20, r=20, t=58, b=24),
        paper_bgcolor="rgba(15, 23, 42, 0.9)",
        plot_bgcolor="rgba(15, 23, 42, 0.9)",
        font=dict(color="#e2e8f0"),
        title=dict(
            text=f"3-Layer Trend: {target_metric.metric_name} ({target_metric.unit})",
            font=dict(size=14),
        ),
        xaxis=dict(title="Mission Day", automargin=True),
        yaxis=dict(title=target_metric.unit or "Value", range=[y_min, y_max], automargin=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def _render_left_panel(results: dict[str, ModuleEvaluationResult]) -> None:
    """Render Left Interactive Body & Cabin Status Panel inside its own bordered card."""
    with st.container(border=True):
        st.subheader("🫀 Crew & Cabin Status Map")
        selected = st.selectbox(
            "Inspect Subsystem",
            options=list(MODULE_ORDER),
            index=list(MODULE_ORDER).index(st.session_state["selected_module"]),
            format_func=lambda m: f"{STATUS_EMOJI.get(results[m].status_light, '🟡')} {MODULE_DISPLAY_NAMES[m]}",
        )
        st.session_state["selected_module"] = selected

        st.plotly_chart(_build_body_cabin_map(results, selected), width="stretch")

        st.markdown("##### Quick Subsystem Traffic Lights")
        for mod_id in MODULE_ORDER:
            res = results[mod_id]
            badge = _status_badge_text(res)
            src_tag = "REAL" if res.data_source == "REAL" else "DEMO"
            short_title = MODULE_SHORT_NAMES.get(mod_id, mod_id)
            if st.button(
                f"{badge} · {short_title} [{src_tag}]",
                key=f"sel_btn_{mod_id}",
                width="stretch",
            ):
                st.session_state["selected_module"] = mod_id
                st.rerun()


def _render_center_panel(results: dict[str, ModuleEvaluationResult]) -> None:
    """Render Center Trend Chart & 3-Step Non-Medical Crew Guidance Panel."""
    sel_id = st.session_state["selected_module"]
    sel_res = results[sel_id]
    with st.container(border=True):
        st.subheader(f"🔬 {MODULE_DISPLAY_NAMES[sel_id]}")
        st.caption(
            f"Status: **{_status_badge_text(sel_res)}**  |  Source: `{sel_res.data_source}`  |  "
            f"Crew: `{sel_res.crew_id}`  |  Day: `{sel_res.mission_day}`"
        )
        if sel_res.summary_note:
            st.info(sel_res.summary_note)

        # 3-Layer Plotly Trend Chart
        st.plotly_chart(_build_trend_chart(sel_res), width="stretch")

        # 3-Step Non-Medical Crew Guidance Cards (stacked cleanly so text never squishes)
        st.markdown("##### 🧑‍🚀 3-Step Non-Medical Crew Guidance")
        with st.container(border=True):
            st.markdown("**1. How to Measure (`how_to_measure`)**")
            st.write(sel_res.guidance.how_to_measure)

        with st.container(border=True):
            st.markdown("**2. What It Means (`plain_explanation`)**")
            st.write(sel_res.guidance.plain_explanation)

        with st.container(border=True):
            st.markdown("**3. What to Do (`action_protocol`)**")
            for idx, step_txt in enumerate(sel_res.guidance.action_protocol, start=1):
                st.markdown(f"{idx}. {step_txt}")

        with st.expander("📊 Detailed Indicator Breakdown", expanded=False):
            rows = [
                {
                    "Metric": m.metric_name,
                    "Current": m.current_val,
                    "Baseline": m.baseline_val,
                    "Unit": m.unit,
                    "Status": m.raw_status if m.watch_flag or not m.quality_passed else m.status_light,
                    "Layer": m.decided_by,
                    "Action": m.action,
                }
                for m in sel_res.metrics
            ]
            st.dataframe(rows, width="stretch", hide_index=True)


def _render_right_panel(schedule: dict[str, Any], cross_context: dict[str, Any]) -> None:
    """Render Right Closed-Loop Planning Board inside its own bordered card."""
    with st.container(border=True):
        st.subheader("📋 Closed-Loop Planning Board")

        if cross_context.get("propagated_flags"):
            with st.container(border=True):
                st.markdown("**🔗 Cross-Module Context Signals**")
                for sig in cross_context["propagated_flags"]:
                    st.caption(f"• {sig}")

        if schedule["conflicts_resolved"]:
            for conflict in schedule["conflicts_resolved"]:
                st.error(f"**{conflict['rule']}**\n\n{conflict['resolution']}")

        tab_short, tab_long = st.tabs(
            ["🚨 Short-Term (0–48h)", "📅 Long-Term (7–30d)"]
        )

        with tab_short:
            for item in schedule["short_term_board"]:
                emoji = STATUS_EMOJI.get(item["status_light"], "🟡")
                urgent_txt = " · **URGENT CMO**" if item["urgent_alert"] else ""
                with st.container(border=True):
                    st.markdown(
                        f"{emoji} **`{item['module_id']}`** · Next: **{item['next_hours']}h**{urgent_txt}"
                    )
                    st.write(item["action"])

        with tab_long:
            for item in schedule["long_term_board"]:
                emoji = STATUS_EMOJI.get(item["status_light"], "🟡")
                red_txt = (
                    f"Projected RED in **{item['days_until_red']}d**"
                    if item["days_until_red"] is not None
                    else "No RED projected"
                )
                with st.container(border=True):
                    st.markdown(f"{emoji} **`{item['module_id']}`** · {red_txt}")
                    st.write(item["adjustment"])


def main() -> None:
    _inject_responsive_css()
    session_state = load_runtime_session()

    if "selected_module" not in st.session_state:
        st.session_state["selected_module"] = "neuro_ocular"

    # Header bar + Layout Viewport Mode Selector
    hdr_left, hdr_right = st.columns([3.2, 1.2], gap="large")
    with hdr_left:
        st.title("🧑‍🚀 Z.O.S.M.A. — Deep-Space Autonomous Medical Mission Control")
        st.caption(
            "Zero-Conflict 5-Module Flight Surgeon Intelligence | Layer 0 QC + 3-Layer Decision Engine | 100% Offline-Ready"
        )
    with hdr_right:
        layout_mode = st.selectbox(
            "🖥️ Viewport Layout Mode",
            options=[
                "Auto 3-Column (Wide / Responsive)",
                "2-Column Split + Bottom Schedule (Laptop)",
                "Single-Column Stacked (Compact / Split-Screen)",
            ],
            index=0,
            help="Automatically wraps on narrow screens via CSS, or manually switch layout density here.",
        )

    # Non-intrusive data source status strip
    data_statuses = inspect_all_data_status()
    status_chips = []
    for mod_id in MODULE_ORDER:
        info = data_statuses[mod_id]
        tag = "REAL CSV" if info["has_real_files"] else "DEMO FALLBACK"
        status_chips.append(f"**{MODULE_SHORT_NAMES[mod_id]}**: `{tag}`")
    with st.expander("📡 Data Folder & CSV Status (`data/<module_id>/`)", expanded=False):
        st.markdown("  ·  ".join(status_chips))
        if st.button("Generate Starter Demo CSV Templates in data/", key="export_csvs_btn"):
            generated = []
            for mod_id in MODULE_ORDER:
                mod = importlib.import_module(f"modules.{mod_id}")
                if hasattr(mod, "export_demo_csvs"):
                    generated.extend(mod.export_demo_csvs())
            st.success(f"Generated {len(generated)} starter files across data/ subdirectories.")
            st.rerun()

    # =========================================================================
    # SECTION 1 (TOP): Telemetry & 5-Module Manual Input Drawer (Spaced 2-Col Grids)
    # =========================================================================
    with st.expander("🎛️ Top Telemetry & Manual Input Drawer (All 5 Modules)", expanded=False):
        meta_c1, meta_c2, meta_c3 = st.columns([1.1, 1.3, 1.6], gap="large")
        with meta_c1:
            crew_id = st.text_input("Crew ID", value=str(session_state.get("crew_id", "C002")))
            mission_day = int(
                st.number_input("Mission Day", min_value=1, max_value=1200, value=int(session_state.get("mission_day", 124)))
            )
        with meta_c2:
            scenario = st.selectbox(
                "Simulation Scenario Preset",
                options=["green", "yellow", "red", "bad_data"],
                index=["green", "yellow", "red", "bad_data"].index(
                    session_state.get("scenario", "green")
                    if session_state.get("scenario") in {"green", "yellow", "red", "bad_data"}
                    else "green"
                ),
            )
        with meta_c3:
            st.markdown("**Telemetry Input Routing**")
            prefer_real_csv = st.checkbox("Prefer Real CSVs in data/", value=True)
            use_manual_overrides = st.checkbox("Apply Manual Slider Overrides below", value=False)

        st.write("")
        tabs = st.tabs([MODULE_SHORT_NAMES[m] for m in MODULE_ORDER])
        saved_ov = session_state.get("manual_overrides", {})
        manual_inputs: dict[str, dict[str, Any]] = {m: {} for m in MODULE_ORDER}

        # Use clean 2-column grids with large gaps so sliders & labels never collide
        # Tab 0: cabin_environment
        with tabs[0]:
            c1, c2 = st.columns(2, gap="large")
            ov = saved_ov.get("cabin_environment", {})
            with c1:
                manual_inputs["cabin_environment"]["ppco2_1h_mmHg"] = st.slider(
                    "ppCO2 1h (mmHg)", 0.5, 5.0, float(ov.get("ppco2_1h_mmHg", 1.85)), 0.05
                )
                manual_inputs["cabin_environment"]["crew_leq8_dBA"] = st.slider(
                    "Crew 8h Noise (dBA)", 50.0, 95.0, float(ov.get("crew_leq8_dBA", 63.0)), 0.5
                )
            with c2:
                manual_inputs["cabin_environment"]["proton_flux_10mev_pfu"] = st.number_input(
                    "GOES >=10MeV Flux (pfu)", 0.0, 500.0, float(ov.get("proton_flux_10mev_pfu", 1.8)), 1.0
                )
                manual_inputs["cabin_environment"]["sleep_tst_h"] = st.slider(
                    "Actiwatch Sleep (h)", 3.0, 10.0, float(ov.get("sleep_tst_h", 7.1)), 0.1
                )
                manual_inputs["cabin_environment"]["spe_alert"] = st.checkbox(
                    "SPE Radiation Storm Alert", value=bool(ov.get("spe_alert", False))
                )

        # Tab 1: cardiovascular
        with tabs[1]:
            c1, c2 = st.columns(2, gap="large")
            ov = saved_ov.get("cardiovascular", {})
            with c1:
                manual_inputs["cardiovascular"]["rest_hr_bpm"] = st.slider(
                    "Resting HR (bpm)", 40.0, 130.0, float(ov.get("rest_hr_bpm", 64.0)), 1.0
                )
                manual_inputs["cardiovascular"]["spo2_pct"] = st.slider(
                    "SpO2 (%)", 85.0, 100.0, float(ov.get("spo2_pct", 98.2)), 0.1
                )
            with c2:
                manual_inputs["cardiovascular"]["pvc_burden_pct"] = st.slider(
                    "Holter PVC Burden (%)", 0.0, 15.0, float(ov.get("pvc_burden_pct", 0.3)), 0.1
                )
                ijv_opts = ["forward", "stagnant", "reversed"]
                cur_ijv = str(ov.get("ijv_flow", "forward"))
                manual_inputs["cardiovascular"]["ijv_flow"] = st.selectbox(
                    "IJV Doppler Flow", ijv_opts, index=ijv_opts.index(cur_ijv) if cur_ijv in ijv_opts else 0
                )
                manual_inputs["cardiovascular"]["ijv_thrombus"] = st.checkbox(
                    "IJV Thrombus Detected", value=bool(ov.get("ijv_thrombus", False))
                )

        # Tab 2: musculoskeletal
        with tabs[2]:
            c1, c2 = st.columns(2, gap="large")
            ov = saved_ov.get("musculoskeletal", {})
            with c1:
                manual_inputs["musculoskeletal"]["csa_thigh_cm2"] = st.slider(
                    "Thigh CSA (cm^2)", 115.0, 165.0, float(ov.get("csa_thigh_cm2", 146.2)), 0.5
                )
                manual_inputs["musculoskeletal"]["velocity_loss_pct"] = st.slider(
                    "VBT Velocity Loss (%)", 0.0, 45.0, float(ov.get("velocity_loss_pct", 12.5)), 0.5
                )
            with c2:
                manual_inputs["musculoskeletal"]["ctx"] = st.slider(
                    "Bone Resorption CTX (ng/mL)", 0.20, 0.80, float(ov.get("ctx", 0.39)), 0.01
                )
                manual_inputs["musculoskeletal"]["body_mass_kg"] = st.slider(
                    "Body Mass (kg)", 55.0, 90.0, float(ov.get("body_mass_kg", 73.1)), 0.2
                )

        # Tab 3: neuro_ocular
        with tabs[3]:
            c1, c2 = st.columns(2, gap="large")
            ov = saved_ov.get("neuro_ocular", {})
            with c1:
                manual_inputs["neuro_ocular"]["delta_trt_um"] = st.slider(
                    "Delta TRT (um)", -10.0, 90.0, float(ov.get("delta_trt_um", 9.0)), 1.0
                )
                manual_inputs["neuro_ocular"]["delta_v_onh_mm3"] = st.slider(
                    "Delta V_ONH (mm^3)", 0.0, 0.50, float(ov.get("delta_v_onh_mm3", 0.06)), 0.01
                )
            with c2:
                manual_inputs["neuro_ocular"]["onsd_mm"] = st.slider(
                    "ONSD (mm)", 4.0, 7.5, float(ov.get("onsd_mm", 5.1)), 0.1
                )
                manual_inputs["neuro_ocular"]["sph_eq_shift_d"] = st.slider(
                    "Hyperopic Shift (D)", -0.5, 2.0, float(ov.get("sph_eq_shift_d", 0.25)), 0.25
                )
                manual_inputs["neuro_ocular"]["folds_foveal"] = st.checkbox(
                    "Foveal Folds Present", value=bool(ov.get("folds_foveal", False))
                )

        # Tab 4: immune_metabolic
        with tabs[4]:
            c1, c2 = st.columns(2, gap="large")
            ov = saved_ov.get("immune_metabolic", {})
            with c1:
                manual_inputs["immune_metabolic"]["temp_c"] = st.slider(
                    "Oral Temp (C)", 35.5, 40.0, float(ov.get("temp_c", 36.7)), 0.1
                )
                manual_inputs["immune_metabolic"]["lymph"] = st.slider(
                    "Lymphocytes (10^9/L)", 0.4, 3.5, float(ov.get("lymph", 1.95)), 0.05
                )
            with c2:
                manual_inputs["immune_metabolic"]["saliva_vzv"] = st.number_input(
                    "Saliva VZV (copies/mL)", 0.0, 20000.0, float(ov.get("saliva_vzv", 0.0)), 50.0
                )
                manual_inputs["immune_metabolic"]["hydration_ml"] = st.slider(
                    "Hydration (mL/day)", 800.0, 4000.0, float(ov.get("hydration_ml", 2550.0)), 50.0
                )

        st.write("")
        run_clicked = st.button("🚀 Save & Run All 5 Agents", type="primary", width="stretch")

    active_overrides = manual_inputs if use_manual_overrides else {}
    results, cross_context = evaluate_all_modules(
        manual_overrides=active_overrides,
        scenario=scenario,
        crew_id=crew_id,
        mission_day=mission_day,
        prefer_real_csv=prefer_real_csv,
    )
    schedule = aggregate_mission_schedule(results=results, cross_context=cross_context)

    if run_clicked:
        save_runtime_session(
            manual_overrides=manual_inputs,
            crew_id=crew_id,
            mission_day=mission_day,
            scenario=scenario,
            results=results,
        )
        st.toast("Saved telemetry snapshot to data/runtime_session.json & executed all 5 modules!", icon="✅")

    st.write("")

    # Mission Top Banner KPIs (with large gap and card CSS)
    k1, k2, k3, k4 = st.columns(4, gap="large")
    k1.metric(
        "Overall Mission Status",
        f"{STATUS_EMOJI.get(schedule['overall_status'], '🟡')} {schedule['overall_status']}",
    )
    k2.metric("Urgent RED Subsystems", f"{len(schedule['urgent_modules'])} / 5")
    k3.metric("Next Mandatory Check", f"In {schedule['next_check_hours']} h")
    k4.metric(
        "Earliest Projected RED",
        f"{schedule['earliest_red_days']} days" if schedule["earliest_red_days"] is not None else "None",
    )

    st.write("")

    # =========================================================================
    # ADAPTIVE MISSION CONTROL DASHBOARD
    # =========================================================================
    if layout_mode.startswith("Auto 3-Column"):
        col_left, col_center, col_right = st.columns([1.08, 1.48, 1.14], gap="large")
        with col_left:
            _render_left_panel(results)
        with col_center:
            _render_center_panel(results)
        with col_right:
            _render_right_panel(schedule, cross_context)

    elif layout_mode.startswith("2-Column Split"):
        top_left, top_right = st.columns([1.05, 1.55], gap="large")
        with top_left:
            _render_left_panel(results)
        with top_right:
            _render_center_panel(results)
        st.write("")
        _render_right_panel(schedule, cross_context)

    else:
        _render_left_panel(results)
        st.write("")
        _render_center_panel(results)
        st.write("")
        _render_right_panel(schedule, cross_context)


if __name__ == "__main__":
    main()
