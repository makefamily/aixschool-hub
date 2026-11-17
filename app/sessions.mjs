// 이 PC의 Claude·Codex 대화 기록 읽기 (읽기 전용, 복사·수정 없음). 맥·윈도우 공통.
// - 가져오기 목록: ~/.claude/projects/*/*.jsonl, ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl
// - 작업 폴더 후보: 최근 대화의 폴더 + ~/Projects 같은 흔한 자리
// - 맥락 크기: 대화 기록 끝부분의 마지막 사용량
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

const HOME = os.homedir();
export const claudeRoot = () => path.join(HOME, '.claude', 'projects');
export const personalCodexHome = () => path.join(HOME, '.codex');
export const CLAUDE_WINDOW = 1_000_000; // Claude 응답 끝(result)에 실제 값이 오면 그걸 쓴다

function readPart(file, n, fromEnd) {
  let fd;
  try {
    fd = fs.openSync(file, 'r');
    const size = fs.fstatSync(fd).size;
    const len = Math.min(n, size);
    const buf = Buffer.alloc(len);
    fs.readSync(fd, buf, 0, len, fromEnd ? size - len : 0);
    let s = buf.toString('utf8');
    if (fromEnd && len < size) s = s.slice(s.indexOf('\n') + 1);
    if (!fromEnd && len < size) s = s.slice(0, s.lastIndexOf('\n'));
    return s;
  } catch { return ''; } finally { if (fd !== undefined) try { fs.closeSync(fd); } catch {} }
}
const lines = (s) => s.split('\n').filter(Boolean).map((l) => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean);
// 사람이 쓴 말이 아닌 것(규칙 주입·명령 표시·허브 머리말)
const NOISE = /^\s*(<|# AGENTS\.md|Caveat:|\[Request interrupted|Name this chat from|This session is being continued from a previous conversation)/;
// 임시 폴더에서 돈 대화(도구 확인용 등)는 뺀다
const TMP = /^(\/private\/tmp|\/tmp|\/var\/folders|\/private\/var\/folders)\//;
const realDir = (p) => { try { return fs.realpathSync.native(p); } catch { return p; } };
const clean = (s) => String(s || '').replace(/&#x20;|&nbsp;/g, ' ').replace(/\s+/g, ' ').trim();
const claudeText = (c) => typeof c === 'string' ? c : Array.isArray(c) ? c.filter((x) => x.type === 'text').map((x) => x.text).join(' ') : '';
const codexText = (c) => Array.isArray(c) ? c.map((x) => x.text || '').join('') : String(c || '');

// ── 대화 하나 요약 ──
function claudeInfo(file) {
  let cwd = null, title = '', name = '';
  for (const o of lines(readPart(file, 768 << 10))) {
    if (o.type === 'ai-title' && o.aiTitle) name = String(o.aiTitle);
    if (o.cwd && !cwd) cwd = o.cwd;
    if (o.isSidechain) return null;
    // claude -p(스크립트·자동화·허브 자체 실행)는 사람이 이어 할 대화가 아니다
    if (o.entrypoint === 'sdk-cli' && !process.env.AIHUB_IMPORT_EXEC) return null;
    if (!title && o.type === 'user' && !o.isMeta) { const t = clean(claudeText(o.message?.content)); if (t && !NOISE.test(t)) title = t; }
    if (cwd && title) break;
  }
  if (!title || !cwd) return null;
  return { runtime: 'claude', id: path.basename(file, '.jsonl'), cwd, title: title.slice(0, 90), name, file };
}
function codexInfo(file) {
  let id = null, cwd = null, source = '', title = '', fallback = '';
  for (const o of lines(readPart(file, 768 << 10))) {
    const p = o.payload || {};
    if (o.type === 'session_meta') { id = p.id; cwd = p.cwd; source = typeof p.source === 'string' ? p.source : Object.keys(p.source || {})[0] || ''; }
    if (!title && o.type === 'event_msg' && p.type === 'user_message') { const t = clean(p.message); if (t && !NOISE.test(t)) title = t; }
    if (!fallback && o.type === 'response_item' && p.type === 'message' && p.role === 'user') { const t = clean(codexText(p.content)); if (t && !NOISE.test(t)) fallback = t; }
    if (id && title) break;
  }
  title = title || fallback;
  // 자동 실행(exec)·하위 에이전트 대화는 목록에서 뺀다
  if (!id || !cwd || !title || source === 'subagent' || (source === 'exec' && !process.env.AIHUB_IMPORT_EXEC)) return null;
  return { runtime: 'codex', id, cwd, title: title.slice(0, 90), name: codexNames().get(id) || '', file };
}

// ── 맥락 크기(대화 끝부분의 마지막 사용량) ──
export function contextOf(file, runtime) {
  const tail = lines(readPart(file, 1536 << 10, true));
  for (let i = tail.length - 1; i >= 0; i--) {
    const o = tail[i];
    if (runtime === 'claude' && o.type === 'assistant' && !o.isSidechain && o.message?.usage) {
      const u = o.message.usage;
      const tokens = (u.input_tokens || 0) + (u.cache_read_input_tokens || 0) + (u.cache_creation_input_tokens || 0);
      return mkCtx(tokens, CLAUDE_WINDOW);
    }
    if (runtime === 'codex' && o.type === 'event_msg' && o.payload?.type === 'token_count' && o.payload.info?.last_token_usage) {
      const info = o.payload.info;
      return mkCtx(info.last_token_usage.total_tokens || info.last_token_usage.input_tokens || 0, info.model_context_window || 272000);
    }
  }
  return null;
}
export const mkCtx = (tokens, window) => ({ tokens, window, pct: window ? Math.min(100, Math.round((tokens / window) * 100)) : null, at: new Date().toISOString() });

// 이어볼 수 있게 원래 대화의 마지막 몇 마디(글만)
export function lastTurns(file, runtime, n = 4) {
  const out = [];
  for (const o of lines(readPart(file, 1536 << 10, true))) {
    const p = o.payload || {};
    if (runtime === 'claude' && !o.isSidechain && !o.isMeta && (o.type === 'user' || o.type === 'assistant')) {
      const t = claudeText(o.message?.content).trim();
      if (t && !NOISE.test(t)) out.push({ role: o.type === 'user' ? 'me' : 'ai', text: t });
    }
    if (runtime === 'codex' && o.type === 'response_item' && p.type === 'message' && (p.role === 'user' || p.role === 'assistant')) {
      const t = codexText(p.content).trim();
      if (t && !NOISE.test(t)) out.push({ role: p.role === 'user' ? 'me' : 'ai', text: t });
    }
  }
  return out.slice(-n).map((m) => ({ ...m, text: m.text.length > 1500 ? m.text.slice(0, 1500) + ' …(뒷부분 생략)' : m.text }));
}

// ── 최근 N일 대화 목록 ──
let cache = { at: 0, days: 0, list: [] };
export function recentSessions(days = 7, { exclude = '' } = {}) {
  if (Date.now() - cache.at < 60_000 && cache.days === days) return cache.list;
  const since = Date.now() - days * 86400_000;
  const out = [];
  const add = (info, st) => { if (info && !TMP.test(info.cwd) && !info.cwd.startsWith(os.tmpdir()) && !(exclude && info.cwd.startsWith(exclude))) out.push({ ...info, mtime: st.mtime.toISOString(), size: st.size }); };
  try {
    for (const d of fs.readdirSync(claudeRoot(), { withFileTypes: true })) {
      if (!d.isDirectory()) continue;
      const dir = path.join(claudeRoot(), d.name);
      let names; try { names = fs.readdirSync(dir); } catch { continue; }
      for (const f of names) {
        if (!f.endsWith('.jsonl')) continue;
        const file = path.join(dir, f); let st; try { st = fs.statSync(file); } catch { continue; }
        if (st.mtimeMs >= since && st.size > 0) add(claudeInfo(file), st);
      }
    }
  } catch {}
  // Codex는 날짜 폴더에 쌓이고, 오래된 대화를 이어 쓰면 옛 날짜 폴더 파일이 갱신된다 → 최근 60일 폴더까지 본다
  const sroot = path.join(personalCodexHome(), 'sessions');
  for (let k = 0; k <= 60; k++) {
    const d = new Date(Date.now() - k * 86400_000);
    const dir = path.join(sroot, String(d.getFullYear()), String(d.getMonth() + 1).padStart(2, '0'), String(d.getDate()).padStart(2, '0'));
    let names; try { names = fs.readdirSync(dir); } catch { continue; }
    for (const f of names) {
      if (!/^rollout-.*\.jsonl$/.test(f)) continue;
      const file = path.join(dir, f); let st; try { st = fs.statSync(file); } catch { continue; }
      if (st.mtimeMs >= since && st.size > 0) add(codexInfo(file), st);
    }
  }
  out.sort((a, b) => b.mtime.localeCompare(a.mtime));
  cache = { at: Date.now(), days, list: out };
  return out;
}

// 대화 ID로 원문 파일 찾기
export function findSessionFile(runtime, id, codexHomeDir = personalCodexHome()) {
  if (!id) return null;
  if (runtime === 'claude') {
    try { for (const d of fs.readdirSync(claudeRoot())) { const f = path.join(claudeRoot(), d, `${id}.jsonl`); if (fs.existsSync(f)) return f; } } catch {}
    return null;
  }
  const stack = [path.join(codexHomeDir, 'sessions')];
  while (stack.length) {
    const d = stack.pop(); let ents; try { ents = fs.readdirSync(d, { withFileTypes: true }); } catch { continue; }
    for (const e of ents) { const p = path.join(d, e.name); if (e.isDirectory()) stack.push(p); else if (e.name.endsWith('.jsonl') && e.name.includes(id)) return p; }
  }
  return null;
}

// ── 작업 폴더 후보 ──
export function expandDir(p) {
  let s = String(p || '').trim().replace(/^["']|["']$/g, '');
  if (!s) return '';
  if (s === '~' || s.startsWith('~/') || s.startsWith('~\\')) s = path.join(HOME, s.slice(1));
  return path.resolve(s);
}
export const isDir = (p) => { try { return fs.statSync(p).isDirectory(); } catch { return false; } };
function children(dir) { try { return fs.readdirSync(dir, { withFileTypes: true }).filter((e) => e.isDirectory() && !e.name.startsWith('.')).map((e) => path.join(dir, e.name)); } catch { return []; } }

export function dirCandidates(q = '', { recent = [], exclude = '' } = {}) {
  const seen = new Map();
  const put = (p0, extra) => { const p = p0 && isDir(p0) ? realDir(p0) : p0; if (!p || TMP.test(p) || (exclude && p.startsWith(exclude)) || !isDir(p)) return; const k = process.platform === 'win32' ? p.toLowerCase() : p; if (!seen.has(k)) return seen.set(k, { path: p, name: path.basename(p) || p, ...extra }); const cur = seen.get(k); for (const [kk, v] of Object.entries(extra)) if (cur[kk] === undefined) cur[kk] = v; };
  const query = String(q || '').trim();
  const typed = /^(~|\/|[A-Za-z]:[\\/]|\\\\)/.test(query) ? expandDir(query) : '';
  if (typed && isDir(typed)) put(typed, { typed: true });
  else if (typed) for (const c of children(path.dirname(typed))) if (path.basename(c).toLowerCase().startsWith(path.basename(typed).toLowerCase())) put(c, { typed: true }); // 경로를 중간까지만 쳤을 때
  for (const r of recent) put(r.path, { used: r.at });
  for (const s of recentSessions(7, { exclude })) put(s.cwd, { lastTalk: s.mtime });
  const roots = [path.join(HOME, 'Projects'), path.join(HOME, 'projects'), path.join(HOME, 'orca', 'workspaces'), path.join(HOME, 'Documents'), path.join(HOME, 'Desktop')];
  if (process.platform === 'win32') roots.push('C:\\Projects', 'D:\\Projects');
  for (const r of roots) for (const c of children(r)) { put(c, {}); if (r.endsWith('workspaces')) for (const cc of children(c)) put(cc, {}); }
  let list = [...seen.values()];
  if (query && !typed) { const ql = query.toLowerCase(); list = list.filter((d) => d.path.toLowerCase().includes(ql)); }
  else if (typed) list = list.filter((d) => d.typed || d.path.toLowerCase().startsWith(typed.toLowerCase()));
  const when = (d) => d.used || d.lastTalk || '';
  list.sort((a, b) => (b.typed ? 1 : 0) - (a.typed ? 1 : 0) || when(b).localeCompare(when(a)) || a.path.localeCompare(b.path));
  return list.slice(0, 40).map((d) => ({ ...d, home: d.path.startsWith(HOME) ? '~' + d.path.slice(HOME.length) : d.path }));
}

// ── 어떻게 끝났나(이어서 할 일 고르기) ──
// stopped: 답 없이 끊김·중단·오류·작업 중 멈춤 / waiting: AI가 질문·확인 요청으로 끝남(내 답 차례)
// live: 지금 다른 창에서 쓰는 중(최근 10분 갱신) / handed: 인계 문서를 쓰고 끝남(다른 세션이 이어감) / done: 결과 보고로 끝남
const ASK = /(\?|할까요|드릴까요|볼까요|괜찮을까요|좋을까요|맞을까요|어떨까요|정해 ?주세요|정해 ?주시면|골라 ?주세요|답해 ?주시면|답해 ?주세요|알려 ?주세요|선택해 ?주세요|승인해 ?주시면|승인하시면|알려 ?주시면|말씀해 ?주시면|결정해 ?주세요|확인해 ?주시면|원하시면|직접 해 ?주세요)/;
function asksBack(text) {
  // 끝의 "다음 할 일" 안내는 빼고, 마지막 문단 두세 줄만 본다
  const t = String(text || '').replace(/\n+(\*\*)?다음 할 일[\s\S]*$/, '').trim();
  return ASK.test(t.split('\n').filter((l) => l.trim()).slice(-3).join('\n'));
}
const LIVE_MS = 10 * 60_000;
export function stateOf(s) {
  if (s.runtime === 'aside') return s.state || { kind: 'done' };
  // 파일 수정 시각은 믿지 않는다: Claude Code가 쉬는 동안에도 요약(away_summary) 같은 기록을 덧붙여 수십 개가 한꺼번에 바뀐다.
  // 마지막으로 사람·AI가 실제로 말한 시각을 쓴다.
  const tail = lines(readPart(s.file, 1024 << 10, true));
  let lastAt = 0, summary = '', aiName = '';
  for (let i = tail.length - 1; i >= 0; i--) {
    const o = tail[i]; const p = o.payload || {};
    if (!summary && o.type === 'system' && o.subtype === 'away_summary' && o.content) summary = String(o.content);
    const real = s.runtime === 'claude' ? (o.type === 'user' || o.type === 'assistant') && !o.isSidechain && !o.isCompactSummary : (o.type === 'response_item' && p.type === 'message') || (o.type === 'event_msg' && /^(user_message|agent_message|task_complete|turn_aborted|error)$/.test(p.type || ''));
    if (real && o.timestamp) { lastAt = new Date(o.timestamp).getTime() || 0; break; }
  }
  if (!lastAt) { try { lastAt = fs.statSync(s.file).mtimeMs; } catch {} }
  let ask = ''; // 마지막으로 사람이 한 말(제목은 첫 말이라 오래된 요청일 수 있다)
  for (let i = tail.length - 1; i >= 0; i--) {
    const o = tail[i]; const p = o.payload || {};
    if (!aiName && o.type === 'ai-title' && o.aiTitle) aiName = String(o.aiTitle);
    if (ask && (aiName || s.runtime !== 'claude')) break;
    if (ask) continue;
    if (s.runtime === 'claude' && o.type === 'user' && !o.isMeta && !o.isSidechain && !o.isCompactSummary) { const c = o.message?.content; if (!(Array.isArray(c) && c.some((x) => x.type === 'tool_result'))) { const t = clean(claudeText(c)); if (t && !NOISE.test(t)) ask = t; } }
    if (s.runtime === 'codex' && o.type === 'event_msg' && p.type === 'user_message') { const t = clean(p.message); if (t && !NOISE.test(t)) ask = t; }
    if (s.runtime === 'codex' && o.type === 'response_item' && p.type === 'message' && p.role === 'user') { const t = clean(codexText(p.content)); if (t && !NOISE.test(t)) ask = t; }
  }
  const live = Date.now() - lastAt < LIVE_MS;
  let r = null, handed = false;
  if (s.runtime === 'claude') {
    for (let i = tail.length - 1; i >= 0 && !r; i--) {
      const o = tail[i]; if (o.isSidechain) continue;
      if (o.type === 'assistant') {
        const c = o.message?.content || [];
        if (c.some((x) => x.type === 'tool_use' && /HANDOFF-[^"]*\.md/.test(JSON.stringify(x.input || {})))) handed = true;
        if (o.isApiErrorMessage) r = { kind: 'stopped', why: '오류로 멈춤' };
        else if (c.some((x) => x.type === 'tool_use')) r = { kind: 'stopped', why: '작업 도중 끊김' };
        else { const t = claudeText(c).trim(); if (t) r = asksBack(t) ? { kind: 'waiting', why: '내 답을 기다림', last: t } : { kind: 'done', why: '결과 보고로 끝남', last: t }; }
      } else if (o.type === 'user' && !o.isMeta && !o.isCompactSummary) {
        const c = o.message?.content; const t = claudeText(c).trim();
        if (/^\[Request interrupted/.test(t)) r = { kind: 'stopped', why: '중간에 멈춤' };
        else if (Array.isArray(c) && c.some((x) => x.type === 'tool_result')) r = { kind: 'stopped', why: '작업 도중 끊김' };
        else if (t && !NOISE.test(t)) r = { kind: 'stopped', why: '답 없이 끊김' };
      }
    }
    // 인계 문서는 마지막 답 직전 몇 턴 안에서 썼는지 본다
    if (!handed) handed = tail.slice(-40).some((o) => o.type === 'assistant' && (o.message?.content || []).some((x) => x.type === 'tool_use' && /HANDOFF-[^"]*\.md/.test(JSON.stringify(x.input || {}))));
  } else {
    for (let i = tail.length - 1; i >= 0 && !r; i--) {
      const o = tail[i]; const p = o.payload || {};
      if (o.type === 'event_msg' && p.type === 'turn_aborted') r = { kind: 'stopped', why: '중간에 멈춤' };
      else if (o.type === 'event_msg' && p.type === 'error') r = { kind: 'stopped', why: '오류로 멈춤' };
      else if (o.type === 'event_msg' && p.type === 'user_message') r = { kind: 'stopped', why: '답 없이 끊김' };
      else if (o.type === 'event_msg' && p.type === 'task_complete') { const t = String(p.last_agent_message || '').trim(); if (t) r = asksBack(t) ? { kind: 'waiting', why: '내 답을 기다림', last: t } : { kind: 'done', why: '결과 보고로 끝남', last: t }; }
      else if (o.type === 'response_item' && p.type === 'message' && p.role === 'assistant') { const t = codexText(p.content).trim(); if (t) r = asksBack(t) ? { kind: 'waiting', why: '내 답을 기다림', last: t } : { kind: 'done', why: '결과 보고로 끝남', last: t }; }
      else if (o.type === 'response_item' && /call$/.test(p.type || '')) r = { kind: 'stopped', why: '작업 도중 끊김' };
    }
    handed = tail.slice(-60).some((o) => /HANDOFF-[^"\\]*\.md/.test(JSON.stringify(o.payload?.input || o.payload?.arguments || '')));
  }
  r = r || { kind: 'done', why: '결과 보고로 끝남' };
  { const c = contextOf(s.file, s.runtime); if (c) r.ctx = c.pct; }
  r.at = new Date(lastAt).toISOString(); if (summary) r.summary = summary; if (ask) r.ask = ask; if (aiName) r.name = aiName;
  if (live) return { ...r, kind: 'live', why: '지금 다른 창에서 쓰는 중', was: r.kind };
  if (handed && r.kind !== 'stopped') return { ...r, kind: 'handed', why: '인계 문서를 쓰고 넘어감' };
  return r;
}

// Aside: CLI가 주는 목록(상태 포함). 사람이 직접 시작한 것만.
export function asideSessions(days = 7, run) {
  const out = [];
  let j; try { j = JSON.parse(run('aside', ['session', 'list', '--json'])); } catch { return out; }
  const since = Date.now() - days * 86400_000;
  for (const s of j.sessions || []) {
    if ((s.ephemeral && !process.env.AIHUB_IMPORT_EXEC) || s.incognito || s.trigger?.type !== 'user' || new Date(s.updatedAt).getTime() < since) continue;
    if (s.trigger?.source === 'cli' && !process.env.AIHUB_IMPORT_EXEC) continue; // 다른 AI·스크립트가 터미널에서 시킨 것
    const file = asideFile(s.id);
    const last = file ? asideLastAnswer(file) : '';
    const state = s.status === 'running' ? { kind: 'live', why: 'Aside에서 지금 도는 중' } : s.status === 'interrupted' || s.status === 'error' || s.status === 'failed' ? { kind: 'stopped', why: s.status === 'interrupted' ? '중간에 멈춤' : '오류로 멈춤' } : last && asksBack(last) ? { kind: 'waiting', why: '내 답을 기다림', last } : { kind: 'done', why: '결과 보고로 끝남', last };
    out.push({ runtime: 'aside', id: s.id, cwd: '', file, title: String(s.title || '').slice(0, 90), mtime: new Date(s.updatedAt).toISOString(), unread: !!(s.readAt && s.readAt < s.updatedAt), state });
  }
  return out;
}

const asideRoot = () => path.join(HOME, '.aside', 'u', '0', 'sessions');
let asideIdx = { at: 0, map: new Map() };
export function asideFile(id) {
  if (Date.now() - asideIdx.at > 60_000) { asideIdx = { at: Date.now(), map: new Map() }; try { for (const d of fs.readdirSync(asideRoot())) { const k = d.slice(d.indexOf('_') + 1); asideIdx.map.set(k, d); } } catch {} }
  const d = asideIdx.map.get(id); if (!d) return null;
  const f = path.join(asideRoot(), d, 'messages.jsonl'); return fs.existsSync(f) ? f : null;
}
const asideText = (c) => Array.isArray(c) ? c.filter((x) => x.type === 'text').map((x) => x.text).join('') : typeof c === 'string' ? c : '';
function asideLastAnswer(file) { const L = lines(readPart(file, 512 << 10, true)); for (let i = L.length - 1; i >= 0; i--) if (L[i].role === 'assistant') { const t = asideText(L[i].content).trim(); if (t) return t; } return ''; }
export function asideTurns(file, n = 4) {
  const out = [];
  for (const o of lines(readPart(file, 1024 << 10, true))) if (o.role === 'user' || o.role === 'assistant') { const t = asideText(o.content).trim(); if (t && !NOISE.test(t)) out.push({ role: o.role === 'user' ? 'me' : 'ai', text: t.length > 1500 ? t.slice(0, 1500) + ' …(뒷부분 생략)' : t }); }
  return out.slice(-n);
}

// Codex 앱이 붙인 대화 제목(session_index.jsonl, 뒤에 적힌 게 최신)
let cxNames = { at: 0, map: new Map() };
export function codexNames() {
  if (Date.now() - cxNames.at < 60_000) return cxNames.map;
  const map = new Map();
  try { for (const o of lines(fs.readFileSync(path.join(personalCodexHome(), 'session_index.jsonl'), 'utf8'))) if (o.id && o.thread_name) map.set(o.id, String(o.thread_name)); } catch {}
  cxNames = { at: Date.now(), map };
  return map;
}
