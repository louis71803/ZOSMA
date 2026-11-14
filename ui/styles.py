"""SpaceX Crew Dragon / NASA Deep-Space HUD Stylesheet (`ui/styles.py`).

Separated into its own module so styling, glassmorphism cards, animations,
and responsive breakpoints remain clean and easy to maintain.
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
  grid-template-columns: minmax(310px, 1.05fr) minmax(390px, 1.50fr) minmax(310px, 1.12fr);
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
  gap: 13px;
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

/* ================= LEFT: HOLOGRAPHIC ANATOMY & HABITAT SCANNER ================= */
.scanner-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.view-pill-group {
  display: inline-flex;
  background: rgba(4, 9, 18, 0.85);
  border: 1px solid rgba(56, 189, 248, 0.22);
  border-radius: 8px;
  padding: 2px;
  gap: 2px;
}

.view-pill-btn {
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.4px;
  padding: 4px 9px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.view-pill-btn:hover {
  color: #e2e8f0;
}

.view-pill-btn.active {
  background: rgba(56, 189, 248, 0.22);
  color: #38bdf8;
  box-shadow: inset 0 0 0 1px rgba(56, 189, 248, 0.45);
}

.svg-stage {
  width: 100%;
  background: radial-gradient(circle at 50% 48%, rgba(56, 189, 248, 0.09), rgba(5, 9, 18, 0.90) 74%);
  border: 1px solid rgba(56, 189, 248, 0.18);
  border-radius: 13px;
  padding: 8px 8px 6px 8px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  position: relative;
  transition: background 0.35s ease, border-color 0.35s ease, box-shadow 0.35s ease;
}

/* Dynamic Cabin Environment stage backdrops (Deep Blue / Amber / Red) */
.svg-stage.env-stage-GREEN {
  background:
    radial-gradient(circle at 50% 45%, rgba(14, 165, 233, 0.20), rgba(6, 18, 42, 0.94) 76%);
  border-color: rgba(56, 189, 248, 0.45);
  box-shadow: inset 0 0 28px rgba(14, 165, 233, 0.14);
}

.svg-stage.env-stage-YELLOW {
  background:
    radial-gradient(circle at 50% 45%, rgba(245, 158, 11, 0.22), rgba(28, 18, 6, 0.94) 76%);
  border-color: rgba(245, 158, 11, 0.55);
  box-shadow: inset 0 0 32px rgba(245, 158, 11, 0.18);
}

.svg-stage.env-stage-RED {
  background:
    radial-gradient(circle at 50% 45%, rgba(239, 68, 68, 0.28), rgba(36, 8, 12, 0.95) 76%);
  border-color: rgba(239, 68, 68, 0.68);
  box-shadow: inset 0 0 38px rgba(239, 68, 68, 0.26), 0 0 18px rgba(239, 68, 68, 0.2);
}

.svg-stage.env-stage-QC {
  background:
    radial-gradient(circle at 50% 45%, rgba(249, 115, 22, 0.22), rgba(28, 14, 6, 0.94) 76%);
  border-color: rgba(249, 115, 22, 0.55);
}

.bio-svg {
  width: 100%;
  max-height: 360px;
  height: auto;
  display: block;
}

.scanner-caption {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 10px;
  color: #94a3b8;
  padding: 4px 6px 2px 6px;
  border-top: 1px solid rgba(148, 163, 184, 0.08);
  margin-top: 4px;
}

.hotspot-group, .organ-zone {
  cursor: pointer;
  transition: filter 0.18s ease, opacity 0.18s ease, transform 0.18s ease;
}

.hotspot-group:hover .node-core,
.organ-zone:hover {
  filter: brightness(1.32) drop-shadow(0 0 7px rgba(56, 189, 248, 0.65));
}

@keyframes pulseRing {
  0% { transform: scale(1); opacity: 0.75; }
  70% { transform: scale(1.9); opacity: 0; }
  100% { transform: scale(1.9); opacity: 0; }
}

@keyframes organAlertPulse {
  0%, 100% { opacity: 0.55; filter: drop-shadow(0 0 4px currentColor); }
  50% { opacity: 0.98; filter: drop-shadow(0 0 12px currentColor); }
}

@keyframes heartBeat {
  0%, 100% { transform: scale(1); }
  18% { transform: scale(1.09); }
  34% { transform: scale(0.98); }
  50% { transform: scale(1.06); }
}

.pulse-ring {
  transform-box: fill-box;
  transform-origin: center;
  animation: pulseRing 2.2s infinite ease-out;
}

.pulse-ring-fast {
  transform-box: fill-box;
  transform-origin: center;
  animation: pulseRing 1.1s infinite ease-out;
}

.organ-alert-RED {
  animation: organAlertPulse 1.15s infinite ease-in-out;
}

.organ-alert-YELLOW {
  animation: organAlertPulse 2.2s infinite ease-in-out;
}

.heart-anim-normal {
  transform-box: fill-box;
  transform-origin: center;
  animation: heartBeat 1.8s infinite ease-in-out;
}

.heart-anim-fast {
  transform-box: fill-box;
  transform-origin: center;
  animation: heartBeat 0.85s infinite ease-in-out;
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
