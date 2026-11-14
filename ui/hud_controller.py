"""Main Client-Side SpaceX HUD Controller (`ui/hud_controller.py`).

Combines `HUD_I18N_JS` and `HUD_ANATOMY_JS` with trend chart rendering,
slide-over telemetry drawer controls, and instant organ-to-trend interactivity.
"""

from __future__ import annotations

from ui.anatomy_svgs import HUD_ANATOMY_JS
from ui.i18n import HUD_I18N_JS

HUD_CONTROLLER_BODY_JS = r"""
  const STATUS_HEX = {
    GREEN: '#10b981',
    YELLOW: '#f59e0b',
    RED: '#ef4444',
    QC: '#f97316'
  };

  // Local instant UI state:
  // - Selecting a subsystem automatically switches to its dedicated holographic anatomy ('anatomy')
  // - Neuro-Ocular defaults to 'eye_zoom' (Eye Cross-Section + Vestibular Labyrinth)
  // - Musculoskeletal supports 'front' / 'back' toggle
  const state = {
    lang: data.lang || 'en',
    selectedModule: data.default_module || 'neuro_ocular',
    viewMode: 'anatomy',       // 'anatomy' | 'overview'
    musculoSide: 'front',      // 'front' | 'back'
    neuroView: 'eye_zoom',     // 'eye_zoom' | 'cns_full'
    selectedMetricIdx: 0,
    guideTab: 'measure',       // 'measure' | 'meaning' | 'action'
    planTab: 'short',          // 'short' | 'long'
    drawerOpen: false,
    drawerTab: 'cabin_environment',
    crew_id: data.crew_id || 'C002',
    mission_day: data.mission_day || 124,
    scenario: data.scenario || 'green',
    prefer_real_csv: data.prefer_real_csv !== false,
    use_manual_overrides: Boolean(data.use_manual_overrides),
    inputs: JSON.parse(JSON.stringify(data.manual_inputs || {}))
  };

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

  function buildScannerSubcontrols() {
    let rightControls = '';
    if (state.viewMode === 'anatomy') {
      if (state.selectedModule === 'musculoskeletal') {
        rightControls = `
          <div class="view-pill-group">
            <button class="view-pill-btn ${state.musculoSide === 'front' ? 'active' : ''}" data-musculo-side="front">${esc(t('view_front'))}</button>
            <button class="view-pill-btn ${state.musculoSide === 'back' ? 'active' : ''}" data-musculo-side="back">${esc(t('view_back'))}</button>
          </div>
        `;
      } else if (state.selectedModule === 'neuro_ocular') {
        rightControls = `
          <div class="view-pill-group">
            <button class="view-pill-btn ${state.neuroView === 'eye_zoom' ? 'active' : ''}" data-neuro-view="eye_zoom">${esc(t('view_eye_zoom'))}</button>
            <button class="view-pill-btn ${state.neuroView === 'cns_full' ? 'active' : ''}" data-neuro-view="cns_full">${esc(t('view_cns_full'))}</button>
          </div>
        `;
      }
    }

    return `
      <div class="scanner-toolbar">
        <div class="view-pill-group">
          <button class="view-pill-btn ${state.viewMode === 'anatomy' ? 'active' : ''}" data-view-mode="anatomy">${esc(t('view_anatomy'))}</button>
          <button class="view-pill-btn ${state.viewMode === 'overview' ? 'active' : ''}" data-view-mode="overview">${esc(t('view_overview'))}</button>
        </div>
        ${rightControls}
      </div>
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

    // Dynamic ambient color stage when Cabin Environment anatomy is active
    const stageEnvClass = (state.viewMode === 'anatomy' && state.selectedModule === 'cabin_environment')
      ? `env-stage-${selSk}`
      : '';

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

            <!-- LEFT COLUMN: HOLOGRAPHIC ANATOMY & HABITAT SCANNER -->
            <div class="hud-panel">
              <div class="panel-hdr">
                <span class="panel-title"><span class="panel-title-dot"></span>${esc(t('bio_title'))}</span>
              </div>

              ${buildScannerSubcontrols()}

              <div class="svg-stage ${stageEnvClass}">
                ${buildHolographicStage(modulesMap)}
                <div class="scanner-caption">
                  <span>${esc(state.viewMode === 'overview' ? t('view_overview') : modShortName(state.selectedModule, state.selectedModule))}</span>
                  <span style="color:#38bdf8;">${esc(t('click_node'))}</span>
                </div>
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
    // Language toggle inside Settings Drawer
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

    // Overview nodes & subsystem list pills -> auto-switch to dedicated holographic anatomy
    root.querySelectorAll('[data-mod], [data-select-mod]').forEach(el => {
      el.onclick = () => {
        const mod = el.getAttribute('data-mod') || el.getAttribute('data-select-mod');
        if (mod) {
          state.selectedModule = mod;
          state.viewMode = 'anatomy';
          if (mod === 'neuro_ocular') state.neuroView = 'eye_zoom';
          state.selectedMetricIdx = 0;
          render();
        }
      };
    });

    // View mode toggle (Dedicated Anatomy <-> All Systems Overview)
    root.querySelectorAll('[data-view-mode]').forEach(btn => {
      btn.onclick = () => {
        state.viewMode = btn.getAttribute('data-view-mode') || 'anatomy';
        render();
      };
    });

    // Musculoskeletal Front / Back toggle
    root.querySelectorAll('[data-musculo-side]').forEach(btn => {
      btn.onclick = () => {
        state.musculoSide = btn.getAttribute('data-musculo-side') || 'front';
        render();
      };
    });

    // Neuro-Ocular Eye+Vestibular Zoom / Full CNS toggle
    root.querySelectorAll('[data-neuro-view]').forEach(btn => {
      btn.onclick = () => {
        state.neuroView = btn.getAttribute('data-neuro-view') || 'eye_zoom';
        render();
      };
    });

    // Clicking a glowing organ region inside SVG jumps center Trend Chart to that metric
    root.querySelectorAll('[data-organ-metric]').forEach(el => {
      el.onclick = () => {
        const idx = Number(el.getAttribute('data-organ-metric')) || 0;
        state.selectedMetricIdx = idx;
        render();
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
"""


def build_hud_js() -> str:
    """Assemble the complete ES module script for Streamlit v2 component mounting."""
    return (
        "export default function(component) {\n"
        "  const { data, setTriggerValue, parentElement } = component;\n"
        "  if (!data) return;\n"
        "  let root = parentElement.querySelector('#zosma-hud-mount');\n"
        "  if (!root) {\n"
        "    root = document.createElement('div');\n"
        "    root.id = 'zosma-hud-mount';\n"
        "    parentElement.appendChild(root);\n"
        "  }\n"
        f"{HUD_I18N_JS}\n"
        f"{HUD_ANATOMY_JS}\n"
        f"{HUD_CONTROLLER_BODY_JS}\n"
        "}\n"
    )
