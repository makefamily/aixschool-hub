// 허브 업데이트: GitHub Releases 최신 묶음을 받아 허브 코드(hub/)와 스킬만 바꾼다.
// 작업(work·tasks)·내 자료(my)·로그인(codex-home/auth.json)·키(keys, 키체인)는 건드리지 않는다.
// 앱을 열었을 때만 확인한다(자동 실행·예약 작업 없음).
import fs from 'node:fs';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { REPO, PLATFORM, hubHome } from './lib.mjs';

const FEED = process.env.AIHUB_UPDATE_FEED || 'https://api.github.com/repos/makefamily/aixschool-hub/releases/latest';
const ASSET = PLATFORM === 'windows' ? 'AISchoolHub-windows.zip' : 'AISchoolHub-mac.zip';

export function currentVersion(dir = REPO) {
  try { return fs.readFileSync(path.join(dir, 'VERSION'), 'utf8').trim() || 'dev'; } catch { return 'dev'; }
}
// '0.2.10' > '0.2.9' 처럼 숫자로 비교
export function newer(a, b) {
  const pa = String(a).replace(/^v/, '').split('.').map(Number), pb = String(b).replace(/^v/, '').split('.').map(Number);
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) { const x = pa[i] || 0, y = pb[i] || 0; if (x !== y) return x > y; }
  return false;
}

let cache = { at: 0, data: null };
export async function check(force = false) {
  if (!force && cache.data && Date.now() - cache.at < 6 * 3600e3) return cache.data;
  const current = currentVersion();
  try {
    const r = await fetch(FEED, { headers: { accept: 'application/vnd.github+json', 'user-agent': 'aixschool-hub' }, signal: AbortSignal.timeout(10000) });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const j = await r.json();
    const latest = String(j.tag_name || '').replace(/^v/, '');
    const asset = (j.assets || []).find((a) => a.name === ASSET);
    const data = { current, latest, notes: String(j.body || '').trim().slice(0, 1200), url: asset?.browser_download_url || '', available: current !== 'dev' && !!latest && !!asset && newer(latest, current) };
    cache = { at: Date.now(), data };
    return data;
  } catch (e) { return { current, latest: '', available: false, error: String(e.message || e) }; }
}

// 폴더 맞추기: src 내용으로 dst를 덮어쓰고, src에 없는 것은 지운다. dst 폴더 자체는 지우지 않는다
// (윈도우에서 서버가 이 폴더를 작업 위치로 잡고 있어 폴더째 지우면 실패한다)
function mirror(src, dst) {
  fs.mkdirSync(dst, { recursive: true });
  const want = new Set(fs.readdirSync(src));
  for (const name of fs.readdirSync(dst)) {
    if (want.has(name)) continue;
    fs.rmSync(path.join(dst, name), { recursive: true, force: true });
  }
  for (const name of want) {
    const s = path.join(src, name), d = path.join(dst, name);
    if (fs.statSync(s).isDirectory()) {
      if (fs.existsSync(d) && !fs.statSync(d).isDirectory()) fs.rmSync(d, { force: true });
      mirror(s, d);
    } else {
      if (fs.existsSync(d) && fs.statSync(d).isDirectory()) fs.rmSync(d, { recursive: true, force: true });
      fs.copyFileSync(s, d);
    }
  }
}

// 업데이트 적용. step(글)로 진행을 알린다. 성공하면 새 버전 번호를 돌려준다.
export async function apply(step = () => {}) {
  const info = await check(true);
  if (!info.available) throw new Error(info.error ? `새 버전을 확인하지 못했어요(${info.error})` : '이미 최신 버전이에요');
  const work = path.join(hubHome(), 'update');
  fs.rmSync(work, { recursive: true, force: true });
  fs.mkdirSync(work, { recursive: true });

  step(`v${info.latest} 받는 중`);
  const r = await fetch(info.url, { headers: { 'user-agent': 'aixschool-hub' }, signal: AbortSignal.timeout(300000) });
  if (!r.ok) throw new Error(`묶음을 받지 못했어요(HTTP ${r.status})`);
  const zip = path.join(work, 'bundle.zip');
  fs.writeFileSync(zip, Buffer.from(await r.arrayBuffer()));

  step('압축 푸는 중');
  const x = path.join(work, 'x');
  const u = PLATFORM === 'windows'
    ? spawnSync('powershell', ['-NoProfile', '-Command', `Expand-Archive -LiteralPath '${zip}' -DestinationPath '${x}' -Force`], { encoding: 'utf8', windowsHide: true })
    : spawnSync('ditto', ['-x', '-k', zip, x], { encoding: 'utf8' });
  if (u.status !== 0) throw new Error(`압축을 풀지 못했어요 ${(u.stderr || '').slice(0, 200)}`);
  const newHub = path.join(x, 'AISchoolHub-install', 'hub');
  if (!fs.existsSync(path.join(newHub, 'app', 'server.mjs')) || currentVersion(newHub) !== info.latest) throw new Error('받은 묶음이 올바르지 않아요');

  step('허브 코드 바꾸는 중');
  const prev = path.join(work, 'hub-prev');
  fs.cpSync(REPO, prev, { recursive: true }); // 실패하면 되돌릴 사본
  try {
    mirror(newHub, REPO);
    step('스킬·규칙 다시 까는 중');
    const s = spawnSync(process.execPath, [path.join(REPO, 'tools', 'setup.mjs')], { encoding: 'utf8', windowsHide: true, env: { ...process.env, AIHUB_HOME: hubHome(), AIHUB_SKIP_LOGIN: '1' } });
    if (s.status !== 0) throw new Error(`스킬·규칙 깔기 실패 ${(s.stderr || s.stdout || '').slice(-300)}`);
  } catch (e) {
    try { mirror(prev, REPO); } catch {}
    throw e;
  }
  fs.rmSync(zip, { force: true });
  fs.rmSync(x, { recursive: true, force: true });
  cache = { at: 0, data: null };
  return info.latest;
}

