// 내 PC에 있던 스킬을 찾아 이 PC의 허브에만 넣는다(개인용). 다른 사람에게 올리지 않는다.
// 사용:
//   node tools/skill-register.mjs list            내 스킬 목록 + 허브에 있는지 + 주의할 점
//   node tools/skill-register.mjs add <이름...>   허브 폴더 personal-skills 에 복사
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';
import { REPO, PLATFORM, args, redact, hubHome } from './lib.mjs';

const a = args();
const cmd = a._[0];
const MAN = path.join(REPO, 'skills', 'manifest.json');
const manifest = JSON.parse(fs.readFileSync(MAN, 'utf8'));
const PERSONAL = path.join(hubHome(), 'personal-skills');
const SKIP = new Set(['.system', 'synced', '.DS_Store']);

function localRoots() {
  const h = os.homedir();
  return [
    ['claude', path.join(h, '.claude', 'skills')],
    ['codex', path.join(process.env.CODEX_HOME_USER || path.join(h, '.codex'), 'skills')],
    ['agents', path.join(h, '.agents', 'skills')],
  ].filter(([, p]) => fs.existsSync(p));
}

function readAll(dir, cap = 2_000_000) {
  let out = '', size = 0;
  const walk = (d) => {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      const p = path.join(d, e.name);
      let st; try { st = fs.statSync(p); } catch { continue; }
      if (st.isDirectory()) { if (!['node_modules', '.git', '.venv', '__pycache__'].includes(e.name)) walk(p); continue; }
      size += st.size;
      if (out.length < cap && /\.(md|txt|json|ya?ml|toml|js|mjs|ts|py|sh|ps1|html|css)$/i.test(e.name)) out += '\n' + fs.readFileSync(p, 'utf8');
    }
  };
  walk(dir);
  return { text: out, size };
}

// 맥/윈도우에서 돌 수 있는지 추정. 확실하지 않으면 둘 다로 두고 메모를 남긴다.
function guessOs(t) {
  const mac = /launchctl|osascript|security find-generic-password|pbcopy|\bopen -a\b|~\/Library\/|\/Applications\/|LaunchAgents|keychain/i.test(t);
  const win = /\.ps1\b|powershell|schtasks|C:\\\\|%USERPROFILE%|\$env:/i.test(t);
  if (mac && !win) return { os: ['mac'], why: '맥 전용 명령(키체인·launchd·osascript 등)이 들어 있음' };
  if (win && !mac) return { os: ['windows'], why: '윈도우 전용 명령(PowerShell·C:\\ 경로 등)이 들어 있음' };
  return { os: ['mac', 'windows'], why: mac && win ? '맥·윈도우 명령이 둘 다 있음(둘 다 지원하는 것으로 봄)' : '' };
}
function guessRequires(t) {
  const r = [];
  if (/\bpython3?\b|\.py\b/.test(t)) r.push('python');
  if (/\bnode\b|\.mjs\b|npx\b/.test(t)) r.push('node');
  if (/\borca\b/i.test(t)) r.push('orca');
  if (/hyperframes/i.test(t)) r.push('hyperframes');
  if (/\baside\b/i.test(t)) r.push('aside');
  return [...new Set(r)];
}
function personalHits(t) {
  const h = [];
  if (/\/Users\/[A-Za-z0-9_-]+\/|C:\\\\?Users\\\\?[A-Za-z0-9_-]+/.test(t)) h.push('개인 PC 경로');
  if (/-100\d{9,}|chat_id/.test(t)) h.push('텔레그램 방 번호');
  if (/[A-Za-z0-9._%+-]+@(gmail|naver|daum|kakao)\.(com|net)/i.test(t)) h.push('개인 메일 주소');
  if (/01[016789]-?\d{3,4}-?\d{4}/.test(t)) h.push('전화번호');
  return h;
}

if (cmd === 'list') {
  const inRepo = new Set([...manifest.skills.map((s) => s.name), ...(fs.existsSync(PERSONAL) ? fs.readdirSync(PERSONAL) : [])]);
  const seen = new Map();
  for (const [src, root] of localRoots()) {
    for (const e of fs.readdirSync(root, { withFileTypes: true })) {
      if (SKIP.has(e.name) || e.name.startsWith('.')) continue;
      const dir = path.join(root, e.name);
      if (!fs.existsSync(path.join(dir, 'SKILL.md')) || seen.has(e.name)) continue;
      const { text, size } = readAll(dir);
      let desc = (text.match(/^description:\s*(.+)$/m) || [, ''])[1].trim();
      if (/^[>|]-?$/.test(desc)) desc = (text.match(/^description:\s*[>|]-?\s*\n\s+(.+)$/m) || [, ''])[1];
      desc = desc.replace(/^["']|["']$/g, '').slice(0, 70);
      seen.set(e.name, { name: e.name, from: src, kb: Math.round(size / 1024), registered: inRepo.has(e.name), secrets: redact(text).count, personal: personalHits(text), ...guessOs(text), requires: guessRequires(text), desc });
    }
  }
  const rows = [...seen.values()].sort((x, y) => Number(x.registered) - Number(y.registered) || x.name.localeCompare(y.name));
  if (a.json) { console.log(JSON.stringify(rows, null, 2)); process.exit(0); }
  console.log(`[AI 학교 허브] ${PLATFORM} · 내 스킬 ${rows.length}개 (등록됨 ${rows.filter((r) => r.registered).length})`);
  for (const r of rows) {
    const warn = [r.secrets ? `키 모양 ${r.secrets}곳(등록 불가)` : '', r.personal.length ? r.personal.join('·') : '', r.kb > 3000 ? `${r.kb}KB(큼)` : ''].filter(Boolean).join(', ');
    console.log(`${r.registered ? '[등록됨]' : '[새 스킬]'} ${r.name} · ${r.os.join('/')} · ${r.desc}${warn ? ' · 주의: ' + warn : ''}`);
  }
  process.exit(0);
}

if (cmd === 'add') {
  const names = a._.slice(1);
  if (!names.length) { console.error('사용: add <이름...>'); process.exit(2); }
  const roots = localRoots(); let n = 0;
  for (const name of names) {
    if (!/^[\w.-]+$/.test(name)) { console.error(`[건너뜀] ${name}: 이름이 올바르지 않음`); continue; }
    const hit = roots.map(([, r]) => path.join(r, name)).find((d) => fs.existsSync(path.join(d, 'SKILL.md')));
    if (!hit) { console.error(`[건너뜀] ${name}: 내 PC 스킬 폴더에 없음`); continue; }
    const { text, size } = readAll(hit);
    const sec = redact(text).count;
    if (sec) { console.error(`[넣지 않음] ${name}: 키·토큰 모양 글자 ${sec}곳. 그 부분을 지우거나 금고로 옮긴 뒤 다시`); continue; }
    if (size > 20 * 1024 * 1024) { console.error(`[넣지 않음] ${name}: ${Math.round(size / 1048576)}MB — 너무 큼(20MB 넘음)`); continue; }
    const dst = path.join(PERSONAL, name);
    fs.rmSync(dst, { recursive: true, force: true });
    fs.mkdirSync(PERSONAL, { recursive: true });
    fs.cpSync(hit, dst, { recursive: true, dereference: true, filter: (s) => !/[\\/](node_modules|\.git|\.venv|__pycache__)([\\/]|$)/.test(s) && !/\.DS_Store$/.test(s) });
    console.log(`[허브에 넣음] ${name} · ${guessOs(text).os.join('/')}`); n++;
  }
  process.exit(n ? 0 : 1);
}

console.error('사용: list | add <이름...>');
process.exit(2);
