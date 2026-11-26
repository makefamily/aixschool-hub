// AI 학교 허브 화면 — 외부 라이브러리 없음.
window.addEventListener('error', (e) => { try { fetch('/api/client-log', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ m: '화면 오류: ' + e.message + ' @' + e.lineno }) }); } catch {} toast('화면에 문제가 생겼어요. 앱을 껐다 켜 주세요'); });
window.addEventListener('unhandledrejection', (e) => { try { fetch('/api/client-log', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ m: '화면 오류: ' + (e.reason?.message || e.reason) }) }); } catch {} });

const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const ic = (id, cls = '') => `<svg class="i ${cls}"><use href="#${id}"/></svg>`;
const api = async (url, opt = {}) => { const r = await fetch(url, { headers: { 'content-type': 'application/json' }, ...opt, body: opt.body ? JSON.stringify(opt.body) : undefined }); const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.msg || `오류 ${r.status}`); return j; };
const S = { st: null, view: 'today', taskId: null, task: null, files: [], sideTab: 'preview', previewSrc: '', mdText: null, usage: null, q: '', res: [], setTab: 'ai', scan: null, scanBusy: false, pane: 'list', learnBusy: false, pending: [], rules: null, auth: null, dir: {}, staff: null, skills: null, prefill: null, my: null, conns: null, oss: null, login: {}, split: false, splitIds: [], splitTasks: {}, att: {} };
try { const v = JSON.parse(localStorage.getItem('split') || 'null'); if (v) { S.split = !!v.on; S.splitIds = (v.ids || []).slice(0, 4); } } catch {}
function saveSplit() { try { localStorage.setItem('split', JSON.stringify({ on: S.split, ids: S.splitIds })); } catch {} }
function toast(t) { const d = document.createElement('div'); d.className = 'toast'; d.textContent = t; document.body.appendChild(d); setTimeout(() => d.remove(), 3600); }
const ago = (iso) => { if (!iso) return ''; const m = Math.round((Date.now() - new Date(iso)) / 60000); return m < 1 ? '방금' : m < 60 ? `${m}분 전` : m < 1440 ? `${Math.round(m / 60)}시간 전` : `${Math.round(m / 1440)}일 전`; };
const stLabel = (s) => ({ working: ['work', '하는 중'], done: ['done', '끝남'], error: ['late', '오류'], idle: ['done', '새 작업'] }[s] || ['done', s]);
const base = (p) => String(p || '').split(/[\\/]/).filter(Boolean).pop() || p;
const rtName = (r) => (r === 'claude' ? 'Claude' : 'Codex');
const modelOpts = (rt, sel = '') => ((S.models && S.models[rt]) || [{ id: '', label: 'Default' }]).map((m) => `<option value="${esc(m.id)}" ${m.id === sel ? 'selected' : ''}>${esc(m.label)}</option>`).join('');
const MODEL_HELP = '모델은 대화를 시작할 때 정해요. 바꾸려면 새로 맡기기에서 골라 새 대화로 맡겨 주세요';
const rtChip = (t) => `<button type="button" class="chip mchip" data-act="ctxhelp" data-msg="${esc(MODEL_HELP)}" title="${esc(MODEL_HELP)}">${rtName(t.runtime)}${t.modelLabel ? ' · ' + esc(t.modelLabel) : ''}</button>`;
// 대화가 얼마나 찼나: 50%부터 새 대화를 권한다
const ctxChip = (t) => { const p = ctxPct(t); if (p == null) return ''; const msg = `이 대화가 기억할 수 있는 양 중 ${p}%를 썼어요. 50%가 넘으면 새 대화로 이어가는 게 좋아요`; return `<button type="button" class="ctxchip ${p >= 80 ? 'hot' : p >= 50 ? 'warn' : ''}" data-act="ctxhelp" data-msg="${esc(msg)}" title="${esc(msg)}"><span class="bar" role="progressbar" aria-label="대화가 찬 정도" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${p}"><i style="width:${Math.max(3, p)}%"></i></span>대화 ${p}% 참</button>`; };
const ctxPct = (t) => (t.ctx && typeof t.ctx.pct === 'number' ? t.ctx.pct : null);
// ── 붙여 넣은 사진(대화창마다 따로): 'send' / 'new-today' / 'p-태스크ID'
const attKey = (f) => (f.dataset.form === 'send' ? `send-${S.taskId}` : f.dataset.form === 'newtask' ? `new-${f.dataset.where}` : `p-${f.dataset.id}`);
const ATT_MAX = 6;
function attStrip(k) {
  const L = S.att[k] || []; if (!L.length) return '';
  return `<div class="atts">${L.map((x, i) => `<div class="att"><img src="${x.data}" alt="붙인 사진 ${i + 1}"><button type="button" data-act="attdel" data-k="${esc(k)}" data-i="${i}" aria-label="사진 빼기">×</button></div>`).join('')}</div>`;
}
const attBtn = (k) => `<button type="button" class="btn attbtn" data-act="attpick" aria-label="사진 붙이기" title="사진 붙이기 · 캡처를 Ctrl+V(맥은 Cmd+V)로 붙여 넣어도 돼요">${ic('image', 's')}사진</button><input type="file" accept="image/png,image/jpeg,image/gif,image/webp,image/heic,image/heif" multiple data-attin="${esc(k)}" hidden tabindex="-1">`;
const readUrl = (blob) => new Promise((ok, no) => { const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = () => no(r.error); r.readAsDataURL(blob); });
// 큰 캡처는 줄인다(AI가 받는 한 장 크기 제한 5MB). 글씨가 읽히게 긴 쪽 2000px까지만 줄이고, 그래도 크면 JPG로.
async function prepImage(file) {
  const OK = ['image/png', 'image/jpeg', 'image/gif', 'image/webp'], LIMIT = 3.5 * 1024 * 1024;
  const url = await readUrl(file);
  const img = await new Promise((ok, no) => { const im = new Image(); im.onload = () => ok(im); im.onerror = () => no(new Error('이 사진은 열 수 없어요')); im.src = url; });
  const big = Math.max(img.naturalWidth, img.naturalHeight);
  if (!big) throw new Error('이 사진은 열 수 없어요');
  if (OK.includes(file.type) && file.size <= LIMIT && big <= 2400) return url;
  const k = Math.min(1, 2000 / big); const c = document.createElement('canvas');
  c.width = Math.round(img.naturalWidth * k); c.height = Math.round(img.naturalHeight * k);
  c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
  let out = c.toDataURL('image/png');
  if (out.length * 0.75 > LIMIT) { const x = c.getContext('2d'); x.globalCompositeOperation = 'destination-over'; x.fillStyle = '#fff'; x.fillRect(0, 0, c.width, c.height); out = c.toDataURL('image/jpeg', 0.9); } // 투명 배경이 검게 나오지 않게
  return out;
}
const isImg = (f) => f && (/^image\//.test(f.type) || (!f.type && /\.(png|jpe?g|gif|webp|heic|heif)$/i.test(f.name || '')));
async function addImages(k, files) {
  const all = [...files]; const imgs = all.filter(isImg);
  if (all.length > imgs.length) toast('사진(PNG·JPG·GIF·WEBP)만 붙일 수 있어요');
  if (!imgs.length) return false;
  const L = (S.att[k] ||= []);
  S.attBusy = (S.attBusy || 0) + 1;
  try {
    for (const f of imgs) {
      if (L.length >= ATT_MAX) { toast(`사진은 한 번에 ${ATT_MAX}장까지예요`); break; }
      try { const d = await prepImage(f); if (/^data:image\/(png|jpeg|gif|webp);base64,/.test(d)) L.push({ data: d }); else toast('이 사진은 열 수 없어요'); } catch (e) { toast(e.message || '사진을 붙이지 못했어요'); }
    }
  } finally { S.attBusy--; }
  render(); return true;
}
const fileUrl = (name) => `/files/${S.taskId}/${String(name).split('/').map(encodeURIComponent).join('/')}`;

// ── 마크다운 그리기: AI 답·.md 결과물의 기호(**, #, -, 표)를 보기 좋게. 먼저 전부 이스케이프한 뒤 바꾼다(안전).
function inline(s) {
  return s
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
    .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, '$1<i>$2</i>')
    .replace(/\[([^\]]+)\]\((?:&lt;)?([^)\s]*?)(?:&gt;)?\)/g, (_, label, href) => {
      if (/^https?:/i.test(href)) return `<a href="#" data-act="openurl" data-url="${href}">${label}</a>`;
      const name = decodeURIComponent(href.replace(/^\.\//, '').split(/[\\/]/).pop() || label);
      return `<button class="chip" data-act="preview" data-name="${esc(name)}">${ic('file', 's')}${label}</button>`;
    });
}
function md(src) {
  const lines = esc(src).split('\n'); const out = []; let i = 0;
  while (i < lines.length) {
    const l = lines[i];
    if (/^```/.test(l)) { const buf = []; i++; while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]); i++; out.push(`<pre><code>${buf.join('\n')}</code></pre>`); continue; }
    if (/^\s*\|.*\|\s*$/.test(l) && i + 1 < lines.length && /^\s*\|[\s:|-]+\|\s*$/.test(lines[i + 1])) {
      const cells = (x) => x.trim().replace(/^\||\|$/g, '').split('|').map((c) => inline(c.trim()));
      const head = cells(l); i += 2; const rows = [];
      while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) rows.push(cells(lines[i++]));
      out.push(`<div class="mdt"><table><thead><tr>${head.map((c) => `<th>${c}</th>`).join('')}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`); continue;
    }
    let m;
    if ((m = l.match(/^(#{1,6})\s+(.*)$/))) { out.push(`<p class="mh">${inline(m[2])}</p>`); i++; continue; }
    if (/^\s*([-*]|\d+[.)])\s+/.test(l)) {
      const ordered = /^\s*\d+[.)]\s+/.test(l); const items = [];
      while (i < lines.length && /^\s*([-*]|\d+[.)])\s+/.test(lines[i])) items.push(inline(lines[i++].replace(/^\s*([-*]|\d+[.)])\s+/, '')));
      out.push(`<${ordered ? 'ol' : 'ul'}>${items.map((x) => `<li>${x}</li>`).join('')}</${ordered ? 'ol' : 'ul'}>`); continue;
    }
    if (/^\s*(---|\*\*\*)\s*$/.test(l)) { out.push('<hr>'); i++; continue; }
    if (!l.trim()) { i++; continue; }
    const para = []; while (i < lines.length && lines[i].trim() && !/^(#{1,6}\s|```|\s*([-*]|\d+[.)])\s+|\s*\|)/.test(lines[i])) para.push(inline(lines[i++]));
    if (para.length) out.push(`<p>${para.join('<br>')}</p>`); else { out.push(`<p>${inline(l)}</p>`); i++; }
  }
  return out.join('');
}

async function load() { S.st = await api('/api/state'); api('/api/my').then((m) => { S.my = m; if (S.view === 'today') render(); }).catch(() => {}); if (S.taskId) await openTask(S.taskId, true); render(); }
async function loadUsage() { try { S.usage = await api('/api/usage'); renderSB(); } catch {} }
async function openTask(id, quiet) {
  if (S.taskId !== id) S.markEdit = false;
  S.taskId = id; S.task = await api(`/api/tasks/${id}`);
  S.files = await api(`/api/tasks/${id}/files`).catch(() => []);
  if (!S.previewSrc || !(S.previewSrc.startsWith(`/files/${id}/`) || S.previewSrc.startsWith(`/api/tasks/${id}/img/`))) { const h = S.files.find((f) => /\.html?$/i.test(f.name)) || S.files.find((f) => /\.(png|jpe?g|webp|gif|svg|pdf|md|txt)$/i.test(f.name)); setPreview(h ? fileUrl(h.name) : ''); }
  if (!quiet) { S.view = 'work'; S.pane = 'chat'; render(); }
}
// .md·.txt 결과물은 글자를 받아 그려서 보여 준다
async function setPreview(u) {
  S.previewSrc = u; S.mdText = null;
  if (/\.(md|txt)$/i.test(u.split('?')[0])) { try { S.mdText = await (await fetch(u)).text(); } catch { S.mdText = ''; } render(); }
}

