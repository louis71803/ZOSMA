"""Mission Briefing Onboarding Bar & Multi-Crew Selector UI (`ui/onboarding_bar.py`).

Role 1 exclusively owns this file.
Implements Stage 2:
1. Top collapsible 30-second Mission Briefing Quick-Start Banner (`buildOnboardingBannerHtml`)
   - Step 1: Hardware Auto-Online (`Cabin & Rad`) vs. Physiological Pre-Flight Baseline (`STANDBY`)
   - Step 2: Log Initial In-Orbit Check-In (`📝 START DAY-1 CHECK-IN` button)
   - Step 3: 3-Step Autonomous Protocol & Reviewer Quick-Load (`⚡ LOAD DAY-124 DATASET` button)
2. Multi-Crew Selector & Add-Crew Controls (`buildCrewSelectorBarHtml`)
3. Developer / Mission Data Lifecycle Controls (`Day-1 Cold Start` <-> `Day-124 Full Dataset`)
"""

from __future__ import annotations

HUD_ONBOARDING_JS = r"""
  function buildOnboardingBannerHtml(modulesMap) {
    if (!state.guideBannerOpen) return '';

    const standbyCount = Object.values(modulesMap || {}).filter(m => m && m.standby).length;
    const isDay1Mode = state.data_lifecycle_mode === 'day1_standby';

    const modeBadge = isDay1Mode
      ? `<span class="onb-mode-pill standby">${esc(t('onb_mode_day1'))} · ${standbyCount} ${esc(t('onb_standby_cnt'))}</span>`
      : `<span class="onb-mode-pill active">${esc(t('onb_mode_day124'))}</span>`;

    return `
      <div class="onboarding-banner" id="onboarding-banner">
        <div class="onb-hdr">
          <div class="onb-title-row">
            <span class="onb-icon">🚀</span>
            <span class="onb-title">${esc(t('onb_title'))}</span>
            ${modeBadge}
          </div>
          <div class="onb-hdr-actions">
            ${isDay1Mode ? `
              <button type="button" class="onb-quick124-btn" id="onb-load-124-btn" title="${esc(t('onb_load124_tip'))}">
                ${esc(t('onb_load124_btn'))}
              </button>
            ` : `
              <button type="button" class="onb-quick124-btn" id="onb-reset-day1-btn">
                ${esc(t('onb_reset_day1_btn'))}
              </button>
            `}
            <button type="button" class="onb-dismiss-btn" id="onb-dismiss-btn">
              ${esc(t('onb_dismiss_btn'))}
            </button>
          </div>
        </div>

        <div class="onb-steps-grid">
          <div class="onb-step-card">
            <div class="onb-step-num">STEP 01</div>
            <div class="onb-step-title">${esc(t('onb_s1_title'))}</div>
            <div class="onb-step-desc">${esc(t('onb_s1_desc'))}</div>
          </div>

          <div class="onb-step-card highlight">
            <div class="onb-step-num">STEP 02</div>
            <div class="onb-step-title">${esc(t('onb_s2_title'))}</div>
            <div class="onb-step-desc">${esc(t('onb_s2_desc'))}</div>
            <button type="button" class="onb-cta-btn" id="onb-start-checkin-btn">
              ${esc(t('onb_s2_btn'))}
            </button>
          </div>

          <div class="onb-step-card">
            <div class="onb-step-num">STEP 03</div>
            <div class="onb-step-title">${esc(state.developer_mode ? t('onb_s3_dev_title') : t('onb_s3_title'))}</div>
            <div class="onb-step-desc">${esc(state.developer_mode ? t('onb_s3_dev_desc') : t('onb_s3_desc'))}</div>
          </div>
        </div>
      </div>
    `;
  }

  function buildCrewLifecycleBoxHtml() {
    const roster = Array.isArray(data.crew_roster) ? data.crew_roster : [];
    const isDay1 = state.data_lifecycle_mode === 'day1_standby';

    const crewPillsHtml = roster.map(c => {
      const active = c.crew_id === state.crew_id;
      const roleLbl = state.lang === 'zh' ? (c.role_zh || c.role_en || '') : (c.role_en || '');
      return `
        <button type="button" class="crew-select-pill ${active ? 'active' : ''}" data-select-crew="${esc(c.crew_id)}" title="${esc(roleLbl)}">
          <strong>${esc(c.crew_id)}</strong>
          <span>${esc(roleLbl)}</span>
        </button>
      `;
    }).join('');

    return `
      <div class="crew-lifecycle-box">
        <div class="checkin-section-hdr" style="padding-bottom:5px;">
          <span>👨‍🚀 ${esc(t('crew_roster_title'))}</span>
          <span class="checkin-section-sub">${esc(t('crew_roster_sub'))}</span>
        </div>

        <div class="crew-pills-wrap">
          ${crewPillsHtml}
        </div>

        <div class="add-crew-row">
          <input class="field-input" id="inp-new-crew-id" placeholder="${esc(t('add_crew_ph'))}" style="flex:1;min-width:110px;" />
          <input class="field-input" id="inp-new-crew-role" placeholder="${esc(t('add_crew_role_ph'))}" style="flex:1.4;min-width:130px;" />
          <button type="button" class="rem-btn" id="create-crew-btn" style="padding:7px 11px;white-space:nowrap;">
            ${esc(t('add_crew_btn'))}
          </button>
        </div>

        <div class="lifecycle-switch-row">
          <div style="display:flex;flex-direction:column;gap:2px;">
            <span style="font-size:11px;font-weight:700;color:#7dd3fc;">📡 ${esc(t('lifecycle_lbl'))}</span>
            <span style="font-size:10.5px;color:#94a3b8;">${esc(isDay1 ? t('lifecycle_day1_desc') : t('lifecycle_day124_desc'))}</span>
          </div>
          <div class="lifecycle-btns">
            <button type="button" class="view-pill-btn ${isDay1 ? 'active' : ''}" id="btn-mode-day1">
              ${esc(t('btn_day1_cold'))}
            </button>
            <button type="button" class="view-pill-btn ${!isDay1 ? 'active' : ''}" id="btn-mode-day124">
              ${esc(t('btn_day124_full'))}
            </button>
          </div>
        </div>
      </div>
    `;
  }

  function bindOnboardingAndCrewEvents() {
    const guideToggleBtn = root.querySelector('#toggle-guide-btn');
    if (guideToggleBtn) {
      guideToggleBtn.onclick = () => {
        state.guideBannerOpen = !state.guideBannerOpen;
        render();
      };
    }

    const dismissBtn = root.querySelector('#onb-dismiss-btn');
    if (dismissBtn) {
      dismissBtn.onclick = () => {
        state.guideBannerOpen = false;
        state.onboarding_completed = true;
        render();
        sendPayload('dismiss_onboarding');
      };
    }

    const startChkBtn = root.querySelector('#onb-start-checkin-btn');
    if (startChkBtn) {
      startChkBtn.onclick = () => {
        state.drawerSection = 'checkin';
        state.checkinModuleTab = 'cardiovascular';
        state.drawerOpen = true;
        state.drawerScrollTop = 0;
        render();
      };
    }

    const load124Btn = root.querySelector('#onb-load-124-btn');
    if (load124Btn) {
      load124Btn.onclick = () => {
        state.data_lifecycle_mode = 'day124_showcase';
        state.mission_day = 124;
        state.clock.anchor_midnight_ms = localMidnightMs(getSpacecraftNowMs());
        state.clock.anchor_mission_day = 124;
        state.clock.module_due_ms = {};
        state.chimedKeys = {};
        state.guideBannerOpen = false;
        state.onboarding_completed = true;
        sendPayload('switch_lifecycle_mode', { data_lifecycle_mode: 'day124_showcase', mission_day: 124 });
      };
    }

    const resetDay1BannerBtn = root.querySelector('#onb-reset-day1-btn');
    if (resetDay1BannerBtn) {
      resetDay1BannerBtn.onclick = () => {
        state.data_lifecycle_mode = 'day1_standby';
        state.mission_day = 1;
        state.clock.anchor_midnight_ms = localMidnightMs(getSpacecraftNowMs());
        state.clock.anchor_mission_day = 1;
        state.clock.module_due_ms = {};
        state.chimedKeys = {};
        state.guideBannerOpen = true;
        state.onboarding_completed = false;
        sendPayload('switch_lifecycle_mode', { data_lifecycle_mode: 'day1_standby', mission_day: 1 });
      };
    }

    // Crew roster pill click -> switch active astronaut profile
    root.querySelectorAll('[data-select-crew]').forEach(btn => {
      btn.onclick = () => {
        const nextCrew = btn.getAttribute('data-select-crew');
        if (nextCrew && nextCrew !== state.crew_id) {
          state.crew_id = nextCrew;
          state.clock.module_due_ms = {};
          state.chimedKeys = {};
          sendPayload('switch_crew', { crew_id: nextCrew });
        }
      };
    });

    // Create / Add new astronaut profile in data/crew_records/<ID>.json
    const createCrewBtn = root.querySelector('#create-crew-btn');
    if (createCrewBtn) {
      createCrewBtn.onclick = () => {
        const idEl = root.querySelector('#inp-new-crew-id');
        const roleEl = root.querySelector('#inp-new-crew-role');
        const rawId = idEl ? idEl.value.trim().toUpperCase() : '';
        const rawRole = roleEl ? roleEl.value.trim() : '';
        if (!rawId) return;
        state.crew_id = rawId;
        state.data_lifecycle_mode = 'day1_standby';
        state.mission_day = 1;
        state.clock.anchor_midnight_ms = localMidnightMs(getSpacecraftNowMs());
        state.clock.anchor_mission_day = 1;
        state.clock.module_due_ms = {};
        state.chimedKeys = {};
        state.guideBannerOpen = true;
        sendPayload('create_crew', {
          crew_id: rawId,
          role_label: rawRole,
          data_lifecycle_mode: 'day1_standby',
          mission_day: 1
        });
      };
    }

    // Lifecycle mode buttons inside Drawer
    const btnDay1 = root.querySelector('#btn-mode-day1');
    if (btnDay1) {
      btnDay1.onclick = () => {
        state.data_lifecycle_mode = 'day1_standby';
        state.mission_day = 1;
        state.clock.anchor_midnight_ms = localMidnightMs(getSpacecraftNowMs());
        state.clock.anchor_mission_day = 1;
        state.clock.module_due_ms = {};
        state.chimedKeys = {};
        state.guideBannerOpen = true;
        state.onboarding_completed = false;
        sendPayload('switch_lifecycle_mode', { data_lifecycle_mode: 'day1_standby', mission_day: 1 });
      };
    }

    const btnDay124 = root.querySelector('#btn-mode-day124');
    if (btnDay124) {
      btnDay124.onclick = () => {
        state.data_lifecycle_mode = 'day124_showcase';
        state.mission_day = 124;
        state.clock.anchor_midnight_ms = localMidnightMs(getSpacecraftNowMs());
        state.clock.anchor_mission_day = 124;
        state.clock.module_due_ms = {};
        state.chimedKeys = {};
        state.guideBannerOpen = false;
        state.onboarding_completed = true;
        sendPayload('switch_lifecycle_mode', { data_lifecycle_mode: 'day124_showcase', mission_day: 124 });
      };
    }
  }
"""
