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

/* ================= OFFLINE SPACECRAFT CLOCK & REMINDER BANNER ================= */
.rtc-widget {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px;
  border-radius: 10px;
  background: rgba(5, 11, 24, 0.88);
  border: 1px solid rgba(56, 189, 248, 0.28);
  box-shadow: inset 0 0 12px rgba(56, 189, 248, 0.08);
  cursor: default;
}

.rtc-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #38bdf8;
  box-shadow: 0 0 8px #38bdf8;
  animation: pulseRing 2s infinite ease-out;
}

.rtc-readout {
  display: flex;
  flex-direction: column;
  gap: 1px;
  line-height: 1.15;
}

.rtc-time {
  font-family: 'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #f8fafc;
}

.rtc-date {
  font-size: 10px;
  letter-spacing: 0.7px;
  color: #7dd3fc;
  font-weight: 600;
}

.rtc-scale-chip {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 5px;
  background: rgba(56, 189, 248, 0.14);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.3);
}

.rtc-scale-chip.fast {
  background: rgba(245, 158, 11, 0.2);
  color: #fbbf24;
  border-color: rgba(245, 158, 11, 0.45);
}

.reminder-banner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 15px;
  border-radius: 12px;
  background: linear-gradient(90deg, rgba(245, 158, 11, 0.18), rgba(127, 29, 29, 0.28));
  border: 1px solid rgba(251, 191, 36, 0.55);
  box-shadow: 0 0 20px rgba(245, 158, 11, 0.15);
}

.reminder-banner.urgent {
  background: linear-gradient(90deg, rgba(220, 38, 38, 0.30), rgba(69, 10, 10, 0.55));
  border-color: rgba(248, 113, 113, 0.7);
  box-shadow: 0 0 22px rgba(239, 68, 68, 0.25);
}

.reminder-left {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12.5px;
  font-weight: 600;
  color: #fef3c7;
}

.reminder-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.rem-btn {
  border: 1px solid rgba(56, 189, 248, 0.45);
  background: rgba(15, 23, 42, 0.82);
  color: #e0f2fe;
  font-size: 11px;
  font-weight: 700;
  padding: 5px 10px;
  border-radius: 7px;
  cursor: pointer;
}

.rem-btn:hover {
  background: rgba(56, 189, 248, 0.22);
}

.clock-box {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: rgba(15, 23, 42, 0.72);
  border: 1px solid rgba(56, 189, 248, 0.26);
  border-radius: 10px;
  padding: 12px;
}

.clock-grid {
  display: grid;
  grid-template-columns: 1fr 1fr auto auto;
  gap: 8px;
  align-items: end;
}

@media (max-width: 600px) {
  .clock-grid {
    grid-template-columns: 1fr 1fr;
  }
}

.clock-speed-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
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
  white-space: nowrap;
  flex-shrink: 0;
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
  gap: 8px;
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
  gap: 9px;
  min-width: 0;
  flex: 1;
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
.led-REF { background: #64748b; box-shadow: none; opacity: 0.75; }

.urgent-esc-banner {
  background: linear-gradient(90deg, rgba(220, 38, 38, 0.32), rgba(127, 29, 29, 0.55));
  border: 1px solid rgba(248, 113, 113, 0.75);
  border-radius: 9px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 700;
  color: #fecaca;
  letter-spacing: 0.4px;
  box-shadow: 0 0 16px rgba(239, 68, 68, 0.25);
}

.sim-disclaimer-bar {
  font-size: 11px;
  color: #94a3b8;
  text-align: center;
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(8, 14, 28, 0.55);
  border: 1px dashed rgba(148, 163, 184, 0.16);
}

.subsys-name {
  font-size: 12.5px;
  font-weight: 600;
  color: #f1f5f9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.subsys-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.src-chip {
  font-size: 9.5px;
  letter-spacing: 0.6px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(148, 163, 184, 0.12);
  color: #94a3b8;
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}

.src-chip-real {
  background: rgba(16, 185, 129, 0.14);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.28);
}