// ── 위 줄 ──
function topbar() {
  const tasks = S.st.tasks; const w = tasks.some((x) => x.status === 'working');
  const tab = (v, icon, name, extra = '') => `<button class="tab ${S.view === v ? 'on' : ''}" data-act="go" data-v="${v}">${ic(icon)}${name}${extra}</button>`;
  const tabs = tab('today', 'home', '오늘') + tab('work', 'layers', '내 작업', `<span class="c num">${tasks.length}</span>${w ? '<span class="dot work"></span>' : ''}`) + tab('staff', 'users', 'AI 직원') + tab('settings', 'gear', '설정');
  return `<div class="top"><span class="mark">AI</span><div class="tabs">${tabs}</div><span class="sp"></span>
  <div class="top-r">${S.st.pending ? `<button class="waiting" data-act="settings" data-tab="learn"><span class="dot wait"></span>규칙 후보 <b class="num">${S.st.pending}</b></button>` : ''}
  <button class="me" data-act="settings" data-tab="me">${esc(S.st.me || '이름')}</button></div></div>`;
}

// ── 업데이트 알림: 앱 오른쪽 아래(상태 줄 위)에 카드로 뜬다 ──
const X_SVG = '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8"/></svg>';
function updCardHtml() {
  const u = S.upd; if (!u) return '';
  if (u.updating) return `<div class="updcard" role="status" aria-live="polite" aria-label="업데이트하는 중"><div class="uc-head"><h3>업데이트하는 중</h3></div><p>${esc(u.updating)}</p><div class="uc-bar"><i></i></div><p class="uc-sub">끝나면 화면이 저절로 새로 열려요.</p></div>`;
  if (!u.available || S.updHide === u.latest) return '';
  const notes = (u.notes || '').trim();
  return `<div class="updcard" role="complementary" aria-live="polite" aria-label="새 버전 알림"><div class="uc-head"><h3>새 버전이 나왔어요</h3><button class="uc-x" data-act="updlater" aria-label="나중에 하기" title="나중에">${X_SVG}</button></div><p>AI 학교 허브 <span class="num">v${esc(u.latest)}</span>을 받을 수 있어요.</p><p class="uc-sub">누르면 새 버전으로 바꾸고 저절로 다시 켜져요. 맡긴 일과 대화는 그대로 남아요.</p>${notes && S.updNotes ? `<div class="uc-notes">${esc(notes)}</div>` : ''}${notes ? `<button class="uc-link" data-act="updnotes">${S.updNotes ? '바뀐 내용 접기' : '바뀐 내용 보기'}</button>` : ''}<button class="btn pri uc-go" data-act="update">업데이트</button></div>`;
}
let updShown = '';
function renderUpd() {
  let box = $('#updpop'); if (!box) { box = document.createElement('div'); box.id = 'updpop'; document.body.appendChild(box); }
  // 오른쪽에 내장 브라우저(별도 화면)가 떠 있으면 그 밑에 가려지므로 왼쪽 아래로 옮긴다
  box.classList.toggle('left', S.view === 'work' && S.sideTab === 'preview' && nativeOk());
  const h = updCardHtml(); if (h === updShown) return;
  const was = !!updShown; updShown = h; box.innerHTML = h;
  if (h && !was) box.firstElementChild.classList.add('in');
}

// ── 오늘 ──
function todayView() {
  const working = S.st.tasks.filter((t) => t.status === 'working');
  const recent = S.st.tasks.slice(0, 5);
  const d = new Date(); const wd = '일월화수목금토'[d.getDay()];
  // 흔한 노트북 창(1280×800·1366×768)에서도 스크롤 없이 한 화면에: 0건 카드는 숨기고, 폴더·찾기는 최근 작업 머리로
  const found = S.q ? searchResults() : '';
  return `<div class="page"><h2>${d.getMonth() + 1}월 ${d.getDate()}일 ${wd}요일</h2>
  <div class="grid2"><div style="display:flex;flex-direction:column;gap:16px">
   <div class="card"><h4>총괄 비서에게 맡기기<span class="r">필요한 직원을 알아서 불러요</span></h4>${newTaskForm('today')}</div>
   ${myCard()}
   ${working.length ? `<div class="card"><h4>AI가 하는 중<span class="r num">${working.length}건</span></h4>${working.map(taskWl).join('')}</div>` : ''}
  </div><div style="display:flex;flex-direction:column;gap:16px">
   <div class="card"><div class="rhead"><h4>최근 작업</h4><span class="sp"></span><button class="btn sm" data-act="revealroot" data-what="folder" title="맡긴 일의 결과물이 모두 이 폴더에 쌓여요">${ic('folder', 's')}폴더 열기</button><button class="btn sm" data-act="revealroot" data-what="terminal">${ic('term', 's')}터미널 열기</button></div>
    ${searchForm()}${found || recent.map(taskWl).join('') || '<p class="empty">아직 작업이 없어요. 왼쪽에서 첫 일을 맡겨 보세요.</p>'}</div>
  </div></div></div>`;
}
function myCard() {
  const m = S.my; if (!m) return '';
  return `<div class="card"><h4 title="AI가 일할 때 먼저 읽는 나만의 자료예요. 채울수록 결과가 원하는 대로 나와요">내 자료<span class="r num">${m.done}/${m.total} 채움</span></h4>
   <ul class="mylist row1">${m.items.map((x) => `<li class="${x.done ? 'ok' : ''}"><span class="st ${x.done ? 'work' : 'done'}">${x.done ? '채움' : '비어 있음'}</span>${esc(x.name)}</li>`).join('')}</ul>
   <div class="acts"><button class="btn dark" data-act="myinterview">AI와 같이 채우기</button><button class="btn" data-act="myreveal">${ic('folder', 's')}폴더 열기</button></div></div>`;
}
const taskWl = (t) => { const [c, l] = stLabel(t.status); return `<button class="wl" data-act="open" data-id="${t.id}"><span class="st ${c}">${l}</span><div style="min-width:0"><b>${esc(t.title)}</b><small>${rtName(t.runtime)}${t.picked ? ` · ${esc(base(t.cwd))}` : ''} · ${ago(t.updated)}</small></div><span class="sp"></span>${ic('chev')}</button>`; };

// AI 고르기: 로그인된 쪽을 기본으로, 안 된 쪽은 고를 수 없게
function aiChoices() {
  const a = S.st.auth; // null이면 아직 확인 중 → 둘 다 열어 둠
  const ok = (k) => !a || a[k];
  const def = a ? (a.codex ? 'codex' : a.claude ? 'claude' : '') : 'codex';
  return { ok, def, none: a && !a.codex && !a.claude };
}
function newTaskForm(where) {
  const ai = aiChoices(); const pf = S.prefill && S.prefill.where === where ? S.prefill : null;
  const opt = (k) => `<option value="${k}" ${ai.ok(k) ? '' : 'disabled'} ${ai.def === k ? 'selected' : ''}>${rtName(k)}${ai.ok(k) ? '' : ' (로그인 필요)'}</option>`;
  return `<form data-form="newtask" data-where="${where}" style="display:flex;flex-direction:column;gap:8px">
   ${ai.none ? `<div class="warnbox">Claude·Codex 둘 다 로그인이 필요해요. <button type="button" class="linkbtn" data-act="settings" data-tab="ai">AI 로그인 열기</button></div>` : ''}
   <div class="field"><input name="title" placeholder="작업 이름 (예: 4주차 수업 정리 덱)" value="${esc(pf?.title || '')}" required></div>
   ${attStrip('new-' + where)}<div class="field area"><textarea name="text" rows="4" placeholder="총괄 비서에게 평소 말하듯 적어 주세요. 예) 이 메모로 블로그 글이랑 스레드 2편, 카드뉴스 5장 만들어줘 · 모르는 화면은 캡처해서 붙여 넣어도 돼요">${esc(pf?.text || '')}</textarea></div>
   ${dirPicker(where)}
   <div class="ctl"><div class="field" style="min-height:32px"><select name="runtime" aria-label="맡길 AI" data-rtsel>${opt('codex')}${opt('claude')}</select></div><div class="field" style="min-height:32px"><select name="model" aria-label="모델" aria-describedby="mhelp-${where}">${modelOpts(ai.def || 'codex')}</select></div>${attBtn('new-' + where)}<span class="sp"></span><button class="go" ${ai.none ? 'disabled' : ''}>맡기기</button></div>
   <p class="mhelp" id="mhelp-${where}">모델은 맨 위가 기본이에요. 깊이 생각할 일은 위쪽 모델을 골라 새 대화로 맡기세요.</p>
</form>`;
}
// 다른 폴더에서 작업하기(선택): 기본은 허브가 새 폴더를 만든다
function dirPicker(where) {
  const d = S.dir[where] || {};
  const head = `<input type="hidden" name="cwd" value="${esc(d.path || '')}"><button type="button" class="dirbtn ${d.open ? 'on' : ''}" data-act="dirtoggle" data-where="${where}">${ic('folder', 's')}<span class="dk">작업 폴더</span><span class="dv">${d.path ? esc(base(d.path)) : '새 폴더 (기본)'}</span><span class="sp"></span><span class="dp">${d.path ? '' : '다른 폴더에서 하려면 누르기'}</span>${ic('chev', 's dch')}</button>`;
  if (!d.open) return `<div class="dirpick">${head}</div>`;
  return `<div class="dirpick">${head}<div class="dirpanel"><div class="field">${ic('search', 's')}<input data-dirq="${where}" value="${esc(d.q || '')}" placeholder="폴더 이름으로 찾기" autocomplete="off"></div><div class="dirlist" data-dirlist="${where}">${dirListHtml(where)}</div></div></div>`;
}
function dirListHtml(where) {
  const d = S.dir[where] || {}; const list = d.list;
  const def = `<button type="button" class="dirrow ${!d.path ? 'on' : ''}" data-act="dirpick" data-where="${where}" data-path=""><span class="dn">새 폴더 (기본)</span><span class="dp">허브가 이 작업만의 폴더를 만들어요</span></button>`;
  if (!list) return def + '<p class="empty" style="padding:8px 10px">폴더 찾는 중…</p>';
  return def + (list.map((x) => `<button type="button" class="dirrow ${d.path === x.path ? 'on' : ''}" data-act="dirpick" data-where="${where}" data-path="${esc(x.path)}"><span class="dn">${esc(x.name)}</span><span class="dp">${esc(x.home).replace(/([\\/])/g, '$1<wbr>')}</span></button>`).join('') || '<p class="empty" style="padding:8px 10px">맞는 폴더가 없어요.</p>');
}
let dirTimer;
async function loadDirs(where, q) { const d = (S.dir[where] = S.dir[where] || {}); d.q = q; try { d.list = await api(`/api/dirs?q=${encodeURIComponent(q || '')}`); } catch { d.list = []; } const el = document.querySelector(`[data-dirlist="${where}"]`); if (el) el.innerHTML = dirListHtml(where); }
const searchForm = () => `<form data-form="search" class="sform"><div class="field">${ic('search', 's')}<input name="q" value="${esc(S.q)}" placeholder="작업 찾기 · 이름·파일·대화 내용" aria-label="작업 찾기"></div></form>`;
function searchResults() { return searchBox().replace(/^<form[\s\S]*?<\/form>\s*/, ''); }
function searchBox() {
  return `<form data-form="search"><div class="field">${ic('search', 's')}<input name="q" value="${esc(S.q)}" placeholder="작업 이름·파일 이름·대화 내용"></div></form>
  <div style="margin-top:8px">${S.res.map((r) => `<button class="row" data-act="open" data-id="${esc(r.id || '')}"><span class="st done">${esc(r.kind === '태스크' ? '작업' : r.kind)}</span><div style="min-width:0"><div class="t">${esc(r.title)}</div><div class="m">${esc(r.sub || '')}</div></div></button>`).join('')}${S.q && !S.res.length ? '<p class="empty">찾은 게 없어요.</p>' : ''}</div>`;
}

