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
  grid-template-columns: repeat(auto-fit, minmax(128px, 1fr));
  gap: 8px;
  max-height: 205px;
  overflow-y: auto;
  padding-right: 4px;
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
      src_sim: 'SIMULATED',
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
      src_sim: '模擬資料',
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

  const METRIC_ZH = {
    ppco2_1h_mmHg: '艙內 1h 二氧化碳分壓',
    proton_flux_10mev_pfu: 'GOES ≥10MeV 質子通量',
    proton_flux_100mev_pfu: 'GOES ≥100MeV 質子通量',
    dose_rate_uGy_h: 'DOSTEL 區域劑量率',
    career_dose_mSv: '累積任務輻射劑量',
    module_spl_dBA: '艙段空間聲壓級',
    crew_leq8_dBA: '乘員 8 小時噪音暴露',
    daily_noise_dose_pct: '每日噪音劑量百分比',
    audiogram_sts_max_dB: '純音聽力暫時閾移 (STS)',
    p_total_kPa: '艙內總氣壓',
    pio2_mmHg: '吸入氧分壓 (PIO2)',
    temp_C: '艙內環境溫度',
    rh_pct: '艙內相對濕度',
    max_smac_ratio: '揮發氣體最大 SMAC 比',
    water_toc_mg_L: '飲水總有機碳 (TOC)',
    water_iodine_mg_L: '飲水殘餘碘濃度',
    microbial_max_limit_ratio: '空氣/表面/水微生物比',
    particulate_max_limit_ratio: '懸浮微粒濃度上限比',
    sleep_tst_h: '腕錶睡眠總時數',
    pvt_speed_1_per_s: 'PVT-B 反應速度',
    workload_bedford: 'Bedford 工作負荷評分',
    stress_vas: '主觀壓力評分 (VAS)',
    circadian_midpoint_shift_h: '晝夜節律中點偏移',
    co2_sensor_qc: 'CO2 感測器凍結檢核',
    rest_hr_bpm: '靜息心率',
    sbp_mmHg: '收縮壓 (PTT SBP)',
    spo2_pct: '血氧飽和度 (SpO2)',
    resp_rate_bpm: '靜息呼吸頻率',
    pvc_burden_pct: '24h 心室早期收縮負荷',
    stand_hr_rise_bpm: '直立/LBNP 心率升幅',
    ijv_flow_status: '頸內靜脈血流狀態',
    steady_hr_150w_bpm: '150W 固定負荷心率',
    gls_change_pct: '左心室縱向應變變化 (GLS)',
    plasma_volume_delta_pct: '血漿容量變化 (%ΔPV)',
    potassium_mmol_l: '血清鉀離子 (K+)',
    ecg_lead_quality: '心電導極訊號品質',
    csa_thigh_cm2: '大腿肌肉截面積',
    csa_calf_cm2: '小腿肌肉截面積',
    velocity_loss_pct: '深蹲速度衰減率 (VBT)',
    e4d_s_bone_index: 'E4D 骨骼刺激指數',
    iso_peak_force_n: '等長最大肌力峰值',
    body_mass_kg: '太空微重力體重',
    ntx_bone_resorption: '骨吸收指標 NTX',
    ctx_bone_resorption: '骨吸收指標 CTX',
    p1np_bone_formation: '骨生成指標 P1NP',
    est_monthly_bone_loss_pct: '推估每月骨流失率',
    osd575_ca_alp_baseline: 'OSD-575 血清鈣/ALP基準',
    musculoskeletal_qc_gatekeeper: '骨骼肌肉 QC 閘門',
    delta_trt_um: '視網膜厚度變化 ΔTRT',
    delta_v_onh_mm3: '視神經盤體積變化',
    onsd_mm: '視神經鞘直徑 ONSD',
    sph_eq_shift_d: '遠視屈光偏移量',
    vor_gain: '前庭動眼反射增益',
    oct_scan_qc: 'Mini OCT 掃描品質',
    lymphocytes_10e9_l: '淋巴球計數',
    oral_temp_c: '口腔體溫',
    saliva_vzv_copies_ml: '唾液水痘病毒量 (VZV)',
    crp_mg_l: 'C-反應蛋白發炎指標',
    hydration_ml: '24小時飲水量',
    neutrophil_qc_ratio: '嗜中性球分選比例 QC'
  };

  const LAYER_ZH = {
    fixed_threshold: '固定臨床閾值',
    baseline: '個人基準 ±2SD',
    rule: '生理決策規則',
    spe_rule: '太陽風暴連動規則',
    fast_track: '緊急快速通道規則',
    trend: '趨勢斜率預測',
    quality_check: 'Layer 0 品質閘門'
  };

  const EXACT_ZH = {
    'Nominal cabin ECLSS, radiation, acoustic, and sleep telemetry.': '艙內維生環控 (ECLSS)、輻射劑量、聲學噪音與睡眠監測皆正常。',
    'Continue daily Bio-Monitor morning vitals & planned CEVIS cycling.': '維持每日晨間穿戴式生理監測與既定 CEVIS 飛輪有氧訓練。',
    'Continue daily Bio-Monitor morning vitals & scheduled CEVIS Zone 2/4 cycling.': '維持每日晨間 Bio-Monitor 生理監測與既定 CEVIS 第 2/4 區間飛輪訓練。',
    'Continue daily oral temp, hydration log, and monthly Bio-Analyzer CBC.': '維持每日口腔體溫量測、飲水紀錄與每月一次 Bio-Analyzer 血球分析。',
    'Continue nominal 6-day/week E4D resistance & CEVIS countermeasure schedule; target VBT loss 20-30%.': '維持每週 6 天 E4D 抗阻與 CEVIS 對抗訓練；目標速度衰減區間 20–30%。',
    'Continue monthly Mini OCT, Amsler grid, and VOG vestibular checks.': '維持每月一次 Mini OCT 眼底掃描、阿姆斯勒方格表與 VOG 前庭平衡檢測。',
    'Continue standard ECLSS telemetry logging and weekly dosimeter readout.': '持續記錄標準 ECLSS 環控遙測並每週讀取一次個人輻射劑量計。',
    'Maintain current CEVIS aerobic conditioning + bi-weekly LBNP tolerance check.': '維持現行 CEVIS 有氧體能訓練，並每兩週執行一次 LBNP 下半身負壓耐受測試。',
    'Maintain current CEVIS aerobic conditioning + bi-weekly LBNP orthostatic tolerance check.': '維持現行 CEVIS 有氧體能訓練，並每兩週執行一次 LBNP 下半身負壓姿勢耐受測試。',
    'Administer 500-750 mL electrolyte fluid load and repeat Bio-Monitor + Holter check in 12h.': '立即補充 500–750 mL 電解質液，並於 12 小時後複檢 Bio-Monitor 與 Holter 心電監測。',
    'Shift CEVIS to Zone 2 steady aerobic conditioning (4x/week), add LBNP 3x/week, and re-evaluate in 7 days.': '將 CEVIS 調整為第 2 區間穩態有氧訓練（每週 4 次）、加入每週 3 次 LBNP 訓練，並於 7 天後重新評估。',
    'STOP all high-intensity CEVIS & heavy E4D resistance workouts immediately.': '立即停止所有高強度 CEVIS 飛輪與高負荷 E4D 阻力訓練。',
    'Perform Ultrasound 2 bilateral IJV compression sweep + 12-lead ECG + serum K+/clotting re-check.': '立即執行 Ultrasound 2 雙側頸內靜脈壓迫掃描、12 導程心電圖與血清鉀離子/凝血功能複檢。',
    'Suspend HIIT for 14 days; run daily resting ECG, potassium repletion, and LBNP orthostatic conditioning.': '暫停高強度間歇訓練 14 天；每日執行靜息心電圖、補鉀調整與 LBNP 姿勢耐受訓練。',
    'Verify Bio-Monitor ECG strap skin contact (quality >= 0.50), keep motion < 0.50 g, and confirm weekly BP cuff calibration.': '確認 Bio-Monitor 心電胸帶與皮膚貼合良好（訊號品質 ≥ 0.50）、動作干擾 < 0.50 g，並確認每週血壓袖帶校正。',
    'Sensor dropout, dry electrodes, or impossible readings (e.g., SpO2 < 50% or null HR) cannot safely evaluate heart or clot status.': '感測器斷訊、電極乾燥或生理不可能讀數（如 SpO2 < 50% 或心率遺失）無法安全評估心臟與血栓風險。',
    'Re-wet Bio-Monitor thoracic ECG pads and tighten chest strap.': '潤濕 Bio-Monitor 胸部心電電極片並拉緊胸帶。',
    'Clean optical SpO2 fingertip/wrist sensor and eliminate cabin vibration/motion for 60 seconds.': '清潔光學指尖/腕式血氧感測器，並保持靜止 60 秒以排除艙內震動干擾。',
    'Repeat resting vitals capture immediately before running clinical evaluation.': '進行臨床判讀前，請立即重新擷取靜息生命徵象。',
    'Inspect Bio-Monitor garment conductive pads and SpO2 clip during weekly hardware check.': '於每週硬體檢核時檢查 Bio-Monitor 導電織片與 SpO2 夾具。',
    'Wear Bio-Monitor shirt for resting HR/BP/SpO2/Resp; run 24h Holter (MIT-BIH check), CEVIS 150W test, LBNP stand test, and Ultrasound 2 GLS + neck IJV compression.': '穿著 Bio-Monitor 感測衣量測靜息心率/血壓/血氧/呼吸；執行 24h Holter 心律（MIT-BIH 驗證）、CEVIS 150W 測試、LBNP 站立測試與 Ultrasound 2 心臟應變 (GLS) 及頸內靜脈壓迫掃描。',
    'Microgravity shifts ~2L of fluid toward the head, shrinking plasma volume (%DeltaPV), causing neck vein stasis/clots (IJV), electrolyte-driven PVCs, and orthostatic fainting.': '微重力會將約 2 公升體液推向頭部，造成血漿容量萎縮 (%ΔPV)、頸內靜脈血液滯留/血栓 (IJV)、電解質異常誘發心室早搏 (PVC) 與直立性暈厥風險。',
    'Maintain Vitamin D3 supplementation (2000 IU/d) and 2.5 L/d renal hydration.': '持續補充維生素 D3 (2000 IU/日) 並維持每日 2.5 公升飲水以預防腎結石。',
    'Maintain current E4D progressive resistance schedule (weekly 168h verification).': '維持現行 E4D 漸進式抗阻訓練處方（每週 168 小時定期檢核）。',
    'Maintain baseline monthly SANS imaging & pre-landing vestibular drills.': '維持基準每月 SANS 眼科影像追蹤與著陸前前庭適應訓練。',

    'Read MCA CO2 bench, DOSTEL area/crew dosimeters, acoustic SPL meter, and wrist Actiwatch sync.': '讀取 MCA 二氧化碳分析儀、DOSTEL 區域/個人輻射劑量計、聲壓計並同步腕式 Actiwatch 睡眠資料。',
    'Cross-check primary MCA IR bench against portable Drager / backup CDRA CO2 monitor.': '使用手持式 Drager 或備用 CDRA 二氧化碳監測器交叉比對主 MCA 紅外線分析儀讀數。',
    'Wear Bio-Monitor shirt for resting HR/ECG; place Ultrasound 2 linear probe laterally on neck for IJV Doppler flow.': '穿著 Bio-Monitor 感測衣量測靜息心率與心電圖；將 Ultrasound 2 線性探頭置於頸部外側量測頸內靜脈 (IJV) 都卜勒血流。',
    'Wet Bio-Monitor thoracic electrodes lightly with water, tighten chest strap, and sit quietly for 60s.': '以清水微濕 Bio-Monitor 胸部電極片、拉緊胸帶並靜坐 60 秒後重新量測。',
    '1) Attach E4D VBT linear encoder & zero the load cell; log squat peak force, loading rate, reps, and intra-set velocity loss. 2) Scan pre-marked 50% mid-thigh & 30% proximal calf landmarks with Ultrasound 2. 3) Record morning SLAMMD body mass and run Bio-Analyzer NTX/CTX/P1NP fingerstick/urine cartridge.': '1) 安裝 E4D 速度編碼器並歸零荷重元，記錄深蹲峰值力、發力率與組內速度衰減。2) 使用 Ultrasound 2 掃描預先標記的大腿中段 50% 與小腿近端 30% 位置。3) 記錄晨間 SLAMMD 體重並執行 Bio-Analyzer 骨代謝指標 (NTX/CTX/P1NP) 檢測。',
    '1) Zero the E4D load cell with no cable tension. 2) Apply acoustic gel to Ultrasound 2 linear probe at the pre-marked 30% proximal calf & 50% mid-thigh skin tattoos. 3) Verify readings sit inside physiological bounds (Calf CSA 25-200 cm^2, Thigh CSA 50-350 cm^2) before logging.': '1) 於無拉索張力下將 E4D 荷重元歸零。2) 在預先標記的小腿 30% 與大腿 50% 標記處塗抹超音波耦合劑進行掃描。3) 確認數值落於生理合理區間（小腿 25–200、大腿 50–350 cm²）再上傳紀錄。',
    'Capture registered Mini OCT macular/ONH cube, perform Amsler grid monocular test, and measure ONSD 3 mm behind globe via Ultrasound 2.': '擷取已對位基準之 Mini OCT 黃斑部/視神經盤體積掃描，執行單眼阿姆斯勒方格測試，並用 Ultrasound 2 量測眼球後 3mm 視神經鞘直徑 (ONSD)。',
    'Dim cabin light, stabilize head on Mini OCT chinrest, fixate green cross, and verify Auto-Register lock.': '調暗艙內照明，將下巴穩靠於 Mini OCT 支架，注視綠色十字並確認自動對位鎖定 (Auto-Register) 亮燈。',
    'Measure oral temp before eating/drinking; collect morning saliva swab; run Bio-Analyzer fingerstick CBC.': '於進食飲水前量測口腔體溫；採集晨間唾液拭子；執行 Bio-Analyzer 指尖採血全血球計數 (CBC)。',
    'Warm finger 60s, wipe first blood drop, fill Bio-Analyzer cartridge bubble-free, and insert within 30s.': '溫熱手指 60 秒後拭去第一滴血，確保卡匣無氣泡後於 30 秒內插入 Bio-Analyzer 判讀。',

    'Hostile closed-cabin air, CO2 buildup, noise fatigue, and solar proton storms directly impair cognition, immunity, and optic nerve health.': '封閉太空艙內的二氧化碳累積、噪音疲勞與太陽質子風暴會直接損害認知判斷力、免疫功能與視神經健康。',
    'A frozen CO2 sensor hides rising cabin ppCO2, risking headaches and SANS optic nerve swelling.': '凍結卡死的 CO2 感測器會掩蓋艙內二氧化碳升高，導致頭痛與 SANS 視神經水腫風險。',
    'Microgravity shifts ~2L of fluid toward the head, shrinking plasma volume and risking neck vein stasis/clots (IJV) or orthostatic fainting.': '微重力會使約 2 公升體液湧向頭部，導致血漿容量下降並引發頸內靜脈血流滯留/血栓 (IJV) 或姿勢性暈厥風險。',
    'Motion artifact or dry skin creates false arrhythmia alarms.': '皮膚乾燥或肢體晃動會造成心電圖假性心律不整警報。',
    "Without Earth's 1g gravity, weight-bearing leg muscles rapidly shrink and bone calcium dissolves into the bloodstream (raising fracture and kidney-stone risk before Mars landing). Tracking E4D mechanical stimulus (S_bone, VBT 20-30% zone), muscle cross-section, and bone turnover keeps countermeasures effective offline.": '在缺乏地球 1g 重力下，下肢負重肌群會快速萎縮且骨鈣溶出至血液中（大幅提高火星著陸前骨折與腎結石風險）。透過追蹤 E4D 機械刺激指數、肌肉截面積與骨代謝指標，可離線確保對抗訓練確實有效。',
    'Corrupted or implausible measurements (such as a 999 cm^2 ultrasound artifact or missing force cell) must be blocked before decision logic runs so false alarms or missed bone/muscle loss do not occur.': '異常或超出人體極限的感測器偽影（例如 999 cm² 超音波誤判或荷重元斷訊）必須在進入醫療決策前先攔截，避免誤報或漏判骨肌流失。',
    'Spaceflight Associated Neuro-ocular Syndrome (SANS) flattens the back of the eye and swells the optic nerve due to headward fluid shift and elevated CO2.': '太空飛行相關神經眼症候群 (SANS) 是因微重力體液頭向轉移加上艙內偏高的 CO2，造成眼球後壁變平與視神經盤水腫。',
    'Unregistered OCT scans can misread micron-level retinal swelling.': '未成功與基準影像對位的 OCT 掃描會導致微米級視網膜厚度變化判讀失準。',
    'Space radiation, isolation stress, and microgravity suppress T-cell immunity, reactivating latent viruses (VZV/EBV) and raising kidney stone risk.': '太空輻射、孤立壓力與微重力會抑制 T 細胞免疫力，促使體內潛伏病毒（水痘 VZV / EBV）再活化並升高腎結石風險。',
    'Clotted or micro-bubbled fingerstick samples cause false neutropenia readings.': '指尖血樣凝固或混入氣泡會造成儀器分選錯誤，產生假性嗜中性球低下警示。',

    'Cycle CDRA bed regeneration and verify portable fan mixing to clear CO2 pockets.': '啟動 CDRA 除碳床再生循環並確認艙內對流風扇運轉，消除局部二氧化碳滯留。',
    'Wear acoustic ear protection in high-SPL equipment modules.': '進入高噪音設備艙段時請務必配戴主動降噪護耳設備。',
    'Monitor GOES solar weather every 6h and maintain sleep hygiene schedule >= 7h/night.': '每 6 小時監測一次 GOES 太陽風暴氣象並維持每晚 ≥ 7 小時睡眠作息。',
    'If SPE_alert or pfu >= 100: relocate crew to Water Wall radiation storm shelter immediately.': '若 SPE 警報或質子通量 ≥ 100 pfu：立即將乘員撤離至 Water Wall 輻射掩體避難。',
    'If ppCO2 >= 3.0 mmHg: activate backup CDRA scrubber and verify cabin airflow fans.': '若 ppCO2 ≥ 3.0 mmHg：立即啟用備用 CDRA 除碳設備並檢查艙內循環風扇。',
    'If rapid depressurization/alarm: don emergency masks & isolate affected hatch.': '若發生快速失壓或氨氣/火警警報：立即戴上緊急呼吸面罩並隔離受影響艙門。',
    'Enforce shielded sleep-station occupancy, daily CDRA sorbent regeneration, and post-SPE CBC follow-up.': '強制乘員於具輻射遮蔽之睡眠艙休息、每日執行 CDRA 吸附床再生並追蹤風暴後 CBC 血球變化。',
    'Verify cabin CO2 with handheld backup detector immediately.': '立即使用手持備用氣體偵測器手動複核艙內 CO2 濃度。',
    'Switch telemetry to backup CO2 sensor and clean MCA inlet filter.': '切換遙測至備用 CO2 感測器並清潔 MCA 進氣過濾網。',
    'Calibrate MCA zero-gas reference monthly.': '每月定期執行 MCA 零點標準氣體校正。',

    'Run 30-min LBNP at -20 mmHg to reduce cephalad venous stasis.': '執行 30 分鐘 -20 mmHg 下半身負壓 (LBNP) 訓練，以減輕頭部靜脈血液鬱積。',
    'Hydrate +500 mL electrolyte solution and repeat resting vitals in 12h.': '立即補充 500 mL 電解質液並於 12 小時後複檢靜息生命徵象。',
    'Shift CEVIS to Zone 2 steady aerobic conditioning (4x/week) and add LBNP 3x/week.': '將 CEVIS 調整為第 2 區間穩態有氧訓練（每週 4 次）並增加每週 3 次 LBNP 訓練。',
    'STOP all strenuous E4D & high-intensity CEVIS exercise immediately.': '立即停止所有高強度 E4D 重訓與高強度 CEVIS 間歇騎乘。',
    'Perform Ultrasound 2 bilateral IJV compression sweep + 12-lead ECG capture.': '立即以 Ultrasound 2 掃描雙側頸內靜脈 (IJV) 壓迫試驗並擷取 12 導程心電圖。',
    'If IJV thrombus/reversed flow: initiate onboard anticoagulation checklist & LBNP -25 mmHg.': '若確認 IJV 血栓或逆流：啟動隨艦抗凝血處置清單並執行 -25 mmHg LBNP。',
    'Suspend HIIT for 14 days; daily resting ECG, potassium monitoring, and LBNP orthostatic conditioning.': '暫停高強度間歇訓練 14 天；每日追蹤靜息心電圖、血鉀濃度並執行 LBNP 耐受調整。',
    'Re-seat Bio-Monitor chest strap and capture clean 60s ECG.': '重新固定 Bio-Monitor 胸帶電極並擷取一段乾淨的 60 秒靜息心電圖。',
    'Re-wet Bio-Monitor ECG strap and repeat resting recording.': '潤濕 Bio-Monitor 心電胸帶電極後重新執行靜息心電圖紀錄。',
    'Inspect Bio-Monitor electrode pads during weekly maintenance.': '於每週設備維護時檢查 Bio-Monitor 電極片接觸狀況。',

    'Increase E4D squat/deadlift load +5% with faster concentric loading rate to push S_bone >= 0.90 and VBT loss into 20-30%.': '將 E4D 深蹲/硬舉負荷提升 +5% 並加快向心發力速度，使骨骼刺激指數 S_bone ≥ 0.90 且 VBT 落在 20–30%。',
    'Add 1 extra unilateral heel-raise / posterior-chain set and confirm protein >= 1.6 g/kg/day.': '增加 1 組單腳提踵與後側鏈訓練，並確保每日蛋白質攝取 ≥ 1.6 g/kg。',
    'Schedule follow-up Ultrasound 2 thigh/calf & E4D check in 72 hours.': '安排 72 小時後複檢 Ultrasound 2 大小腿截面積與 E4D 訓練數據。',
    '+5% E4D squat/deadlift load progression with higher loading rate; repeat Ultrasound CSA & bone markers in 72h–7d.': '將 E4D 深蹲/硬舉負荷漸進增加 +5% 並提高發力率；於 72 小時至 7 天內複檢超音波肌肉截面積與骨代謝指標。',
    'STOP the fatigued E4D set immediately if VBT velocity loss > 30% and alert ground Flight Surgeon.': '若 VBT 速度衰減超過 30% 請立即停止該組訓練，並通報地面航太醫師。',
    'Shift next session to controlled eccentric/hypertrophy loading (cap VBT loss <= 25%) and verify Cardio/Immune clearance.': '下次訓練改為受控離心與肌肥大負荷（速度衰減上限 ≤ 25%），並確認心血管與免疫系統已解除紅燈管制。',
    'Verify hydration >= 2.8 L/day, +20g post-workout whey/leucine, and Vitamin D3/Ca intake; repeat Ultrasound 2 scan within 24h.': '確認每日飲水 ≥ 2.8 公升、運動後補充 20g 乳清蛋白/白胺酸與維生素 D3/鈣片，並於 24 小時內複掃超音波。',
    '24h ground alert + 4-week progressive lower-limb hypertrophy block, +350 kcal/day protein surplus, and 14-day Bio-Analyzer CTX/NTX & Ultrasound CSA re-evaluation.': '發出 24 小時地面醫療通報＋啟動 4 週下肢肌肥大強化週期、每日增加 +350 kcal 高蛋白熱量盈餘，並於 14 天後重測 CTX/NTX 與肌肉截面積。',
    'Sensor QC rejected implausible value(s). Recalibrate and repeat measurement immediately.': 'Layer 0 品質閘門攔截到異常讀數，請立即重新校正並重測。',
    'Check E4D cable pin lock and Ultrasound 2 probe contact.': '檢查 E4D 拉索插銷鎖定與 Ultrasound 2 探頭貼合度。',
    'Re-measure immediately (next_measurement_in_hours = 0) before starting heavy sets.': '在進行大重量訓練前請立即重測（複檢間隔 = 0 小時）。',
    'Verify E4D & Ultrasound 2 calibration checklist prior to each session.': '每次訓練前請依檢核表確認 E4D 與 Ultrasound 2 校正狀態。',

    'Equip Space Anticipation Glasses if near-vision blur occurs (+0.75 D shift).': '若出現近距離視力模糊（遠視偏移 ≥ +0.75 D），請立即換戴太空調節眼鏡。',
    'Schedule bi-weekly Mini OCT & cross-check cabin ppCO2 levels.': '安排每兩週一次 Mini OCT 追蹤並交叉確認艙內 ppCO2 濃度。',
    'Increase Mini OCT cadence to every 14 days and add 3x/week LBNP fluid unloading.': '將 Mini OCT 檢查頻率提高至每 14 天一次，並加入每週 3 次 LBNP 體液減壓訓練。',
    'Notify Flight Surgeon immediately for Grade-2+ SANS / foveal fold protocol.': '立即通報地面航太醫師啟動 Grade-2+ SANS／黃斑皺摺處置程序。',
    'Run 45-min LBNP at -25 mmHg and keep sleeping torso slightly elevated / avoid head-down posture.': '執行 45 分鐘 -25 mmHg LBNP 減壓，睡眠時維持軀幹微墊高並避免頭低腳高姿勢。',
    'Repeat Mini OCT & Amsler grid check in 24 hours; verify cabin ppCO2 < 2.0 mmHg.': '於 24 小時後複測 Mini OCT 與阿姆斯勒方格表，並確認艙內 ppCO2 < 2.0 mmHg。',
    'Weekly Mini OCT + Ultrasound ONSD surveillance + daily LBNP fluid-shift countermeasure for 30 days.': '連續 30 天執行每週 Mini OCT ＋ 超音波 ONSD 監測 ＋ 每日 LBNP 體液轉移對抗訓練。',
    'Re-acquire registered Mini OCT scan immediately.': '請立即重新拍攝已對位基準之 Mini OCT 眼底掃描。',
    'Repeat Mini OCT scan until quality score >= 6.0 and baseline registration passes.': '重新執行 Mini OCT 掃描直到影像品質分數 ≥ 6.0 且基準對位成功。',
    'Verify optical window cleanliness on Mini OCT monthly.': '每月清潔並檢查 Mini OCT 光學鏡頭視窗。',

    'Schedule Bio-Analyzer CBC check in 48 hours (especially if SPE alert triggered).': '安排 48 小時後執行 Bio-Analyzer CBC 血球追蹤（尤其在太陽風暴警報觸發後）。',
    'Boost fluid intake to >= 2500 mL/day and prioritize >= 7.5h sleep.': '提升每日飲水量至 ≥ 2500 mL，並確保每晚睡眠 ≥ 7.5 小時。',
    'Weekly saliva viral qPCR & sleep/stress load reduction over next 14 days.': '未來 14 天每週執行一次唾液病毒 qPCR 檢測並降低睡眠/心理負荷。',
    'Isolate crew member in sleep quarters if fever >= 38.0 C or active VZV skin vesicles present.': '若發燒 ≥ 38.0°C 或出現水痘皮膚水泡，立即於個人睡眠艙進行醫療隔離。',
    'Initiate onboard Valacyclovir / broad-spectrum medical kit protocol per offline Flight Surgeon guide.': '依離線航太醫療手冊啟動隨艦抗病毒藥物 (Valacyclovir) 或廣效醫療包治療程序。',
    'Run Bio-Analyzer CBC & hydration log every 12h (mandatory 48h post-SPE if solar storm active).': '每 12 小時追蹤一次 Bio-Analyzer CBC 與飲水紀錄（若發生太陽風暴，48 小時後必須強制抽血複檢）。',
    'Suspend strenuous exercise; 14-day antiviral/recovery course + sleep optimization >= 8h/night.': '暫停劇烈體能訓練；執行 14 天抗病毒/康復療程並確保每晚睡眠 ≥ 8 小時。',
    'Re-run Bio-Analyzer CBC immediately to clear QC warning.': '請立即重測 Bio-Analyzer CBC 以排除樣本分選異常警示。',
    'Re-run Bio-Analyzer CBC with fresh cartridge.': '更換全新檢測卡匣並重新執行 Bio-Analyzer CBC。',
    'Inspect Bio-Analyzer optical reader during weekly maintenance.': '於每週設備保養時檢查 Bio-Analyzer 光學判讀頭。',

    'Hold high-load E4D squats/deadlifts until Cardiovascular & Immune return to YELLOW/GREEN.': '在心血管與免疫系統恢復至黃燈或綠燈前，持續暫停高負荷 E4D 深蹲與硬舉訓練。',

    // Role 6: 17-Card Cabin Environment corpus (RAD-01..03, ACO-01..03, ATM-01..07, ISO-01..04)
    'Execute Layer-0 QC checks across DOSTEL/GOES radiation, Type-1 SLM/dosimeter/OOHA acoustics, MCA/CDRA/THC/AQM/TOCA/microbial habitat loops, and Actiwatch/PVT-B/Bedford behavioral assays.': '依序執行 Layer 0 品質檢核：DOSTEL/GOES 輻射偵測、Type-1 聲壓計/個人噪音計/OOHA 聽力測驗、MCA/CDRA/THC/AQM/TOCA 氣水微生物環控迴路，以及 Actiwatch 睡眠、PVT-B 警覺度與 Bedford 工作負荷量測。',
    'Integrates 17 closed-habitat, radiation, acoustic, and circadian-isolation cards across 3 NASA RIDGE hazards to provide autonomous offline decision support (all Red actions end with a human decision).': '整合 17 張封閉艙段環控、太空輻射、聲學噪音與生理節律監測卡（涵蓋 NASA 輻射/孤立/封閉環境三大危害），提供離線自主醫療決策支援（所有紅燈處置均保留人工最終確認）。',
    'All 17 Radiation, Acoustics, Atmosphere, and Isolation cards nominal; continue scheduled monitoring.': '全部 17 項輻射、聲學、大氣水質環控與孤立節律監測卡皆正常，請持續定期監測。',

    '[RAD-01] Verify DOSTEL/IV-TEPC detector health and await next non-SAA 1-h mean.': '[RAD-01 區域劑量] 檢查 DOSTEL/IV-TEPC 偵測器健康狀態，並等待下一個非南大西洋異常區 (non-SAA) 1 小時均值。',
    '[RAD-01] Verify non-SAA orbital position and cross-check RAD-03 proton flux.': '[RAD-01 區域劑量] 確認軌道非處於南大西洋異常區 (SAA) 並交叉比對 RAD-03 太陽質子通量。',
    '[RAD-01] Relocate prolonged work tasks to higher-shielding module locations.': '[RAD-01 區域劑量] 將長時間作業移往具較高輻射遮蔽厚度之艙段執行。',
    '[RAD-01] Move to the most shielded area; in Orion, line cabin walls with stowage.': '[RAD-01 區域劑量] 立即移動至遮蔽最完善區域；若於獵戶座艙，以儲物包覆蓋艙壁加強屏蔽。',
    '[RAD-01] Terminate EVA immediately and notify flight surgeon (human decision).': '[RAD-01 區域劑量] 立即終止艙外活動 (EVA) 並通報航太醫師進行人工決策。',
    '[RAD-01] ALARA; missions > 6 months: >= 20 g/cm² shielding plus 10 cm water-equivalent storm shelter in crew quarters.': '[RAD-01 長期處方] 落實 ALARA 最小合理暴露原則；超過 6 個月任務須維持 ≥20 g/cm² 屏蔽與睡眠區 10 cm 等效水牆避難空間。',
    '[RAD-01] ALARA; missions > 6 months: >= 20 g/cm² shielding plus a 10 cm water-equivalent storm shelter in crew quarters (rearranged water containers).': '[RAD-01 長期處方] 落實 ALARA 原則；超過 6 個月任務於乘員艙維持 ≥20 g/cm² 屏蔽與 10 cm 水箱風暴掩體。',

    '[RAD-02] Complete 24-h module location log and sync Crew Passive/Active Dosimeter.': '[RAD-02 個人劑量] 補齊 24 小時艙段停留紀錄並同步乘員主/被動輻射劑量計。',
    '[RAD-02] Increase sleep/work hours in high-shielding modules and review remaining EVA dose budget.': '[RAD-02 個人劑量] 增加高屏蔽艙段內之睡眠與工作時數，並重新審查剩餘 EVA 劑量預算。',
    '[RAD-02] Restrict unshielded module/EVA exposure immediately; flight surgeon & mission management review required (human decision).': '[RAD-02 個人劑量] 立即限制無遮蔽艙段停留與艙外活動；須經航太醫師與任務管理層人工審查。',
    '[RAD-02] Log daily module occupancy and sleep inside higher-shielded crew quarters.': '[RAD-02 長期處方] 每日記錄艙段分佈並於高屏蔽睡眠區就寢。',
    '[RAD-02] Enforce ALARA scheduling, polyethylene/water sleep-station shielding, and personal active dosimeter cross-checks.': '[RAD-02 長期處方] 執行 ALARA 排程、強化睡眠站聚乙烯/水層遮蔽並定期交叉核對主動式個人劑量計。',

    '[RAD-03] Switch to GOES secondary satellite / DONKI backup feed; verify local RAD-01 DOSTEL/HERA.': '[RAD-03 太陽風暴] 切換至 GOES 備用衛星／DONKI 備援資料源，並檢核本地 RAD-01 DOSTEL/HERA 讀數。',
    '[RAD-03] Review EVA schedule and pre-position storm shelter water/stowage supplies.': '[RAD-03 太陽風暴] 檢視艙外活動排程並預先於輻射掩體就位飲水與儲物屏蔽物資。',
    '[RAD-03] Increase RAD-01 evaluation to every 5 min.': '[RAD-03 太陽風暴] 將 RAD-01 輻射評估頻率提高至每 5 分鐘一次。',
    '[RAD-03] Move crew to the most shielded storm shelter area immediately; terminate any planned/ongoing EVA.': '[RAD-03 太陽風暴] 立即將全體乘員撤離至遮蔽最強之風暴掩體；終止任何進行中或預定之 EVA。',
    '[RAD-03] Increase RAD-01 telemetry readout to 5-min cadence and notify ground & flight surgeon for human decision.': '[RAD-03 太陽風暴] 將 RAD-01 遙測頻率提升至 5 分鐘並通報地面與航太醫師進行人工決策。',
    '[RAD-03] Maintain dual GOES primary/secondary ground-to-ship telemetry and local HERA alerting.': '[RAD-03 長期處方] 維持 GOES 主/備雙衛星地面遙測與艦上本地 HERA 自主預警系統。',
    '[RAD-03] Maintain automated SWPC GOES primary/secondary feed + onboard HERA local trigger for deep-space comm-delay autonomy.': '[RAD-03 長期處方] 維持自動化 SWPC GOES 雙通道與本地 HERA 觸發機制，確保深空通訊延遲下的自主防輻射能力。',

    '[ACO-01] Perform field acoustic calibrator check and repeat octave-band survey.': '[ACO-01 艙內噪音] 使用聲學校正器檢核測音儀後，重新執行八音度頻帶量測。',
    '[ACO-01] Inspect fan mufflers/vibration isolators and use hearing protection during extended tasks in module.': '[ACO-01 艙內噪音] 檢查風扇消音器與減震墊；於該艙段長時間作業時請配戴護耳裝備。',
    '[ACO-01] Don hearing protection immediately, isolate noisy rack/pump, notify ground & flight surgeon (human decision).': '[ACO-01 艙內噪音] 立即戴上護耳裝備、隔離高噪音機櫃或幫浦，並通報地面與航太醫師。',
    '[ACO-01] Verify SLM calibration before and after every monthly acoustic survey.': '[ACO-01 長期處方] 每月聲壓量測前後皆須執行聲壓計 (SLM) 現場校正。',
    '[ACO-01] Maintain acoustic blankets, clean fan intake screens, and enforce NC-50 work / NC-40 sleep envelopes.': '[ACO-01 長期處方] 維護隔音毯與風扇進氣濾網，落實工作區 NC-50、睡眠區 NC-40 噪音規範。',

    '[ACO-02] Repeat 24-h personal noise dosimetry session ensuring >=20 h uncovered wear.': '[ACO-02 個人噪音] 重新執行 24 小時個人噪音劑量佩戴，確保未遮蔽有效佩戴時間 ≥20 小時。',
    '[ACO-02] Use sleep earplugs / ANR headset during noisy work and inspect sleep-station ventilation.': '[ACO-02 個人噪音] 高噪音作業配戴降噪耳機/耳塞並檢查睡眠艙通風口噪音。',
    '[ACO-02] Mandate ANR hearing protection, quiet sleep quarters, schedule ACO-03 audiogram & flight surgeon review (human decision).': '[ACO-02 個人噪音] 強制配戴主動降噪護耳設備、改至安靜睡眠區休息，並安排 ACO-03 聽力檢查與醫師審查。',
    '[ACO-02] Schedule 24-h personal noise dosimetry every 60 mission days.': '[ACO-02 長期處方] 每 60 任務日定期執行一次 24 小時個人噪音劑量監測。',
    '[ACO-02] Perform 24-h personal dosimetry every 60 days; wear hearing protection for tasks >80 dBA.': '[ACO-02 長期處方] 每 60 天執行個人噪音監測；遇 >80 dBA 作業須強制配戴聽力防護。',

    '[ACO-03] Repeat pure-tone audiometry inside quiet NC-40 berth and confirm within-frequency repeatability <=10 dB.': '[ACO-03 聽力閾值] 於 NC-40 安靜睡眠艙內重測純音聽力，確認同頻率重測誤差 ≤10 dB。',
    '[ACO-03] Reduce noise exposure, verify headset volume, and schedule follow-up retest audiogram.': '[ACO-03 聽力閾值] 降低噪音暴露、檢核通訊耳機音量上限並排程複測聽力圖。',
    '[ACO-03] Enforce auditory rest + ANR hearing protection; notify ground & flight surgeon for clinical human decision.': '[ACO-03 聽力閾值] 強制執行聽覺休息與主動降噪防護，並通報地面與航太醫師進行臨床評估。',
    '[ACO-03] Perform periodic OOHA/KUDUwave hearing checks in quiet sleep station.': '[ACO-03 長期處方] 定期於安靜睡眠站內執行 OOHA/KUDUwave 聽力檢測。',
    '[ACO-03] Conduct periodic KUDUwave/OOHA audiograms and cross-reference with ACO-01/ACO-02 noise logs.': '[ACO-03 長期處方] 定期執行聽力檢查並與 ACO-01/ACO-02 噪音暴露紀錄交叉比對。',

    '[ATM-01] Cross-check primary MCA IR bench against portable CO2 meter and backup CDRA sensor immediately.': '[ATM-01 艙內 CO2] 立即以手持式 CO2 偵測器與備用 CDRA 感測器比對主 MCA 紅外線讀數。',
    '[ATM-01] Check CDRA and ventilation, prompt headache/vision self-report.': '[ATM-01 艙內 CO2] 檢查 CDRA 除碳器與通風循環，並要求乘員回報是否有頭痛或視力模糊。',
    '[ATM-01] Increase CO2 removal or move crew to a better-ventilated module; notify flight surgeon if headache is reported (human decision).': '[ATM-01 艙內 CO2] 提高除碳效率或將乘員移至通風較佳艙段；若有頭痛症狀立即通報航太醫師。',
    '[ATM-01] Perform scheduled MCA zero/span calibration and verify inter-module air mixing fans.': '[ATM-01 長期處方] 定期執行 MCA 零點/跨距校正並確認跨艙氣體混合風扇運轉正常。',
    '[ATM-01] Maintain 7-day rolling ppCO2 < 2.5 mmHg, clean air diffusers, and avoid stagnant sleep-berth CO2 pockets.': '[ATM-01 長期處方] 維持 7 日移動平均 ppCO2 < 2.5 mmHg，定期清潔風口避免睡眠艙二氧化碳積聚。',

    '[ATM-02] Verify dual cabin pressure transducers and MCA O2 partial pressure bench.': '[ATM-02 氣壓與氧氣] 檢核雙重艙壓感測器一致性與 MCA 氧分壓分析儀狀態。',
    '[ATM-02] Inspect N2/O2 pressure control assembly (PCA) valves and check hull hatch seals with ultrasonic leak detector.': '[ATM-02 氣壓與氧氣] 檢查 N2/O2 壓力控制閥 (PCA) 並以超音波測漏儀巡檢艙門氣密墊片。',
    '[ATM-02] Execute depressurization emergency procedure; notify ground and flight surgeon immediately (human decision).': '[ATM-02 氣壓與氧氣] 立即執行失壓/低氧緊急應變程序並通報地面與航太醫師。',
    '[ATM-02] Maintain redundant pressure transducers calibrated to 101.3 kPa nominal setpoint.': '[ATM-02 長期處方] 維持備援壓力感測器校正於 101.3 kPa 標準艙壓設定點。',
    '[ATM-02] Maintain 101.3 kPa total pressure, PIO2 139–168 mmHg, O2 <= 23.5%, and unobstructed hatch seals.': '[ATM-02 長期處方] 維持 101.3 kPa 總壓、PIO2 139–168 mmHg、氧濃度 ≤23.5% 與艙門密封清潔。',

    '[ATM-03] Cross-check THC sensor with portable psychrometer and verify fan airflow across sensor.': '[ATM-03 溫濕度] 使用可攜式乾濕球溫度計比對 THC 感測器，並確認探頭氣流暢通。',
    '[ATM-03] Keep cabin within 20–25 °C and 30–60% RH performance zone.': '[ATM-03 長期處方] 將艙內溫濕度維持於 20–25 °C 與 30–60% 相對濕度舒適效能區間。',
    '[ATM-03] Maintain THC performance zone (20–25 °C, 30–60% RH) to prevent heat stress and surface condensation.': '[ATM-03 長期處方] 維持 THC 溫濕度目標區間（20–25 °C、30–60% RH）以防熱壓力與艙壁結露。',

    '[ATM-04] Run AQM calibration check and verify cabin air with colorimetric Drager tubes if odor noticed.': '[ATM-04 揮發氣體] 執行 AQM 氣相層析校正檢核；若聞到異味立即以 Drager 檢知管採樣。',
    '[ATM-04] Verify TCCS charcoal bed life and AQM carrier gas supply.': '[ATM-04 長期處方] 定期確認 TCCS 活性碳濾床壽命與 AQM 載氣鋼瓶存量。',
    '[ATM-04] Enforce strict flight material off-gassing screening, log alcohol-wipe usage, and maintain TCCS beds.': '[ATM-04 長期處方] 嚴格控管酬載除氣篩檢、記錄酒精擦拭用量並維護 TCCS 除毒濾床。',
    '[ATM-04] Maintain TCCS charcoal/catalyst beds, AQM internal check standards, and accessible PBA respirators.': '[ATM-04 長期處方] 維護 TCCS 活性碳/觸媒床、AQM 內校標準與隨手可得之緊急呼吸器 (PBA)。'
  };

  function zhText(raw) {
    if (raw === null || raw === undefined) return '';
    const s = String(raw).trim();
    if (state.lang !== 'zh') return s;
    if (EXACT_ZH[s]) return EXACT_ZH[s];

    let out = s;
    // Dynamic 17-card summary note from Role 6
    out = out.replace(/^17-Card Status: GREEN$/, '17 項環控與輻射監測卡：全數正常 GREEN');
    out = out.replace(/^17-Card Status: (YELLOW|RED|NO_DATA) \| ([^=]+)=(.+)$/, (_, st, key, list) => {
      const lbl = st === 'RED' ? '危急 RED' : (st === 'YELLOW' ? '預警 YELLOW' : '品質檢核異常 NO_DATA/QC');
      return `17 項環控監測卡：${lbl}｜異常卡片：${list}`;
    });
    // Generic card prefixes [ATM-05..07] / [ISO-01..04]
    out = out.replace(/^\[(ATM-0[567]|ISO-0[1-4])\]\s*/, '[$1] ');
    out = out.replace(/^cabin_environment\.spe_alert -> immune_metabolic\.spe_event_flag$/, '艙內輻射風暴警報 (SPE) ➔ 免疫代謝模組（觸發 48h 淋巴球複檢）');
    out = out.replace(/^cabin_environment\.ppco2_1h_mmHg \(([^)]+)\) -> neuro_ocular$/, '艙內 ppCO2 濃度 ($1 mmHg) ➔ 神經眼壓 SANS 協同判讀');
    out = out.replace(/^CO2-SANS SYNERGY ALERT: Cabin ppCO2 \(([^)]+)\) elevates intracranial venous congestion risk alongside Neuro-Ocular findings\. Prioritize CDRA scrubber inspection and avoid head-down tilt or prolonged supine posture\.$/, 'CO2-SANS 協同風險警報：艙內二氧化碳分壓 ($1) 與神經眼壓異常同時發生，將顯著提高顱內靜脈鬱積風險。請優先檢查 CDRA 除碳器並避免頭低位姿勢。');
    out = out.replace(/^SAFETY OVERRIDE: Heavy E4D axial resistance loading & maximal CEVIS intervals SUSPENDED due to (.+)\. Switch to light passive ROM \/ hydration monitoring only\.$/, '安全衝突強制介入：由於 $1，系統已自動暫停高負荷 E4D 軸向抗阻與高強度 CEVIS 訓練，僅保留輕度關節活動與水分補充監測。');
    out = out.replace(/^SPE SHELTER OVERRIDE: Relocate crew to Water Wall \/ storm shelter immediately\. Defer non-essential E4D\/CEVIS sessions and schedule mandatory 48h post-SPE CBC lymphocyte check\.$/, '太陽質子風暴避難介入：立即將乘員撤離至 Water Wall 輻射掩體。延後非必要體能訓練並自動排入 48 小時後 CBC 淋巴球追蹤。');
    out = out.replace(/Cardiovascular RED \(arrhythmia \/ IJV thrombosis \/ hemodynamic alert\)/g, '心血管系統紅燈（心律不整 / 頸內靜脈血栓 / 血流動力警示）');
    out = out.replace(/Immune RED \(fever \/ acute inflammatory or viral reactivation alert\)/g, '免疫系統紅燈（發燒 / 急性發炎或病毒再活化警示）');

    out = out.replace(/^ppCO2 ([\d.]+) mmHg, Proton ([\d.]+) pfu \(SPE=(True|False)\), LEQ8 ([\d.]+) dBA, Sleep ([\d.]+)h\.$/, (_, a, b, c, d, e) => `艙內 CO2 ${a} mmHg｜質子通量 ${b} pfu (風暴=${c === 'True' ? '是' : '否'})｜8h噪音 ${d} dBA｜睡眠 ${e} 小時`);
    out = out.replace(/^Rest HR ([\d.]+) bpm, SpO2 ([\d.]+)%, IJV '([^']+)', PVC ([\d.]+)%\.$/, (_, a, b, c, d) => `靜息心率 ${a} bpm｜血氧 ${b}%｜頸靜脈血流 '${c === 'forward' ? '順向' : (c === 'stagnant' ? '滯留' : '逆流')}'｜PVC ${d}%`);
    out = out.replace(/^Rest HR ([\d.]+) bpm, BP ([\d.]+\/[\d.]+), SpO2 ([\d.]+)%, PVC ([\d.]+)%, IJV '([^']+)', %DeltaPV ([+-]?[\d.]+)%\.(?: \| (.+))?$/, (_, hr, bp, spo2, pvc, ijv, pv, corr) => {
      const ijvZh = ijv === 'forward' ? '順向' : (ijv === 'stagnant' ? '滯留' : '逆流');
      const base = `靜息心率 ${hr} bpm｜血壓 ${bp}｜血氧 ${spo2}%｜PVC ${pvc}%｜頸靜脈 '${ijvZh}'｜血漿容量 ${pv}%`;
      return corr ? `${base}｜${zhText(corr)}` : base;
    });
    out = out.replace(/^PE \/ HYPOXIA CORRELATION \(M3\+M4->M9\): Low SpO2 \+ Tachypnea \(>25\/min\) [—-] perform immediate bilateral IJV Ultrasound 2 clot check and verify cabin O2\/ppCO2\.$/, '肺栓塞 / 低血氧關聯警示 (M3+M4→M9)：低血氧併發呼吸急促 (>25次/分) — 立即執行雙側頸內靜脈 (IJV) 超音波血栓檢查並核對艙內氧氣/ppCO2。');
    out = out.replace(/^ARRHYTHMIA-ELECTROLYTE CORRELATION \(M5\+M11\): Elevated PVC burden \(([\d.]+)%\) paired with hypokalemia \(K\+=([\d.]+) mmol\/L\) [—-] administer oral KCl and repeat ECG\.$/, '心律不整-電解質關聯警示 (M5+M11)：心室早搏負荷偏高 ($1%) 併發低血鉀 (K+=$2 mmol/L) — 給予口服氯化鉀 (KCl) 並複測心電圖。');
    out = out.replace(/^RHYTHM-ELECTROLYTE CHECK \(M5->M11\): Elevated PVC burden \(([\d.]+)%\) [—-] verify serum K\+ >= 3\.5 mmol\/L before exercise\.$/, '心律-電解質檢核 (M5→M11)：心室早搏負荷偏高 ($1%) — 運動前請先確認血清鉀 K+ ≥ 3.5 mmol/L。');
    out = out.replace(/^ORTHOSTATIC-HYPOVOLEMIA CORRELATION \(M6\+M10\): Orthostatic intolerance paired with ([+-]?[\d.]+)% plasma volume loss [—-] initiate oral salt\+fluid loading\.$/, '直立不耐-低血容關聯警示 (M6+M10)：直立耐受不良併發血漿容量流失 ($1%) — 立即啟動口服鹽水與液體補充。');
    out = out.replace(/^S_bone=([\d.]+), VBT=([\d.]+)%, Thigh=([^,]+), Calf=([^,]+), CTX=([^,]+), Est Hip Loss=([^\s]+)\.$/, (_, a, b, c, d, e, f) => `骨骼刺激 S_bone=${a}｜速度衰減 ${b}%｜大腿 ${c}｜小腿 ${d}｜骨吸收 CTX ${e}｜推估髖骨流失 ${f}`);
    out = out.replace(/^(OD|OS) delta TRT \+([\d.]+) um, delta V_ONH \+([\d.]+) mm3, ONSD ([\d.]+) mm(?: \| Cross-context cabin ppCO2=([\d.]+) mmHg)?\.$/, (_, eye, trt, vonh, onsd, co2) => `${eye} 眼視網膜 ΔTRT +${trt} µm｜視神經盤 ΔV_ONH +${vonh} mm³｜ONSD ${onsd} mm` + (co2 ? `｜連動艙內 ppCO2=${co2} mmHg` : ''));
    out = out.replace(/^Temp ([\d.]+) C, Lymph ([\d.]+) \(([^)]+)\), VZV ([\d.]+), SPE=(True|False)\.$/, (_, temp, ly, dp, vzv, spe) => `體溫 ${temp}°C｜淋巴球 ${ly} (${dp})｜水痘病毒 VZV ${vzv}｜風暴警報=${spe === 'True' ? '是' : '否'}`);
    out = out.replace(/^MCA CO2 sensor flatlined for ([\d.]+)h \(>=24h stuck-sensor QC fault\)\.$/, 'MCA 二氧化碳感測器讀數已凍結 $1 小時（觸發 ≥24h 故障閘門）。');
    out = out.replace(/^Bio-Monitor ECG \/ PTT lead quality below 0\.50 threshold\.$/, 'Bio-Monitor 心電/脈搏波導極訊號品質低於 0.50 門檻，請重新貼合電極。');
    out = out.replace(/^Mini OCT QC failed for (OD|OS) \(score=([\d.]+), registered=(True|False)\)\.$/, '$1 眼 Mini OCT 品質檢核未通過（品質分=$2，對位=$3），請重新掃描。');
    out = out.replace(/^Bio-Analyzer QC failed: Neutrophil fraction ([\d.]+)% < 10% \(possible sample mis-sort\)\.$/, 'Bio-Analyzer 品質檢核失敗：嗜中性球比例僅 $1% (<10%)，疑為採血分選異常。');
    out = out.replace(/^Layer 0 QC Gatekeeper rejected telemetry:/, 'Layer 0 品質閘門已攔截異常遙測：');
    return out;
  }

  function metricLabel(name) {
    if (state.lang !== 'zh') return name;
    return METRIC_ZH[name] || name;
  }

  function layerLabel(decidedBy) {
    if (state.lang !== 'zh') return decidedBy || 'rule';
    return LAYER_ZH[decidedBy] || decidedBy || 'rule';
  }

  function ruleLabel(rule) {
    if (state.lang !== 'zh') return rule;
    const map = {
      HALT_HEAVY_EXERCISE_ON_CARDIO_OR_IMMUNE_RED: '安全衝突強制暫停重訓 (心血管/免疫紅燈)',
      SPE_SHELTER_AND_48H_LYMPHOCYTE_CHECK: '太陽風暴避難與 48h 淋巴球複檢連動',
      CO2_SANS_SYNERGY_MITIGATION: 'CO2 與 SANS 眼壓協同風險處置'
    };
    return map[rule] || rule;
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

  const DRAWER_ZH = {
    ppco2_1h_mmHg: '艙內 1 小時二氧化碳分壓 (mmHg)',
    proton_flux_10mev_pfu: 'GOES ≥10MeV 質子通量 (pfu)',
    crew_leq8_dBA: '乘員 8 小時噪音暴露 (dBA)',
    sleep_tst_h: 'Actiwatch 睡眠時數 (小時)',
    spe_alert: 'SPE 太陽質子風暴警報',
    rest_hr_bpm: '靜息心率 (bpm)',
    spo2_pct: '周邊血氧飽和度 SpO2 (%)',
    pvc_burden_pct: 'Holter 24小時 PVC 負荷 (%)',
    ijv_flow: '頸內靜脈 (IJV) 超音波血流',
    ijv_thrombus: '偵測到頸內靜脈血栓',
    csa_thigh_cm2: '大腿肌肉截面積 CSA (cm²)',
    velocity_loss_pct: 'E4D 深蹲速度衰減率 (%)',
    ctx: '骨吸收指標 CTX (ng/mL)',
    body_mass_kg: 'SLAMMD 微重力體重 (kg)',
    delta_trt_um: 'Mini OCT 視網膜厚度變化 ΔTRT (µm)',
    delta_v_onh_mm3: '視神經盤體積變化 ΔV_ONH (mm³)',
    onsd_mm: '超音波視神經鞘直徑 ONSD (mm)',
    sph_eq_shift_d: '遠視屈光偏移量 (Diopters)',
    folds_foveal: '出現黃斑部/脈絡膜皺摺',
    temp_c: '口腔體溫 (°C)',
    lymph: '淋巴球計數 (10⁹/L)',
    saliva_vzv: '唾液水痘病毒 VZV DNA (copies/mL)',
    hydration_ml: '24小時飲水量 (mL)'
  };

  const FLOW_OPT_ZH = {
    forward: '順向 (FORWARD)',
    stagnant: '滯留 (STAGNANT)',
    reversed: '逆流 (REVERSED)'
  };

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
      const lbl = state.lang === 'zh' ? (DRAWER_ZH[f.key] || f.label) : f.label;
      if (f.type === 'checkbox') {
        return `
          <label class="field-group" style="flex-direction:row;align-items:center;gap:9px;padding-top:14px;cursor:pointer;">
            <input type="checkbox" data-input-key="${f.key}" data-input-type="checkbox" ${val ? 'checked' : ''} />
            <span class="field-label" style="font-size:12px;color:#e2e8f0;">${esc(lbl)}</span>
          </label>
        `;
      }
      if (f.type === 'select') {
        const opts = f.options.map(o => {
          const optTxt = state.lang === 'zh' ? (FLOW_OPT_ZH[o] || o.toUpperCase()) : o.toUpperCase();
          return `<option value="${o}" ${val === o ? 'selected' : ''}>${esc(optTxt)}</option>`;
        }).join('');
        return `
          <div class="field-group">
            <span class="field-label">${esc(lbl)}</span>
            <select class="field-select" data-input-key="${f.key}" data-input-type="select">${opts}</select>
          </div>
        `;
      }
      return `
        <div class="field-group">
          <div class="field-label">
            <span>${esc(lbl)}</span>
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
      const srcBadge = m && m.data_source === 'REAL'
        ? t('src_real')
        : (m && m.data_source === 'SIMULATED' ? t('src_sim') : (m ? m.data_source : t('src_demo')));
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
        : `${t('layer_prefix')} ${layerLabel(m.decided_by)}`;
      return `
        <div class="metric-card ${idx === state.selectedMetricIdx ? 'active' : ''}" data-metric-idx="${idx}">
          <div class="m-top">
            <span class="m-name" title="${esc(metricLabel(m.metric_name))}">${esc(metricLabel(m.metric_name))}</span>
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
      guideContentHtml = `<div>${esc(zhText(g.how_to_measure))}</div>`;
    } else if (state.guideTab === 'meaning') {
      guideContentHtml = `<div>${esc(zhText(g.plain_explanation))}</div>`;
    } else {
      const steps = Array.isArray(g.action_protocol) ? g.action_protocol : [g.action_protocol || 'Nominal'];
      guideContentHtml = `<ol class="protocol-list">${steps.map(s => `<li>${esc(zhText(s))}</li>`).join('')}</ol>`;
    }

    // Conflicts & cross-module signals
    const conflictsHtml = (schedule.conflicts_resolved || []).map(c => `
      <div class="conflict-banner">
        <div class="conflict-rule">⚡ ${esc(ruleLabel(c.rule))}</div>
        <div class="conflict-text">${esc(zhText(c.resolution))}</div>
      </div>
    `).join('');

    const flags = data.propagated_flags || [];
    const signalsHtml = flags.length
      ? `<div class="signal-box"><strong>${esc(t('bus_title'))}</strong>${flags.map(f => `<span>• ${esc(zhText(f))}</span>`).join('')}</div>`
      : '';

    // Timeline cards
    const timelineItems = state.planTab === 'short'
      ? (schedule.short_term_board || []).map(item => ({
          mod: item.module_id,
          status: item.status_light,
          tag: item.next_hours === 0 ? t('tag_immediate') : `T+${item.next_hours}H`,
          text: zhText(item.action)
        }))
      : (schedule.long_term_board || []).map(item => ({
          mod: item.module_id,
          status: item.status_light,
          tag: item.days_until_red !== null && item.days_until_red !== undefined ? t('tag_red_in', { d: item.days_until_red }) : t('tag_regimen'),
          text: zhText(item.adjustment)
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

              ${selMod.summary_note ? `<div class="summary-strip">${esc(zhText(selMod.summary_note))}</div>` : ''}

              <div class="metric-grid">
                ${metricTilesHtml}
              </div>

              <div class="chart-card">
                <div class="chart-hdr">
                  <span class="chart-title">
                    ${esc(t('traj_title'))} · <span style="color:#38bdf8">${esc(activeMetric ? metricLabel(activeMetric.metric_name) : '')}</span>
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