.src-chip-sim {
  background: rgba(148, 163, 184, 0.12);
  color: #94a3b8;
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.mode-pill {
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.7px;
  padding: 5px 10px;
  border-radius: 8px;
  border: 1px solid rgba(16, 185, 129, 0.35);
  background: rgba(16, 185, 129, 0.12);
  color: #34d399;
  cursor: default;
  user-select: none;
}

.mode-pill.dev {
  border-color: rgba(245, 158, 11, 0.5);
  background: rgba(245, 158, 11, 0.16);
  color: #fbbf24;
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
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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

.guide-hdr-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.guide-hdr-title {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.9px;
  color: #94a3b8;
  text-transform: uppercase;
  white-space: nowrap;
}

.guide-hdr-pill {
  font-size: 10.5px;
  font-weight: 600;
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.10);
  border: 1px solid rgba(56, 189, 248, 0.28);
  padding: 2px 8px;
  border-radius: 6px;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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

.dev-toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: rgba(15, 23, 42, 0.72);
  border: 1px solid rgba(245, 158, 11, 0.24);
  border-radius: 10px;
  padding: 10px 12px;
}

.dev-toggle-row.active {
  border-color: rgba(245, 158, 11, 0.55);
  background: rgba(41, 26, 8, 0.45);
}

.toggle-switch {
  position: relative;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}

.toggle-switch input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-track {
  width: 44px;
  height: 24px;
  border-radius: 999px;
  background: rgba(51, 65, 85, 0.85);
  border: 1px solid rgba(148, 163, 184, 0.3);
  position: relative;
  transition: all 0.18s ease;
}

.toggle-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #cbd5e1;
  position: absolute;
  top: 2px;
  left: 2px;
  transition: transform 0.18s ease, background 0.18s ease;
}

.toggle-switch input:checked + .toggle-track {
  background: rgba(245, 158, 11, 0.35);
  border-color: rgba(251, 191, 36, 0.7);
}

.toggle-switch input:checked + .toggle-track .toggle-thumb {
  transform: translateX(20px);
  background: #fbbf24;
  box-shadow: 0 0 8px rgba(251, 191, 36, 0.65);
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
  align-items: center;
  gap: 12px;
}

.pipe-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.pipe-missing {
  font-size: 10px;
  color: #fbbf24;
  opacity: 0.9;
}

/* ================= CREW DAILY CHECK-IN & DEV REFERENCE UI ================= */
.daily-log-btn {
  border: 1px solid rgba(16, 185, 129, 0.52);
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.22), rgba(5, 150, 105, 0.10));
  color: #d1fae5;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.4px;
  padding: 8px 14px;
  border-radius: 9px;
  cursor: pointer;
  transition: all 0.18s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.daily-log-btn:hover {
  background: rgba(16, 185, 129, 0.34);
  box-shadow: 0 0 16px rgba(16, 185, 129, 0.28);
}

.rem-btn-primary {
  border-color: rgba(16, 185, 129, 0.72);
  background: rgba(16, 185, 129, 0.24);
  color: #ecfdf5;
}

.rem-btn-primary:hover {
  background: rgba(16, 185, 129, 0.38);
}

.tl-log-btn {
  border: 1px solid rgba(56, 189, 248, 0.35);
  background: rgba(56, 189, 248, 0.12);
  color: #bae6fd;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 6px;
  cursor: pointer;
}

.tl-log-btn:hover {
  background: rgba(56, 189, 248, 0.26);
}

.drawer-mode-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  background: rgba(3, 7, 15, 0.8);
  padding: 4px;
  border-radius: 9px;
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.due-context-box {
  background: linear-gradient(90deg, rgba(245, 158, 11, 0.18), rgba(120, 53, 15, 0.22));
  border: 1px solid rgba(251, 191, 36, 0.5);
  border-radius: 10px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.checkin-meta-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(15, 23, 42, 0.68);
  border: 1px solid rgba(56, 189, 248, 0.22);
  border-radius: 9px;
  font-size: 11.5px;
  font-weight: 600;
  color: #e2e8f0;
}