// ── 내 작업 ──
function weekKey(iso) { const d = new Date(iso || 0); const now = new Date(); const day = (x) => Math.floor((x - new Date(x.getFullYear(), 0, 1)) / 864e5); const diff = Math.floor((now - d) / 864e5); if (diff < 1 && now.getDate() === d.getDate()) return '오늘'; if (diff < 7) return '이번 주'; if (diff < 14) return '지난주'; return `${d.getMonth() + 1}월`; }
function workView() {
  const list = S.st.tasks;
  // 날짜순(기본) 또는 폴더별: 실제 프로젝트 폴더에서 한 일은 폴더 이름으로, 허브가 만든 새 폴더는 한 묶음으로
  const keyOf = (t) => t.status === 'working' ? 'AI가 하는 중' : S.byFolder ? (t.picked ? (base(t.cwd) === 'my' && /AISchoolHub[\\/]my$/.test(t.cwd) ? '내 자료 폴더' : base(t.cwd)) : '허브가 만든 새 폴더') : weekKey(t.updated);
  const groups = []; for (const t of list) { const k = keyOf(t); let g = groups.find((x) => x.k === k); if (!g) groups.push((g = { k, items: [] })); g.items.push(t); }
  groups.sort((a, b) => (a.k === 'AI가 하는 중' ? -1 : b.k === 'AI가 하는 중' ? 1 : S.byFolder ? (a.k === '허브가 만든 새 폴더') - (b.k === '허브가 만든 새 폴더') : 0));
  const row = (t) => `<button class="row ${(S.split ? S.splitIds.includes(t.id) : t.id === S.taskId) ? 'on' : ''}" data-act="open" data-id="${t.id}"><span class="dot ${t.status === 'working' ? 'work' : t.status === 'error' ? 'err' : 'idle'}" style="margin-top:8px"></span><div style="min-width:0"><div class="t">${esc(t.title)}</div><div class="m">${rtName(t.runtime)} · ${ago(t.updated)}${t.mark ? ` · <span class="mk ${t.mark.mark}">${MARKS[t.mark.mark]}</span>` : ''}</div></div></button>`;
  const rail = `<div class="rail"><div class="lbl" style="display:flex;align-items:center">내 작업<span class="sp" style="flex:1"></span><button class="btn ${S.split ? 'dark' : ''}" data-act="split" title="대화 여러 개를 한 화면에 나란히 봐요">${ic('layers', 's')}${S.split ? '나란히 보기 끄기' : '나란히 보기'}</button></div>${S.split ? '<p class="crumb" style="margin:-4px 0 0">작업을 누르면 오른쪽 칸에 들어가요. 최대 4개까지요.</p>' : ''}${searchBox()}
   <details ${list.length ? '' : 'open'}><summary class="lbl" style="cursor:pointer">${ic('plus', 's')}새 작업</summary>${newTaskForm('work')}</details>
   ${list.length ? `<div class="seg2" role="group" aria-label="목록 보기"><button class="${S.byFolder ? '' : 'on'}" data-act="byfolder" data-v="0" aria-pressed="${!S.byFolder}">날짜순</button><button class="${S.byFolder ? 'on' : ''}" data-act="byfolder" data-v="1" aria-pressed="${!!S.byFolder}">폴더별</button></div>` : ''}
   ${groups.map((g) => `<div><div class="lbl">${S.byFolder && g.k !== 'AI가 하는 중' ? ic('folder', 's') : ''}${esc(g.k)} <span class="num" style="font-weight:400">${g.items.length}</span></div>${g.items.map(row).join('')}</div>`).join('')}
   ${!list.length ? '<p class="empty">아직 작업이 없어요. 위 새 작업에서 맡겨 보세요.</p>' : ''}</div>`;
  if (S.split) return `<div class="body split" data-pane="${S.pane === 'list' ? 'list' : 'chat'}">${rail}${splitHtml()}</div>`;
  return `<div class="body ${S.wide ? 'wide' : ''}" data-pane="${S.pane}" style="${S.sideW ? `--side-w:${S.sideW}px` : ''}">${rail}${S.task ? taskMain() + `<div class="resizer" data-drag="side" title="끌어서 미리보기 폭 바꾸기"></div>` + sidePanel() : `<div class="mainc"><div class="page" style="background:var(--card)"><p class="empty">왼쪽에서 작업을 고르거나 새로 맡기세요.</p></div></div>`}</div>`;
}
// 나란히 보기: 대화 2~4개를 칸으로 나눠 보고 칸마다 바로 보낸다
function splitHtml() {
  const ids = S.splitIds;
  const pane = (id) => {
    const t = S.splitTasks[id]; if (!t) { if (!(S.splitLoading ||= new Set()).has(id)) { S.splitLoading.add(id); loadSplit(id).then(() => { S.splitLoading.delete(id); render(); }); } return `<div class="spl"><p class="empty" style="padding:16px">불러오는 중…</p></div>`; }
    const busy = t.status === 'working';
    return `<div class="spl" data-id="${id}"><div class="th"><button class="btn mob-only" data-act="pane" data-p="list" aria-label="목록으로">${ic('back', 's')}</button><span class="dot ${busy ? 'work' : t.status === 'error' ? 'err' : 'idle'}"></span><h3 title="${esc(t.title)}">${esc(t.title)}</h3>${rtChip(t)}${ctxChip(t)}${busy ? '<span class="st work">AI가 일하는 중</span>' : ''}<span class="sp"></span><button class="btn" data-act="splone" data-id="${id}" title="이 대화만 크게 보기">${ic('eye', 's')}</button><button class="btn" data-act="splx" data-id="${id}" title="이 칸 닫기" aria-label="이 칸 닫기">×</button></div>
     <div class="chat" data-chat="${id}">${chatHtml(t) || '<p class="empty">아직 대화가 없어요.</p>'}${busy ? '<div class="typing">AI가 일하는 중이에요…</div>' : ''}</div>
     <div class="comp"><form class="box" data-form="psend" data-id="${id}">${attStrip('p-' + id)}<textarea name="text" aria-label="메시지" placeholder="이어서 할 말 · Enter로 보내기" ${busy ? 'disabled' : ''}></textarea><div class="ctl">${busy ? '' : attBtn('p-' + id)}<span class="sp"></span>${busy ? `<button type="button" class="btn" data-act="pstop" data-id="${id}">${ic('stop', 's')}멈추기</button>` : `<button class="send" aria-label="보내기">${ic('up')}</button>`}</div></form></div></div>`;
  };
  const slots = ids.map(pane);
  if (ids.length < 2) slots.push(`<div class="spl slot"><p class="empty">왼쪽 목록에서 작업을 누르면<br>이 칸에 들어와요.</p></div>`);
  return `<div class="splitgrid" data-n="${slots.length}">${slots.join('')}</div>`;
}
async function loadSplit(id) { try { S.splitTasks[id] = await api(`/api/tasks/${id}`); } catch { S.splitIds = S.splitIds.filter((x) => x !== id); delete S.splitTasks[id]; saveSplit(); } }
async function addSplit(id) {
  if (!S.splitIds.includes(id)) { if (S.splitIds.length >= 4) S.splitIds.pop(); S.splitIds.push(id); saveSplit(); }
  await loadSplit(id); S.pane = 'chat'; render();
}
async function toggleSplit() {
  S.split = !S.split;
  if (S.split) {
    const known = new Set(S.st.tasks.map((t) => t.id)); S.splitIds = S.splitIds.filter((x) => known.has(x));
    if (S.taskId && !S.splitIds.includes(S.taskId)) S.splitIds.unshift(S.taskId);
    for (const t of S.st.tasks) { if (S.splitIds.length >= 2) break; if (!S.splitIds.includes(t.id)) S.splitIds.push(t.id); }
    S.splitIds = S.splitIds.slice(0, 4);
    await Promise.all(S.splitIds.map(loadSplit));
  }
  saveSplit(); S.view = 'work'; S.pane = 'chat'; render();
}
// 대화: 이어진 '실행' 줄은 접어서 "작업 과정 N단계"로, 스킬 사용·파일은 한 줄씩 보이게
function chatHtml(t) {
  const out = []; let steps = [];
  const flush = () => { if (!steps.length) return; out.push(`<details class="steps"><summary>작업 과정 ${steps.length}단계</summary>${steps.map((m) => `<div class="log">${esc(m.text)}</div>`).join('')}</details>`); steps = []; };
  for (const m of t.messages) {
    const isStep = m.role === 'log' && m.kind !== 'skill' && m.kind !== 'file' && !/^(파일|스킬 사용) ·/.test(m.text);
    if (isStep) { steps.push(m); continue; }
    flush();
    if (m.role === 'me') out.push(`<div class="u ${m.sys ? 'sys' : ''}">${(m.images || []).length ? `<div class="uimgs">${m.images.map((n, i) => `<button type="button" class="uimg" data-act="imgview" data-task="${t.id}" data-src="/api/tasks/${t.id}/img/${encodeURIComponent(n)}" aria-label="보낸 사진 ${i + 1} 크게 보기"><img src="/api/tasks/${t.id}/img/${encodeURIComponent(n)}" alt=""></button>`).join('')}</div>` : ''}${esc(m.text)}</div>`);
    else if (m.role === 'ai') out.push(`<div class="a">${md(m.text)}</div>`);
    else if (m.role === 'warn') out.push(`<div class="warnbox" role="alert">${esc(m.text)}${m.kind === 'login' || m.kind === 'missing' ? ` <button class="linkbtn" data-act="settings" data-tab="ai">AI 로그인 열기</button>` : ''}${m.detail ? `<details class="why"><summary>자세히</summary><div>${esc(m.detail)}</div></details>` : ''}</div>`);
    else if (m.kind === 'skill' || /^스킬 사용 ·/.test(m.text)) out.push(`<div class="log skill">${ic('users', 's')}${esc(m.text)}</div>`);
    else out.push(`<div class="log">${ic('file', 's')}${esc(m.text)}</div>`);
  }
  flush();
  return out.join('');
}
const MARKS = { good: '잘 됐어요', redo: '다시 해야 해요' };
function markBar(t) {
  if (t.status === 'working' || !t.messages.some((m) => m.role === 'ai')) return '';
  if (t.mark && !S.markEdit) return `<div class="markbar done"><span class="st ${t.mark.mark === 'good' ? 'work' : 'wait'}">${MARKS[t.mark.mark]}</span>${t.mark.note ? `<span class="mnote">${esc(t.mark.note)}</span>` : ''}<span class="sp"></span><button class="linkbtn" data-act="markedit">바꾸기</button></div>`;
  return `<form class="markbar" data-form="mark"><span class="mq">이번 결과 어땠어요?</span><button type="submit" class="btn sm" name="mark" value="good">잘 됐어요</button><button type="submit" class="btn sm" name="mark" value="redo">다시 해야 해요</button><div class="field mfield"><input name="note" maxlength="200" placeholder="한 줄 메모 (선택) · 무엇이 좋았나, 무엇이 아쉬웠나" aria-label="한 줄 메모" value="${esc(t.mark?.note || '')}"></div></form>`;
}
function taskMain() {
  const t = S.task; const busy = t.status === 'working'; const pct = ctxPct(t);
  const band = pct != null && pct >= 50 && !t.continuedTo && !t.ctxDismissed && !busy ? `<div class="ctxband"><div><b>대화가 길어졌어요.</b> 더 길어지면 앞 내용을 흐리게 기억해요. 새 대화로 이어가면 지금 AI가 정리 카드를 쓰고, 같은 폴더의 새 대화가 그 카드부터 시작해요.</div><div class="acts" style="margin:0"><button class="btn dark" data-act="ctxgo">새 대화로 이어가기</button><button class="btn" data-act="ctxno">나중에</button></div></div>`
    : t.continuedTo ? `<div class="ctxband done"><div>이 대화는 새 대화로 이어졌어요.</div><button class="btn" data-act="open" data-id="${t.continuedTo}">이어진 대화 열기</button></div>` : '';
  return `<div class="mainc"><div class="th"><button class="btn mob-only" data-act="pane" data-p="list" aria-label="목록으로">${ic('back', 's')}</button><span class="dot ${busy ? 'work' : 'idle'}"></span><h3>${esc(t.title)}</h3>${rtChip(t)}${ctxChip(t)}<span class="sp"></span>
   <button class="btn" data-act="reveal" data-what="folder" title="${esc(t.cwd)}">${ic('folder', 's')}폴더 열기</button><button class="btn" data-act="reveal" data-what="terminal" title="터미널 열기" aria-label="터미널 열기">${ic('term', 's')}터미널 열기</button>
   <button class="btn mob-only" data-act="pane" data-p="side" aria-label="미리보기">${ic('eye', 's')}</button></div>${band}
   <div class="chat" id="chat">${chatHtml(t) || '<p class="empty">아래에 맡길 일을 적어 주세요. 허브에 있는 AI 직원(스킬)을 AI가 알아서 불러 써요.</p>'}${busy ? '<div class="typing">AI가 일하는 중이에요…</div>' : ''}</div>
   ${markBar(t)}
   <div class="comp"><form class="box" data-form="send">${attStrip('send-' + t.id)}<textarea name="text" aria-label="메시지" placeholder="이어서 할 말 · Enter로 보내기, Shift+Enter 줄바꿈 · 캡처는 붙여 넣기" ${busy ? 'disabled' : ''}></textarea>
   <div class="ctl">${busy ? '' : attBtn('send-' + t.id)}<span class="crumb">${t.picked ? esc(base(t.cwd)) + ' 폴더에서 작업' : ''}</span><span class="sp"></span>${busy ? `<button type="button" class="btn" data-act="stop">${ic('stop', 's')}멈추기</button>` : `<button class="send" aria-label="보내기">${ic('up')}</button>`}</div></form></div></div>`;
}
function sidePanel() {
  const t = S.task; let pane = '';
  const isFile = S.previewSrc.startsWith('/files/');
  const bar = `<form class="urlbar" data-form="url">${nativeOk() ? `<button type="button" class="btn" data-act="nav" data-go="back" aria-label="뒤로">${ic('back', 's')}</button><button type="button" class="btn" data-act="nav" data-go="reload" aria-label="새로고침">${ic('refresh', 's')}</button>` : ''}<input name="u" value="${esc(isFile ? decodeURIComponent(S.previewSrc.split('/').slice(3).join('/')) : S.previewSrc)}" placeholder="결과물 파일 이름 또는 웹 주소" aria-label="주소"><button class="btn">열기</button><button type="button" class="btn" data-act="wide" aria-label="크게 보기">${ic(S.wide ? 'shrink' : 'expand', 's')}${S.wide ? '작게' : '크게'}</button></form>`;
  if (S.sideTab === 'preview') {
    if (nativeOk()) pane = bar + `<div id="native-slot" style="flex:1;min-height:300px;background:#fff"></div>`;
    else if (S.mdText != null) pane = bar + `<div class="mdview">${md(S.mdText)}</div>`;
    else if (/\/img\/|\.(png|jpe?g|gif|webp)$/i.test(S.previewSrc.split('?')[0])) pane = bar + `<div class="imgfit"><img src="${esc(S.previewSrc)}" alt="미리보기 사진"></div>`; // 사진은 칸에 맞춰 보여 준다
    else pane = bar + (S.previewSrc ? `<iframe class="preview" src="${esc(S.previewSrc)}"></iframe>` : '<p class="empty" style="padding:16px">AI가 HTML·이미지·문서를 만들면 여기 바로 떠요.</p>');
  } else if (S.sideTab === 'files') pane = `<div class="acts" style="padding:10px 16px;margin:0"><button class="btn" data-act="reveal" data-what="folder">${ic('folder', 's')}폴더 열기</button></div>` + (S.files.map((f) => `<button class="file" data-act="preview" data-name="${esc(f.name)}"><span class="fi">${ic('file')}</span><div><b>${esc(f.name)}</b><small>${Math.max(1, Math.round(f.size / 1024))}KB · ${ago(f.mtime)}</small></div></button>`).join('') || '<p class="empty" style="padding:16px">아직 결과물이 없어요.</p>');
  else pane = `<div style="padding:16px;display:flex;flex-direction:column;gap:12px"><div class="card"><h4>이 작업</h4><p class="md">작업 폴더: ${esc(base(t.cwd))}\n만든 때: ${new Date(t.created).toLocaleString('ko-KR')}\n맡긴 AI: ${rtName(t.runtime)}${(t.skillsUsed || []).length ? `\n쓴 스킬: ${esc(t.skillsUsed.join(', '))}` : ''}</p>
   <div class="acts"><button class="btn" data-act="reveal" data-what="folder">${ic('folder', 's')}폴더 열기</button><button class="btn" data-act="reveal" data-what="terminal">${ic('term', 's')}터미널 열기</button><button class="btn" data-act="rename">이름 바꾸기</button><button class="btn" data-act="delete">작업 지우기</button></div>
   <p class="crumb" style="margin-top:8px">작업 지우기는 목록에서만 지워요. 폴더의 결과물은 그대로 남아요.</p></div></div>`;
  return `<div class="side"><div class="stabs"><button class="mob-only" data-act="pane" data-p="chat" aria-label="대화로">${ic('back', 's')}</button><button class="${S.sideTab === 'preview' ? 'on' : ''}" data-act="stab" data-t="preview">미리보기</button><button class="${S.sideTab === 'files' ? 'on' : ''}" data-act="stab" data-t="files">결과물 ${S.files.length}</button><button class="${S.sideTab === 'card' ? 'on' : ''}" data-act="stab" data-t="card">정보</button></div><div class="spane">${pane}</div></div>`;
}

