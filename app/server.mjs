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
import * as upd from '../tools/update.mjs';

// 허브를 다른 AI 창(Orca·Claude Code 터미널)에서 켰을 때 따라온 그 창의 표시를 지운다.
// 남겨 두면 허브가 돌린 대화가 사람이 연 대화처럼 기록되고, 하던 일 목록에 섞인다.
for (const k of Object.keys(process.env)) if (/^(CLAUDECODE|CLAUDE_CODE_|ORCA_)/.test(k)) delete process.env[k];
// 켠 쪽 PC에 유료 API 키가 있으면 Claude·Codex가 구독 대신 그 키로 돌아 요금이 나간다 → 허브는 늘 구독 로그인만 쓴다
for (const k of ['ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_BASE_URL', 'CLAUDE_CODE_USE_BEDROCK', 'CLAUDE_CODE_USE_VERTEX', 'OPENAI_API_KEY', 'OPENAI_BASE_URL', 'CODEX_API_KEY']) delete process.env[k];
// 앱을 Finder·시작 메뉴로 열면 PATH가 짧다. 서버를 켠 Node의 폴더를 넣어 둬야 Node로 도는 프로그램(codex 등)이 Node를 찾는다.
{ const d = path.dirname(process.execPath); const cur = (process.env.PATH || '').split(path.delimiter); if (!cur.includes(d)) process.env.PATH = [d, ...cur].filter(Boolean).join(path.delimiter); }
// 예상 못 한 오류 하나로 서버 전체가 꺼지면 창에 '127.0.0.1 연결 거부'만 남는다 → 기록만 남기고 계속 돈다(2026-11-27)
process.on('uncaughtException', (e) => { try { console.error('[AI 학교 허브] 처리 못 한 오류(서버는 계속 돔)', e?.stack || e); } catch {} });
process.on('unhandledRejection', (e) => { try { console.error('[AI 학교 허브] 처리 못 한 오류(서버는 계속 돔)', e?.stack || e); } catch {} });
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
// 허브가 꺼졌다 켜지면 돌던 AI는 이미 없다. '하는 중'으로 남은 작업을 멈춘 것으로 바꿔 둔다.
for (const t of allTasks()) if (t.status === 'working') { t.status = 'done'; t.messages.push({ ts: new Date().toISOString(), role: 'warn', text: '허브가 다시 켜지면서 이 일은 멈췄어요. 이어서 하려면 다시 말을 보내 주세요.' }); writeTask(t); }
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
  try { const mine = myStaff().find((x) => x.skill === name); if (mine) return `내 직원 ${mine.name} (${name})`; } catch {}
  try { const m = JSON.parse(fs.readFileSync(path.join(REPO, 'skills', 'manifest.json'), 'utf8')).skills.find((x) => x.name === name); if (m) return `${m.desc} (${name})`; } catch {}
  return name;
}
function pushMsg(t, m) { t.messages.push({ ts: new Date().toISOString(), ...m }); t.updated = new Date().toISOString(); writeTask(t); emit({ type: 'msg', task: t.id, msg: t.messages.at(-1) }); }