.checkin-trail-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 6px 11px;
  background: rgba(16, 185, 129, 0.08);
  border: 1px dashed rgba(16, 185, 129, 0.35);
  border-radius: 8px;
  font-size: 11px;
  color: #6ee7b7;
}

.checkin-section {
  background: rgba(11, 19, 36, 0.65);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 11px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.checkin-section-hdr {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  color: #f1f5f9;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  padding-bottom: 7px;
}

.checkin-section-sub {
  font-size: 10.5px;
  font-weight: 500;
  color: #94a3b8;
}

.checkin-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 10px;
}

.checkin-card {
  background: rgba(5, 10, 21, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 9px;
  padding: 9px 10px;
}

.field-span-full {
  grid-column: 1 / -1;
  background: rgba(5, 10, 21, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 9px;
  padding: 10px;
}

.num-stepper-row {
  display: flex;
  align-items: center;
  gap: 5px;
}

.num-input {
  flex: 1;
  text-align: center;
  font-weight: 700;
  color: #38bdf8;
  min-width: 0;
}

.step-btn {
  width: 28px;
  height: 30px;
  border-radius: 7px;
  border: 1px solid rgba(148, 163, 184, 0.25);
  background: rgba(15, 23, 42, 0.9);
  color: #cbd5e1;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
}

.step-btn:hover {
  border-color: #38bdf8;
  color: #38bdf8;
}

.symptom-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}

.symptom-chip {
  border: 1px solid rgba(148, 163, 184, 0.26);
  background: rgba(15, 23, 42, 0.75);
  color: #cbd5e1;
  font-size: 11px;
  font-weight: 600;
  padding: 5px 10px;
  border-radius: 999px;
  cursor: pointer;
}

.symptom-chip.active {
  border-color: rgba(245, 158, 11, 0.75);
  background: rgba(245, 158, 11, 0.22);
  color: #fde68a;
}

.dev-ref-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  margin-top: 4px;
  padding-top: 5px;
  border-top: 1px dashed rgba(148, 163, 184, 0.14);
}

.dev-ref-ranges {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  font-size: 9.8px;
  line-height: 1.3;
}

.ref-tag {
  white-space: nowrap;
}

.ref-g { color: #6ee7b7; }
.ref-y { color: #fcd34d; }
.ref-r { color: #fca5a5; }

.dev-ref-btns {
  display: inline-flex;
  gap: 3px;
  flex-shrink: 0;
}

.ref-fill-btn {
  border-radius: 5px;
  font-size: 9.5px;
  font-weight: 800;
  padding: 2px 6px;
  cursor: pointer;
  border: 1px solid transparent;
}

.ref-fill-g {
  background: rgba(16, 185, 129, 0.16);
  border-color: rgba(16, 185, 129, 0.45);
  color: #34d399;
}

.ref-fill-y {
  background: rgba(245, 158, 11, 0.18);
  border-color: rgba(245, 158, 11, 0.48);
  color: #fbbf24;
}

.ref-fill-r {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.5);
  color: #f87171;
}

.dev-quick-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  width: 100%;
}

/* ================= STAGE 2: MISSION BRIEFING ONBOARDING & MULTI-CREW UI ================= */
.guide-toggle-btn {
  border: 1px solid rgba(56, 189, 248, 0.42);
  background: rgba(15, 23, 42, 0.85);
  color: #7dd3fc;
  font-size: 11.5px;
  font-weight: 700;
  padding: 7px 11px;
  border-radius: 9px;
  cursor: pointer;
  transition: all 0.16s ease;
}

.guide-toggle-btn:hover, .guide-toggle-btn.active {
  background: rgba(56, 189, 248, 0.22);
  color: #f0f9ff;
  box-shadow: 0 0 12px rgba(56, 189, 248, 0.25);
}

.onboarding-banner {
  background: linear-gradient(135deg, rgba(8, 22, 48, 0.92), rgba(12, 19, 38, 0.95));
  border: 1px solid rgba(56, 189, 248, 0.42);
  border-radius: 14px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.45), inset 0 0 22px rgba(56, 189, 248, 0.07);
}

.onb-hdr {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.14);
  padding-bottom: 9px;
}

.onb-title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 9px;
}

