(() => {
  'use strict';

  const EVAL_STORAGE_KEY = 'daycare_eval_2026_state_v1';
  const ORG_STORAGE_KEY = 'welfarego.daycare.org.v1';
  const FONT_STORAGE_KEY = 'welfarego.daycare.font.v1';
  const THEME_STORAGE_KEY = 'welfarego.daycare.theme.v1';
  const STAFF_SIM_STORAGE_KEY = 'welfarego.daycare.staffsim.v1';

  const DOMAINS = [
    { code: '01', name: '기관운영', max: 27, color: '#2151c8' },
    { code: '02', name: '수급자 존중', max: 18, color: '#1a8fd8' },
    { code: '03', name: '서비스 제공', max: 33, color: '#1f8a4c' },
    { code: '04', name: '서비스 결과', max: 22, color: '#d9770a' },
  ];

  function esc(str) {
    return String(str ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function fmtNum(n) {
    return String(Math.round(n * 100) / 100);
  }

  function fmtWon(n) {
    return Math.round(n).toLocaleString('ko-KR') + '원';
  }

  function showToast(msg) {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.hidden = false;
    clearTimeout(window.__govToastTimer);
    window.__govToastTimer = setTimeout(() => { t.hidden = true; }, 2500);
  }

  function readSavedEval() {
    try {
      const raw = localStorage.getItem(EVAL_STORAGE_KEY);
      if (raw) return JSON.parse(raw);
    } catch (_) {}
    return {};
  }

  function evalCriterionResult(ind, crit, scores) {
    const optIdx = scores[`${ind.id}_${crit.no}`] ?? 0;
    const opt = crit.options[optIdx] || crit.options[0];
    if (crit.linkedTo) {
      const parentCrit = ind.criteria.find(c => c.no === crit.linkedTo);
      if (parentCrit) {
        const pOpt = parentCrit.options[scores[`${ind.id}_${parentCrit.no}`] ?? 0] || parentCrit.options[0];
        if (pOpt.score === 0 && !pOpt.isNA) {
          return { score: 0, isNA: false, lockedByLink: true, optIdx };
        }
      }
    }
    return { score: opt.score, isNA: !!opt.isNA, lockedByLink: false, optIdx };
  }

  function computeEvalSummary(indicators, scores, docChecks) {
    let totalObtained = 0;
    let totalValidMax = 0;
    const domainStats = {};
    DOMAINS.forEach(d => { domainStats[d.name] = { obtained: 0, validMax: 0, pct: 0, indTotal: 0, indReady: 0 }; });

    let totalDocs = 0;
    let checkedDocs = 0;
    let readyIndicators = 0;

    indicators.forEach(ind => {
      domainStats[ind.domain].indTotal++;
      ind.criteria.forEach(c => {
        const res = evalCriterionResult(ind, c, scores);
        if (!res.isNA) {
          totalObtained = Math.round((totalObtained + res.score) * 100) / 100;
          totalValidMax = Math.round((totalValidMax + c.maxScore) * 100) / 100;
          domainStats[ind.domain].obtained = Math.round((domainStats[ind.domain].obtained + res.score) * 100) / 100;
          domainStats[ind.domain].validMax = Math.round((domainStats[ind.domain].validMax + c.maxScore) * 100) / 100;
        }
      });
      const dCount = ind.docs ? ind.docs.length : (ind.docsCount || 0);
      let indChecked = 0;
      for (let i = 0; i < dCount; i++) {
        totalDocs++;
        if (docChecks[`${ind.id}_${i}`]) {
          checkedDocs++;
          indChecked++;
        }
      }
      if (dCount > 0 && indChecked === dCount) {
        readyIndicators++;
        domainStats[ind.domain].indReady++;
      }
    });

    const normalizedTotal = totalValidMax > 0 ? (totalObtained / totalValidMax) * 100 : 0;
    let minDomainPct = 100;
    const weakDomainsA = [];
    DOMAINS.forEach(d => {
      const st = domainStats[d.name];
      st.pct = st.validMax > 0 ? (st.obtained / st.validMax) * 100 : 100;
      if (st.pct < minDomainPct) minDomainPct = st.pct;
      if (st.pct < 70) weakDomainsA.push(`${d.name}(${st.pct.toFixed(1)}%)`);
    });

    let grade = 'E', gradeLabel = 'E등급 (미흡)';
    if (normalizedTotal >= 90 && minDomainPct >= 70) { grade = 'A'; gradeLabel = 'A등급 (최우수)'; }
    else if (normalizedTotal >= 80 && minDomainPct >= 60) { grade = 'B'; gradeLabel = 'B등급 (우수)'; }
    else if (normalizedTotal >= 70 && minDomainPct >= 50) { grade = 'C'; gradeLabel = 'C등급 (양호)'; }
    else if (normalizedTotal >= 60 && minDomainPct >= 40) { grade = 'D'; gradeLabel = 'D등급 (보통)'; }

    const docPct = totalDocs > 0 ? Math.round((checkedDocs / totalDocs) * 100) : 0;
    return { totalObtained, totalValidMax, normalizedTotal, domainStats, grade, gradeLabel, weakDomainsA, totalDocs, checkedDocs, docPct, readyIndicators };
  }

  function paintHeaderStatus(ev) {
    const scoreEl = document.getElementById('hdrScore');
    const gradeEl = document.getElementById('hdrGradeBadge');
    const checkEl = document.getElementById('hdrCheckProgress');
    if (scoreEl) scoreEl.textContent = ev.normalizedTotal.toFixed(1);
    if (gradeEl) {
      gradeEl.textContent = `${ev.grade}등급`;
      gradeEl.className = `grade-badge grade-${ev.grade}`;
    }
    if (checkEl) checkEl.textContent = `${ev.docPct}% (${ev.checkedDocs}/${ev.totalDocs})`;
  }

  function readSavedOrgSuffix() {
    try {
      const saved = JSON.parse(localStorage.getItem(ORG_STORAGE_KEY) || '{}');
      const qs = new URLSearchParams();
      if (saved.org && String(saved.org).trim()) qs.set('org', String(saved.org).trim());
      if (saved.code && String(saved.code).trim()) qs.set('code', String(saved.code).trim());
      return qs.toString() ? `?${qs.toString()}` : '';
    } catch (_) {
      return '';
    }
  }

  function applySavedOrgToStaticLinks(scope) {
    const suffix = readSavedOrgSuffix();
    if (!suffix) return;
    (scope || document).querySelectorAll('a[href^="/forms/"]').forEach(a => {
      if (a.classList.contains('dc-form-dl') || a.id === 'dcBundleZipBtn') return;
      const raw = a.getAttribute('href') || '';
      const base = raw.split('?')[0];
      if (base === '/forms/bundle.zip' || /\.(hwpx|docx|xlsx)$/.test(base) || /\/print$/.test(base)) {
        a.setAttribute('href', base + suffix);
      }
    });
  }

  function centerActiveSubtab(navEl) {
    const subtabs = navEl || document.querySelector('.gov-subtabs');
    const activeSubtab = subtabs?.querySelector('.gov-subtab-btn.active');
    if (subtabs && activeSubtab) {
      subtabs.scrollLeft = Math.max(0, activeSubtab.offsetLeft - (subtabs.clientWidth - activeSubtab.offsetWidth) / 2);
    }
  }

  /* =========================================================
     전체메뉴(드로어) · 메인 통합검색
     ========================================================= */
  function initDrawer() {
    const drawer = document.getElementById('drawer');
    const openBtn = document.getElementById('btnMenu');
    if (!drawer || !openBtn) return;
    const closeBtn = document.getElementById('btnMenuClose');

    function setOpen(open, restoreFocus = true) {
      drawer.hidden = !open;
      openBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      document.body.classList.toggle('drawer-open', open);
      if (open) closeBtn?.focus();
      else if (restoreFocus) openBtn.focus();
    }

    function showPanel(key) {
      drawer.querySelectorAll('[data-dmenu]').forEach(b => b.classList.toggle('is-on', b.getAttribute('data-dmenu') === key));
      drawer.querySelectorAll('[data-dpanel]').forEach(p => { p.hidden = p.getAttribute('data-dpanel') !== key; });
    }

    openBtn.addEventListener('click', () => setOpen(true));
    closeBtn?.addEventListener('click', () => setOpen(false));
    drawer.querySelectorAll('[data-dmenu]').forEach(b => b.addEventListener('click', () => showPanel(b.getAttribute('data-dmenu'))));
    drawer.querySelectorAll('a[href]').forEach(a => a.addEventListener('click', () => {
      setOpen(false, false);
    }));
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && !drawer.hidden) setOpen(false); });
    window.matchMedia('(min-width: 901px)').addEventListener?.('change', e => { if (e.matches && !drawer.hidden) setOpen(false, false); });

    // 현재 페이지에 맞는 대분류를 먼저 보여준다.
    const path = location.pathname;
    if (path.startsWith('/operations')) showPanel('ops');
    else if (path.startsWith('/forms')) showPanel('forms');
    else if (path.startsWith('/office')) showPanel('office');
    else if (path.startsWith('/about')) showPanel('about');
  }

  /* 화면 테마: 기본은 밝은 화면, 사용자가 누르면 어두운 화면(브라우저에 저장) */
  function initTheme() {
    const btn = document.getElementById('btnTheme');
    function paint() {
      const dark = document.documentElement.getAttribute('data-theme') === 'dark';
      if (btn) {
        btn.setAttribute('aria-pressed', dark ? 'true' : 'false');
        const label = dark ? '밝은 화면으로 바꾸기' : '어두운 화면으로 바꾸기';
        btn.setAttribute('aria-label', label);
        btn.title = label;
      }
      document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#121418' : '#2151c8');
    }
    paint();
    btn?.addEventListener('click', () => {
      const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      if (next === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
      else document.documentElement.removeAttribute('data-theme');
      try { localStorage.setItem(THEME_STORAGE_KEY, next); } catch (_) {}
      paint();
    });
  }

  function initHomeSearch() {
    const form = document.getElementById('homeSearchForm');
    const kind = document.getElementById('homeSearchKind');
    const qInput = document.getElementById('homeSearchQ');

    document.querySelectorAll('a[href="/#search"]').forEach(link => {
      link.addEventListener('click', e => {
        if (location.pathname === '/') {
          e.preventDefault();
          document.getElementById('search')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
          qInput?.focus();
        }
      });
    });

    if (!form) return;
    const syncAction = () => {
      if (kind && kind.value) form.setAttribute('action', kind.value);
    };
    kind?.addEventListener('change', syncAction);
    form.addEventListener('submit', syncAction);
    if (location.hash === '#search') {
      setTimeout(() => qInput?.focus(), 50);
    }
  }

  function applyQueryParam(inputId, handler) {
    const q = new URLSearchParams(location.search).get('q');
    const el = document.getElementById(inputId);
    if (!q || !el) return;
    el.value = q.slice(0, 60);
    handler();
  }

  /* =========================================================
     0. GLOBAL FONT SIZE & HEADER STATUS BAR (All Pages)
     ========================================================= */
  function initGlobalChrome() {
    function applyFont(size) {
      const root = document.documentElement;
      root.classList.remove('font-sm', 'font-lg');
      if (size === 'sm') root.classList.add('font-sm');
      if (size === 'lg') root.classList.add('font-lg');
      ['btnFontSm', 'btnFontMd', 'btnFontLg'].forEach(id => {
        document.getElementById(id)?.classList.remove('active');
      });
      const activeId = size === 'sm' ? 'btnFontSm' : (size === 'lg' ? 'btnFontLg' : 'btnFontMd');
      document.getElementById(activeId)?.classList.add('active');
      try { localStorage.setItem(FONT_STORAGE_KEY, size); } catch (_) {}
    }

    initDrawer();
    initHomeSearch();
    initTheme();
    applySavedOrgToStaticLinks(document);

    document.getElementById('btnFontSm')?.addEventListener('click', () => applyFont('sm'));
    document.getElementById('btnFontMd')?.addEventListener('click', () => applyFont('md'));
    document.getElementById('btnFontLg')?.addEventListener('click', () => applyFont('lg'));
    try {
      const savedFont = localStorage.getItem(FONT_STORAGE_KEY);
      if (savedFont === 'sm' || savedFont === 'lg') applyFont(savedFont);
    } catch (_) {}

    const globalEl = document.getElementById('global-eval-summary');
    if (globalEl) {
      try {
        const inds = JSON.parse(globalEl.textContent);
        const saved = readSavedEval();
        const ev = computeEvalSummary(inds, saved.scores || {}, saved.docChecks || {});
        paintHeaderStatus(ev);

        const homeChkBar = document.getElementById('homeChecklistBanner');
        if (homeChkBar) {
          homeChkBar.innerHTML = `
            <div class="prog-wrap">
              <div class="prog-meta">
                <span>평가 지표별 준비완료 <strong>${ev.readyIndicators} / ${inds.length}개</strong></span>
                <span style="color:var(--gov-navy);">필수서류 ${ev.checkedDocs} / ${ev.totalDocs}건 (${ev.docPct}%)</span>
              </div>
              <div class="chk-prog-track"><div class="chk-prog-fill" style="width:${ev.docPct}%;"></div></div>
            </div>
            <a class="btn btn-sm btn-primary" href="/evaluation#checklist">자가점검 이어하기 &rsaquo;</a>
          `;
        }

        const homeStrip = document.getElementById('homeDomainStrip');
        if (homeStrip) {
          homeStrip.innerHTML = DOMAINS.map(d => {
            const st = ev.domainStats[d.name];
            const passA = st.pct >= 70;
            return `
              <a href="/evaluation" class="dom-card">
                <div class="dom-top">
                  <span class="dom-name"><span style="color:var(--gov-slate-500);margin-right:4px;">${d.code}</span>${esc(d.name)}</span>
                  <span class="dom-pct ${passA ? '' : 'fail'}">${st.pct.toFixed(0)}%</span>
                </div>
                <div class="dom-score-row">
                  <strong>${fmtNum(st.obtained)}<small> / ${fmtNum(st.validMax)}점</small></strong>
                  <small>준비 ${st.indReady}/${st.indTotal}개</small>
                </div>
                <div class="dom-bar">
                  <div class="dom-bar-fill ${passA ? '' : 'fail'}" style="width:${Math.min(100, st.pct)}%;background:${passA ? d.color : '#b91c1c'};"></div>
                </div>
              </a>
            `;
          }).join('');
        }
      } catch (_) {}
    }
  }

  /* =========================================================
     1. EVALUATION PORTAL (/evaluation)
     ========================================================= */
  function initEvaluation() {
    const root = document.getElementById('dcEvalApp');
    const dataEl = document.getElementById('dc-eval-data');
    if (!root || !dataEl) return;

    const bundle = JSON.parse(dataEl.textContent);
    const INDICATORS = bundle.indicators || [];
    const CALENDAR_TASKS = bundle.calendar_tasks || [];
    const INTERVIEW_CARDS = bundle.interview_cards || [];
    const formsLiteEl = document.getElementById('dc-forms-lite');
    const FORMS_MAP = {};
    if (formsLiteEl) {
      JSON.parse(formsLiteEl.textContent).forEach(f => { FORMS_MAP[f.slug] = f; });
    }

    const saved = readSavedEval();
    const state = {
      scores: saved.scores || {},
      docChecks: saved.docChecks || {},
      calChecks: saved.calChecks || {},
      intChecks: saved.intChecks || {},
      activeTab: 'explorer',
      search: '',
      domainFilter: 'ALL',
      methodFilter: 'ALL',
      quickChip: 'ALL',
      chkDomain: 'ALL',
      chkOnlyPending: false,
      chkSearch: '',
      simDomain: 'ALL',
      simOnlyLost: false,
      calCycle: 'ALL',
      intType: 'ALL',
      currentModalId: null,
    };

    INDICATORS.forEach(ind => {
      ind.criteria.forEach(c => {
        const k = `${ind.id}_${c.no}`;
        if (state.scores[k] === undefined) state.scores[k] = 0;
      });
    });

    function saveState() {
      try {
        localStorage.setItem(EVAL_STORAGE_KEY, JSON.stringify({
          scores: state.scores,
          docChecks: state.docChecks,
          calChecks: state.calChecks,
          intChecks: state.intChecks,
        }));
      } catch (_) {}
    }

    function updateSummary() {
      const ev = computeEvalSummary(INDICATORS, state.scores, state.docChecks);
      paintHeaderStatus(ev);

      const grid = document.getElementById('domainSummaryGrid');
      grid.innerHTML = DOMAINS.map(d => {
        const st = ev.domainStats[d.name];
        const passA = st.pct >= 70;
        const selected = state.domainFilter === d.name;
        return `
          <button type="button" data-pick-dom="${esc(d.name)}" class="dom-card ${selected ? 'selected' : ''}">
            <div class="dom-top">
              <span class="dom-name"><span style="color:var(--gov-slate-500);margin-right:4px;">${d.code}</span>${esc(d.name)}</span>
              <span class="dom-pct ${passA ? '' : 'fail'}">${st.pct.toFixed(0)}%</span>
            </div>
            <div class="dom-score-row">
              <strong>${fmtNum(st.obtained)}<small> / ${fmtNum(st.validMax)}점</small></strong>
              <small>A기준 70%</small>
            </div>
            <div class="dom-bar">
              <div class="dom-bar-fill ${passA ? '' : 'fail'}" style="width:${Math.min(100, st.pct)}%;background:${passA ? d.color : '#b91c1c'};"></div>
            </div>
          </button>
        `;
      }).join('');

      grid.querySelectorAll('[data-pick-dom]').forEach(btn => {
        btn.addEventListener('click', () => {
          const dom = btn.getAttribute('data-pick-dom');
          state.domainFilter = state.domainFilter === dom ? 'ALL' : dom;
          document.getElementById('domainFilter').value = state.domainFilter;
          updateSummary();
          renderExplorer();
        });
      });
    }

    function renderExplorer() {
      const q = state.search.trim().toLowerCase();
      const filtered = INDICATORS.filter(ind => {
        if (state.domainFilter !== 'ALL' && ind.domain !== state.domainFilter) return false;
        if (state.methodFilter !== 'ALL' && !ind.methods.includes(state.methodFilter)) return false;
        if (state.quickChip === 'NEW' && !ind.isNew) return false;
        if (state.quickChip === 'LINK' && !ind.hasLink) return false;
        if (state.quickChip === 'HIGH' && ind.maxScore < 4) return false;
        if (state.quickChip === 'INTERVIEW' && !ind.methods.includes('면담') && !ind.methods.includes('시연')) return false;
        if (q) {
          const hay = [
            ind.id, ind.name, ind.domain, ind.summary, ind.new2026, ind.direction,
            ...ind.criteria.map(c => c.text),
            ...ind.verification,
            ...ind.docs,
            ...ind.pitfalls.map(p => `${p.bad} ${p.good}`),
          ].join(' ').toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      });

      document.getElementById('resultCount').textContent = `검색결과 총 ${filtered.length}건`;
      const container = document.getElementById('indicatorGrid');
      if (!filtered.length) {
        container.innerHTML = `<div class="gov-card plain" style="grid-column:1/-1;text-align:center;color:var(--gov-slate-600);padding:36px;">조건에 해당하는 평가지표가 없습니다. 검색어 또는 분류 조건을 초기화해 주십시오.</div>`;
        return;
      }

      container.innerHTML = filtered.map(ind => {
        let indObtained = 0, indValid = 0, hasNA = false;
        ind.criteria.forEach(c => {
          const r = evalCriterionResult(ind, c, state.scores);
          if (r.isNA) hasNA = true;
          else {
            indObtained = Math.round((indObtained + r.score) * 100) / 100;
            indValid = Math.round((indValid + c.maxScore) * 100) / 100;
          }
        });
        const isFull = hasNA || Math.abs(indObtained - indValid) < 1e-6;
        const checkedCnt = ind.docs.filter((_, idx) => state.docChecks[`${ind.id}_${idx}`]).length;
        const numStr = String(ind.id).padStart(2, '0');
        return `
          <article data-open-ind="${ind.id}" tabindex="0" class="ind-card ${isFull ? '' : 'is-lost'}">
            <div class="ind-card-body">
              <div class="ind-card-top">
                <div class="ind-card-idwrap">
                  <span class="ind-no">${numStr}</span>
                  <div>
                    <div class="ind-meta">${esc(ind.domain)} · 매뉴얼 p.${ind.manualPage}</div>
                    <h3 class="ind-name">${esc(ind.name)}</h3>
                  </div>
                </div>
                <span class="ind-pts ${ind.maxScore >= 4 ? 'high' : ''}">${ind.maxScore}점</span>
              </div>
              <div class="tag-row" style="margin-top:9px;">
                ${ind.isNew ? '<span class="tag tag-danger">신설</span>' : ''}
                ${ind.hasLink ? '<span class="tag tag-warn">연동</span>' : ''}
                ${ind.methods.map(m => `<span class="tag tag-slate">${esc(m)}</span>`).join('')}
              </div>
              <p class="ind-summary">${esc(ind.summary)}</p>
              <div class="ind-change"><strong>2026 변경·핵심:</strong> ${esc(ind.new2026)}</div>
            </div>
            <div class="ind-card-foot">
              <span style="font-weight:700;color:${isFull ? 'var(--gov-ok)' : 'var(--gov-danger)'};">
                ${hasNA ? '해당없음' : `모의 ${fmtNum(indObtained)}/${fmtNum(indValid)}점`}
              </span>
              <span style="color:var(--gov-slate-600);">서류점검 ${checkedCnt}/${ind.docs.length}</span>
              <span style="color:var(--gov-navy);font-weight:700;">상세보기 &rsaquo;</span>
            </div>
          </article>
        `;
      }).join('');

      container.querySelectorAll('[data-open-ind]').forEach(el => {
        const handler = () => openModal(Number(el.getAttribute('data-open-ind')));
        el.addEventListener('click', handler);
        el.addEventListener('keydown', e => {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handler(); }
        });
      });
    }

    function openModal(indId, preserveScroll = false) {
      const ind = INDICATORS.find(x => x.id === indId);
      if (!ind) return;
      state.currentModalId = indId;

      document.getElementById('mBadges').innerHTML = `
        <span class="tag" style="background:rgba(255,255,255,0.16);color:#fff;">${esc(ind.domain)}</span>
        <span class="tag" style="background:var(--gov-paper);color:var(--gov-navy);">배점 ${ind.maxScore}점</span>
        ${ind.isNew ? '<span class="tag" style="background:#dc2626;color:#fff;">2026 신설지표</span>' : ''}
        ${ind.hasLink ? '<span class="tag" style="background:#d97706;color:#fff;">연동 주의</span>' : ''}
        <span class="tag" style="background:rgba(255,255,255,0.16);color:#fff;">매뉴얼 p.${ind.manualPage}</span>
      `;
      document.getElementById('mTitle').textContent = `지표 ${String(ind.id).padStart(2, '0')}. ${ind.name}`;
      document.getElementById('mPageInfo').textContent = `지표 ${ind.id} / ${INDICATORS.length}`;
      document.getElementById('mPrevBtn').disabled = ind.id === 1;
      document.getElementById('mNextBtn').disabled = ind.id === INDICATORS.length;

      const orgSfx = readSavedOrgSuffix();
      const linkedForms = (ind.form_slugs || []).map(s => FORMS_MAP[s]).filter(Boolean);
      const linkedFormsHtml = linkedForms.length ? `
        <div class="modal-sec no-print">
          <h3 class="modal-sec-title">연계 2026 최신 표준서식 바로 내려받기</h3>
          <div class="stack-sm">
            ${linkedForms.map(f => `
              <div style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:10px;padding:12px 14px;border:1px solid var(--gov-tint-line);border-radius:6px;background:var(--gov-tint);">
                <span style="font-size:0.84rem;font-weight:700;color:var(--gov-navy-dark);">[${esc(f.code_badge)}] ${esc(f.no)}. ${esc(f.title)}</span>
                <span style="display:flex;gap:6px;flex-wrap:wrap;">
                  <a class="btn btn-xs btn-primary" href="/forms/${encodeURIComponent(f.slug)}.hwpx${orgSfx}">한글(HWPX)</a>
                  ${f.has_gov_hwp ? `<a class="btn btn-xs btn-warn" href="/forms/${encodeURIComponent(f.slug)}/gov.hwp">법정원본 HWP</a>` : ''}
                  <a class="btn btn-xs btn-soft" href="/forms/${encodeURIComponent(f.slug)}.docx${orgSfx}">DOCX</a>
                  <a class="btn btn-xs btn-soft" href="/forms/${encodeURIComponent(f.slug)}.xlsx${orgSfx}">XLSX</a>
                  <a class="btn btn-xs" href="/forms/${encodeURIComponent(f.slug)}/print${orgSfx}" target="_blank" rel="noopener noreferrer">인쇄</a>
                </span>
              </div>
            `).join('')}
          </div>
        </div>
      ` : '';

      const body = document.getElementById('mBody');
      const prevScroll = body.scrollTop;
      body.innerHTML = `
        <div class="modal-sec">
          <div class="gov-table-wrap">
            <table class="gov-table">
              <tbody>
                <tr><th style="width:112px;">지표적용기간</th><td>${esc(ind.period)}</td></tr>
                <tr><th>평가방법</th><td>${esc(ind.methods.join(', '))}</td></tr>
                <tr><th>2026 주요 변경</th><td style="font-weight:700;color:var(--gov-navy);">${esc(ind.new2026)}</td></tr>
                <tr><th>평가방향 (원문)</th><td>${esc(ind.direction)}</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="modal-sec" style="background:var(--gov-tint-soft);border:1px solid var(--gov-tint-line);border-radius:6px;padding:14px 16px;font-size:0.88rem;line-height:1.68;">
          <div style="font-size:0.78rem;font-weight:800;color:var(--gov-navy);margin-bottom:4px;">실무 핵심 요약</div>
          ${esc(ind.summary)}
        </div>

        <div class="modal-sec">
          <h3 class="modal-sec-title">1. 세부 평가기준 및 모의 채점</h3>
          ${ind.criteria.map(c => {
            const res = evalCriterionResult(ind, c, state.scores);
            return `
              <div class="crit-box ${res.lockedByLink ? 'locked' : ''}" style="flex-direction:column;align-items:stretch;">
                <div style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:6px;">
                  <div class="tag-row">
                    <span class="tag tag-solid">기준 ${c.no}</span>
                    <span class="tag tag-slate">대상: ${esc(c.target)}</span>
                    <span class="tag tag-navy">${esc(c.method)}</span>
                    ${c.isNew ? '<span class="tag tag-danger">신설</span>' : ''}
                    ${c.linkedTo ? `<span class="tag tag-warn">기준${c.linkedTo} 연동</span>` : ''}
                  </div>
                  <strong style="font-size:0.82rem;color:var(--gov-navy);">배점 ${c.maxScore}점</strong>
                </div>
                <div style="font-size:0.88rem;font-weight:700;color:var(--gov-ink);margin:4px 0;">${esc(c.text)}</div>
                ${res.lockedByLink
                  ? `<div style="font-size:0.8rem;font-weight:700;color:var(--gov-warn-text);background:var(--gov-warn-soft);border:1px solid var(--gov-warn-line);padding:9px 12px;border-radius:6px;">[연동 안내] 선행 기준(기준 ${c.linkedTo})이 미충족되어 자동 0점 처리되었습니다.</div>`
                  : `<div class="opt-group no-print">
                      ${c.options.map((opt, oIdx) => {
                        const cls = res.optIdx === oIdx ? (opt.score === c.maxScore || opt.isNA ? 'is-full' : 'is-lost') : '';
                        return `<button type="button" data-ms-i="${ind.id}" data-ms-c="${c.no}" data-ms-o="${oIdx}" class="opt-btn ${cls}">${esc(opt.label)}</button>`;
                      }).join('')}
                    </div>`
                }
              </div>
            `;
          }).join('')}
        </div>

        <div class="modal-sec">
          <h3 class="modal-sec-title">2. 현장 확인방법 및 매뉴얼 유의사항</h3>
          <div style="background:var(--gov-surface);border:1px solid var(--gov-line);border-radius:6px;padding:14px 18px;">
            <ul style="margin:0;padding-left:18px;font-size:0.84rem;line-height:1.72;color:var(--gov-ink);">
              ${ind.verification.map(v => `<li>${esc(v)}</li>`).join('')}
            </ul>
          </div>
        </div>

        <div class="modal-sec">
          <h3 class="modal-sec-title">3. 필수 준비 서류 및 현장 점검표</h3>
          <div style="border:1px solid var(--gov-line);border-radius:6px;background:var(--gov-paper);overflow:hidden;">
            ${ind.docs.map((doc, idx) => {
              const checked = !!state.docChecks[`${ind.id}_${idx}`];
              return `
                <label class="doc-chk-row ${checked ? 'checked' : ''}">
                  <input type="checkbox" data-doc-key="${ind.id}_${idx}" ${checked ? 'checked' : ''}>
                  <span>${esc(doc)}</span>
                </label>
              `;
            }).join('')}
          </div>
        </div>

        ${linkedFormsHtml}

        <div class="modal-sec">
          <h3 class="modal-sec-title danger">4. 주요 감점(불인정) 사례 및 예방 기준</h3>
          <div class="gov-table-wrap">
            <table class="gov-table">
              <thead><tr><th style="width:33%;">주요 감점 사례 (불인정)</th><th style="width:33%;">올바른 실무 준비</th><th style="width:34%;">판정 사유</th></tr></thead>
              <tbody>
                ${ind.pitfalls.map(p => `
                  <tr>
                    <td style="color:var(--gov-danger-text);">${esc(p.bad)}</td>
                    <td style="color:var(--gov-ok-text);font-weight:600;">${esc(p.good)}</td>
                    <td>${esc(p.why)}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>

        <div style="font-size:11.5px;color:var(--gov-slate-600);padding-top:10px;border-top:1px solid var(--gov-line);display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:8px;">
          <span><strong>관련 법령 및 근거:</strong> ${esc(ind.law)}</span>
          <a class="btn btn-xs no-print" href="https://www.longtermcare.or.kr/npbs/d/m/000/moveBoardView?menuId=npe0000002804&amp;bKey=B0153&amp;search_boardId=25" target="_blank" rel="noopener noreferrer">공단 2026 평가매뉴얼 원문 게시글 (p.${ind.manualPage}) &rsaquo;</a>
        </div>
      `;

      body.scrollTop = preserveScroll ? prevScroll : 0;

      body.querySelectorAll('[data-ms-i]').forEach(btn => {
        btn.addEventListener('click', () => {
          state.scores[`${btn.getAttribute('data-ms-i')}_${btn.getAttribute('data-ms-c')}`] = Number(btn.getAttribute('data-ms-o'));
          saveState();
          updateSummary();
          renderExplorer();
          if (state.activeTab === 'simulator') renderSimulator();
          openModal(indId, true);
        });
      });

      body.querySelectorAll('[data-doc-key]').forEach(chk => {
        chk.addEventListener('change', () => {
          state.docChecks[chk.getAttribute('data-doc-key')] = chk.checked;
          saveState();
          updateSummary();
          renderExplorer();
          if (state.activeTab === 'checklist') renderChecklist();
          openModal(indId, true);
        });
      });

      document.getElementById('detailModal').hidden = false;
      try { history.replaceState(null, '', '#indicator-' + ind.id); } catch (_) {}
    }

    function closeModal() {
      document.getElementById('detailModal').hidden = true;
      state.currentModalId = null;
      try { history.replaceState(null, '', '#' + state.activeTab); } catch (_) {}
    }

    function renderChecklist() {
      const ev = computeEvalSummary(INDICATORS, state.scores, state.docChecks);
      const indCntEl = document.getElementById('chkReadyIndCount');
      if (!indCntEl) return;
      indCntEl.textContent = String(ev.readyIndicators);
      document.getElementById('chkReadyDocCount').textContent = String(ev.checkedDocs);
      document.getElementById('chkTotalDocCount').textContent = String(ev.totalDocs);
      document.getElementById('chkReadyPct').textContent = String(ev.docPct);
      document.getElementById('chkProgressBar').style.width = `${ev.docPct}%`;

      document.getElementById('chkDomainSummary').innerHTML = DOMAINS.map(d => {
        const st = ev.domainStats[d.name];
        const doneAll = st.indReady === st.indTotal;
        return `
          <div style="padding:10px 12px;border:1px solid var(--gov-line);border-radius:6px;background:var(--gov-surface);">
            <div style="display:flex;justify-content:space-between;font-size:0.78rem;font-weight:700;color:var(--gov-slate-700);">
              <span>${d.code} ${esc(d.name)}</span>
              <span style="color:${doneAll ? 'var(--gov-ok)' : 'var(--gov-navy)'};">${st.indReady}/${st.indTotal}개 완료</span>
            </div>
          </div>
        `;
      }).join('');

      const q = state.chkSearch.trim().toLowerCase();
      const orgSfx = readSavedOrgSuffix();
      const items = INDICATORS.filter(ind => {
        if (state.chkDomain !== 'ALL' && ind.domain !== state.chkDomain) return false;
        const doneCnt = ind.docs.filter((_, idx) => state.docChecks[`${ind.id}_${idx}`]).length;
        const isDone = ind.docs.length > 0 && doneCnt === ind.docs.length;
        if (state.chkOnlyPending && isDone) return false;
        if (q) {
          const hay = [String(ind.id), ind.name, ind.domain, ind.summary, ...ind.docs].join(' ').toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      });

      document.getElementById('chkResultCount').textContent = `표시 중 ${items.length}개 지표`;
      const board = document.getElementById('checklistBoard');
      if (!items.length) {
        board.innerHTML = `<div class="gov-card plain" style="text-align:center;color:var(--gov-slate-600);padding:32px;">${state.chkOnlyPending ? '모든 평가지표 서류 점검이 완료되었습니다!' : '검색 조건에 맞는 지표가 없습니다.'}</div>`;
        return;
      }

      board.innerHTML = items.map(ind => {
        const doneCnt = ind.docs.filter((_, idx) => state.docChecks[`${ind.id}_${idx}`]).length;
        const totalCnt = ind.docs.length;
        const isDone = totalCnt > 0 && doneCnt === totalCnt;
        const statusTag = isDone
          ? `<span class="tag tag-ok">준비완료 (${doneCnt}/${totalCnt})</span>`
          : (doneCnt > 0
            ? `<span class="tag tag-warn">진행중 (${doneCnt}/${totalCnt})</span>`
            : `<span class="tag tag-slate">미점검 (0/${totalCnt})</span>`);
        const firstForm = (ind.form_slugs || []).map(s => FORMS_MAP[s]).find(Boolean);
        return `
          <article class="chk-card ${isDone ? 'is-done' : ''}">
            <div class="chk-card-head">
              <label class="chk-master-lbl">
                <input type="checkbox" data-chk-master="${ind.id}" ${isDone ? 'checked' : ''}>
                <span>[${String(ind.id).padStart(2, '0')}] ${esc(ind.name)}</span>
              </label>
              <div style="display:flex;flex-wrap:wrap;align-items:center;gap:6px;">
                <span class="tag tag-slate">${esc(ind.domain)}</span>
                <span class="tag tag-navy">${ind.maxScore}점</span>
                ${ind.isNew ? '<span class="tag tag-danger">신설</span>' : ''}
                ${ind.hasLink ? '<span class="tag tag-warn">연동</span>' : ''}
                ${statusTag}
                ${firstForm ? `<a class="btn btn-xs btn-soft no-print" href="/forms/${encodeURIComponent(firstForm.slug)}.hwpx${orgSfx}">서식(한글)</a>` : ''}
                <button type="button" data-chk-open="${ind.id}" class="btn btn-xs no-print">기준 상세</button>
              </div>
            </div>
            <div class="chk-docs-list">
              ${ind.docs.map((doc, idx) => {
                const checked = !!state.docChecks[`${ind.id}_${idx}`];
                return `
                  <label class="doc-chk-row ${checked ? 'checked' : ''}">
                    <input type="checkbox" data-chk-doc="${ind.id}_${idx}" ${checked ? 'checked' : ''}>
                    <span>${esc(doc)}</span>
                  </label>
                `;
              }).join('')}
            </div>
          </article>
        `;
      }).join('');

      board.querySelectorAll('[data-chk-master]').forEach(master => {
        master.addEventListener('change', () => {
          const id = Number(master.getAttribute('data-chk-master'));
          const ind = INDICATORS.find(x => x.id === id);
          if (!ind) return;
          ind.docs.forEach((_, idx) => {
            state.docChecks[`${ind.id}_${idx}`] = master.checked;
          });
          saveState();
          updateSummary();
          renderExplorer();
          renderChecklist();
        });
      });

      board.querySelectorAll('[data-chk-doc]').forEach(chk => {
        chk.addEventListener('change', () => {
          state.docChecks[chk.getAttribute('data-chk-doc')] = chk.checked;
          saveState();
          updateSummary();
          renderExplorer();
          renderChecklist();
        });
      });

      board.querySelectorAll('[data-chk-open]').forEach(btn => {
        btn.addEventListener('click', () => openModal(Number(btn.getAttribute('data-chk-open'))));
      });
    }

    function renderSimulator() {
      const ev = computeEvalSummary(INDICATORS, state.scores, state.docChecks);
      document.getElementById('simTotalScore').textContent = ev.normalizedTotal.toFixed(1);
      document.getElementById('simValidMax').textContent = fmtNum(ev.totalValidMax);
      const sb = document.getElementById('simGradeBadge');
      sb.textContent = ev.gradeLabel;
      sb.className = `grade-badge grade-${ev.grade}`;

      const diag = document.getElementById('simDiagnosis');
      if (ev.grade === 'A') {
        diag.innerHTML = `<strong style="color:var(--gov-ok);">[충족]</strong> 최우수(A등급) 기준(총점 90점 이상 및 전 영역 70% 이상)을 모두 충족하고 있습니다.`;
      } else {
        const parts = [];
        if (ev.normalizedTotal < 90) parts.push(`총점 ${(90 - ev.normalizedTotal).toFixed(1)}점 부족`);
        if (ev.weakDomainsA.length) parts.push(`70% 미만 영역: ${ev.weakDomainsA.join(', ')}`);
        diag.innerHTML = `<strong style="color:var(--gov-danger);">[보완 필요]</strong> A등급 기준 미달 항목 — ${esc(parts.join(' / '))}`;
      }

      document.getElementById('domainChartBars').innerHTML = DOMAINS.map(d => {
        const st = ev.domainStats[d.name];
        const pass = st.pct >= 70;
        return `
          <div class="chart-row">
            <div class="chart-lbl">${esc(d.name)}<small>${fmtNum(st.obtained)} / ${fmtNum(st.validMax)}점</small></div>
            <div class="chart-track">
              <div class="chart-threshold" title="A등급 과락 기준(70%)"></div>
              <div class="chart-fill ${pass ? '' : 'fail'}" style="width:${Math.min(100, st.pct)}%;background:${pass ? d.color : '#b91c1c'};"></div>
            </div>
            <div class="chart-pct" style="color:${pass ? 'var(--gov-navy)' : 'var(--gov-danger)'};">${st.pct.toFixed(1)}%</div>
          </div>
        `;
      }).join('');

      const list = document.getElementById('simulatorList');
      const items = INDICATORS.filter(ind => {
        if (state.simDomain !== 'ALL' && ind.domain !== state.simDomain) return false;
        if (state.simOnlyLost) {
          const lost = ind.criteria.some(c => {
            const r = evalCriterionResult(ind, c, state.scores);
            return !r.isNA && r.score < c.maxScore;
          });
          if (!lost) return false;
        }
        return true;
      });

      if (!items.length) {
        list.innerHTML = `<div class="gov-card plain" style="text-align:center;color:var(--gov-slate-600);padding:32px;">감점된 항목이 없습니다. 모든 항목이 만점(또는 해당없음) 상태입니다.</div>`;
        return;
      }

      list.innerHTML = items.map(ind => `
        <div class="gov-card plain">
          <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;padding-bottom:8px;margin-bottom:8px;border-bottom:1px solid var(--gov-line);">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
              <span class="ind-no" style="width:24px;height:24px;font-size:11px;">${String(ind.id).padStart(2, '0')}</span>
              <span style="font-size:11.5px;color:var(--gov-slate-500);">${esc(ind.domain)}</span>
              <strong style="font-size:0.88rem;">${esc(ind.name)}</strong>
              <span class="tag tag-navy">${ind.maxScore}점</span>
            </div>
            <button type="button" data-sim-open="${ind.id}" class="btn btn-xs btn-soft">상세 해설</button>
          </div>
          ${ind.criteria.map(c => {
            const res = evalCriterionResult(ind, c, state.scores);
            return `
              <div class="crit-box ${res.lockedByLink ? 'locked' : ''}">
                <div style="font-size:0.78rem;flex:1;min-width:220px;">
                  <strong style="color:var(--gov-navy);">${'①②③④⑤⑥'[c.no - 1]} [${esc(c.target)}/${c.maxScore}점]</strong> ${esc(c.text)}
                </div>
                ${res.lockedByLink
                  ? `<span class="tag tag-warn">[연동] 기준${c.linkedTo} 미충족 0점</span>`
                  : `<div class="opt-group">
                      ${c.options.map((opt, oIdx) => {
                        const cls = res.optIdx === oIdx ? (opt.score === c.maxScore || opt.isNA ? 'is-full' : 'is-lost') : '';
                        return `<button type="button" data-sc-i="${ind.id}" data-sc-c="${c.no}" data-sc-o="${oIdx}" class="opt-btn ${cls}">${esc(opt.label)}</button>`;
                      }).join('')}
                    </div>`
                }
              </div>
            `;
          }).join('')}
        </div>
      `).join('');

      list.querySelectorAll('[data-sc-i]').forEach(btn => {
        btn.addEventListener('click', () => {
          state.scores[`${btn.getAttribute('data-sc-i')}_${btn.getAttribute('data-sc-c')}`] = Number(btn.getAttribute('data-sc-o'));
          saveState();
          updateSummary();
          renderSimulator();
          renderExplorer();
        });
      });
      list.querySelectorAll('[data-sim-open]').forEach(btn => {
        btn.addEventListener('click', () => openModal(Number(btn.getAttribute('data-sim-open'))));
      });
    }

    function renderCalendar() {
      const filtered = CALENDAR_TASKS.filter(t => state.calCycle === 'ALL' || t.cycle === state.calCycle);
      const doneAll = CALENDAR_TASKS.filter(t => state.calChecks[t.id]).length;
      document.getElementById('calProgressText').textContent = `점검 완료: ${doneAll} / ${CALENDAR_TASKS.length}`;

      const list = document.getElementById('calendarList');
      list.innerHTML = filtered.map(t => {
        const checked = !!state.calChecks[t.id];
        return `
          <div class="cal-card ${checked ? 'done' : ''}">
            <input type="checkbox" data-cal-id="${esc(t.id)}" ${checked ? 'checked' : ''} aria-label="${esc(t.title)} 완료">
            <div style="flex:1;min-width:0;">
              <div class="tag-row" style="margin-bottom:5px;">
                <span class="tag tag-navy">${esc(t.cycle)}</span>
                <button type="button" data-cal-ind="${t.indId}" class="btn btn-xs">지표 ${String(t.indId).padStart(2, '0')} 상세 &rsaquo;</button>
              </div>
              <h4 style="font-size:0.86rem;margin-bottom:4px;">${esc(t.title)}</h4>
              <p style="font-size:0.76rem;color:var(--gov-slate-600);line-height:1.55;">${esc(t.detail)}</p>
            </div>
          </div>
        `;
      }).join('');

      list.querySelectorAll('[data-cal-id]').forEach(chk => {
        chk.addEventListener('change', () => {
          state.calChecks[chk.getAttribute('data-cal-id')] = chk.checked;
          saveState();
          renderCalendar();
        });
      });
      list.querySelectorAll('[data-cal-ind]').forEach(btn => {
        btn.addEventListener('click', () => openModal(Number(btn.getAttribute('data-cal-ind'))));
      });
    }

    function renderInterview() {
      const filtered = INTERVIEW_CARDS.filter(c => state.intType === 'ALL' || c.type === state.intType);
      const list = document.getElementById('interviewList');
      list.innerHTML = filtered.map(c => {
        const checked = !!state.intChecks[c.id];
        const cls = c.type === '현장 시연' ? 'tag-danger' : (c.type === '수급자 면담' ? 'tag-ok' : 'tag-navy');
        return `
          <article class="int-card">
            <div class="int-head">
              <div style="display:flex;gap:10px;align-items:flex-start;flex:1;">
                <input type="checkbox" data-int-id="${esc(c.id)}" ${checked ? 'checked' : ''} style="width:16px;height:16px;margin-top:3px;accent-color:var(--gov-navy);" title="숙지 완료">
                <div>
                  <div class="tag-row" style="margin-bottom:5px;">
                    <span class="tag ${cls}">${esc(c.type)}</span>
                    <button type="button" data-int-ind="${c.indId}" class="btn btn-xs">지표 ${String(c.indId).padStart(2, '0')} 상세 &rsaquo;</button>
                  </div>
                  <h4 style="font-size:0.88rem;color:var(--gov-ink);">${esc(c.title)}</h4>
                  <p style="font-size:0.78rem;color:var(--gov-slate-700);margin-top:3px;"><strong>질문:</strong> ${esc(c.q)}</p>
                </div>
              </div>
              <button type="button" data-toggle-ans="${esc(c.id)}" class="btn btn-sm btn-soft">기준답안 열기</button>
            </div>
            <div id="ans_${esc(c.id)}" class="int-ans" hidden>${esc(c.a)}</div>
          </article>
        `;
      }).join('');

      list.querySelectorAll('[data-toggle-ans]').forEach(btn => {
        btn.addEventListener('click', () => {
          const box = document.getElementById('ans_' + btn.getAttribute('data-toggle-ans'));
          box.hidden = !box.hidden;
          btn.textContent = box.hidden ? '기준답안 열기' : '기준답안 닫기';
        });
      });
      list.querySelectorAll('[data-int-id]').forEach(chk => {
        chk.addEventListener('change', () => {
          state.intChecks[chk.getAttribute('data-int-id')] = chk.checked;
          saveState();
        });
      });
      list.querySelectorAll('[data-int-ind]').forEach(btn => {
        btn.addEventListener('click', () => openModal(Number(btn.getAttribute('data-int-ind'))));
      });
    }

    function updateSampleCalc() {
      const staff = Math.max(0, parseInt(document.getElementById('calcStaffInput').value || '0', 10));
      const clients = Math.max(0, parseInt(document.getElementById('calcClientInput').value || '0', 10));
      const staffSample = staff >= 30 ? 4 : (staff >= 10 ? 3 : (staff === 1 ? 1 : (staff >= 2 ? 2 : 0)));
      let clientSample = 0;
      let clientText = '';
      if (clients < 3) {
        clientText = '<strong style="color:var(--gov-danger);">평가불가 기관 (수급자 3인 미만)</strong>';
      } else {
        clientSample = clients >= 30 ? 4 : (clients >= 10 ? 3 : 2);
        clientText = `<strong>${clientSample}명</strong> (면담 합격 합계 ${(clientSample * 0.75).toFixed(2)}점 이상)`;
      }
      document.getElementById('sampleCalcOutput').innerHTML = `
        <div>
          <div class="out-line"><span>직원 자료·면담 표본 수</span><strong>${staffSample}명 (면담 합격 합계 ${(staffSample * 0.75).toFixed(2)}점 이상)</strong></div>
          <div class="out-line"><span>수급자 자료·면담 표본 수</span><span>${clientText}</span></div>
        </div>
        <p style="font-size:0.75rem;color:var(--gov-slate-700);line-height:1.6;">
          • <strong>면담·시연 합격 기준:</strong> 표본별 세부점수(1 / 0.75 / 0.5 / 0점)의 <strong>평균이 0.75점 이상</strong>일 경우 충족.<br>
          • <strong>유의사항:</strong> 선정된 직원 중 일부라도 평가를 거부하는 경우 평가 거부 기관으로 처리됩니다.
        </p>
      `;
    }

    function switchTab(tabName) {
      state.activeTab = tabName;
      document.querySelectorAll('.eval-tab-panel').forEach(p => { p.hidden = true; });
      const target = document.getElementById('tab-' + tabName);
      if (target) target.hidden = false;
      const evalNav = document.getElementById('evalNav');
      document.querySelectorAll('#evalNav [data-tab]').forEach(btn => {
        const active = btn.getAttribute('data-tab') === tabName;
        btn.classList.toggle('active', active);
        btn.setAttribute('aria-selected', String(active));
      });
      centerActiveSubtab(evalNav);
      if (state.currentModalId === null) {
        try { history.replaceState(null, '', '#' + tabName); } catch (_) {}
      }
      if (tabName === 'checklist') renderChecklist();
      if (tabName === 'simulator') renderSimulator();
      if (tabName === 'calendar') renderCalendar();
      if (tabName === 'interview') renderInterview();
      if (tabName === 'guide') updateSampleCalc();
    }

    document.querySelectorAll('#evalNav [data-tab]').forEach(btn => {
      btn.addEventListener('click', () => switchTab(btn.getAttribute('data-tab')));
    });

    document.getElementById('chkSearchInput')?.addEventListener('input', e => {
      state.chkSearch = e.target.value || '';
      renderChecklist();
    });
    document.querySelectorAll('#chkDomainTabs [data-cdom]').forEach(btn => {
      btn.addEventListener('click', () => {
        state.chkDomain = btn.getAttribute('data-cdom');
        document.querySelectorAll('#chkDomainTabs [data-cdom]').forEach(b => b.classList.toggle('active', b === btn));
        renderChecklist();
      });
    });
    document.getElementById('btnChkOnlyPending')?.addEventListener('click', e => {
      state.chkOnlyPending = !state.chkOnlyPending;
      e.currentTarget.classList.toggle('active', state.chkOnlyPending);
      e.currentTarget.textContent = state.chkOnlyPending ? '전체 지표 보기' : '미완료 지표만 보기';
      renderChecklist();
    });
    document.getElementById('btnChkFillAll')?.addEventListener('click', () => {
      INDICATORS.forEach(ind => ind.docs.forEach((_, idx) => { state.docChecks[`${ind.id}_${idx}`] = true; }));
      saveState(); updateSummary(); renderExplorer(); renderChecklist();
      showToast('36개 전체 평가지표 서류를 점검 완료로 표시했습니다.');
    });
    document.getElementById('btnChkReset')?.addEventListener('click', () => {
      state.docChecks = {};
      saveState(); updateSummary(); renderExplorer(); renderChecklist();
      showToast('서류 자가점검 체크를 초기화했습니다.');
    });
    document.getElementById('btnChkPrint')?.addEventListener('click', () => {
      document.body.classList.add('print-checklist');
      window.print();
      setTimeout(() => document.body.classList.remove('print-checklist'), 300);
    });

    const searchEl = document.getElementById('searchInput');
    const clearBtn = document.getElementById('clearSearchBtn');
    searchEl.addEventListener('input', () => {
      state.search = searchEl.value;
      clearBtn.hidden = !state.search;
      renderExplorer();
    });
    clearBtn.addEventListener('click', () => {
      searchEl.value = '';
      state.search = '';
      clearBtn.hidden = true;
      renderExplorer();
    });

    document.getElementById('domainFilter').addEventListener('change', e => {
      state.domainFilter = e.target.value;
      updateSummary();
      renderExplorer();
    });
    document.getElementById('methodFilter').addEventListener('change', e => {
      state.methodFilter = e.target.value;
      renderExplorer();
    });

    document.querySelectorAll('#quickChips [data-chip]').forEach(btn => {
      btn.addEventListener('click', () => {
        state.quickChip = btn.getAttribute('data-chip');
        document.querySelectorAll('#quickChips [data-chip]').forEach(b => b.classList.toggle('active', b === btn));
        renderExplorer();
      });
    });

    document.getElementById('mCloseBtn').addEventListener('click', closeModal);
    document.getElementById('detailModal').addEventListener('click', e => {
      if (e.target.id === 'detailModal') closeModal();
    });
    document.getElementById('mPrevBtn').addEventListener('click', () => {
      if (state.currentModalId > 1) openModal(state.currentModalId - 1);
    });
    document.getElementById('mNextBtn').addEventListener('click', () => {
      if (state.currentModalId < INDICATORS.length) openModal(state.currentModalId + 1);
    });
    document.getElementById('mPrintBtn').addEventListener('click', () => window.print());
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && state.currentModalId !== null) closeModal();
    });

    document.querySelectorAll('#simDomainTabs [data-sdom]').forEach(btn => {
      btn.addEventListener('click', () => {
        state.simDomain = btn.getAttribute('data-sdom');
        document.querySelectorAll('#simDomainTabs [data-sdom]').forEach(b => b.classList.toggle('active', b === btn));
        renderSimulator();
      });
    });

    document.getElementById('btnFillAll').addEventListener('click', () => {
      INDICATORS.forEach(ind => ind.criteria.forEach(c => { state.scores[`${ind.id}_${c.no}`] = 0; }));
      saveState(); updateSummary(); renderSimulator(); renderExplorer();
      showToast('전체 36개 지표를 만점으로 설정했습니다.');
    });
    document.getElementById('btnResetSim').addEventListener('click', () => {
      INDICATORS.forEach(ind => ind.criteria.forEach(c => {
        const zeroIdx = c.options.findIndex(o => o.score === 0 && !o.isNA);
        state.scores[`${ind.id}_${c.no}`] = zeroIdx >= 0 ? zeroIdx : 0;
      }));
      saveState(); updateSummary(); renderSimulator(); renderExplorer();
      showToast('모의 채점을 0점으로 초기화했습니다.');
    });
    document.getElementById('btnOnlyLost').addEventListener('click', e => {
      state.simOnlyLost = !state.simOnlyLost;
      e.currentTarget.classList.toggle('active', state.simOnlyLost);
      renderSimulator();
    });
    document.getElementById('btnExportJson').addEventListener('click', () => {
      const ev = computeEvalSummary(INDICATORS, state.scores, state.docChecks);
      const payload = {
        exportedAt: new Date().toISOString(),
        totalScore: Number(ev.normalizedTotal.toFixed(2)),
        grade: ev.grade,
        scores: state.scores,
        docChecks: state.docChecks,
        calChecks: state.calChecks,
        intChecks: state.intChecks,
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = '2026_주야간보호_자가진단결과.json';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      showToast('자가진단 결과 파일(JSON)을 저장했습니다.');
    });
    document.getElementById('inputImportJson')?.addEventListener('change', e => {
      const file = e.target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const data = JSON.parse(String(reader.result || '{}'));
          if (data.scores && typeof data.scores === 'object') state.scores = data.scores;
          if (data.docChecks && typeof data.docChecks === 'object') state.docChecks = data.docChecks;
          if (data.calChecks && typeof data.calChecks === 'object') state.calChecks = data.calChecks;
          if (data.intChecks && typeof data.intChecks === 'object') state.intChecks = data.intChecks;
          saveState();
          updateSummary();
          renderExplorer();
          renderChecklist();
          renderSimulator();
          showToast('저장된 자가진단 결과(JSON)를 불러왔습니다.');
        } catch (_) {
          showToast('올바른 자가진단 JSON 파일이 아닙니다.');
        }
      };
      reader.readAsText(file, 'utf-8');
      e.target.value = '';
    });

    document.querySelectorAll('#cycleTabs [data-cycle]').forEach(btn => {
      btn.addEventListener('click', () => {
        state.calCycle = btn.getAttribute('data-cycle');
        document.querySelectorAll('#cycleTabs [data-cycle]').forEach(b => b.classList.toggle('active', b === btn));
        renderCalendar();
      });
    });

    document.querySelectorAll('#interviewTypeTabs [data-itype]').forEach(btn => {
      btn.addEventListener('click', () => {
        state.intType = btn.getAttribute('data-itype');
        document.querySelectorAll('#interviewTypeTabs [data-itype]').forEach(b => b.classList.toggle('active', b === btn));
        renderInterview();
      });
    });

    document.getElementById('calcStaffInput').addEventListener('input', updateSampleCalc);
    document.getElementById('calcClientInput').addEventListener('input', updateSampleCalc);

    updateSummary();
    applyQueryParam('searchInput', () => {
      state.search = searchEl.value;
      clearBtn.hidden = !state.search;
    });
    renderExplorer();

    function applyEvalHash() {
      const h = (location.hash || '').replace('#', '');
      if (h.startsWith('indicator-')) {
        const id = parseInt(h.replace('indicator-', ''), 10);
        if (id >= 1 && id <= INDICATORS.length) openModal(id);
      } else if (['explorer', 'checklist', 'simulator', 'calendar', 'interview', 'guide'].includes(h)) {
        if (state.currentModalId !== null) {
          document.getElementById('detailModal').hidden = true;
          state.currentModalId = null;
        }
        switchTab(h);
      }
    }
    applyEvalHash();
    window.addEventListener('hashchange', applyEvalHash);
  }

  /* =========================================================
     2. OPERATIONS MANUAL & CALCULATORS (/operations)
     ========================================================= */
  function initOperations() {
    const root = document.getElementById('dcOpsApp');
    const feeDataEl = document.getElementById('dc-ops-fees-json');
    if (!root || !feeDataEl) return;

    const DATA = JSON.parse(feeDataEl.textContent);
    const GRADE_KEY_TO_IDX = { g1: 0, g2: 1, g3: 2, g4: 3, g5: 4, gc: 5 };

    function switchOpsTab(tab) {
      document.querySelectorAll('.ops-tab-panel').forEach(p => { p.hidden = true; });
      const el = document.getElementById('opstab-' + tab);
      if (el) el.hidden = false;
      const opsNav = document.getElementById('opsNav');
      document.querySelectorAll('#opsNav [data-opstab]').forEach(btn => {
        const active = btn.getAttribute('data-opstab') === tab;
        btn.classList.toggle('active', active);
        btn.setAttribute('aria-selected', String(active));
      });
      centerActiveSubtab(opsNav);
      try { history.replaceState(null, '', '#' + tab); } catch (_) {}
    }

    document.querySelectorAll('#opsNav [data-opstab]').forEach(btn => {
      btn.addEventListener('click', () => switchOpsTab(btn.getAttribute('data-opstab')));
    });

    function calcFee() {
      const room = document.getElementById('opsRoomType').value;
      const gradeKey = document.getElementById('opsGrade').value;
      const bandIdx = Number(document.getElementById('opsBand').value);
      const copayRate = Number(document.getElementById('opsCopay').value);
      const days = Math.max(0, parseInt(document.getElementById('opsDays').value || '0', 10));
      const holidays = Math.max(0, parseInt(document.getElementById('opsHolidays').value || '0', 10));
      const mealDaily = Math.max(0, parseInt(document.getElementById('opsMealDaily').value || '0', 10));

      const out = document.getElementById('opsFeeOutput');
      if (room === 'dementia' && gradeKey === 'g1') {
        out.innerHTML = `<div style="color:var(--gov-danger);font-weight:700;font-size:0.82rem;">치매전담실(사-1~사-5)은 2~5등급 및 인지지원등급 수급자 대상이며 고시 표에 1등급 단가가 없습니다. 2~5등급 또는 일반 주·야간보호를 선택해 주세요.</div>`;
        return;
      }

      const table = room === 'dementia' ? DATA.dementia : DATA.general;
      const dailyUnit = table[bandIdx][gradeKey];
      const holidayUnit = Math.round(dailyUnit * 1.3);
      const totalDays = days + holidays;
      const grossBenefit = dailyUnit * days + holidayUnit * holidays;

      const limRow = DATA.limits[GRADE_KEY_TO_IDX[gradeKey]];
      const baseLimit = limRow.limit;
      const qualifiesExtra = totalDays >= 15 && bandIdx >= 2;
      const extraPct = qualifiesExtra ? (room === 'dementia' ? limRow.dementia_extra_pct : limRow.extra_pct) : 0;
      const effectiveLimit = Math.round(baseLimit * (1 + extraPct / 100));

      const withinLimit = Math.min(grossBenefit, effectiveLimit);
      const excessCost = Math.max(0, grossBenefit - effectiveLimit);
      const copayCost = Math.round(withinLimit * copayRate);
      const nhisShare = withinLimit - copayCost;
      const mealTotal = mealDaily * totalDays;
      const familyTotal = copayCost + excessCost + mealTotal;

      out.innerHTML = `
        <div>
          <div class="out-line"><span>적용 1일 수가 (${esc(table[bandIdx].code)})</span><strong>${fmtWon(dailyUnit)}${holidays ? ` · 공휴일 ${fmtWon(holidayUnit)}` : ''}</strong></div>
          <div class="out-line"><span>월 총 급여비용 (${totalDays}일 이용)</span><strong>${fmtWon(grossBenefit)}</strong></div>
          <div class="out-line"><span>적용 월 한도액${extraPct ? ` (15일·8h+ 추가 +${extraPct}%)` : ''}</span><strong>${fmtWon(effectiveLimit)}</strong></div>
          <div class="out-line"><span>공단 부담금 (지원액)</span><strong style="color:var(--gov-navy);">${fmtWon(nhisShare)}</strong></div>
          <div class="out-line"><span>급여 본인부담금 (${Math.round(copayRate * 100)}%)</span><strong>${fmtWon(copayCost)}</strong></div>
          <div class="out-line"><span>한도 초과 전액부담액 (100%)</span><strong style="color:${excessCost ? 'var(--gov-danger)' : 'var(--gov-ok)'};">${fmtWon(excessCost)}</strong></div>
          <div class="out-line"><span>비급여 식사·간식비 (${totalDays}일)</span><strong>${fmtWon(mealTotal)}</strong></div>
        </div>
        <div class="out-total">
          <div>
            <div style="font-size:0.76rem;font-weight:700;color:var(--gov-navy-dark);">수급자(가족) 예상 월 총납부액</div>
            <div style="font-size:11px;color:var(--gov-slate-500);">본인부담금 + 한도초과 + 비급여 식대</div>
          </div>
          <div class="big">${fmtWon(familyTotal)}</div>
        </div>
      `;
    }

    ['opsRoomType', 'opsGrade', 'opsBand', 'opsCopay', 'opsDays', 'opsHolidays', 'opsMealDaily'].forEach(id => {
      document.getElementById(id)?.addEventListener('input', calcFee);
      document.getElementById(id)?.addEventListener('change', calcFee);
    });

    function trunc2(users, staff) {
      return staff > 0 ? Math.floor((users * 100) / staff) / 100 : Infinity;
    }

    function minCareForAddon(users, reqCount, limitRatio) {
      if (users <= 0) return 0;
      let n = reqCount + 1;
      while (trunc2(users, n) >= limitRatio && n < 200) n++;
      return n;
    }

    function getBasePointCap(total) {
      if (total < 5) return 1.4;
      if (total < 10) return 2.6;
      if (total < 30) return 4.0;
      if (total < 50) return 6.4;
      if (total < 70) return 8.8;
      if (total < 80) return 10.0;
      if (total < 90) return 11.2;
      if (total < 120) return 13.6;
      return 14.8;
    }

    function getExtraCareCapBonus(total, extraCare) {
      if (total < 10 || extraCare <= 0) return 0;
      if (total < 30) return extraCare >= 4 ? 2.4 : (extraCare === 3 ? 1.2 : 0);
      if (total < 50) return extraCare >= 5 ? 2.4 : (extraCare === 4 ? 1.2 : 0);
      if (total < 70) return extraCare >= 6 ? 2.4 : (extraCare === 5 ? 1.2 : 0);
      if (total < 90) return extraCare >= 7 ? 2.4 : (extraCare === 6 ? 1.2 : 0);
      if (total < 120) return extraCare >= 9 ? 3.6 : (extraCare === 8 ? 2.4 : (extraCare === 7 ? 1.2 : 0));
      return extraCare >= 10 ? 3.6 : (extraCare === 9 ? 2.4 : (extraCare === 8 ? 1.2 : 0));
    }

    const STF_INPUT_IDS = [
      'stfGeneralUsers', 'stfDementiaUsers', 'stfMonthlyBenefit',
      'stfActCareGen', 'stfActCareDem', 'stfActSw', 'stfActPt',
      'stfActNurse', 'stfActRn', 'stfActCook', 'stfProgramAddon',
    ];

    function saveStaffSim() {
      try {
        const data = { outsourced: !!document.getElementById('stfMealOutsourced')?.checked };
        STF_INPUT_IDS.forEach(id => {
          const el = document.getElementById(id);
          if (el) data[id] = el.value;
        });
        localStorage.setItem(STAFF_SIM_STORAGE_KEY, JSON.stringify(data));
      } catch (_) {}
    }

    function loadStaffSim() {
      try {
        const raw = localStorage.getItem(STAFF_SIM_STORAGE_KEY);
        if (!raw) return;
        const data = JSON.parse(raw);
        STF_INPUT_IDS.forEach(id => {
          const el = document.getElementById(id);
          if (el && data[id] !== undefined) el.value = data[id];
        });
        const outChk = document.getElementById('stfMealOutsourced');
        if (outChk && typeof data.outsourced === 'boolean') outChk.checked = data.outsourced;
      } catch (_) {}
    }

    function applyStaffPresetMode(mode) {
      const gen = Math.max(0, parseInt(document.getElementById('stfGeneralUsers').value || '0', 10));
      const dem = Math.max(0, parseInt(document.getElementById('stfDementiaUsers').value || '0', 10));
      const total = gen + dem;
      const outsourced = !!document.getElementById('stfMealOutsourced')?.checked;
      const careGenReq = gen > 0 ? Math.max(1, Math.round(gen / 7)) : 0;
      const careDemReq = dem > 0 ? Math.max(1, Math.round(dem / 4)) : 0;
      const swReq = total >= 10 ? 1 : 0;
      const cookReq = outsourced ? 0 : (total >= 1 ? 1 : 0);

      if (mode === 'min') {
        document.getElementById('stfActCareGen').value = String(careGenReq);
        document.getElementById('stfActCareDem').value = String(careDemReq);
        document.getElementById('stfActSw').value = String(swReq);
        document.getElementById('stfActPt').value = '0';
        document.getElementById('stfActNurse').value = total >= 1 ? '1' : '0';
        document.getElementById('stfActRn').value = '0';
        document.getElementById('stfActCook').value = String(cookReq);
        document.getElementById('stfProgramAddon').value = '0';
      } else {
        document.getElementById('stfActCareGen').value = String(minCareForAddon(gen, careGenReq, 6.4));
        document.getElementById('stfActCareDem').value = String(minCareForAddon(dem, careDemReq, 3.9));
        document.getElementById('stfActSw').value = String(total >= 10 ? swReq + 1 : 1);
        document.getElementById('stfActPt').value = total >= 30 ? '1' : '0';
        document.getElementById('stfActNurse').value = total >= 1 ? '1' : '0';
        document.getElementById('stfActRn').value = '0';
        document.getElementById('stfActCook').value = String(cookReq);
      }
      saveStaffSim();
      calcStaffing();
    }

    function calcStaffing() {
      const gen = Math.max(0, parseInt(document.getElementById('stfGeneralUsers').value || '0', 10));
      const dem = Math.max(0, parseInt(document.getElementById('stfDementiaUsers').value || '0', 10));
      const total = gen + dem;
      const outsourced = !!document.getElementById('stfMealOutsourced')?.checked;
      const monthlyBenefit = Math.max(0, parseFloat(document.getElementById('stfMonthlyBenefit')?.value || '0'));

      const actCareGen = Math.max(0, parseInt(document.getElementById('stfActCareGen')?.value || '0', 10));
      const actCareDem = Math.max(0, parseInt(document.getElementById('stfActCareDem')?.value || '0', 10));
      const actSw = Math.max(0, parseInt(document.getElementById('stfActSw')?.value || '0', 10));
      const actPt = Math.max(0, parseInt(document.getElementById('stfActPt')?.value || '0', 10));
      const actNurse = Math.max(0, parseInt(document.getElementById('stfActNurse')?.value || '0', 10));
      const rawRn = Math.max(0, parseInt(document.getElementById('stfActRn')?.value || '0', 10));
      const actRn = Math.min(actNurse, rawRn);
      const actCook = Math.max(0, parseInt(document.getElementById('stfActCook')?.value || '0', 10));
      const progVal = Number(document.getElementById('stfProgramAddon')?.value || '0');

      const swReq = total >= 10 ? 1 : 0;
      const nurseOrPtReq = total >= 1 ? 1 : 0;
      const clerkReq = total >= 25 ? 1 : 0;
      const helperReq = total >= 10 ? 1 : 0;
      const cookReq = outsourced ? 0 : (total >= 1 ? 1 : 0);
      const careGenMin = gen > 0 ? Math.max(1, Math.round(gen / 7)) : 0;
      const careDemMin = dem > 0 ? Math.max(1, Math.round(dem / 4)) : 0;
      const careGenAddon = minCareForAddon(gen, careGenMin, 6.4);
      const careDemAddon = minCareForAddon(dem, careDemMin, 3.9);
      const seniorCap = total >= 35 ? Math.floor(total / 35) : 0;

      // 법정 기준 미달 직종 점검
      const shortages = [];
      let violationCount = 0;
      if (actCareGen < careGenMin) { shortages.push(`일반실 요양보호사 ${careGenMin - actCareGen}명 부족`); violationCount++; }
      if (actCareDem < careDemMin) { shortages.push(`치매전담실 요양보호사 ${careDemMin - actCareDem}명 부족`); violationCount++; }
      if (actSw < swReq) { shortages.push(`사회복지사 ${swReq - actSw}명 부족`); violationCount++; }
      if ((actNurse + actPt) < nurseOrPtReq) { shortages.push('간호(조무)사·물리(작업)치료사 필수 1명 미배치'); violationCount++; }
      if (!outsourced && actCook < cookReq) { shortages.push('조리원 필수 1명 미배치'); violationCount++; }

      // 간호·물리치료 기본 1명 배분 (기관에 유리하도록 간호인력 우선 기본배정 후 물리치료 추가산정)
      let baseNurseUsed = 0, basePtUsed = 0;
      if (nurseOrPtReq === 1 && (actNurse + actPt) >= 1) {
        if (actNurse >= 1) baseNurseUsed = 1;
        else basePtUsed = 1;
      }

      const ratioGen = gen > 0 ? trunc2(gen, actCareGen) : 0;
      const ratioDem = dem > 0 ? trunc2(dem, actCareDem) : 0;
      const ratioNurse = total > 0 ? trunc2(total, actNurse) : 0;

      const extraCareGen = (gen > 0 && actCareGen > careGenMin && ratioGen < 6.4) ? (actCareGen - careGenMin) : 0;
      const extraCareDem = (dem > 0 && actCareDem > careDemMin && ratioDem < 3.9) ? (actCareDem - careDemMin) : 0;
      const extraSw = actSw > swReq ? (actSw - swReq) : 0;
      const extraPt = (actNurse + actPt) >= nurseOrPtReq ? Math.max(0, actPt - basePtUsed) : 0;
      const rawExtraNurse = (actNurse + actPt) >= nurseOrPtReq ? Math.max(0, actNurse - baseNurseUsed) : 0;
      const extraNurse = (rawExtraNurse > 0 && ratioNurse < 19.0) ? rawExtraNurse : 0;

      // 3개 직종 이상 인력기준 위반 시 전 직종 인력추가배치 가산 미적용(고시 제54조제3항)
      const blockAllByViolation = violationCount >= 3;
      const ptsCareGen = blockAllByViolation ? 0 : Math.round(extraCareGen * 120) / 100;
      const ptsCareDem = blockAllByViolation ? 0 : Math.round(extraCareDem * 120) / 100;
      const ptsSw = blockAllByViolation ? 0 : Math.round(extraSw * 140) / 100;
      const ptsPt = blockAllByViolation ? 0 : Math.round(extraPt * 140) / 100;
      const ptsNurse = blockAllByViolation ? 0 : Math.round(extraNurse * 120) / 100;

      const rawCappedPool = Math.round((ptsCareGen + ptsCareDem + ptsSw + ptsPt + ptsNurse) * 100) / 100;
      const baseCap = total > 0 ? getBasePointCap(total) : 0;
      const extraCapBonus = total > 0 ? getExtraCareCapBonus(total, extraCareGen + extraCareDem) : 0;
      const effectiveCap = Math.round((baseCap + extraCapBonus) * 100) / 100;
      const recognizedPool = Math.min(rawCappedPool, effectiveCap);
      const clippedPts = Math.round(Math.max(0, rawCappedPool - effectiveCap) * 100) / 100;

      const ptsCook = (!blockAllByViolation && !outsourced && total >= 1 && actCook > cookReq) ? 1.2 : 0;
      const ptsRn = total > 0 ? Math.round(actRn * 60) / 100 : 0;
      const ptsProg = gen > 0 ? progVal : 0;
      const totalPts = Math.round((recognizedPool + ptsCook + ptsRn + ptsProg) * 100) / 100;

      const serviceScore = (gen === 0 && dem > 0) ? 1.3 : 1.5;
      const denomUsers = gen > 0 ? gen : dem;
      const estPayout = (denomUsers > 0 && monthlyBenefit > 0 && totalPts > 0)
        ? Math.round(((monthlyBenefit * 0.85) * (totalPts / denomUsers) * serviceScore) / 10) * 10
        : 0;

      const trapGenWarn = (gen > 0 && actCareGen > careGenMin && ratioGen >= 6.4)
        ? `<div class="stf-alert warn">[6.4명 미만 미달 주의] 일반실 ${gen}명에 요양보호사 ${actCareGen}명 배치 시 1인당 <strong>${ratioGen.toFixed(2)}명</strong>(소수 셋째자리 절사)으로 6.4명 미만 요건에 미달하여 가산 0점입니다. 최소 <strong>${careGenAddon}명</strong>부터 가산(${((careGenAddon - careGenMin) * 1.2).toFixed(1)}점)됩니다.</div>`
        : '';
      const trapNurseWarn = (rawExtraNurse > 0 && ratioNurse >= 19.0)
        ? `<div class="stf-alert warn">[간호인력 19.0명 미만 미달] 간호(조무)사 추가 인원이 있으나 1인당 <strong>${ratioNurse.toFixed(2)}명</strong>으로 19.0명 미만 요건 미달(0점)입니다.</div>`
        : '';
      const capWarn = clippedPts > 0
        ? `<div class="stf-alert warn">[인정범위 상한 초과] 직종별 합계 ${rawCappedPool.toFixed(1)}점 중 구간 상한(<strong>${effectiveCap.toFixed(1)}점</strong>) 초과분 <strong>${clippedPts.toFixed(1)}점</strong>은 미인정됩니다(고시 제56조제2·4항).</div>`
        : '';

      document.getElementById('stfOutput').innerHTML = `
        <div>
          ${shortages.length
            ? `<div class="stf-alert danger">[법정 인력기준 미달 · 감액 주의] ${esc(shortages.join(' / '))}${blockAllByViolation ? ' (3개 직종 이상 위반으로 전 직종 인력추가배치 가산 제외)' : ''}</div>`
            : `<div class="stf-alert ok">[법정 인력배치기준 충족] 총 일일 이용자 ${total}명(일반 ${gen}${dem ? ` + 치매 ${dem}` : ''}) 필수 인력 요건을 모두 충족했습니다.</div>`
          }
          ${trapGenWarn}${trapNurseWarn}${capWarn}

          <div class="stf-sim-kpi">
            <div>
              <div style="font-size:0.76rem;font-weight:700;color:var(--gov-navy-dark);">인정 가산점수 총합 (상한 ${effectiveCap.toFixed(1)}점${extraCapBonus ? ` · 요보추가 +${extraCapBonus.toFixed(1)} 반영` : ''})</div>
              <div style="font-size:0.84rem;font-weight:800;color:var(--gov-ink);margin-top:2px;">
                인력추가 ${recognizedPool.toFixed(1)}점${ptsCook ? ` + 조리원 1.2점` : ''}${ptsRn ? ` + 간호사 ${ptsRn.toFixed(1)}점` : ''}${ptsProg ? ` + 프로그램 ${ptsProg}점` : ''} = <span style="color:var(--gov-navy);">${totalPts.toFixed(2)}점</span>
              </div>
            </div>
            <div style="text-align:right;">
              <div style="font-size:0.74rem;color:var(--gov-slate-600);font-weight:700;">예상 월 가산 수령액 (공단 100% 지급)</div>
              <div class="big">+${fmtWon(estPayout)}</div>
            </div>
          </div>

          <div class="gov-table-wrap" style="margin-bottom:8px;">
            <table class="gov-table" style="font-size:0.79rem;">
              <thead>
                <tr><th>직종</th><th>법정 의무</th><th>현재 배치</th><th>가산 판정 · 인정점수</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>요양보호사(일반)</strong></td>
                  <td>${careGenMin}명 <small style="color:var(--gov-slate-500);">(가산 ${careGenAddon}명+)</small></td>
                  <td><strong>${actCareGen}명</strong>${gen && actCareGen ? ` <small>(1인당 ${ratioGen.toFixed(2)}명)</small>` : ''}</td>
                  <td style="font-weight:700;color:${ptsCareGen ? 'var(--gov-ok)' : 'var(--gov-slate-600)'};">${ptsCareGen ? `+${extraCareGen}명 인정 (+${ptsCareGen.toFixed(1)}점)` : '해당없음 (0점)'}</td>
                </tr>
                ${dem > 0 ? `
                <tr>
                  <td><strong>요양보호사(치매)</strong></td>
                  <td>${careDemMin}명 <small style="color:var(--gov-slate-500);">(가산 ${careDemAddon}명+)</small></td>
                  <td><strong>${actCareDem}명</strong> <small>(1인당 ${ratioDem.toFixed(2)}명)</small></td>
                  <td style="font-weight:700;color:${ptsCareDem ? 'var(--gov-ok)' : 'var(--gov-slate-600)'};">${ptsCareDem ? `+${extraCareDem}명 인정 (+${ptsCareDem.toFixed(1)}점)` : '해당없음 (0점)'}</td>
                </tr>` : ''}
                <tr>
                  <td><strong>사회복지사</strong></td>
                  <td>${swReq ? '1명 필수' : '의무없음(10인미만)'}</td>
                  <td><strong>${actSw}명</strong></td>
                  <td style="font-weight:700;color:${ptsSw ? 'var(--gov-ok)' : 'var(--gov-slate-600)'};">${ptsSw ? `+${extraSw}명 추가 (+${ptsSw.toFixed(1)}점)` : '기본배치 (0점)'}</td>
                </tr>
                <tr>
                  <td><strong>간호(조무)·물리치료</strong></td>
                  <td>합산 ${nurseOrPtReq}명 필수</td>
                  <td>간호 <strong>${actNurse}</strong>(RN ${actRn}) · 물리 <strong>${actPt}</strong></td>
                  <td style="font-weight:700;color:${(ptsPt + ptsNurse + ptsRn) ? 'var(--gov-ok)' : 'var(--gov-slate-600)'};">
                    ${(ptsPt || ptsNurse || ptsRn)
                      ? [ptsPt ? `물리 +${ptsPt.toFixed(1)}점` : '', ptsNurse ? `간호추가 +${ptsNurse.toFixed(1)}점` : '', ptsRn ? `RN면허 +${ptsRn.toFixed(1)}점` : ''].filter(Boolean).join(' · ')
                      : '기본 1명 충당 (0점)'}
                  </td>
                </tr>
                <tr>
                  <td><strong>조리원</strong></td>
                  <td>${outsourced ? '위탁 면제' : `${cookReq}명 필수`}</td>
                  <td><strong>${actCook}명</strong></td>
                  <td style="font-weight:700;color:${ptsCook ? 'var(--gov-ok)' : 'var(--gov-slate-600)'};">${ptsCook ? '상한 외 별도 +1.2점' : (outsourced ? '위탁 제외' : '기본배치 (0점)')}</td>
                </tr>
                <tr>
                  <td><strong>시설장·사무원·보조원</strong></td>
                  <td colspan="3">시설장 <strong>1명</strong> 필수 / 사무원(25인+) <strong>${clerkReq ? '1명 필수' : '선택'}</strong> / 보조원·운전원(10인+) <strong>${helperReq ? '1명 필수(월50%+)' : '선택'}</strong></td>
                </tr>
                <tr>
                  <td><strong>선임 요양보호사(35인+)</strong></td>
                  <td colspan="3"><strong>${seniorCap ? `최대 ${seniorCap}명 지정 가능 (월 15만 원 장려수당)` : '이용자 35명 미만 해당없음'}</strong></td>
                </tr>
              </tbody>
            </table>
          </div>
          <p style="font-size:11.5px;color:var(--gov-slate-600);margin:0;">※ 가산금 산식(고시 제56조): (월 급여비용 합계 × 85%) × (인정 가산점수 ÷ 기준 이용자 ${denomUsers}명) × 서비스유형점수(${serviceScore}점), 10원 미만 반올림.</p>
        </div>
      `;
    }

    STF_INPUT_IDS.forEach(id => {
      const el = document.getElementById(id);
      el?.addEventListener('input', () => { saveStaffSim(); calcStaffing(); });
      el?.addEventListener('change', () => { saveStaffSim(); calcStaffing(); });
    });
    document.getElementById('stfMealOutsourced')?.addEventListener('change', () => {
      saveStaffSim();
      calcStaffing();
    });
    document.getElementById('btnStfAutoRev')?.addEventListener('click', () => {
      const g = Math.max(0, parseInt(document.getElementById('stfGeneralUsers').value || '0', 10));
      const d = Math.max(0, parseInt(document.getElementById('stfDementiaUsers').value || '0', 10));
      const baseUsers = g > 0 ? g : d;
      const unitAvg = (g === 0 && d > 0) ? 1500000 : 1250000;
      document.getElementById('stfMonthlyBenefit').value = String(baseUsers * unitAvg);
      saveStaffSim();
      calcStaffing();
      showToast(`${baseUsers}명 기준 월 예상 급여비용을 자동 입력했습니다.`);
    });
    document.getElementById('btnStfSetMin')?.addEventListener('click', () => {
      applyStaffPresetMode('min');
      showToast('현재 수급자 수 기준 법정 최소 인원으로 설정했습니다.');
    });
    document.getElementById('btnStfSetRec')?.addEventListener('click', () => {
      applyStaffPresetMode('rec');
      showToast('수급자 수에 맞는 추천 가산 인력 조합을 적용했습니다.');
    });
    document.querySelectorAll('#stfPresetBar [data-stf-preset]').forEach(btn => {
      btn.addEventListener('click', () => {
        const n = parseInt(btn.getAttribute('data-stf-preset'), 10);
        document.getElementById('stfGeneralUsers').value = String(n);
        document.getElementById('stfDementiaUsers').value = '0';
        document.getElementById('stfMonthlyBenefit').value = String(n * 1250000);
        document.querySelectorAll('#stfPresetBar [data-stf-preset]').forEach(b => b.classList.toggle('active', b === btn));
        applyStaffPresetMode('rec');
      });
    });

    loadStaffSim();

    function calcLabor() {
      const rev = Math.max(0, parseFloat(document.getElementById('lbrRevenue').value || '0'));
      const exp = Math.max(0, parseFloat(document.getElementById('lbrExpense').value || '0'));
      const ratio = rev > 0 ? (exp / rev) * 100 : 0;
      const targetAmt = rev * 0.486;
      const diff = exp - targetAmt;
      const pass = rev > 0 && ratio >= 48.6;

      document.getElementById('lbrOutput').innerHTML = `
        <div>
          <div class="out-line"><span>현재 장기요양요원 인건비 지출비율</span><strong style="color:${pass ? 'var(--gov-ok)' : 'var(--gov-danger)'};">${ratio.toFixed(2)}% (기준 48.6%)</strong></div>
          <div class="out-line"><span>48.6% 법정 최소 인건비 지출 기준액</span><strong>${fmtWon(targetAmt)}</strong></div>
          <div class="out-line"><span>기준 대비 ${diff >= 0 ? '여유액' : '부족액'}</span><strong style="color:${diff >= 0 ? 'var(--gov-ok)' : 'var(--gov-danger)'};">${diff >= 0 ? '+' : ''}${fmtWon(diff)}</strong></div>
        </div>
        <div class="out-total">
          <strong style="font-size:0.84rem;color:${pass ? 'var(--gov-ok)' : 'var(--gov-danger)'};">${pass ? '[충족] 2026 의무 인건비 지출비율(48.6%) 준수' : '[미달] 장기요양요원 4직종 인건비 보완 필요'}</strong>
        </div>
      `;
    }

    ['lbrRevenue', 'lbrExpense'].forEach(id => {
      document.getElementById(id)?.addEventListener('input', calcLabor);
    });

    calcFee();
    calcStaffing();
    calcLabor();

    function applyOpsHash() {
      const h = (location.hash || '').replace('#', '');
      if (['fees', 'staffing', 'sop', 'training', 'audit'].includes(h)) {
        switchOpsTab(h);
      }
    }
    applyOpsHash();
    window.addEventListener('hashchange', applyOpsHash);
  }

  /* =========================================================
     3. FORMS LIBRARY (/forms)
     ========================================================= */
  function initForms() {
    const root = document.getElementById('dcFormsApp');
    if (!root) return;

    const orgInput = document.getElementById('formsOrgName');
    const codeInput = document.getElementById('formsOrgCode');
    const bundleBtn = document.getElementById('dcBundleZipBtn');
    const searchInput = document.getElementById('formsSearch');
    let activeCat = 'ALL';

    function loadOrg() {
      try {
        const saved = JSON.parse(localStorage.getItem(ORG_STORAGE_KEY) || '{}');
        if (saved.org) orgInput.value = saved.org;
        if (saved.code) codeInput.value = saved.code;
      } catch (_) {}
    }

    function syncFormLinks() {
      const org = orgInput.value.trim();
      const code = codeInput.value.trim();
      const qs = new URLSearchParams();
      if (org) qs.set('org', org);
      if (code) qs.set('code', code);
      const suffix = qs.toString() ? `?${qs.toString()}` : '';

      document.querySelectorAll('.dc-form-dl').forEach(a => {
        a.href = a.getAttribute('data-base') + suffix;
      });
      if (bundleBtn) bundleBtn.href = '/forms/bundle.zip' + suffix;
      document.querySelectorAll('#drawer a[href^="/forms/bundle.zip"]').forEach(a => {
        a.href = '/forms/bundle.zip' + suffix;
      });
    }

    function filterForms() {
      const q = (searchInput.value || '').trim().toLowerCase();
      let shown = 0;
      document.querySelectorAll('#formsGrid .form-card').forEach(card => {
        const cat = card.getAttribute('data-fcat');
        const hay = card.getAttribute('data-fsearch') || '';
        const visible = (activeCat === 'ALL' || cat === activeCat) && (!q || hay.includes(q));
        card.hidden = !visible;
        if (visible) shown++;
      });
      document.getElementById('formsResultCount').textContent = `표시 중 ${shown}종`;
    }

    document.getElementById('btnApplyOrg')?.addEventListener('click', () => {
      try {
        localStorage.setItem(ORG_STORAGE_KEY, JSON.stringify({ org: orgInput.value.trim(), code: codeInput.value.trim() }));
      } catch (_) {}
      syncFormLinks();
      showToast('기관명·기관기호를 모든 다운로드 서식에 반영했습니다.');
    });

    document.getElementById('btnClearOrg')?.addEventListener('click', () => {
      orgInput.value = '';
      codeInput.value = '';
      try { localStorage.removeItem(ORG_STORAGE_KEY); } catch (_) {}
      syncFormLinks();
      showToast('기관명 입력을 초기화했습니다.');
    });

    orgInput?.addEventListener('input', syncFormLinks);
    codeInput?.addEventListener('input', syncFormLinks);
    searchInput?.addEventListener('input', filterForms);

    document.querySelectorAll('#formsCatTabs [data-fcat]').forEach(btn => {
      btn.addEventListener('click', () => {
        activeCat = btn.getAttribute('data-fcat');
        document.querySelectorAll('#formsCatTabs [data-fcat]').forEach(b => b.classList.toggle('active', b === btn));
        filterForms();
      });
    });

    loadOrg();
    syncFormLinks();
    applyQueryParam('formsSearch', () => {});
    filterForms();
  }

  initGlobalChrome();
  initEvaluation();
  initOperations();
  initForms();
  centerActiveSubtab();
})();
