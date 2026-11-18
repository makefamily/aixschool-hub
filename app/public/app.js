// AI 학교 허브 화면 — 외부 라이브러리 없음.
window.addEventListener('error', (e) => { try { fetch('/api/client-log', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ m: '화면 오류: ' + e.message + ' @' + e.lineno }) }); } catch {} toast('화면에 문제가 생겼어요. 앱을 껐다 켜 주세요'); });
window.addEventListener('unhandledrejection', (e) => { try { fetch('/api/client-log', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ m: '화면 오류: ' + (e.reason?.message || e.reason) }) }); } catch {} });

const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const ic = (id, cls = '') => `<svg class="i ${cls}"><use href="#${id}"/></svg>`;
const api = async (url, opt = {}) => { const r = await fetch(url, { headers: { 'content-type': 'application/json' }, ...opt, body: opt.body ? JSON.stringify(opt.body) : undefined }); const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.msg || `오류 ${r.status}`); return j; };
const S = { st: null, view: 'today', taskId: null, task: null, files: [], sideTab: 'preview', previewSrc: '', mdText: null, usage: null, q: '', res: [], setTab: 'ai', scan: null, scanBusy: false, pane: 'list', learnBusy: false, pending: [], rules: null, auth: null, dir: {}, staff: null, skills: null, prefill: null, my: null, conns: null, oss: null };
function toast(t) { const d = document.createElement('div'); d.className = 'toast'; d.textContent = t; document.body.appendChild(d); setTimeout(() => d.remove(), 3600); }
const ago = (iso) => { if (!iso) return ''; const m = Math.round((Date.now() - new Date(iso)) / 60000); return m < 1 ? '방금' : m < 60 ? `${m}분 전` : m < 1440 ? `${Math.round(m / 60)}시간 전` : `${Math.round(m / 1440)}일 전`; };
const stLabel = (s) => ({ working: ['work', '하는 중'], done: ['done', '끝남'], error: ['late', '오류'], idle: ['done', '새 작업'] }[s] || ['done', s]);
const base = (p) => String(p || '').split(/[\\/]/).filter(Boolean).pop() || p;
const rtName = (r) => (r === 'claude' ? 'Claude' : 'Codex');
const ctxPct = (t) => (t.ctx && typeof t.ctx.pct === 'number' ? t.ctx.pct : null);
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
  S.taskId = id; S.task = await api(`/api/tasks/${id}`);
  S.files = await api(`/api/tasks/${id}/files`).catch(() => []);
  if (!S.previewSrc || !S.previewSrc.startsWith(`/files/${id}/`)) { const h = S.files.find((f) => /\.html?$/i.test(f.name)) || S.files.find((f) => /\.(png|jpe?g|webp|gif|svg|pdf|md|txt)$/i.test(f.name)); setPreview(h ? fileUrl(h.name) : ''); }
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

// ── 업데이트 띠: 새 버전이 있을 때만 위 줄 아래에 뜬다 ──
function updBar() {
  const u = S.upd; if (!u) return '';
  if (u.updating) return `<div class="updbar"><span class="dot work"></span><span>업데이트 중 · ${esc(u.updating)}</span><span class="sp"></span><span class="ink3">끝나면 화면이 저절로 새로 열려요</span></div>`;
  if (!u.available || S.updHide === u.latest) return '';
  const first = (u.notes || '').split('\n').map((l) => l.replace(/^[-*\s]+/, '').trim()).find(Boolean) || '';
  return `<div class="updbar"><span>새 버전 <b class="num">v${esc(u.latest)}</b>이 나왔어요</span>${first ? `<span class="ink3 updnote" title="${esc(u.notes)}">${esc(first)}</span>` : ''}<span class="sp"></span><button class="btn" data-act="updlater">나중에</button><button class="btn pri" data-act="update">업데이트</button></div>`;
}

