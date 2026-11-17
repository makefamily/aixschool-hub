// AI 학교 허브 공용 도구 함수 (맥·윈도우 공통, 외부 패키지 없음)
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

export const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const PLATFORM = process.platform === 'win32' ? 'windows' : process.platform === 'darwin' ? 'mac' : 'linux';

// 허브가 쓰는 PC별 폴더. 사용자 개인 Codex·Claude 설정과 섞이지 않게 따로 둔다.
// 기본: 코드가 <허브 폴더>/hub 에 있으면 그 위 폴더가 허브 폴더다(맥 ~/AISchoolHub, 윈도우 C:\\AISchoolHub).
export function hubHome() {
  if (process.env.AIHUB_HOME) return process.env.AIHUB_HOME;
  if (path.basename(REPO) === 'hub') return path.dirname(REPO);
  return PLATFORM === 'windows' ? 'C:\\AISchoolHub' : path.join(os.homedir(), 'AISchoolHub');
}
export const codexHome = () => path.join(hubHome(), 'codex-home');
export const workRoot = () => path.join(hubHome(), 'work');
// 내 규칙 파일: AI가 대화 중에 직접 한 줄씩 보탤 수 있게 이 폴더만 쓰기 허용(Codex writable_roots, Claude --add-dir)
export const myDir = () => path.join(hubHome(), 'my');
export function myRulesFile() {
  const f = path.join(myDir(), 'rules.md');
  try {
    fs.mkdirSync(myDir(), { recursive: true });
    const old = path.join(hubHome(), 'personal-rules.md');
    if (!fs.existsSync(f) && fs.existsSync(old)) fs.renameSync(old, f);
    if (!fs.existsSync(f)) fs.writeFileSync(f, '# 내 규칙\n\n## 내 규칙\n\n');
  } catch {}
  return f;
}
// 내 자료: 비어 있는 틀로 전달하고 학생이 채운다. 채울수록 결과가 내 것처럼 나온다.
const MARK = '<!-- 아래에 적어 주세요 -->';
const TPL = {
  'about.md': `# 나와 내 일\n\nAI가 글·기획·디자인을 할 때 가장 먼저 읽는 파일이에요. 짧게라도 적어 두면 결과가 훨씬 내 일에 맞게 나와요.\nAI에게 "내 자료 같이 채우자"라고 하면 질문하면서 대신 적어 줘요.\n\n- 내가 하는 일(업종·상품·서비스):\n- 내 고객은 누구인가:\n- 고객이 나를 찾는 이유:\n- 지금 가장 걸리는 문제:\n- 자주 쓰는 말·피하는 말:\n- 브랜드 색·글꼴(있으면):\n\n${MARK}\n`,
  'thinking.md': `# 내 생각·원칙\n\n내가 일할 때 지키는 기준, 좋아하는 방식, 절대 하지 않는 것을 적어요. 글의 관점과 판단이 내 것처럼 나와요.\n\n- 일할 때 지키는 기준:\n- 고객에게 꼭 전하고 싶은 것:\n- 하지 않는 것:\n\n${MARK}\n`,
  'writing/README.md': `# 내가 쓴 글\n\n이 폴더에 내가 직접 쓴 글을 3~10편 넣어 주세요(블로그·스레드·인스타·톡 공지 아무거나, 텍스트나 .md 파일).\nAI가 문장 길이·말투·자주 쓰는 표현을 보고 내 글처럼 써요.\n`,
  'refs/README.md': `# 닮고 싶은 레퍼런스\n\n좋아하는 글·디자인·영상의 캡처나 링크를 이 폴더에 넣어 주세요. AI가 구조와 느낌을 참고해요(그대로 베끼지는 않아요).\n`,
};
export function ensureMy() {
  for (const [rel, body] of Object.entries(TPL)) { const f = path.join(myDir(), rel); if (!fs.existsSync(f)) { fs.mkdirSync(path.dirname(f), { recursive: true }); fs.writeFileSync(f, body); } }
  myRulesFile();
}
// 채운 정도: 틀 밖에 내용이 있거나, 폴더에 파일이 있으면 채움
export function myStatus() {
  ensureMy();
  const filled = (rel) => { const t = fs.readFileSync(path.join(myDir(), rel), 'utf8'); const after = t.includes(MARK) ? t.split(MARK)[1] : ''; const lines = t.split('\n').filter((l) => /^- [^:]+:\s*\S/.test(l)).length; return after.replace(/\s/g, '').length >= 20 || lines >= 2; };
  const count = (dir) => { try { return fs.readdirSync(path.join(myDir(), dir)).filter((f) => !f.startsWith('.') && f !== 'README.md').length; } catch { return 0; } };
  const items = [
    { key: 'about', name: '나와 내 일', done: filled('about.md') },
    { key: 'thinking', name: '내 생각·원칙', done: filled('thinking.md') },
    { key: 'writing', name: `내가 쓴 글 ${count('writing')}편`, done: count('writing') >= 3 },
    { key: 'refs', name: `레퍼런스 ${count('refs')}개`, done: count('refs') >= 1 },
  ];
  return { dir: myDir(), items, done: items.filter((x) => x.done).length, total: items.length };
}