.onb-icon {
  font-size: 16px;
}

.onb-title {
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 1px;
  color: #f8fafc;
}

.onb-mode-pill {
  font-size: 10.5px;
  font-weight: 700;
  padding: 2px 9px;
  border-radius: 999px;
}

.onb-mode-pill.standby {
  background: rgba(56, 189, 248, 0.16);
  border: 1px solid rgba(56, 189, 248, 0.48);
  color: #7dd3fc;
}

.onb-mode-pill.active {
  background: rgba(16, 185, 129, 0.16);
  border: 1px solid rgba(16, 185, 129, 0.48);
  color: #6ee7b7;
}

.onb-hdr-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.onb-quick124-btn {
  border: 1px solid rgba(245, 158, 11, 0.55);
  background: rgba(245, 158, 11, 0.16);
  color: #fde68a;
  font-size: 11px;
  font-weight: 700;
  padding: 5px 11px;
  border-radius: 7px;
  cursor: pointer;
}

.onb-quick124-btn:hover {
  background: rgba(245, 158, 11, 0.28);
}

.onb-dismiss-btn {
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(15, 23, 42, 0.75);
  color: #94a3b8;
  font-size: 11px;
  font-weight: 600;
  padding: 5px 10px;
  border-radius: 7px;
  cursor: pointer;
}

.onb-dismiss-btn:hover {
  color: #f8fafc;
}

.onb-steps-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(220px, 1fr));
  gap: 12px;
}

@media (max-width: 960px) {
  .onb-steps-grid {
    grid-template-columns: 1fr;
  }
}

.onb-step-card {
  background: rgba(5, 11, 24, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 10px;
  padding: 11px 13px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.onb-step-card.highlight {
  border-color: rgba(16, 185, 129, 0.48);
  background: linear-gradient(180deg, rgba(6, 34, 29, 0.55), rgba(5, 11, 24, 0.8));
}

.onb-step-num {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 1px;
  color: #38bdf8;
}

.onb-step-title {
  font-size: 12.5px;
  font-weight: 700;
  color: #f1f5f9;
}

.onb-step-desc {
  font-size: 11.5px;
  line-height: 1.48;
  color: #cbd5e1;
}

.onb-cta-btn {
  margin-top: auto;
  align-self: flex-start;
  border: 1px solid rgba(16, 185, 129, 0.65);
  background: linear-gradient(135deg, #059669, #10b981);
  color: #022c22;
  font-size: 11.5px;
  font-weight: 800;
  padding: 6px 12px;
  border-radius: 7px;
  cursor: pointer;
}

.crew-lifecycle-box {
  background: rgba(11, 19, 36, 0.78);
  border: 1px solid rgba(56, 189, 248, 0.28);
  border-radius: 11px;
  padding: 11px 12px;
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.crew-pills-wrap {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(125px, 1fr));
  gap: 6px;
}

.crew-select-pill {
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(5, 10, 21, 0.78);
  color: #cbd5e1;
  border-radius: 8px;
  padding: 6px 9px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  cursor: pointer;
  text-align: left;
}

.crew-select-pill strong {
  font-size: 12px;
  color: #f8fafc;
}

.crew-select-pill span {
  font-size: 10px;
  color: #94a3b8;
}

.crew-select-pill.active {
  border-color: #38bdf8;
  background: rgba(56, 189, 248, 0.18);
  box-shadow: inset 0 0 0 1px rgba(56, 189, 248, 0.35);
}

.crew-select-pill.active strong {
  color: #7dd3fc;
}

.add-crew-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.lifecycle-switch-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding-top: 7px;
  border-top: 1px dashed rgba(148, 163, 184, 0.16);
}

.lifecycle-btns {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

/* STANDBY LED & BADGE STYLES */
.led-STANDBY {
  background: #38bdf8;
  box-shadow: 0 0 9px rgba(56, 189, 248, 0.75);
}

.badge-STANDBY {
  background: rgba(56, 189, 248, 0.14);
  color: #7dd3fc;
  border: 1px solid rgba(56, 189, 248, 0.42);
}
"""