// ── AI 직원 ──
function staffView() {
  const st = S.staff; if (!st) return '<div class="page"><p class="empty">불러오는 중…</p></div>';
  const card = (s) => `<div class="card staff"><h4>${esc(s.name)}</h4><p>${esc(s.role)}</p>${s.example ? `<p class="q">이렇게 말해 보세요 · “${esc(s.example)}”</p>` : ''}${s.needs || (s.with || []).length ? `<details class="more"><summary>자세히</summary>${s.needs ? `<p class="crumb">필요한 것: ${esc(s.needs)}</p>` : ''}${(s.with || []).length ? `<p class="crumb">함께 쓰는 스킬: ${esc(s.with.join(', '))}</p>` : ''}</details>` : ''}<div class="acts"><button class="btn" data-act="hire" data-name="${esc(s.name)}">이 직원에게 맡기기</button></div></div>`;
  const chief = (st.staff || []).find((s) => s.chief);
  const main = (st.staff || []).filter((s) => !s.helper && !s.chief); const helpers = (st.staff || []).filter((s) => s.helper);
  const teams = [...new Set(main.map((s) => s.team || ''))];
  // 유입·전환 두 묶음(2026-11-25 동규대표 미팅 결정). 묶음 안은 처음 쓰는 대표님에게 권하는 순서대로 번호를 붙인다.
  const stages = (st.stages || []).filter((g) => main.some((s) => s.stage === g.id));
  const numCard = (s) => card(s).replace('<div class="card staff"><h4>', `<div class="card staff"><h4><span class="ord num">${s.order}</span>`).replace('</h4>', `<span class="r">${esc(s.team || '')}</span></h4>`);
  const stageHtml = (g) => { const L = main.filter((s) => s.stage === g.id).sort((a, b) => a.order - b.order); return `<div class="stagehead ${g.id === 'support' ? 'sub' : ''}"><h3>${esc(g.label)} <span class="num">${L.length}명</span></h3><p>${esc(g.desc)}</p></div><div class="staffgrid">${L.map(numCard).join('')}</div>`; };
  return `<div class="page"><h2>AI 직원 ${main.length}명</h2><p class="lead">허브에 들어 있는 AI 직원이에요. 일을 맡기면 AI가 알맞은 직원을 알아서 불러요. 직원 이름을 직접 말해도 돼요. 쓰면서 내 일에 맞게 고쳐 가면 내 직원이 돼요.</p>
  ${chief ? `<div class="card chief"><h4>${esc(chief.name)}<span class="r">총괄</span></h4><p>${esc(chief.role)}</p><p class="q">이렇게 말해 보세요 · “${esc(chief.example)}”</p><div class="acts"><button class="btn pri" data-act="hire" data-name="${esc(chief.name)}">총괄 비서에게 맡기기</button></div></div>` : ''}
  ${stages.length ? stages.map(stageHtml).join('') : teams.map((tm) => `<div class="teamhead">${esc(tm)}</div><div class="staffgrid">${main.filter((s) => (s.team || '') === tm).map(card).join('')}</div>`).join('') || '<p class="empty">직원 목록을 못 읽었어요.</p>'}
  <div class="stagehead sub"><div class="rhead"><h3>내 직원 <span class="num">${(st.mine || []).length}명</span></h3><span class="sp"></span><button class="btn pri" data-act="makestaff">${ic('plus', 's')}직원 만들기</button></div><p>내 일에 맞는 직원을 AI와 대화로 만들어요. 만든 직원은 여기에 뜨고 바로 부를 수 있어요.</p></div>
  ${(st.mine || []).length ? `<div class="staffgrid">${st.mine.map(card).join('')}</div>` : '<p class="empty" style="padding:4px 0 8px">아직 만든 직원이 없어요.</p>'}
  ${helpers.length ? `<details class="card" style="margin-top:16px"><summary><b>뒤에서 돕는 직원 ${helpers.length}명</b> <span class="crumb">직접 부를 일은 적고, AI가 만들고 점검할 때 알아서 써요</span></summary><div class="staffgrid" style="margin-top:12px">${helpers.map(card).join('')}</div></details>` : ''}
  ${(S.oss || []).length ? `<details class="card" style="margin-top:16px"><summary><b>같이 쓰면 좋은 오픈소스 ${S.oss.length}개</b> <span class="crumb">대표가 실제로 써 온 무료 도구예요. AI에게 말하면 확인을 받고 깔아서 써요</span></summary><div class="staffgrid" style="margin-top:12px">${S.oss.map((o) => `<div class="card staff"><h4>${esc(o.name)}<span class="r">${esc(o.area || '')}</span></h4><p>${esc(o.what || '')}</p>${o.license ? `<p class="crumb">라이선스: ${esc(o.license)}${o.note ? ' · ' + esc(o.note) : ''}</p>` : ''}<div class="acts">${o.say ? `<button class="btn" data-act="osshire" data-name="${esc(o.name)}">이걸로 맡기기</button>` : ''}${o.url ? `<a class="btn" href="#" data-act="openurl" data-url="${esc(o.url)}">사이트</a>` : ''}</div></div>`).join('')}</div></details>` : ''}</div>`;
}

