"""Main Client-Side SpaceX HUD Controller (`ui/hud_controller.py`).

Combines `HUD_I18N_JS` and `HUD_ANATOMY_JS` with trend chart rendering,
slide-over telemetry drawer controls, and instant organ-to-trend interactivity.
"""

from __future__ import annotations

from ui.anatomy_svgs import HUD_ANATOMY_JS
from ui.drawer_renderer import HUD_DRAWER_JS
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
  const savedClk = data.offline_clock || {};
  const nowHost = Date.now();
  const initialScEpoch = Number(savedClk.spacecraft_epoch_ms) || nowHost;
  const initialHostEpoch = Number(savedClk.host_epoch_ms) || nowHost;
  const initialScale = Boolean(data.developer_mode) ? (Number(savedClk.time_scale) || 1) : 1;
  // Advance saved spacecraft clock by elapsed host wall time since last save
  const currentScMsOnLoad = initialScEpoch + Math.max(0, nowHost - initialHostEpoch) * initialScale;

  function localMidnightMs(ms) {
    const d = new Date(ms);
    d.setHours(0, 0, 0, 0);
    return d.getTime();
  }

  const initialAnchorMidnight = savedClk.anchor_midnight_ms !== undefined && savedClk.anchor_midnight_ms !== null
    ? Number(savedClk.anchor_midnight_ms)
    : localMidnightMs(nowHost);
  const initialAnchorDay = savedClk.anchor_mission_day !== undefined && savedClk.anchor_mission_day !== null
    ? Number(savedClk.anchor_mission_day)
    : Number(data.mission_day || 124);

  const prevUi = root._zosmaUiState || {};

  const state = {
    lang: data.lang || 'en',
    developer_mode: Boolean(data.developer_mode),
    selectedModule: data.default_module || prevUi.selectedModule || 'neuro_ocular',
    viewMode: prevUi.viewMode || 'anatomy',       // 'anatomy' | 'overview'
    musculoSide: prevUi.musculoSide || 'front',   // 'front' | 'back'
    neuroView: prevUi.neuroView || 'eye_zoom',    // 'eye_zoom' | 'cns_full'
    selectedMetricIdx: Number(data.default_metric_idx !== undefined ? data.default_metric_idx : (prevUi.selectedMetricIdx || 0)),
    guideTab: data.default_guide_tab || prevUi.guideTab || 'measure',       // 'measure' | 'meaning' | 'action'
    planTab: prevUi.planTab || 'short',           // 'short' | 'long'
    drawerOpen: Boolean(prevUi.drawerOpen),
    drawerSection: prevUi.drawerSection || 'checkin',  // 'checkin' | 'settings'
    checkinModuleTab: prevUi.checkinModuleTab || data.default_module || 'cabin_environment',
    drawerTab: prevUi.drawerTab || 'cabin_environment',
    drawerScrollTop: Number(prevUi.drawerScrollTop || 0),
    crew_id: data.crew_id || 'C002',
    mission_day: data.mission_day || 124,
    scenario: data.scenario || 'green',
    prefer_real_csv: data.prefer_real_csv !== false,
    use_manual_overrides: Boolean(data.use_manual_overrides),
    inputs: JSON.parse(JSON.stringify(data.manual_inputs || {})),
    dailyVitals: JSON.parse(JSON.stringify(data.daily_vitals || {})),
    moduleCheckins: JSON.parse(JSON.stringify(data.module_checkins || {})),
    checkinSeries: JSON.parse(JSON.stringify(data.checkin_series || {})),
    clock: {
      spacecraft_epoch_ms: currentScMsOnLoad,
      host_epoch_ms: nowHost,
      time_scale: initialScale,
      sound_enabled: savedClk.sound_enabled !== false,
      anchor_midnight_ms: initialAnchorMidnight,
      anchor_mission_day: initialAnchorDay,
      module_due_ms: Object.assign({}, savedClk.module_due_ms || {})
    },
    chimedKeys: Object.assign({}, prevUi.chimedKeys || {})
  };

  function syncPersistedUiState() {
    const curDrawer = root.querySelector('#drawer-panel');
    if (curDrawer) {
      state.drawerScrollTop = curDrawer.scrollTop;
    }
    root._zosmaUiState = {
      selectedModule: state.selectedModule,
      viewMode: state.viewMode,
      musculoSide: state.musculoSide,
      neuroView: state.neuroView,
      selectedMetricIdx: state.selectedMetricIdx,
      guideTab: state.guideTab,
      planTab: state.planTab,
      drawerOpen: state.drawerOpen,
      drawerSection: state.drawerSection,
      checkinModuleTab: state.checkinModuleTab,
      drawerTab: state.drawerTab,
      drawerScrollTop: state.drawerScrollTop,
      chimedKeys: state.chimedKeys
    };
  }

  function getSpacecraftNowMs() {
    const elapsed = Math.max(0, Date.now() - state.clock.host_epoch_ms);
    return state.clock.spacecraft_epoch_ms + elapsed * (state.clock.time_scale || 1);
  }

  function computeMccMissionDay(scMs) {
    const curMid = localMidnightMs(scMs);
    const deltaDays = Math.round((curMid - state.clock.anchor_midnight_ms) / 86400000);
    return Math.max(1, Number(state.clock.anchor_mission_day || 124) + deltaDays);
  }

  function getLocalTzLabel() {
    const offsetMin = -new Date().getTimezoneOffset();
    const sign = offsetMin >= 0 ? '+' : '-';
    const absMin = Math.abs(offsetMin);
    const h = Math.floor(absMin / 60);
    const m = absMin % 60;
    return m ? `UTC${sign}${h}:${String(m).padStart(2, '0')}` : `UTC${sign}${h}`;
  }

  function formatScDate(ms) {
    const d = new Date(ms);
    const pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  }

  function formatScTime(ms) {
    const d = new Date(ms);
    const pad = n => String(n).padStart(2, '0');
    return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  }

  function formatCountdown(diffMs) {
    if (diffMs <= 0) return t('rtc_due_now');
    const totalSec = Math.floor(diffMs / 1000);
    const h = Math.floor(totalSec / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    const s = totalSec % 60;
    const pad = n => String(n).padStart(2, '0');
    return `${pad(h)}:${pad(m)}:${pad(s)}`;
  }

  function ensureModuleDueTimers(modulesMap, scNow) {
    Object.keys(modulesMap).forEach(modId => {
      const m = modulesMap[modId];
      const nextH = Number((m && m.short_term_plan && m.short_term_plan.next_measurement_in_hours) ?? 24);
      const maxHorizonMs = Math.max(1, nextH) * 3600 * 1000;
      const existing = state.clock.module_due_ms[modId];
      if (existing === undefined || existing === null || isNaN(Number(existing))) {
        state.clock.module_due_ms[modId] = nextH === 0 ? scNow : (scNow + nextH * 3600 * 1000);
      } else if (nextH === 0 && existing > scNow) {
        state.clock.module_due_ms[modId] = scNow;
      } else if ((existing - scNow) > maxHorizonMs + 60000) {
        // Clamp if scenario switched from longer interval (168h) to tighter interval (4h/12h)
        state.clock.module_due_ms[modId] = scNow + nextH * 3600 * 1000;
      }
    });
  }

  function playAlertChime() {
    if (!state.clock.sound_enabled) return;
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const now = ctx.currentTime;
      [880, 1174.66].forEach((freq, i) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, now + i * 0.14);
        gain.gain.setValueAtTime(0.06, now + i * 0.14);
        gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.14 + 0.18);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now + i * 0.14);
        osc.stop(now + i * 0.14 + 0.19);
      });
    } catch (_) {}
  }

  function getDueModules(modulesMap, scNow) {
    const due = [];
    Object.keys(modulesMap).forEach(modId => {
      const dueAt = Number(state.clock.module_due_ms[modId] ?? (scNow + 3600000));
      if (dueAt <= scNow) {
        const m = modulesMap[modId];
        due.push({
          module_id: modId,
          status: statusKey(m),
          overdue_ms: scNow - dueAt
        });
      }
    });
    return due;
  }

  function snapshotClockForSave() {
    const scNow = getSpacecraftNowMs();
    state.clock.spacecraft_epoch_ms = scNow;
    state.clock.host_epoch_ms = Date.now();
    return {
      spacecraft_epoch_ms: Math.round(scNow),
      host_epoch_ms: state.clock.host_epoch_ms,
      time_scale: state.clock.time_scale,
      sound_enabled: state.clock.sound_enabled,
      anchor_midnight_ms: state.clock.anchor_midnight_ms,
      anchor_mission_day: state.clock.anchor_mission_day,
      module_due_ms: state.clock.module_due_ms
    };
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
    if (!modObj.quality_passed) {
      const raw = String(modObj.raw_status || 'QC FAIL').toUpperCase();
      if (state.lang === 'zh') {
        if (raw.includes('NO_DATA')) return '無資料';
        if (raw.includes('RESCAN')) return '需重掃';
        return '資料不足';
      }
      if (raw.includes('NO_DATA')) return 'NO DATA';
      if (raw.includes('RESCAN')) return 'RESCAN';
      return 'QC FAIL';
    }
    if (modObj.watch_flag) return t('status_WATCH');
    const st = modObj.status_light || 'GREEN';
    return t('status_' + st);
  }

  function sendPayload(actionType, extra = {}) {
    syncPersistedUiState();
    setTriggerValue('hud_action', {
      type: actionType,
      ts: Date.now(),
      lang: state.lang,
      developer_mode: Boolean(state.developer_mode),
      crew_id: state.crew_id,
      mission_day: Number(state.mission_day) || 124,
      scenario: state.scenario,
      offline_clock: snapshotClockForSave(),
      prefer_real_csv: Boolean(state.prefer_real_csv),
      use_manual_overrides: Boolean(state.use_manual_overrides),
      manual_inputs: state.inputs,
      daily_vitals: state.dailyVitals,
      module_checkins: state.moduleCheckins,
      selected_module: state.selectedModule,
      selected_metric_idx: state.selectedMetricIdx,
      guide_tab: state.guideTab,
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

  const MUSCULO_GROUP_MAP = {
    e4d_s_bone_index: 'training',
    iso_peak_force_n: 'training',
    velocity_loss_pct: 'training',
    csa_thigh_cm2: 'csa',
    csa_calf_cm2: 'csa',
    body_mass_kg: 'body_mass',
    ntx_bone_resorption: 'bone_metabolism',
    ctx_bone_resorption: 'bone_metabolism',
    p1np_bone_formation: 'bone_metabolism',
    est_monthly_bone_loss_pct: 'bone_metabolism',
    osd575_ca_alp_baseline: 'bone_metabolism'
  };

  function resolveMetricDisplayName(m) {
    if (!m) return '';
    // Item 6: Only show 'OSD-575' if data/shared_real/OSD-575_cmp.csv is actually present (ref_data_source === 'REAL')
    if (m.metric_name === 'osd575_ca_alp_baseline') {
      if (m.ref_data_source === 'REAL') {
        return state.lang === 'zh' ? 'OSD-575 血清鈣/ALP基準' : 'NASA OSDR OSD-575';
      }
      return state.lang === 'zh' ? '內建參考值（非 NASA 資料）' : (m.display_name || 'Built-in reference (non-NASA data)');
    }
    return metricLabel(m.metric_name);
  }

  function buildTrendSvg(metric, missionDay, modQualityPassed = true) {
    if (!metric) {
      return `<div style="padding:24px;color:#64748b;font-size:12px;">No telemetry series available.</div>`;
    }
    // Item 4: When INSUFFICIENT_DATA / QC failed, do not plot invalid points or 30-day projection line
    if (!modQualityPassed || !metric.quality_passed || metric.raw_status === 'INSUFFICIENT_DATA') {
      return `<div style="padding:36px 18px;text-align:center;color:#fb923c;font-size:12.5px;font-weight:600;border:1px dashed rgba(249,115,22,0.35);border-radius:10px;background:rgba(249,115,22,0.06);">${esc(t('qc_trend_blocked'))}</div>`;
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

  function render() {
    const prevDrawer = root.querySelector('#drawer-panel');
    if (prevDrawer) {
      state.drawerScrollTop = prevDrawer.scrollTop;
    }

    const modulesMap = data.modules || {};
    const schedule = data.schedule || {};
    const order = data.module_order || Object.keys(modulesMap);
    const scNow = getSpacecraftNowMs();
    state.mission_day = computeMccMissionDay(scNow);
    ensureModuleDueTimers(modulesMap, scNow);
    const dueModules = getDueModules(modulesMap, scNow);
    const minDueMs = order.reduce((acc, modId) => {
      const d = Number(state.clock.module_due_ms[modId] ?? (scNow + 3600000));
      return Math.min(acc, d);
    }, scNow + 999 * 3600 * 1000);
    const nextDiffMs = minDueMs - scNow;

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
      const isReal = m && m.data_source === 'REAL';
      const srcBadge = isReal
        ? t('src_real')
        : (m && m.data_source === 'SIMULATED' ? t('src_sim') : (m ? m.data_source : t('src_demo')));
      return `
        <div class="subsys-pill ${isSel ? 'selected' : ''}" data-select-mod="${modId}">
          <div class="subsys-left">
            <span class="led-dot led-${sk}"></span>
            <span class="subsys-name">${esc(modShortName(modId, m ? m.short_name : modId))}</span>
          </div>
          <div class="subsys-meta">
            <span class="src-chip ${isReal ? 'src-chip-real' : 'src-chip-sim'}">${esc(srcBadge)}</span>
            <span class="badge badge-${sk}">${esc(badgeLabel(m))}</span>
          </div>
        </div>
      `;
    }).join('');

    // Mini metric tiles (Items 1, 5, 6 + clean single-line delta/QC caption)
    const metricTilesHtml = metrics.map((m, idx) => {
      const isRef = m.raw_status === 'REFERENCE' || m.metric_name === 'p1np_bone_formation' || m.metric_name === 'osd575_ca_alp_baseline';
      const msk = !m.quality_passed ? 'QC' : (isRef ? 'REF' : (m.status_light || 'GREEN'));
      let deltaTxt = '';
      if (!m.quality_passed || m.raw_status === 'INSUFFICIENT_DATA') {
        deltaTxt = layerLabel('quality_check');
      } else if (m.delta_pct !== null && m.delta_pct !== undefined) {
        deltaTxt = `${m.delta_pct > 0 ? '+' : ''}${m.delta_pct}% ${t('vs_base')}`;
      } else if (m.message && m.message.length <= 48) {
        deltaTxt = zhText(m.message);
      } else {
        deltaTxt = `${t('layer_prefix')} ${layerLabel(m.decided_by)}`;
      }
      const dispName = resolveMetricDisplayName(m);
      return `
        <div class="metric-card ${idx === state.selectedMetricIdx ? 'active' : ''}" data-metric-idx="${idx}">
          <div class="m-top">
            <span class="m-name" title="${esc(dispName)}">${esc(dispName)}</span>
            <span class="led-dot led-${msk}" style="width:7px;height:7px;"></span>
          </div>
          <div class="m-val-row">
            <span class="m-val">${esc(m.current_val)}</span>
            <span class="m-unit">${esc(m.unit)}</span>
          </div>
          <div class="m-delta" title="${esc(m.message ? zhText(m.message) : deltaTxt)}">${esc(deltaTxt)}</div>
        </div>
      `;
    }).join('');

    // 3-step Crew Guidance content:
    // 1) Support Role 2's grouped guidance (`guidance.groups` keyed by metric)
    // 2) Support Role 3's per-metric guidance (`how_to_measure` / `why_in_space` / `action_steps`)
    // 3) Fallback to module-level `selMod.guidance`
    const rawGuidance = selMod.guidance || {};
    let g = rawGuidance;
    if (rawGuidance.groups && activeMetric) {
      const grpKey = MUSCULO_GROUP_MAP[activeMetric.metric_name];
      if (grpKey && rawGuidance.groups[grpKey]) {
        g = rawGuidance.groups[grpKey];
      }
    }

    const hasFullMetricGuide = Boolean(
      activeMetric &&
      (activeMetric.how_to_measure ||
        activeMetric.measurement_guide ||
        activeMetric.why_in_space ||
        activeMetric.plain_explanation ||
        (Array.isArray(activeMetric.action_steps) && activeMetric.action_steps.length))
    );
    const mGuideMeasure = activeMetric && (activeMetric.how_to_measure || activeMetric.measurement_guide);
    const mGuideMeaning = activeMetric && (activeMetric.why_in_space || activeMetric.plain_explanation);
    const mGuideSteps = (activeMetric && Array.isArray(activeMetric.action_steps) && activeMetric.action_steps.length)
      ? activeMetric.action_steps
      : (hasFullMetricGuide && activeMetric && activeMetric.action ? [activeMetric.action] : null);

    const activeGuideSt = activeMetric
      ? (!activeMetric.quality_passed ? 'QC' : (activeMetric.status_light || 'GREEN'))
      : 'GREEN';
    const activeGuideStText = activeGuideSt === 'QC'
      ? badgeLabel({ quality_passed: false, raw_status: activeMetric && activeMetric.raw_status })
      : (t('status_' + activeGuideSt) !== ('status_' + activeGuideSt) ? t('status_' + activeGuideSt) : activeGuideSt);
    const activeGuideName = activeMetric
      ? (activeMetric.indicator ? zhText(activeMetric.indicator) : resolveMetricDisplayName(activeMetric))
      : '';
    const activeGuideTitle = hasFullMetricGuide
      ? `${activeGuideName} · ${activeGuideStText}`
      : t('guide_sop');

    let guideContentHtml = '';
    if (state.guideTab === 'measure') {
      guideContentHtml = `<div style="white-space:pre-line;">${esc(zhText(mGuideMeasure || g.how_to_measure))}</div>`;
    } else if (state.guideTab === 'meaning') {
      guideContentHtml = `<div style="white-space:pre-line;">${esc(zhText(mGuideMeaning || g.plain_explanation))}</div>`;
    } else {
      const steps = mGuideSteps || (Array.isArray(g.action_protocol) ? g.action_protocol : [g.action_protocol || 'Nominal']);
      guideContentHtml = `<ol class="protocol-list">${steps.map(s => `<li>${esc(zhText(s))}</li>`).join('')}</ol>`;
      if (state.selectedModule === 'cardiovascular' && selMod.correlation_alerts && selMod.correlation_alerts.length) {
        guideContentHtml += `<div class="conflict-banner" style="margin-top:8px;">
          <div class="conflict-rule">⚡ ${esc(t('cross_link_title'))}</div>
          <div class="conflict-text">${selMod.correlation_alerts.map(c => esc(zhText(c))).join('<br>')}</div>
        </div>`;
      }
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

    // Timeline cards (group consecutive actions from the same module & window into one clean card)
    const rawTimelineItems = state.planTab === 'short'
      ? (schedule.short_term_board || []).map(item => {
          const dueAt = state.clock.module_due_ms[item.module_id];
          let tag = item.next_hours === 0 ? t('tag_immediate') : `T+${item.next_hours}H`;
          if (dueAt !== undefined) {
            const rem = dueAt - scNow;
            tag = rem <= 0 ? t('rtc_due_now') : t('rtc_due_in', { t: formatCountdown(rem) });
          }
          return {
            mod: item.module_id,
            status: item.status_light,
            tag: tag,
            dueModId: dueAt !== undefined ? item.module_id : '',
            text: zhText(item.action)
          };
        })
      : (schedule.long_term_board || []).map(item => ({
          mod: item.module_id,
          status: item.status_light,
          tag: item.days_until_red !== null && item.days_until_red !== undefined ? t('tag_red_in', { d: item.days_until_red }) : t('tag_regimen'),
          dueModId: '',
          text: zhText(item.adjustment)
        }));

    const groupedTimeline = [];
    const seenGroupMap = {};
    rawTimelineItems.forEach(it => {
      const gKey = `${it.mod}__${it.status}`;
      if (!seenGroupMap[gKey]) {
        const entry = {
          mod: it.mod,
          status: it.status,
          tag: it.tag,
          dueModId: it.dueModId,
          texts: [it.text]
        };
        seenGroupMap[gKey] = entry;
        groupedTimeline.push(entry);
      } else if (!seenGroupMap[gKey].texts.includes(it.text)) {
        seenGroupMap[gKey].texts.push(it.text);
      }
    });

    const timelineHtml = groupedTimeline.map(it => {
      const col = STATUS_HEX[it.status] || '#10b981';
      const modTitle = modShortName(it.mod, it.mod.replace('_', ' '));
      const dueAttr = it.dueModId ? `data-due-mod="${it.dueModId}"` : '';
      const bodyHtml = it.texts.length === 1
        ? `<div class="tl-desc">${esc(it.texts[0])}</div>`
        : `<ol class="protocol-list" style="font-size:12px;color:#e2e8f0;">${it.texts.map(line => `<li>${esc(line)}</li>`).join('')}</ol>`;
      const canQuickLog = Boolean(modulesMap[it.mod]);
      return `
        <div class="timeline-card" style="--tl-color:${col}">
          <div class="tl-hdr">
            <span class="tl-mod">${esc(modTitle)}</span>
            <div style="display:flex;align-items:center;gap:6px;">
              ${canQuickLog ? `<button type="button" class="tl-log-btn" data-quick-log-mod="${esc(it.mod)}">${esc(t('timeline_log_btn'))}</button>` : ''}
              <span class="tl-time" ${dueAttr}>${esc(it.tag)}</span>
            </div>
          </div>
          ${bodyHtml}
        </div>
      `;
    }).join('');

    // Data folder footer strip
    const folderItemsList = (data.data_statuses || []).map(ds => {
      const mode = ds.source_mode || (ds.has_real_files ? 'REAL_CSV' : 'SIMULATED_DEMO');
      const mObj = modulesMap[ds.module_id];
      const isActualReal = mObj && mObj.data_source === 'REAL';
      let label = t('src_demo');
      let col = '#94a3b8';
      if (mode === 'REAL_CSV' && isActualReal) {
        label = t('src_real');
        col = '#34d399';
      } else if (mode === 'PARTIAL_FALLBACK') {
        label = `${t('src_partial')} (${ds.present_count || 0}/${ds.expected_count || 0})`;
        col = '#fbbf24';
      } else if (ds.has_real_files && !isActualReal) {
        label = t('src_sim');
        col = '#94a3b8';
      }
      const missCount = Array.isArray(ds.missing_files) ? ds.missing_files.length : 0;
      const missHint = missCount > 0 ? `<span class="pipe-missing">(${esc(t('missing_files_lbl', { n: missCount }))})</span>` : '';
      return `<span class="pipe-chip"><strong>${esc(modShortName(ds.module_id, ds.short_name))}:</strong> <span style="color:${col}">${esc(label)}</span>${missHint}</span>`;
    });

    const sr = data.shared_real_status || {};
    const srMiss = Array.isArray(sr.missing_files) ? sr.missing_files.length : 0;
    const srCol = sr.source_mode === 'REAL_CSV' ? '#34d399' : (sr.source_mode === 'PARTIAL_FALLBACK' ? '#fbbf24' : '#94a3b8');
    const srLabel = sr.source_mode === 'REAL_CSV'
      ? t('src_real')
      : (sr.source_mode === 'PARTIAL_FALLBACK' ? `${t('src_partial')} (${sr.present_count || 0}/${sr.expected_count || 0})` : t('src_demo'));
    const srMissHint = srMiss > 0 ? `<span class="pipe-missing">(${esc(t('missing_files_lbl', { n: srMiss }))})</span>` : '';
    folderItemsList.push(`<span class="pipe-chip"><strong>${esc(t('shared_real_lbl'))}:</strong> <span style="color:${srCol}">${esc(srLabel)}</span>${srMissHint}</span>`);
    const folderItems = folderItemsList.join('');

    const selSk = statusKey(selMod);
    const scenLabelMap = {
      green: t('scen_green'),
      yellow: t('scen_yellow'),
      red: t('scen_red'),
      bad_data: t('scen_bad')
    };

    // Item 3: When INSUFFICIENT_DATA / QC failed on selected or any module, show '—' instead of '無風險 / NONE'
    const anyQcFailed = Object.values(modulesMap).some(m => m && !m.quality_passed);
    let projectedRedDisplay = esc(t('none_lbl'));
    if (anyQcFailed || !selMod.quality_passed) {
      projectedRedDisplay = '—';
    } else if (schedule.earliest_red_days !== null && schedule.earliest_red_days !== undefined) {
      projectedRedDisplay = esc(schedule.earliest_red_days) + ' ' + esc(t('days_unit'));
    }

    // Item 8: Enrich musculoskeletal summary note with Isometric Strength delta_pct while keeping CTX
    let summaryRaw = selMod.summary_note || '';
    if (state.selectedModule === 'musculoskeletal' && selMod.quality_passed) {
      const isoMetric = metrics.find(m => m.metric_name === 'iso_peak_force_n');
      if (isoMetric && isoMetric.delta_pct !== null && isoMetric.delta_pct !== undefined && !summaryRaw.includes('Strength=')) {
        const sign = Number(isoMetric.delta_pct) > 0 ? '+' : '';
        summaryRaw = summaryRaw.replace('VBT=', `Strength=${sign}${isoMetric.delta_pct}%, VBT=`);
      }
    }

    // Item 2: Urgent escalation red banner at top of Musculoskeletal card
    const urgentEscHtml = (selMod.urgent_escalation || (state.selectedModule === 'musculoskeletal' && selMod.short_term_plan && selMod.short_term_plan.urgent_alert))
      ? `<div class="urgent-esc-banner">${esc(t('urgent_escalation_banner'))}</div>`
      : '';

    // Dynamic ambient color stage when Cabin Environment anatomy is active
    const stageEnvClass = (state.viewMode === 'anatomy' && state.selectedModule === 'cabin_environment')
      ? `env-stage-${selSk}`
      : '';

    const dueBannerHtml = dueModules.length ? `
      <div class="reminder-banner ${dueModules.some(d => d.status === 'RED') ? 'urgent' : ''}" id="reminder-banner">
        <div class="reminder-left">
          <span>⏰</span>
          <span>
            <strong>${esc(t('rem_banner_title'))}</strong>
            ${dueModules.map(d => `<span class="badge badge-${d.status}" style="margin-left:6px;">${esc(modShortName(d.module_id, d.module_id))}</span>`).join('')}
          </span>
        </div>
        <div class="reminder-actions">
          <button class="rem-btn rem-btn-primary" id="open-due-checkin-btn">${esc(t('rem_log_btn'))}</button>
          <button class="rem-btn" id="ack-due-btn">${esc(t('rem_mark_done'))}</button>
          <button class="rem-btn" id="toggle-sound-btn">${esc(state.clock.sound_enabled ? t('rem_mute') : t('rem_unmute'))}</button>
        </div>
      </div>
    ` : '';

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
                  <span class="crew-pill" id="crew-day-pill">${esc(t('crew_badge', { crew: state.crew_id, day: state.mission_day }))}</span>
                </div>
                <div class="brand-sub">${esc(t('hud_sub'))}</div>
              </div>
            </div>

            <div class="cmd-controls">
              <!-- OFFLINE SPACECRAFT CLOCK WIDGET (display only) -->
              <div class="rtc-widget" title="${esc(t('clk_section_title'))}">
                <span class="rtc-dot"></span>
                <div class="rtc-readout">
                  <span class="rtc-time" id="sc-clock-time">${esc(formatScTime(scNow))}</span>
                  <span class="rtc-date" id="sc-clock-date">${esc(formatScDate(scNow))} · ${esc(getLocalTzLabel())} · ${esc(t('rtc_offline_tag'))}</span>
                </div>
                ${state.developer_mode ? `<span class="rtc-scale-chip ${state.clock.time_scale > 1 ? 'fast' : ''}" id="sc-clock-scale">${state.clock.time_scale}x</span>` : ''}
              </div>

              <span class="mode-pill ${state.developer_mode ? 'dev' : ''}" id="mode-pill-badge" title="${esc(t('dev_mode_desc'))}">
                ${esc(state.developer_mode ? t('dev_mode_on') : t('dev_mode_off'))}
              </span>

              ${state.developer_mode ? `
                <div class="scen-group" title="Switch Simulation Preset">
                  ${['green', 'yellow', 'red', 'bad_data'].map(sc => `
                    <button class="scen-btn ${state.scenario === sc ? 'active-' + sc : ''}" data-scen="${sc}">
                      ${esc(scenLabelMap[sc])}
                    </button>
                  `).join('')}
                </div>
              ` : ''}

              <button class="daily-log-btn" id="open-checkin-btn">
                ${esc(t('daily_log_btn'))}
              </button>

              <button class="drawer-toggle-btn" id="open-drawer-btn">
                ${esc(t('drawer_btn'))} ${(state.developer_mode && state.use_manual_overrides) ? '(' + esc(t('manual_on')) + ')' : ''}
              </button>
            </div>
          </div>

          <!-- LIVE DUE / OVERDUE REMINDER BANNER -->
          <div id="reminder-slot">${dueBannerHtml}</div>

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
            <div class="kpi-tile" style="--accent:${nextDiffMs <= 0 ? '#f59e0b' : '#38bdf8'}">
              <span class="kpi-label">${esc(t('kpi_triage_lbl'))}</span>
              <span class="kpi-val" id="kpi-countdown-val" style="color:${nextDiffMs <= 0 ? '#fbbf24' : '#f8fafc'}">${esc(formatCountdown(nextDiffMs))}</span>
              <span class="kpi-sub">${esc(t('kpi_triage_sub'))}</span>
            </div>
            <div class="kpi-tile" style="--accent:#a855f7">
              <span class="kpi-label">${esc(t('kpi_proj_lbl'))}</span>
              <span class="kpi-val">${projectedRedDisplay}</span>
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

              ${urgentEscHtml}
              ${summaryRaw ? `<div class="summary-strip">${esc(zhText(summaryRaw))}</div>` : ''}

              <div class="metric-grid">
                ${metricTilesHtml}
              </div>

              <div class="chart-card">
                <div class="chart-hdr">
                  <span class="chart-title">
                    ${esc(t('traj_title'))} · <span style="color:#38bdf8">${esc(activeMetric ? resolveMetricDisplayName(activeMetric) : '')}</span>
                    ${activeMetric && activeMetric.unit ? `(${esc(activeMetric.unit)})` : ''}
                  </span>
                  <div class="chart-legend">
                    <span class="leg-item"><span class="leg-line" style="background:#38bdf8;"></span>${esc(t('leg_measured'))}</span>
                    <span class="leg-item"><span class="leg-line" style="background:#f472b6;"></span>${esc(t('leg_forecast'))}</span>
                  </div>
                </div>
                ${buildTrendSvg(activeMetric, state.mission_day, selMod.quality_passed !== false)}
              </div>

              <div class="guide-box">
                <div class="guide-hdr-row">
                  <span class="guide-hdr-title">${esc(t('guide_hdr'))}</span>
                  <span class="guide-hdr-pill" title="${esc(activeGuideTitle)}">${esc(activeGuideTitle)}</span>
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
            ${state.developer_mode ? `
              <button class="secondary-btn" style="padding:4px 10px;font-size:10.5px;" id="gen-csv-btn">
                ${esc(t('gen_csv_btn'))}
              </button>
            ` : ''}
          </div>

          <!-- ITEM 7: FIXED SIMULATION DISCLAIMER FOOTER -->
          <div class="sim-disclaimer-bar">
            ${esc(t('sim_disclaimer'))}
          </div>

        </div>
      </div>

      ${buildDrawerPanelHtml(modulesMap, order, scNow, dueModules)}
    `;

    const nextDrawer = root.querySelector('#drawer-panel');
    if (nextDrawer) {
      if (state.drawerScrollTop > 0) {
        nextDrawer.scrollTop = state.drawerScrollTop;
      }
      nextDrawer.onscroll = () => {
        state.drawerScrollTop = nextDrawer.scrollTop;
        if (root._zosmaUiState) {
          root._zosmaUiState.drawerScrollTop = nextDrawer.scrollTop;
        }
      };
    }
    syncPersistedUiState();
    bindEvents();
  }

  function bindEvents() {
    // Scenario preset buttons -> reset module timers to new scenario cadence and evaluate
    root.querySelectorAll('[data-scen]').forEach(btn => {
      btn.onclick = () => {
        state.scenario = btn.getAttribute('data-scen');
        state.use_manual_overrides = false;
        state.clock.module_due_ms = {};
        state.chimedKeys = {};
        sendPayload('switch_scenario');
      };
    });

    // Top bar Daily Check-In button opens Drawer on Check-In tab
    const openCheckinBtn = root.querySelector('#open-checkin-btn');
    if (openCheckinBtn) {
      openCheckinBtn.onclick = () => {
        const due = getDueModules(data.modules || {}, getSpacecraftNowMs());
        state.drawerSection = 'checkin';
        if (due.length) state.checkinModuleTab = due[0].module_id;
        else state.checkinModuleTab = state.selectedModule;
        state.drawerOpen = true;
        state.drawerScrollTop = 0;
        render();
      };
    }

    // Reminder Banner: Log Check-In Data / Mark Checked & Reset Timer / Toggle Mute
    function bindReminderBannerEvents() {
      const dueLogBtn = root.querySelector('#open-due-checkin-btn');
      if (dueLogBtn) {
        dueLogBtn.onclick = () => {
          const due = getDueModules(data.modules || {}, getSpacecraftNowMs());
          state.drawerSection = 'checkin';
          if (due.length) state.checkinModuleTab = due[0].module_id;
          state.drawerOpen = true;
          state.drawerScrollTop = 0;
          render();
        };
      }
      const ackBtn = root.querySelector('#ack-due-btn');
      if (ackBtn) {
        ackBtn.onclick = () => {
          const scNow = getSpacecraftNowMs();
          const modulesMap = data.modules || {};
          Object.keys(modulesMap).forEach(modId => {
            const dueAt = Number(state.clock.module_due_ms[modId] ?? scNow);
            if (dueAt <= scNow) {
              const nextH = Number((modulesMap[modId].short_term_plan && modulesMap[modId].short_term_plan.next_measurement_in_hours) ?? 24);
              const resetH = nextH > 0 ? nextH : 1;
              state.clock.module_due_ms[modId] = scNow + resetH * 3600 * 1000;
              delete state.chimedKeys[modId];
            }
          });
          render();
          sendPayload('save_clock');
        };
      }
      const soundBtn = root.querySelector('#toggle-sound-btn');
      if (soundBtn) {
        soundBtn.onclick = () => {
          state.clock.sound_enabled = !state.clock.sound_enabled;
          render();
          sendPayload('save_clock');
        };
      }
    }
    bindReminderBannerEvents();

    // Right Timeline Card quick-log button
    root.querySelectorAll('[data-quick-log-mod]').forEach(btn => {
      btn.onclick = () => {
        const modId = btn.getAttribute('data-quick-log-mod');
        if (modId) state.checkinModuleTab = modId;
        state.drawerSection = 'checkin';
        state.drawerOpen = true;
        render();
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

    // Settings Drawer open button
    const openBtn = root.querySelector('#open-drawer-btn');
    if (openBtn) openBtn.onclick = () => { state.drawerSection = 'settings'; state.drawerOpen = true; render(); };

    // Generate Demo CSVs
    const genCsvBtn = root.querySelector('#gen-csv-btn');
    if (genCsvBtn) {
      genCsvBtn.onclick = () => {
        sendPayload('generate_demo_csvs');
      };
    }

    bindDrawerEvents();
  }

  // Background 1-second offline clock ticker (updates DOM smoothly without full re-render)
  if (root._zosmaTimerId) {
    clearInterval(root._zosmaTimerId);
  }
  root._zosmaTimerId = setInterval(() => {
    const modulesMap = data.modules || {};
    const order = data.module_order || Object.keys(modulesMap);
    const scNow = getSpacecraftNowMs();

    const tEl = root.querySelector('#sc-clock-time');
    const dEl = root.querySelector('#sc-clock-date');
    if (tEl) tEl.textContent = formatScTime(scNow);
    if (dEl) dEl.textContent = `${formatScDate(scNow)} · ${getLocalTzLabel()} · ${t('rtc_offline_tag')}`;

    const chkClockEl = root.querySelector('#chk-sc-clock-meta');
    if (chkClockEl) chkClockEl.textContent = `${formatScDate(scNow)} · ${formatScTime(scNow)}`;

    const liveDay = computeMccMissionDay(scNow);
    if (liveDay !== state.mission_day) {
      state.mission_day = liveDay;
      const badgeEl = root.querySelector('#crew-day-pill');
      if (badgeEl) badgeEl.textContent = t('crew_badge', { crew: state.crew_id, day: liveDay });
      const chkDayEl = root.querySelector('#chk-crew-day-meta');
      if (chkDayEl) chkDayEl.textContent = `🧑‍🚀 ${t('crew_badge', { crew: state.crew_id, day: liveDay })}`;
      const dayInp = root.querySelector('#inp-day');
      if (dayInp) dayInp.value = liveDay;
      sendPayload('save_clock');
    }

    const minDueMs = order.reduce((acc, modId) => {
      const d = Number(state.clock.module_due_ms[modId] ?? (scNow + 3600000));
      return Math.min(acc, d);
    }, scNow + 999 * 3600 * 1000);
    const nextDiffMs = minDueMs - scNow;
    const kpiCd = root.querySelector('#kpi-countdown-val');
    if (kpiCd) {
      kpiCd.textContent = formatCountdown(nextDiffMs);
      kpiCd.style.color = nextDiffMs <= 0 ? '#fbbf24' : '#f8fafc';
    }

    root.querySelectorAll('[data-due-mod]').forEach(el => {
      const modId = el.getAttribute('data-due-mod');
      const dueAt = Number(state.clock.module_due_ms[modId] ?? (scNow + 3600000));
      const rem = dueAt - scNow;
      el.textContent = rem <= 0 ? t('rtc_due_now') : t('rtc_due_in', { t: formatCountdown(rem) });
    });

    const dueModules = getDueModules(modulesMap, scNow);
    const slot = root.querySelector('#reminder-slot');
    if (slot) {
      if (dueModules.length && !root.querySelector('#reminder-banner')) {
        render();
        playAlertChime();
        dueModules.forEach(d => { state.chimedKeys[d.module_id] = true; });
      } else if (dueModules.length) {
        let newlyDue = false;
        dueModules.forEach(d => {
          if (!state.chimedKeys[d.module_id]) {
            state.chimedKeys[d.module_id] = true;
            newlyDue = true;
          }
        });
        if (newlyDue) {
          render();
          playAlertChime();
        }
      }
    }
  }, 1000);

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
        f"{HUD_DRAWER_JS}\n"
        f"{HUD_CONTROLLER_BODY_JS}\n"
        "}\n"
    )
