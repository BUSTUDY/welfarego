(() => {
  'use strict';
  const SAVED = 'welfarego.saved.v1';
  const COMPARE = 'welfarego.compare.v1';
  let toastTimer;
  const toast = message => {
    const box = document.getElementById('toast');
    box.textContent = message;
    box.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { box.hidden = true; }, 3200);
  };
  function read(key) {
    try {
      const data = JSON.parse(localStorage.getItem(key) || '[]');
      return Array.isArray(data) ? [...new Set(data.filter(x => typeof x === 'string' && x.length <= 200))].slice(0, 100) : [];
    } catch { return []; }
  }
  function write(key, values) {
    try { localStorage.setItem(key, JSON.stringify(values)); return true; }
    catch { toast('브라우저 저장소를 사용할 수 없습니다. 사이트 데이터 설정을 확인해 주세요.'); return false; }
  }
  function syncSaved() {
    const values = read(SAVED);
    document.querySelectorAll('[data-saved-count]').forEach(el => { el.textContent = values.length; });
    document.querySelectorAll('[data-save]').forEach(button => {
      const selected = values.includes(button.dataset.save);
      button.setAttribute('aria-pressed', String(selected));
      const label = button.querySelector('span');
      if (label) label.textContent = selected ? '저장됨' : '저장';
    });
  }
  function syncCompare() {
    const values = read(COMPARE).slice(0, 3);
    document.querySelectorAll('[data-compare]').forEach(el => { el.checked = values.includes(el.dataset.compare); });
    const bar = document.getElementById('compare-bar');
    if (bar) {
      bar.hidden = !values.length;
      document.getElementById('compare-count').textContent = values.length;
      document.getElementById('compare-link').href = '/care/compare?ids=' + encodeURIComponent(values.join(','));
    }
  }
  let savedItems = [], savedFilter = 'all';
  const types = {jobs: '복지 일자리', care: '돌봄기관', benefits: '복지혜택', grants: '공공 지원사업'};
  function drawSaved() {
    const list = document.getElementById('saved-list');
    if (!list) return;
    list.replaceChildren();
    const keys = read(SAVED);
    const items = savedItems.filter(x => keys.includes(x.save_key) && (savedFilter === 'all' || x.kind === savedFilter));
    const missing = keys.length - savedItems.filter(x => keys.includes(x.save_key)).length;
    document.getElementById('saved-empty').hidden = items.length > 0 || (savedFilter === 'all' && missing > 0);
    document.getElementById('saved-status').textContent = `${items.length}개 항목` + (missing > 0 ? ` · 더 이상 제공되지 않는 ${missing}개 항목은 저장 목록에서 정리할 수 있습니다.` : '');
    for (const item of items) {
      const card = document.createElement('article');
      card.className = 'result-card';
      const source = document.createElement('p');
      source.className = 'record-source';
      source.textContent = `${types[item.kind]} · ${item.org || '제공기관 원문 확인'}`;
      const remove = document.createElement('button');
      remove.className = 'saved-remove'; remove.type = 'button';
      remove.textContent = '저장 해제'; remove.dataset.remove = item.save_key;
      remove.setAttribute('aria-label', item.name + ' 저장 해제');
      const title = document.createElement('h3');
      const link = document.createElement('a');
      link.className = 'saved-card-name'; link.textContent = item.name;
      // Only same-origin details or HTTP(S) URLs supplied by the server are accepted.
      const target = item.detail_url || item.url || '/' + item.kind;
      const url = new URL(target, location.origin);
      link.href = ['http:', 'https:'].includes(url.protocol) ? url.href : '/' + item.kind;
      if (url.origin !== location.origin) { link.target = '_blank'; link.rel = 'noopener noreferrer'; }
      title.append(link);
      const meta = document.createElement('p'); meta.className = 'record-meta';
      meta.textContent = `${item.kind === 'benefits' && !item.region ? '전국 공통' : item.location}` + (item.end ? ` · 마감 ${item.end} (${item.status_label})` : '');
      card.append(remove, source, title, meta); list.append(card);
    }
    for (const key of keys.filter(key => !savedItems.some(item => item.save_key === key))) {
      if (savedFilter !== 'all') continue;
      const card = document.createElement('article'); card.className = 'result-card';
      const label = document.createElement('p'); label.textContent = '현재 데이터에서 제공되지 않는 저장 항목';
      const remove = document.createElement('button'); remove.className = 'saved-remove'; remove.type = 'button';
      remove.textContent = '저장 해제'; remove.dataset.remove = key;
      card.append(remove, label); list.append(card);
    }
  }
  document.addEventListener('click', event => {
    const button = event.target.closest('[data-save]');
    if (button) {
      const values = read(SAVED), key = button.dataset.save, selected = values.includes(key);
      if (!selected && values.length >= 100) { toast('관심 항목은 최대 100개까지 저장할 수 있습니다.'); return; }
      if (write(SAVED, selected ? values.filter(x => x !== key) : [...values, key])) {
        syncSaved(); toast(selected ? '관심 공고에서 해제했습니다.' : '관심 공고에 저장했습니다.');
      }
    }
    const remove = event.target.closest('[data-remove]');
    if (remove && write(SAVED, read(SAVED).filter(x => x !== remove.dataset.remove))) { syncSaved(); drawSaved(); }
    const filter = event.target.closest('[data-saved-filter]');
    if (filter) {
      savedFilter = filter.dataset.savedFilter;
      document.querySelectorAll('[data-saved-filter]').forEach(el => { el.classList.toggle('active', el === filter); });
      drawSaved();
    }
    if (event.target.closest('#compare-clear') && write(COMPARE, [])) syncCompare();
  });
  document.addEventListener('change', event => {
    const input = event.target.closest('[data-compare]');
    if (!input) return;
    const values = read(COMPARE), key = input.dataset.compare;
    if (input.checked && values.length >= 3 && !values.includes(key)) {
      input.checked = false; toast('기관은 최대 3곳까지 비교할 수 있습니다.'); return;
    }
    write(COMPARE, input.checked ? [...new Set([...values, key])] : values.filter(x => x !== key));
    syncCompare();
  });
  window.addEventListener('storage', event => {
    if (event.key === SAVED || event.key === null) { syncSaved(); if (document.getElementById('saved-list')) loadSaved(); }
    if (event.key === COMPARE || event.key === null) syncCompare();
  });
  async function loadSaved() {
    const ids = read(SAVED);
    if (!ids.length) { savedItems = []; drawSaved(); return; }
    try {
      const response = await fetch('/api/portal/saved?ids=' + encodeURIComponent(ids.join(',')), {cache: 'no-store'});
      if (!response.ok) throw new Error('Request failed');
      const data = await response.json(); savedItems = data.items; drawSaved();
    } catch {
      document.getElementById('saved-status').textContent = '저장 항목을 불러오지 못했습니다. 잠시 후 페이지를 새로고침해 주세요.';
    }
  }
  syncSaved(); syncCompare();
  if (document.getElementById('saved-list')) loadSaved();
})();