// ── 설정 ──
function settingsView() {
  const tabs = [['me', '내 정보'], ['ai', 'AI 로그인'], ['conn', '연결'], ['skills', '내 PC 스킬'], ['rules', '규칙'], ['learn', '자동 점검']];
  const nav = `<div class="nav">${tabs.map(([k, n]) => `<button class="ni ${S.setTab === k ? 'on' : ''}" data-act="settab" data-tab="${k}">${n}${k === 'learn' && S.st.pending ? `<span class="c num">${S.st.pending}</span>` : ''}</button>`).join('')}</div>`;
  let page = '';
  const back = `<button class="btn mob-only" data-act="pane" data-p="nav" style="margin-bottom:12px">${ic('back', 's')}설정</button>`;
  if (S.setTab === 'me') page = `<h2>내 정보</h2><p class="lead">허브 화면에 보이는 이름이에요. 이 PC 밖으로 나가지 않아요.</p><form data-form="me" class="card" style="max-width:480px;display:flex;flex-direction:column;gap:10px"><div class="field"><input name="me" value="${esc(S.st.me)}" placeholder="이름" aria-label="이름"></div><button class="btn dark" style="align-self:flex-start">저장</button></form><div class="card" style="max-width:480px;margin-top:12px"><h4>허브 안내</h4><p class="md">처음 열었을 때 나온 안내를 다시 봐요.</p><div class="acts"><button class="btn" data-act="introshow">안내 다시 보기</button></div></div>`;
  if (S.setTab === 'ai') page = `<h2>AI 로그인</h2><p class="lead">허브는 내 구독으로 일해요. 둘 중 하나만 로그인돼 있어도 돼요. 로그인을 누르면 브라우저에 로그인 창이 열리고, 마치면 여기가 자동으로 바뀌어요.</p>${S.auth ? [['codex', 'Codex (ChatGPT 구독)'], ['claude', 'Claude (Claude 구독)']].map(([w, n]) => { const a = S.auth[w] || {}; const L = S.login[w]; const busy = L && ['opening', 'waiting', 'checking'].includes(L.state); return `<div class="card" style="max-width:640px;margin-bottom:12px"><h4>${n}<span class="r"><span class="st ${a.ok ? 'work' : 'wait'}">${a.ok ? '로그인됨' : busy ? '로그인하는 중' : a.installed ? '로그인 필요' : '프로그램 없음'}</span></span></h4><p class="md">${esc(a.text || '')}</p>${busy ? '' : `<div class="acts">${a.installed ? `<button class="btn ${a.ok ? '' : 'pri'}" data-act="authlogin" data-who="${w}">${a.ok ? '다시 로그인' : '로그인'}</button>${a.ok ? `<button class="btn" data-act="authlogout" data-who="${w}">로그아웃</button>` : ''}` : '<span class="crumb">강사에게 설치를 부탁하세요. 설치한 뒤 아래 다시 확인을 누르면 로그인 버튼이 나와요.</span>'}</div>`}${loginBox(w, L)}</div>`; }).join('') + `<button class="btn" data-act="authrefresh">${ic('refresh', 's')}다시 확인</button>` + pcCard(S.auth.pc) : '<p class="empty">확인하는 중…</p>'}`;
  if (S.setTab === 'conn') page = connPage();
  if (S.setTab === 'skills') page = skillsPage();
  if (S.setTab === 'rules') page = rulesPage();
  if (S.setTab === 'learn') page = learnPage();
  return `<div class="body" data-pane="${S.pane === 'page' ? 'page' : 'nav'}">${nav}<div class="page">${back}${page}</div></div>`;
}
function connPage() {
  const c = S.conns; if (!c) return '<h2>연결</h2><p class="empty">불러오는 중…</p>';
  const card = (x) => { const ks = x.keys || []; const ok = ks.length && ks.every((k) => k.has);
    return `<div class="card conn" style="max-width:720px;margin-bottom:12px"><h4>${esc(x.name)}<span class="r">${ks.length ? `<span class="st ${ok ? 'work' : 'wait'}">${ok ? '연결됨' : '연결 전'}</span>` : '<span class="st done">키 필요 없음</span>'}</span></h4>
    <p>${esc(x.what)} <span class="crumb">· ${esc(x.staff)}</span></p>
    ${(x.steps || []).length ? `<details class="more"><summary>키 받는 순서 보기</summary><ol class="steps">${x.steps.map((t) => `<li>${esc(t)}</li>`).join('')}</ol></details>` : ''}
    ${ks.map((k) => `<form class="keyrow" data-form="key"><input type="hidden" name="name" value="${esc(k.name)}"><label>${esc(k.label)}</label><div class="field"><input type="password" name="value" autocomplete="off" placeholder="${k.has ? '저장돼 있어요 · 바꾸려면 새로 붙여 넣기' : '여기에 붙여 넣기'}"></div><button class="btn">저장</button>${k.has ? `<button type="button" class="btn" data-act="keydel" data-name="${esc(k.name)}">지우기</button>` : ''}</form>`).join('')}
    <div class="acts">${ks.length ? `<button class="btn pri" data-act="connhelp" data-id="${esc(x.id)}">AI에게 연결 도와 달라</button>` : ''}<a class="btn" href="#" data-act="openurl" data-url="${esc(x.doc)}">공식 안내</a></div></div>`; };
  return `<h2>연결</h2><p class="lead">AI 직원이 바깥 서비스에 올리고 보내려면 내 계정의 키가 필요해요. 흐름은 다 들어 있고 키만 비어 있어요. 키는 이 PC 금고에만 저장되고 대화·파일에 남지 않아요.</p>${c.connections.map(card).join('')}`;
}
// 로그인 진행 칸: 여는 중 → 브라우저에서 로그인(또는 코드 입력) → 자동으로 '로그인됨'
// 서버가 알고 있는 로그인 진행 상태를 화면에 맞춘다(화면을 다시 열어도 코드·버튼이 그대로 보이게)
function syncLogin() { for (const w of ['codex', 'claude']) { const v = S.auth?.login?.[w]; if (v) S.login[w] = v; else if (S.login[w] && S.login[w].state !== 'opening' && S.login[w].state !== 'failed') S.login[w] = null; } }
function loginBox(w, L) {
  if (!L) return '';
  const box = (inner) => `<div style="margin-top:12px;padding-top:12px;border-top:1px solid var(--line)">${inner}</div>`;
  const stop = `<button class="btn" data-act="authcancel" data-who="${w}">그만두기</button>`;
  if (L.state === 'opening') return box(`<p class="md">로그인 창을 여는 중이에요. 잠시만 기다려 주세요. 처음에는 조금 오래 걸릴 수 있어요.</p><div class="acts">${stop}</div>`);
  if (L.state === 'checking') return box('<p class="md">코드를 확인하는 중이에요.</p>');
  if (L.state === 'failed') return box(`<p class="md">${esc(L.note || '로그인이 끝나지 않았어요. 다시 눌러 주세요.')}</p>${w === 'codex' ? `<div class="acts"><button class="btn" data-act="authdevice" data-who="codex">코드로 로그인</button></div>` : ''}`);
  if (L.state !== 'waiting') return '';
  if (L.mode === 'device') return box(`<p class="md">브라우저에 열린 화면에서 ChatGPT 계정으로 로그인한 뒤, 아래 코드를 입력하세요. 15분 안에 마치면 여기가 자동으로 로그인됨으로 바뀌어요.</p>
    <div style="font-size:30px;font-weight:600;letter-spacing:3px;font-family:ui-monospace,Menlo,Consolas,monospace;color:var(--ink);margin:12px 0;user-select:all">${esc(L.code)}</div>
    <div class="acts"><button class="btn pri" data-act="authcopy" data-who="${w}" data-what="code">코드 복사</button><button class="btn" data-act="authopen" data-who="${w}">코드 입력 화면 열기</button><button class="btn" data-act="authcopy" data-who="${w}" data-what="url">주소 복사</button>${stop}</div>`);
  return box(`<p class="md">브라우저에 로그인 창을 열었어요. 로그인을 마치면 여기가 자동으로 로그인됨으로 바뀌어요.</p>
    <div class="acts"><button class="btn" data-act="authopen" data-who="${w}">로그인 창 다시 열기</button><button class="btn" data-act="authcopy" data-who="${w}" data-what="url">로그인 주소 복사</button>${w === 'codex' ? `<button class="btn" data-act="authdevice" data-who="codex">코드로 로그인</button>` : ''}${stop}</div>
    ${w === 'codex' ? '<p class="crumb" style="margin-top:8px">창이 안 열리거나 로그인 뒤 오류 화면이 나오면 코드로 로그인을 눌러 보세요.</p>' : `<p class="md" style="margin-top:12px">브라우저에 긴 코드가 나오면 복사해서 여기에 붙여 넣으세요.</p><form data-form="authcode" data-who="claude" style="display:flex;gap:6px;margin-top:6px"><div class="field" style="flex:1"><input name="code" autocomplete="off" placeholder="코드 붙여 넣기" aria-label="로그인 코드"></div><button class="btn dark">확인</button></form>`}`);
}
function pcCard(pc) {
  if (!pc) return '';
  const row = (name, x) => { const st = x.how === 'none' ? ['wait', '설치 안 됨'] : x.how === 'cmd' ? ['wait', '우회 실행'] : ['work', '직접 실행']; return `<tr><td>${name}</td><td><span class="st ${st[0]}">${st[1]}</span></td><td style="word-break:break-all;color:var(--ink3)">${esc(x.path || '-')}</td></tr>`; };
  return `<details class="card" style="max-width:640px;margin-top:16px"><summary><b>이 PC 점검</b> <span class="crumb">강사 확인용</span></summary><p class="md" style="margin-top:8px">사용자 폴더: ${esc(pc.home)}${pc.oddHome ? ' (띄어쓰기·한글 있음 → AI를 직접 실행하도록 맞춤)' : ''}</p>
   <table class="t" style="margin-top:8px"><tbody>${row('Claude', pc.claude)}${row('Codex', pc.codex)}</tbody></table></details>`;
}
function skillsPage() {
  const sc = S.scan;
  let scanHtml = '';
  if (S.scanBusy) scanHtml = '<p class="empty">이 PC의 스킬을 찾는 중…</p>';
  else if (sc) {
    const fresh = sc.filter((r) => !r.registered);
    scanHtml = `<form data-form="register"><div class="card" style="margin-top:12px"><h4>이 PC에서 찾은 스킬<span class="r num">새 스킬 ${fresh.length}개</span></h4>
    ${sc.map((r) => { const bad = r.secrets > 0; return `<label class="skrow ${bad ? 'bad' : ''}"><input type="checkbox" name="n" value="${esc(r.name)}" ${bad ? 'disabled' : ''}><div><b>${esc(r.desc || r.name)}</b><small>${esc(r.name)} · ${r.registered ? '허브에 있음' : '새 스킬'}${bad ? ' · 키 같은 글자가 있어 넣을 수 없어요' : ''}</small></div></label>`; }).join('') || '<p class="empty">찾은 스킬이 없어요.</p>'}
    <div class="acts" style="align-items:center"><span class="md">고른 스킬은 이 PC의 허브에만 들어가요.</span><span class="sp"></span><button class="btn dark">고른 스킬 허브에 넣기</button></div></div></form>`;
  }
  return `<h2>내 PC 스킬</h2><p class="lead">허브에 기본으로 든 AI 직원은 위 AI 직원 탭에 있어요. 내 PC에 따로 만들어 둔 스킬이 있으면 찾아서 허브에 넣을 수 있어요.</p>
  <div class="acts" style="margin:0 0 4px"><button class="btn pri" data-act="scan">${ic('search', 's')}내 PC 스킬 찾기</button></div>${scanHtml}`;
}
function rulesPage() {
  const r = S.rules; if (!r) return '<h2>규칙</h2><p class="empty">불러오는 중…</p>';
  const mine = String(r.personal || '').split('\n').filter((l) => /^\s*-\s+/.test(l)).map((l) => l.replace(/^\s*-\s+/, '').replace(/\s*\(\d{4}-\d{2}-\d{2}, 근거:.*\)\s*$/, ''));
  return `<h2>규칙</h2><p class="lead">AI가 일을 시작할 때마다 읽는 약속이에요. 내 규칙은 대화하면서 "앞으로 이렇게 해 줘"라고 말하고, 자동 점검에서 골라 쌓아요.</p>
  <div class="card"><h4>내 규칙<span class="r num">${mine.length}줄</span></h4>${mine.length ? `<ol class="rules">${mine.map((x) => `<li>${esc(x)}</li>`).join('')}</ol>` : '<p class="empty">아직 없어요. 자동 점검에서 고르면 여기에 쌓여요.</p>'}</div>
  <details class="card" style="margin-top:12px"><summary><b>허브 기본 규칙</b> <span class="crumb">모든 수강생 공통</span></summary><div class="mdview" style="padding:8px 0 0">${md(r.text)}</div></details>`;
}
function learnPage() {
  const on = S.st.learnConsent;
  return `<h2>자동 점검</h2><p class="lead">이 PC에서 AI와 나눈 대화를 훑어, 규칙이 될 만한 말을 후보로 보여 줘요. 대화 원문은 이 PC 밖으로 나가지 않아요.</p>
  <div class="card" style="max-width:640px"><label class="toggle"><input type="checkbox" data-act="consent" ${on ? 'checked' : ''}>내 대화 기록 점검에 동의해요 (언제든 끌 수 있어요)</label>
  <div class="acts"><button class="btn pri" data-act="learnscan" ${!on || S.learnBusy ? 'disabled' : ''}>${ic('spark', 's')}${S.learnBusy ? '점검 중…' : '지금 점검 (최근 7일)'}</button></div></div>
  <div style="margin-top:16px">${S.pending.map((c) => `<div class="cand"><div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><span class="st done">${c.kind === 'skill' ? '스킬' : '규칙'}</span><b>${esc(c.title)}</b></div>
   <p style="margin-top:6px">${esc(c.text)}</p>${(c.evidence || []).length ? `<details class="more"><summary>내가 한 말 ${c.evidence.length}개 보기</summary>${c.evidence.map((e) => `<p class="q">“${esc(e)}”</p>`).join('')}</details>` : ''}
   <div class="acts"><button class="btn dark" data-act="decide" data-id="${c.id}" data-c="personal">${c.kind === 'skill' ? '내 스킬로 넣기' : '내 규칙으로 넣기'}</button><button class="btn" data-act="decide" data-id="${c.id}" data-c="discard">버리기</button></div></div>`).join('') || '<p class="empty">후보가 없어요. 동의한 뒤 지금 점검을 눌러 보세요.</p>'}</div>`;
}

