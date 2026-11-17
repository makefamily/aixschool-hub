// AI 학교 허브 서버 — 외부 패키지 없음(Node 20+). 맥·윈도우 공통.
// 실행: node app/server.mjs   (포트 7710, 이 PC 안에서만 열림)
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { spawn, spawnSync } from 'node:child_process';
import { REPO, PLATFORM, hubHome, codexHome, workRoot, codexCommand, codexEnv, claudeCommand, asideCommand, cliSpawnArgs, pcCheck, modelArgs, myDir, myStatus, ensureMy } from '../tools/lib.mjs';
import * as keys from '../tools/keys.mjs';
import * as learn from './learn.mjs';
import * as sess from './sessions.mjs';

// 허브를 다른 AI 창(Orca·Claude Code 터미널)에서 켰을 때 따라온 그 창의 표시를 지운다.
// 남겨 두면 허브가 돌린 대화가 사람이 연 대화처럼 기록되고, 하던 일 목록에 섞인다.
for (const k of Object.keys(process.env)) if (/^(CLAUDECODE|CLAUDE_CODE_|ORCA_)/.test(k)) delete process.env[k];
const PORT = Number(process.env.AIHUB_PORT || 7710);
const PUB = path.join(REPO, 'app', 'public');
const TASKS = path.join(hubHome(), 'tasks');
fs.mkdirSync(TASKS, { recursive: true });
fs.mkdirSync(workRoot(), { recursive: true });

// ── 설정·토큰 ──────────────────────────────────────────────
const CONF = path.join(hubHome(), 'hub.json');
const conf = Object.assign({ me: '', team: 'my', learnConsent: false }, fs.existsSync(CONF) ? JSON.parse(fs.readFileSync(CONF, 'utf8').replace(/^\uFEFF/, '')) : {});
conf.team = 'my';
if (!conf.token) conf.token = crypto.randomBytes(16).toString('hex');
const saveConf = () => fs.writeFileSync(CONF, JSON.stringify(conf, null, 2));
saveConf();

const TEAMS = [{ id: 'my', name: '내 작업', icon: 'layers' }]; // 학생 허브는 팀이 없다. 작업 탭 하나만.