// ── 앱 껍데기(창 프로그램) 바꾸기 ─────────────────────────────
// 허브 업데이트는 hub 폴더만 바꾼다. 껍데기가 이 판보다 낮으면 같은 판 묶음을 다시 받아 껍데기만 새로 깐다.
// 업데이트 직후 한 번만(판마다 한 번) 시도한다. 실패해도 허브는 옛 껍데기로 그대로 돈다.
// 이 값은 desktop/src-tauri/tauri.conf.json 의 version 과 같아야 한다(build-release 가 확인).
export const SHELL_VERSION = '0.3.0';
const APP_DIR_NAME = 'AI 학교 허브';
export function shellNeeded() {
  return newer(SHELL_VERSION, process.env.AIHUB_SHELL_VERSION || '0.2.0');
}
export async function shellUpdate(log = console.log) {
  if (!shellNeeded()) return 'skip';
  const mark = path.join(hubHome(), 'shell-update.json');
  try { if (JSON.parse(fs.readFileSync(mark, 'utf8')).ver === SHELL_VERSION) return 'tried'; } catch {}
  fs.writeFileSync(mark, JSON.stringify({ ver: SHELL_VERSION, from: process.env.AIHUB_SHELL_VERSION || '0.2.0', at: new Date().toISOString() }));
  const ver = currentVersion();
  if (ver === 'dev') return 'dev';
  const work = path.join(hubHome(), 'update', 'shell');
  fs.rmSync(work, { recursive: true, force: true });
  fs.mkdirSync(work, { recursive: true });
  const url = process.env.AIHUB_SHELL_BUNDLE || `https://github.com/makefamily/aixschool-hub/releases/download/v${ver}/${ASSET}`;
  log(`[앱 업데이트] 앱 ${process.env.AIHUB_SHELL_VERSION || '0.2.0'} → ${SHELL_VERSION}, 묶음 받는 중`);
  let zip = url;
  if (/^https?:/.test(url)) {
    const r = await fetch(url, { headers: { 'user-agent': 'aixschool-hub' }, signal: AbortSignal.timeout(300000) });
    if (!r.ok) throw new Error(`묶음을 받지 못함(HTTP ${r.status})`);
    zip = path.join(work, 'bundle.zip');
    fs.writeFileSync(zip, Buffer.from(await r.arrayBuffer()));
  }
  const x = path.join(work, 'x');
  const u = PLATFORM === 'windows'
    ? spawnSync('powershell', ['-NoProfile', '-Command', `Expand-Archive -LiteralPath '${zip}' -DestinationPath '${x}' -Force`], { encoding: 'utf8', windowsHide: true })
    : spawnSync('ditto', ['-x', '-k', zip, x], { encoding: 'utf8' });
  if (u.status !== 0) throw new Error(`압축을 풀지 못함 ${(u.stderr || '').slice(0, 200)}`);
  const inst = path.join(x, 'AISchoolHub-install');
  const hubLog = path.join(hubHome(), 'hub.log');
  if (PLATFORM === 'windows') {
    const exe = fs.readdirSync(inst).find((f) => /setup.*\.exe$/i.test(f));
    if (!exe) throw new Error('묶음에 앱 설치 파일이 없음');
    const m = exe.match(/_(\d+\.\d+\.\d+)_/);
    if (m && m[1] !== SHELL_VERSION) throw new Error(`묶음의 앱 판(${m[1]})이 기대(${SHELL_VERSION})와 다름`);
    const setup = path.join(work, 'shell-setup.exe');
    fs.copyFileSync(path.join(inst, exe), setup);
    const known = process.env.AIHUB_SHELL_PATH || '';
    const q = (s) => s.replace(/'/g, "''");
    // 앱을 닫고 설치 파일(/S)로 바꾼 뒤 앱을 다시 켠다. 기록은 hub.log 에.
    const ps = [
      "$ErrorActionPreference = 'SilentlyContinue'",
      `$log = '${q(hubLog)}'`,
      'function L($t) { [IO.File]::AppendAllText($log, "[앱 업데이트] $t`r`n") }',
      'Start-Sleep 2',
      // 설치 파일(/S)은 앱이 켜져 있으면 바꾸지 않고 멈춘다(종료 코드 2, 윈도우 실측) → 앱을 먼저 닫는다
      'Get-Process aixschool-hub -ErrorAction SilentlyContinue | Stop-Process -Force',
      'for ($i = 0; $i -lt 20 -and (Get-Process aixschool-hub -ErrorAction SilentlyContinue); $i++) { Start-Sleep -Milliseconds 500 }',
      `$p = Start-Process '${q(setup)}' -ArgumentList '/S' -PassThru -Wait`,
      'L "설치 파일 끝(코드 $($p.ExitCode))"',
      'Start-Sleep 2',
      // 업데이트용 환경 값을 새 앱에 물려주지 않는다(새 앱은 보통 켤 때와 똑같이 시작)
      "'AIHUB_IDLE_EXIT', 'AIHUB_APP_PID', 'AIHUB_SHELL_VERSION', 'AIHUB_SHELL_PATH', 'AIHUB_SHELL_BUNDLE' | % { Remove-Item \"Env:$_\" -ErrorAction SilentlyContinue }",
      "if (-not (Get-Process aixschool-hub -ErrorAction SilentlyContinue)) {",
      `  $exe = '${q(known)}'`,
      `  if (-not $exe -or -not (Test-Path $exe)) { $exe = Join-Path $env:LOCALAPPDATA '${APP_DIR_NAME}\\aixschool-hub.exe' }`,
      "  if (-not (Test-Path $exe)) { $exe = (Get-ChildItem $env:LOCALAPPDATA -Recurse -Filter 'aixschool-hub.exe' -ErrorAction SilentlyContinue | Select-Object -First 1).FullName }",
      '  if ($exe) { Start-Process $exe; L "앱 다시 켬" } else { L "앱 실행 파일을 못 찾음" }',
      '}',
    ].join('\r\n');
    const ps1 = path.join(work, 'shell-install.ps1');
    fs.writeFileSync(ps1, '﻿' + ps, 'utf8');
    // detached 로 띄우면 PowerShell이 아무것도 안 하고 바로 끝난다(윈도우 실측). 윈도우는 서버가 꺼져도 자식이 남으므로 분리하지 않는다
    spawn('powershell', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-File', ps1], { stdio: 'ignore', windowsHide: true }).on('error', (e) => log(`[앱 업데이트] 설치 스크립트를 못 띄움 ${e.message}`)).unref();
    log('[앱 업데이트] 설치 파일 실행(앱이 잠깐 닫혔다 다시 열림)');
    return 'started';
  }
  // 맥: .app 을 바꿔 넣고 앱을 다시 켠다
  const app = path.join(inst, `${APP_DIR_NAME}.app`);
  if (!fs.existsSync(app)) throw new Error('묶음에 앱이 없음');
  const fromEnv = (process.env.AIHUB_SHELL_PATH || '').match(/^(.*\.app)\/Contents\/MacOS\//)?.[1];
  const target = [fromEnv, path.join(process.env.HOME || '', 'Applications', `${APP_DIR_NAME}.app`), `/Applications/${APP_DIR_NAME}.app`].find((p) => p && fs.existsSync(p));
  if (!target) throw new Error('설치된 앱 위치를 못 찾음');
  const sh = path.join(work, 'shell-install.sh');
  const Q = (s) => `'${s.replace(/'/g, `'\\''`)}'`;
  fs.writeFileSync(sh, [
    '#!/bin/sh',
    `L() { echo "[앱 업데이트] $1" >> ${Q(hubLog)}; }`,
    `T=${Q(target)}; N=${Q(app)}`,
    'sleep 2',
    'xattr -dr com.apple.quarantine "$N" 2>/dev/null',
    'pkill -x aixschool-hub; for i in 1 2 3 4 5 6 7 8 9 10; do pgrep -x aixschool-hub >/dev/null || break; sleep 1; done',
    'rm -rf "$T.old"; if mv "$T" "$T.old" && ditto "$N" "$T"; then rm -rf "$T.old"; L "앱 바꿈"; else rm -rf "$T"; mv "$T.old" "$T"; L "앱 바꾸기 실패, 원래 앱 그대로"; fi',
    '[ -n "$AIHUB_SHELL_NO_OPEN" ] || open "$T"',
  ].join('\n'));
  fs.chmodSync(sh, 0o755);
  spawn('/bin/sh', [sh], { detached: true, stdio: 'ignore' }).unref();
  log('[앱 업데이트] 앱 바꾸는 중(앱이 잠깐 닫혔다 다시 열림)');
  return 'started';
}
