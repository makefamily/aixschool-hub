// 자동 점검: 이 PC의 AI 대화 기록에서 "규칙·스킬이 될 만한 말"을 찾아 후보로 만든다.
// - 대화 원문은 이 PC 밖(팀 저장소)으로 나가지 않는다. 후보와 짧은 근거 인용만 사람이 고른 뒤 반영된다.
// - 후보 정리는 이 사람 구독의 Codex로 1번 돌린다(동의한 경우만).
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import { spawn } from 'node:child_process';
import { codexCommand, codexHome, codexEnv, redact, modelArgs, PLATFORM, claudeCommand, cliSpawnArgs, myRulesFile } from '../tools/lib.mjs';

const P = (hub) => path.join(hub, 'learn');
const pendFile = (hub) => path.join(P(hub), 'pending.json');
const logFile = (hub) => path.join(P(hub), 'decided.jsonl');
export const personalFile = () => myRulesFile();
export const pending = (hub) => { try { return JSON.parse(fs.readFileSync(pendFile(hub), 'utf8')); } catch { return []; } };
const savePending = (hub, list) => { fs.mkdirSync(P(hub), { recursive: true }); fs.writeFileSync(pendFile(hub), JSON.stringify(list, null, 2)); };
export const personalRules = (hub) => { try { return fs.readFileSync(personalFile(hub), 'utf8'); } catch { return ''; } };

// 대화 기록 위치(맥·윈도우). 개인 Codex·Claude, 허브 전용 Codex, 맥 Orca의 Codex 계정 폴더.
function sessionRoots() {
  const h = os.homedir();
  const r = [path.join(h, '.codex', 'sessions'), path.join(codexHome(), 'sessions'), path.join(h, '.claude', 'projects')];
  if (PLATFORM === 'mac') {
    const orca = path.join(h, 'Library', 'Application Support', 'Orca', 'codex-accounts');
    if (fs.existsSync(orca)) for (const a of fs.readdirSync(orca)) r.push(path.join(orca, a, 'home', 'sessions'));
  }
  return [...new Set(r)].filter((p) => fs.existsSync(p));
}
function recentFiles(root, since) {
  const out = []; const st = [root];
  while (st.length) {
    const d = st.pop(); let es; try { es = fs.readdirSync(d, { withFileTypes: true }); } catch { continue; }
    for (const e of es) { const p = path.join(d, e.name); if (e.isDirectory()) st.push(p); else if (e.name.endsWith('.jsonl')) { try { if (fs.statSync(p).mtimeMs >= since) out.push(p); } catch {} } }
  }
  return out;
}
const SIGNAL = /하지\s?마|하지마|금지|항상|앞으로|매번|왜 또|다시는|규칙|기억해|말했잖|틀렸|아니라|빼고|넣지\s?마|꼭 |반드시|이렇게 해|이런 식으로|스킬로|자꾸|또 그러|그만/;
function userTexts(file) {
  const out = [];
  for (const l of fs.readFileSync(file, 'utf8').split('\n')) {
    let o; try { o = JSON.parse(l); } catch { continue; }
    let t = '';
    if (o.type === 'response_item' && o.payload?.type === 'message' && o.payload.role === 'user') t = (o.payload.content || []).map((c) => c.text || '').join('');
    else if (o.type === 'user' && o.message?.role === 'user') t = typeof o.message.content === 'string' ? o.message.content : (o.message.content || []).filter((c) => c.type === 'text').map((c) => c.text).join('');
    t = String(t).trim();
    if (!t || t.length > 1500 || t.startsWith('<') || t.startsWith('#') || t.startsWith('[AI 학교 허브]')) continue;
    out.push(t);
  }
  return out;
}
const scrub = (t) => redact(t).text.replace(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}/g, '[메일]').replace(/01[016789]-?\d{3,4}-?\d{4}/g, '[전화]');

function askCodex(prompt, cwd) {
  return new Promise((resolve, reject) => {
    const [bin, pre] = codexCommand();
    const p = spawn(bin, [...pre, 'exec', ...modelArgs(), '--skip-git-repo-check', '--sandbox', 'read-only', '--json', '-'], { cwd, env: codexEnv() });
    p.stdin.end(prompt, 'utf8');
    let out = '', err = '';
    p.stdout.setEncoding('utf8'); p.stdout.on('data', (d) => (out += d)); p.stderr.on('data', (d) => (err += d));
    p.on('close', (code) => {
      let text = '';
      for (const l of out.split('\n')) { try { const o = JSON.parse(l); if (o.type === 'item.completed' && o.item?.type === 'agent_message') text = o.item.text; } catch {} }
      code === 0 && text ? resolve(text) : reject(new Error(err.slice(-400) || `코드 ${code}`));
    });
  });
}

// Codex가 없거나 로그인 안 된 학생은 Claude로 정리한다(도구 없이 답만).
function askClaude(prompt, cwd) {
  return new Promise((resolve, reject) => {
    const c = cliSpawnArgs(claudeCommand(), ['-p', '--output-format', 'text', '--tools', '', '--setting-sources', '']);
    const p = spawn(c.cmd, c.args, { cwd, shell: c.shell });
    p.stdin.end(prompt, 'utf8');
    let out = '', err = '';
    p.stdout.setEncoding('utf8'); p.stdout.on('data', (d) => (out += d)); p.stderr.on('data', (d) => (err += d));
    p.on('error', (e) => reject(e));
    p.on('close', (code) => (code === 0 && out.trim() ? resolve(out) : reject(new Error(err.slice(-400) || `코드 ${code}`))));
  });
}
async function askAny(prompt, cwd) {
  try { return await askCodex(prompt, cwd); } catch (e1) { try { return await askClaude(prompt, cwd); } catch (e2) { throw new Error(`Codex: ${e1.message} / Claude: ${e2.message}`); } }
}

