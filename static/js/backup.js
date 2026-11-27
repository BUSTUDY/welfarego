/*
 * 내 자료 백업 · 불러오기 (엑셀 .xlsx)
 *
 * - 사용자가 입력한 자료는 서버에 없고 브라우저 localStorage에만 있으므로,
 *   브라우저를 바꾸거나 캐시를 지우기 전에 엑셀 파일로 보관할 수 있게 한다.
 * - 파일 생성·읽기는 모두 브라우저 안에서 처리하며 서버로 전송하지 않는다.
 * - 엑셀 라이브러리(SheetJS)는 백업 창에서 실제로 쓸 때만 불러온다.
 */
(() => {
  'use strict';

  const FORMAT = 'welfarego-daycare-backup';
  const VERSION = 1;
  const SHEET_INFO = '안내';
  const SHEET_DATA = '백업데이터';
  const DATA_HEADER = ['키', '항목', '순번', '데이터(JSON)'];
  const CHUNK = 30000; // 엑셀 셀 한도(32,767자)보다 작게 나눠 저장
  const MAX_FILE_BYTES = 5 * 1024 * 1024;

  // 백업 대상. 글자 크기·화면 테마 같은 표시 설정은 제외한다.
  const ITEMS = [
    { key: 'daycare_eval_2026_state_v1', label: '평가매뉴얼 자가진단·서류점검·일정·면담' },
    { key: 'welfarego.daycare.org.v1', label: '기관명·기관기호' },
    { key: 'welfarego.daycare.staffsim.v1', label: '인력배치·가산 시뮬레이터' },
    { key: 'welfarego.daycare.worktime.v1', label: '월 기준시간·근무표' },
    { key: 'welfarego.daycare.records.v1', label: '기록 문안 보관함' },
    { key: 'welfarego.daycare.calendar.v1', label: '월간 이용달력' },
    { key: 'welfarego.daycare.shuttle.v1', label: '차량 송영 운행일지' },
  ];
  const ITEM_BY_KEY = new Map(ITEMS.map(it => [it.key, it]));

  let xlsxPromise = null;
  let overlay = null;
  let lastFocus = null;
  let pending = null; // 불러오기 확인 대기 중인 항목 [{key, label, text}]

  function toast(msg) {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.hidden = false;
    clearTimeout(window.__govToastTimer);
    window.__govToastTimer = setTimeout(() => { t.hidden = true; }, 3500);
  }

  function readStore(key) {
    try { return localStorage.getItem(key); } catch (_) { return null; }
  }

  function loadXlsx() {
    if (window.XLSX) return Promise.resolve(window.XLSX);
    if (xlsxPromise) return xlsxPromise;
    const holder = document.querySelector('script[data-xlsx-src]');
    const src = holder && holder.getAttribute('data-xlsx-src');
    if (!src) return Promise.reject(new Error('엑셀 라이브러리 경로를 찾을 수 없습니다.'));
    xlsxPromise = new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = src;
      s.onload = () => (window.XLSX ? resolve(window.XLSX) : reject(new Error('엑셀 라이브러리를 초기화하지 못했습니다.')));
      s.onerror = () => { xlsxPromise = null; reject(new Error('엑셀 라이브러리를 불러오지 못했습니다. 네트워크를 확인해 주세요.')); };
      document.head.appendChild(s);
    });
    return xlsxPromise;
  }

  function pad(n) { return String(n).padStart(2, '0'); }

  function stamp(d) {
    return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}`;
  }

  function currentSummary() {
    return ITEMS.map(it => {
      const raw = readStore(it.key);
      return { ...it, has: raw !== null && raw !== '', size: raw ? raw.length : 0 };
    });
  }

  /* ───────────── 백업 파일 만들기 ───────────── */
  async function exportBackup() {
    const present = currentSummary().filter(it => it.has);
    if (!present.length) {
      setStatus('백업할 자료가 아직 없습니다. 도구에서 자료를 입력·저장한 뒤 다시 시도해 주세요.', 'warn');
      return;
    }
    setStatus('엑셀 파일을 만드는 중입니다…');
    let XLSX;
    try { XLSX = await loadXlsx(); } catch (e) { setStatus(e.message, 'err'); return; }

    const now = new Date();
    const dataRows = [DATA_HEADER];
    present.forEach(it => {
      const raw = readStore(it.key) || '';
      for (let i = 0, part = 1; i < raw.length || part === 1; i += CHUNK, part += 1) {
        dataRows.push([it.key, it.label, part, raw.slice(i, i + CHUNK)]);
        if (i + CHUNK >= raw.length) break;
      }
    });

    const infoRows = [
      ['웰페어고 내 자료 백업'],
      [],
      ['형식', FORMAT],
      ['버전', VERSION],
      ['생성일시', now.toLocaleString('ko-KR')],
      ['사이트', location.origin],
      [],
      ['※ 이 파일은 웰페어고의 [내 자료 백업] → [백업 불러오기]로 복원합니다.'],
      ['※ "백업데이터" 시트의 내용은 수정·삭제하지 마세요. 값이 바뀌면 복원되지 않을 수 있습니다.'],
      ['※ 개인정보가 포함될 수 있으니 파일을 외부에 공유하지 마세요.'],
      [],
      ['포함된 항목', '백업 여부'],
      ...currentSummary().map(it => [it.label, it.has ? '포함' : '저장된 자료 없음']),
    ];

    const wb = XLSX.utils.book_new();
    const wsInfo = XLSX.utils.aoa_to_sheet(infoRows);
    wsInfo['!cols'] = [{ wch: 44 }, { wch: 30 }];
    const wsData = XLSX.utils.aoa_to_sheet(dataRows);
    wsData['!cols'] = [{ wch: 34 }, { wch: 36 }, { wch: 8 }, { wch: 90 }];
    XLSX.utils.book_append_sheet(wb, wsInfo, SHEET_INFO);
    XLSX.utils.book_append_sheet(wb, wsData, SHEET_DATA);

    const buf = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
    const blob = new Blob([buf], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `웰페어고_내자료백업_${stamp(now)}.xlsx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
    setStatus(`${present.length}개 항목을 엑셀 파일로 저장했습니다. 다운로드 폴더를 확인해 주세요.`, 'ok');
  }

  /* ───────────── 백업 파일 읽기 ───────────── */
  function cellText(v) {
    return v === null || v === undefined ? '' : String(v);
  }

  function parseWorkbook(XLSX, wb) {
    const info = wb.Sheets[SHEET_INFO];
    const data = wb.Sheets[SHEET_DATA];
    if (!info || !data) throw new Error('웰페어고 백업 파일이 아닙니다. ("안내", "백업데이터" 시트가 없습니다.)');

    const infoRows = XLSX.utils.sheet_to_json(info, { header: 1, defval: '', raw: true });
    const fmt = infoRows.find(r => cellText(r[0]).trim() === '형식');
    if (!fmt || cellText(fmt[1]).trim() !== FORMAT) throw new Error('웰페어고 백업 파일이 아닙니다. (형식 정보가 다릅니다.)');
    const ver = infoRows.find(r => cellText(r[0]).trim() === '버전');
    if (!ver || Number(ver[1]) > VERSION) throw new Error('더 최신 버전의 백업 파일입니다. 사이트를 새로고침한 뒤 다시 시도해 주세요.');

    const rows = XLSX.utils.sheet_to_json(data, { header: 1, defval: '', raw: true });
    const parts = new Map();
    let ignored = 0;
    rows.slice(1).forEach(r => {
      const key = cellText(r[0]).trim();
      if (!key) return;
      if (!ITEM_BY_KEY.has(key)) { ignored += 1; return; }
      const no = Number(r[2]);
      if (!Number.isInteger(no) || no < 1) throw new Error(`"${key}" 항목의 순번이 올바르지 않습니다.`);
      if (!parts.has(key)) parts.set(key, []);
      parts.get(key).push({ no, text: cellText(r[3]) });
    });

    const result = [];
    parts.forEach((list, key) => {
      list.sort((a, b) => a.no - b.no);
      list.forEach((p, i) => {
        if (p.no !== i + 1) throw new Error(`"${ITEM_BY_KEY.get(key).label}" 항목의 데이터가 일부 누락되었습니다.`);
      });
      const text = list.map(p => p.text).join('');
      let parsed;
      try { parsed = JSON.parse(text); } catch (_) {
        throw new Error(`"${ITEM_BY_KEY.get(key).label}" 항목의 데이터가 손상되었습니다. 백업 파일을 수정하지 않았는지 확인해 주세요.`);
      }
      if (parsed === null || typeof parsed !== 'object') {
        throw new Error(`"${ITEM_BY_KEY.get(key).label}" 항목의 데이터 형식이 올바르지 않습니다.`);
      }
      result.push({ key, label: ITEM_BY_KEY.get(key).label, text });
    });
    if (!result.length) throw new Error('복원할 자료가 없는 백업 파일입니다.');
    result.sort((a, b) => ITEMS.findIndex(i => i.key === a.key) - ITEMS.findIndex(i => i.key === b.key));
    return { items: result, ignored };
  }

  async function handleFile(file) {
    pending = null;
    renderPending();
    if (!file) return;
    if (!/\.xlsx$/i.test(file.name)) { setStatus('.xlsx 형식의 엑셀 파일만 불러올 수 있습니다.', 'err'); return; }
    if (file.size > MAX_FILE_BYTES) { setStatus('파일이 너무 큽니다. (최대 5MB)', 'err'); return; }
    setStatus('백업 파일을 읽는 중입니다…');
    try {
      const XLSX = await loadXlsx();
      const wb = XLSX.read(await file.arrayBuffer(), { type: 'array' });
      const { items, ignored } = parseWorkbook(XLSX, wb);
      pending = items;
      renderPending();
      setStatus(`백업 파일을 확인했습니다. ${items.length}개 항목을 복원할 수 있습니다.` +
        (ignored ? ` (알 수 없는 항목 ${ignored}행은 건너뜁니다.)` : ''), 'ok');
    } catch (e) {
      setStatus(e && e.message ? e.message : '백업 파일을 읽지 못했습니다.', 'err');
    }
  }

  function applyRestore() {
    if (!pending || !pending.length) return;
    const before = pending.map(it => ({ key: it.key, prev: readStore(it.key) }));
    try {
      pending.forEach(it => localStorage.setItem(it.key, it.text));
    } catch (_) {
      // 일부만 쓰인 상태가 남지 않도록 되돌린다.
      before.forEach(b => {
        try { if (b.prev === null) localStorage.removeItem(b.key); else localStorage.setItem(b.key, b.prev); } catch (__) { /* noop */ }
      });
      setStatus('브라우저 저장 공간에 쓸 수 없어 복원하지 못했습니다. 기존 자료는 그대로 유지됩니다.', 'err');
      return;
    }
    const n = pending.length;
    pending = null;
    setStatus(`${n}개 항목을 복원했습니다. 잠시 후 화면을 새로고침합니다…`, 'ok');
    setTimeout(() => location.reload(), 900);
  }

  /* ───────────── 대화상자 ───────────── */
  function setStatus(msg, kind) {
    const el = document.getElementById('bkStatus');
    if (!el) { toast(msg); return; }
    el.textContent = msg;
    el.className = 'bk-status' + (kind ? ` is-${kind}` : '');
  }

  function renderSummary() {
    const ul = document.getElementById('bkSummary');
    if (!ul) return;
    ul.textContent = '';
    currentSummary().forEach(it => {
      const li = document.createElement('li');
      li.className = it.has ? 'has' : 'none';
      const name = document.createElement('span');
      name.textContent = it.label;
      const state = document.createElement('em');
      state.textContent = it.has ? '저장됨' : '없음';
      li.append(name, state);
      ul.appendChild(li);
    });
  }

  function renderPending() {
    const box = document.getElementById('bkPending');
    if (!box) return;
    box.textContent = '';
    box.hidden = !pending;
    if (!pending) return;
    const p = document.createElement('p');
    p.textContent = '아래 항목을 이 브라우저에 복원합니다. 이미 저장된 같은 항목은 백업 파일 내용으로 덮어씁니다.';
    const ul = document.createElement('ul');
    pending.forEach(it => {
      const li = document.createElement('li');
      li.textContent = it.label + (readStore(it.key) ? ' (현재 자료를 덮어씀)' : '');
      ul.appendChild(li);
    });
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn btn-primary';
    btn.textContent = '복원하고 새로고침';
    btn.addEventListener('click', applyRestore);
    box.append(p, ul, btn);
  }

  function buildOverlay() {
    const el = document.createElement('div');
    el.className = 'bk-overlay no-print';
    el.hidden = true;
    el.innerHTML = `
      <div class="bk-panel" role="dialog" aria-modal="true" aria-labelledby="bkTitle">
        <div class="bk-head">
          <h2 id="bkTitle">내 자료 백업</h2>
          <button type="button" class="icon-btn" id="bkClose" aria-label="닫기">&times;</button>
        </div>
        <p class="bk-lead">입력한 자료는 서버가 아닌 <strong>이 브라우저</strong>에만 저장됩니다. 브라우저를 바꾸거나 기록·캐시를 지우면 사라지므로 엑셀 파일로 보관해 두세요. 파일은 이 기기에서만 만들고 읽으며 서버로 전송되지 않습니다.</p>
        <ul class="bk-summary" id="bkSummary"></ul>
        <div class="bk-actions">
          <button type="button" class="btn btn-primary" id="bkExport">엑셀로 백업하기</button>
          <button type="button" class="btn btn-soft" id="bkImport">백업 불러오기</button>
          <input type="file" id="bkFile" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" hidden>
        </div>
        <div class="bk-pending" id="bkPending" hidden></div>
        <p class="bk-status" id="bkStatus" role="status" aria-live="polite"></p>
        <p class="bk-note">백업 파일에는 기관명 등 개인정보가 포함될 수 있습니다. 공용 PC에서는 사용 후 파일을 삭제해 주세요.</p>
      </div>`;
    document.body.appendChild(el);

    el.addEventListener('click', e => { if (e.target === el) closeDialog(); });
    el.querySelector('#bkClose').addEventListener('click', closeDialog);
    el.querySelector('#bkExport').addEventListener('click', exportBackup);
    const file = el.querySelector('#bkFile');
    el.querySelector('#bkImport').addEventListener('click', () => file.click());
    file.addEventListener('change', () => { const f = file.files && file.files[0]; file.value = ''; handleFile(f); });
    el.addEventListener('keydown', e => {
      if (e.key === 'Escape') { closeDialog(); return; }
      if (e.key !== 'Tab') return;
      const f = Array.from(el.querySelectorAll('button:not([hidden])')).filter(b => !b.disabled && b.offsetParent !== null);
      if (!f.length) return;
      const first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });
    return el;
  }

  function openDialog() {
    if (!overlay) overlay = buildOverlay();
    lastFocus = document.activeElement;
    pending = null;
    renderSummary();
    renderPending();
    setStatus('');
    overlay.hidden = false;
    document.documentElement.classList.add('bk-open');
    const first = overlay.querySelector('#bkExport');
    if (first) first.focus();
    // 라이브러리를 미리 받아 두면 첫 클릭이 빨라진다.
    loadXlsx().catch(() => {});
  }

  function closeDialog() {
    if (!overlay) return;
    overlay.hidden = true;
    pending = null;
    document.documentElement.classList.remove('bk-open');
    if (lastFocus && typeof lastFocus.focus === 'function') lastFocus.focus();
  }

  document.addEventListener('click', e => {
    const trigger = e.target.closest('[data-backup-open], [data-backup-export], [data-backup-import]');
    if (!trigger) return;
    e.preventDefault();
    const drawer = document.getElementById('drawer');
    if (drawer && !drawer.hidden && drawer.contains(trigger)) document.getElementById('btnMenuClose')?.click();
    openDialog();
    // 화면에 바로 놓인 버튼은 대화상자를 연 뒤 곧바로 해당 동작을 실행한다.
    // (파일 선택창은 클릭 직후에만 열 수 있으므로 같은 클릭 안에서 호출한다.)
    if (trigger.hasAttribute('data-backup-export')) exportBackup();
    else if (trigger.hasAttribute('data-backup-import')) overlay.querySelector('#bkFile').click();
  });

  if (location.hash === '#backup') openDialog();
})();