function runCodexTurn(t, text, imgs = []) {
  let bin, pre; try { [bin, pre] = codexCommand(); } catch { setTimeout(() => finish(t.id, 1, 'ENOENT'), 0); return { kill() {} }; }
  const a = ['exec', ...(t.model ? ['-m', t.model] : modelArgs()), '--skip-git-repo-check', '--json'];
  if (t.thread_id) a.push('resume', t.thread_id, '-'); else a.push('-');
  for (const im of imgs) a.push(`--image=${im.file}`); // 프롬프트(-) 뒤에 붙여야 '-'를 그림 이름으로 먹지 않는다
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
function runClaudeTurn(t, text, imgs = []) {
  // 학생 PC에서 Claude가 직원 스킬을 읽고 파이썬·노드 도구를 돌릴 수 있게: 허브 작업 폴더·내 자료를 열고, 일에 필요한 명령만 미리 허용(지우기·관리자 권한 같은 위험한 명령은 계속 확인 필요)
  const a = ['-p', '--output-format', 'stream-json', '--verbose', '--permission-mode', 'acceptEdits', '--add-dir', workRoot(), '--add-dir', myDir(),
    '--allowedTools', CLAUDE_ALLOWED.join(','), '--disallowedTools', 'Bash(rm -rf:*),Bash(sudo:*),Bash(git push:*)'];
  if (t.model) a.push('--model', t.model);
  if (t.thread_id) a.push('--resume', t.thread_id);
  // 사진이 있으면 글과 사진을 한 메시지(stream-json)로 넘긴다. Claude가 따로 파일을 열 필요가 없다.
  if (imgs.length) a.push('--input-format', 'stream-json');
  const c = cliSpawnArgs(claudeCommand(), a);
  const p = spawn(c.cmd, c.args, { cwd: t.cwd, shell: c.shell });
  p.on('error', (e) => { p.spawnErr = String(e && e.code === 'ENOENT' ? 'ENOENT' : e); });
  p.stdin.on('error', () => {});
  if (imgs.length) {
    const content = [{ type: 'text', text }, ...imgs.map((im) => ({ type: 'image', source: { type: 'base64', media_type: im.mime, data: fs.readFileSync(im.file).toString('base64') } }))];
    p.stdin.end(JSON.stringify({ type: 'user', message: { role: 'user', content } }) + '\n', 'utf8');
  } else p.stdin.end(text, 'utf8');
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
function friendlyError(rt, err, picked = false) {
  const e = String(err || ''); const who = rt === 'claude' ? 'Claude' : 'Codex';
  if (picked && /issue with the selected model|may not exist or you may not have access|model.{0,80}(not (found|supported|available)|does not exist|unavailable|not have access|no access)|invalid model|unknown model/i.test(e)) return { kind: 'model', text: `고른 모델을 지금 ${who} 구독에서 쓸 수 없어요. 새로 맡기기에서 모델을 '기본'으로 골라 새 대화로 다시 맡겨 주세요.` };
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
  else if (code !== 0) { const f = friendlyError(t.runtime, err, !!t.model); if (t.runtime === 'codex' && !t.codexPersonal && STALE_RE.test(String(err || ''))) { markCodexStale(); f.kind = 'login'; f.text = 'Codex 로그인이 끊겼어요. 설정 › AI 로그인에서 다시 로그인한 뒤 보내 주세요.'; refreshAuth(true); } pushMsg(t, { role: 'warn', kind: f.kind, text: f.text, detail: String(err).trim().split('\n').slice(-3).join(' ').slice(0, 300) }); }
  else { writeTask(t); if (t.runtime === 'codex' && !t.codexPersonal && codexStale()) { clearCodexStale(); refreshAuth(true); } }
  emit({ type: 'status', task: id, status: t.status });
  usageCache.codex.at = 0; // 다음 조회 때 남은 양 새로 읽기
  try { syncMyStaff(); } catch (e) { console.error('[내 직원]', e.message); }
  const fn = afterTurn.get(id); if (fn) { afterTurn.delete(id); try { fn(code); } catch (e) { console.error('[이어가기 오류]', e); } }
  if (restartPending && !running.size) setTimeout(() => maybeRestart('기다리던 작업 끝남'), 1000);
}

// ── 예약해서 보내기: 허브가 켜져 있는 동안 30초마다 확인 ──
// 정한 시각부터 1시간 안에만 보낸다(그보다 늦게 켜졌으면 그날은 건너뜀). 하루 한 번.
function tickSchedules(now = new Date()) {
  const ymd = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  const wd = now.getDay(); const mins = now.getHours() * 60 + now.getMinutes();
  for (const t of allTasks()) {
    const sc = t.schedule; if (!sc || !sc.on || !sc.text || !sc.time || t.runtime === 'aside') continue;
    if (sc.days === 'weekdays' && (wd === 0 || wd === 6)) continue;
    if (sc.lastDay === ymd) continue;
    const [h, mi] = sc.time.split(':').map(Number); const at = h * 60 + mi;
    if (mins < at || mins > at + 60) continue;
    if (running.has(t.id)) continue; // 일하는 중이면 다음 확인 때
    const cur = readTask(t.id); cur.schedule = { ...cur.schedule, lastDay: ymd, lastRun: now.toISOString() }; writeTask(cur);
    try { console.log(`[예약] ${cur.title} · ${sc.time}`); send(cur, sc.text, { internal: true, show: `[예약 ${sc.time}] ${sc.text}` }); } catch (e) { console.error('[예약 실패]', e.message); }
  }
}
setInterval(() => { try { tickSchedules(); } catch (e) { console.error('[예약]', e.message); } }, 30_000).unref();
setTimeout(() => { try { tickSchedules(); } catch {} }, 5000).unref();

// ── 내 직원(my/staff/<이름>/SKILL.md) ──
function myStaff() {
  const dir = path.join(myDir(), 'staff'); const out = [];
  let names = []; try { names = fs.readdirSync(dir); } catch { return out; }
  for (const n of names) {
    const f = path.join(dir, n, 'SKILL.md'); let t; try { t = fs.readFileSync(f, 'utf8'); } catch { continue; }
    const fm = (t.match(/^---\s*\n([\s\S]*?)\n---/) || [])[1] || '';
    const get = (k) => ((fm.match(new RegExp(`^${k}:\\s*(.+)$`, 'm')) || [])[1] || '').replace(/^["']|["']$/g, '').trim();
    out.push({ name: get('title') || n, skill: get('name') || n, role: get('description'), mine: true, at: fs.statSync(f).mtimeMs });
  }
  return out.sort((a, b) => a.at - b.at);
}
let myStaffSig = '';
function syncMyStaff(force) {
  const sig = myStaff().map((x) => x.skill + ':' + x.at).join('|');
  if (!force && sig === myStaffSig) return; myStaffSig = sig;
  const r = spawnSync(process.execPath, [path.join(REPO, 'tools', 'skills-sync.mjs')], { encoding: 'utf8', timeout: 60000, windowsHide: true, env: { ...process.env, AIHUB_HOME: hubHome() } });
  if (r.status !== 0) console.error('[내 직원] 스킬 다시 깔기 실패', (r.stderr || r.stdout || '').slice(-300));
}
// 켤 때: 다른 PC에서 옮겨 온 내 직원처럼 스킬 자리에 아직 없는 직원이 있으면 바로 깐다
setTimeout(() => { try { const L = myStaff(); const miss = L.some((x) => !fs.existsSync(path.join(codexHome(), 'skills', x.skill, 'SKILL.md'))); if (miss) syncMyStaff(true); else myStaffSig = L.map((x) => x.skill + ':' + x.at).join('|'); } catch (e) { console.error('[내 직원]', e.message); } }, 0);

// ── 고를 수 있는 모델 ──
// 기본은 맨 위. Codex는 구독이 내려 준 목록(models_cache.json) 순서 그대로, Claude는 별칭.
// 모델은 대화를 시작할 때만 고른다(대화 중간에 바꾸면 앞 맥락을 다른 모델이 이어받아 흐려진다).
// 보여 줄 모델(민수 지정 2026-11-25). 이름은 각 앱이 보여 주는 그대로, 맨 위가 기본이다.
const CODEX_SHOW = ['gpt-6.2-sol', 'gpt-6.2-astra', 'gpt-6.1-terra', 'gpt-6-luna'];
const CODEX_NAME = { 'gpt-6.2-sol': 'GPT-6.2-Sol', 'gpt-6.2-astra': 'GPT-6.2-Astra', 'gpt-6.1-terra': 'GPT-6.1 Terra', 'gpt-6-luna': 'GPT-6-Luna' };
function modelList() {
  // Codex: 그 PC의 구독 목록(models_cache.json)에 있는 것만, 앱이 쓰는 표시 이름으로. 목록이 없으면 정해 둔 이름으로.
  let have = null;
  for (const home of [codexHome(), sess.personalCodexHome()]) {
    try { const d = JSON.parse(fs.readFileSync(path.join(home, 'models_cache.json'), 'utf8')); have = new Map((d.models || []).map((m) => [m.slug, m.display_name || m.slug])); break; } catch {}
  }
  const codex = CODEX_SHOW.filter((id) => !have || have.has(id)).map((id) => ({ id, label: (have && have.get(id)) || CODEX_NAME[id] }));
  if (codex.length && codex[0].id === CODEX_SHOW[0]) codex[0].id = ''; // 맨 위(GPT-6.2-Sol) = 구독 기본값: -m 없이 돈다
  const claude = [{ id: 'fable', label: 'Fable 5.2' }, { id: 'opus', label: 'Opus 5.5' }, { id: 'sonnet', label: 'Sonnet 5.5' }, { id: 'haiku', label: 'Haiku 5.5' }];
  return { codex: codex.length ? codex : [{ id: '', label: 'GPT-6.2-Sol' }], claude };
}

// ── 붙여 넣은 사진 ──
// 화면이 data URL로 보낸 사진을 허브 폴더(uploads/태스크ID)에 저장한다. 작업 폴더(실제 저장소일 수 있음)는 더럽히지 않는다.
const UPLOADS = path.join(hubHome(), 'uploads');
const IMG_EXT = { 'image/png': '.png', 'image/jpeg': '.jpg', 'image/gif': '.gif', 'image/webp': '.webp' };
const IMG_MAX = 6, IMG_BYTES = 10 << 20;
function sniffImage(b) {
  if (b.length > 8 && b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47) return 'image/png';
  if (b.length > 3 && b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return 'image/jpeg';
  if (b.length > 6 && b.toString('ascii', 0, 4) === 'GIF8') return 'image/gif';
  if (b.length > 12 && b.toString('ascii', 0, 4) === 'RIFF' && b.toString('ascii', 8, 12) === 'WEBP') return 'image/webp';
  return null;
}
// 먼저 전부 검사한다(잘못된 사진이면 작업·파일을 하나도 만들지 않는다)
function checkImages(list) {
  if (!Array.isArray(list) || !list.length) return [];
  if (list.length > IMG_MAX) throw new Error(`사진은 한 번에 ${IMG_MAX}장까지 보낼 수 있어요`);
  return list.map((im) => {
    const m = String(typeof im === 'string' ? im : im?.data || '').match(/^data:(image\/(?:png|jpeg|gif|webp));base64,([A-Za-z0-9+/=]+)$/);
    if (!m) throw new Error('PNG·JPG·GIF·WEBP 사진만 보낼 수 있어요');
    const buf = Buffer.from(m[2], 'base64');
    if (buf.length > IMG_BYTES) throw new Error('사진 한 장이 너무 커요(10MB까지)');
    const mime = sniffImage(buf); // 이름은 .png인데 속은 JPG인 경우가 있어 앞 바이트로 다시 정한다
    if (!mime) throw new Error('PNG·JPG·GIF·WEBP 사진만 보낼 수 있어요');
    return { mime, buf };
  });
}
function saveImages(t, list) {
  const ok = checkImages(list); if (!ok.length) return [];
  const dir = path.join(UPLOADS, t.id); fs.mkdirSync(dir, { recursive: true });
  return ok.map(({ mime, buf }, i) => {
    const name = `${Date.now()}-${i + 1}${IMG_EXT[mime]}`;
    fs.writeFileSync(path.join(dir, name), buf);
    return { name, mime, file: path.join(dir, name) };
  });
}

function send(t, text, { show = null, internal = false, images = [] } = {}) {
  if (running.has(t.id)) throw new Error('이 태스크는 AI가 아직 답하는 중이에요');
  if (images.length && t.runtime === 'aside') throw new Error('Aside 대화에는 사진을 보낼 수 없어요. Codex나 Claude 작업에서 보내 주세요');
  const intent = t.thread_id && !internal && !images.length ? handoffIntent(text) : null;
  if (intent) return { intent: 'handoff', ...intent };
  const imgs = saveImages(t, images);
  if (imgs.length && !String(text).trim()) text = imgs.length > 1 ? '붙여 넣은 사진들을 보고 무엇인지 설명해 줘.' : '붙여 넣은 사진을 보고 무엇인지 설명해 줘.';
  const r = maskSecrets(text);
  pushMsg(t, { role: 'me', text: show || r.text, who: conf.me, ...(show ? { sys: true } : {}), ...(imgs.length ? { images: imgs.map((x) => x.name) } : {}) });
  if (r.count) pushMsg(t, { role: 'warn', text: `키 같은 글자 ${r.count}곳을 가렸어요. 대화·저장소에 남기지 않았어요. 각자 금고(맥 키체인·윈도우 자격 증명 관리자)에 저장해 주세요.` });
  t.status = 'working'; writeTask(t); emit({ type: 'status', task: t.id, status: 'working' });
  running.set(t.id, t.runtime === 'claude' ? runClaudeTurn(t, r.text, imgs) : t.runtime === 'aside' ? runAsideTurn(t, r.text) : runCodexTurn(t, r.text, imgs));
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
    const nt = newTask({ title: `${base} · 이어서 ${gen}`, team: old.team, runtime: old.runtime, cwd: old.cwd, extra: { picked: !!old.picked, gen, continuedFrom: old.id, codexPersonal: old.codexPersonal || false, ...(old.model ? { model: old.model, modelLabel: old.modelLabel } : {}) } });
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
    setTimeout(() => { try { p.kill(); } catch {} end({ status: null, stdout: out, stderr: errt, error: Object.assign(new Error('timeout'), { code: 'TIMEOUT' }) }); }, opt.timeout || 15000);
  });
}
let authCache = null;
// 허브 Codex 로그인 끊김 표시: Codex 실행이 '리프레시 토큰 이미 사용됨/취소됨/401'로 실패하면 표시 파일을 남긴다.
// `codex login status`는 로그인 파일만 읽어서 끊긴 로그인도 '로그인됨'으로 보이기 때문(실측 M1·likim, 11-22).
// 다시 로그인해 auth.json이 새로 써지면(표시 파일보다 새것) 끊김 표시는 무시된다.
const STALE_RE = /refresh token (was )?(already used|revoked|expired)|could not be refreshed|unauthori[sz]ed \(401\)|\b401\b/i;
const staleFile = () => path.join(codexHome(), '.hub-login-stale');
function codexStale() {
  try { const st = fs.statSync(staleFile()); const a = fs.statSync(path.join(codexHome(), 'auth.json')); return st.mtimeMs >= a.mtimeMs; } catch { return false; }
}
function markCodexStale() { try { fs.mkdirSync(codexHome(), { recursive: true }); fs.writeFileSync(staleFile(), new Date().toISOString()); } catch {} }
function clearCodexStale() { try { fs.unlinkSync(staleFile()); } catch {} }
// 예전 설치는 개인 Codex 로그인 파일(~/.codex/auth.json)을 허브로 복사했다. 리프레시 토큰은 한 번만 쓸 수 있어서
// 한쪽이 갱신하면 다른 쪽(허브 또는 개인 Codex)이 끊긴다. 아직 안 갈라진 복사본이면 허브 쪽만 지운다(개인 파일은 건드리지 않음, 값은 출력 안 함).
function dropCopiedCodexLogin() {
  try {
    const hub = path.join(codexHome(), 'auth.json');
    const user = path.join(process.env.CODEX_HOME_USER || path.join(os.homedir(), '.codex'), 'auth.json');
    if (!fs.existsSync(hub) || !fs.existsSync(user) || path.resolve(hub) === path.resolve(user)) return false;
    const rt = (p) => { try { return JSON.parse(fs.readFileSync(p, 'utf8'))?.tokens?.refresh_token || null; } catch { return null; } };
    const a = rt(hub), b = rt(user);
    if (a && b && a === b) { fs.unlinkSync(hub); console.log('[로그인] 허브 Codex 로그인이 개인 로그인 복사본이라 허브 쪽만 지움 → 설정 › AI 로그인에서 허브 로그인 필요'); return true; }
  } catch (e) { console.error('[로그인] 복사본 확인 실패', e.message); }
  return false;
}
dropCopiedCodexLogin();
async function authStatus() {
  // 처음 실행은 오래 걸릴 수 있어(새로 깐 프로그램 검사) 넉넉히 기다린다. 늦는 것과 없는 것은 다르게 알려 준다.
  let c;
  try { const [bin, pre] = codexCommand(); c = await cap(bin, [...pre, 'login', 'status'], { env: codexEnv(), timeout: 30000 }); } catch (e) { c = { status: null, stdout: '', stderr: '', error: Object.assign(e, { code: 'ENOENT' }) }; }
  const cs = cliSpawnArgs(claudeCommand(), ['auth', 'status']);
  const cl = await cap(cs.cmd, cs.args, { shell: cs.shell, timeout: 30000 });
  const ctext = ((c.stdout || '') + (c.stderr || '')).trim();
  const cltext = ((cl.stdout || '') + (cl.stderr || '')).trim();
  let clnice = '', clj = null;
  try { const j = clj = JSON.parse(cl.stdout); clnice = [j.loggedIn ? '로그인됨' : '로그인 안 됨', j.subscriptionType ? `${j.subscriptionType} 구독` : '', j.authMethod === 'claude.ai' ? 'Claude 계정' : j.authMethod && j.authMethod !== 'none' ? j.authMethod : '', j.email ? j.email.replace(/^(.{2}).*(@.*)$/, '$1***$2') : ''].filter(Boolean).join(' · '); } catch {}
  const slow = '확인이 오래 걸려요. 잠시 뒤 다시 확인을 눌러 주세요.';
  // Codex: 이름만 있고 실행이 안 되는 설치본도 있다(실측). 답을 알아볼 수 있을 때만 '있음'으로 본다.
  const cSlow = c.error?.code === 'TIMEOUT', cKnown = /logged in/i.test(ctext);
  const clSlow = cl.error?.code === 'TIMEOUT', clKnown = !!clj || /logged in|not logged/i.test(cltext);
  const codex = { ok: c.status === 0 && cKnown, installed: cSlow || cKnown, text: cSlow ? slow : /logged in using chatgpt/i.test(ctext) ? 'ChatGPT 계정으로 로그인됨' : /not logged/i.test(ctext) ? '로그인 안 됨' : cKnown ? ctext.split('\n').pop().slice(0, 120) : c.error?.code === 'ENOENT' ? 'Codex 프로그램이 없어요' : 'Codex 프로그램이 제대로 실행되지 않아요' };
  if (codex.installed && !cSlow) {
    if (!fs.existsSync(path.join(codexHome(), 'auth.json'))) Object.assign(codex, { ok: false, text: '허브용 Codex 로그인이 필요해요' });
    else if (codexStale()) Object.assign(codex, { ok: false, stale: true, text: '로그인이 끊겼어요. 다시 로그인해 주세요' });
  }
  const claude = { ok: cl.status === 0 && /"loggedIn":\s*true|logged in/i.test(cltext) && !/not logged/i.test(cltext), installed: clSlow || clKnown, text: clSlow ? slow : clKnown ? clnice || cltext.split('\n').slice(0, 3).join(' ').slice(0, 160) : cl.error?.code === 'ENOENT' ? 'Claude 프로그램이 없어요' : 'Claude 프로그램이 제대로 실행되지 않아요' };
  if (!codex.installed && !cSlow) console.error(`[로그인 확인] Codex 실행 안 됨 · ${(c.error?.message || ctext).split('\n')[0].slice(0, 200)}`);
  if (!claude.installed && !clSlow) console.error(`[로그인 확인] Claude 실행 안 됨 · ${(cl.error?.message || cltext).split('\n')[0].slice(0, 200)}`);
  return { pc: pcCheck(), codex, claude, login: { codex: loginView('codex'), claude: loginView('claude') } };
}
// 로그인 상태가 바뀌었을 때만 화면에 알린다. (확인할 때마다 알리면, 설정 › AI 로그인 화면이 그 알림을 받고 다시 확인을 불러
// 끝없이 되풀이된다 — 실측 10초에 12번. 그동안 화면이 '확인하는 중'으로 깜빡여 버튼이 안 눌린다.)
let authBusy = null;
async function refreshAuth(fresh) {
  // 동시에 여러 번 확인하지 않는다. fresh: 로그인·로그아웃 직후처럼 지금부터 새로 확인한 결과가 필요할 때
  if (authBusy) { if (!fresh) return authBusy; await authBusy; if (authBusy) return authBusy; }
  authBusy = (async () => {
    try {
      const a = await authStatus(); const was = authCache;
      authCache = { at: Date.now(), codex: a.codex.ok, claude: a.claude.ok, full: a, sig: JSON.stringify([a.codex, a.claude]) };
      if (!was || was.sig !== authCache.sig) emit({ type: 'auth', codex: a.codex.ok, claude: a.claude.ok });
    } catch (e) { console.error('[로그인 확인 오류]', e); }
    authBusy = null; return authCache;
  })();
  return authBusy;
}
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
// 주소를 이 PC 기본 브라우저로 연다(윈도우는 셸을 거치지 않아 & 가 든 주소도 안전)
// 윈도우: 연결 프로그램 확인 단계에서 '앱 선택' 창만 뜨고 끝나는 PC가 있다(likim 실측).
// 그래서 기본 브라우저의 실행 파일을 직접 찾아 주소를 넘긴다. 못 찾으면 엣지(윈도우 기본 포함).
function winBrowser() {
  const q = (k, v) => spawnSync('reg', ['query', k, ...(v ? ['/v', v] : ['/ve'])], { encoding: 'utf8', windowsHide: true }).stdout || '';
  const prog = (q('HKCU\\Software\\Microsoft\\Windows\\Shell\\Associations\\UrlAssociations\\https\\UserChoice', 'ProgId').match(/ProgId\s+REG_SZ\s+(\S+)/) || [])[1];
  if (prog) {
    const cmd = (q(`HKCR\\${prog}\\shell\\open\\command`).match(/REG_(?:EXPAND_)?SZ\s+(.+)/) || [])[1] || '';
    const exe = (cmd.match(/^"([^"]+\.exe)"/i) || cmd.match(/^(\S+\.exe)/i) || [])[1];
    if (exe && fs.existsSync(exe)) return exe;
  }
  return [process.env['ProgramFiles(x86)'], process.env.ProgramFiles, process.env.LOCALAPPDATA].filter(Boolean).map((d) => path.join(d, 'Microsoft', 'Edge', 'Application', 'msedge.exe')).find((f) => fs.existsSync(f)) || null;
}
function openUrl(u) {
  try {
    const edge = PLATFORM === 'windows' ? winBrowser() : null;
    const c = edge ? spawn(edge, [u], { detached: true, stdio: 'ignore' })
      : PLATFORM === 'windows' ? spawn('rundll32.exe', ['url.dll,FileProtocolHandler', u], { detached: true, stdio: 'ignore', windowsHide: true })
      : spawn(PLATFORM === 'mac' ? 'open' : 'xdg-open', [u], { detached: true, stdio: 'ignore' });
    c.on('error', () => {}); c.unref();
  } catch {}
}
// ── AI 로그인 진행 ──────────────────────────────────────────
// 로그인 프로그램을 띄워 두고(브라우저에서 끝낼 때까지 살아 있어야 한다) 주소·코드를 받아 화면에 보여 준다.
// Codex: 브라우저 로그인이 기본. 주소를 못 받거나 프로그램이 바로 끝나면(포트 1455 충돌 등) 코드 입력 방식으로 바꾼다.
// Claude: 프로그램이 브라우저를 직접 열지 않게 하고(BROWSER), 받은 주소를 허브가 연다. 브라우저에 코드가 나오면 허브에 붙여 넣는다.
const logins = {};
const LOGIN_PIDS = path.join(hubHome(), 'login-pids.json');
const readPids = () => { try { return JSON.parse(fs.readFileSync(LOGIN_PIDS, 'utf8')); } catch { return {}; } };
function notePid(who, pid) { const j = readPids(); if (pid) j[who] = pid; else delete j[who]; try { fs.writeFileSync(LOGIN_PIDS, JSON.stringify(j)); } catch {} }
// 맥은 로그인 프로그램을 따로 묶음(프로세스 그룹)으로 띄워, 그 아래 프로그램까지 한 번에 끈다
function killPid(pid) {
  try { if (PLATFORM === 'windows') spawn('taskkill', ['/PID', String(pid), '/T', '/F'], { windowsHide: true }).on('error', () => {}); else process.kill(-pid, 'SIGTERM'); } catch { try { process.kill(pid); } catch {} }
}
function loginView(who) { const L = logins[who]; return L ? { who, mode: L.mode, state: L.state, url: L.url, copyUrl: L.copyUrl || L.url, code: L.code, canPaste: who === 'claude' && L.state === 'waiting', note: L.note } : null; }
function setLogin(who, L, patch) { if (logins[who] !== L) return; Object.assign(L, patch); emit({ type: 'login', who, login: loginView(who) }); }
function stopLogin(who) {
  const L = logins[who]; if (!L) return;
  delete logins[who]; clearTimeout(L.timer); clearTimeout(L.slow); clearTimeout(L.shimWait); clearInterval(L.poll);
  if (L.child.pid && L.child.exitCode === null && L.child.signalCode === null) killPid(L.child.pid);
  notePid(who, null);
}
// 다시 누를 때: 앞의 로그인 프로그램이 완전히 끝난 뒤(포트 1455를 놓은 뒤) 새로 시작한다
async function stopLoginWait(who) {
  const L = logins[who]; stopLogin(who);
  if (L && L.child.pid && L.child.exitCode === null && L.child.signalCode === null) await new Promise((r) => { const t = setTimeout(r, 3000); L.child.once('close', () => { clearTimeout(t); r(); }); });
}
// 앱을 닫으면 서버가 곧바로 꺼져 진행 중이던 로그인 프로그램이 남는다(실측: 하루 가까이 1455를 잡고 있었다). 다음에 켤 때 치운다.
async function sweepLogins() {
  for (const [who, pid] of Object.entries(readPids())) {
    if (logins[who]) continue;
    try {
      const n = Number(pid); if (!n) continue;
      const r = PLATFORM === 'windows'
        ? await cap('powershell', ['-NoProfile', '-Command', `(Get-CimInstance Win32_Process -Filter "ProcessId=${n}").CommandLine`], {})
        : await cap('ps', ['-A', '-o', 'pgid=,command='], {});
      const line = PLATFORM === 'windows' ? r.stdout || '' : (r.stdout || '').split('\n').filter((l) => Number(l.trim().split(/\s+/)[0]) === n).join('\n');
      if (logins[who]) continue;
      if (/\blogin\b/.test(line) && /codex|claude/i.test(line)) { killPid(n); console.log(`[로그인] 지난번에 남은 ${who} 로그인 프로그램을 정리함`); }
    } catch {}
    notePid(who, null);
  }
}
setTimeout(sweepLogins, 1500);
process.on('exit', () => { for (const L of Object.values(logins)) { try { if (!L.child.pid || L.child.exitCode !== null || L.child.signalCode !== null) continue; if (PLATFORM === 'windows') spawnSync('taskkill', ['/PID', String(L.child.pid), '/T', '/F'], { windowsHide: true }); else process.kill(-L.child.pid, 'SIGTERM'); } catch {} } });
for (const sig of ['SIGTERM', 'SIGINT', 'SIGHUP']) process.on(sig, () => process.exit(0));
// Claude가 브라우저를 열려고 부르는 자리에 끼워 넣는 작은 파일: 받은 주소를 파일에 적기만 한다
function browserShim() {
  try {
    const dir = path.join(hubHome(), 'login'); fs.mkdirSync(dir, { recursive: true });
    const out = path.join(dir, 'claude-url.txt'); try { fs.unlinkSync(out); } catch {}
    if (/\s/.test(dir)) return null; // 띄어쓰기가 든 경로는 프로그램이 제대로 못 부른다 → 주소 직접 열기로 간다
    const shim = path.join(dir, PLATFORM === 'windows' ? 'open-url.cmd' : 'open-url.sh');
    if (PLATFORM === 'windows') fs.writeFileSync(shim, `@echo off\r\n>"${out}" echo %*\r\n`);
    else fs.writeFileSync(shim, `#!/bin/sh\nprintf '%s\\n' "$1" > '${out}'\n`, { mode: 0o755 });
    return { shim, out };
  } catch { return null; }
}
const stripAnsi = (t) => t.replace(/\u001b\[[0-9;?]*[A-Za-z]/g, '');
function startLogin(who, mode = 'browser') {
  stopLogin(who);
  let bin, pre = [];
  if (who === 'codex') [bin, pre] = codexCommand(); else bin = claudeCommand();
  const cs = cliSpawnArgs(bin, [...pre, ...(who === 'codex' ? (mode === 'device' ? ['login', '--device-auth'] : ['login']) : ['auth', 'login'])]);
  const env = who === 'codex' ? codexEnv() : { ...process.env };
  const shim = who === 'claude' ? browserShim() : null;
  if (shim) env.BROWSER = shim.shim;
  const child = spawn(cs.cmd, cs.args, { env, stdio: [who === 'claude' ? 'pipe' : 'ignore', 'pipe', 'pipe'], shell: cs.shell, windowsHide: true, detached: PLATFORM !== 'windows' });
  const L = (logins[who] = { child, mode, state: 'opening', url: '', copyUrl: '', code: '', note: '', buf: '', at: Date.now() });
  if (child.pid) notePid(who, child.pid);
  console.log(`[로그인] ${who} ${mode} 시작 · pid ${child.pid || '-'} · ${bin}`);
  child.stdin?.on('error', () => {});
  const show = (url, opened) => { if (L.state !== 'opening') return; if (opened) openUrl(url); console.log(`[로그인] ${who} 주소 받음 · ${opened ? '허브가 브라우저를 엶' : '프로그램이 브라우저를 엶'}`); setLogin(who, L, { state: 'waiting', url }); };
  const on = (d) => {
    L.buf = (L.buf + stripAnsi(String(d))).slice(-6000);
    if (who === 'claude' && !L.copyUrl) { // 프로그램이 찍는 주소는 로그인 뒤 코드를 보여 주는 주소다(다른 기기에서도 된다) → '주소 복사'에 쓴다
      const u = L.buf.match(/https:\/\/[^\s"']*(?:oauth|authorize)[^\s"']*/i);
      if (u) { L.copyUrl = u[0]; if (L.state === 'opening') { if (!shim) show(u[0], true); else L.shimWait = setTimeout(() => show(u[0], true), 4000); } else setLogin(who, L, {}); } // 가로챈 주소가 안 오면 이 주소를 연다
      return;
    }
    if (L.state !== 'opening') return;
    if (who === 'codex' && mode === 'device') {
      const u = L.buf.match(/https:\/\/\S+\/device\S*/i), k = L.buf.match(/\b[A-Z0-9]{4}-[A-Z0-9]{4,6}\b/);
      if (u && k) { L.code = k[0]; show(u[0], true); }
    } else if (who === 'codex') {
      // 맥은 Codex가 브라우저를 직접 연다(실측). 허브까지 열면 같은 로그인 창이 두 개 뜬다. 안 열렸을 때는 화면의 '로그인 창 다시 열기'로 연다.
      const u = L.buf.match(/https:\/\/[^\s"']*(?:oauth|authorize)[^\s"']*/i); if (u) show(u[0], PLATFORM !== 'mac');
    }
  };
  child.stdout.on('data', on); child.stderr.on('data', on);
  if (shim) L.poll = setInterval(() => { // Claude가 열려던 주소(로그인 뒤 자동으로 끝나는 주소)를 허브가 대신 연다
    let u = ''; try { u = (fs.readFileSync(shim.out, 'utf8').match(/https:\/\/[^\s"']+/) || [''])[0]; } catch {}
    if (u) { clearInterval(L.poll); clearTimeout(L.shimWait); if (L.state === 'opening') show(u, true); }
    else if (L.state !== 'opening') clearInterval(L.poll);
  }, 150);
  child.on('error', (e) => { console.error(`[로그인] ${who} 실행 실패 · ${e.message}`); if (logins[who] === L) { clearInterval(L.poll); clearTimeout(L.shimWait); notePid(who, null); setLogin(who, L, { state: 'failed', note: `${who === 'codex' ? 'Codex' : 'Claude'} 프로그램을 실행하지 못했어요.` }); } });
  child.on('close', async (code) => {
    clearInterval(L.poll); clearTimeout(L.shimWait); clearTimeout(L.timer); clearTimeout(L.slow);
    if (logins[who] !== L) return;
    notePid(who, null);
    const tail = L.buf.trim().split('\n').slice(-3).join(' ').slice(0, 300);
    console.log(`[로그인] ${who} ${mode} 끝 · 코드 ${code} · ${tail.replace(/https:\/\/\S+/g, '(주소)')}`);
    const a = await refreshAuth(true);
    if (logins[who] !== L) return;
    if (a?.[who]) { delete logins[who]; return emit({ type: 'login', who, login: { who, state: 'done' } }); }
    if (L.state === 'failed') return; // 실행 자체가 안 된 경우는 이미 알렸다
    const note = /wasn't accepted|invalid.*code|expired/i.test(L.buf) ? '코드가 맞지 않거나 시간이 지났어요. 로그인을 다시 눌러 주세요.' : L.state === 'opening' ? '로그인 창을 열지 못했어요. 다시 눌러 주세요.' : '로그인이 끝나지 않았어요. 다시 눌러 주세요.';
    setLogin(who, L, { state: 'failed', note });
  });
  // 느린 PC는 프로그램이 뜨는 데만 10초 넘게 걸리기도 한다(실측). 1분이 지나도 주소가 없으면 그때 실패로 본다.
  L.slow = setTimeout(() => { if (logins[who] === L && L.state === 'opening') { stopLogin(who); emit({ type: 'login', who, login: { who, mode, state: 'failed', note: '로그인 창을 열지 못했어요. 인터넷 연결을 확인하고 다시 눌러 주세요.' } }); } }, 60_000);
  // 15분 안에 안 끝나면 정리한다(코드 유효 시간과 같다)
  L.timer = setTimeout(() => { if (logins[who] === L) { stopLogin(who); emit({ type: 'login', who, login: { who, state: 'failed', note: '시간이 지나 로그인을 멈췄어요. 다시 눌러 주세요.' } }); } }, 15 * 60_000);
  return L;
}
// 주소(와 코드)가 나오거나 끝날 때까지 잠깐 기다린다
const loginReady = (L, ms) => new Promise((resolve) => { const t0 = Date.now(); const iv = setInterval(() => { if (L.state !== 'opening' || L.child.exitCode !== null || Date.now() - t0 > ms) { clearInterval(iv); resolve(); } }, 100); });
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
// 사진 6장(장당 10MB, base64로 약 1.37배)까지 넉넉히 받고, 그보다 크면 끊는다
const BODY_MAX = 100 << 20;
const body = (req) => new Promise((r, no) => { let s = '', n = 0, over = false; req.setEncoding('utf8'); req.on('data', (d) => { if (over) return; n += Buffer.byteLength(d); if (n > BODY_MAX) { over = true; s = ''; no(new Error('보낸 내용이 너무 커요. 사진 수를 줄여 주세요')); return req.resume(); } s += d; }); req.on('end', () => { if (over) return; try { r(s ? JSON.parse(s) : {}); } catch { r({}); } }); });
function serveFile(res, file) {
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end('없음'); }
  res.writeHead(200, { 'content-type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream', 'cache-control': 'no-cache' });
  fs.createReadStream(file).pipe(res);
}
function authed(req) { const ip = req.socket.remoteAddress || ''; return ip === '127.0.0.1' || ip === '::1' || ip === '::ffff:127.0.0.1'; }
// 다른 사이트가 브라우저를 거쳐 이 PC의 허브를 부르지 못하게 한다: 주소(Host)가 이 허브가 아니거나, 다른 출처(Origin)에서 온 요청은 받지 않는다.
function sameSite(req, p) {
  const ok = new Set([`127.0.0.1:${PORT}`, `localhost:${PORT}`]);
  if (!ok.has(String(req.headers.host || '').toLowerCase())) return false;
  const o = req.headers.origin;
  if (o !== undefined && !ok.has(String(o).toLowerCase().replace(/^http:\/\//, ''))) return false;
  const s = req.headers['sec-fetch-site'];
  if (s && s !== 'same-origin' && s !== 'none' && p.startsWith('/api/')) return false;
  return true;
}
function lanAddrs() {
  const r = [];
  for (const [n, list] of Object.entries(os.networkInterfaces())) for (const a of list || []) if (a.family === 'IPv4' && !a.internal) r.push({ name: n, ip: a.address, tailscale: a.address.startsWith('100.') });
  return r;
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://x');
  const p = decodeURIComponent(url.pathname);
  if (!authed(req)) { res.writeHead(403); return res.end('이 PC 안에서만 열려요'); }
  if (!sameSite(req, p)) { res.writeHead(403); return res.end('허브 화면에서만 쓸 수 있어요'); }
  try {
    let m;
    if (p === '/api/events') { res.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-cache', connection: 'keep-alive' }); res.write(': ok\n\n'); clients.add(res); req.on('close', () => clients.delete(res)); return; }
    if (p === '/api/state' && req.method === 'GET') return json(res, 200, { me: conf.me, team: conf.team, platform: PLATFORM, teams: TEAMS, tasks: allTasks().map(({ messages, ...t }) => ({ ...t, last: messages.at(-1)?.text?.slice(0, 80) || '', count: messages.length })), learnConsent: conf.learnConsent, introSeen: !!conf.introSeen, pending: learn.pending(hubHome()).length, auth: authCache ? { codex: authCache.codex, claude: authCache.claude } : null });
    if (p === '/api/intro' && req.method === 'POST') { const b = await body(req); conf.introSeen = b.seen !== false; saveConf(); return json(res, 200, { ok: true, seen: conf.introSeen }); }
    if (p === '/api/me' && req.method === 'POST') { const b = await body(req); conf.me = String(b.me || '').slice(0, 20); if (b.team) conf.team = b.team; saveConf(); return json(res, 200, { ok: true }); }
    if (p === '/api/usage') { const c = await codexUsage(); if (url.searchParams.get('claude') === '1') await claudeProbe(true); else claudeProbe(false); return json(res, 200, { codex: c, claude: usageCache.claude }); }
    if (p === '/api/search') return json(res, 200, search(url.searchParams.get('q')));
    if (p === '/api/tasks' && req.method === 'POST') { const b = await body(req); const rt = ['claude', 'aside'].includes(b.runtime) ? b.runtime : 'codex'; if (b.images?.length) { if (rt === 'aside') return json(res, 400, { ok: false, msg: 'Aside 대화에는 사진을 보낼 수 없어요' }); try { checkImages(b.images); } catch (e) { return json(res, 400, { ok: false, msg: e.message }); } } const mdl = String(b.model ?? (modelList()[rt]?.[0]?.id || '')); if (mdl && !(modelList()[rt] || []).some((x) => x.id === mdl)) return json(res, 400, { ok: false, msg: '고를 수 없는 모델이에요' }); const t = newTask({ title: b.title || '새 태스크', team: b.team, runtime: rt, cwd: b.cwd || '', extra: mdl ? { model: mdl, modelLabel: (modelList()[rt] || []).find((x) => x.id === mdl)?.label || mdl } : {} }); if (b.text || b.images?.length) { try { send(t, String(b.text || ''), { images: b.images || [] }); } catch (e) { running.delete(t.id); fs.rmSync(tfile(t.id), { force: true }); fs.rmSync(path.join(UPLOADS, t.id), { recursive: true, force: true }); throw e; } } return json(res, 200, t); }
    if (p === '/api/models') return json(res, 200, modelList());
    if (p === '/api/dirs') return json(res, 200, sess.dirCandidates(url.searchParams.get('q') || '', { recent: conf.recentDirs || [], exclude: hubHome() }));
    if ((m = p.match(/^\/api\/tasks\/([\w-]+)$/))) return json(res, 200, readTask(m[1]));
    if ((m = p.match(/^\/api\/tasks\/([\w-]+)\/send$/)) && req.method === 'POST') { const b = await body(req); const t = readTask(m[1]); return json(res, 200, send(t, String(b.text || ''), { images: b.images || [] })); }
    if ((m = p.match(/^\/api\/tasks\/([\w-]+)\/img\/([\w.-]+)$/))) return serveFile(res, path.join(UPLOADS, m[1], m[2]));
    if ((m = p.match(/^\/api\/tasks\/([\w-]+)\/files$/))) return json(res, 200, taskFiles(readTask(m[1])));
    if ((m = p.match(/^\/api\/tasks\/([\w-]+)\/stop$/)) && req.method === 'POST') { const r = running.get(m[1]); if (!r) return json(res, 200, { ok: true, idle: true }); r.stopped = true; killTree(r); return json(res, 200, { ok: true }); }
    if ((m = p.match(/^\/api\/tasks\/([\w-]+)\/rename$/)) && req.method === 'POST') { const b = await body(req); const t = readTask(m[1]); t.title = String(b.title || '').trim().slice(0, 60) || t.title; writeTask(t); return json(res, 200, { ok: true }); }
    if ((m = p.match(/^\/api\/tasks\/([\w-]+)\/delete$/)) && req.method === 'POST') { if (running.has(m[1])) return json(res, 409, { ok: false, msg: 'AI가 일하는 중이에요. 멈춘 뒤 지워 주세요' }); fs.rmSync(tfile(m[1]), { force: true }); fs.rmSync(path.join(UPLOADS, m[1]), { recursive: true, force: true }); return json(res, 200, { ok: true }); }
    if ((m = p.match(/^\/api\/tasks\/([\w-]+)\/reveal$/)) && req.method === 'POST') { const b = await body(req); const t = readTask(m[1]); return json(res, 200, reveal(t.cwd, b.what === 'terminal' ? 'terminal' : 'folder')); }
    if (p === '/api/reveal' && req.method === 'POST') { const b = await body(req); return json(res, 200, reveal(workRoot(), b.what === 'terminal' ? 'terminal' : 'folder')); }
    // 업데이트: 확인(앱 열 때) · 적용(버튼). 적용이 끝나면 새 코드로 서버를 다시 켠다
    if (p === '/api/update' && req.method === 'GET') return json(res, 200, { ...(await upd.check(url.searchParams.get('force') === '1')), updating: updating || null });
    if (p === '/api/update' && req.method === 'POST') {
      if (updating) return json(res, 409, { ok: false, msg: '이미 업데이트하는 중이에요' });
      if (running.size) return json(res, 409, { ok: false, msg: 'AI가 일하는 중이에요. 끝난 뒤에 업데이트해 주세요' });
      updating = '시작';
      const step = (t) => { updating = t; console.log(`[업데이트] ${t}`); emit({ type: 'update', step: t }); };
      upd.apply(step).then((v) => { step(`v${v} 적용 끝, 다시 켜는 중`); emit({ type: 'update', step: 'restart', version: v }); setTimeout(restartSelf, 600); })
        .catch((e) => { updating = null; console.error('[업데이트 실패]', e); emit({ type: 'update', step: 'fail', msg: String(e.message || e) }); });
      return json(res, 200, { ok: true });
    }
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
    if (p === '/api/staff') { let d; try { d = JSON.parse(fs.readFileSync(path.join(REPO, 'skills', 'staff.json'), 'utf8')); } catch { d = { staff: [] }; } d.mine = myStaff(); return json(res, 200, d); }
    if ((m = p.match(/^\/api\/tasks\/([\w-]+)\/continue$/)) && req.method === 'POST') { const t = readTask(m[1]); return json(res, 200, startContinue(t)); }
    if ((m = p.match(/^\/api\/tasks\/([\w-]+)\/schedule$/)) && req.method === 'POST') {
      const b = await body(req); const t = readTask(m[1]);
      if (t.runtime === 'aside') return json(res, 400, { ok: false, msg: 'Aside 대화는 예약할 수 없어요' });
      const time = /^([01]\d|2[0-3]):[0-5]\d$/.test(String(b.time || '')) ? String(b.time) : null; const text = String(b.text || '').trim().slice(0, 2000);
      if (b.on && (!time || !text)) return json(res, 400, { ok: false, msg: '시각과 보낼 말을 적어 주세요' });
      t.schedule = { ...(t.schedule || {}), on: !!b.on, days: b.days === 'weekdays' ? 'weekdays' : 'daily', time: time || t.schedule?.time || '09:00', text: text || t.schedule?.text || '' };
      writeTask(t); return json(res, 200, { ok: true, schedule: t.schedule });
    }
    if ((m = p.match(/^\/api\/tasks\/([\w-]+)\/mark$/)) && req.method === 'POST') { const b = await body(req); const t = readTask(m[1]); const mk = ['good', 'redo'].includes(b.mark) ? b.mark : null; t.mark = mk ? { mark: mk, note: maskSecrets(String(b.note || '').slice(0, 200)).text, at: new Date().toISOString() } : null; writeTask(t); return json(res, 200, { ok: true, mark: t.mark }); }
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
    // 화면에는 알고 있는 상태를 바로 보여 주고(확인에 몇 초씩 걸리는 PC가 있다 — 실측 3~7초), 뒤에서 다시 확인해 바뀌면 알린다.
    // '다시 확인' 버튼(fresh=1)은 새로 확인한 결과를 기다린다.
    if (p === '/api/auth') {
      if (authCache && url.searchParams.get('fresh') !== '1') { refreshAuth(); return json(res, 200, { ...authCache.full, login: { codex: loginView('codex'), claude: loginView('claude') } }); }
      const a = await refreshAuth(url.searchParams.get('fresh') === '1'); return json(res, 200, a?.full || {});
    }
    if ((m = p.match(/^\/api\/auth\/(codex|claude)\/(login|logout|cancel|code|open)$/)) && req.method === 'POST') {
      const [, who, act] = m; const name = who === 'codex' ? 'Codex' : 'Claude';
      const b = act === 'login' || act === 'code' ? await body(req).catch(() => ({})) : {};
      if (act === 'cancel') { stopLogin(who); return json(res, 200, { ok: true }); }
      if (act === 'open') { const L = logins[who]; if (L?.url) openUrl(L.url); return json(res, 200, { ok: !!L?.url, msg: L?.url ? '브라우저에 로그인 창을 열었어요' : '로그인을 다시 눌러 주세요' }); }
      if (act === 'code') { // 브라우저에 나온 코드를 로그인 프로그램에 넘긴다
        const L = logins[who]; const code = String(b.code || '').trim();
        if (!L || L.state !== 'waiting' || !L.child.stdin?.writable) return json(res, 200, { ok: false, msg: '로그인을 다시 눌러 주세요' });
        if (!code) return json(res, 200, { ok: false, msg: '코드를 붙여 넣어 주세요' });
        L.child.stdin.write(code + '\n'); setLogin(who, L, { state: 'checking' });
        return json(res, 200, { ok: true, msg: '코드를 확인하는 중이에요' });
      }
      if (act === 'logout') {
        stopLogin(who);
        const [bin, pre] = who === 'codex' ? codexCommand() : [claudeCommand(), []];
        const cs = cliSpawnArgs(bin, [...pre, ...(who === 'codex' ? ['logout'] : ['auth', 'logout'])]);
        await cap(cs.cmd, cs.args, { env: who === 'codex' ? codexEnv() : process.env, shell: cs.shell }); await refreshAuth(true);
        return json(res, 200, { ok: true, msg: '로그아웃했어요' });
      }
      let L;
      await stopLoginWait(who);
      try { L = startLogin(who, who === 'codex' && b.mode === 'device' ? 'device' : 'browser'); } catch (e) { return json(res, 200, { ok: false, msg: `${name} 프로그램이 없어요`, login: { who, state: 'failed', note: `${name} 프로그램이 이 PC에 없어요.` } }); }
      await loginReady(L, who === 'codex' ? 15000 : 10000);
      // Codex 브라우저 로그인이 주소도 못 내고 끝났거나 멈췄으면 코드 입력 방식으로 바꾼다
      if (who === 'codex' && L.mode === 'browser' && L.state !== 'waiting' && logins[who] === L) {
        console.log('[로그인] codex 브라우저 방식이 안 돼 코드 입력 방식으로 바꿈');
        try { await stopLoginWait('codex'); L = startLogin('codex', 'device'); await loginReady(L, 15000); } catch {}
      }
      // 아직 여는 중이면 그대로 알려 준다. 주소가 나오면 화면이 스스로 바뀐다.
      const v = loginView(who) || { who, state: 'failed', note: '로그인 창을 열지 못했어요. 다시 눌러 주세요.' };
      return json(res, 200, { ok: v.state !== 'failed', login: v, msg: v.state === 'failed' ? v.note : v.state === 'opening' ? '' : v.mode === 'device' ? '브라우저에 코드 입력 창을 열었어요' : '브라우저에 로그인 창을 열었어요' });
    }
    // 화면
    if (p === '/' || p === '/index.html') return serveFile(res, path.join(PUB, 'index.html'));
    if (p.startsWith('/static/')) { const f = path.resolve(PUB, p.slice(8)); if (!f.startsWith(PUB)) { res.writeHead(403); return res.end(); } return serveFile(res, f); }
    res.writeHead(404); res.end('없음');
  } catch (e) { console.error(`[오류] ${req.method} ${p} · ${e.stack || e}`); json(res, 500, { ok: false, msg: String(e.message || e) }); }
});
// 업데이트 뒤 새 코드로 다시 켜기: 새 서버를 따로 띄우고 지금 서버는 끝낸다.
// 새 서버는 앱이 직접 켠 것이 아니라서, 앱(창 프로그램)이 꺼진 것을 확인했을 때만 스스로 꺼진다.
// 예전에는 '화면 연결이 1분 없으면' 꺼졌는데, 절전·와이파이 변경으로 연결이 잠깐 끊겨도 서버가 꺼져
// 창에 '127.0.0.1 연결 거부'가 남았다(2026-11-27). 앱이 살아 있는 동안은 서버를 끄지 않는다.
let updating = null;
// 앱 프로세스 번호: 앱이 직접 켠 서버면 부모가 앱이다. 다시 켠 서버는 물려받은 번호를 쓴다.
const APP_PID = process.env.AIHUB_IDLE_EXIT ? Number(process.env.AIHUB_APP_PID) || 0 : process.ppid;
const APP_EXE = 'aixschool-hub';
function appAlive() {
  if (APP_PID) { try { process.kill(APP_PID, 0); return true; } catch (e) { if (e.code === 'EPERM') return true; } }
  // 번호를 모르거나(예전 판이 다시 켠 서버) 그 앱이 꺼졌으면 이름으로 찾는다. 앱을 닫았다 바로 다시 켜면 새 앱이 이 서버를 이어 쓰기 때문.
  // 확인 자체가 안 되면 살아 있다고 본다(서버가 남는 편이 낫다).
  try {
    if (PLATFORM === 'windows') {
      const r = spawnSync('tasklist', ['/FI', `IMAGENAME eq ${APP_EXE}.exe`, '/NH'], { windowsHide: true, encoding: 'utf8', timeout: 10000 });
      if (r.status !== 0 || r.error) return true;
      return r.stdout.toLowerCase().includes(`${APP_EXE}.exe`);
    }
    const r = spawnSync('pgrep', ['-x', APP_EXE], { timeout: 10000 });
    return r.status === 1 ? false : true;
  } catch { return true; }
}
function restartSelf() {
  const log = fs.openSync(path.join(hubHome(), 'hub.log'), 'a');
  const c = spawn(process.execPath, [path.join(REPO, 'app', 'server.mjs')], { cwd: REPO, env: { ...process.env, AIHUB_HOME: hubHome(), AIHUB_IDLE_EXIT: '1', AIHUB_APP_PID: APP_PID ? String(APP_PID) : '' }, detached: true, stdio: ['ignore', log, log], windowsHide: true });
  c.unref();
  server.close(); for (const r of clients) { try { r.end(); } catch {} }
  setTimeout(() => process.exit(0), 300);
}
if (process.env.AIHUB_IDLE_EXIT) {
  setInterval(() => { if (running.size || updating || appAlive()) return; console.log('[AI 학교 허브] 앱이 닫혀 서버를 끝냄'); process.exit(0); }, 15000).unref();
}
let listenTries = 0;
server.on('error', (e) => {
  if (e.code === 'EADDRINUSE' && listenTries++ < 40) return setTimeout(() => server.listen(PORT, '127.0.0.1'), 500);
  console.error('[AI 학교 허브] 서버를 열지 못함', e);
  if (e.code === 'EACCES') console.error(`[AI 학교 허브] 윈도우가 ${PORT}번 포트를 쓰지 못하게 막아 둠(Hyper-V·WSL·Docker 예약 포트일 가능성). PC를 다시 시작하면 풀리는 경우가 많음`);
  else if (e.code === 'EADDRINUSE') console.error(`[AI 학교 허브] ${PORT}번 포트를 다른 프로그램이 20초 넘게 쓰고 있음. 작업 관리자에서 남은 Node.js를 끝내고 다시 켜기`);
  process.exit(1);
});
server.listen(PORT, '127.0.0.1', () => {
  console.log(`[AI 학교 허브] v${upd.currentVersion()} 실행 · http://127.0.0.1:${PORT} · 허브 폴더 ${hubHome()} · pid ${process.pid}`);
  // 업데이트로 다시 켜진 서버: 앱 껍데기가 이 판보다 낮으면 같은 판 묶음으로 껍데기도 바꾼다(판마다 한 번)
  if (process.env.AIHUB_IDLE_EXIT && !process.env.AIHUB_NO_SHELL_UPDATE) setTimeout(() => upd.shellUpdate((t) => console.log(t)).then((r) => { if (r !== 'started') console.log(`[앱 업데이트] 건너뜀(${r})`); }).catch((e) => console.error('[앱 업데이트] 실패(허브는 그대로 씀)', e.message)), 4000);
  try { const pc = pcCheck(); console.log(`[이 PC] 사용자 폴더 ${pc.home}${pc.oddHome ? ' (띄어쓰기·한글 있음 → AI를 직접 실행)' : ''} · Claude ${pc.claude.how} ${pc.claude.path} · Codex ${pc.codex.how}`); } catch {}
});
