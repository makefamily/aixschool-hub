// 처음 설치: 이 PC에 허브 폴더를 만들고, Codex 로그인을 붙이고, 허브 스킬·규칙을 깐다.
// 사용: node tools/setup.mjs
// 사용자 개인 Codex 설정(~/.codex/config.toml)은 건드리지 않는다. 로그인 파일만 허브 폴더로 복사한다.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';
import { PLATFORM, hubHome, codexHome, workRoot, codexCommand, codexEnv, REPO, myDir, myRulesFile, ensureMy } from './lib.mjs';

console.log(`[AI 학교 허브] ${PLATFORM} 설치 · 허브 폴더 ${hubHome()}`);
fs.mkdirSync(codexHome(), { recursive: true });
fs.mkdirSync(workRoot(), { recursive: true });

// 1) 허브 전용 Codex 설정 (BOM 없이 UTF-8로 써야 Codex가 읽는다)
const cfg = path.join(codexHome(), 'config.toml');
if (!fs.existsSync(cfg)) {
  fs.writeFileSync(cfg, [
    // 모델은 학생 구독의 기본값을 쓴다(구독마다 쓸 수 있는 모델이 달라서 고정하지 않음)
    'model_reasoning_effort = "medium"',
    'sandbox_mode = "workspace-write"',   // 작업 폴더 안에서만 쓰기
    'approval_policy = "never"',
    // 윈도우: 관리자 설정 없이 쓰는 방식. 실제 화면 세션에서 작업 폴더 쓰기 확인(likim 11-16).
    ...(PLATFORM === 'windows' ? ['', '[windows]', 'sandbox = "unelevated"'] : []),
    '',
  ].join('\n'), { encoding: 'utf8' });
  console.log('  Codex 설정 만듦');
}

// 1-1) 내 규칙 폴더는 Codex가 작업 폴더 밖이어도 쓸 수 있게 연다(이미 있으면 그대로)
myRulesFile(); ensureMy();
{
  let t = fs.readFileSync(cfg, 'utf8').replace(/^\uFEFF/, '');
  // 내 자료 폴더 쓰기 + 인터넷(설치·게시·자료 조사에 필요) 허용
  t = t.replace(/\n*\[sandbox_workspace_write\][\s\S]*?(?=\n\[|$)/, '');
  t = t.trimEnd() + `\n\n[sandbox_workspace_write]\nwritable_roots = ['${myDir()}']\nnetwork_access = true\n`;
  fs.writeFileSync(cfg, t, { encoding: 'utf8' }); console.log('  내 자료 폴더 쓰기·인터넷 허용');
}

// 2) Codex 로그인: 이미 로그인된 PC면 로그인 파일을 복사, 아니면 브라우저 로그인
const auth = path.join(codexHome(), 'auth.json');
const userAuth = path.join(process.env.CODEX_HOME_USER || path.join(os.homedir(), '.codex'), 'auth.json');
if (!fs.existsSync(auth)) {
  if (fs.existsSync(userAuth)) { fs.copyFileSync(userAuth, auth); console.log('  기존 Codex 로그인을 허브에 붙임'); }
  else {
    // Codex가 없거나 로그인을 미루면 건너뛴다. 허브 설정 › AI 로그인에서 나중에 할 수 있다.
    if (process.env.AIHUB_SKIP_LOGIN) console.log('  Codex 로그인은 나중에(허브 설정 › AI 로그인)');
    else try { const [bin, pre] = codexCommand(); console.log('  Codex 로그인이 필요합니다. 브라우저가 열리면 로그인하세요.'); spawnSync(bin, [...pre, 'login'], { stdio: 'inherit', env: codexEnv() }); }
    catch { console.log('  Codex가 이 PC에 없어요. Claude만으로도 허브는 돌아가요.'); }
  }
}

// 3) 허브 스킬·규칙
const sync = spawnSync(process.execPath, [path.join(REPO, 'tools', 'skills-sync.mjs')], { stdio: 'inherit', env: { ...process.env, AIHUB_HOME: hubHome() } });
if (sync.status !== 0) { console.error('[AI 학교 허브] 스킬·규칙 깔기 실패'); process.exit(1); }
console.log('[AI 학교 허브] 설치 끝');