// ── 오늘 ──
function todayView() {
  const working = S.st.tasks.filter((t) => t.status === 'working');
  const recent = S.st.tasks.slice(0, 6);
  const d = new Date(); const wd = '일월화수목금토'[d.getDay()];
  return `<div class="page"><h2>${d.getMonth() + 1}월 ${d.getDate()}일 ${wd}요일</h2><p class="lead">${esc(S.st.me || '')}님, AI에게 맡긴 일과 결과물을 한곳에서 봐요.</p>
  <div class="grid2"><div style="display:flex;flex-direction:column;gap:16px">
   <div class="card"><h4>총괄 비서에게 맡기기<span class="r">필요한 직원을 알아서 불러요</span></h4>${newTaskForm('today')}</div>
   ${myCard()}
   <div class="card"><h4>AI가 하는 중<span class="r num">${working.length}건</span></h4>${working.map(taskWl).join('') || '<p class="empty">지금 하는 일이 없어요.</p>'}</div>
  </div><div style="display:flex;flex-direction:column;gap:16px">
   <div class="card"><h4>작업 찾기</h4>${searchBox()}</div>
   <div class="card"><h4>최근 작업</h4>${recent.map(taskWl).join('') || '<p class="empty">아직 작업이 없어요. 왼쪽에서 첫 일을 맡겨 보세요.</p>'}</div>
   <div class="card"><h4>내 작업 폴더</h4><p class="md">맡긴 일의 결과물이 모두 이 폴더에 쌓여요.</p><div class="acts"><button class="btn" data-act="revealroot" data-what="folder">${ic('folder', 's')}폴더 열기</button><button class="btn" data-act="revealroot" data-what="terminal">${ic('term', 's')}터미널 열기</button></div></div>
  </div></div></div>`;
}
function myCard() {
  const m = S.my; if (!m) return '';
  return `<div class="card"><h4>내 자료<span class="r num">${m.done}/${m.total} 채움</span></h4><p class="md">AI가 일할 때 먼저 읽는 나만의 자료예요. 처음엔 비어 있어요. 내 글·생각·일을 채울수록 결과가 원하는 대로 나와요.</p>
   <ul class="mylist">${m.items.map((x) => `<li class="${x.done ? 'ok' : ''}"><span class="st ${x.done ? 'work' : 'done'}">${x.done ? '채움' : '비어 있음'}</span>${esc(x.name)}</li>`).join('')}</ul>
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
   <div class="field area"><textarea name="text" rows="4" placeholder="총괄 비서에게 평소 말하듯 적어 주세요. 예) 이 메모로 블로그 글이랑 스레드 2편, 카드뉴스 5장 만들어줘">${esc(pf?.text || '')}</textarea></div>
   ${dirPicker(where)}
   <div class="ctl"><div class="field" style="min-height:32px"><select name="runtime" aria-label="맡길 AI">${opt('codex')}${opt('claude')}</select></div><span class="sp"></span><button class="go" ${ai.none ? 'disabled' : ''}>맡기기</button></div>
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
  return def + (list.map((x) => `<button type="button" class="dirrow ${d.path === x.path ? 'on' : ''}" data-act="dirpick" data-where="${where}" data-path="${esc(x.path)}"><span class="dn">${esc(x.name)}</span><span class="dp">${esc(x.home)}</span></button>`).join('') || '<p class="empty" style="padding:8px 10px">맞는 폴더가 없어요.</p>');
}
let dirTimer;
async function loadDirs(where, q) { const d = (S.dir[where] = S.dir[where] || {}); d.q = q; try { d.list = await api(`/api/dirs?q=${encodeURIComponent(q || '')}`); } catch { d.list = []; } const el = document.querySelector(`[data-dirlist="${where}"]`); if (el) el.innerHTML = dirListHtml(where); }
function searchBox() {
  return `<form data-form="search"><div class="field">${ic('search', 's')}<input name="q" value="${esc(S.q)}" placeholder="작업 이름·파일 이름·대화 내용"></div></form>
  <div style="margin-top:8px">${S.res.map((r) => `<button class="row" data-act="open" data-id="${esc(r.id || '')}"><span class="st done">${esc(r.kind === '태스크' ? '작업' : r.kind)}</span><div style="min-width:0"><div class="t">${esc(r.title)}</div><div class="m">${esc(r.sub || '')}</div></div></button>`).join('')}${S.q && !S.res.length ? '<p class="empty">찾은 게 없어요.</p>' : ''}</div>`;
}

// ── 내 작업 ──
function weekKey(iso) { const d = new Date(iso || 0); const now = new Date(); const day = (x) => Math.floor((x - new Date(x.getFullYear(), 0, 1)) / 864e5); const diff = Math.floor((now - d) / 864e5); if (diff < 1 && now.getDate() === d.getDate()) return '오늘'; if (diff < 7) return '이번 주'; if (diff < 14) return '지난주'; return `${d.getMonth() + 1}월`; }
function workView() {
  const list = S.st.tasks;
  const groups = []; for (const t of list) { const k = t.status === 'working' ? 'AI가 하는 중' : weekKey(t.updated); let g = groups.find((x) => x.k === k); if (!g) groups.push((g = { k, items: [] })); g.items.push(t); }
  groups.sort((a, b) => (a.k === 'AI가 하는 중' ? -1 : b.k === 'AI가 하는 중' ? 1 : 0));
  const row = (t) => `<button class="row ${t.id === S.taskId ? 'on' : ''}" data-act="open" data-id="${t.id}"><span class="dot ${t.status === 'working' ? 'work' : t.status === 'error' ? 'err' : 'idle'}" style="margin-top:8px"></span><div style="min-width:0"><div class="t">${esc(t.title)}</div><div class="m">${rtName(t.runtime)} · ${ago(t.updated)}</div></div></button>`;
  const rail = `<div class="rail"><div class="lbl">내 작업</div>${searchBox()}
   <details ${list.length ? '' : 'open'}><summary class="lbl" style="cursor:pointer">${ic('plus', 's')}새 작업</summary>${newTaskForm('work')}</details>
   ${groups.map((g) => `<div><div class="lbl">${g.k}</div>${g.items.map(row).join('')}</div>`).join('')}
   ${!list.length ? '<p class="empty">아직 작업이 없어요. 위 새 작업에서 맡겨 보세요.</p>' : ''}</div>`;
  return `<div class="body ${S.wide ? 'wide' : ''}" data-pane="${S.pane}" style="${S.sideW ? `--side-w:${S.sideW}px` : ''}">${rail}${S.task ? taskMain() + `<div class="resizer" data-drag="side" title="끌어서 미리보기 폭 바꾸기"></div>` + sidePanel() : `<div class="mainc"><div class="page" style="background:var(--card)"><p class="empty">왼쪽에서 작업을 고르거나 새로 맡기세요.</p></div></div>`}</div>`;
}
// 대화: 이어진 '실행' 줄은 접어서 "작업 과정 N단계"로, 스킬 사용·파일은 한 줄씩 보이게
function chatHtml(t) {
  const out = []; let steps = [];
  const flush = () => { if (!steps.length) return; out.push(`<details class="steps"><summary>작업 과정 ${steps.length}단계</summary>${steps.map((m) => `<div class="log">${esc(m.text)}</div>`).join('')}</details>`); steps = []; };
  for (const m of t.messages) {
    const isStep = m.role === 'log' && m.kind !== 'skill' && m.kind !== 'file' && !/^(파일|스킬 사용) ·/.test(m.text);
    if (isStep) { steps.push(m); continue; }
    flush();
    if (m.role === 'me') out.push(`<div class="u ${m.sys ? 'sys' : ''}">${esc(m.text)}</div>`);
    else if (m.role === 'ai') out.push(`<div class="a">${md(m.text)}</div>`);
    else if (m.role === 'warn') out.push(`<div class="warnbox">${esc(m.text)}${m.kind === 'login' || m.kind === 'missing' ? ` <button class="linkbtn" data-act="settings" data-tab="ai">AI 로그인 열기</button>` : ''}${m.detail ? `<details class="why"><summary>자세히</summary><div>${esc(m.detail)}</div></details>` : ''}</div>`);
    else if (m.kind === 'skill' || /^스킬 사용 ·/.test(m.text)) out.push(`<div class="log skill">${ic('users', 's')}${esc(m.text)}</div>`);
    else out.push(`<div class="log">${ic('file', 's')}${esc(m.text)}</div>`);
  }
  flush();
  return out.join('');
}
function taskMain() {
  const t = S.task; const busy = t.status === 'working'; const pct = ctxPct(t);
  const band = pct != null && pct >= 50 && !t.continuedTo && !t.ctxDismissed && !busy ? `<div class="ctxband"><div><b>대화가 길어졌어요.</b> 더 길어지면 앞 내용을 흐리게 기억해요. 새 대화로 이어가면 지금 AI가 정리 카드를 쓰고, 같은 폴더의 새 대화가 그 카드부터 시작해요.</div><div class="acts" style="margin:0"><button class="btn dark" data-act="ctxgo">새 대화로 이어가기</button><button class="btn" data-act="ctxno">나중에</button></div></div>`
    : t.continuedTo ? `<div class="ctxband done"><div>이 대화는 새 대화로 이어졌어요.</div><button class="btn" data-act="open" data-id="${t.continuedTo}">이어진 대화 열기</button></div>` : '';
  return `<div class="mainc"><div class="th"><button class="btn mob-only" data-act="pane" data-p="list" aria-label="목록으로">${ic('back', 's')}</button><span class="dot ${busy ? 'work' : 'idle'}"></span><h3>${esc(t.title)}</h3><span class="chip">${rtName(t.runtime)}</span><span class="sp"></span>
   <button class="btn" data-act="reveal" data-what="folder" title="${esc(t.cwd)}">${ic('folder', 's')}폴더 열기</button><button class="btn" data-act="reveal" data-what="terminal">${ic('term', 's')}터미널 열기</button>
   <button class="btn mob-only" data-act="pane" data-p="side" aria-label="미리보기">${ic('eye', 's')}</button></div>${band}
   <div class="chat" id="chat">${chatHtml(t) || '<p class="empty">아래에 맡길 일을 적어 주세요. 허브에 있는 AI 직원(스킬)을 AI가 알아서 불러 써요.</p>'}${busy ? '<div class="typing">AI가 일하는 중이에요…</div>' : ''}</div>
   <div class="comp"><form class="box" data-form="send"><textarea name="text" aria-label="메시지" placeholder="이어서 할 말 · Enter로 보내기, Shift+Enter 줄바꿈" ${busy ? 'disabled' : ''}></textarea>
   <div class="ctl"><span class="crumb">${t.picked ? esc(base(t.cwd)) + ' 폴더에서 작업' : ''}</span><span class="sp"></span>${busy ? `<button type="button" class="btn" data-act="stop">${ic('stop', 's')}멈추기</button>` : `<button class="send" aria-label="보내기">${ic('up')}</button>`}</div></form></div></div>`;
}
function sidePanel() {
  const t = S.task; let pane = '';
  const isFile = S.previewSrc.startsWith('/files/');
  const bar = `<form class="urlbar" data-form="url">${nativeOk() ? `<button type="button" class="btn" data-act="nav" data-go="back" aria-label="뒤로">${ic('back', 's')}</button><button type="button" class="btn" data-act="nav" data-go="reload" aria-label="새로고침">${ic('refresh', 's')}</button>` : ''}<input name="u" value="${esc(isFile ? decodeURIComponent(S.previewSrc.split('/').slice(3).join('/')) : S.previewSrc)}" placeholder="결과물 파일 이름 또는 웹 주소" aria-label="주소"><button class="btn">열기</button><button type="button" class="btn" data-act="wide" aria-label="크게 보기">${ic(S.wide ? 'shrink' : 'expand', 's')}${S.wide ? '작게' : '크게'}</button></form>`;
  if (S.sideTab === 'preview') {
    if (nativeOk()) pane = bar + `<div id="native-slot" style="flex:1;min-height:300px;background:#fff"></div>`;
    else if (S.mdText != null) pane = bar + `<div class="mdview">${md(S.mdText)}</div>`;
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
  const card = (s) => `<div class="card staff"><h4>${esc(s.name)}</h4><p>${esc(s.role)}</p>${s.example ? `<p class="q">이렇게 말해 보세요 · “${esc(s.example)}”</p>` : ''}${s.needs ? `<p class="crumb">필요한 것: ${esc(s.needs)}</p>` : ''}${(s.with || []).length ? `<p class="crumb">함께 쓰는 스킬: ${esc(s.with.join(', '))}</p>` : ''}<div class="acts"><button class="btn dark" data-act="hire" data-name="${esc(s.name)}">이 직원에게 맡기기</button></div></div>`;
  const chief = (st.staff || []).find((s) => s.chief);
  const main = (st.staff || []).filter((s) => !s.helper && !s.chief); const helpers = (st.staff || []).filter((s) => s.helper);
  const teams = [...new Set(main.map((s) => s.team || ''))];
  return `<div class="page"><h2>AI 직원 ${main.length}명</h2><p class="lead">허브에 들어 있는 AI 직원이에요. 일을 맡기면 AI가 알맞은 직원을 알아서 불러요. 직원 이름을 직접 말해도 돼요. 쓰면서 내 일에 맞게 고쳐 가면 내 직원이 돼요.</p>
  ${chief ? `<div class="card chief"><h4>${esc(chief.name)}<span class="r">총괄</span></h4><p>${esc(chief.role)}</p><p class="q">이렇게 말해 보세요 · “${esc(chief.example)}”</p><div class="acts"><button class="btn pri" data-act="hire" data-name="${esc(chief.name)}">총괄 비서에게 맡기기</button></div></div>` : ''}
  ${teams.map((tm) => `<div class="teamhead">${esc(tm)}</div><div class="staffgrid">${main.filter((s) => (s.team || '') === tm).map(card).join('')}</div>`).join('') || '<p class="empty">직원 목록을 못 읽었어요.</p>'}
  ${helpers.length ? `<details class="card" style="margin-top:16px"><summary><b>뒤에서 돕는 직원 ${helpers.length}명</b> <span class="crumb">직접 부를 일은 적고, AI가 만들고 점검할 때 알아서 써요</span></summary><div class="staffgrid" style="margin-top:12px">${helpers.map(card).join('')}</div></details>` : ''}
  ${(S.oss || []).length ? `<div class="teamhead" style="margin-top:28px">같이 쓰면 좋은 오픈소스</div><p class="md" style="margin-bottom:10px">대표가 실제로 써 온 무료 도구예요. AI에게 말하면 확인을 받고 깔아서 써요. 라이선스 주의가 있는 건 표시해 뒀어요.</p><div class="staffgrid">${S.oss.map((o) => `<div class="card staff"><h4>${esc(o.name)}<span class="r">${esc(o.area || '')}</span></h4><p>${esc(o.what || '')}</p>${o.license ? `<p class="crumb">라이선스: ${esc(o.license)}${o.note ? ' · ' + esc(o.note) : ''}</p>` : ''}<div class="acts">${o.say ? `<button class="btn dark" data-act="osshire" data-name="${esc(o.name)}">이걸로 맡기기</button>` : ''}${o.url ? `<a class="btn" href="#" data-act="openurl" data-url="${esc(o.url)}">사이트</a>` : ''}</div></div>`).join('')}</div>` : ''}</div>`;
}

// ── 설정 ──
function settingsView() {
  const tabs = [['me', '내 정보'], ['ai', 'AI 로그인'], ['conn', '연결'], ['skills', '내 PC 스킬'], ['rules', '규칙'], ['learn', '자동 점검']];
  const nav = `<div class="nav">${tabs.map(([k, n]) => `<button class="ni ${S.setTab === k ? 'on' : ''}" data-act="settab" data-tab="${k}">${n}${k === 'learn' && S.st.pending ? `<span class="c num">${S.st.pending}</span>` : ''}</button>`).join('')}</div>`;
  let page = '';
  const back = `<button class="btn mob-only" data-act="pane" data-p="nav" style="margin-bottom:12px">${ic('back', 's')}설정</button>`;
  if (S.setTab === 'me') page = `<h2>내 정보</h2><p class="lead">허브 화면에 보이는 이름이에요. 이 PC 밖으로 나가지 않아요.</p><form data-form="me" class="card" style="max-width:480px;display:flex;flex-direction:column;gap:10px"><div class="field"><input name="me" value="${esc(S.st.me)}" placeholder="이름" aria-label="이름"></div><button class="btn dark" style="align-self:flex-start">저장</button></form>`;
  if (S.setTab === 'ai') page = `<h2>AI 로그인</h2><p class="lead">허브는 내 구독으로 일해요. 둘 중 하나만 로그인돼 있어도 돼요. 로그인을 누르면 이 PC에 브라우저 로그인 창이 열려요.</p>${S.auth ? [['codex', 'Codex (ChatGPT 구독)'], ['claude', 'Claude (Claude 구독)']].map(([w, n]) => { const a = S.auth[w] || {}; return `<div class="card" style="max-width:640px;margin-bottom:12px"><h4>${n}<span class="r"><span class="st ${a.ok ? 'work' : 'wait'}">${a.ok ? '로그인됨' : a.installed ? '로그인 필요' : '프로그램 없음'}</span></span></h4><p class="md">${esc(a.text || '')}</p><div class="acts">${a.installed ? `<button class="btn ${a.ok ? '' : 'pri'}" data-act="authlogin" data-who="${w}">${a.ok ? '다시 로그인' : '로그인'}</button>${a.ok ? `<button class="btn" data-act="authlogout" data-who="${w}">로그아웃</button>` : ''}` : '<span class="crumb">강사에게 설치를 부탁하세요.</span>'}</div></div>`; }).join('') + `<button class="btn" data-act="authrefresh">${ic('refresh', 's')}다시 확인</button>` + pcCard(S.auth.pc) : '<p class="empty">확인하는 중…</p>'}`;
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
    <ol class="steps">${(x.steps || []).map((t) => `<li>${esc(t)}</li>`).join('')}</ol>
    ${ks.map((k) => `<form class="keyrow" data-form="key"><input type="hidden" name="name" value="${esc(k.name)}"><label>${esc(k.label)}</label><div class="field"><input type="password" name="value" autocomplete="off" placeholder="${k.has ? '저장돼 있어요 · 바꾸려면 새로 붙여 넣기' : '여기에 붙여 넣기'}"></div><button class="btn dark">저장</button>${k.has ? `<button type="button" class="btn" data-act="keydel" data-name="${esc(k.name)}">지우기</button>` : ''}</form>`).join('')}
    <div class="acts">${ks.length ? `<button class="btn pri" data-act="connhelp" data-id="${esc(x.id)}">AI에게 연결 도와 달라</button>` : ''}<a class="btn" href="#" data-act="openurl" data-url="${esc(x.doc)}">공식 안내</a></div></div>`; };
  return `<h2>연결</h2><p class="lead">AI 직원이 바깥 서비스에 올리고 보내려면 내 계정의 키가 필요해요. 흐름은 다 들어 있고 키만 비어 있어요. 키는 이 PC 금고에만 저장되고 대화·파일에 남지 않아요.</p>${c.connections.map(card).join('')}`;
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
   <p style="margin-top:6px">${esc(c.text)}</p>${(c.evidence || []).map((e) => `<p class="q">내가 한 말 · “${esc(e)}”</p>`).join('')}
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
  return `${parts.join('')}<span class="sp"></span><span>AI 학교 허브${S.upd?.current && S.upd.current !== 'dev' ? ` v${esc(S.upd.current)}` : ''}</span>`;
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
  const forms = [...document.querySelectorAll('[data-form=newtask]')].map((f) => [f.dataset.where, f.elements.title.value, f.elements.text.value, f.elements.runtime.value]);
  const foc = document.activeElement; const focSel = foc?.dataset?.dirq ? `[data-dirq="${foc.dataset.dirq}"]` : foc?.form?.dataset?.form === 'newtask' ? `[data-form=newtask][data-where="${foc.form.dataset.where}"] [name="${foc.name}"]` : null;
  const body = S.view === 'today' ? `<div class="body">${todayView()}</div>` : S.view === 'work' ? workView() : S.view === 'staff' ? `<div class="body">${staffView()}</div>` : settingsView();
  $('#root').innerHTML = topbar() + updBar() + body + `<div class="sb" id="sb">${sbHtml()}</div>` + mtab() + (!S.st.me ? meModal() : '');
  if (!S.prefill) for (const [w, ti, tx, rt] of forms) { const f = $(`[data-form=newtask][data-where="${w}"]`); if (f) { const E = f.elements; E.title.value = ti; E.text.value = tx; if (!E.runtime.querySelector(`option[value="${rt}"]`)?.disabled) E.runtime.value = rt; } }
  S.prefill = null;
  if (focSel) { const el = $(focSel); if (el) { el.focus(); try { const n = el.value.length; el.setSelectionRange(n, n); } catch {} } }
  const c = $('#chat'); if (c) c.scrollTop = c.scrollHeight;
  const ta = $('[data-form=send] textarea'); if (ta && draft) ta.value = draft;
  placeNative();
}
function meModal() { return `<div class="modal"><form class="card" data-form="me"><h4>처음 오셨어요</h4><p class="md" style="margin-bottom:10px">허브에서 부를 이름을 적어 주세요. 이 PC 밖으로 나가지 않아요.</p><div class="field" style="margin-bottom:12px"><input name="me" placeholder="이름" aria-label="이름" required></div><button class="btn dark">시작</button></form></div>`; }

