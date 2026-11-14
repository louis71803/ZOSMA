"""SpaceX Crew Dragon / NASA Deep-Space HUD Frontend Component (HTML + CSS + JS).

Renders a pure client-side responsive glassmorphism Mission Control interface
inside Streamlit (`st.components.v2`) with instant interactive switching and
bidirectional Python callbacks for running the 5 Z.O.S.M.A. medical agents.
"""

from __future__ import annotations

HUD_HTML = """
<div id="zosma-hud-mount"></div>
"""

HUD_CSS = """
:host, * {
  box-sizing: border-box;
  font-family: 'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
}

:host {
  display: block;
  width: 100%;
  color: #e2e8f0;
}

.hud-shell {
  width: 100%;
  background:
    radial-gradient(circle at 14% 12%, rgba(56, 189, 248, 0.09), transparent 36%),
    radial-gradient(circle at 88% 8%, rgba(99, 102, 241, 0.08), transparent 34%),
    linear-gradient(180deg, #050913 0%, #070d1b 55%, #050912 100%);
  border: 1px solid rgba(56, 189, 248, 0.18);
  border-radius: 18px;
  padding: 18px 20px 22px 20px;
  box-shadow: 0 20px 55px rgba(0, 0, 0, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.05);
  position: relative;
  overflow: hidden;
}

/* Subtle tactical grid overlay */
.hud-shell::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(148, 163, 184, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.03) 1px, transparent 1px);
  background-size: 32px 32px;
  pointer-events: none;
  z-index: 0;
}

.hud-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ================= TOP COMMAND BAR ================= */
.cmd-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 12px 16px;
  background: rgba(11, 19, 36, 0.82);
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 14px;
  backdrop-filter: blur(12px);
}

.brand-group {
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-emblem {
  width: 42px;
  height: 42px;
  border-radius: 11px;
  background: linear-gradient(135deg, rgba(56, 189, 248, 0.22), rgba(14, 165, 233, 0.05));
  border: 1px solid rgba(56, 189, 248, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #38bdf8;
  font-weight: 800;
  font-size: 16px;
  letter-spacing: 1px;
  box-shadow: 0 0 18px rgba(56, 189, 248, 0.22);
}

.brand-titles {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.brand-name {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 1.6px;
  color: #f8fafc;
}

.brand-sub {
  font-size: 11.5px;
  color: #94a3b8;
  letter-spacing: 0.5px;
}

.crew-pill {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.8px;
  padding: 3px 9px;
  border-radius: 999px;
  background: rgba(56, 189, 248, 0.12);
  border: 1px solid rgba(56, 189, 248, 0.35);
  color: #7dd3fc;
}

.cmd-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.scen-group {
  display: inline-flex;
  background: rgba(5, 10, 20, 0.78);
  padding: 3px;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  gap: 3px;
}

.scen-btn {
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.6px;
  padding: 6px 11px;
  border-radius: 7px;
  cursor: pointer;
  transition: all 0.16s ease;
}

.scen-btn:hover {
  color: #f1f5f9;
  background: rgba(148, 163, 184, 0.1);
}

.scen-btn.active-green {
  background: rgba(16, 185, 129, 0.2);
  color: #34d399;
  box-shadow: inset 0 0 0 1px rgba(16, 185, 129, 0.45);
}
.scen-btn.active-yellow {
  background: rgba(245, 158, 11, 0.2);
  color: #fbbf24;
  box-shadow: inset 0 0 0 1px rgba(245, 158, 11, 0.45);
}
.scen-btn.active-red {
  background: rgba(239, 68, 68, 0.24);
  color: #f87171;
  box-shadow: inset 0 0 0 1px rgba(239, 68, 68, 0.5);
}
.scen-btn.active-bad_data {
  background: rgba(249, 115, 22, 0.22);
  color: #fb923c;
  box-shadow: inset 0 0 0 1px rgba(249, 115, 22, 0.48);
}

.drawer-toggle-btn {
  border: 1px solid rgba(56, 189, 248, 0.45);
  background: linear-gradient(135deg, rgba(56, 189, 248, 0.18), rgba(14, 165, 233, 0.08));
  color: #e0f2fe;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.4px;
  padding: 8px 14px;
  border-radius: 9px;
  cursor: pointer;
  transition: all 0.18s ease;
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.drawer-toggle-btn:hover {
  background: rgba(56, 189, 248, 0.28);
  box-shadow: 0 0 16px rgba(56, 189, 248, 0.28);
}

/* ================= TOP KPI RIBBON ================= */
.kpi-ribbon {
  display: grid;
  grid-template-columns: repeat(4, minmax(180px, 1fr));
  gap: 12px;
}

.kpi-tile {
  background: rgba(11, 19, 36, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 12px;
  padding: 12px 15px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  position: relative;
  overflow: hidden;
}

.kpi-tile::after {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--accent, #38bdf8);
}

.kpi-label {
  font-size: 10.5px;
  text-transform: uppercase;
  letter-spacing: 1.1px;
  color: #94a3b8;
  font-weight: 600;
}

.kpi-val {
  font-size: 19px;
  font-weight: 700;
  color: #f8fafc;
  letter-spacing: 0.4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.kpi-sub {
  font-size: 11px;
  color: #64748b;
}

/* ================= 3-COLUMN TACTICAL GRID ================= */
.main-grid {
  display: grid;
  grid-template-columns: minmax(300px, 1.02fr) minmax(390px, 1.52fr) minmax(310px, 1.12fr);
  gap: 16px;
  align-items: stretch;
}

@media (max-width: 1260px) {
  .main-grid {
    grid-template-columns: minmax(290px, 1fr) minmax(340px, 1.35fr);
  }
  .panel-right {
    grid-column: 1 / -1;
  }
}

@media (max-width: 860px) {
  .kpi-ribbon {
    grid-template-columns: repeat(2, 1fr);
  }
  .main-grid {
    grid-template-columns: 1fr;
  }
}

.hud-panel {
  background: rgba(11, 19, 36, 0.76);
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 15px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  backdrop-filter: blur(10px);
}

.panel-hdr {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
  padding-bottom: 10px;
}

.panel-title {
  font-size: 12.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1.3px;
  color: #cbd5e1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-title-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #38bdf8;
  box-shadow: 0 0 8px #38bdf8;
}

.badge {
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.7px;
  padding: 3px 8px;
  border-radius: 6px;
  text-transform: uppercase;
}

.badge-GREEN {
  background: rgba(16, 185, 129, 0.16);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.4);
}
.badge-YELLOW {
  background: rgba(245, 158, 11, 0.16);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.42);
}
.badge-RED {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.5);
  box-shadow: 0 0 12px rgba(239, 68, 68, 0.25);
}
.badge-QC {
  background: rgba(249, 115, 22, 0.2);
  color: #fb923c;
  border: 1px solid rgba(249, 115, 22, 0.5);
}

/* ================= LEFT: BIOMETRIC SVG SCANNER ================= */
.svg-stage {
  width: 100%;
  background: radial-gradient(circle at 50% 48%, rgba(56, 189, 248, 0.08), rgba(5, 9, 18, 0.85) 72%);
  border: 1px solid rgba(56, 189, 248, 0.14);
  border-radius: 12px;
  padding: 8px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.bio-svg {
  width: 100%;
  max-height: 365px;
  height: auto;
  display: block;
}

.hotspot-group {
  cursor: pointer;
  transition: opacity 0.18s ease;
}

.hotspot-group:hover .node-core {
  filter: brightness(1.25);
}

@keyframes pulseRing {
  0% { transform: scale(1); opacity: 0.75; }
  70% { transform: scale(1.9); opacity: 0; }
  100% { transform: scale(1.9); opacity: 0; }
}

.pulse-ring {
  transform-box: fill-box;
  transform-origin: center;
  animation: pulseRing 2.2s infinite ease-out;
}

.pulse-ring-fast {
  transform-box: fill-box;
  transform-origin: center;
  animation: pulseRing 1.15s infinite ease-out;
}

.subsys-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.subsys-pill {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 12px;
  border-radius: 10px;
  background: rgba(6, 12, 24, 0.68);
  border: 1px solid rgba(148, 163, 184, 0.12);
  cursor: pointer;
  transition: all 0.16s ease;
}

.subsys-pill:hover {
  border-color: rgba(56, 189, 248, 0.38);
  background: rgba(15, 28, 52, 0.72);
}

.subsys-pill.selected {
  background: linear-gradient(90deg, rgba(56, 189, 248, 0.16), rgba(15, 23, 42, 0.75));
  border-color: #38bdf8;
  box-shadow: 0 0 14px rgba(56, 189, 248, 0.16);
}

.subsys-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.led-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
}
.led-GREEN { background: #10b981; box-shadow: 0 0 8px #10b981; }
.led-YELLOW { background: #f59e0b; box-shadow: 0 0 8px #f59e0b; }
.led-RED { background: #ef4444; box-shadow: 0 0 10px #ef4444; }
.led-QC { background: #f97316; box-shadow: 0 0 8px #f97316; }

.subsys-name {
  font-size: 12.5px;
  font-weight: 600;
  color: #f1f5f9;
}

.subsys-meta {
  display: flex;
  align-items: center;
  gap: 6px;
}

.src-chip {
  font-size: 9.5px;
  letter-spacing: 0.6px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(148, 163, 184, 0.12);
  color: #94a3b8;
  font-weight: 600;
}

/* ================= CENTER: DIAGNOSTICS, TREND & 3-STEP GUIDE ================= */
.summary-strip {
  font-size: 12.5px;
  line-height: 1.45;
  color: #bae6fd;
  background: rgba(14, 116, 144, 0.16);
  border-left: 3px solid #38bdf8;
  padding: 9px 12px;
  border-radius: 0 8px 8px 0;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(125px, 1fr));
  gap: 9px;
}

.metric-card {
  background: rgba(6, 12, 24, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.13);
  border-radius: 10px;
  padding: 10px 11px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-card:hover {
  border-color: rgba(56, 189, 248, 0.35);
}

.metric-card.active {
  border-color: #38bdf8;
  background: rgba(14, 30, 56, 0.82);
}

.m-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
}

.m-name {
  font-size: 10.5px;
  color: #94a3b8;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.m-val-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.m-val {
  font-size: 16.5px;
  font-weight: 700;
  color: #f8fafc;
}

.m-unit {
  font-size: 10.5px;
  color: #64748b;
}

.m-delta {
  font-size: 10px;
  color: #94a3b8;
}

/* Trend SVG Box */
.chart-card {
  background: rgba(5, 10, 20, 0.82);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 12px;
  padding: 12px 14px 10px 14px;
}

.chart-hdr {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.chart-title {
  font-size: 12px;
  font-weight: 600;
  color: #e2e8f0;
  letter-spacing: 0.4px;
}

.chart-legend {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 10.5px;
  color: #94a3b8;
}

.leg-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.leg-line {
  width: 14px;
  height: 2.5px;
  border-radius: 2px;
}

.trend-svg {
  width: 100%;
  height: 195px;
  display: block;
}

/* 3-Step Non-Medical Crew Guide Segmented Card */
.guide-box {
  background: rgba(6, 12, 24, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 12px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.guide-tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  background: rgba(3, 7, 15, 0.75);
  padding: 4px;
  border-radius: 9px;
}

.guide-tab {
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 11.5px;
  font-weight: 600;
  padding: 7px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: center;
}

.guide-tab:hover {
  color: #e2e8f0;
}

.guide-tab.active {
  background: rgba(56, 189, 248, 0.18);
  color: #38bdf8;
  box-shadow: inset 0 0 0 1px rgba(56, 189, 248, 0.4);
}

.guide-body {
  font-size: 13px;
  line-height: 1.58;
  color: #dbeafe;
  min-height: 68px;
}

.protocol-list {
  margin: 0;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* ================= RIGHT: CLOSED-LOOP TIMELINE ================= */
.conflict-banner {
  background: linear-gradient(135deg, rgba(127, 29, 29, 0.45), rgba(69, 10, 10, 0.65));
  border: 1px solid rgba(248, 113, 113, 0.5);
  border-radius: 10px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.conflict-rule {
  font-size: 10.5px;
  font-weight: 800;
  letter-spacing: 0.8px;
  color: #fca5a5;
  text-transform: uppercase;
}

.conflict-text {
  font-size: 12px;
  line-height: 1.42;
  color: #fee2e2;
}

.signal-box {
  background: rgba(15, 23, 42, 0.6);
  border: 1px dashed rgba(56, 189, 248, 0.32);
  border-radius: 9px;
  padding: 8px 11px;
  font-size: 11px;
  color: #93c5fd;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.plan-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  background: rgba(3, 7, 15, 0.75);
  padding: 4px;
  border-radius: 9px;
}

.timeline-list {
  display: flex;
  flex-direction: column;
  gap: 9px;
  max-height: 430px;
  overflow-y: auto;
  padding-right: 4px;
}

.timeline-card {
  background: rgba(6, 12, 24, 0.78);
  border: 1px solid rgba(148, 163, 184, 0.13);
  border-left: 3px solid var(--tl-color, #10b981);
  border-radius: 9px;
  padding: 9px 11px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.tl-hdr {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.tl-mod {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.7px;
  color: #cbd5e1;
}

.tl-time {
  font-size: 10.5px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 999px;
  background: rgba(56, 189, 248, 0.14);
  color: #7dd3fc;
}

.tl-desc {
  font-size: 12px;
  line-height: 1.45;
  color: #e2e8f0;
}

/* ================= SLIDE-OVER TELEMETRY DRAWER ================= */
.drawer-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 15, 0.76);
  backdrop-filter: blur(6px);
  z-index: 999;
  display: none;
  justify-content: flex-end;
}

.drawer-backdrop.open {
  display: flex;
}

.drawer-panel {
  width: min(640px, 96vw);
  height: 100%;
  background: #081020;
  border-left: 1px solid rgba(56, 189, 248, 0.32);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
  box-shadow: -16px 0 45px rgba(0, 0, 0, 0.75);
}

.drawer-hdr {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(148, 163, 184, 0.15);
  padding-bottom: 12px;
}

.drawer-title {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.8px;
  color: #f8fafc;
}

.close-btn {
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(15, 23, 42, 0.8);
  color: #cbd5e1;
  border-radius: 8px;
  padding: 5px 11px;
  cursor: pointer;
  font-size: 12px;
}

.form-meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
  background: rgba(15, 23, 42, 0.55);
  padding: 12px;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.field-label {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 600;
  display: flex;
  justify-content: space-between;
}

.field-input, .field-select {
  background: #050a15;
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 7px;
  color: #f8fafc;
  padding: 7px 9px;
  font-size: 12.5px;
}

.field-range {
  width: 100%;
  accent-color: #38bdf8;
}

.mod-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.mod-tab-btn {
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(15, 23, 42, 0.65);
  color: #94a3b8;
  font-size: 11.5px;
  font-weight: 600;
  padding: 6px 11px;
  border-radius: 8px;
  cursor: pointer;
}

.mod-tab-btn.active {
  border-color: #38bdf8;
  background: rgba(56, 189, 248, 0.18);
  color: #e0f2fe;
}

.sliders-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 12px;
  background: rgba(11, 19, 36, 0.65);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 11px;
  padding: 14px;
}

.drawer-footer {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid rgba(148, 163, 184, 0.15);
}

.lang-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: rgba(15, 23, 42, 0.72);
  border: 1px solid rgba(56, 189, 248, 0.24);
  border-radius: 10px;
  padding: 10px 12px;
}

.lang-switch {
  display: inline-flex;
  background: #050a15;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 8px;
  padding: 3px;
  gap: 3px;
}

.lang-btn {
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 11.5px;
  font-weight: 600;
  padding: 5px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.lang-btn.active {
  background: rgba(56, 189, 248, 0.22);
  color: #38bdf8;
  box-shadow: inset 0 0 0 1px rgba(56, 189, 248, 0.45);
}

.run-btn {
  flex: 1;
  border: none;
  background: linear-gradient(135deg, #0284c7, #38bdf8);
  color: #04101d;
  font-weight: 800;
  font-size: 13px;
  letter-spacing: 0.6px;
  padding: 11px 18px;
  border-radius: 9px;
  cursor: pointer;
  box-shadow: 0 0 22px rgba(56, 189, 248, 0.35);
}

.run-btn:hover {
  filter: brightness(1.08);
}

.secondary-btn {
  border: 1px solid rgba(148, 163, 184, 0.3);
  background: rgba(15, 23, 42, 0.85);
  color: #cbd5e1;
  font-size: 12px;
  font-weight: 600;
  padding: 10px 14px;
  border-radius: 9px;
  cursor: pointer;
}

/* Footer Data Strip */
.data-strip {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 10px;
  background: rgba(8, 14, 28, 0.75);
  border: 1px solid rgba(148, 163, 184, 0.1);
  font-size: 11px;
  color: #64748b;
}

.data-strip-items {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
"""