export async function scan({ hub, repo, days = 7, me = '' }) {
  const since = Date.now() - days * 864e5;
  const roots = sessionRoots();
  const snippets = []; let files = 0;
  for (const r of roots) for (const f of recentFiles(r, since)) {
    files++;
    for (const t of userTexts(f)) if (SIGNAL.test(t)) snippets.push(scrub(t).slice(0, 300));
  }
  const uniq = [...new Set(snippets)].slice(-160);
  if (!uniq.length) { savePending(hub, pending(hub)); return { ok: true, files, found: 0, candidates: 0 }; }
  const man = JSON.parse(fs.readFileSync(path.join(repo, 'skills', 'manifest.json'), 'utf8'));
  const skillList = man.skills.map((s) => `- ${s.name}: ${s.desc || ''}`).join('\n');
  const rules = fs.readFileSync(path.join(repo, 'AGENTS.md'), 'utf8').slice(0, 6000);

  const prompt = [
    `너는 AI 학교 허브의 규칙·스킬 점검 담당이다. ${me || '사용자'}님이 최근 ${days}일 동안 AI에게 한 말 중 교정·지시로 보이는 문장들이 아래에 있다.`,
    '이 중 앞으로도 반복해서 지켜야 할 것만 골라 규칙·스킬 후보로 만든다. 한 번만 필요한 지시, 그 작업에만 해당하는 내용은 버린다.',
    '이미 허브 규칙·내 규칙·스킬에 있는 내용이면 새로 만들지 말고 버린다. 규칙 문장은 이 사람이 한 말 그대로의 뜻을 살려 한두 줄로 쓴다.',
    '',
    '출력: JSON 배열만. 최대 10개. 다른 말 금지. 각 항목:',
    '{"title":"짧은 이름","kind":"rule|skill","text":"규칙 문장 한두 줄 또는 스킬이 할 일 설명","evidence":["근거 원문 인용 80자 이내, 최대 2개"],"suggest":"personal","why":"왜 이렇게 제안하는지 한 줄"}',
    '',
    '## 허브 규칙', rules, '', '## 허브 스킬', skillList, '', '## 내 규칙', personalRules(hub) || '(없음)', '',
    '## 최근 교정·지시 문장', ...uniq.map((s) => `- ${s.replace(/\n/g, ' ')}`),
  ].join('\n');
  const text = await askAny(prompt, hub);
  const m = text.match(/\[[\s\S]*\]/);
  let items = []; try { items = JSON.parse(m ? m[0] : text); } catch { throw new Error('후보 정리 결과를 읽지 못했어요: ' + text.slice(0, 200)); }
  const list = pending(hub);
  for (const it of items) list.push({ id: crypto.randomBytes(4).toString('hex'), at: new Date().toISOString(), ...it });
  savePending(hub, list);
  return { ok: true, files, found: uniq.length, candidates: items.length };
}

const today = () => new Date().toISOString().slice(0, 10);
function appendUnder(file, heading, line) {
  let s = fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '';
  const i = s.indexOf(heading);
  if (i < 0) s = s.trimEnd() + `\n\n${heading}\n\n${line}\n`;
  else { const j = s.indexOf('\n## ', i + heading.length); const at = j < 0 ? s.length : j; s = s.slice(0, at).trimEnd() + `\n${line}\n` + s.slice(at); }
  fs.writeFileSync(file, s);
}

// choice: personal(내 전용) | team(팀 공용) | update(기존 것 보완) | discard(버리기)
export function decide({ hub, repo, id, choice, team, me }) {
  const list = pending(hub);
  const it = list.find((x) => x.id === id);
  if (!it) return { ok: false, msg: '후보를 찾지 못했어요' };
  const src = `(${today()}, 근거: ${(it.evidence || [])[0] || '대화 기록'})`;
  if (choice === 'team' || choice === 'update') choice = 'personal'; // 학생 허브는 내 PC에만 쌓는다
  const repoPaths = [];
  const slug = String(it.title).replace(/[^\w가-힣-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 30) || 'skill';
  if (choice === 'personal') {
    if (it.kind === 'skill') {
      const d = path.join(hub, 'personal-skills', slug); fs.mkdirSync(d, { recursive: true });
      fs.writeFileSync(path.join(d, 'SKILL.md'), `---\nname: ${slug}\ndescription: ${it.text.replace(/\n/g, ' ')}\n---\n\n# ${it.title}\n\n${it.text}\n\n${src}\n`);
    } else appendUnder(personalFile(hub), '## 내 규칙', `- ${it.text} ${src}`);
  } else if (choice !== 'discard') return { ok: false, msg: '선택이 올바르지 않아요' };
  savePending(hub, list.filter((x) => x.id !== id));
  fs.appendFileSync(logFile(hub), JSON.stringify({ ...it, choice, by: me, at: new Date().toISOString() }) + '\n');
  return { ok: true, title: it.title, choice, repoPaths };
}