// ── 누르기 ──
async function reveal(what, root) { const r = await api(root ? '/api/reveal' : `/api/tasks/${S.taskId}/reveal`, { method: 'POST', body: { what } }); if (!r.ok) toast(r.msg || '열지 못했어요'); }
document.addEventListener('click', async (e) => {
  const b = e.target.closest('[data-act]'); if (!b || b.tagName === 'SELECT' || b.type === 'checkbox') return;
  const a = b.dataset.act;
  try {
    if (a === 'go') { S.view = b.dataset.v; if (S.view === 'work') S.pane = S.task ? S.pane : 'list'; if (S.view === 'settings') { S.pane = 'nav'; loadSetTab(); } if (S.view === 'staff' && !S.staff) { S.staff = await api('/api/staff'); S.oss = await api('/api/open-source').catch(() => []); } if (S.view === 'today') S.my = await api('/api/my').catch(() => S.my); render(); }
    else if (a === 'update') { await api('/api/update', { method: 'POST' }); S.upd.updating = '시작'; render(); }
    else if (a === 'updlater') { S.updHide = S.upd?.latest; render(); }
    else if (a === 'settings') { S.view = 'settings'; if (b.dataset.tab) { S.setTab = b.dataset.tab; S.pane = 'page'; } else S.pane = 'nav'; render(); loadSetTab(); }
    else if (a === 'settab') { S.setTab = b.dataset.tab; S.pane = 'page'; render(); loadSetTab(); }
    else if (a === 'open') { if (b.dataset.id) await openTask(b.dataset.id); }
    else if (a === 'dirtoggle') { const w = b.dataset.where; const d = (S.dir[w] = S.dir[w] || {}); d.open = !d.open; render(); if (d.open) { setTimeout(() => $(`[data-dirq="${w}"]`)?.focus(), 30); loadDirs(w, d.q || ''); } }
    else if (a === 'dirpick') { const w = b.dataset.where; const d = (S.dir[w] = S.dir[w] || {}); d.path = b.dataset.path; d.open = false; render(); }
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
    else if (a === 'hire') { const s = (S.staff?.staff || []).find((x) => x.name === b.dataset.name); S.view = 'today'; S.prefill = { where: 'today', title: s ? `${s.name} · ${s.example}`.slice(0, 40) : '', text: s ? `${s.name}에게 맡길게. ${s.example}` : '' }; render(); setTimeout(() => { const ta = $('[data-form=newtask][data-where=today] textarea'); if (ta) { ta.focus(); ta.select(); } }, 30); }
    else if (a === 'myinterview') { const r = await api('/api/my/interview', { method: 'POST' }); await load(); await openTask(r.task); }
    else if (a === 'myreveal') { const r = await api('/api/my/reveal', { method: 'POST' }); if (!r.ok) toast(r.msg || '열지 못했어요'); }
    else if (a === 'connhelp') { const r = await api('/api/connections/help', { method: 'POST', body: { id: b.dataset.id } }); await load(); await openTask(r.task); }
    else if (a === 'keydel') { if (!confirm('저장한 키를 지울까요?')) return; await api('/api/connections/key', { method: 'POST', body: { name: b.dataset.name, remove: true } }); S.conns = await api('/api/connections'); render(); toast('지웠어요'); }
    else if (a === 'osshire') { const o = (S.oss || []).find((x) => x.name === b.dataset.name); S.view = 'today'; S.prefill = { where: 'today', title: `${o.name} 써 보기`, text: o.say }; render(); }
    else if (a === 'authlogin' || a === 'authlogout') { const r = await api(`/api/auth/${b.dataset.who}/${a === 'authlogin' ? 'login' : 'logout'}`, { method: 'POST' }); toast(r.msg); }
    else if (a === 'authrefresh') { S.auth = null; render(); S.auth = await api('/api/auth'); await load(); }
    else if (a === 'scan') { S.scanBusy = true; render(); S.scan = await api('/api/skills/scan', { method: 'POST' }); S.scanBusy = false; render(); }
    else if (a === 'learnscan') { S.learnBusy = true; render(); await api('/api/learn/scan', { method: 'POST', body: { days: 7 } }); }
    else if (a === 'decide') { const r = await api('/api/learn/decide', { method: 'POST', body: { id: b.dataset.id, choice: b.dataset.c } }); toast(r.choice === 'discard' ? '버렸어요' : r.ok ? '넣었어요' : (r.msg || '넣지 못했어요')); S.pending = await api('/api/learn/pending'); S.rules = null; await load(); }
  } catch (err) { toast(err.message); S.scanBusy = false; render(); }
});
document.addEventListener('change', async (e) => { const el = e.target; if (el.dataset.act === 'consent') { await api('/api/learn/consent', { method: 'POST', body: { on: el.checked } }); await load(); } });
document.addEventListener('input', (e) => { const el = e.target; if (el.dataset.dirq) { clearTimeout(dirTimer); const w = el.dataset.dirq, v = el.value; dirTimer = setTimeout(() => loadDirs(w, v), 180); } });
document.addEventListener('keydown', (e) => {
  if (e.target.dataset?.dirq && e.key === 'Enter') { e.preventDefault(); const first = document.querySelector(`[data-dirlist="${e.target.dataset.dirq}"] .dirrow:nth-child(2)`); if (first) first.click(); return; }
  if (e.target.matches('[data-form=send] textarea') && e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); e.target.form.requestSubmit(); }
});
// 미리보기 폭 끌어서 바꾸기
document.addEventListener('pointerdown', (e) => {
  if (e.target.dataset?.drag !== 'side') return; e.preventDefault();
  const bodyEl = e.target.closest('.body'); const move = (ev) => { const w = Math.max(320, Math.min(innerWidth - 560, innerWidth - ev.clientX)); S.sideW = w; bodyEl.style.setProperty('--side-w', w + 'px'); placeNative(); };
  const up = () => { removeEventListener('pointermove', move); removeEventListener('pointerup', up); try { localStorage.setItem('sideW', String(S.sideW)); } catch {} };
  addEventListener('pointermove', move); addEventListener('pointerup', up);
});
try { const w = Number(localStorage.getItem('sideW')); if (w) S.sideW = w; } catch {}
document.addEventListener('submit', async (e) => {
  e.preventDefault(); const f = e.target; const d = Object.fromEntries(new FormData(f)); const k = f.dataset.form;
  try {
    if (k === 'search') { S.q = d.q; S.res = d.q ? await api(`/api/search?q=${encodeURIComponent(d.q)}`) : []; render(); }
    else if (k === 'newtask') { if (!d.runtime) return toast('먼저 설정 › AI 로그인에서 로그인해 주세요'); const t = await api('/api/tasks', { method: 'POST', body: d }); f.reset(); S.dir[f.dataset.where] = {}; await load(); await openTask(t.id); }
    else if (k === 'send') { if (!d.text.trim()) return; f.querySelector('textarea').value = ''; await api(`/api/tasks/${S.taskId}/send`, { method: 'POST', body: { text: d.text } }); await openTask(S.taskId, true); render(); }
    else if (k === 'url') { let u = d.u.trim(); if (!u) return; if (!/^(https?:|\/)/.test(u)) u = /\.\w{1,5}$/.test(u) && !/^www\./.test(u) && S.files.some((x) => x.name === u) ? fileUrl(u) : 'https://' + u; await setPreview(u); render(); }
    else if (k === 'me') { await api('/api/me', { method: 'POST', body: d }); await load(); const a = S.st.auth; if (a && !a.codex && !a.claude) { S.view = 'settings'; S.setTab = 'ai'; S.pane = 'page'; render(); loadSetTab(); toast('먼저 AI 로그인을 해 주세요'); } else toast('오늘 탭의 새로 맡기기에서 첫 일을 맡겨 보세요'); }
    else if (k === 'key') { if (!d.value.trim()) return toast('키를 붙여 넣어 주세요'); await api('/api/connections/key', { method: 'POST', body: { name: d.name, value: d.value } }); f.reset(); S.conns = await api('/api/connections'); render(); toast('이 PC 금고에 저장했어요'); }
    else if (k === 'register') { const names = [...f.querySelectorAll('input[name=n]:checked')].map((x) => x.value); if (!names.length) return toast('넣을 스킬을 골라 주세요'); toast('허브에 넣는 중…'); const r = await api('/api/skills/register', { method: 'POST', body: { names } }); toast(r.ok ? `${names.length}개를 허브에 넣었어요` : '넣지 못했어요'); S.scan = await api('/api/skills/scan', { method: 'POST' }); render(); }
  } catch (err) { toast(err.message); }
});
async function loadSetTab() {
  try {
    if (S.setTab === 'rules' && !S.rules) S.rules = await api('/api/rules');
    if (S.setTab === 'learn') S.pending = await api('/api/learn/pending');
    if (S.setTab === 'ai' && !S.auth) S.auth = await api('/api/auth');
    if (S.setTab === 'conn') S.conns = await api('/api/connections');
    render();
  } catch (err) { toast(err.message); }
}