// 허브 Codex 실행 환경: 사용자 홈의 개인 스킬(~/.agents/skills 등)이 섞이지 않게 홈을 허브 안 빈 폴더로 돌린다.
// (대화 기록에 개인 규칙·스킬이 남으면 넘길 때 팀 저장소로 같이 올라가기 때문)
export function codexEnv(home = codexHome()) {
  const shim = path.join(hubHome(), 'home-shim');
  fs.mkdirSync(shim, { recursive: true });
  return { ...process.env, CODEX_HOME: home, HOME: shim, USERPROFILE: shim };
}

export function has(cmd) {
  const r = spawnSync(PLATFORM === 'windows' ? 'where' : 'which', [cmd], { stdio: 'ignore' });
  return r.status === 0;
}

// 링크는 실제 내용으로 복사한다(윈도우에서 링크가 안 되는 경우 대비)
export function copyDir(src, dst) {
  fs.cpSync(src, dst, { recursive: true, dereference: true, force: true });
}

// 키·토큰 모양 글자를 가린다. 넘김 꾸러미·대본 저장 전에 반드시 거친다.
const SECRET_PATTERNS = [
  /sk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}/g,
  /gh[pousr]_[A-Za-z0-9]{30,}/g,
  /github_pat_[A-Za-z0-9_]{30,}/g,
  /xox[abpr]-[A-Za-z0-9-]{10,}/g,
  /AKIA[0-9A-Z]{16}/g,
  /AIza[0-9A-Za-z_-]{30,}/g,
  /\b\d{8,10}:[A-Za-z0-9_-]{30,}\b/g, // 텔레그램 봇 토큰
  /eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/g, // JWT
  /-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g,
  /((?:password|passwd|api[_-]?key|secret|token)\s*[:=]\s*["']?)[^\s"',]{8,}/gi,
];
export function redact(text) {
  let n = 0;
  let out = text;
  for (const re of SECRET_PATTERNS) {
    out = out.replace(re, (m, pre) => { n++; return (typeof pre === 'string' && m.startsWith(pre) ? pre : '') + '[가림]'; });
  }
  return { text: out, count: n };
}

export function findRollout(threadId, home = codexHome()) {
  const root = path.join(home, 'sessions');
  if (!fs.existsSync(root)) return null;
  const stack = [root];
  while (stack.length) {
    const d = stack.pop();
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) stack.push(p);
      else if (e.name.endsWith('.jsonl') && e.name.includes(threadId)) return p;
    }
  }
  return null;
}

export function args(argv = process.argv.slice(2)) {
  const o = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) { const k = a.slice(2); const v = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true; o[k] = v; }
    else o._.push(a);
  }
  return o;
}

// 윈도우는 codex.cmd를 셸 없이 못 띄우므로 npm 전역의 codex.js를 node로 직접 실행한다.
// 설치 스크립트가 허브 폴더 안(cli/)에 깐 Codex를 먼저 쓴다(관리자 권한·PATH 필요 없음).
let codexCmd;
export function codexCommand() {
  if (codexCmd) return codexCmd;
  const local = path.join(hubHome(), 'cli', 'node_modules', '@openai', 'codex', 'bin', 'codex.js');
  if (fs.existsSync(local)) return (codexCmd = [process.execPath, [local]]);
  if (PLATFORM !== 'windows') return (codexCmd = ['codex', []]);
  const r = spawnSync('where', ['codex'], { encoding: 'utf8' });
  for (const p of (r.stdout || '').split(/\r?\n/).filter(Boolean)) {
    const js = path.join(path.dirname(p), 'node_modules', '@openai', 'codex', 'bin', 'codex.js');
    if (fs.existsSync(js)) return (codexCmd = [process.execPath, [js]]);
  }
  throw new Error('Codex 프로그램이 이 PC에 없어요. Claude만으로도 허브는 돌아가요.');
}

// Claude CLI 위치: PATH에 없어도 기본 설치 자리(~/.local/bin, ~/.claude/local)를 찾아본다.
let claudeCmd;
export function claudeCommand() {
  if (claudeCmd) return claudeCmd;
  if (process.env.AIHUB_CLAUDE_BIN) return (claudeCmd = PLATFORM === 'windows' ? resolveWinCmd(process.env.AIHUB_CLAUDE_BIN) : process.env.AIHUB_CLAUDE_BIN);
  const home = os.homedir();
  const cands = PLATFORM === 'windows'
    ? [path.join(home, '.local', 'bin', 'claude.exe'), path.join(process.env.APPDATA || '', 'npm', 'claude.cmd')]
    : [path.join(home, '.local', 'bin', 'claude'), path.join(home, '.claude', 'local', 'claude'), '/opt/homebrew/bin/claude', '/usr/local/bin/claude'];
  const r = spawnSync(PLATFORM === 'windows' ? 'where' : 'which', ['claude'], { encoding: 'utf8' });
  // 윈도우의 where는 확장자 없는 셸 스크립트(npm\claude)를 먼저 주는데 그건 실행이 안 된다 → .exe/.cmd만 쓴다
  const found = (r.stdout || '').split(/\r?\n/).filter(Boolean);
  const onPath = PLATFORM === 'windows' ? found.find((f) => /\.exe$/i.test(f)) || found.find((f) => /\.cmd$/i.test(f)) : found[0];
  const picked = onPath || cands.find((c) => fs.existsSync(c)) || 'claude';
  return (claudeCmd = PLATFORM === 'windows' ? resolveWinCmd(picked) : picked);
}

