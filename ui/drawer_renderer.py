"""Modular Slide-Over Drawer Renderer (`ui/drawer_renderer.py`).

Implements Plan A:
- Drawer Section Switcher:
  1) `checkin` (Flight Mode & Developer Mode):
     - Contextual Scheduled Due Check-In alert (when triggered by reminder banner or due module)
     - Daily Routine Vitals form (Temp, HR, BP, SpO2, Sleep, Hydration, Stress, Symptoms)
     - Scheduled Subsystem Check-In inputs (contextual per due/selected module)
     - Developer Mode recommended reference ranges (Green / Yellow / Red) + one-click G/Y/R fill chips
  2) `settings` (System & Developer Telemetry):
     - Language toggle, Flight/Developer mode switch, Offline Spacecraft RTC calibration, Crew/Sol
     - Developer Mode full sensor overrides with G/Y/R reference guides
"""

from __future__ import annotations

from ui.checkin_spec import build_checkin_spec_js

HUD_DRAWER_BODY_JS = r"""
  function getFieldLabel(f) {
    return state.lang === 'zh' ? (f.zh || f.en || f.key) : (f.en || f.key);
  }

  function buildRefHintHtml(f, targetKind, targetMod) {
    if (!state.developer_mode || !f.ref) return '';
    const g = f.ref.green || {};
    const y = f.ref.yellow || {};
    const r = f.ref.red || {};
    const encPreset = (val) => esc(JSON.stringify(val));
    return `
      <div class="dev-ref-bar">
        <div class="dev-ref-ranges">
          <span class="ref-tag ref-g">🟢 ${esc(g.range || '')}</span>
          <span class="ref-tag ref-y">🟡 ${esc(y.range || '')}</span>
          <span class="ref-tag ref-r">🔴 ${esc(r.range || '')}</span>
        </div>
        <div class="dev-ref-btns">
          <button type="button" class="ref-fill-btn ref-fill-g" title="${esc(t('dev_fill_g'))}"
                  data-fill-kind="${esc(targetKind)}" data-fill-mod="${esc(targetMod || '')}"
                  data-fill-key="${esc(f.key)}" data-fill-val="${encPreset(g.preset)}">G</button>
          <button type="button" class="ref-fill-btn ref-fill-y" title="${esc(t('dev_fill_y'))}"
                  data-fill-kind="${esc(targetKind)}" data-fill-mod="${esc(targetMod || '')}"
                  data-fill-key="${esc(f.key)}" data-fill-val="${encPreset(y.preset)}">Y</button>
          <button type="button" class="ref-fill-btn ref-fill-r" title="${esc(t('dev_fill_r'))}"
                  data-fill-kind="${esc(targetKind)}" data-fill-mod="${esc(targetMod || '')}"
                  data-fill-key="${esc(f.key)}" data-fill-val="${encPreset(r.preset)}">R</button>
        </div>
      </div>
    `;
  }

  function buildCheckinFieldControl(f, currentVal, kind, modId) {
    const lbl = getFieldLabel(f);
    const refHtml = buildRefHintHtml(f, kind, modId);
    const modAttr = modId ? `data-chk-mod="${esc(modId)}"` : '';

    if (f.type === 'symptoms') {
      const selected = Array.isArray(currentVal) ? currentVal : [];
      const chipsHtml = (CHECKIN_SPEC.symptoms || []).map(sym => {
        const active = selected.includes(sym.id);
        const sLbl = state.lang === 'zh' ? sym.zh : sym.en;
        return `
          <button type="button" class="symptom-chip ${active ? 'active' : ''}" data-symptom-id="${esc(sym.id)}">
            ${active ? '✓ ' : ''}${esc(sLbl)}
          </button>
        `;
      }).join('');
      return `
        <div class="field-group field-span-full">
          <div class="field-label">
            <span>${esc(lbl)}</span>
            <span style="color:#7dd3fc;font-size:10.5px;">${selected.length ? esc(selected.length + ' ' + t('chk_sym_count')) : esc(t('chk_sym_none'))}</span>
          </div>
          <div class="symptom-grid">${chipsHtml}</div>
          ${refHtml}
        </div>
      `;
    }

    if (f.type === 'checkbox') {
      return `
        <div class="field-group checkin-card">
          <label style="display:flex;align-items:center;gap:9px;cursor:pointer;padding:4px 0;">
            <input type="checkbox" data-chk-kind="${esc(kind)}" ${modAttr} data-chk-key="${esc(f.key)}" data-chk-type="checkbox" ${currentVal ? 'checked' : ''} />
            <span class="field-label" style="font-size:12px;color:#e2e8f0;">${esc(lbl)}</span>
          </label>
          ${refHtml}
        </div>
      `;
    }

    if (f.type === 'select') {
      const opts = (f.options || []).map(o => {
        let optTxt = String(o).toUpperCase();
        if (state.lang === 'zh') {
          optTxt = FLOW_OPT_ZH[o] || AMSLER_OPT_ZH[o] || optTxt;
        }
        return `<option value="${esc(o)}" ${currentVal === o ? 'selected' : ''}>${esc(optTxt)}</option>`;
      }).join('');
      return `
        <div class="field-group checkin-card">
          <span class="field-label">${esc(lbl)}</span>
          <select class="field-select" data-chk-kind="${esc(kind)}" ${modAttr} data-chk-key="${esc(f.key)}" data-chk-type="select">${opts}</select>
          ${refHtml}
        </div>
      `;
    }

    const val = (currentVal !== undefined && currentVal !== null) ? currentVal : f.default;
    return `
      <div class="field-group checkin-card">
        <div class="field-label">
          <span>${esc(lbl)}</span>
        </div>
        <div class="num-stepper-row">
          <button type="button" class="step-btn" data-step-dir="-1" data-chk-kind="${esc(kind)}" ${modAttr} data-chk-key="${esc(f.key)}" data-step="${f.step}" data-min="${f.min}" data-max="${f.max}">−</button>
          <input class="field-input num-input" type="number"
                 min="${f.min}" max="${f.max}" step="${f.step}" value="${esc(val)}"
                 data-chk-kind="${esc(kind)}" ${modAttr} data-chk-key="${esc(f.key)}" data-chk-type="number" />
          <button type="button" class="step-btn" data-step-dir="1" data-chk-kind="${esc(kind)}" ${modAttr} data-chk-key="${esc(f.key)}" data-step="${f.step}" data-min="${f.min}" data-max="${f.max}">+</button>
        </div>
        ${refHtml}
      </div>
    `;
  }

  function buildDevOverrideFieldsHtml() {
    const tab = state.drawerTab;
    const cur = state.inputs[tab] || {};
    const fields = (CHECKIN_SPEC.dev_override_fields && CHECKIN_SPEC.dev_override_fields[tab]) || [];

    return fields.map(f => {
      const val = cur[f.key] !== undefined ? cur[f.key] : f.default;
      const lbl = getFieldLabel(f);
      const refHtml = buildRefHintHtml(f, 'dev_override', tab);

      if (f.type === 'checkbox') {
        return `
          <div class="field-group checkin-card">
            <label style="display:flex;align-items:center;gap:9px;padding-top:4px;cursor:pointer;">
              <input type="checkbox" data-input-key="${esc(f.key)}" data-input-type="checkbox" ${val ? 'checked' : ''} />
              <span class="field-label" style="font-size:12px;color:#e2e8f0;">${esc(lbl)}</span>
            </label>
            ${refHtml}
          </div>
        `;
      }
      if (f.type === 'select') {
        const opts = (f.options || []).map(o => {
          const optTxt = state.lang === 'zh' ? (FLOW_OPT_ZH[o] || String(o).toUpperCase()) : String(o).toUpperCase();
          return `<option value="${esc(o)}" ${val === o ? 'selected' : ''}>${esc(optTxt)}</option>`;
        }).join('');
        return `
          <div class="field-group checkin-card">
            <span class="field-label">${esc(lbl)}</span>
            <select class="field-select" data-input-key="${esc(f.key)}" data-input-type="select">${opts}</select>
            ${refHtml}
          </div>
        `;
      }
      return `
        <div class="field-group checkin-card">
          <div class="field-label">
            <span>${esc(lbl)}</span>
            <strong style="color:#38bdf8;" id="lbl-${esc(f.key)}">${esc(val)}</strong>
          </div>
          <input class="field-range" type="range"
                 min="${f.min}" max="${f.max}" step="${f.step}" value="${esc(val)}"
                 data-input-key="${esc(f.key)}" data-input-type="number" />
          ${refHtml}
        </div>
      `;
    }).join('');
  }

  function buildDrawerPanelHtml(modulesMap, order, scNow, dueModules) {
    const dueIds = dueModules.map(d => d.module_id);
    if (!order.includes(state.checkinModuleTab)) {
      state.checkinModuleTab = dueIds[0] || state.selectedModule || order[0];
    }

    const dailyFieldsHtml = (CHECKIN_SPEC.daily_fields || []).map(f => {
      return buildCheckinFieldControl(f, state.dailyVitals[f.key], 'daily', '');
    }).join('');

    const modCheckFields = (CHECKIN_SPEC.module_checkin_fields && CHECKIN_SPEC.module_checkin_fields[state.checkinModuleTab]) || [];
    const modCheckValues = state.moduleCheckins[state.checkinModuleTab] || {};
    const modFieldsHtml = modCheckFields.map(f => {
      return buildCheckinFieldControl(f, modCheckValues[f.key], 'module', state.checkinModuleTab);
    }).join('');

    const dueNoticeHtml = dueModules.length ? `
      <div class="due-context-box">
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
          <span style="font-size:12px;font-weight:700;color:#fde68a;">⏰ ${esc(t('chk_due_context'))}</span>
          ${dueModules.map(d => `<span class="badge badge-${d.status}">${esc(modShortName(d.module_id, d.module_id))}</span>`).join('')}
        </div>
        <span style="font-size:11px;color:#fcd34d;">${esc(t('chk_due_context_sub'))}</span>
      </div>
    ` : '';

    const loggedDays = Object.keys((state.checkinSeries && state.checkinSeries[state.crew_id]) || {})
      .map(Number)
      .filter(n => !isNaN(n))
      .sort((a, b) => a - b);
    const historyTrailHtml = loggedDays.length ? `
      <div class="checkin-trail-bar">
        <span>📈 ${esc(t('chk_logged_days_lbl'))}</span>
        <strong>${loggedDays.map(d => 'D' + d).join(' → ')}</strong>
      </div>
    ` : '';

    const checkinTabHtml = `
      ${buildCrewLifecycleBoxHtml()}
      ${dueNoticeHtml}
      <div class="checkin-meta-bar">
        <span id="chk-crew-day-meta">🧑‍🚀 ${esc(t('crew_badge', { crew: state.crew_id, day: state.mission_day }))}</span>
        <span id="chk-sc-clock-meta" style="color:#7dd3fc;">${esc(formatScDate(scNow))} · ${esc(formatScTime(scNow))}</span>
      </div>
      ${historyTrailHtml}

      <div class="checkin-section">
        <div class="checkin-section-hdr">
          <span>🌅 ${esc(t('chk_sec_daily_title'))}</span>
          <span class="checkin-section-sub">${esc(t('chk_sec_daily_sub'))}</span>
        </div>
        <div class="checkin-grid">
          ${dailyFieldsHtml}
        </div>
      </div>

      <div class="checkin-section">
        <div class="checkin-section-hdr">
          <span>🔬 ${esc(t('chk_sec_mod_title'))}</span>
          <span class="checkin-section-sub">${esc(t('chk_sec_mod_sub'))}</span>
        </div>
        <div class="mod-tabs" style="margin-bottom:8px;">
          ${order.map(modId => {
            const isDue = dueIds.includes(modId);
            const m = modulesMap[modId];
            return `
              <button type="button" class="mod-tab-btn ${state.checkinModuleTab === modId ? 'active' : ''}" data-chk-tab="${esc(modId)}">
                ${isDue ? '⏰ ' : ''}${esc(modShortName(modId, m ? m.short_name : modId))}
              </button>
            `;
          }).join('')}
        </div>
        <div class="checkin-grid">
          ${modFieldsHtml}
        </div>
      </div>

      <div class="drawer-footer">
        ${state.developer_mode ? `
          <div class="dev-quick-row">
            <span style="font-size:10.5px;color:#fbbf24;font-weight:700;">🛠 ${esc(t('dev_quick_lbl'))}</span>
            <button type="button" class="ref-fill-btn ref-fill-g" data-fill-all="green">${esc(t('dev_fill_all_g'))}</button>
            <button type="button" class="ref-fill-btn ref-fill-y" data-fill-all="yellow">${esc(t('dev_fill_all_y'))}</button>
            <button type="button" class="ref-fill-btn ref-fill-r" data-fill-all="red">${esc(t('dev_fill_all_r'))}</button>
          </div>
        ` : ''}
        <button type="button" class="run-btn" id="submit-checkin-btn">${esc(t('chk_submit_btn'))}</button>
      </div>
    `;

    const settingsTabHtml = `
      ${buildCrewLifecycleBoxHtml()}
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

      <div class="dev-toggle-row ${state.developer_mode ? 'active' : ''}">
        <div style="display:flex;flex-direction:column;gap:2px;">
          <span style="font-size:11.5px;font-weight:700;color:#fbbf24;letter-spacing:0.6px;">🛠 ${esc(t('dev_mode_label'))}</span>
          <span style="font-size:11px;color:#94a3b8;">${esc(t('dev_mode_desc'))}</span>
        </div>
        <label class="toggle-switch">
          <input type="checkbox" id="inp-dev-mode" ${state.developer_mode ? 'checked' : ''} />
          <span class="toggle-track"><span class="toggle-thumb"></span></span>
        </label>
      </div>

      <!-- OFFLINE SPACECRAFT RTC CALIBRATION & SIMULATION SPEED -->
      <div class="clock-box">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">
          <div style="display:flex;flex-direction:column;gap:2px;">
            <span style="font-size:11.5px;font-weight:700;color:#38bdf8;letter-spacing:0.6px;">⏱ ${esc(t('clk_section_title'))}</span>
            <span style="font-size:10.5px;color:#94a3b8;">${esc(t('clk_section_desc'))}</span>
          </div>
          <label style="font-size:11px;color:#cbd5e1;display:flex;align-items:center;gap:5px;cursor:pointer;white-space:nowrap;">
            <input type="checkbox" id="inp-clock-sound" ${state.clock.sound_enabled ? 'checked' : ''} />
            ${esc(t('clk_sound_lbl'))}
          </label>
        </div>
        <div class="clock-grid">
          <div class="field-group">
            <span class="field-label">${esc(t('clk_date_lbl'))}</span>
            <input class="field-input" type="date" id="inp-clk-date" value="${esc(formatScDate(scNow))}" />
          </div>
          <div class="field-group">
            <span class="field-label">${esc(t('clk_time_lbl'))}</span>
            <input class="field-input" type="time" step="1" id="inp-clk-time" value="${esc(formatScTime(scNow))}" />
          </div>
          <button class="rem-btn" style="padding:8px 12px;" id="apply-clock-btn">${esc(t('clk_apply_btn'))}</button>
          <button class="rem-btn" style="padding:8px 12px;border-color:rgba(16,185,129,0.5);color:#6ee7b7;" id="sync-earth-now-btn">${esc(t('clk_now_btn'))}</button>
        </div>
        ${state.developer_mode ? `
          <div class="clock-speed-row">
            <div style="display:flex;align-items:center;gap:5px;">
              <span style="font-size:10.5px;color:#94a3b8;font-weight:600;">${esc(t('clk_speed_lbl'))}</span>
              ${[1, 60, 3600].map(sp => `
                <button class="view-pill-btn ${state.clock.time_scale === sp ? 'active' : ''}" data-clk-speed="${sp}">${sp}x</button>
              `).join('')}
            </div>
            <div style="display:flex;align-items:center;gap:5px;">
              <span style="font-size:10.5px;color:#94a3b8;font-weight:600;">${esc(t('clk_jump_lbl'))}</span>
              ${[1, 12, 24].map(hrs => `
                <button class="view-pill-btn" data-clk-jump="${hrs}">+${hrs}H</button>
              `).join('')}
            </div>
          </div>
        ` : ''}
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
        ${state.developer_mode ? `
          <div class="field-group" style="justify-content:center;gap:8px;">
            <label style="font-size:11.5px;color:#cbd5e1;display:flex;align-items:center;gap:6px;cursor:pointer;">
              <input type="checkbox" id="inp-prefer-csv" ${state.prefer_real_csv ? 'checked' : ''} />
              ${esc(t('prefer_csv_lbl'))}
            </label>
            <label style="font-size:11.5px;color:#fbbf24;display:flex;align-items:center;gap:6px;cursor:pointer;">
              <input type="checkbox" id="inp-dev-complete-hist" ${state.dev_complete_history ? 'checked' : ''} />
              ${esc(t('dev_auto_hist_lbl'))}
            </label>
            <label style="font-size:11.5px;color:#38bdf8;font-weight:600;display:flex;align-items:center;gap:6px;cursor:pointer;">
              <input type="checkbox" id="inp-use-manual" ${state.use_manual_overrides ? 'checked' : ''} />
              ${esc(t('enable_manual_lbl'))}
            </label>
          </div>
        ` : ''}
      </div>

      ${state.developer_mode ? `
        <div class="mod-tabs">
          ${order.map(modId => {
            const m = modulesMap[modId];
            return `
              <button class="mod-tab-btn ${state.drawerTab === modId ? 'active' : ''}" data-drawer-tab="${esc(modId)}">
                ${esc(modShortName(modId, m ? m.short_name : modId))}
              </button>
            `;
          }).join('')}
        </div>

        <div class="sliders-grid">
          ${buildDevOverrideFieldsHtml()}
        </div>
      ` : ''}

      <div class="drawer-footer">
        ${state.developer_mode ? `<button class="secondary-btn" id="reset-overrides-btn">${esc(t('reset_btn'))}</button>` : ''}
        <button class="run-btn" id="save-run-btn">${esc(t('save_run_btn'))}</button>
      </div>
    `;

    return `
      <div class="drawer-backdrop ${state.drawerOpen ? 'open' : ''}" id="drawer-backdrop">
        <div class="drawer-panel" id="drawer-panel">
          <div class="drawer-hdr">
            <span class="drawer-title">${esc(state.drawerSection === 'checkin' ? t('chk_drawer_title') : t('drawer_title'))}</span>
            <button class="close-btn" id="close-drawer-btn">${esc(t('close_btn'))}</button>
          </div>

          <div class="drawer-mode-tabs">
            <button type="button" class="guide-tab ${state.drawerSection === 'checkin' ? 'active' : ''}" data-drawer-section="checkin">
              ${esc(t('drawer_tab_checkin'))}
            </button>
            <button type="button" class="guide-tab ${state.drawerSection === 'settings' ? 'active' : ''}" data-drawer-section="settings">
              ${esc(t('drawer_tab_settings'))}
            </button>
          </div>

          ${state.drawerSection === 'checkin' ? checkinTabHtml : settingsTabHtml}
        </div>
      </div>
    `;
  }

  function bindDrawerEvents() {
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

    // Drawer primary section switch (Crew Check-In <-> Settings & Dev Overrides)
    root.querySelectorAll('[data-drawer-section]').forEach(btn => {
      btn.onclick = () => {
        state.drawerSection = btn.getAttribute('data-drawer-section') || 'checkin';
        render();
      };
    });

    // Check-In subsystem tab switch
    root.querySelectorAll('[data-chk-tab]').forEach(btn => {
      btn.onclick = () => {
        state.checkinModuleTab = btn.getAttribute('data-chk-tab') || state.selectedModule;
        render();
      };
    });

    // Symptom multi-select chips
    root.querySelectorAll('[data-symptom-id]').forEach(btn => {
      btn.onclick = () => {
        const sid = btn.getAttribute('data-symptom-id');
        if (!sid) return;
        const list = Array.isArray(state.dailyVitals.symptoms) ? [...state.dailyVitals.symptoms] : [];
        const idx = list.indexOf(sid);
        if (idx >= 0) list.splice(idx, 1);
        else list.push(sid);
        state.dailyVitals.symptoms = list;
        render();
      };
    });

    // Daily & Scheduled Check-In inputs
    root.querySelectorAll('[data-chk-key]').forEach(inp => {
      if (inp.classList.contains('step-btn')) return;
      const kind = inp.getAttribute('data-chk-kind');
      const modId = inp.getAttribute('data-chk-mod') || state.checkinModuleTab;
      const key = inp.getAttribute('data-chk-key');
      const typ = inp.getAttribute('data-chk-type');
      const handler = () => {
        let v = inp.value;
        if (typ === 'number') {
          if (inp.value === '' || isNaN(Number(inp.value))) return;
          v = Number(inp.value);
        } else if (typ === 'checkbox') {
          v = inp.checked;
        }
        if (kind === 'daily') {
          state.dailyVitals[key] = v;
        } else {
          if (!state.moduleCheckins[modId]) state.moduleCheckins[modId] = {};
          state.moduleCheckins[modId][key] = v;
        }
      };
      inp.oninput = handler;
      inp.onchange = handler;
    });

    // Stepper +/- buttons for number fields (update DOM & state directly without full re-render)
    root.querySelectorAll('.step-btn').forEach(btn => {
      btn.onclick = () => {
        const dir = Number(btn.getAttribute('data-step-dir')) || 1;
        const kind = btn.getAttribute('data-chk-kind');
        const modId = btn.getAttribute('data-chk-mod') || state.checkinModuleTab;
        const key = btn.getAttribute('data-chk-key');
        const step = Number(btn.getAttribute('data-step')) || 1;
        const min = Number(btn.getAttribute('data-min'));
        const max = Number(btn.getAttribute('data-max'));
        const curRaw = kind === 'daily'
          ? state.dailyVitals[key]
          : (state.moduleCheckins[modId] && state.moduleCheckins[modId][key]);
        let nextVal = (Number(curRaw) || 0) + dir * step;
        const decimals = (String(step).split('.')[1] || '').length;
        nextVal = Number(nextVal.toFixed(decimals));
        if (!isNaN(min)) nextVal = Math.max(min, nextVal);
        if (!isNaN(max)) nextVal = Math.min(max, nextVal);
        if (kind === 'daily') state.dailyVitals[key] = nextVal;
        else {
          if (!state.moduleCheckins[modId]) state.moduleCheckins[modId] = {};
          state.moduleCheckins[modId][key] = nextVal;
        }
        const row = btn.closest('.num-stepper-row');
        const numInp = row ? row.querySelector('input.num-input') : null;
        if (numInp) numInp.value = nextVal;
      };
    });

    // Developer Mode: one-click G/Y/R fill per field
    root.querySelectorAll('[data-fill-key]').forEach(btn => {
      btn.onclick = () => {
        const kind = btn.getAttribute('data-fill-kind');
        const modId = btn.getAttribute('data-fill-mod');
        const key = btn.getAttribute('data-fill-key');
        const raw = btn.getAttribute('data-fill-val');
        let parsed = raw;
        try { parsed = JSON.parse(raw); } catch (_) {}
        if (kind === 'daily') {
          state.dailyVitals[key] = parsed;
        } else if (kind === 'module') {
          if (!state.moduleCheckins[modId]) state.moduleCheckins[modId] = {};
          state.moduleCheckins[modId][key] = parsed;
        } else if (kind === 'dev_override') {
          if (!state.inputs[modId]) state.inputs[modId] = {};
          state.inputs[modId][key] = parsed;
          state.use_manual_overrides = true;
        }
        render();
      };
    });

    // Developer Mode: Fill ALL active check-in fields with G/Y/R preset
    root.querySelectorAll('[data-fill-all]').forEach(btn => {
      btn.onclick = () => {
        const tier = btn.getAttribute('data-fill-all');
        (CHECKIN_SPEC.daily_fields || []).forEach(f => {
          if (f.ref && f.ref[tier]) {
            state.dailyVitals[f.key] = Array.isArray(f.ref[tier].preset)
              ? [...f.ref[tier].preset]
              : f.ref[tier].preset;
          }
        });
        const modFields = (CHECKIN_SPEC.module_checkin_fields && CHECKIN_SPEC.module_checkin_fields[state.checkinModuleTab]) || [];
        if (!state.moduleCheckins[state.checkinModuleTab]) state.moduleCheckins[state.checkinModuleTab] = {};
        modFields.forEach(f => {
          if (f.ref && f.ref[tier]) {
            state.moduleCheckins[state.checkinModuleTab][f.key] = f.ref[tier].preset;
          }
        });
        render();
      };
    });

    // Submit Crew Daily Check-In -> persist day point, reset ONLY active module due timer, re-run 5 agents
    const submitChkBtn = root.querySelector('#submit-checkin-btn');
    if (submitChkBtn) {
      submitChkBtn.onclick = () => {
        const scNow = getSpacecraftNowMs();
        const modulesMap = data.modules || {};
        const targetMod = state.checkinModuleTab;
        const checkedMods = [targetMod];

        // Clear only the submitted module from due banner while keeping other unlogged due modules intact
        const nextH = Number((modulesMap[targetMod] && modulesMap[targetMod].short_term_plan && modulesMap[targetMod].short_term_plan.next_measurement_in_hours) ?? 24);
        const resetH = nextH > 0 ? nextH : 1;
        state.clock.module_due_ms[targetMod] = scNow + resetH * 3600 * 1000;
        delete state.chimedKeys[targetMod];

        const remainingDue = getDueModules(modulesMap, scNow);
        if (remainingDue.length) {
          // Keep drawer open and advance to the next remaining due module so crew can clear them one by one
          state.checkinModuleTab = remainingDue[0].module_id;
          state.drawerOpen = true;
          state.drawerScrollTop = 0;
        } else {
          state.drawerOpen = false;
        }

        sendPayload('submit_daily_checkin', {
          daily_vitals: state.dailyVitals,
          module_checkins: state.moduleCheckins,
          checked_modules: checkedMods,
          active_checkin_module: targetMod,
        });
      };
    }

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

    // Developer Mode toggle inside Settings Drawer
    const devModeChk = root.querySelector('#inp-dev-mode');
    if (devModeChk) {
      devModeChk.onchange = () => {
        state.developer_mode = devModeChk.checked;
        if (!state.developer_mode) {
          state.scenario = 'green';
          state.prefer_real_csv = true;
          state.use_manual_overrides = false;
          state.clock.spacecraft_epoch_ms = getSpacecraftNowMs();
          state.clock.host_epoch_ms = Date.now();
          state.clock.time_scale = 1;
          state.clock.module_due_ms = {};
          state.chimedKeys = {};
        }
        render();
        sendPayload('toggle_developer_mode');
      };
    }

    // Drawer Offline Clock Controls
    const soundChk = root.querySelector('#inp-clock-sound');
    if (soundChk) {
      soundChk.onchange = () => {
        state.clock.sound_enabled = soundChk.checked;
      };
    }

    const applyClkBtn = root.querySelector('#apply-clock-btn');
    if (applyClkBtn) {
      applyClkBtn.onclick = () => {
        const dEl = root.querySelector('#inp-clk-date');
        const tEl = root.querySelector('#inp-clk-time');
        if (dEl && tEl && dEl.value && tEl.value) {
          const tStr = tEl.value.length === 5 ? `${tEl.value}:00` : tEl.value;
          const parsed = new Date(`${dEl.value}T${tStr}`).getTime();
          if (!isNaN(parsed)) {
            const oldNow = getSpacecraftNowMs();
            const shift = parsed - oldNow;
            state.clock.spacecraft_epoch_ms = parsed;
            state.clock.host_epoch_ms = Date.now();
            state.mission_day = computeMccMissionDay(parsed);
            Object.keys(state.clock.module_due_ms).forEach(k => {
              state.clock.module_due_ms[k] = Number(state.clock.module_due_ms[k]) + shift;
            });
            render();
            sendPayload('save_clock');
          }
        }
      };
    }

    const syncNowBtn = root.querySelector('#sync-earth-now-btn');
    if (syncNowBtn) {
      syncNowBtn.onclick = () => {
        const nowMs = Date.now();
        state.clock.spacecraft_epoch_ms = nowMs;
        state.clock.host_epoch_ms = nowMs;
        state.clock.time_scale = 1;
        state.clock.module_due_ms = {};
        state.chimedKeys = {};
        state.mission_day = computeMccMissionDay(nowMs);
        render();
        sendPayload('sync_earth_now');
      };
    }

    root.querySelectorAll('[data-clk-speed]').forEach(btn => {
      btn.onclick = () => {
        const sp = Number(btn.getAttribute('data-clk-speed')) || 1;
        const scNow = getSpacecraftNowMs();
        state.clock.spacecraft_epoch_ms = scNow;
        state.clock.host_epoch_ms = Date.now();
        state.clock.time_scale = sp;
        state.mission_day = computeMccMissionDay(scNow);
        render();
        sendPayload('save_clock');
      };
    });

    root.querySelectorAll('[data-clk-jump]').forEach(btn => {
      btn.onclick = () => {
        const hrs = Number(btn.getAttribute('data-clk-jump')) || 1;
        const nextMs = getSpacecraftNowMs() + hrs * 3600 * 1000;
        state.clock.spacecraft_epoch_ms = nextMs;
        state.clock.host_epoch_ms = Date.now();
        state.mission_day = computeMccMissionDay(nextMs);
        render();
        sendPayload('save_clock');
      };
    });

    // Drawer module tabs (Developer Overrides)
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
    if (inpDay) {
      inpDay.onchange = () => {
        const newDay = Math.max(1, Number(inpDay.value) || 124);
        const scNow = getSpacecraftNowMs();
        state.mission_day = newDay;
        state.clock.anchor_midnight_ms = localMidnightMs(scNow);
        state.clock.anchor_mission_day = newDay;
      };
    }

    const inpPreferCsv = root.querySelector('#inp-prefer-csv');
    if (inpPreferCsv) inpPreferCsv.onchange = () => { state.prefer_real_csv = inpPreferCsv.checked; };

    const inpDevHist = root.querySelector('#inp-dev-complete-hist');
    if (inpDevHist) {
      inpDevHist.onchange = () => {
        state.dev_complete_history = inpDevHist.checked;
        sendPayload('toggle_dev_complete_history');
      };
    }

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
        state.clock.module_due_ms = {};
        state.chimedKeys = {};
        sendPayload('save_and_run');
      };
    }

    // Reset manual overrides
    const resetBtn = root.querySelector('#reset-overrides-btn');
    if (resetBtn) {
      resetBtn.onclick = () => {
        state.use_manual_overrides = false;
        state.drawerOpen = false;
        state.clock.module_due_ms = {};
        state.chimedKeys = {};
        sendPayload('reset_overrides');
      };
    }
  }
"""

HUD_DRAWER_JS = build_checkin_spec_js() + "\n" + HUD_DRAWER_BODY_JS
