// 허브 업데이트: GitHub Releases 최신 묶음을 받아 허브 코드(hub/)와 스킬만 바꾼다.
// 작업(work·tasks)·내 자료(my)·로그인(codex-home/auth.json)·키(keys, 키체인)는 건드리지 않는다.
// 앱을 열었을 때만 확인한다(자동 실행·예약 작업 없음).
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
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
