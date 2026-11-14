"""Holographic 5-Module Anatomy & Habitat SVG Generators (`ui/anatomy_svgs.py`).

Provides unified SpaceX/NASA dark-HUD vector visualizations:
- `overview`: All-systems astronaut + habitat node map
- `cabin_environment`: Dynamic color-coded radiation shield & ECLSS habitat field
- `musculoskeletal`: Toggleable Front (`front`) & Back (`back`) muscle groups + spine
- `cardiovascular`: Animated heart, bilateral neck IJV veins, aorta, and lower-limb vessels
- `immune_metabolic`: Streamlined hypothalamus, thyroid, thymus/lymph nodes, and kidneys/adrenals
- `neuro_ocular`: Default magnified Eye Cross-Section + Vestibular Labyrinth (`eye_zoom`) & Full CNS (`cns_full`)

Every anatomical region dynamically lights up (Cyan/Green -> Amber -> Pulsing Red)
based on real-time Python metric statuses, and clicking an organ jumps the center
3-Layer Trend Chart directly to that indicator.
"""

from __future__ import annotations

HUD_ANATOMY_JS = r"""
  const ORGAN_NORMAL_FILL = 'rgba(56, 189, 248, 0.18)';
  const ORGAN_NORMAL_STROKE = '#38bdf8';

  function findMetricIndex(modObj, candidateNames) {
    const list = (modObj && modObj.metrics) || [];
    for (let c = 0; c < candidateNames.length; c++) {
      const idx = list.findIndex(m => m.metric_name === candidateNames[c]);
      if (idx >= 0) return idx;
    }
    return 0;
  }

  function worstMetricStatus(modObj, candidateNames) {
    const list = (modObj && modObj.metrics) || [];
    const rank = { GREEN: 0, YELLOW: 1, QC: 2, RED: 3 };
    let best = 'GREEN';
    let matched = false;
    candidateNames.forEach(name => {
      const m = list.find(it => it.metric_name === name);
      if (m) {
        matched = true;
        const st = !m.quality_passed ? 'QC' : (m.status_light || 'GREEN');
        if ((rank[st] || 0) > (rank[best] || 0)) best = st;
      }
    });
    if (!matched && modObj) {
      return statusKey(modObj);
    }
    return best;
  }

  function metricSummaryText(modObj, candidateNames) {
    const list = (modObj && modObj.metrics) || [];
    for (let i = 0; i < candidateNames.length; i++) {
      const m = list.find(it => it.metric_name === candidateNames[i]);
      if (m) {
        return `${metricLabel(m.metric_name)}: ${m.current_val}${m.unit ? ' ' + m.unit : ''} [${m.status_light}]`;
      }
    }
    return '';
  }

  function organPalette(st, isSelectedMetric) {
    if (st === 'RED') {
      return {
        fill: 'rgba(239, 68, 68, 0.48)',
        stroke: '#f87171',
        text: '#fca5a5',
        cls: 'organ-alert-RED'
      };
    }
    if (st === 'YELLOW') {
      return {
        fill: 'rgba(245, 158, 11, 0.42)',
        stroke: '#fbbf24',
        text: '#fde68a',
        cls: 'organ-alert-YELLOW'
      };
    }
    if (st === 'QC') {
      return {
        fill: 'rgba(249, 115, 22, 0.40)',
        stroke: '#fb923c',
        text: '#fdba74',
        cls: 'organ-alert-YELLOW'
      };
    }
    // Nominal GREEN -> calm holographic cyan/emerald
    return {
      fill: isSelectedMetric ? 'rgba(56, 189, 248, 0.34)' : 'rgba(16, 185, 129, 0.22)',
      stroke: isSelectedMetric ? '#38bdf8' : '#34d399',
      text: isSelectedMetric ? '#7dd3fc' : '#a7f3d0',
      cls: ''
    };
  }

  function baseAstronautShellSvg(strokeColor = 'rgba(125,211,252,0.42)') {
    return `
      <g class="holo-shell">
        <circle cx="150" cy="56" r="22" fill="rgba(15,23,42,0.55)" stroke="${strokeColor}" stroke-width="1.4" />
        <path d="M 140 78 L 160 78
                 L 186 90 C 197 95, 203 106, 205 122
                 L 212 184 C 213 191, 201 193, 198 185
                 L 188 128 L 179 128
                 L 176 200
                 L 183 302 C 184 311, 168 312, 166 302
                 L 155 218 L 145 218
                 L 134 302 C 132 312, 116 311, 117 302
                 L 124 200
                 L 121 128 L 112 128
                 L 102 185 C 99 193, 87 191, 88 184
                 L 95 122 C 97 106, 103 95, 114 90 Z"
              fill="rgba(15,23,42,0.55)" stroke="${strokeColor}" stroke-width="1.4" stroke-linejoin="round" />
      </g>
    `;
  }

  /* 0. OVERVIEW ALL-SYSTEMS NODE MAP */
  function buildOverviewSvg(modulesMap) {
    const cab = modulesMap['cabin_environment'];
    const cabHex = STATUS_HEX[statusKey(cab)] || '#38bdf8';

    const nodes = [
      { id: 'cabin_environment', label: t('node_cabin'),   x: 54,  y: 50,  lx: 16,  ly: 26 },
      { id: 'neuro_ocular',      label: t('node_neuro'),   x: 150, y: 56,  lx: 214, ly: 52 },
      { id: 'cardiovascular',    label: t('node_cardio'),  x: 156, y: 126, lx: 214, ly: 122 },
      { id: 'immune_metabolic',  label: t('node_immune'),  x: 146, y: 180, lx: 214, ly: 182 },
      { id: 'musculoskeletal',   label: t('node_musculo'), x: 133, y: 262, lx: 214, ly: 264 }
    ];

    const nodesSvg = nodes.map(n => {
      const m = modulesMap[n.id];
      const sk = statusKey(m);
      const hex = STATUS_HEX[sk] || '#10b981';
      const isSel = state.selectedModule === n.id;
      const pulseClass = sk === 'RED' ? 'pulse-ring-fast' : 'pulse-ring';
      return `
        <g class="hotspot-group" data-mod="${n.id}">
          <title>${esc(modFullName(n.id, n.label))}</title>
          <line x1="${n.x}" y1="${n.y}" x2="${n.lx - 4}" y2="${n.ly - 3}"
                stroke="${isSel ? '#38bdf8' : 'rgba(148,163,184,0.4)'}"
                stroke-width="${isSel ? '1.6' : '1'}" stroke-dasharray="${isSel ? 'none' : '3,3'}" />
          <circle cx="${n.x}" cy="${n.y}" r="${isSel ? 12 : 9}" fill="${hex}" opacity="0.28" class="${pulseClass}" />
          ${isSel ? `<circle cx="${n.x}" cy="${n.y}" r="14" fill="none" stroke="#38bdf8" stroke-width="1.6" />` : ''}
          <circle class="node-core" cx="${n.x}" cy="${n.y}" r="${isSel ? 6.2 : 5}" fill="${hex}" stroke="#f8fafc" stroke-width="1.4" />
          <text x="${n.lx}" y="${n.ly}" fill="${isSel ? '#38bdf8' : '#cbd5e1'}"
                font-size="9.5" font-weight="${isSel ? '700' : '600'}" letter-spacing="0.7">
            ${esc(n.label)}
          </text>
        </g>
      `;
    }).join('');

    return `
      <svg class="bio-svg" viewBox="0 0 330 335" xmlns="http://www.w3.org/2000/svg">
        <rect x="10" y="10" width="310" height="315" rx="16"
              fill="none" stroke="${cabHex}" stroke-opacity="0.45" stroke-width="1.4" stroke-dasharray="6,4" />
        <circle cx="150" cy="170" r="92" fill="none" stroke="rgba(56,189,248,0.08)" stroke-width="1" />
        <circle cx="150" cy="170" r="126" fill="none" stroke="rgba(56,189,248,0.05)" stroke-width="1" />
        ${baseAstronautShellSvg('rgba(125,211,252,0.58)')}
        <line x1="150" y1="82" x2="150" y2="202" stroke="rgba(56,189,248,0.2)" stroke-width="1" stroke-dasharray="2,3" />
        ${nodesSvg}
      </svg>
    `;
  }

  /* 1. CABIN ENVIRONMENT & RADIATION HOLOGRAPHIC SHIELD */
  function buildCabinEnvSvg(modObj) {
    const overallSk = statusKey(modObj);
    const themeMap = {
      GREEN:  { primary: '#38bdf8', shield: 'rgba(14, 165, 233, 0.16)', wave: 'rgba(56, 189, 248, 0.28)' },
      YELLOW: { primary: '#f59e0b', shield: 'rgba(245, 158, 11, 0.22)', wave: 'rgba(251, 191, 36, 0.42)' },
      RED:    { primary: '#ef4444', shield: 'rgba(239, 68, 68, 0.28)',  wave: 'rgba(248, 113, 113, 0.62)' },
      QC:     { primary: '#f97316', shield: 'rgba(249, 115, 22, 0.22)', wave: 'rgba(251, 146, 60, 0.45)' }
    };
    const th = themeMap[overallSk] || themeMap.GREEN;

    const radCandidates = ['proton_flux_10mev_pfu', 'dose_rate_uGy_h', 'career_dose_mSv'];
    const atmCandidates = ['ppco2_1h_mmHg', 'p_total_kPa', 'pio2_mmHg', 'max_smac_ratio'];
    const acoCandidates = ['crew_leq8_dBA', 'module_spl_dBA', 'audiogram_sts_max_dB'];
    const isoCandidates = ['sleep_tst_h', 'pvt_speed_1_per_s', 'circadian_midpoint_shift_h'];

    const radIdx = findMetricIndex(modObj, radCandidates);
    const atmIdx = findMetricIndex(modObj, atmCandidates);
    const acoIdx = findMetricIndex(modObj, acoCandidates);
    const isoIdx = findMetricIndex(modObj, isoCandidates);

    const radPal = organPalette(worstMetricStatus(modObj, radCandidates), state.selectedMetricIdx === radIdx);
    const atmPal = organPalette(worstMetricStatus(modObj, atmCandidates), state.selectedMetricIdx === atmIdx);
    const acoPal = organPalette(worstMetricStatus(modObj, acoCandidates), state.selectedMetricIdx === acoIdx);
    const isoPal = organPalette(worstMetricStatus(modObj, isoCandidates), state.selectedMetricIdx === isoIdx);

    return `
      <svg class="bio-svg" viewBox="0 0 330 335" xmlns="http://www.w3.org/2000/svg">
        <!-- Outer Spacecraft Pressure Hull & Radiation Water-Wall Shield -->
        <rect x="10" y="10" width="310" height="315" rx="22"
              fill="${th.shield}" stroke="${th.primary}" stroke-width="2" />
        <rect x="20" y="20" width="290" height="295" rx="16"
              fill="none" stroke="${th.wave}" stroke-width="1.3" stroke-dasharray="8,4" />

        <!-- Solar Proton / Cosmic Ray Wave Arcs (Top-Left & Top-Right) -->
        <g class="organ-zone ${radPal.cls}" data-organ-metric="${radIdx}">
          <title>${esc(t('organ_rad_shield'))} · ${esc(metricSummaryText(modObj, radCandidates))}</title>
          <path d="M 28 76 Q 165 18 302 76" fill="none" stroke="${radPal.stroke}" stroke-width="2.4" />
          <path d="M 44 92 Q 165 40 286 92" fill="none" stroke="${radPal.stroke}" stroke-width="1.5" stroke-dasharray="5,3" />
          <rect x="22" y="26" width="112" height="24" rx="6" fill="rgba(5,10,22,0.82)" stroke="${radPal.stroke}" stroke-width="1.2" />
          <text x="78" y="41" fill="${radPal.text}" font-size="9" font-weight="700" text-anchor="middle">${esc(t('organ_rad_shield'))}</text>
        </g>

        <!-- Central Protected Crew Silhouette -->
        <g transform="translate(15, 22) scale(0.9)">
          ${baseAstronautShellSvg(th.primary)}
        </g>

        <!-- Atmosphere CO2 / Pressure Airflow Loop -->
        <g class="organ-zone ${atmPal.cls}" data-organ-metric="${atmIdx}">
          <title>${esc(t('organ_atm_co2'))} · ${esc(metricSummaryText(modObj, atmCandidates))}</title>
          <ellipse cx="165" cy="158" rx="68" ry="32" fill="${atmPal.fill}" stroke="${atmPal.stroke}" stroke-width="1.5" stroke-dasharray="6,3" />
          <rect x="196" y="26" width="112" height="24" rx="6" fill="rgba(5,10,22,0.82)" stroke="${atmPal.stroke}" stroke-width="1.2" />
          <text x="252" y="41" fill="${atmPal.text}" font-size="9" font-weight="700" text-anchor="middle">${esc(t('organ_atm_co2'))}</text>
        </g>

        <!-- Acoustic SPL Waves (Left Hull) -->
        <g class="organ-zone ${acoPal.cls}" data-organ-metric="${acoIdx}">
          <title>${esc(t('organ_acoustics'))} · ${esc(metricSummaryText(modObj, acoCandidates))}</title>
          <path d="M 38 155 Q 52 175 38 195 M 48 148 Q 66 175 48 202" fill="none" stroke="${acoPal.stroke}" stroke-width="2" stroke-linecap="round" />
          <rect x="22" y="284" width="116" height="24" rx="6" fill="rgba(5,10,22,0.82)" stroke="${acoPal.stroke}" stroke-width="1.2" />
          <text x="80" y="299" fill="${acoPal.text}" font-size="9" font-weight="700" text-anchor="middle">${esc(t('organ_acoustics'))}</text>
        </g>

        <!-- Sleep & Circadian Lighting Zone (Right Hull) -->
        <g class="organ-zone ${isoPal.cls}" data-organ-metric="${isoIdx}">
          <title>${esc(t('organ_circadian'))} · ${esc(metricSummaryText(modObj, isoCandidates))}</title>
          <circle cx="278" cy="175" r="14" fill="${isoPal.fill}" stroke="${isoPal.stroke}" stroke-width="1.6" />
          <path d="M 274 167 A 9 9 0 1 0 285 181 A 7 7 0 1 1 274 167 Z" fill="${isoPal.stroke}" />
          <rect x="192" y="284" width="116" height="24" rx="6" fill="rgba(5,10,22,0.82)" stroke="${isoPal.stroke}" stroke-width="1.2" />
          <text x="250" y="299" fill="${isoPal.text}" font-size="9" font-weight="700" text-anchor="middle">${esc(t('organ_circadian'))}</text>
        </g>
      </svg>
    `;
  }

  /* 2. MUSCULOSKELETAL ANATOMY (FRONT & BACK TOGGLEABLE) */
  function buildMusculoSvg(modObj, side = 'front') {
    const thighCand = ['csa_thigh_cm2'];
    const calfCand  = ['csa_calf_cm2'];
    const boneCand  = ['ctx_bone_resorption', 'ntx_bone_resorption', 'est_monthly_bone_loss_pct', 'e4d_s_bone_index'];
    const coreCand  = ['velocity_loss_pct', 'iso_peak_force_n', 'body_mass_kg'];

    const thighIdx = findMetricIndex(modObj, thighCand);
    const calfIdx  = findMetricIndex(modObj, calfCand);
    const boneIdx  = findMetricIndex(modObj, boneCand);
    const coreIdx  = findMetricIndex(modObj, coreCand);

    const thighPal = organPalette(worstMetricStatus(modObj, thighCand), state.selectedMetricIdx === thighIdx);
    const calfPal  = organPalette(worstMetricStatus(modObj, calfCand), state.selectedMetricIdx === calfIdx);
    const bonePal  = organPalette(worstMetricStatus(modObj, boneCand), state.selectedMetricIdx === boneIdx);
    const corePal  = organPalette(worstMetricStatus(modObj, coreCand), state.selectedMetricIdx === coreIdx);

    if (side === 'back') {
      return `
        <svg class="bio-svg" viewBox="0 0 330 335" xmlns="http://www.w3.org/2000/svg">
          ${baseAstronautShellSvg('rgba(148,163,184,0.38)')}

          <!-- Posterior Spine Vertebrae & Pelvis Bone Axis -->
          <g class="organ-zone ${bonePal.cls}" data-organ-metric="${boneIdx}">
            <title>${esc(t('organ_spine_bone'))} · ${esc(metricSummaryText(modObj, boneCand))}</title>
            <line x1="150" y1="80" x2="150" y2="192" stroke="${bonePal.stroke}" stroke-width="4" stroke-dasharray="5,3" />
            <path d="M 129 186 Q 150 202 171 186 L 165 205 Q 150 212 135 205 Z"
                  fill="${bonePal.fill}" stroke="${bonePal.stroke}" stroke-width="1.5" />
            <line x1="154" y1="96" x2="218" y2="66" stroke="${bonePal.stroke}" stroke-width="1" stroke-dasharray="3,2" />
            <text x="222" y="69" fill="${bonePal.text}" font-size="9" font-weight="700">${esc(t('organ_spine_bone'))}</text>
          </g>

          <!-- Trapezius / Latissimus / Erector Spinae -->
          <g class="organ-zone ${corePal.cls}" data-organ-metric="${coreIdx}">
            <title>${esc(t('organ_erector'))} · ${esc(metricSummaryText(modObj, coreCand))}</title>
            <path d="M 124 94 L 146 88 L 146 174 L 128 162 Z" fill="${corePal.fill}" stroke="${corePal.stroke}" stroke-width="1.3" />
            <path d="M 176 94 L 154 88 L 154 174 L 172 162 Z" fill="${corePal.fill}" stroke="${corePal.stroke}" stroke-width="1.3" />
            <line x1="176" y1="128" x2="218" y2="124" stroke="${corePal.stroke}" stroke-width="1" stroke-dasharray="3,2" />
            <text x="222" y="127" fill="${corePal.text}" font-size="9" font-weight="700">${esc(t('organ_erector'))}</text>
          </g>

          <!-- Gluteus Maximus & Posterior Hamstrings -->
          <g class="organ-zone ${thighPal.cls}" data-organ-metric="${thighIdx}">
            <title>${esc(t('organ_glute_ham'))} · ${esc(metricSummaryText(modObj, thighCand))}</title>
            <ellipse cx="138" cy="198" rx="13" ry="12" fill="${thighPal.fill}" stroke="${thighPal.stroke}" stroke-width="1.4" />
            <ellipse cx="162" cy="198" rx="13" ry="12" fill="${thighPal.fill}" stroke="${thighPal.stroke}" stroke-width="1.4" />
            <path d="M 126 212 Q 137 210 144 214 L 141 254 Q 133 257 125 252 Z" fill="${thighPal.fill}" stroke="${thighPal.stroke}" stroke-width="1.5" />
            <path d="M 174 212 Q 163 210 156 214 L 159 254 Q 167 257 175 252 Z" fill="${thighPal.fill}" stroke="${thighPal.stroke}" stroke-width="1.5" />
            <line x1="175" y1="230" x2="218" y2="218" stroke="${thighPal.stroke}" stroke-width="1.1" stroke-dasharray="3,2" />
            <text x="222" y="221" fill="${thighPal.text}" font-size="9" font-weight="700">${esc(t('organ_glute_ham'))}</text>
          </g>

          <!-- Posterior Calves (Gastrocnemius & Soleus) -->
          <g class="organ-zone ${calfPal.cls}" data-organ-metric="${calfIdx}">
            <title>${esc(t('organ_calves'))} · ${esc(metricSummaryText(modObj, calfCand))}</title>
            <path d="M 123 258 C 118 272, 120 288, 126 298 L 136 298 C 141 286, 141 272, 138 258 Z"
                  fill="${calfPal.fill}" stroke="${calfPal.stroke}" stroke-width="1.6" />
            <path d="M 177 258 C 182 272, 180 288, 174 298 L 164 298 C 159 286, 159 272, 162 258 Z"
                  fill="${calfPal.fill}" stroke="${calfPal.stroke}" stroke-width="1.6" />
            <line x1="179" y1="278" x2="218" y2="278" stroke="${calfPal.stroke}" stroke-width="1.1" stroke-dasharray="3,2" />
            <text x="222" y="281" fill="${calfPal.text}" font-size="9" font-weight="700">${esc(t('organ_calves'))}</text>
          </g>
        </svg>
      `;
    }

    // Default FRONT Muscle & Bone View
    return `
      <svg class="bio-svg" viewBox="0 0 330 335" xmlns="http://www.w3.org/2000/svg">
        ${baseAstronautShellSvg('rgba(148,163,184,0.38)')}

        <!-- Pectorals & Abdominal Core (VBT / Peak Force) -->
        <g class="organ-zone ${corePal.cls}" data-organ-metric="${coreIdx}">
          <title>${esc(t('organ_core_pect'))} · ${esc(metricSummaryText(modObj, coreCand))}</title>
          <path d="M 124 96 Q 137 92 148 98 L 148 122 Q 134 124 123 116 Z" fill="${corePal.fill}" stroke="${corePal.stroke}" stroke-width="1.4" />
          <path d="M 176 96 Q 163 92 152 98 L 152 122 Q 166 124 177 116 Z" fill="${corePal.fill}" stroke="${corePal.stroke}" stroke-width="1.4" />
          <rect x="137" y="128" width="26" height="48" rx="6" fill="${corePal.fill}" stroke="${corePal.stroke}" stroke-width="1.3" />
          <line x1="150" y1="128" x2="150" y2="176" stroke="${corePal.stroke}" stroke-width="1" />
          <line x1="137" y1="144" x2="163" y2="144" stroke="${corePal.stroke}" stroke-width="1" />
          <line x1="137" y1="160" x2="163" y2="160" stroke="${corePal.stroke}" stroke-width="1" />
          <line x1="177" y1="110" x2="216" y2="102" stroke="${corePal.stroke}" stroke-width="1" stroke-dasharray="3,2" />
          <text x="220" y="105" fill="${corePal.text}" font-size="9" font-weight="700">${esc(t('organ_core_pect'))}</text>
        </g>

        <!-- Pelvis & Femoral Neck Bone Turnover (CTX / NTX / S_bone) -->
        <g class="organ-zone ${bonePal.cls}" data-organ-metric="${boneIdx}">
          <title>${esc(t('organ_spine_bone'))} · ${esc(metricSummaryText(modObj, boneCand))}</title>
          <path d="M 128 182 Q 150 196 172 182 L 166 202 Q 150 210 134 202 Z"
                fill="${bonePal.fill}" stroke="${bonePal.stroke}" stroke-width="1.6" />
          <line x1="170" y1="190" x2="216" y2="168" stroke="${bonePal.stroke}" stroke-width="1" stroke-dasharray="3,2" />
          <text x="220" y="171" fill="${bonePal.text}" font-size="9" font-weight="700">${esc(t('organ_spine_bone'))}</text>
        </g>

        <!-- Anterior Thigh Quadriceps (csa_thigh_cm2) -->
        <g class="organ-zone ${thighPal.cls}" data-organ-metric="${thighIdx}">
          <title>${esc(t('organ_quads'))} · ${esc(metricSummaryText(modObj, thighCand))}</title>
          <path d="M 125 204 Q 137 200 145 208 L 142 254 Q 133 258 124 250 Z"
                fill="${thighPal.fill}" stroke="${thighPal.stroke}" stroke-width="1.7" />
          <path d="M 175 204 Q 163 200 155 208 L 158 254 Q 167 258 176 250 Z"
                fill="${thighPal.fill}" stroke="${thighPal.stroke}" stroke-width="1.7" />
          <line x1="176" y1="228" x2="216" y2="224" stroke="${thighPal.stroke}" stroke-width="1.1" stroke-dasharray="3,2" />
          <text x="220" y="227" fill="${thighPal.text}" font-size="9" font-weight="700">${esc(t('organ_quads'))}</text>
        </g>

        <!-- Anterior Lower Leg / Calf Group (csa_calf_cm2) -->
        <g class="organ-zone ${calfPal.cls}" data-organ-metric="${calfIdx}">
          <title>${esc(t('organ_calves'))} · ${esc(metricSummaryText(modObj, calfCand))}</title>
          <path d="M 123 260 Q 131 256 138 260 L 135 298 L 124 298 Z"
                fill="${calfPal.fill}" stroke="${calfPal.stroke}" stroke-width="1.6" />
          <path d="M 177 260 Q 169 256 162 260 L 165 298 L 176 298 Z"
                fill="${calfPal.fill}" stroke="${calfPal.stroke}" stroke-width="1.6" />
          <line x1="177" y1="280" x2="216" y2="280" stroke="${calfPal.stroke}" stroke-width="1.1" stroke-dasharray="3,2" />
          <text x="220" y="283" fill="${calfPal.text}" font-size="9" font-weight="700">${esc(t('organ_calves'))}</text>
        </g>
      </svg>
    `;
  }

  /* 3. CARDIOVASCULAR & VASCULAR TREE */
  function buildCardioSvg(modObj) {
    const ijvCand   = ['ijv_flow_status'];
    const heartCand = ['rest_hr_bpm', 'pvc_burden_pct', 'gls_change_pct', 'steady_hr_150w_bpm'];
    const aortaCand = ['sbp_mmHg', 'spo2_pct', 'resp_rate_bpm'];
    const lowerCand = ['stand_hr_rise_bpm', 'plasma_volume_delta_pct', 'potassium_mmol_l'];

    const ijvIdx   = findMetricIndex(modObj, ijvCand);
    const heartIdx = findMetricIndex(modObj, heartCand);
    const aortaIdx = findMetricIndex(modObj, aortaCand);
    const lowerIdx = findMetricIndex(modObj, lowerCand);

    const ijvSt   = worstMetricStatus(modObj, ijvCand);
    const heartSt = worstMetricStatus(modObj, heartCand);
    const aortaSt = worstMetricStatus(modObj, aortaCand);
    const lowerSt = worstMetricStatus(modObj, lowerCand);

    const ijvPal   = organPalette(ijvSt, state.selectedMetricIdx === ijvIdx);
    const heartPal = organPalette(heartSt, state.selectedMetricIdx === heartIdx);
    const aortaPal = organPalette(aortaSt, state.selectedMetricIdx === aortaIdx);
    const lowerPal = organPalette(lowerSt, state.selectedMetricIdx === lowerIdx);

    const heartAnim = (heartSt === 'RED' || heartSt === 'YELLOW') ? 'heart-anim-fast' : 'heart-anim-normal';

    return `
      <svg class="bio-svg" viewBox="0 0 330 335" xmlns="http://www.w3.org/2000/svg">
        ${baseAstronautShellSvg('rgba(148,163,184,0.34)')}

        <!-- Lower Limb Arterial & Venous Return Tree -->
        <g class="organ-zone ${lowerPal.cls}" data-organ-metric="${lowerIdx}">
          <title>${esc(t('organ_lower_vasc'))} · ${esc(metricSummaryText(modObj, lowerCand))}</title>
          <path d="M 150 184 L 134 235 L 129 294 M 150 184 L 166 235 L 171 294"
                fill="none" stroke="${lowerPal.stroke}" stroke-width="2.2" stroke-linecap="round" />
          <path d="M 146 186 L 138 242 L 134 292 M 154 186 L 162 242 L 166 292"
                fill="none" stroke="#38bdf8" stroke-opacity="0.65" stroke-width="1.4" stroke-dasharray="4,2" />
          <line x1="168" y1="252" x2="214" y2="252" stroke="${lowerPal.stroke}" stroke-width="1" stroke-dasharray="3,2" />
          <text x="218" y="255" fill="${lowerPal.text}" font-size="9" font-weight="700">${esc(t('organ_lower_vasc'))}</text>
        </g>

        <!-- Aortic Arch, Brachial & Abdominal Aorta -->
        <g class="organ-zone ${aortaPal.cls}" data-organ-metric="${aortaIdx}">
          <title>${esc(t('organ_aorta'))} · ${esc(metricSummaryText(modObj, aortaCandidatesFallback(aortaCand)))}</title>
          <path d="M 152 116 C 152 98, 166 98, 164 114 L 150 184
                   M 152 104 L 116 118 L 98 175
                   M 158 104 L 184 118 L 202 175"
                fill="none" stroke="${aortaPal.stroke}" stroke-width="2.5" stroke-linecap="round" />
          <line x1="184" y1="118" x2="214" y2="108" stroke="${aortaPal.stroke}" stroke-width="1" stroke-dasharray="3,2" />
          <text x="218" y="111" fill="${aortaPal.text}" font-size="9" font-weight="700">${esc(t('organ_aorta'))}</text>
        </g>

        <!-- Bilateral Neck Internal Jugular Veins (IJV Stasis / Clot Target) -->
        <g class="organ-zone ${ijvPal.cls}" data-organ-metric="${ijvIdx}">
          <title>${esc(t('organ_ijv'))} · ${esc(metricSummaryText(modObj, ijvCand))}</title>
          <path d="M 142 66 L 140 104 M 158 66 L 160 104"
                fill="none" stroke="${ijvPal.stroke}" stroke-width="3.6" stroke-linecap="round" />
          <circle cx="141" cy="84" r="3.5" fill="${ijvPal.stroke}" />
          <circle cx="159" cy="84" r="3.5" fill="${ijvPal.stroke}" />
          <line x1="162" y1="82" x2="214" y2="66" stroke="${ijvPal.stroke}" stroke-width="1.1" stroke-dasharray="3,2" />
          <text x="218" y="69" fill="${ijvPal.text}" font-size="9" font-weight="700">${esc(t('organ_ijv'))}</text>
        </g>

        <!-- Central Animated Heart -->
        <g class="organ-zone ${heartAnim} ${heartPal.cls}" data-organ-metric="${heartIdx}">
          <title>${esc(t('organ_heart'))} · ${esc(metricSummaryText(modObj, heartCand))}</title>
          <path d="M 156 122
                   C 156 115, 145 114, 145 123
                   C 145 131, 156 138, 158 142
                   C 162 138, 170 130, 169 122
                   C 169 114, 159 115, 156 122 Z"
                fill="${heartPal.fill}" stroke="${heartPal.stroke}" stroke-width="2" />
          <line x1="171" y1="130" x2="214" y2="152" stroke="${heartPal.stroke}" stroke-width="1.1" stroke-dasharray="3,2" />
          <text x="218" y="155" fill="${heartPal.text}" font-size="9" font-weight="700">${esc(t('organ_heart'))}</text>
        </g>
      </svg>
    `;
  }

  function aortaCandidatesFallback(c) { return c; }

  /* 4. IMMUNE, ENDOCRINE & METABOLIC STREAMLINED GLANDULAR MAP */
  function buildImmuneSvg(modObj) {
    const tempCand   = ['oral_temp_c'];
    const thyrCand   = ['crp_mg_l'];
    const lymphCand  = ['lymphocytes_10e9_l', 'saliva_vzv_copies_ml', 'neutrophil_qc_ratio'];
    const renalCand  = ['hydration_ml'];

    const tempIdx  = findMetricIndex(modObj, tempCand);
    const thyrIdx  = findMetricIndex(modObj, thyrCand);
    const lymphIdx = findMetricIndex(modObj, lymphCand);
    const renalIdx = findMetricIndex(modObj, renalCand);

    const tempPal  = organPalette(worstMetricStatus(modObj, tempCand), state.selectedMetricIdx === tempIdx);
    const thyrPal  = organPalette(worstMetricStatus(modObj, thyrCand), state.selectedMetricIdx === thyrIdx);
    const lymphPal = organPalette(worstMetricStatus(modObj, lymphCand), state.selectedMetricIdx === lymphIdx);
    const renalPal = organPalette(worstMetricStatus(modObj, renalCand), state.selectedMetricIdx === renalIdx);

    return `
      <svg class="bio-svg" viewBox="0 0 330 335" xmlns="http://www.w3.org/2000/svg">
        ${baseAstronautShellSvg('rgba(148,163,184,0.36)')}

        <!-- Hypothalamus / Pineal Thermoregulation Center -->
        <g class="organ-zone ${tempPal.cls}" data-organ-metric="${tempIdx}">
          <title>${esc(t('organ_hypothal'))} · ${esc(metricSummaryText(modObj, tempCand))}</title>
          <circle cx="150" cy="52" r="6" fill="${tempPal.fill}" stroke="${tempPal.stroke}" stroke-width="1.6" />
          <circle cx="150" cy="52" r="2.5" fill="${tempPal.stroke}" />
          <line x1="158" y1="52" x2="212" y2="48" stroke="${tempPal.stroke}" stroke-width="1" stroke-dasharray="3,2" />
          <text x="216" y="51" fill="${tempPal.text}" font-size="9" font-weight="700">${esc(t('organ_hypothal'))}</text>
        </g>

        <!-- Butterfly Thyroid Gland -->
        <g class="organ-zone ${thyrPal.cls}" data-organ-metric="${thyrIdx}">
          <title>${esc(t('organ_thyroid'))} · ${esc(metricSummaryText(modObj, thyrCand))}</title>
          <path d="M 144 82 C 141 78, 141 90, 146 88 L 150 86 L 154 88 C 159 90, 159 78, 156 82 L 150 84 Z"
                fill="${thyrPal.fill}" stroke="${thyrPal.stroke}" stroke-width="1.6" />
          <line x1="160" y1="85" x2="212" y2="86" stroke="${thyrPal.stroke}" stroke-width="1" stroke-dasharray="3,2" />
          <text x="216" y="89" fill="${thyrPal.text}" font-size="9" font-weight="700">${esc(t('organ_thyroid'))}</text>
        </g>

        <!-- Thymus, Spleen & Thoracic Lymphatic Network -->
        <g class="organ-zone ${lymphPal.cls}" data-organ-metric="${lymphIdx}">
          <title>${esc(t('organ_thymus_lymph'))} · ${esc(metricSummaryText(modObj, lymphCand))}</title>
          <polygon points="150,102 142,118 150,128 158,118" fill="${lymphPal.fill}" stroke="${lymphPal.stroke}" stroke-width="1.6" />
          <!-- Axillary & Cervical Lymph Nodes + Vessels -->
          <line x1="150" y1="88" x2="150" y2="104" stroke="${lymphPal.stroke}" stroke-width="1.1" stroke-dasharray="2,2" />
          <line x1="142" y1="114" x2="124" y2="118" stroke="${lymphPal.stroke}" stroke-width="1.1" stroke-dasharray="2,2" />
          <line x1="158" y1="114" x2="176" y2="118" stroke="${lymphPal.stroke}" stroke-width="1.1" stroke-dasharray="2,2" />
          <circle cx="124" cy="118" r="3.5" fill="${lymphPal.fill}" stroke="${lymphPal.stroke}" stroke-width="1.3" />
          <circle cx="176" cy="118" r="3.5" fill="${lymphPal.fill}" stroke="${lymphPal.stroke}" stroke-width="1.3" />
          <!-- Spleen -->
          <ellipse cx="168" cy="146" rx="6" ry="9" fill="${lymphPal.fill}" stroke="${lymphPal.stroke}" stroke-width="1.4" />
          <line x1="180" y1="118" x2="212" y2="132" stroke="${lymphPal.stroke}" stroke-width="1" stroke-dasharray="3,2" />
          <text x="216" y="135" fill="${lymphPal.text}" font-size="9" font-weight="700">${esc(t('organ_thymus_lymph'))}</text>
        </g>

        <!-- Bilateral Kidneys + Adrenal Glands (Hydration / Renal Stone & Cortisol Stress) -->
        <g class="organ-zone ${renalPal.cls}" data-organ-metric="${renalIdx}">
          <title>${esc(t('organ_adrenal_kidney'))} · ${esc(metricSummaryText(modObj, renalCand))}</title>
          <!-- Left & Right Kidneys -->
          <path d="M 138 158 C 130 156, 129 176, 138 175 C 142 174, 142 160, 138 158 Z"
                fill="${renalPal.fill}" stroke="${renalPal.stroke}" stroke-width="1.6" />
          <path d="M 162 158 C 170 156, 171 176, 162 175 C 158 174, 158 160, 162 158 Z"
                fill="${renalPal.fill}" stroke="${renalPal.stroke}" stroke-width="1.6" />
          <!-- Adrenal Caps -->
          <polygon points="133,156 139,151 141,157" fill="${renalPal.stroke}" opacity="0.85" />
          <polygon points="167,156 161,151 159,157" fill="${renalPal.stroke}" opacity="0.85" />
          <!-- Ureters -->
          <path d="M 140 172 L 146 198 M 160 172 L 154 198" fill="none" stroke="${renalPal.stroke}" stroke-width="1.1" stroke-opacity="0.7" />
          <line x1="171" y1="168" x2="212" y2="182" stroke="${renalPal.stroke}" stroke-width="1" stroke-dasharray="3,2" />
          <text x="216" y="185" fill="${renalPal.text}" font-size="9" font-weight="700">${esc(t('organ_adrenal_kidney'))}</text>
        </g>
      </svg>
    `;
  }

  /* 5. NEURO-OCULAR & VESTIBULAR (DEFAULT: MAGNIFIED EYE + VESTIBULAR; TOGGLE: FULL CNS) */
  function buildNeuroSvg(modObj, subview = 'eye_zoom') {
    const trtCand  = ['delta_trt_um', 'oct_scan_qc'];
    const onhCand  = ['delta_v_onh_mm3'];
    const onsdCand = ['onsd_mm'];
    const sphCand  = ['sph_eq_shift_d'];
    const vorCand  = ['vor_gain'];

    const trtIdx  = findMetricIndex(modObj, trtCand);
    const onhIdx  = findMetricIndex(modObj, onhCand);
    const onsdIdx = findMetricIndex(modObj, onsdCand);
    const sphIdx  = findMetricIndex(modObj, sphCand);
    const vorIdx  = findMetricIndex(modObj, vorCand);

    const trtPal  = organPalette(worstMetricStatus(modObj, trtCand), state.selectedMetricIdx === trtIdx);
    const onhPal  = organPalette(worstMetricStatus(modObj, onhCand), state.selectedMetricIdx === onhIdx);
    const onsdPal = organPalette(worstMetricStatus(modObj, onsdCand), state.selectedMetricIdx === onsdIdx);
    const sphPal  = organPalette(worstMetricStatus(modObj, sphCand), state.selectedMetricIdx === sphIdx);
    const vorPal  = organPalette(worstMetricStatus(modObj, vorCand), state.selectedMetricIdx === vorIdx);

    if (subview === 'cns_full') {
      return `
        <svg class="bio-svg" viewBox="0 0 330 335" xmlns="http://www.w3.org/2000/svg">
          ${baseAstronautShellSvg('rgba(148,163,184,0.34)')}

          <!-- Cerebral Cortex & Ocular Pathways -->
          <g class="organ-zone ${trtPal.cls}" data-organ-metric="${trtIdx}">
            <title>${esc(t('organ_brain_cortex'))} · ${esc(metricSummaryText(modObj, trtCand))}</title>
            <ellipse cx="150" cy="48" rx="16" ry="12" fill="${trtPal.fill}" stroke="${trtPal.stroke}" stroke-width="1.6" />
            <circle cx="143" cy="58" r="3.5" fill="${trtPal.stroke}" />
            <circle cx="157" cy="58" r="3.5" fill="${trtPal.stroke}" />
            <line x1="168" y1="48" x2="212" y2="48" stroke="${trtPal.stroke}" stroke-width="1" stroke-dasharray="3,2" />
            <text x="216" y="51" fill="${trtPal.text}" font-size="9" font-weight="700">${esc(t('organ_brain_cortex'))}</text>
          </g>

          <!-- Inner Ear Vestibular Nuclei -->
          <g class="organ-zone ${vorPal.cls}" data-organ-metric="${vorIdx}">
            <title>${esc(t('organ_vestibular'))} · ${esc(metricSummaryText(modObj, vorCand))}</title>
            <circle cx="131" cy="58" r="4" fill="${vorPal.fill}" stroke="${vorPal.stroke}" stroke-width="1.5" />
            <circle cx="169" cy="58" r="4" fill="${vorPal.fill}" stroke="${vorPal.stroke}" stroke-width="1.5" />
            <line x1="174" y1="58" x2="212" y2="86" stroke="${vorPal.stroke}" stroke-width="1" stroke-dasharray="3,2" />
            <text x="216" y="89" fill="${vorPal.text}" font-size="9" font-weight="700">${esc(t('organ_vestibular'))}</text>
          </g>

          <!-- Spinal Cord & Peripheral Plexus Branches -->
          <g class="organ-zone ${onsdPal.cls}" data-organ-metric="${onsdIdx}">
            <title>${esc(t('organ_spinal_cord'))} · ${esc(metricSummaryText(modObj, onsdCand))}</title>
            <line x1="150" y1="62" x2="150" y2="196" stroke="${onsdPal.stroke}" stroke-width="3" />
            <path d="M 150 92 L 112 118 L 98 175
                     M 150 92 L 188 118 L 202 175
                     M 150 186 L 132 242 L 128 294
                     M 150 186 L 168 242 L 172 294"
                  fill="none" stroke="#38bdf8" stroke-opacity="0.65" stroke-width="1.4" />
            <line x1="154" y1="142" x2="212" y2="142" stroke="${onsdPal.stroke}" stroke-width="1" stroke-dasharray="3,2" />
            <text x="216" y="145" fill="${onsdPal.text}" font-size="9" font-weight="700">${esc(t('organ_spinal_cord'))}</text>
          </g>
        </svg>
      `;
    }

    // DEFAULT: MAGNIFIED HOLOGRAPHIC EYE CROSS-SECTION + VESTIBULAR LABYRINTH
    return `
      <svg class="bio-svg" viewBox="0 0 330 335" xmlns="http://www.w3.org/2000/svg">
        <!-- Tactical Reticle Grid -->
        <circle cx="118" cy="142" r="82" fill="none" stroke="rgba(56,189,248,0.10)" stroke-width="1" stroke-dasharray="4,4" />
        <line x1="22" y1="142" x2="295" y2="142" stroke="rgba(56,189,248,0.12)" stroke-width="1" stroke-dasharray="3,3" />

        <!-- Outer Sclera Eye Globe -->
        <circle cx="112" cy="142" r="62" fill="rgba(8,18,38,0.88)" stroke="rgba(125,211,252,0.55)" stroke-width="2" />

        <!-- Anterior Cornea & Crystalline Lens (Hyperopic Shift / Globe Flattening) -->
        <g class="organ-zone ${sphPal.cls}" data-organ-metric="${sphIdx}">
          <title>${esc(t('organ_cornea_lens'))} · ${esc(metricSummaryText(modObj, sphCand))}</title>
          <path d="M 56 112 C 34 126, 34 158, 56 172" fill="${sphPal.fill}" stroke="${sphPal.stroke}" stroke-width="2.2" />
          <ellipse cx="68" cy="142" rx="9" ry="24" fill="${sphPal.fill}" stroke="${sphPal.stroke}" stroke-width="1.8" />
          <!-- Optical focal rays -->
          <path d="M 24 126 L 68 130 L 166 142 M 24 158 L 68 154 L 166 142"
                fill="none" stroke="${sphPal.stroke}" stroke-opacity="0.55" stroke-width="1" stroke-dasharray="3,2" />
          <line x1="68" y1="114" x2="92" y2="44" stroke="${sphPal.stroke}" stroke-width="1" stroke-dasharray="3,2" />
          <text x="96" y="46" fill="${sphPal.text}" font-size="9" font-weight="700">${esc(t('organ_cornea_lens'))}</text>
        </g>

        <!-- Posterior Retina / Macula Arc (Delta TRT) -->
        <g class="organ-zone ${trtPal.cls}" data-organ-metric="${trtIdx}">
          <title>${esc(t('organ_retina_trt'))} · ${esc(metricSummaryText(modObj, trtCand))}</title>
          <path d="M 136 88 A 56 56 0 0 1 136 196" fill="none" stroke="${trtPal.stroke}" stroke-width="6" stroke-linecap="round" />
          <line x1="154" y1="98" x2="196" y2="74" stroke="${trtPal.stroke}" stroke-width="1.1" stroke-dasharray="3,2" />
          <text x="200" y="77" fill="${trtPal.text}" font-size="9" font-weight="700">${esc(t('organ_retina_trt'))}</text>
        </g>

        <!-- Distended Optic Nerve Sheath (ONSD 3mm behind globe) -->
        <g class="organ-zone ${onsdPal.cls}" data-organ-metric="${onsdIdx}">
          <title>${esc(t('organ_onsd_sheath'))} · ${esc(metricSummaryText(modObj, onsdCand))}</title>
          <path d="M 170 122 C 205 118, 245 122, 286 126
                   L 286 158
                   C 245 162, 205 166, 170 162 Z"
                fill="${onsdPal.fill}" stroke="${onsdPal.stroke}" stroke-width="2" />
          <!-- 3mm behind globe caliper marker -->
          <line x1="192" y1="116" x2="192" y2="168" stroke="#38bdf8" stroke-width="1.3" stroke-dasharray="2,2" />
          <line x1="224" y1="162" x2="224" y2="202" stroke="${onsdPal.stroke}" stroke-width="1.1" stroke-dasharray="3,2" />
          <text x="180" y="215" fill="${onsdPal.text}" font-size="9" font-weight="700">${esc(t('organ_onsd_sheath'))}</text>
        </g>

        <!-- Optic Nerve Head / Disc Edema (Delta V_ONH) -->
        <g class="organ-zone ${onhPal.cls}" data-organ-metric="${onhIdx}">
          <title>${esc(t('organ_onh_disc'))} · ${esc(metricSummaryText(modObj, onhCand))}</title>
          <ellipse cx="170" cy="142" rx="9" ry="16" fill="${onhPal.fill}" stroke="${onhPal.stroke}" stroke-width="2.2" />
          <line x1="176" y1="130" x2="206" y2="104" stroke="${onhPal.stroke}" stroke-width="1.1" stroke-dasharray="3,2" />
          <text x="210" y="106" fill="${onhPal.text}" font-size="9" font-weight="700">${esc(t('organ_onh_disc'))}</text>
        </g>

        <!-- Inner-Ear Vestibular Semicircular Canals & Cochlea (Bottom Inset) -->
        <g class="organ-zone ${vorPal.cls}" data-organ-metric="${vorIdx}">
          <title>${esc(t('organ_vestibular'))} · ${esc(metricSummaryText(modObj, vorCand))}</title>
          <rect x="24" y="236" width="282" height="78" rx="12" fill="rgba(6,13,28,0.82)" stroke="rgba(56,189,248,0.22)" stroke-width="1.2" />
          <!-- 3 Orthogonal Semicircular Canals -->
          <ellipse cx="76" cy="274" rx="22" ry="11" transform="rotate(-28 76 274)" fill="none" stroke="${vorPal.stroke}" stroke-width="2" />
          <ellipse cx="76" cy="274" rx="22" ry="11" transform="rotate(35 76 274)" fill="none" stroke="${vorPal.stroke}" stroke-width="2" />
          <circle cx="76" cy="274" r="13" fill="${vorPal.fill}" stroke="${vorPal.stroke}" stroke-width="1.6" />
          <!-- Spiral Cochlea -->
          <path d="M 94 276 C 108 266, 118 278, 108 288 C 100 294, 94 286, 102 280" fill="none" stroke="${vorPal.stroke}" stroke-width="2" />
          <text x="132" y="269" fill="${vorPal.text}" font-size="10" font-weight="700">${esc(t('organ_vestibular'))}</text>
          <text x="132" y="286" fill="#94a3b8" font-size="9.5">${esc(metricSummaryText(modObj, vorCand))}</text>
        </g>
      </svg>
    `;
  }

  function buildHolographicStage(modulesMap) {
    if (state.viewMode === 'overview') {
      return buildOverviewSvg(modulesMap);
    }
    const modObj = modulesMap[state.selectedModule];
    switch (state.selectedModule) {
      case 'cabin_environment':
        return buildCabinEnvSvg(modObj);
      case 'musculoskeletal':
        return buildMusculoSvg(modObj, state.musculoSide);
      case 'cardiovascular':
        return buildCardioSvg(modObj);
      case 'immune_metabolic':
        return buildImmuneSvg(modObj);
      case 'neuro_ocular':
      default:
        return buildNeuroSvg(modObj, state.neuroView);
    }
  }
"""