// ── 태스크 저장 ─────────────────────────────────────────────
const tfile = (id) => path.join(TASKS, `${id}.json`);
const readTask = (id) => JSON.parse(fs.readFileSync(tfile(id), 'utf8'));
const writeTask = (t) => fs.writeFileSync(tfile(t.id), JSON.stringify(t, null, 2));
const allTasks = () => fs.readdirSync(TASKS).filter((f) => f.endsWith('.json')).map((f) => { try { return JSON.parse(fs.readFileSync(path.join(TASKS, f), 'utf8')); } catch { return null; } }).filter(Boolean).sort((a, b) => (b.updated || '').localeCompare(a.updated || ''));
const slug = (s) => String(s).replace(/[\\/:*?"<>|\s]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40) || 'task';
// cwd를 주면 그 폴더에서 일한다. 안 주면 허브 work 아래 새 폴더.
function newTask({ title, team, runtime = 'codex', thread_id = null, from = null, handoff = null, cwd = '', extra = {} }) {
  const id = `${new Date().toISOString().slice(0, 10).replace(/-/g, '')}-${crypto.randomBytes(3).toString('hex')}`;
  let picked = false;
  if (cwd) {
    const d = sess.expandDir(cwd);
    if (!sess.isDir(d)) throw new Error(`작업 폴더가 없어요: ${cwd}`);
    cwd = d; picked = true; rememberDir(d);
  } else { cwd = path.join(workRoot(), `${id}-${slug(title)}`); fs.mkdirSync(cwd, { recursive: true }); }
  const t = { id, title, team: team || conf.team, runtime, thread_id, cwd, picked, owner: conf.me, from, handoff, status: 'idle', created: new Date().toISOString(), updated: new Date().toISOString(), messages: [], ...extra };
  writeTask(t);
  return t;
}
function rememberDir(d) { conf.recentDirs = [{ path: d, at: new Date().toISOString() }, ...(conf.recentDirs || []).filter((x) => x.path !== d)].slice(0, 15); saveConf(); }
// 결과물 목록: 허브 폴더는 맨 위 파일, 실제 저장소는 git으로 바뀐 파일(없으면 맨 위 파일)
function taskFiles(t) {
  const stat = (rel) => { try { const st = fs.statSync(path.join(t.cwd, rel)); return st.isFile() ? { name: rel, size: st.size, mtime: st.mtime } : null; } catch { return null; } };
  let names = null;
  if (t.picked) {
    const g = spawnSync('git', ['-C', t.cwd, 'status', '--porcelain=v1', '-uall'], { encoding: 'utf8', timeout: 8000 });
    if (g.status === 0) names = g.stdout.split('\n').filter(Boolean).map((l) => l.slice(3).replace(/^"|"$/g, '').split(' -> ').pop()).slice(0, 80);
  }
  if (!names) names = walkFiles(t.cwd);
  return names.map(stat).filter(Boolean).sort((a, b) => b.mtime - a.mtime);
}
// 작업 폴더 안 파일(하위 폴더 포함, 숨김·node_modules 제외, 최대 200개)
function walkFiles(root) {
  const out = []; const st = [''];
  while (st.length && out.length < 200) {
    const rel = st.pop(); let es; try { es = fs.readdirSync(path.join(root, rel), { withFileTypes: true }); } catch { continue; }
    for (const e of es) {
      if (e.name.startsWith('.') || e.name === 'node_modules' || e.name === '__pycache__') continue;
      const r = rel ? `${rel}/${e.name}` : e.name;
      if (e.isDirectory()) { if (r.split('/').length < 4) st.push(r); } else out.push(r);
    }
  }
  return out;
}
const codexHomeOf = (t) => (t.codexPersonal ? sess.personalCodexHome() : codexHome());

// ── 실시간 알림(SSE) ────────────────────────────────────────
const clients = new Set();
function emit(ev) { const s = `data: ${JSON.stringify(ev)}\n\n`; for (const c of clients) c.write(s); }

// ── AI 실행 ─────────────────────────────────────────────────
const running = new Map();
// 스킬을 불렀으면 한 줄로 보여 준다(같은 스킬은 한 번만)
function skillUsed(t, name) {
  if ((t.skillsUsed || []).includes(name)) return;
  t.skillsUsed = [...(t.skillsUsed || []), name];
  pushMsg(t, { role: 'log', kind: 'skill', skill: name, text: `스킬 사용 · ${skillLabel(name)}` });
}
let staffCache = null;
function skillLabel(name) {
  try { staffCache ||= JSON.parse(fs.readFileSync(path.join(REPO, 'skills', 'staff.json'), 'utf8')); } catch { staffCache = { staff: [] }; }
  const s = (staffCache.staff || []).find((x) => x.skill === name);
  if (s) return `${s.name} (${name})`;
  try { const m = JSON.parse(fs.readFileSync(path.join(REPO, 'skills', 'manifest.json'), 'utf8')).skills.find((x) => x.name === name); if (m) return `${m.desc} (${name})`; } catch {}
  return name;
}
function pushMsg(t, m) { t.messages.push({ ts: new Date().toISOString(), ...m }); t.updated = new Date().toISOString(); writeTask(t); emit({ type: 'msg', task: t.id, msg: t.messages.at(-1) }); }

function runCodexTurn(t, text) {
  let bin, pre; try { [bin, pre] = codexCommand(); } catch { setTimeout(() => finish(t.id, 1, 'ENOENT'), 0); return { kill() {} }; }
  const a = ['exec', ...modelArgs(), '--skip-git-repo-check', '--json'];
  if (t.thread_id) a.push('resume', t.thread_id, '-'); else a.push('-');
  const where = t.picked ? `작업 폴더는 실제 프로젝트 폴더(${t.cwd})다. 그 폴더의 규칙 파일(AGENTS.md 등)이 있으면 따른다.` : '결과물은 지금 작업 폴더에 파일로 만든다.';
  const prefix = t.thread_id ? '' : `[AI 학교 허브] 요청한 사람: ${conf.me || '수강생'}\n${where}\n\n`;
  // 가져온 개인 Codex 대화는 원래 자리(~/.codex)에서 그대로 이어 쓴다(복사 없음)
  const p = spawn(bin, [...pre, ...a], { cwd: t.cwd, env: t.codexPersonal ? process.env : codexEnv() });
  p.on('error', (e) => { p.spawnErr = String(e && e.code === 'ENOENT' ? 'ENOENT' : e); });
  p.stdin.on('error', () => {});
  p.stdin.end(prefix + text, 'utf8');
  let buf = '', err = '';
  p.stdout.setEncoding('utf8');
  p.stdout.on('data', (d) => {
    buf += d; let i;
    while ((i = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, i); buf = buf.slice(i + 1);
      let o; try { o = JSON.parse(line); } catch { continue; }
      if (o.type === 'thread.started' && !t.thread_id) { t.thread_id = o.thread_id; writeTask(t); }
      if (o.type === 'item.completed') {
        const it = o.item || {};
        if (it.type === 'agent_message') pushMsg(t, { role: 'ai', text: it.text });
        else if (it.type === 'command_execution') { const cmd = String(it.command || ''); const sk = cmd.match(/skills[\\/]+([\w.-]+)[\\/]+SKILL\.md/i); if (sk) skillUsed(t, sk[1]); else pushMsg(t, { role: 'log', kind: 'step', text: `실행 · ${cmd.replace(/^\/bin\/(z|ba)?sh -lc\s*/, '').replace(/^['"]|['"]$/g, '').split('\n')[0].slice(0, 90)}` }); }
        else if (it.type === 'file_change') pushMsg(t, { role: 'log', kind: 'file', text: `파일 · ${(it.changes || []).map((c) => `${c.kind} ${path.basename(c.path)}`).join(', ')}` });
      }
      if (o.type === 'turn.completed') { t.usage = o.usage; updateCtx(t); writeTask(t); }
      if (o.type === 'turn.failed' || (o.type === 'error' && !/^Reconnecting/.test(o.message || ''))) err += '\n' + (o.error?.message || o.message || '');
    }
  });
  p.stderr.on('data', (d) => { err += d; });
  return p.on('close', (code) => finish(t.id, code, p.spawnErr || err));
}

const CLAUDE_ALLOWED = ['Read', 'Edit', 'Write', 'Glob', 'Grep', 'WebFetch', 'WebSearch', 'Skill', 'Task', 'TodoWrite',
  ...['python3', 'python', 'py', 'node', 'npx', 'npm', 'ffmpeg', 'ffprobe', 'yt-dlp', 'whisper', 'ls', 'cat', 'head', 'tail', 'grep', 'find', 'wc', 'sort', 'cd', 'pwd', 'echo', 'mkdir', 'cp', 'mv', 'touch', 'sed', 'awk', 'file', 'sips', 'open', 'curl', 'unzip', 'zip', 'test', 'which', 'where', 'date',
    'Get-ChildItem', 'Get-Content', 'Set-Location', 'New-Item', 'Copy-Item', 'Move-Item', 'Test-Path', 'Start-Process', 'powershell', 'pwsh'].map((c) => `Bash(${c}:*)`), 'PowerShell'];
function runClaudeTurn(t, text) {
  // 학생 PC에서 Claude가 직원 스킬을 읽고 파이썬·노드 도구를 돌릴 수 있게: 허브 작업 폴더·내 자료를 열고, 일에 필요한 명령만 미리 허용(지우기·관리자 권한 같은 위험한 명령은 계속 확인 필요)
  const a = ['-p', '--output-format', 'stream-json', '--verbose', '--permission-mode', 'acceptEdits', '--add-dir', workRoot(), '--add-dir', myDir(),
    '--allowedTools', CLAUDE_ALLOWED.join(','), '--disallowedTools', 'Bash(rm -rf:*),Bash(sudo:*),Bash(git push:*)'];
  if (t.thread_id) a.push('--resume', t.thread_id);
  const c = cliSpawnArgs(claudeCommand(), a);
  const p = spawn(c.cmd, c.args, { cwd: t.cwd, shell: c.shell });
  p.on('error', (e) => { p.spawnErr = String(e && e.code === 'ENOENT' ? 'ENOENT' : e); });
  p.stdin.on('error', () => {});
  p.stdin.end(text, 'utf8');
  let buf = '', err = '', lastTok = 0;
  p.stdout.setEncoding('utf8');
  p.stdout.on('data', (d) => {
    buf += d; let i;
    while ((i = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, i); buf = buf.slice(i + 1);
      let o; try { o = JSON.parse(line); } catch { continue; }
      if (o.type === 'system' && o.session_id && !t.thread_id) { t.thread_id = o.session_id; writeTask(t); }
      if (o.type === 'assistant' && !o.parent_tool_use_id && o.message?.usage) { const u = o.message.usage; lastTok = (u.input_tokens || 0) + (u.cache_read_input_tokens || 0) + (u.cache_creation_input_tokens || 0); }
      if (o.type === 'result' && o.is_error) err += '\n' + String(o.result || o.subtype || '');
      if (o.type === 'result') { const mu = Object.values(o.modelUsage || {}); const win = Math.max(0, ...mu.map((x) => x.contextWindow || 0)) || t.ctx?.window || sess.CLAUDE_WINDOW; if (lastTok) { t.ctx = sess.mkCtx(lastTok, win); writeTask(t); } }
      if (o.type === 'assistant') for (const c of o.message?.content || []) {
        if (c.type === 'text' && c.text.trim()) pushMsg(t, { role: 'ai', text: c.text });
        if (c.type === 'tool_use') { if (c.name === 'Skill' && c.input?.skill) skillUsed(t, c.input.skill); else if (/^(Write|Edit|MultiEdit|NotebookEdit)$/.test(c.name) && c.input?.file_path) pushMsg(t, { role: 'log', kind: 'file', text: `파일 · ${c.name === 'Write' ? '만듦' : '고침'} ${path.basename(c.input.file_path)}` }); else pushMsg(t, { role: 'log', kind: 'step', text: `실행 · ${c.name} ${JSON.stringify(c.input).slice(0, 140)}` }); }
      }
      if (o.type === 'rate_limit_event' && o.rate_limit_info) saveClaudeUsage(o.rate_limit_info);
    }
  });
  p.stderr.on('data', (d) => { err += d; });
  return p.on('close', (code) => finish(t.id, code, p.spawnErr || err));
}

// Codex 맥락: 대화 기록 끝의 마지막 사용량(token_count)을 읽는다
function updateCtx(t) {
  try {
    const f = (t.rollout && fs.existsSync(t.rollout)) ? t.rollout : sess.findSessionFile('codex', t.thread_id, codexHomeOf(t));
    if (!f) return; t.rollout = f;
    const c = sess.contextOf(f, 'codex'); if (c) t.ctx = c;
  } catch {}
}
const afterTurn = new Map(); // 태스크 id → 턴이 끝나면 한 번 부를 함수
// Aside: 브라우저 AI. 대화는 Aside 쪽에 남고, 허브는 같은 대화 ID로 이어서 묻는다
function runAsideTurn(t, text) {
  const bin = asideCommand();
  if (!bin) { setTimeout(() => finish(t.id, 1, 'Aside 프로그램을 찾지 못했어요'), 0); return { kill() {} }; }
  const a = t.thread_id ? ['session', 'resume', t.thread_id, text, '--json', '--timeout', '30m'] : ['--json', '--timeout', '30m', text];
  const c = cliSpawnArgs(bin, a);
  const p = spawn(c.cmd, c.args, { cwd: t.cwd, shell: c.shell });
  let out = '', err = '';
  p.stdout.setEncoding('utf8'); p.stdout.on('data', (d) => { out += d; });
  p.stderr.on('data', (d) => { err += d; });
  p.on('error', (e) => { err += String(e); });
  return p.on('close', (code) => {
    let j = null; try { j = JSON.parse(out.slice(out.indexOf('{'))); } catch {}
    if (j) {
      if (j.session?.id && !t.thread_id) { t.thread_id = j.session.id; writeTask(t); }
      if (j.answer) pushMsg(t, { role: 'ai', text: j.answer });
      if (j.outcome && j.outcome !== 'completed') pushMsg(t, { role: 'log', text: `Aside · ${j.outcome}${j.error ? ' · ' + String(j.error).slice(0, 200) : ''}` });
    }
    finish(t.id, j && j.outcome === 'completed' ? 0 : code || 1, err || out);
  });
}
// 실패 이유를 학생 말로: 프로그램 없음 / 로그인 필요 / 사용량 다 씀 / 그 밖
function friendlyError(rt, err) {
  const e = String(err || ''); const who = rt === 'claude' ? 'Claude' : 'Codex';
  if (/ENOENT|not recognized|command not found|찾지 못했|없어요/i.test(e)) return { kind: 'missing', text: `이 PC에 ${who} 프로그램이 없어요. 설정 › AI 로그인에서 확인하거나, 위에서 다른 AI를 골라 주세요.` };
  if (/log ?in|logged out|not logged|unauthori[sz]ed|401|auth|credential|token.*expir/i.test(e)) return { kind: 'login', text: `${who} 로그인이 필요해요. 설정 › AI 로그인에서 로그인한 뒤 다시 보내 주세요.` };
  if (/rate.?limit|usage limit|quota|429|limit reached|too many requests|exceeded/i.test(e)) return { kind: 'quota', text: `${who} 사용량을 다 썼어요. 아래 줄에서 다시 채워지는 날을 보고, 그 전엔 다른 AI로 맡겨 보세요.` };
  return { kind: 'other', text: `${who}가 일을 끝내지 못했어요. 다시 보내 보거나, 내용을 조금 바꿔 보내 주세요.` };
}
function finish(id, code, err) {
  const r = running.get(id); running.delete(id);
  const t = readTask(id);
  t.status = code === 0 ? 'done' : 'error';
  if (r && r.stopped) { t.status = 'done'; pushMsg(t, { role: 'warn', text: '멈췄어요. 이어서 하려면 다시 말을 보내 주세요.' }); }
  else if (code !== 0) { const f = friendlyError(t.runtime, err); pushMsg(t, { role: 'warn', kind: f.kind, text: f.text, detail: String(err).trim().split('\n').slice(-3).join(' ').slice(0, 300) }); }
  else writeTask(t);
  emit({ type: 'status', task: id, status: t.status });
  usageCache.codex.at = 0; // 다음 조회 때 남은 양 새로 읽기
  const fn = afterTurn.get(id); if (fn) { afterTurn.delete(id); try { fn(code); } catch (e) { console.error('[이어가기 오류]', e); } }
  if (restartPending && !running.size) setTimeout(() => maybeRestart('기다리던 작업 끝남'), 1000);
}

function send(t, text, { show = null, internal = false } = {}) {
  if (running.has(t.id)) throw new Error('이 태스크는 AI가 아직 답하는 중이에요');
  const intent = t.thread_id && !internal ? handoffIntent(text) : null;
  if (intent) return { intent: 'handoff', ...intent };
  const r = maskSecrets(text);
  pushMsg(t, { role: 'me', text: show || r.text, who: conf.me, ...(show ? { sys: true } : {}) });
  if (r.count) pushMsg(t, { role: 'warn', text: `키 같은 글자 ${r.count}곳을 가렸어요. 대화·저장소에 남기지 않았어요. 각자 금고(맥 키체인·윈도우 자격 증명 관리자)에 저장해 주세요.` });
  t.status = 'working'; writeTask(t); emit({ type: 'status', task: t.id, status: 'working' });
  running.set(t.id, t.runtime === 'claude' ? runClaudeTurn(t, r.text) : t.runtime === 'aside' ? runAsideTurn(t, r.text) : runCodexTurn(t, r.text));
  return { ok: true };
}
import { redact as maskSecrets } from '../tools/lib.mjs';

const findSession = (rt, id) => rt === 'aside' ? sess.asideSessions(30, (bin, a) => { const c = cliSpawnArgs(asideCommand() || 'aside', a); return spawnSync(c.cmd, c.args, { encoding: 'utf8', timeout: 20000, shell: c.shell }).stdout || ''; }).find((x) => x.id === id) : sess.recentSessions(30, { exclude: hubHome() }).find((x) => x.id === id && x.runtime === rt);
// 이 PC의 하던 대화 목록(20초 캐시)
const listCache = { at: 0, days: 0, data: null };
function sessionList(days = 7, fresh = false) {
  if (!fresh && listCache.data && listCache.days === days && Date.now() - listCache.at < 20_000) return listCache.data;
  const taken = new Map(allTasks().filter((t) => t.thread_id).map((t) => [t.thread_id, t.id]));
  const run = (b, a) => { const c = cliSpawnArgs(asideCommand() || 'aside', a); return spawnSync(c.cmd, c.args, { encoding: 'utf8', timeout: 20000, shell: c.shell }).stdout || ''; };
  const since = Date.now() - days * 86400_000;
  const all = [...sess.recentSessions(days, { exclude: hubHome() }).map((s) => { const state = sess.stateOf(s); return { ...s, mtime: state.at || s.mtime, state }; }).filter((s) => new Date(s.mtime).getTime() >= since), ...(asideCommand() ? sess.asideSessions(days, run) : [])];
  all.sort((a, b) => b.mtime.localeCompare(a.mtime));
  const list = all.map(({ file, state, ...s }) => ({ ...s, first: s.title, title: String(state.name || s.name || s.title).slice(0, 90), state: { kind: state.kind, why: state.why, last: String(state.last || '').replace(/\s+/g, ' ').trim().slice(-140), summary: String(state.summary || '').replace(/\s+/g, ' ').trim().slice(0, 200), ask: String(state.ask || '').slice(0, 160), ctx: state.ctx ?? null }, task: taken.get(s.id) || null, home: s.cwd ? (s.cwd.startsWith(os.homedir()) ? '~' + s.cwd.slice(os.homedir().length) : s.cwd) : '브라우저(Aside)' }));
  listCache.at = Date.now(); listCache.days = days; listCache.data = { days, list };
  return listCache.data;
}
function importOne(b, cache = {}) {
      const s = b.runtime === 'aside' ? (cache.ax ||= sess.asideSessions(30, (bin, a) => spawnSync(asideCommand() || 'aside', a, { encoding: 'utf8', timeout: 20000 }).stdout || '')).find((x) => x.id === b.id) : (cache.cc ||= sess.recentSessions(30, { exclude: hubHome() })).find((x) => x.id === b.id && x.runtime === b.runtime);
  if (!s) return { ok: false, msg: '그 대화를 이 PC에서 못 찾았어요' };
  const dup = allTasks().find((t) => t.thread_id === s.id); if (dup) return { ok: true, task: dup.id, existed: true };
  listCache.at = 0;
  if (s.runtime === 'aside') {
    const t = newTask({ title: b.title || String(s.name || s.title).slice(0, 40), team: b.team, runtime: 'aside', thread_id: s.id, extra: { imported: { at: new Date().toISOString(), from: '이 PC의 Aside' } } });
    pushMsg(t, { role: 'log', text: `가져옴 · Aside 대화 그대로 이어서 · 대화 ID ${s.id}` });
    if (s.file) for (const m of sess.asideTurns(s.file, 4)) pushMsg(t, { ...m, orig: true });
    return { ok: true, task: t.id };
  }
  if (!sess.isDir(s.cwd)) return { ok: false, msg: `원래 폴더가 없어요: ${s.cwd}` };
  const t = newTask({ title: b.title || String(s.name || s.title).slice(0, 40), team: b.team, runtime: s.runtime, thread_id: s.id, cwd: s.cwd, extra: { imported: { at: new Date().toISOString(), from: s.runtime === 'codex' ? '이 PC의 Codex' : '이 PC의 Claude' }, codexPersonal: s.runtime === 'codex', rollout: s.runtime === 'codex' ? s.file : undefined, ctx: sess.contextOf(s.file, s.runtime) } });
  pushMsg(t, { role: 'log', text: `가져옴 · ${s.runtime === 'claude' ? 'Claude' : 'Codex'} 대화 그대로 이어서 · 원래 폴더 ${t.cwd} · 대화 ID ${s.id}` });
  for (const m of sess.lastTurns(s.file, s.runtime, 4)) pushMsg(t, { ...m, orig: true });
  if (sess.stateOf(s).kind === 'live') pushMsg(t, { role: 'warn', text: '이 대화는 가져올 때 다른 창(Orca·터미널)에서 쓰는 중이었어요. 그 창을 닫고 여기서 이어 주세요. 두 곳에서 동시에 말하면 대화가 엉켜요.' });
  return { ok: true, task: t.id };
    }

// ── 새 대화로 이어가기(맥락 50% 넘었을 때) ──
// 1) 지금 대화의 AI에게 이어가기 카드를 쓰게 한다  2) 같은 폴더·같은 AI로 새 태스크  3) 첫 메시지로 카드+원문 경로
const CONT_DIR = path.join(hubHome(), 'continue');
const CONT_ASK = [
  '이 대화가 길어져서 새 대화로 넘어간다. 새 대화의 너(같은 AI)가 맥락을 하나도 놓치지 않게 이어가기 카드를 써 줘.',
  '요약으로 뭉개지 말고, 사람이 한 말과 정한 것은 원문 그대로 인용해.',
  '형식(마크다운 제목 그대로):',
  '## 목표', '## 정한 것 (원문 인용)', '## 지킬 것 (조건·금지·기준)', '## 버린 안과 이유', '## 지금 상태 (만든 파일·바뀐 것·경로)', '## 남은 일 (순서대로)', '## 열린 질문',
  '카드만 출력하고 다른 말은 하지 마. 파일은 고치지 마.',
].join('\n');
function startContinue(t, { followUp = '' } = {}) {
  if (running.has(t.id)) throw new Error('AI가 답하는 중이에요. 끝난 뒤 눌러 주세요');
  if (!t.thread_id) throw new Error('아직 대화가 없어요');
  if (t.continuedTo) return { ok: true, task: t.continuedTo, existed: true };
  const start = t.messages.length;
  afterTurn.set(t.id, (code) => {
    const old = readTask(t.id);
    const card = old.messages.slice(start).filter((m) => m.role === 'ai').map((m) => m.text).pop();
    if (code !== 0 || !card) { pushMsg(old, { role: 'log', text: '이어가기 카드를 못 받았어요. 다시 눌러 주세요' }); return emit({ type: 'continued', task: old.id, ok: false }); }
    const src = old.runtime === 'codex' ? (old.rollout || sess.findSessionFile('codex', old.thread_id, codexHomeOf(old))) : old.runtime === 'aside' ? sess.asideFile(old.thread_id) : sess.findSessionFile('claude', old.thread_id);
    const gen = (old.gen || 1) + 1;
    const base = old.title.replace(/\s*·\s*이어서 \d+$/, '').trim();
    // 같은 폴더·같은 AI·같은 대화 기록 자리(개인 Codex면 개인 자리)로 새 태스크
    const nt = newTask({ title: `${base} · 이어서 ${gen}`, team: old.team, runtime: old.runtime, cwd: old.cwd, extra: { picked: !!old.picked, gen, continuedFrom: old.id, codexPersonal: old.codexPersonal || false } });
    fs.mkdirSync(CONT_DIR, { recursive: true });
    const cardFile = path.join(CONT_DIR, `${nt.id}.md`);
    fs.writeFileSync(cardFile, maskSecrets(`# 이어가기 카드 · ${old.title}\n\n원래 대화 ID: ${old.thread_id}\n원문: ${src || '못 찾음'}\n\n${card}\n`).text);
    old.continuedTo = nt.id; writeTask(old);
    pushMsg(old, { role: 'log', text: `새 대화로 이어감 · ${nt.title}` });
    const first = [
      `[이어가기] 앞 대화가 길어져 새 대화로 이어간다. 아래 카드를 먼저 읽고 시작해.`,
      `작업 폴더: ${nt.cwd}`,
      `앞 대화 ID: ${old.thread_id}`,
      `앞 대화 원문 파일: ${src || '없음'} (카드에 없는 세부가 필요하면 이 파일을 직접 열어 확인해)`,
      `카드 파일: ${cardFile}`,
      '', card, '',
      followUp ? `카드를 읽었으면 지금 상태를 두세 줄로 확인한 뒤, 이번 요청을 해 줘.\n\n이번 요청: ${followUp}` : '카드를 읽었으면 지금 상태를 두세 줄로 확인하고, 남은 일 첫 번째를 어떻게 할지 말해 줘. 아직 파일은 고치지 마.',
    ].join('\n');
    send(nt, first, { internal: true, show: `앞 대화에서 이어가기 카드를 받아 새 대화를 시작했어요.\n카드: ${cardFile}${followUp ? `\n\n이번 요청: ${followUp}` : ''}` });
    emit({ type: 'continued', task: old.id, to: nt.id, ok: true });
  });
  send(t, CONT_ASK, { internal: true, show: '새 대화로 이어가기 · 지금 대화의 AI에게 이어가기 카드를 쓰게 했어요' });
  return { ok: true, started: true };
}

// ── 구독 남은 양 ────────────────────────────────────────────
const usageCache = { codex: { at: 0, data: null }, claude: null };
// Claude는 남은 양 조회 창구가 없어서, Claude 응답에 같이 오는 사용률(rate_limit_event)을 저장해 둔다.
const CL_USAGE = path.join(hubHome(), 'claude-usage.json');
try { usageCache.claude = JSON.parse(fs.readFileSync(CL_USAGE, 'utf8')); } catch {}
function saveClaudeUsage(info) {
  const w = info.unifiedWindows || {};
  const pct = (x) => (x && typeof x.utilization === 'number' ? Math.round(x.utilization * 100) : null);
  usageCache.claude = { at: Date.now(), fiveHour: pct(w.five_hour), weekly: pct(w.seven_day), fiveReset: w.five_hour?.resetsAt || null, weeklyReset: w.seven_day?.resetsAt || null, status: info.status };
  try { fs.writeFileSync(CL_USAGE, JSON.stringify(usageCache.claude)); } catch {}
}
// 사용률을 한 번 받아 오는 아주 짧은 확인(가장 가벼운 모델, 도구·설정 없이). 30분에 한 번까지만.
let clProbe = null;
function claudeProbe(force) {
  if (clProbe) return clProbe;
  if (!force && usageCache.claude && Date.now() - usageCache.claude.at < 30 * 60_000) return Promise.resolve(usageCache.claude);
  clProbe = new Promise((resolve) => {
    let p;
    try { const c = cliSpawnArgs(claudeCommand(), ['-p', '--output-format', 'stream-json', '--verbose', '--model', 'haiku', '--tools', '', '--setting-sources', '']); p = spawn(c.cmd, c.args, { cwd: hubHome(), shell: c.shell }); }
    catch { clProbe = null; return resolve(usageCache.claude); }
    p.stdin.end('ok', 'utf8');
    let buf = '';
    p.stdout.setEncoding('utf8');
    p.stdout.on('data', (d) => { buf += d; for (const l of buf.split('\n')) { try { const o = JSON.parse(l); if (o.type === 'rate_limit_event' && o.rate_limit_info) saveClaudeUsage(o.rate_limit_info); } catch {} } });
    const done = () => { clProbe = null; resolve(usageCache.claude); };
    p.on('close', done); p.on('error', done);
    setTimeout(() => { try { p.kill(); } catch {} }, 60_000);
  });
  return clProbe;
}
function codexUsage() {
  if (Date.now() - usageCache.codex.at < 60_000 && usageCache.codex.data) return Promise.resolve(usageCache.codex.data);
  return new Promise((resolve) => {
    const [bin, pre] = codexCommand();
    const p = spawn(bin, [...pre, 'app-server'], { env: codexEnv() });
    let out = '', done = false;
    const end = (v) => { if (done) return; done = true; try { p.kill(); } catch {} resolve(v); };
    p.stdout.setEncoding('utf8');
    p.stdout.on('data', (d) => {
      out += d;
      for (const l of out.split('\n')) { try { const o = JSON.parse(l); if (o.id === 2) { const rl = o.result?.rateLimits || {}; const data = { plan: rl.planType, weekly: rl.primary?.usedPercent, weeklyReset: rl.primary?.resetsAt, fiveHour: rl.secondary?.usedPercent ?? null, resets: o.result?.rateLimitResetCredits?.availableCount ?? null }; usageCache.codex = { at: Date.now(), data }; end(data); } } catch {} }
    });
    p.on('error', () => end(null));
    const w = (o) => p.stdin.write(JSON.stringify(o) + '\n');
    w({ jsonrpc: '2.0', id: 1, method: 'initialize', params: { clientInfo: { name: 'aixschool-hub', version: '0.1.0' } } });
    w({ jsonrpc: '2.0', method: 'initialized', params: {} });
    w({ jsonrpc: '2.0', id: 2, method: 'account/rateLimits/read', params: {} });
    setTimeout(() => end(usageCache.codex.data), 8000);
  });
}

// ── 팀 저장소 동기화: 학생 허브에는 없다(팀 저장소·자동 받기·자동 다시 켜기 없음) ──
const STARTED_CODE = '';
let restartPending = false;
function maybeRestart() { return false; }
const lastPull = null;

// ── 넘김 꾸러미 ─────────────────────────────────────────────
function listHandoffs() { return []; }
function runTool(name, args) {
  const r = spawnSync(process.execPath, [path.join(REPO, 'tools', name), ...args], { encoding: 'utf8', maxBuffer: 64 << 20, env: { ...process.env, AIHUB_HOME: hubHome() } });
  return { ok: r.status === 0, out: (r.stdout || '') + (r.stderr || '') };
}

// 프로그램을 띄워 출력만 받는다(서버를 멈추지 않게 비동기)
function cap(cmd, args, opt = {}) {
  return new Promise((resolve) => {
    let out = '', errt = '', done = false; let p;
    const end = (o) => { if (!done) { done = true; resolve(o); } };
    try { p = spawn(cmd, args, { ...opt, windowsHide: true }); } catch (e) { return end({ status: null, stdout: '', stderr: '', error: e }); }
    p.stdout?.setEncoding('utf8'); p.stdout?.on('data', (d) => (out += d)); p.stderr?.on('data', (d) => (errt += d));
    p.on('error', (e) => end({ status: null, stdout: out, stderr: errt, error: e }));
    p.on('close', (code) => end({ status: code, stdout: out, stderr: errt }));
    setTimeout(() => { try { p.kill(); } catch {} end({ status: null, stdout: out, stderr: errt, error: new Error('timeout') }); }, 15000);
  });
}
let authCache = null;
async function authStatus() {
  let c;
  try { const [bin, pre] = codexCommand(); c = await cap(bin, [...pre, 'login', 'status'], { env: codexEnv() }); } catch (e) { c = { status: null, stdout: '', stderr: '', error: e }; }
  const cs = cliSpawnArgs(claudeCommand(), ['auth', 'status']);
  const cl = await cap(cs.cmd, cs.args, { shell: cs.shell });
  const ctext = ((c.stdout || '') + (c.stderr || '')).trim();
  const cltext = ((cl.stdout || '') + (cl.stderr || '')).trim();
  let clnice = '';
  try { const j = JSON.parse(cl.stdout); clnice = [j.loggedIn ? '로그인됨' : '로그인 안 됨', j.subscriptionType ? `${j.subscriptionType} 구독` : '', j.authMethod === 'claude.ai' ? 'Claude 계정' : j.authMethod || '', j.email ? j.email.replace(/^(.{2}).*(@.*)$/, '$1***$2') : ''].filter(Boolean).join(' · '); } catch {}
  return {
    pc: pcCheck(),
    codex: { ok: c.status === 0 && /logged in/i.test(ctext), text: c.error ? 'Codex 프로그램이 없어요' : (/logged in using chatgpt/i.test(ctext) ? 'ChatGPT 계정으로 로그인됨' : /not logged/i.test(ctext) ? '로그인 안 됨' : ctext.split('\n').pop().slice(0, 120)) || '확인 못 함', installed: !c.error },
    claude: { ok: cl.status === 0 && /"loggedIn":\s*true|logged in/i.test(cltext), text: cl.error ? 'Claude 프로그램이 없어요' : clnice || cltext.split('\n').slice(0, 3).join(' ').slice(0, 160), installed: !cl.error },
  };
}
async function refreshAuth() { try { const a = await authStatus(); authCache = { at: Date.now(), codex: a.codex.ok, claude: a.claude.ok, full: a }; emit({ type: 'auth', codex: a.codex.ok, claude: a.claude.ok }); } catch (e) { console.error('[로그인 확인 오류]', e); } return authCache; }
setTimeout(refreshAuth, 300); setInterval(refreshAuth, 10 * 60_000);
function incomingList() { return []; }

// 넘기기·이어받기는 학생 허브에 없다
const holds = new Map();
const PEOPLE = [];
function handoffIntent() { return null; }

function findBrowser() {
  const c = PLATFORM === 'windows'
    ? [path.join(process.env['ProgramFiles'] || 'C:\\Program Files', 'Google', 'Chrome', 'Application', 'chrome.exe'), path.join(process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)', 'Google', 'Chrome', 'Application', 'chrome.exe'), path.join(process.env.LOCALAPPDATA || '', 'Google', 'Chrome', 'Application', 'chrome.exe'), path.join(process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)', 'Microsoft', 'Edge', 'Application', 'msedge.exe'), path.join(process.env['ProgramFiles'] || 'C:\\Program Files', 'Microsoft', 'Edge', 'Application', 'msedge.exe')]
    : ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge', '/Applications/Chromium.app/Contents/MacOS/Chromium'];
  return c.find((f) => f && fs.existsSync(f)) || null;
}
// 멈추기: 윈도우는 프로그램이 띄운 하위 프로그램까지 같이 끈다
function killTree(p) {
  try { if (PLATFORM === 'windows' && p.pid) spawn('taskkill', ['/PID', String(p.pid), '/T', '/F'], { windowsHide: true }).on('error', () => {}); else p.kill(); } catch {}
}
// 이 PC의 탐색기(Finder)·터미널을 작업 폴더에서 연다
function reveal(dir, what) {
  if (!sess.isDir(dir)) return { ok: false, msg: '폴더가 없어요' };
  const go = (cmd, args, opt = {}) => { const c = spawn(cmd, args, { detached: true, stdio: 'ignore', windowsHide: false, ...opt }); c.on('error', () => {}); c.unref(); };
  try {
    if (PLATFORM === 'mac') go('open', what === 'terminal' ? ['-a', 'Terminal', dir] : [dir]);
    else if (PLATFORM === 'windows') {
      if (what === 'terminal') go('powershell.exe', ['-NoExit', '-Command', `Set-Location -LiteralPath '${dir.replace(/'/g, "''")}'`], { cwd: dir }); // detached = 새 창
      else go('explorer.exe', [dir]);
    } else go('xdg-open', [dir]);
    return { ok: true };
  } catch (e) { return { ok: false, msg: String(e.message || e) }; }
}

// ── 검색 ────────────────────────────────────────────────────
function search(q) {
  q = String(q || '').trim().toLowerCase();
  if (!q) return [];
  const out = [];
  const hit = (s) => String(s || '').toLowerCase().includes(q);
  const snip = (s) => { const t = String(s || ''); const i = t.toLowerCase().indexOf(q); return i < 0 ? '' : t.slice(Math.max(0, i - 30), i + 60).replace(/\s+/g, ' '); };
  for (const t of allTasks()) {
    const team = TEAMS.find((x) => x.id === t.team)?.name || '전체';
    if (hit(t.title) || hit(team) || hit(t.owner) || hit(t.from)) out.push({ kind: '태스크', id: t.id, title: t.title, sub: `${team} · ${t.owner || ''}` });
    else { const m = t.messages.find((x) => hit(x.text)); if (m) out.push({ kind: '대화', id: t.id, title: t.title, sub: snip(m.text) }); }
    try { for (const f of (t.picked ? [] : fs.readdirSync(t.cwd))) if (hit(f)) out.push({ kind: '파일', id: t.id, title: f, sub: t.title }); } catch {}
    if (hit(t.cwd) && t.picked) out.push({ kind: '폴더', id: t.id, title: t.title, sub: t.cwd });
  }
  return out.slice(0, 50);
}

// ── HTTP ────────────────────────────────────────────────────
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8', '.md': 'text/plain; charset=utf-8', '.txt': 'text/plain; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.pdf': 'application/pdf', '.mp4': 'video/mp4' };
const json = (res, code, o) => { res.writeHead(code, { 'content-type': MIME['.json'] }); res.end(JSON.stringify(o)); };
const body = (req) => new Promise((r) => { let s = ''; req.setEncoding('utf8'); req.on('data', (d) => (s += d)); req.on('end', () => { try { r(s ? JSON.parse(s) : {}); } catch { r({}); } }); });
function serveFile(res, file) {
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end('없음'); }
  res.writeHead(200, { 'content-type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream', 'cache-control': 'no-cache' });
  fs.createReadStream(file).pipe(res);
}
function authed(req) { const ip = req.socket.remoteAddress || ''; return ip === '127.0.0.1' || ip === '::1' || ip === '::ffff:127.0.0.1'; }
function lanAddrs() {
  const r = [];
  for (const [n, list] of Object.entries(os.networkInterfaces())) for (const a of list || []) if (a.family === 'IPv4' && !a.internal) r.push({ name: n, ip: a.address, tailscale: a.address.startsWith('100.') });
  return r;
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://x');
  const p = decodeURIComponent(url.pathname);
  if (!authed(req)) { res.writeHead(403); return res.end('이 PC 안에서만 열려요'); }
  try {
    let m;
    if (p === '/api/events') { res.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-cache', connection: 'keep-alive' }); res.write(': ok\n\n'); clients.add(res); req.on('close', () => clients.delete(res)); return; }
    if (p === '/api/state' && req.method === 'GET') return json(res, 200, { me: conf.me, team: conf.team, platform: PLATFORM, teams: TEAMS, tasks: allTasks().map(({ messages, ...t }) => ({ ...t, last: messages.at(-1)?.text?.slice(0, 80) || '', count: messages.length })), learnConsent: conf.learnConsent, pending: learn.pending(hubHome()).length, auth: authCache ? { codex: authCache.codex, claude: authCache.claude } : null });
    if (p === '/api/me' && req.method === 'POST') { const b = await body(req); conf.me = String(b.me || '').slice(0, 20); if (b.team) conf.team = b.team; saveConf(); return json(res, 200, { ok: true }); }
    if (p === '/api/usage') { const c = await codexUsage(); if (url.searchParams.get('claude') === '1') await claudeProbe(true); else claudeProbe(false); return json(res, 200, { codex: c, claude: usageCache.claude }); }
    if (p === '/api/search') return json(res, 200, search(url.searchParams.get('q')));
    if (p === '/api/tasks' && req.method === 'POST') { const b = await body(req); const t = newTask({ title: b.title || '새 태스크', team: b.team, runtime: ['claude', 'aside'].includes(b.runtime) ? b.runtime : 'codex', cwd: b.cwd || '' }); if (b.text) send(t, b.text); return json(res, 200, t); }
    if (p === '/api/dirs') return json(res, 200, sess.dirCandidates(url.searchParams.get('q') || '', { recent: conf.recentDirs || [], exclude: hubHome() }));
    if ((m = p.match(/^\/api\/tasks\/([\w-]+)$/))) return json(res, 200, readTask(m[1]));
    if ((m = p.match(/^\/api\/tasks\/([\w-]+)\/send$/)) && req.method === 'POST') { const b = await body(req); const t = readTask(m[1]); return json(res, 200, send(t, String(b.text || ''))); }
    if ((m = p.match(/^\/api\/tasks\/([\w-]+)\/files$/))) return json(res, 200, taskFiles(readTask(m[1])));
    if ((m = p.match(/^\/api\/tasks\/([\w-]+)\/stop$/)) && req.method === 'POST') { const r = running.get(m[1]); if (!r) return json(res, 200, { ok: true, idle: true }); r.stopped = true; killTree(r); return json(res, 200, { ok: true }); }
    if ((m = p.match(/^\/api\/tasks\/([\w-]+)\/rename$/)) && req.method === 'POST') { const b = await body(req); const t = readTask(m[1]); t.title = String(b.title || '').trim().slice(0, 60) || t.title; writeTask(t); return json(res, 200, { ok: true }); }
    if ((m = p.match(/^\/api\/tasks\/([\w-]+)\/delete$/)) && req.method === 'POST') { if (running.has(m[1])) return json(res, 409, { ok: false, msg: 'AI가 일하는 중이에요. 멈춘 뒤 지워 주세요' }); fs.rmSync(tfile(m[1]), { force: true }); return json(res, 200, { ok: true }); }
    if ((m = p.match(/^\/api\/tasks\/([\w-]+)\/reveal$/)) && req.method === 'POST') { const b = await body(req); const t = readTask(m[1]); return json(res, 200, reveal(t.cwd, b.what === 'terminal' ? 'terminal' : 'folder')); }
    if (p === '/api/reveal' && req.method === 'POST') { const b = await body(req); return json(res, 200, reveal(workRoot(), b.what === 'terminal' ? 'terminal' : 'folder')); }
    // 내 자료 채운 정도
    if (p === '/api/my') return json(res, 200, myStatus());
    if (p === '/api/my/reveal' && req.method === 'POST') { ensureMy(); return json(res, 200, reveal(myDir(), 'folder')); }
    if (p === '/api/my/interview' && req.method === 'POST') {
      ensureMy(); const a = authCache || {};
      const t = newTask({ title: '내 자료 같이 채우기', runtime: a.codex === false && a.claude ? 'claude' : 'codex', cwd: myDir() });
      send(t, '내 자료 같이 채우자. 이 폴더의 about.md 와 thinking.md 빈칸을 채우려고 해. 질문을 한 번에 하나씩 해 줘(쉬운 말로, 예시 하나씩 곁들여서). 내가 답하면 내 말 그대로 해당 칸에 적고, 다 채우면 무엇을 적었는지 보여 줘. 내가 말하지 않은 내용은 지어내지 마.');
      return json(res, 200, { ok: true, task: t.id });
    }
    // AI가 실행한 스크립트용: 허브 열쇠(hub.json token)가 맞을 때만 키 값을 준다. 화면에는 절대 안 보낸다.
    if ((m = p.match(/^\/api\/keys\/([A-Z0-9_]+)$/)) && req.headers['x-hub-token'] === conf.token) {
      let allowed = []; try { allowed = JSON.parse(fs.readFileSync(path.join(REPO, 'skills', 'connections.json'), 'utf8')).connections.flatMap((x) => (x.keys || []).map((k) => k.name)); } catch {}
      if (!allowed.includes(m[1])) return json(res, 404, {});
      const v = keys.getKey(m[1]); return v ? json(res, 200, { value: v }) : json(res, 404, {});
    }
    // AI 보호 구역 안에서 브라우저를 못 띄우는 경우(윈도우 Codex)를 위한 대신 렌더. 허브 열쇠 필요, 작업 폴더 안 파일만.
    if (p === '/api/browser' && req.method === 'POST' && req.headers['x-hub-token'] === conf.token) {
      const b = await body(req); const root = path.resolve(workRoot()).toLowerCase();
      const inWork = (f) => { try { return path.resolve(f).toLowerCase().startsWith(root); } catch { return false; } };
      const args = [];
      for (const x of b.args || []) {
        const v = String(x);
        if (/^--(window-size|virtual-time-budget)=[\d,]+$/.test(v) || v === '--dump-dom' || v === '--allow-file-access-from-files') args.push(v);
        else if (v.startsWith('--screenshot=') && inWork(v.slice(13))) args.push(v);
        else if (v.startsWith('file:') && inWork(fileURLToPath(v))) args.push(v);
        else return json(res, 400, { ok: false, msg: '허용되지 않는 값: ' + v.slice(0, 60) });
      }
      const exe = findBrowser(); if (!exe) return json(res, 404, { ok: false, msg: '크롬·엣지를 찾지 못했어요' });
      const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'aihub-render-'));
      const r = await cap(exe, ['--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run', '--no-default-browser-check', '--force-device-scale-factor=1', '--user-data-dir=' + prof, ...args]);
      try { fs.rmSync(prof, { recursive: true, force: true }); } catch {}
      return json(res, 200, { ok: true, out: r.stdout || '' });
    }
    // 연결(키): 키 값은 이 PC 금고에만. 화면에는 있음/없음만.
    if (p === '/api/connections') {
      let c = { connections: [] }; try { c = JSON.parse(fs.readFileSync(path.join(REPO, 'skills', 'connections.json'), 'utf8')); } catch {}
      for (const x of c.connections) x.keys = (x.keys || []).map((k) => ({ ...k, has: keys.hasKey(k.name) }));
      return json(res, 200, c);
    }
    if (p === '/api/connections/key' && req.method === 'POST') {
      const b = await body(req); let allowed = [];
      try { allowed = JSON.parse(fs.readFileSync(path.join(REPO, 'skills', 'connections.json'), 'utf8')).connections.flatMap((x) => (x.keys || []).map((k) => k.name)); } catch {}
      if (!allowed.includes(b.name)) return json(res, 400, { ok: false, msg: '모르는 키 이름이에요' });
      if (b.remove) { keys.deleteKey(b.name); return json(res, 200, { ok: true }); }
      try { keys.setKey(b.name, String(b.value || '')); return json(res, 200, { ok: true }); } catch (e) { return json(res, 400, { ok: false, msg: e.message }); }
    }
    if (p === '/api/connections/help' && req.method === 'POST') {
      const b = await body(req); let c = null;
      try { c = JSON.parse(fs.readFileSync(path.join(REPO, 'skills', 'connections.json'), 'utf8')).connections.find((x) => x.id === b.id); } catch {}
      if (!c) return json(res, 400, { ok: false, msg: '연결을 찾지 못했어요' });
      const a = authCache || {};
      const t = newTask({ title: `${c.name} 연결 도와줘`, runtime: a.codex === false && a.claude ? 'claude' : 'codex' });
      send(t, `${c.name} 연결을 처음 해 보려고 해. 나는 개발자가 아니야. 아래 순서를 한 단계씩 같이 해 줘. 공식 문서(${c.doc})를 먼저 열어 지금 화면 기준으로 어디를 누르면 되는지 쉬운 말로 알려 주고, 한 단계 끝날 때마다 내가 됐다고 하면 다음으로 가 줘. 키·토큰은 대화에 붙이지 말고 허브 설정 › 연결 › ${c.name} 칸에 직접 넣으라고 안내해 줘. 마지막에 연결이 됐는지 확인해 줘.\n\n순서:\n${(c.steps || []).map((x, i) => `${i + 1}. ${x}`).join('\n')}`);
      return json(res, 200, { ok: true, task: t.id });
    }
    if (p === '/api/open-source') { try { return json(res, 200, JSON.parse(fs.readFileSync(path.join(REPO, 'skills', 'open-source.json'), 'utf8'))); } catch { return json(res, 200, []); } }
    if (p === '/api/staff') { try { return json(res, 200, JSON.parse(fs.readFileSync(path.join(REPO, 'skills', 'staff.json'), 'utf8'))); } catch { return json(res, 200, { staff: [] }); } }
    if ((m = p.match(/^\/api\/tasks\/([\w-]+)\/continue$/)) && req.method === 'POST') { const t = readTask(m[1]); return json(res, 200, startContinue(t)); }
    if ((m = p.match(/^\/api\/tasks\/([\w-]+)\/ctx-dismiss$/)) && req.method === 'POST') { const t = readTask(m[1]); t.ctxDismissed = true; writeTask(t); return json(res, 200, { ok: true }); }
    if ((m = p.match(/^\/files\/([\w-]+)\/(.+)$/))) { const t = readTask(m[1]); const f = path.resolve(t.cwd, m[2]); if (!f.startsWith(path.resolve(t.cwd))) { res.writeHead(403); return res.end(); } return serveFile(res, f); }
    if (p === '/api/client-log' && req.method === 'GET') { console.log('[미리보기]', String(url.searchParams.get('m') || '').slice(0, 400)); res.writeHead(204); return res.end(); }
    if (p === '/api/client-log' && req.method === 'POST') { const b = await body(req); console.log('[화면]', String(b.m || '').slice(0, 300)); return json(res, 200, { ok: true }); }
    // 스킬
    if (p === '/api/skills') { const man = JSON.parse(fs.readFileSync(path.join(REPO, 'skills', 'manifest.json'), 'utf8')); const installed = fs.existsSync(path.join(codexHome(), 'skills')) ? fs.readdirSync(path.join(codexHome(), 'skills')) : []; return json(res, 200, { platform: PLATFORM, skills: man.skills.map((s) => ({ ...s, installed: installed.includes(s.name) })) }); }
    if (p === '/api/skills/scan' && req.method === 'POST') { const r = runTool('skill-register.mjs', ['list', '--json']); try { return json(res, 200, JSON.parse(r.out.slice(r.out.indexOf('[')))); } catch { return json(res, 500, { msg: r.out.slice(-400) }); } }
    if (p === '/api/skills/register' && req.method === 'POST') {
      const b = await body(req); if (!b.names?.length) return json(res, 400, { ok: false, msg: '고른 스킬이 없어요' });
      const r = runTool('skill-register.mjs', ['add', ...b.names]);
      spawnSync(process.execPath, [path.join(REPO, 'tools', 'skills-sync.mjs')], { env: { ...process.env, AIHUB_HOME: hubHome() } });
      return json(res, 200, { ok: r.ok, out: r.out });
    }
    // 규칙·팀 기억
    if (p === '/api/rules') { const team = url.searchParams.get('team'); const f = path.join(REPO, 'AGENTS.md'); return json(res, 200, { file: path.relative(REPO, f), text: fs.readFileSync(f, 'utf8'), personal: learn.personalRules(hubHome()) }); }
    // 자동 점검
    if (p === '/api/learn/consent' && req.method === 'POST') { const b = await body(req); conf.learnConsent = !!b.on; saveConf(); return json(res, 200, { ok: true, on: conf.learnConsent }); }
    if (p === '/api/learn/pending') return json(res, 200, learn.pending(hubHome()));
    if (p === '/api/learn/scan' && req.method === 'POST') {
      if (!conf.learnConsent) return json(res, 403, { ok: false, msg: '자동 점검에 먼저 동의해 주세요' });
      const b = await body(req);
      learn.scan({ hub: hubHome(), repo: REPO, days: Number(b.days || 7), me: conf.me }).then((r) => emit({ type: 'learn', ...r })).catch((e) => emit({ type: 'learn', ok: false, msg: String(e) }));
      return json(res, 200, { ok: true, started: true });
    }
    if (p === '/api/learn/decide' && req.method === 'POST') {
      const b = await body(req); const r = learn.decide({ hub: hubHome(), repo: REPO, id: b.id, choice: b.choice, team: b.team, me: conf.me });
      if (r.ok && r.choice !== 'discard') spawnSync(process.execPath, [path.join(REPO, 'tools', 'skills-sync.mjs')], { env: { ...process.env, AIHUB_HOME: hubHome() } });
      return json(res, 200, r);
    }
    // AI 로그인 (이 PC에서 브라우저가 열린다)
    if (p === '/api/auth') { const a = await refreshAuth(); return json(res, 200, a?.full || {}); }
    if ((m = p.match(/^\/api\/auth\/(codex|claude)\/(login|logout)$/)) && req.method === 'POST') {
      const [, who, act] = m;
      const [bin, pre] = who === 'codex' ? codexCommand() : [claudeCommand(), []];
      const args = who === 'codex' ? (act === 'login' ? ['login'] : ['logout']) : ['auth', act];
      const cs = cliSpawnArgs(bin, [...pre, ...args]);
      const child = spawn(cs.cmd, cs.args, { env: who === 'codex' ? codexEnv() : process.env, detached: true, stdio: 'ignore', shell: cs.shell });
      child.unref(); child.on('close', () => refreshAuth()); child.on('error', () => {});
      return json(res, 200, { ok: true, msg: act === 'login' ? '이 PC에 로그인 창(브라우저)이 열려요. 로그인한 뒤 새로고침을 누르세요.' : '로그아웃했어요' });
    }
    // 화면
    if (p === '/' || p === '/index.html') return serveFile(res, path.join(PUB, 'index.html'));
    if (p.startsWith('/static/')) { const f = path.resolve(PUB, p.slice(8)); if (!f.startsWith(PUB)) { res.writeHead(403); return res.end(); } return serveFile(res, f); }
    res.writeHead(404); res.end('없음');
  } catch (e) { console.error(`[오류] ${req.method} ${p} · ${e.stack || e}`); json(res, 500, { ok: false, msg: String(e.message || e) }); }
});
let listenTries = 0;
server.on('error', (e) => { if (e.code === 'EADDRINUSE' && listenTries++ < 40) return setTimeout(() => server.listen(PORT, '127.0.0.1'), 500); console.error('[AI 학교 허브] 서버를 열지 못함', e); process.exit(1); });
server.listen(PORT, '127.0.0.1', () => {
  console.log(`[AI 학교 허브] 실행 · http://127.0.0.1:${PORT} · 허브 폴더 ${hubHome()} · pid ${process.pid}`);
  try { const pc = pcCheck(); console.log(`[이 PC] 사용자 폴더 ${pc.home}${pc.oddHome ? ' (띄어쓰기·한글 있음 → AI를 직접 실행)' : ''} · Claude ${pc.claude.how} ${pc.claude.path} · Codex ${pc.codex.how}`); } catch {}
});