HUD_JS = r"""
export default function(component) {
  const { data, setTriggerValue, parentElement } = component;
  if (!data) return;

  let root = parentElement.querySelector('#zosma-hud-mount');
  if (!root) {
    root = document.createElement('div');
    root.id = 'zosma-hud-mount';
    parentElement.appendChild(root);
  }

  const STATUS_HEX = {
    GREEN: '#10b981',
    YELLOW: '#f59e0b',
    RED: '#ef4444',
    QC: '#f97316'
  };

  // Local instant UI state (no roundtrip lag when clicking subsystems, metrics, or tabs)
  const state = {
    lang: data.lang || 'en',
    selectedModule: data.default_module || 'neuro_ocular',
    selectedMetricIdx: 0,
    guideTab: 'measure',     // 'measure' | 'meaning' | 'action'
    planTab: 'short',        // 'short' | 'long'
    drawerOpen: false,
    drawerTab: 'cabin_environment',
    crew_id: data.crew_id || 'C002',
    mission_day: data.mission_day || 124,
    scenario: data.scenario || 'green',
    prefer_real_csv: data.prefer_real_csv !== false,
    use_manual_overrides: Boolean(data.use_manual_overrides),
    inputs: JSON.parse(JSON.stringify(data.manual_inputs || {}))
  };

  const I18N = {
    en: {
      hud_title: 'Z.O.S.M.A. FLIGHT SURGEON HUD',
      hud_sub: 'AUTONOMOUS DEEP-SPACE MEDICAL INTELLIGENCE · OFFLINE CLOSED-LOOP ENGINE',
      crew_badge: 'CREW {crew} · SOL/DAY {day}',
      scen_green: 'GREEN',
      scen_yellow: 'YELLOW',
      scen_red: 'RED',
      scen_bad: 'QC FAULT',
      drawer_btn: '⚙ SETTINGS & TELEMETRY',
      manual_on: 'MANUAL ON',
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
      bio_title: 'BIOMETRIC & HABITAT TELEMETRY',
      click_node: 'CLICK NODE',
      node_cabin: 'CABIN / RAD',
      node_neuro: 'NEURO-OCULAR',
      node_cardio: 'CARDIOVASCULAR',
      node_immune: 'IMMUNE / RENAL',
      node_musculo: 'MUSCULOSKELETAL',
      traj_title: '3-LAYER LONGITUDINAL TRAJECTORY',
      leg_measured: 'Measured',
      leg_forecast: '+30d Forecast',
      guide_hdr: 'ZERO-MEDICAL-BACKGROUND 3-STEP CREW PROTOCOL',
      guide_sop: 'OFFLINE AUTONOMOUS SOP',
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
      src_demo: 'SYNTHETIC DEMO',
      gen_csv_btn: 'GENERATE DEMO CSV TEMPLATES IN data/',
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
      drawer_btn: '⚙ 設定與感測器微調',
      manual_on: '手動覆寫中',
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
      bio_title: '人體生理與艙內環境掃描',
      click_node: '點擊部位切換',
      node_cabin: '艙內環境 / 輻射',
      node_neuro: '神經眼壓 (SANS)',
      node_cardio: '心血管與有氧',
      node_immune: '免疫與腎臟代謝',
      node_musculo: '骨骼肌肉系統',
      traj_title: '三層縱向趨勢軌跡',
      leg_measured: '實測趨勢',
      leg_forecast: '+30天預測',
      guide_hdr: '無醫療背景太空人 · 三步驟操作指引',
      guide_sop: '離線自主標準作業程序',
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
      src_demo: '模擬示範',
      gen_csv_btn: '在 data/ 生成範本 CSV 檔案',
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

  function esc(str) {
    return String(str === null || str === undefined ? '' : str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function statusKey(modObj) {
    if (!modObj) return 'GREEN';
    if (!modObj.quality_passed) return 'QC';
    return modObj.status_light || 'GREEN';
  }

  function badgeLabel(modObj) {
    if (!modObj) return t('status_GREEN');
    if (!modObj.quality_passed) return (modObj.raw_status || 'QC FAIL');
    if (modObj.watch_flag) return t('status_WATCH');
    const st = modObj.status_light || 'GREEN';
    return t('status_' + st);
  }

  function sendPayload(actionType, extra = {}) {
    setTriggerValue('hud_action', {
      type: actionType,
      ts: Date.now(),
      lang: state.lang,
      crew_id: state.crew_id,
      mission_day: Number(state.mission_day) || 124,
      scenario: state.scenario,
      prefer_real_csv: Boolean(state.prefer_real_csv),
      use_manual_overrides: Boolean(state.use_manual_overrides),
      manual_inputs: state.inputs,
      selected_module: state.selectedModule,
      ...extra
    });
  }

  function buildBiometricSvg(modulesMap) {
    const cab = modulesMap['cabin_environment'];
    const neu = modulesMap['neuro_ocular'];
    const car = modulesMap['cardiovascular'];
    const imm = modulesMap['immune_metabolic'];
    const mus = modulesMap['musculoskeletal'];

    const cabHex = STATUS_HEX[statusKey(cab)] || '#38bdf8';

    const nodes = [
      { id: 'cabin_environment', label: t('node_cabin'), x: 56,  y: 52,  lx: 16,  ly: 28, align: 'start' },
      { id: 'neuro_ocular',      label: t('node_neuro'), x: 150, y: 66,  lx: 214, ly: 56, align: 'start' },
      { id: 'cardiovascular',    label: t('node_cardio'), x: 156, y: 132, lx: 214, ly: 124, align: 'start' },
      { id: 'immune_metabolic',  label: t('node_immune'), x: 146, y: 184, lx: 214, ly: 186, align: 'start' },
      { id: 'musculoskeletal',   label: t('node_musculo'), x: 132, y: 268, lx: 214, ly: 268, align: 'start' }
    ];

    const nodesSvg = nodes.map(n => {
      const m = modulesMap[n.id];
      const sk = statusKey(m);
      const hex = STATUS_HEX[sk] || '#10b981';
      const isSel = state.selectedModule === n.id;
      const pulseClass = sk === 'RED' ? 'pulse-ring-fast' : 'pulse-ring';
      const ringR = isSel ? 12 : 9;

      return `
        <g class="hotspot-group" data-mod="${n.id}">
          <line x1="${n.x}" y1="${n.y}" x2="${n.lx - 4}" y2="${n.ly - 3}"
                stroke="${isSel ? '#38bdf8' : 'rgba(148,163,184,0.38)'}"
                stroke-width="${isSel ? '1.6' : '1'}" stroke-dasharray="${isSel ? 'none' : '3,3'}" />
          <circle cx="${n.x}" cy="${n.y}" r="${ringR}" fill="${hex}" opacity="0.28" class="${pulseClass}" />
          ${isSel ? `<circle cx="${n.x}" cy="${n.y}" r="14" fill="none" stroke="#38bdf8" stroke-width="1.6" />` : ''}
          <circle class="node-core" cx="${n.x}" cy="${n.y}" r="${isSel ? 6.5 : 5.2}" fill="${hex}" stroke="#f8fafc" stroke-width="1.4" />
          <text x="${n.lx}" y="${n.ly}" fill="${isSel ? '#38bdf8' : '#cbd5e1'}"
                font-size="9.5" font-weight="${isSel ? '700' : '600'}" letter-spacing="0.8" text-anchor="${n.align}">
            ${esc(n.label)}
          </text>
        </g>
      `;
    }).join('');

    return `
      <svg class="bio-svg" viewBox="0 0 330 345" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="bodyGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="rgba(56, 189, 248, 0.20)" />
            <stop offset="100%" stop-color="rgba(15, 23, 42, 0.45)" />
          </linearGradient>
        </defs>

        <!-- Habitat Pressure Hull Frame -->
        <rect x="12" y="12" width="306" height="321" rx="18"
              fill="none" stroke="${cabHex}" stroke-opacity="0.45" stroke-width="1.5" stroke-dasharray="6,4" />
        <path d="M 12 34 L 12 12 L 34 12 M 296 12 L 318 12 L 318 34 M 12 311 L 12 333 L 34 333 M 296 333 L 318 333 L 318 311"
              fill="none" stroke="#38bdf8" stroke-width="2" opacity="0.7" />

        <!-- Subtle Radar Rings around Astronaut -->
        <circle cx="150" cy="175" r="95" fill="none" stroke="rgba(56,189,248,0.08)" stroke-width="1" />
        <circle cx="150" cy="175" r="130" fill="none" stroke="rgba(56,189,248,0.05)" stroke-width="1" />

        <!-- Sleek Vector Astronaut Anatomical Silhouette -->
        <g transform="translate(0, 4)">
          <!-- Head & Helmet Visor -->
          <circle cx="150" cy="64" r="22" fill="url(#bodyGrad)" stroke="rgba(125,211,252,0.65)" stroke-width="1.5" />
          <ellipse cx="150" cy="63" rx="14" ry="9" fill="rgba(56,189,248,0.12)" stroke="rgba(56,189,248,0.45)" stroke-width="1" />

          <!-- Neck, Shoulders, Torso & Arms -->
          <path d="M 141 86 L 159 86
                   L 182 96 C 193 100, 198 110, 200 124
                   L 206 184 C 207 191, 196 193, 193 185
                   L 184 130 L 176 130
                   L 173 202
                   L 180 296 C 181 305, 166 306, 164 296
                   L 154 218 L 146 218
                   L 136 296 C 134 306, 119 305, 120 296
                   L 127 202
                   L 124 130 L 116 130
                   L 107 185 C 104 193, 93 191, 94 184
                   L 100 124 C 102 110, 107 100, 118 96 Z"
                fill="url(#bodyGrad)" stroke="rgba(125,211,252,0.58)" stroke-width="1.5" stroke-linejoin="round" />

          <!-- Internal Spine & Chest Telemetry Grid Lines -->
          <line x1="150" y1="90" x2="150" y2="205" stroke="rgba(56,189,248,0.22)" stroke-width="1" stroke-dasharray="2,3" />
          <path d="M 132 122 Q 150 132 168 122" fill="none" stroke="rgba(56,189,248,0.22)" stroke-width="1" />
          <path d="M 134 142 Q 150 151 166 142" fill="none" stroke="rgba(56,189,248,0.18)" stroke-width="1" />
        </g>

        ${nodesSvg}
      </svg>
    `;
  }

  function buildTrendSvg(metric, missionDay) {
    if (!metric) {
      return `<div style="padding:24px;color:#64748b;font-size:12px;">No telemetry series available.</div>`;
    }

    const days = (metric.history_days && metric.history_days.length >= 2)
      ? metric.history_days
      : [0, 30, 60, 90, missionDay];

    let vals = [];
    if (metric.history_values && metric.history_values.length === days.length) {
      vals = metric.history_values.map(Number);
    } else {
      const cur = Number(metric.current_val);
      const base = metric.baseline_val !== null && metric.baseline_val !== undefined && !isNaN(Number(metric.baseline_val))
        ? Number(metric.baseline_val)
        : (isNaN(cur) ? 0 : cur);
      const endVal = isNaN(cur) ? base : cur;
      const step = (endVal - base) / Math.max(days.length - 1, 1);
      vals = days.map((_, i) => Number((base + step * i).toFixed(3)));
    }

    // 30-day linear forecast
    const slope = (days[days.length - 1] > days[0])
      ? (vals[vals.length - 1] - vals[0]) / (days[days.length - 1] - days[0])
      : 0;
    const projDays = [days[days.length - 1], days[days.length - 1] + 15, days[days.length - 1] + 30];
    const projVals = projDays.map(d => vals[vals.length - 1] + slope * (d - days[days.length - 1]));

    const yThresh = metric.yellow_threshold !== null && metric.yellow_threshold !== undefined ? Number(metric.yellow_threshold) : null;
    const rThresh = metric.red_threshold !== null && metric.red_threshold !== undefined ? Number(metric.red_threshold) : null;

    const allNums = [...vals, ...projVals];
    if (yThresh !== null && !isNaN(yThresh)) allNums.push(yThresh);
    if (rThresh !== null && !isNaN(rThresh)) allNums.push(rThresh);

    let yMin = Math.min(...allNums);
    let yMax = Math.max(...allNums);
    const pad = (yMax - yMin) === 0 ? Math.max(Math.abs(yMax) * 0.15, 1) : (yMax - yMin) * 0.18;
    yMin -= pad;
    yMax += pad;

    const xMin = days[0];
    const xMax = projDays[projDays.length - 1];

    const W = 540, H = 185;
    const PL = 44, PR = 18, PT = 14, PB = 26;
    const cw = W - PL - PR;
    const ch = H - PT - PB;

    const sx = d => PL + ((d - xMin) / Math.max(xMax - xMin, 1)) * cw;
    const sy = v => PT + ch - ((v - yMin) / Math.max(yMax - yMin, 1e-6)) * ch;

    const linePts = days.map((d, i) => `${sx(d).toFixed(1)},${sy(vals[i]).toFixed(1)}`).join(' ');
    const areaPts = `${sx(days[0]).toFixed(1)},${(PT + ch).toFixed(1)} ${linePts} ${sx(days[days.length - 1]).toFixed(1)},${(PT + ch).toFixed(1)}`;
    const projPts = projDays.map((d, i) => `${sx(d).toFixed(1)},${sy(projVals[i]).toFixed(1)}`).join(' ');

    const threshLines = [];
    if (yThresh !== null && !isNaN(yThresh)) {
      const yy = sy(yThresh).toFixed(1);
      threshLines.push(`
        <line x1="${PL}" y1="${yy}" x2="${W - PR}" y2="${yy}" stroke="#f59e0b" stroke-width="1.2" stroke-dasharray="5,4" opacity="0.8" />
        <text x="${W - PR - 4}" y="${Number(yy) - 4}" fill="#fbbf24" font-size="9.5" text-anchor="end">WARN ${yThresh}</text>
      `);
    }
    if (rThresh !== null && !isNaN(rThresh)) {
      const ry = sy(rThresh).toFixed(1);
      threshLines.push(`
        <line x1="${PL}" y1="${ry}" x2="${W - PR}" y2="${ry}" stroke="#ef4444" stroke-width="1.3" stroke-dasharray="5,4" opacity="0.85" />
        <text x="${W - PR - 4}" y="${Number(ry) - 4}" fill="#f87171" font-size="9.5" text-anchor="end">CRIT ${rThresh}</text>
      `);
    }

    const yTicks = [yMin, (yMin + yMax) / 2, yMax].map(v => {
      const py = sy(v).toFixed(1);
      const lbl = Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(1);
      return `
        <line x1="${PL}" y1="${py}" x2="${W - PR}" y2="${py}" stroke="rgba(148,163,184,0.08)" stroke-width="1" />
        <text x="${PL - 6}" y="${Number(py) + 3}" fill="#64748b" font-size="9.5" text-anchor="end">${lbl}</text>
      `;
    }).join('');

    const xTicks = [...days, projDays[2]].map(d => {
      const px = sx(d).toFixed(1);
      return `<text x="${px}" y="${H - 6}" fill="#64748b" font-size="9.5" text-anchor="middle">D${d}</text>`;
    }).join('');

    const dots = days.map((d, i) => {
      const px = sx(d).toFixed(1);
      const py = sy(vals[i]).toFixed(1);
      return `<circle cx="${px}" cy="${py}" r="4" fill="#38bdf8" stroke="#050913" stroke-width="1.5" />`;
    }).join('');

    return `
      <svg class="trend-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
        <defs>
          <linearGradient id="cyanArea" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.32" />
            <stop offset="100%" stop-color="#38bdf8" stop-opacity="0.0" />
          </linearGradient>
        </defs>
        ${yTicks}
        ${threshLines.join('')}
        <polygon points="${areaPts}" fill="url(#cyanArea)" />
        <polyline points="${linePts}" fill="none" stroke="#38bdf8" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" />
        <polyline points="${projPts}" fill="none" stroke="#f472b6" stroke-width="2" stroke-dasharray="4,4" />
        ${dots}
        ${xTicks}
      </svg>
    `;
  }

  function buildDrawerFields() {
    const tab = state.drawerTab;
    const cur = state.inputs[tab] || {};

    const schemas = {
      cabin_environment: [
        { key: 'ppco2_1h_mmHg', label: 'Cabin ppCO2 1h (mmHg)', type: 'range', min: 0.5, max: 5.0, step: 0.05 },
        { key: 'proton_flux_10mev_pfu', label: 'GOES >=10MeV Proton Flux (pfu)', type: 'range', min: 0, max: 300, step: 1 },
        { key: 'crew_leq8_dBA', label: 'Crew 8h Noise Exposure (dBA)', type: 'range', min: 50, max: 95, step: 0.5 },
        { key: 'sleep_tst_h', label: 'Actiwatch Sleep Duration (h)', type: 'range', min: 3.0, max: 10.0, step: 0.1 },
        { key: 'spe_alert', label: 'SPE Solar Radiation Storm Alert', type: 'checkbox' }
      ],
      cardiovascular: [
        { key: 'rest_hr_bpm', label: 'Resting Heart Rate (bpm)', type: 'range', min: 40, max: 130, step: 1 },
        { key: 'spo2_pct', label: 'Peripheral SpO2 (%)', type: 'range', min: 85, max: 100, step: 0.1 },
        { key: 'pvc_burden_pct', label: 'Holter 24h PVC Burden (%)', type: 'range', min: 0, max: 15, step: 0.1 },
        { key: 'ijv_flow', label: 'IJV Ultrasound Flow', type: 'select', options: ['forward', 'stagnant', 'reversed'] },
        { key: 'ijv_thrombus', label: 'IJV Thrombus Detected', type: 'checkbox' }
      ],
      musculoskeletal: [
        { key: 'csa_thigh_cm2', label: 'Thigh Muscle CSA (cm²)', type: 'range', min: 115, max: 165, step: 0.5 },
        { key: 'velocity_loss_pct', label: 'E4D VBT Velocity Loss (%)', type: 'range', min: 0, max: 45, step: 0.5 },
        { key: 'ctx', label: 'CTX Bone Resorption (ng/mL)', type: 'range', min: 0.20, max: 0.80, step: 0.01 },
        { key: 'body_mass_kg', label: 'SLAMMD Body Mass (kg)', type: 'range', min: 55, max: 90, step: 0.2 }
      ],
      neuro_ocular: [
        { key: 'delta_trt_um', label: 'Mini OCT ΔTRT (µm)', type: 'range', min: -10, max: 90, step: 1 },
        { key: 'delta_v_onh_mm3', label: 'Optic Nerve Head ΔV_ONH (mm³)', type: 'range', min: 0.0, max: 0.50, step: 0.01 },
        { key: 'onsd_mm', label: 'Ultrasound ONSD (mm)', type: 'range', min: 4.0, max: 7.5, step: 0.1 },
        { key: 'sph_eq_shift_d', label: 'Hyperopic Shift (Diopters)', type: 'range', min: -0.5, max: 2.0, step: 0.25 },
        { key: 'folds_foveal', label: 'Chorioretinal Foveal Folds', type: 'checkbox' }
      ],
      immune_metabolic: [
        { key: 'temp_c', label: 'Oral Temperature (°C)', type: 'range', min: 35.5, max: 40.0, step: 0.1 },
        { key: 'lymph', label: 'Lymphocyte Count (10⁹/L)', type: 'range', min: 0.4, max: 3.5, step: 0.05 },
        { key: 'saliva_vzv', label: 'Saliva VZV DNA (copies/mL)', type: 'range', min: 0, max: 10000, step: 50 },
        { key: 'hydration_ml', label: '24h Fluid Intake (mL)', type: 'range', min: 800, max: 4000, step: 50 }
      ]
    };

    return (schemas[tab] || []).map(f => {
      const val = cur[f.key];
      if (f.type === 'checkbox') {
        return `
          <label class="field-group" style="flex-direction:row;align-items:center;gap:9px;padding-top:14px;cursor:pointer;">
            <input type="checkbox" data-input-key="${f.key}" data-input-type="checkbox" ${val ? 'checked' : ''} />
            <span class="field-label" style="font-size:12px;color:#e2e8f0;">${esc(f.label)}</span>
          </label>
        `;
      }
      if (f.type === 'select') {
        const opts = f.options.map(o => `<option value="${o}" ${val === o ? 'selected' : ''}>${o.toUpperCase()}</option>`).join('');
        return `
          <div class="field-group">
            <span class="field-label">${esc(f.label)}</span>
            <select class="field-select" data-input-key="${f.key}" data-input-type="select">${opts}</select>
          </div>
        `;
      }
      return `
        <div class="field-group">
          <div class="field-label">
            <span>${esc(f.label)}</span>
            <strong style="color:#38bdf8;" id="lbl-${f.key}">${val}</strong>
          </div>
          <input class="field-range" type="range"
                 min="${f.min}" max="${f.max}" step="${f.step}" value="${val}"
                 data-input-key="${f.key}" data-input-type="number" />
        </div>
      `;
    }).join('');
  }

  function render() {
    const modulesMap = data.modules || {};
    const schedule = data.schedule || {};
    const order = data.module_order || Object.keys(modulesMap);
    const selMod = modulesMap[state.selectedModule] || modulesMap[order[0]] || {};
    const metrics = selMod.metrics || [];
    if (state.selectedMetricIdx >= metrics.length) state.selectedMetricIdx = 0;
    const activeMetric = metrics[state.selectedMetricIdx] || metrics[0] || null;

    const overallStatus = schedule.overall_status || 'GREEN';
    const overallAccent = STATUS_HEX[overallStatus] || '#10b981';

    // Subsystem pills
    const subsysHtml = order.map(modId => {
      const m = modulesMap[modId];
      const sk = statusKey(m);
      const isSel = modId === state.selectedModule;
      const srcBadge = m && m.data_source === 'REAL' ? t('src_real') : (m ? m.data_source : 'DEMO');
      return `
        <div class="subsys-pill ${isSel ? 'selected' : ''}" data-select-mod="${modId}">
          <div class="subsys-left">
            <span class="led-dot led-${sk}"></span>
            <span class="subsys-name">${esc(modShortName(modId, m ? m.short_name : modId))}</span>
          </div>
          <div class="subsys-meta">
            <span class="src-chip">${esc(srcBadge)}</span>
            <span class="badge badge-${sk}">${esc(badgeLabel(m))}</span>
          </div>
        </div>
      `;
    }).join('');

    // Mini metric tiles
    const metricTilesHtml = metrics.map((m, idx) => {
      const msk = !m.quality_passed ? 'QC' : (m.status_light || 'GREEN');
      const deltaTxt = (m.delta_pct !== null && m.delta_pct !== undefined)
        ? `${m.delta_pct > 0 ? '+' : ''}${m.delta_pct}% ${t('vs_base')}`
        : `${t('layer_prefix')} ${m.decided_by || 'rule'}`;
      return `
        <div class="metric-card ${idx === state.selectedMetricIdx ? 'active' : ''}" data-metric-idx="${idx}">
          <div class="m-top">
            <span class="m-name" title="${esc(m.metric_name)}">${esc(m.metric_name)}</span>
            <span class="led-dot led-${msk}" style="width:7px;height:7px;"></span>
          </div>
          <div class="m-val-row">
            <span class="m-val">${esc(m.current_val)}</span>
            <span class="m-unit">${esc(m.unit)}</span>
          </div>
          <div class="m-delta">${esc(deltaTxt)}</div>
        </div>
      `;
    }).join('');

    // 3-step Crew Guidance content
    const g = selMod.guidance || {};
    let guideContentHtml = '';
    if (state.guideTab === 'measure') {
      guideContentHtml = `<div>${esc(g.how_to_measure)}</div>`;
    } else if (state.guideTab === 'meaning') {
      guideContentHtml = `<div>${esc(g.plain_explanation)}</div>`;
    } else {
      const steps = Array.isArray(g.action_protocol) ? g.action_protocol : [g.action_protocol || 'Nominal'];
      guideContentHtml = `<ol class="protocol-list">${steps.map(s => `<li>${esc(s)}</li>`).join('')}</ol>`;
    }

    // Conflicts & cross-module signals
    const conflictsHtml = (schedule.conflicts_resolved || []).map(c => `
      <div class="conflict-banner">
        <div class="conflict-rule">⚡ ${esc(c.rule)}</div>
        <div class="conflict-text">${esc(c.resolution)}</div>
      </div>
    `).join('');

    const flags = data.propagated_flags || [];
    const signalsHtml = flags.length
      ? `<div class="signal-box"><strong>${esc(t('bus_title'))}</strong>${flags.map(f => `<span>• ${esc(f)}</span>`).join('')}</div>`
      : '';

    // Timeline cards
    const timelineItems = state.planTab === 'short'
      ? (schedule.short_term_board || []).map(item => ({
          mod: item.module_id,
          status: item.status_light,
          tag: item.next_hours === 0 ? t('tag_immediate') : `T+${item.next_hours}H`,
          text: item.action
        }))
      : (schedule.long_term_board || []).map(item => ({
          mod: item.module_id,
          status: item.status_light,
          tag: item.days_until_red !== null && item.days_until_red !== undefined ? t('tag_red_in', { d: item.days_until_red }) : t('tag_regimen'),
          text: item.adjustment
        }));

    const timelineHtml = timelineItems.map(it => {
      const col = STATUS_HEX[it.status] || '#10b981';
      const modTitle = modShortName(it.mod, it.mod.replace('_', ' '));
      return `
        <div class="timeline-card" style="--tl-color:${col}">
          <div class="tl-hdr">
            <span class="tl-mod">${esc(modTitle)}</span>
            <span class="tl-time">${esc(it.tag)}</span>
          </div>
          <div class="tl-desc">${esc(it.text)}</div>
        </div>
      `;
    }).join('');

    // Data folder footer strip
    const folderItems = (data.data_statuses || []).map(ds =>
      `<span><strong>${esc(modShortName(ds.module_id, ds.short_name))}:</strong> <span style="color:${ds.has_real_files ? '#34d399' : '#94a3b8'}">${ds.has_real_files ? esc(t('src_real')) : esc(t('src_demo'))}</span></span>`
    ).join('');

    const selSk = statusKey(selMod);
    const scenLabelMap = {
      green: t('scen_green'),
      yellow: t('scen_yellow'),
      red: t('scen_red'),
      bad_data: t('scen_bad')
    };

    root.innerHTML = `
      <div class="hud-shell">
        <div class="hud-content">

          <!-- TOP MISSION COMMAND BAR -->
          <div class="cmd-bar">
            <div class="brand-group">
              <div class="brand-emblem">Z</div>
              <div class="brand-titles">
                <div class="brand-name">
                  ${esc(t('hud_title'))}
                  <span class="crew-pill">${esc(t('crew_badge', { crew: state.crew_id, day: state.mission_day }))}</span>
                </div>
                <div class="brand-sub">${esc(t('hud_sub'))}</div>
              </div>
            </div>

            <div class="cmd-controls">
              <div class="scen-group" title="Switch Simulation Preset">
                ${['green', 'yellow', 'red', 'bad_data'].map(sc => `
                  <button class="scen-btn ${state.scenario === sc ? 'active-' + sc : ''}" data-scen="${sc}">
                    ${esc(scenLabelMap[sc])}
                  </button>
                `).join('')}
              </div>
              <button class="drawer-toggle-btn" id="open-drawer-btn">
                ${esc(t('drawer_btn'))} ${state.use_manual_overrides ? '(' + esc(t('manual_on')) + ')' : ''}
              </button>
            </div>
          </div>

          <!-- KPI RIBBON -->
          <div class="kpi-ribbon">
            <div class="kpi-tile" style="--accent:${overallAccent}">
              <span class="kpi-label">${esc(t('kpi_status_lbl'))}</span>
              <span class="kpi-val" style="color:${overallAccent}">${esc(t('status_' + overallStatus))}</span>
              <span class="kpi-sub">${esc(t('kpi_status_sub'))}</span>
            </div>
            <div class="kpi-tile" style="--accent:${(schedule.urgent_modules || []).length ? '#ef4444' : '#38bdf8'}">
              <span class="kpi-label">${esc(t('kpi_red_lbl'))}</span>
              <span class="kpi-val">${(schedule.urgent_modules || []).length} <span style="font-size:13px;color:#64748b;">/ 5</span></span>
              <span class="kpi-sub">${(schedule.urgent_modules || []).length ? esc(schedule.urgent_modules.map(m => modShortName(m, m)).join(', ')) : esc(t('kpi_red_sub_ok'))}</span>
            </div>
            <div class="kpi-tile" style="--accent:#38bdf8">
              <span class="kpi-label">${esc(t('kpi_triage_lbl'))}</span>
              <span class="kpi-val">T + ${esc(schedule.next_check_hours)} H</span>
              <span class="kpi-sub">${esc(t('kpi_triage_sub'))}</span>
            </div>
            <div class="kpi-tile" style="--accent:#a855f7">
              <span class="kpi-label">${esc(t('kpi_proj_lbl'))}</span>
              <span class="kpi-val">${schedule.earliest_red_days !== null && schedule.earliest_red_days !== undefined ? esc(schedule.earliest_red_days) + ' ' + esc(t('days_unit')) : esc(t('none_lbl'))}</span>
              <span class="kpi-sub">${esc(t('kpi_proj_sub'))}</span>
            </div>
          </div>

          <!-- 3-COLUMN MISSION CONTROL WORKSPACE -->
          <div class="main-grid">

            <!-- LEFT COLUMN: BIOMETRIC & HABITAT SCANNER -->
            <div class="hud-panel">
              <div class="panel-hdr">
                <span class="panel-title"><span class="panel-title-dot"></span>${esc(t('bio_title'))}</span>
                <span style="font-size:10.5px;color:#64748b;">${esc(t('click_node'))}</span>
              </div>
              <div class="svg-stage">
                ${buildBiometricSvg(modulesMap)}
              </div>
              <div class="subsys-list">
                ${subsysHtml}
              </div>
            </div>

            <!-- CENTER COLUMN: SUBSYSTEM DIAGNOSTICS & 3-STEP CREW PROTOCOL -->
            <div class="hud-panel">
              <div class="panel-hdr">
                <span class="panel-title"><span class="panel-title-dot"></span>${esc(modFullName(state.selectedModule, selMod.display_name || state.selectedModule))}</span>
                <span class="badge badge-${selSk}">${esc(badgeLabel(selMod))}</span>
              </div>

              ${selMod.summary_note ? `<div class="summary-strip">${esc(selMod.summary_note)}</div>` : ''}

              <div class="metric-grid">
                ${metricTilesHtml}
              </div>

              <div class="chart-card">
                <div class="chart-hdr">
                  <span class="chart-title">
                    ${esc(t('traj_title'))} · <span style="color:#38bdf8">${esc(activeMetric ? activeMetric.metric_name : '')}</span>
                    ${activeMetric && activeMetric.unit ? `(${esc(activeMetric.unit)})` : ''}
                  </span>
                  <div class="chart-legend">
                    <span class="leg-item"><span class="leg-line" style="background:#38bdf8;"></span>${esc(t('leg_measured'))}</span>
                    <span class="leg-item"><span class="leg-line" style="background:#f472b6;"></span>${esc(t('leg_forecast'))}</span>
                  </div>
                </div>
                ${buildTrendSvg(activeMetric, state.mission_day)}
              </div>

              <div class="guide-box">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                  <span style="font-size:11px;font-weight:700;letter-spacing:1px;color:#94a3b8;text-transform:uppercase;">
                    ${esc(t('guide_hdr'))}
                  </span>
                  <span style="font-size:10.5px;color:#64748b;">${esc(t('guide_sop'))}</span>
                </div>
                <div class="guide-tabs">
                  <button class="guide-tab ${state.guideTab === 'measure' ? 'active' : ''}" data-guide-tab="measure">${esc(t('tab_measure'))}</button>
                  <button class="guide-tab ${state.guideTab === 'meaning' ? 'active' : ''}" data-guide-tab="meaning">${esc(t('tab_meaning'))}</button>
                  <button class="guide-tab ${state.guideTab === 'action' ? 'active' : ''}" data-guide-tab="action">${esc(t('tab_action'))}</button>
                </div>
                <div class="guide-body">
                  ${guideContentHtml}
                </div>
              </div>
            </div>

            <!-- RIGHT COLUMN: CLOSED-LOOP SCHEDULE & CONFLICT ARBITRATION -->
            <div class="hud-panel panel-right">
              <div class="panel-hdr">
                <span class="panel-title"><span class="panel-title-dot"></span>${esc(t('plan_title'))}</span>
                <span style="font-size:10.5px;color:#38bdf8;">${esc(t('auto_sync'))}</span>
              </div>

              ${conflictsHtml}
              ${signalsHtml}

              <div class="plan-tabs">
                <button class="guide-tab ${state.planTab === 'short' ? 'active' : ''}" data-plan-tab="short">
                  ${esc(t('plan_short'))}
                </button>
                <button class="guide-tab ${state.planTab === 'long' ? 'active' : ''}" data-plan-tab="long">
                  ${esc(t('plan_long'))}
                </button>
              </div>

              <div class="timeline-list">
                ${timelineHtml}
              </div>
            </div>

          </div>

          <!-- SUBTLE DATA PIPELINE STATUS BAR -->
          <div class="data-strip">
            <div class="data-strip-items">
              <span><strong>${esc(t('pipeline_lbl'))}</strong></span>
              ${folderItems}
            </div>
            <button class="secondary-btn" style="padding:4px 10px;font-size:10.5px;" id="gen-csv-btn">
              ${esc(t('gen_csv_btn'))}
            </button>
          </div>

        </div>
      </div>

      <!-- SLIDE-OVER SETTINGS & MANUAL TELEMETRY DRAWER -->
      <div class="drawer-backdrop ${state.drawerOpen ? 'open' : ''}" id="drawer-backdrop">
        <div class="drawer-panel" id="drawer-panel">
          <div class="drawer-hdr">
            <span class="drawer-title">${esc(t('drawer_title'))}</span>
            <button class="close-btn" id="close-drawer-btn">${esc(t('close_btn'))}</button>
          </div>

          <div class="lang-row">
            <div style="display:flex;flex-direction:column;gap:2px;">
              <span style="font-size:11.5px;font-weight:700;color:#e2e8f0;letter-spacing:0.6px;">${esc(t('lang_label'))}</span>
              <span style="font-size:11px;color:#94a3b8;">${esc(t('lang_desc'))}</span>
            </div>
            <div class="lang-switch">
              <button class="lang-btn ${state.lang === 'en' ? 'active' : ''}" data-lang="en">English</button>
              <button class="lang-btn ${state.lang === 'zh' ? 'active' : ''}" data-lang="zh">繁體中文</button>
            </div>
          </div>

          <div class="form-meta-grid">
            <div class="field-group">
              <span class="field-label">${esc(t('crew_id_lbl'))}</span>
              <input class="field-input" id="inp-crew" value="${esc(state.crew_id)}" />
            </div>
            <div class="field-group">
              <span class="field-label">${esc(t('mission_day_lbl'))}</span>
              <input class="field-input" id="inp-day" type="number" min="1" max="1200" value="${esc(state.mission_day)}" />
            </div>
            <div class="field-group" style="justify-content:center;gap:8px;">
              <label style="font-size:11.5px;color:#cbd5e1;display:flex;align-items:center;gap:6px;cursor:pointer;">
                <input type="checkbox" id="inp-prefer-csv" ${state.prefer_real_csv ? 'checked' : ''} />
                ${esc(t('prefer_csv_lbl'))}
              </label>
              <label style="font-size:11.5px;color:#38bdf8;font-weight:600;display:flex;align-items:center;gap:6px;cursor:pointer;">
                <input type="checkbox" id="inp-use-manual" ${state.use_manual_overrides ? 'checked' : ''} />
                ${esc(t('enable_manual_lbl'))}
              </label>
            </div>
          </div>

          <div class="mod-tabs">
            ${order.map(modId => {
              const m = modulesMap[modId];
              return `
                <button class="mod-tab-btn ${state.drawerTab === modId ? 'active' : ''}" data-drawer-tab="${modId}">
                  ${esc(modShortName(modId, m ? m.short_name : modId))}
                </button>
              `;
            }).join('')}
          </div>

          <div class="sliders-grid">
            ${buildDrawerFields()}
          </div>

          <div class="drawer-footer">
            <button class="secondary-btn" id="reset-overrides-btn">${esc(t('reset_btn'))}</button>
            <button class="run-btn" id="save-run-btn">${esc(t('save_run_btn'))}</button>
          </div>
        </div>
      </div>
    `;

    bindEvents();
  }

  function bindEvents() {
    // Language toggle inside Settings Drawer (instant client-side switch + sync to Python)
    root.querySelectorAll('[data-lang]').forEach(btn => {
      btn.onclick = () => {
        const nextLang = btn.getAttribute('data-lang');
        if (nextLang && nextLang !== state.lang) {
          state.lang = nextLang;
          render();
          sendPayload('switch_lang');
        }
      };
    });

    // Scenario preset buttons -> trigger Python evaluation immediately
    root.querySelectorAll('[data-scen]').forEach(btn => {
      btn.onclick = () => {
        state.scenario = btn.getAttribute('data-scen');
        state.use_manual_overrides = false;
        sendPayload('switch_scenario');
      };
    });

    // SVG hotspots & subsystem pills -> instant client-side switch
    root.querySelectorAll('[data-mod], [data-select-mod]').forEach(el => {
      el.onclick = () => {
        const mod = el.getAttribute('data-mod') || el.getAttribute('data-select-mod');
        if (mod) {
          state.selectedModule = mod;
          state.selectedMetricIdx = 0;
          render();
        }
      };
    });

    // Metric mini cards -> instant trend chart switch
    root.querySelectorAll('[data-metric-idx]').forEach(el => {
      el.onclick = () => {
        state.selectedMetricIdx = Number(el.getAttribute('data-metric-idx')) || 0;
        render();
      };
    });

    // 3-step guide tabs
    root.querySelectorAll('[data-guide-tab]').forEach(el => {
      el.onclick = () => {
        state.guideTab = el.getAttribute('data-guide-tab');
        render();
      };
    });

    // Short / Long term schedule tabs
    root.querySelectorAll('[data-plan-tab]').forEach(el => {
      el.onclick = () => {
        state.planTab = el.getAttribute('data-plan-tab');
        render();
      };
    });

    // Drawer open / close
    const openBtn = root.querySelector('#open-drawer-btn');
    if (openBtn) openBtn.onclick = () => { state.drawerOpen = true; render(); };

    const closeBtn = root.querySelector('#close-drawer-btn');
    if (closeBtn) closeBtn.onclick = () => { state.drawerOpen = false; render(); };

    const backdrop = root.querySelector('#drawer-backdrop');
    if (backdrop) {
      backdrop.onclick = (e) => {
        if (e.target === backdrop) {
          state.drawerOpen = false;
          render();
        }
      };
    }

    // Drawer module tabs
    root.querySelectorAll('[data-drawer-tab]').forEach(btn => {
      btn.onclick = () => {
        state.drawerTab = btn.getAttribute('data-drawer-tab');
        render();
      };
    });

    // Drawer metadata inputs
    const inpCrew = root.querySelector('#inp-crew');
    if (inpCrew) inpCrew.onchange = () => { state.crew_id = inpCrew.value; };

    const inpDay = root.querySelector('#inp-day');
    if (inpDay) inpDay.onchange = () => { state.mission_day = Number(inpDay.value) || 124; };

    const inpPreferCsv = root.querySelector('#inp-prefer-csv');
    if (inpPreferCsv) inpPreferCsv.onchange = () => { state.prefer_real_csv = inpPreferCsv.checked; };

    const inpUseManual = root.querySelector('#inp-use-manual');
    if (inpUseManual) inpUseManual.onchange = () => { state.use_manual_overrides = inpUseManual.checked; };

    // Drawer live slider / select / checkbox inputs
    root.querySelectorAll('[data-input-key]').forEach(inp => {
      const key = inp.getAttribute('data-input-key');
      const typ = inp.getAttribute('data-input-type');
      inp.oninput = () => {
        if (!state.inputs[state.drawerTab]) state.inputs[state.drawerTab] = {};
        let v = inp.value;
        if (typ === 'number') v = Number(inp.value);
        if (typ === 'checkbox') v = inp.checked;
        state.inputs[state.drawerTab][key] = v;
        state.use_manual_overrides = true;
        const chk = root.querySelector('#inp-use-manual');
        if (chk) chk.checked = true;
        const lbl = root.querySelector('#lbl-' + key);
        if (lbl) lbl.textContent = v;
      };
    });

    // Save & Run All 5 Agents
    const saveRunBtn = root.querySelector('#save-run-btn');
    if (saveRunBtn) {
      saveRunBtn.onclick = () => {
        state.drawerOpen = false;
        sendPayload('save_and_run');
      };
    }

    // Reset manual overrides
    const resetBtn = root.querySelector('#reset-overrides-btn');
    if (resetBtn) {
      resetBtn.onclick = () => {
        state.use_manual_overrides = false;
        state.drawerOpen = false;
        sendPayload('reset_overrides');
      };
    }

    // Generate Demo CSVs
    const genCsvBtn = root.querySelector('#gen-csv-btn');
    if (genCsvBtn) {
      genCsvBtn.onclick = () => {
        sendPayload('generate_demo_csvs');
      };
    }
  }

  render();
}
"""