// 실시간
const es = new EventSource('/api/events');
es.onmessage = async (m) => {
  const ev = JSON.parse(m.data);
  if (ev.type === 'msg' && ev.task === S.taskId && S.task) { S.task.messages.push(ev.msg); if (ev.msg.kind === 'file' || ev.msg.text?.startsWith('파일')) S.files = await api(`/api/tasks/${S.taskId}/files`); render(); }
  if (ev.type === 'status') { await load(); if (ev.task === S.taskId && ev.status !== 'working') { S.files = await api(`/api/tasks/${S.taskId}/files`); const h = S.files.find((f) => /\.html?$/i.test(f.name)); if (h && !S.previewSrc) await setPreview(fileUrl(h.name)); render(); loadUsage(); } }
  if (ev.type === 'update') {
    if (ev.step === 'fail') { if (S.upd) S.upd.updating = null; render(); toast(`업데이트하지 못했어요. ${ev.msg || ''}`); }
    else if (ev.step === 'restart') { if (S.upd) S.upd.updating = '다시 켜는 중'; render(); waitRestart(ev.version); }
    else { if (S.upd) S.upd.updating = ev.step; render(); }
  }
  if (ev.type === 'auth') { if (S.st) { S.st.auth = { codex: ev.codex, claude: ev.claude }; S.auth = null; if (S.view === 'settings' && S.setTab === 'ai') loadSetTab(); else render(); } }
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
load().then(route).then(loadUsage).then(checkUpdate); setInterval(loadUsage, 120000); setInterval(checkUpdate, 6 * 3600e3);