// ── 아래 줄: 구독 사용량 ──
function sbHtml() {
  const u = S.usage?.codex; const cl = S.usage?.claude; const a = S.st?.auth;
  const bar = (v) => `<span class="tr"><span class="fl ${v >= 80 ? 'hi' : ''}" style="width:${Math.min(100, v)}%"></span></span>`;
  const day = (t) => { if (!t) return ''; const d = new Date(typeof t === 'number' && t < 1e12 ? t * 1000 : t); return isNaN(d) ? '' : ` · ${d.getMonth() + 1}/${d.getDate()} 다시 채워짐`; };
  const parts = [];
  if (!a || a.codex) parts.push(u && u.weekly != null ? `<span class="mt">Codex 이번 주 ${bar(u.weekly)}<b class="num">${u.weekly}%</b> 씀${day(u.weeklyReset)}</span>` : '<span>Codex 사용량 확인 중…</span>');
  if (!a || a.claude) parts.push(cl && (cl.weekly != null || cl.fiveHour != null) ? `<span class="mt">Claude 이번 주 ${bar(cl.weekly ?? 0)}<b class="num">${cl.weekly ?? 0}%</b> 씀${day(cl.weeklyReset)}</span>` : '<span>Claude 사용량 확인 중…</span>');
  return `${parts.join('')}<span class="sp"></span><span class="ver">AI 학교 허브${S.upd?.current && S.upd.current !== 'dev' ? ` v${esc(S.upd.current)}` : ''}</span>`;
}
function renderSB() { const el = $('#sb'); if (el) el.innerHTML = sbHtml(); }

// ── 내장 브라우저(데스크톱 앱 전용): 바깥 사이트는 미리보기 자리 위에 별도 웹 화면으로
const tinvoke = (...a) => window.__TAURI__?.core?.invoke?.(...a);
const nativeOk = () => !!window.__TAURI__?.core && /^https?:\/\//.test(S.previewSrc || '') && !/^https?:\/\/(127\.0\.0\.1|localhost):7710/.test(S.previewSrc);
let nativeShown = false;
function placeNative() {
  if (!window.__TAURI__?.core) return;
  const slot = $('#native-slot');
  if (slot && !$('.modal') && S.view === 'work' && S.sideTab === 'preview') {
    const r = slot.getBoundingClientRect();
    if (r.width > 40 && r.height > 40) { tinvoke('browser_show', { url: S.previewSrc, x: r.left, y: r.top, w: r.width, h: r.height }).catch(() => toast('이 주소를 미리보기로 열지 못했어요')); nativeShown = true; return; }
  }
  if (nativeShown) { tinvoke('browser_hide'); nativeShown = false; }
}
window.addEventListener('resize', () => placeNative());
function mtab() { const b = (v, icon, n) => `<button class="${S.view === v ? 'on' : ''}" data-act="go" data-v="${v}">${ic(icon)}${n}</button>`; return `<div class="mtab">${b('today', 'home', '오늘')}${b('work', 'layers', '작업')}${b('staff', 'users', 'AI 직원')}${b('settings', 'gear', '설정')}</div>`; }

function render() {
  if (!S.st) return;
  const draft = $('[data-form=send] textarea')?.value;
  const pdrafts = [...document.querySelectorAll('[data-form=psend]')].map((f) => [f.dataset.id, f.elements.text.value, document.activeElement === f.elements.text]);
  const pscroll = Object.fromEntries([...document.querySelectorAll('[data-chat]')].map((c) => [c.dataset.chat, c.scrollHeight - c.scrollTop - c.clientHeight < 40]));
  const forms = [...document.querySelectorAll('[data-form=newtask]')].map((f) => [f.dataset.where, f.elements.title.value, f.elements.text.value, f.elements.runtime.value, f.elements.model?.value || '']);
  const foc = document.activeElement; const focSel = foc?.dataset?.dirq ? `[data-dirq="${foc.dataset.dirq}"]` : foc?.form?.dataset?.form === 'newtask' ? `[data-form=newtask][data-where="${foc.form.dataset.where}"] [name="${foc.name}"]` : null;
  const body = S.view === 'today' ? `<div class="body">${todayView()}</div>` : S.view === 'work' ? workView() : S.view === 'staff' ? `<div class="body">${staffView()}</div>` : settingsView();
  $('#root').innerHTML = topbar() + body + `<div class="sb" id="sb">${sbHtml()}</div>` + mtab() + (!S.st.me ? meModal() : (!S.st.introSeen || S.introOpen) ? introModal() : '');
  if (!S.prefill) for (const [w, ti, tx, rt, mo] of forms) { const f = $(`[data-form=newtask][data-where="${w}"]`); if (f) { const E = f.elements; E.title.value = ti; E.text.value = tx; if (!E.runtime.querySelector(`option[value="${rt}"]`)?.disabled) E.runtime.value = rt; if (E.model) { E.model.innerHTML = modelOpts(E.runtime.value, mo); } } }
  S.prefill = null;
  if (focSel) { const el = $(focSel); if (el) { el.focus(); try { const n = el.value.length; el.setSelectionRange(n, n); } catch {} } }
  const c = $('#chat'); if (c) c.scrollTop = c.scrollHeight;
  for (const el of document.querySelectorAll('[data-chat]')) if (pscroll[el.dataset.chat] !== false) el.scrollTop = el.scrollHeight;
  for (const [id, v, f] of pdrafts) { const el = $(`[data-form=psend][data-id="${id}"] textarea`); if (el) { if (v) el.value = v; if (f) el.focus(); } }
  const ta = $('[data-form=send] textarea'); if (ta && draft) ta.value = draft;
  renderUpd();
  { const md = $('.modal'); if (md && !md.contains(document.activeElement)) md.querySelector('input,button')?.focus(); }
  placeNative();
}
const INTRO_SAY = '오늘 한 일 메모야. 이걸로 스레드 글 2개 써줘.\n\n(여기에 오늘 한 일을 적거나 붙여 넣기)';
function introModal() {
  return `<div class="modal" role="dialog" aria-modal="true" aria-label="AI 학교 허브 안내"><div class="card intro"><h4>AI 학교 허브는 이럴 때 쓰세요</h4>
   <ul class="introl"><li>AI에게 일을 맡기고, AI가 만든 글이나 페이지를 바로 옆 화면에서 봐요.</li><li>AI 직원 24명이 들어 있어요. 총괄 비서에게 말하면 필요한 직원을 알아서 불러요.</li><li>한 번 말한 내 방식은 규칙으로 쌓여서 다음 일부터 지켜요.</li></ul>
   <p class="md">터미널로 이미 잘 쓰고 계시면 그대로 쓰셔도 돼요. 만든 걸 눈으로 보면서 하고 싶을 때 허브를 여시면 돼요.</p>
   <div class="introex"><b>처음엔 이렇게 맡겨 보세요</b><p class="md">저는 그날 한 일을 메모해 두고, 그 메모로 스레드 글을 써요.</p><div class="u">오늘 한 일 메모야. 이걸로 스레드 글 2개 써줘.</div></div>
   <div class="acts"><button class="btn dark" data-act="introstart">이 문장으로 시작하기</button><button class="btn" data-act="introclose">닫기</button></div>
   <p class="crumb">이 안내는 설정 › 내 정보에서 다시 볼 수 있어요.</p></div></div>`;
}
async function closeIntro() { S.introOpen = false; if (!S.st.introSeen) { S.st.introSeen = true; try { await api('/api/intro', { method: 'POST', body: { seen: true } }); } catch {} } }
function meModal() { return `<div class="modal" role="dialog" aria-modal="true" aria-label="처음 오셨어요"><form class="card" data-form="me"><h4>처음 오셨어요</h4><p class="md" style="margin-bottom:10px">허브에서 부를 이름을 적어 주세요. 이 PC 밖으로 나가지 않아요.</p><div class="field" style="margin-bottom:12px"><input name="me" placeholder="이름" aria-label="이름" required></div><button class="btn dark">시작</button></form></div>`; }