// codex 실행. 질문은 stdin(UTF-8)으로 넘긴다 — 윈도우에서 한글이 깨지지 않게.
export function runCodex(codexArgs, prompt, { cwd, home = codexHome() } = {}) {
  const [bin, pre] = codexCommand();
  const r = spawnSync(bin, [...pre, ...codexArgs], {
    cwd, input: prompt, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024,
    env: codexEnv(home),
  });
  return { status: r.status, stdout: r.stdout || '', stderr: r.stderr || '' };
}

// 모델은 학생 구독의 Codex 기본값을 쓴다. 정해야 할 때만 AIHUB_MODEL 로 고정.
export const MODEL = process.env.AIHUB_MODEL || '';
export const modelArgs = () => (MODEL ? ['-m', MODEL] : []);

// Aside CLI 위치: PATH → ~/.local/bin (윈도우는 aside.exe/aside.cmd)
let asideCmd;
export function asideCommand() {
  if (asideCmd !== undefined) return asideCmd;
  const home = os.homedir();
  const r = spawnSync(PLATFORM === 'windows' ? 'where' : 'which', ['aside'], { encoding: 'utf8' });
  const found = (r.stdout || '').split(/\r?\n/).filter(Boolean);
  const onPath = PLATFORM === 'windows' ? found.find((f) => /\.(exe|cmd)$/i.test(f)) : found[0];
  const cands = PLATFORM === 'windows' ? [path.join(home, '.local', 'bin', 'aside.exe'), path.join(process.env.LOCALAPPDATA || '', 'Aside', 'CLI', 'current', 'aside.exe'), path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Aside', 'aside.exe')] : [path.join(home, '.local', 'bin', 'aside'), '/opt/homebrew/bin/aside', '/usr/local/bin/aside'];
  return (asideCmd = onPath || cands.find((c) => fs.existsSync(c)) || null);
}

// 윈도우 .cmd 껍데기는 cmd.exe를 거쳐야 해서 사용자 이름에 띄어쓰기·한글이 있으면 깨질 수 있다.
// npm 껍데기(claude.cmd)가 부르는 진짜 실행 파일(claude.exe)을 찾아 그걸 직접 실행한다.
export function resolveWinCmd(p) {
  if (!/\.cmd$/i.test(p || '')) return p;
  const dir = path.dirname(p), name = path.basename(p, path.extname(p));
  const exe = [path.join(dir, 'node_modules', '@anthropic-ai', 'claude-code', 'bin', `${name}.exe`), path.join(dir, `${name}.exe`)].find((f) => fs.existsSync(f));
  if (exe) return exe;
  try { // 껍데기 안에 적힌 .exe 경로를 읽는다
    const m = fs.readFileSync(p, 'utf8').match(/"%dp0%\\([^"]+\.exe)"/i);
    if (m) { const f = path.join(dir, m[1]); if (fs.existsSync(f)) return f; }
  } catch {}
  return p;
}
// 실행 방법: .exe 등은 직접(셸 없이), 어쩔 수 없이 .cmd면 따옴표로 감싸 cmd를 거친다
const q = (x) => (x === '' || /[\s&()^%!"<>|]/.test(x) ? `"${String(x).replace(/"/g, '""')}"` : x);
export function cliSpawnArgs(bin, args) {
  if (PLATFORM === 'windows' && /\.cmd$/i.test(bin || '')) return { cmd: q(bin), args: args.map(q), shell: true };
  return { cmd: bin, args, shell: false };
}
// 이 PC 점검: 사용자 폴더 이름과 AI 실행 방법
export function pcCheck() {
  const home = os.homedir();
  const how = (b) => (!b || b === 'claude' && !fs.existsSync(b) && PLATFORM === 'windows' ? 'none' : /\.cmd$/i.test(b) ? 'cmd' : 'direct');
  const cl = claudeCommand(); let ax = null; try { ax = asideCommand(); } catch {}
  let cx = null; try { const [b, pre] = codexCommand(); cx = pre[0] || b; } catch {}
  return { platform: PLATFORM, home, oddHome: /\s|[^\x00-\x7F]/.test(home), claude: { path: cl, how: how(cl) }, codex: { path: cx, how: cx ? 'direct' : 'none' }, aside: { path: ax, how: ax ? how(ax) : 'none' } };
}