// ── 누르기 ──
async function reveal(what, root) { const r = await api(root ? '/api/reveal' : `/api/tasks/${S.taskId}/reveal`, { method: 'POST', body: { what } }); if (!r.ok) toast(r.msg || '열지 못했어요'); }
document.addEventListener('click', async (e) => {
  const b = e.target.closest('[data-act]'); if (!b || b.tagName === 'SELECT' || b.type === 'checkbox') return;
  const a = b.dataset.act;
  try {
    if (a === 'go') { S.view = b.dataset.v; if (S.view === 'work') S.pane = S.task ? S.pane : 'list'; if (S.view === 'settings') { S.pane = 'nav'; loadSetTab(); } if (S.view === 'staff' && !S.staff) { S.staff = await api('/api/staff'); S.oss = await api('/api/open-source').catch(() => []); } if (S.view === 'today') S.my = await api('/api/my').catch(() => S.my); render(); }
    else if (a === 'update') { await api('/api/update', { method: 'POST' }); S.upd.updating = '시작'; render(); }
    else if (a === 'updlater') { // 살짝 흐려진 뒤 사라진다
      const c = $('#updpop .updcard'); const off = () => { S.updHide = S.upd?.latest; render(); };
      if (c && !matchMedia('(prefers-reduced-motion: reduce)').matches) { c.classList.add('out'); setTimeout(off, 150); } else off();
    }
    else if (a === 'updnotes') { S.updNotes = !S.updNotes; render(); }
    else if (a === 'settings') { S.view = 'settings'; if (b.dataset.tab) { S.setTab = b.dataset.tab; S.pane = 'page'; } else S.pane = 'nav'; render(); loadSetTab(); }
    else if (a === 'settab') { S.setTab = b.dataset.tab; S.pane = 'page'; render(); loadSetTab(); }
    else if (a === 'open') { if (b.dataset.id) { if (S.split && S.view === 'work' && b.classList.contains('row')) await addSplit(b.dataset.id); else { if (S.split) { S.split = false; saveSplit(); } await openTask(b.dataset.id); } } }
    else if (a === 'split') await toggleSplit();
    else if (a === 'introclose') { await closeIntro(); render(); }
    else if (a === 'introshow') { S.introOpen = true; render(); }
    else if (a === 'introstart') { await closeIntro(); S.view = 'today'; S.prefill = { where: 'today', title: '오늘 한 일로 스레드 글', text: INTRO_SAY }; render(); setTimeout(() => { const ta = $('[data-form=newtask][data-where=today] textarea'); if (ta) { ta.focus(); const i = ta.value.indexOf('('); if (i > 0) ta.setSelectionRange(i, ta.value.length); } }, 30); }
    else if (a === 'splx') { S.splitIds = S.splitIds.filter((x) => x !== b.dataset.id); delete S.splitTasks[b.dataset.id]; saveSplit(); render(); }
    else if (a === 'splone') { S.split = false; saveSplit(); await openTask(b.dataset.id); }
    else if (a === 'pstop') { b.disabled = true; await api(`/api/tasks/${b.dataset.id}/stop`, { method: 'POST' }); }
    else if (a === 'dirtoggle') { const w = b.dataset.where; const d = (S.dir[w] = S.dir[w] || {}); d.open = !d.open; render(); if (d.open) { setTimeout(() => $(`[data-dirq="${w}"]`)?.focus(), 30); loadDirs(w, d.q || ''); } }
    else if (a === 'dirpick') { const w = b.dataset.where; const d = (S.dir[w] = S.dir[w] || {}); d.path = b.dataset.path; d.open = false; render(); }
    else if (a === 'attdel') { (S.att[b.dataset.k] || []).splice(Number(b.dataset.i), 1); render(); }
    else if (a === 'imgview') { await setPreview(b.dataset.src); S.sideTab = 'preview'; if (matchMedia('(max-width:860px)').matches) S.pane = 'side'; if (S.split && S.taskId !== b.dataset.task && b.dataset.task) { S.split = false; saveSplit(); await openTask(b.dataset.task); S.sideTab = 'preview'; await setPreview(b.dataset.src); } render(); }
    else if (a === 'attpick') { b.nextElementSibling?.click(); }
    else if (a === 'ctxhelp') { toast(b.dataset.msg); }
    else if (a === 'ctxgo') { await api(`/api/tasks/${S.taskId}/continue`, { method: 'POST' }); toast('지금 AI가 정리 카드를 쓰는 중이에요. 끝나면 새 대화가 열려요'); await openTask(S.taskId, true); render(); }
    else if (a === 'ctxno') { await api(`/api/tasks/${S.taskId}/ctx-dismiss`, { method: 'POST' }); S.task.ctxDismissed = true; render(); }
    else if (a === 'pane') { S.pane = b.dataset.p; render(); }
    else if (a === 'stab') { S.sideTab = b.dataset.t; render(); }
    else if (a === 'nav') { await tinvoke('browser_go', { action: b.dataset.go }); }
    else if (a === 'preview') { await setPreview(fileUrl(b.dataset.name)); S.sideTab = 'preview'; if (S.pane === 'chat' && innerWidth <= 860) S.pane = 'side'; render(); }
    else if (a === 'openurl') { e.preventDefault(); if (S.view === 'work' && S.task) { await setPreview(b.dataset.url); S.sideTab = 'preview'; render(); } else window.open(b.dataset.url, '_blank', 'noopener'); }
    else if (a === 'wide') { S.wide = !S.wide; render(); }
    else if (a === 'stop') { b.disabled = true; await api(`/api/tasks/${S.taskId}/stop`, { method: 'POST' }); }
    else if (a === 'reveal') await reveal(b.dataset.what);
    else if (a === 'revealroot') await reveal(b.dataset.what, true);
    else if (a === 'rename') { const v = prompt('새 작업 이름', S.task.title); if (v && v.trim()) { await api(`/api/tasks/${S.taskId}/rename`, { method: 'POST', body: { title: v } }); await load(); } }
    else if (a === 'delete') { if (!confirm(`'${S.task.title}' 작업을 목록에서 지울까요? 폴더의 결과물은 남아요.`)) return; await api(`/api/tasks/${S.taskId}/delete`, { method: 'POST' }); S.task = null; S.taskId = null; S.pane = 'list'; await load(); toast('목록에서 지웠어요'); }
    else if (a === 'byfolder') { S.byFolder = b.dataset.v === '1'; try { localStorage.setItem('byFolder', S.byFolder ? '1' : ''); } catch {} render(); }
    else if (a === 'markedit') { S.markEdit = true; render(); }
    else if (a === 'makestaff') { S.view = 'today'; S.prefill = { where: 'today', title: '새 직원 만들기', text: '내 일에 맞는 AI 직원을 하나 만들고 싶어.\n맡기고 싶은 일: (여기에 적기)\n주로 넣어 줄 것: (메모, 사진, 엑셀 등)\n받고 싶은 결과: (글, 이미지, 표 등)' }; render(); setTimeout(() => { const ta = $('[data-form=newtask][data-where=today] textarea'); if (ta) { ta.focus(); const i = ta.value.indexOf('('); if (i > 0) ta.setSelectionRange(i, ta.value.indexOf(')', i) + 1); } }, 30); }
    else if (a === 'hire') { const s = (S.staff?.staff || []).find((x) => x.name === b.dataset.name); S.view = 'today'; S.prefill = { where: 'today', title: s ? `${s.name} · ${s.example}`.slice(0, 40) : '', text: s ? `${s.name}에게 맡길게. ${s.example}` : '' }; render(); setTimeout(() => { const ta = $('[data-form=newtask][data-where=today] textarea'); if (ta) { ta.focus(); ta.select(); } }, 30); }
    else if (a === 'myinterview') { const r = await api('/api/my/interview', { method: 'POST' }); await load(); await openTask(r.task); }
    else if (a === 'myreveal') { const r = await api('/api/my/reveal', { method: 'POST' }); if (!r.ok) toast(r.msg || '열지 못했어요'); }
    else if (a === 'connhelp') { const r = await api('/api/connections/help', { method: 'POST', body: { id: b.dataset.id } }); await load(); await openTask(r.task); }
    else if (a === 'keydel') { if (!confirm('저장한 키를 지울까요?')) return; await api('/api/connections/key', { method: 'POST', body: { name: b.dataset.name, remove: true } }); S.conns = await api('/api/connections'); render(); toast('지웠어요'); }
    else if (a === 'osshire') { const o = (S.oss || []).find((x) => x.name === b.dataset.name); S.view = 'today'; S.prefill = { where: 'today', title: `${o.name} 써 보기`, text: o.say }; render(); }
    else if (a === 'authlogin' || a === 'authdevice') { const w = b.dataset.who; S.login[w] = { who: w, state: 'opening' }; render(); try { const r = await api(`/api/auth/${w}/login`, { method: 'POST', body: { mode: a === 'authdevice' ? 'device' : 'browser' } }); if (S.login[w]) S.login[w] = r.login || null; if (r.msg) toast(r.msg); } catch (e) { S.login[w] = { who: w, state: 'failed', note: '로그인 창을 열지 못했어요. 다시 눌러 주세요.' }; } render(); }
    else if (a === 'authlogout') { const r = await api(`/api/auth/${b.dataset.who}/logout`, { method: 'POST' }); S.login[b.dataset.who] = null; toast(r.msg); }
    else if (a === 'authcancel') { S.login[b.dataset.who] = null; render(); await api(`/api/auth/${b.dataset.who}/cancel`, { method: 'POST' }); }
    else if (a === 'authopen') { const r = await api(`/api/auth/${b.dataset.who}/open`, { method: 'POST' }); toast(r.msg); }
    else if (a === 'authcopy') { const L = S.login[b.dataset.who] || {}; const code = b.dataset.what === 'code'; try { await navigator.clipboard.writeText((code ? L.code : L.copyUrl || L.url) || ''); toast(code ? '코드를 복사했어요. 브라우저 화면에 붙여 넣으세요' : '주소를 복사했어요. 브라우저 주소창에 붙여 넣으세요'); } catch { toast('복사하지 못했어요'); } }
    else if (a === 'authrefresh') { S.auth = null; render(); S.auth = await api('/api/auth?fresh=1'); syncLogin(); await load(); }
    else if (a === 'scan') { S.scanBusy = true; render(); S.scan = await api('/api/skills/scan', { method: 'POST' }); S.scanBusy = false; render(); }
    else if (a === 'learnscan') { S.learnBusy = true; render(); await api('/api/learn/scan', { method: 'POST', body: { days: 7 } }); }
    else if (a === 'decide') { const r = await api('/api/learn/decide', { method: 'POST', body: { id: b.dataset.id, choice: b.dataset.c } }); toast(r.choice === 'discard' ? '버렸어요' : r.ok ? '넣었어요' : (r.msg || '넣지 못했어요')); S.pending = await api('/api/learn/pending'); S.rules = null; await load(); }
  } catch (err) { toast(err.message); S.scanBusy = false; render(); }
});
document.addEventListener('change', async (e) => { const el = e.target; if (el.matches?.('[data-rtsel]')) { const ms = el.form.elements.model; if (ms) ms.innerHTML = modelOpts(el.value); return; } if (el.dataset?.attin) { await addImages(el.dataset.attin, el.files); el.value = ''; return; } if (el.dataset.act === 'consent') { await api('/api/learn/consent', { method: 'POST', body: { on: el.checked } }); await load(); } });
document.addEventListener('input', (e) => { const el = e.target; if (el.dataset.dirq) { clearTimeout(dirTimer); const w = el.dataset.dirq, v = el.value; dirTimer = setTimeout(() => loadDirs(w, v), 180); } });
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && (S.introOpen || (S.st && S.st.me && !S.st.introSeen)) && $('.modal .intro')) { e.preventDefault(); closeIntro().then(render); return; }
  if (e.target.dataset?.dirq && e.key === 'Enter') { e.preventDefault(); const first = document.querySelector(`[data-dirlist="${e.target.dataset.dirq}"] .dirrow:nth-child(2)`); if (first) first.click(); return; }
  if (e.target.matches('[data-form=send] textarea, [data-form=psend] textarea') && e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); e.target.form.requestSubmit(); }
});
// 캡처 붙여 넣기(Ctrl+V / Cmd+V)와 끌어 놓기: 사진만 첨부로 받고, 글은 평소처럼 붙는다
document.addEventListener('paste', (e) => {
  const f = e.target.closest?.('form[data-form=send], form[data-form=psend], form[data-form=newtask]'); if (!f || !e.clipboardData) return;
  const files = [...(e.clipboardData.items || [])].filter((it) => it.kind === 'file' && /^image\//.test(it.type)).map((it) => it.getAsFile()).filter(Boolean);
  const types = [...(e.clipboardData.types || [])];
  if (!files.length || types.includes('text/html') || types.includes('text/rtf')) return;
  e.preventDefault(); addImages(attKey(f), files);
});
document.addEventListener('dragover', (e) => { if ([...(e.dataTransfer?.types || [])].includes('Files')) e.preventDefault(); });
document.addEventListener('drop', (e) => { if (![...(e.dataTransfer?.types || [])].includes('Files')) return; e.preventDefault(); const f = e.target.closest?.('form[data-form=send], form[data-form=psend], form[data-form=newtask]'); if (f && e.dataTransfer.files?.length) addImages(attKey(f), e.dataTransfer.files); });
// 미리보기 폭 끌어서 바꾸기
document.addEventListener('pointerdown', (e) => {
  if (e.target.dataset?.drag !== 'side') return; e.preventDefault();
  const bodyEl = e.target.closest('.body'); const move = (ev) => { const w = Math.max(320, Math.min(innerWidth - 560, innerWidth - ev.clientX)); S.sideW = w; bodyEl.style.setProperty('--side-w', w + 'px'); placeNative(); };
  const up = () => { removeEventListener('pointermove', move); removeEventListener('pointerup', up); try { localStorage.setItem('sideW', String(S.sideW)); } catch {} };
  addEventListener('pointermove', move); addEventListener('pointerup', up);
});
try { const w = Number(localStorage.getItem('sideW')); if (w) S.sideW = w; } catch {}
try { S.byFolder = localStorage.getItem('byFolder') === '1'; } catch {}
document.addEventListener('submit', async (e) => {
  e.preventDefault(); const f = e.target; const d = Object.fromEntries(new FormData(f)); const k = f.dataset.form;
  try {
    if (k === 'search') { S.q = d.q; S.res = d.q ? await api(`/api/search?q=${encodeURIComponent(d.q)}`) : []; render(); }
    else if (k === 'newtask') { if (!d.runtime) return toast('먼저 설정 › AI 로그인에서 로그인해 주세요'); if (S.attBusy) return toast('사진을 준비하는 중이에요. 잠깐 뒤 맡겨 주세요'); const ak = attKey(f); const images = (S.att[ak] || []).map((x) => x.data); const t = await api('/api/tasks', { method: 'POST', body: { ...d, images } }); delete S.att[ak]; f.reset(); S.dir[f.dataset.where] = {}; await load(); await openTask(t.id); }
    else if (k === 'psend' || k === 'send') {
      if (S.attBusy) return toast('사진을 준비하는 중이에요. 잠깐 뒤 보내 주세요');
      const ak = attKey(f); const att = S.att[ak] || []; const images = att.map((x) => x.data); if (!d.text.trim() && !images.length) return;
      const id = k === 'psend' ? f.dataset.id : S.taskId; const sel = k === 'psend' ? `[data-form=psend][data-id="${id}"] textarea` : '[data-form=send] textarea';
      // 보내는 순간 입력칸·사진을 비운다(서버 알림으로 화면이 다시 그려져도 보낸 글이 남지 않게). 실패하면 되돌린다.
      f.querySelector('textarea').value = ''; delete S.att[ak]; render();
      try { await api(`/api/tasks/${id}/send`, { method: 'POST', body: { text: d.text, images } }); }
      catch (err) { const ta = $(sel); if (ta && !ta.value) ta.value = d.text; if (att.length) S.att[ak] = att; render(); const ta2 = $(sel); if (ta2 && !ta2.value) ta2.value = d.text; throw err; }
      if (k === 'psend') await loadSplit(id); else await openTask(S.taskId, true);
      render();
    }
    else if (k === 'mark') { const mk = e.submitter?.value; if (!mk) return; const r = await api(`/api/tasks/${S.taskId}/mark`, { method: 'POST', body: { mark: mk, note: d.note || '' } }); S.task.mark = r.mark; S.markEdit = false; await load(); toast(mk === 'good' ? '잘 됐다고 남겼어요' : '다시 해야 한다고 남겼어요'); }
    else if (k === 'url') { let u = d.u.trim(); if (!u) return; if (!/^(https?:|\/)/.test(u)) u = /\.\w{1,5}$/.test(u) && !/^www\./.test(u) && S.files.some((x) => x.name === u) ? fileUrl(u) : 'https://' + u; await setPreview(u); render(); }
    else if (k === 'me') { await api('/api/me', { method: 'POST', body: d }); await load(); const a = S.st.auth; if (a && !a.codex && !a.claude) { S.view = 'settings'; S.setTab = 'ai'; S.pane = 'page'; render(); loadSetTab(); toast('먼저 AI 로그인을 해 주세요'); } else toast('오늘 탭의 새로 맡기기에서 첫 일을 맡겨 보세요'); }
    else if (k === 'authcode') { if (!d.code.trim()) return toast('코드를 붙여 넣어 주세요'); const r = await api(`/api/auth/${f.dataset.who}/code`, { method: 'POST', body: { code: d.code } }); toast(r.msg); }
    else if (k === 'key') { if (!d.value.trim()) return toast('키를 붙여 넣어 주세요'); await api('/api/connections/key', { method: 'POST', body: { name: d.name, value: d.value } }); f.reset(); S.conns = await api('/api/connections'); render(); toast('이 PC 금고에 저장했어요'); }
    else if (k === 'register') { const names = [...f.querySelectorAll('input[name=n]:checked')].map((x) => x.value); if (!names.length) return toast('넣을 스킬을 골라 주세요'); toast('허브에 넣는 중…'); const r = await api('/api/skills/register', { method: 'POST', body: { names } }); toast(r.ok ? `${names.length}개를 허브에 넣었어요` : '넣지 못했어요'); S.scan = await api('/api/skills/scan', { method: 'POST' }); render(); }
  } catch (err) { toast(err.message); }
});
async function loadSetTab() {
  try {
    if (S.setTab === 'rules' && !S.rules) S.rules = await api('/api/rules');
    if (S.setTab === 'learn') S.pending = await api('/api/learn/pending');
    if (S.setTab === 'ai' && !S.auth) { S.auth = await api('/api/auth'); syncLogin(); }
    if (S.setTab === 'conn') S.conns = await api('/api/connections');
    render();
  } catch (err) { toast(err.message); }
}

// 실시간
const es = new EventSource('/api/events');
es.onmessage = async (m) => {
  const ev = JSON.parse(m.data);
  if (ev.type === 'msg' && S.split && S.splitTasks[ev.task]) { S.splitTasks[ev.task].messages.push(ev.msg); if (S.view === 'work') render(); }
  if (ev.type === 'status' && S.split && S.splitTasks[ev.task]) await loadSplit(ev.task);
  if (ev.type === 'msg' && ev.task === S.taskId && S.task) { S.task.messages.push(ev.msg); if (ev.msg.kind === 'file' || ev.msg.text?.startsWith('파일')) S.files = await api(`/api/tasks/${S.taskId}/files`); render(); }
  if (ev.type === 'status') { await load(); if (ev.task === S.taskId && ev.status !== 'working') { S.files = await api(`/api/tasks/${S.taskId}/files`); const h = S.files.find((f) => /\.html?$/i.test(f.name)); if (h && !S.previewSrc) await setPreview(fileUrl(h.name)); render(); loadUsage(); } }
  if (ev.type === 'update') {
    if (ev.step === 'fail') { if (S.upd) S.upd.updating = null; render(); toast(`업데이트하지 못했어요. ${ev.msg || ''}`); }
    else if (ev.step === 'restart') { if (S.upd) S.upd.updating = '다시 켜는 중'; render(); waitRestart(ev.version); }
    else { if (S.upd) S.upd.updating = ev.step; render(); }
  }
  if (ev.type === 'login') { const done = ev.login?.state === 'done'; S.login[ev.who] = done ? null : ev.login; if (done) toast('로그인됐어요'); if (S.view === 'settings' && S.setTab === 'ai') { const f = document.activeElement?.form?.dataset?.form === 'authcode'; const v = $('[data-form=authcode] input')?.value; render(); const i = $('[data-form=authcode] input'); if (i && v) { i.value = v; if (f) i.focus(); } } }
  if (ev.type === 'auth') { api('/api/models').then((m) => { S.models = m; }).catch(() => {}); if (S.st) { S.st.auth = { codex: ev.codex, claude: ev.claude }; if (S.view === 'settings' && S.setTab === 'ai') { try { S.auth = await api('/api/auth'); syncLogin(); } catch {} } else S.auth = null; render(); } } // 화면을 비우지 않고 새 상태로 바꾼다
  if (ev.type === 'learn') { S.learnBusy = false; S.pending = await api('/api/learn/pending'); await load(); toast(ev.ok ? `점검 끝 · 대화 ${ev.files}개에서 후보 ${ev.candidates}개` : '점검하지 못했어요. 잠시 뒤 다시 눌러 주세요'); }
  if (ev.type === 'continued') { await load(); if (ev.ok && ev.task === S.taskId) { await openTask(ev.to); toast('새 대화로 이어갔어요'); } else if (!ev.ok) toast('정리 카드를 못 받았어요. 다시 눌러 주세요'); }
};
// 주소 뒤 #task=<id> / #settings=<탭> / #staff 로 바로 열기
async function route() {
  const h = new URLSearchParams(location.hash.slice(1));
  if (h.get('task')) { await openTask(h.get('task')); if (h.get('side')) { S.sideTab = h.get('side'); render(); } }
  else if (h.get('settings')) { S.view = 'settings'; S.setTab = h.get('settings'); S.pane = 'page'; render(); await loadSetTab(); }
  else if (h.has('staff')) { S.view = 'staff'; S.staff = await api('/api/staff'); S.oss = await api('/api/open-source').catch(() => []); render(); }
}
// 업데이트 확인: 앱을 열 때, 그리고 켜 둔 동안 6시간마다
async function checkUpdate() { try { S.upd = await api('/api/update'); render(); } catch {} }
// 새 코드로 서버가 다시 켜질 때까지 기다렸다가 화면을 새로 연다
async function waitRestart(v) {
  for (let i = 0; i < 80; i++) {
    await new Promise((r) => setTimeout(r, 1500));
    try { const u = await (await fetch('/api/update')).json(); if (u.current === v) { location.reload(); return; } } catch {}
  }
  toast('다시 켜지지 않았어요. 앱을 껐다 켜 주세요');
}
api('/api/models').then((m) => { S.models = m; render(); }).catch(() => {});
load().then(route).then(loadUsage).then(checkUpdate); setInterval(loadUsage, 120000); setInterval(checkUpdate, 6 * 3600e3);
