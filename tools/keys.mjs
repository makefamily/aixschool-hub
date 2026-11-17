// 키 보관함: 각자 PC의 금고에 키를 넣고 꺼낸다. 키는 화면·대화·파일에 그대로 남기지 않는다.
// 맥: 키체인(서비스 이름 aixschool-hub) · 윈도우: 이 PC 이 계정에서만 풀리는 암호화 파일(DPAPI, 허브 폴더 keys/)
// 사용(스크립트 안에서): import { getKey } from '<hub>/tools/keys.mjs'  → 값은 변수로만 쓴다
// 명령: node tools/keys.mjs has <이름> | list | delete <이름> | set <이름>  (set은 값을 표준입력으로 받는다)
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { PLATFORM, hubHome } from './lib.mjs';

const SERVICE = 'aixschool-hub';
const okName = (n) => /^[A-Z0-9_]{2,64}$/.test(String(n || ''));
const winDir = () => path.join(hubHome(), 'keys');
const ps = (script, input) => spawnSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', script], { input, encoding: 'utf8', windowsHide: true });

export function setKey(name, value) {
  if (!okName(name)) throw new Error('키 이름은 영문 대문자·숫자·_ 만 써요');
  value = String(value || '').trim(); if (!value) throw new Error('값이 비어 있어요');
  if (PLATFORM === 'mac') {
    const r = spawnSync('security', ['add-generic-password', '-U', '-a', name, '-s', SERVICE, '-w', value], { encoding: 'utf8' });
    if (r.status !== 0) throw new Error('키체인에 넣지 못했어요');
  } else if (PLATFORM === 'windows') {
    fs.mkdirSync(winDir(), { recursive: true });
    const out = path.join(winDir(), `${name}.dat`).replace(/'/g, "''");
    const r = ps(`$v=[Console]::In.ReadToEnd().Trim(); $s=ConvertTo-SecureString $v -AsPlainText -Force; ConvertFrom-SecureString $s | Set-Content -LiteralPath '${out}' -Encoding ascii`, value);
    if (r.status !== 0) throw new Error('키를 저장하지 못했어요');
  } else throw new Error('이 PC에서는 키 보관함을 쓸 수 없어요');
  return true;
}
export function getKey(name) {
  if (!okName(name)) return null;
  if (PLATFORM === 'mac') {
    const r = spawnSync('security', ['find-generic-password', '-a', name, '-s', SERVICE, '-w'], { encoding: 'utf8' });
    return r.status === 0 ? r.stdout.replace(/\n$/, '') : null;
  }
  if (PLATFORM === 'windows') {
    const f = path.join(winDir(), `${name}.dat`); if (!fs.existsSync(f)) return null;
    const r = ps(`$s=Get-Content -LiteralPath '${f.replace(/'/g, "''")}' | ConvertTo-SecureString; [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))`);
    return r.status === 0 ? r.stdout.replace(/\r?\n$/, '') : null;
  }
  return null;
}
export const hasKey = (name) => !!getKey(name);
// AI 보호 구역(샌드박스) 안에서는 금고를 직접 못 열 수 있다 → 이 PC의 허브 서버에 묻는다(127.0.0.1, 허브 열쇠 필요)
export async function fetchKey(name) {
  const direct = getKey(name); if (direct) return direct;
  try {
    const conf = JSON.parse(fs.readFileSync(path.join(hubHome(), 'hub.json'), 'utf8').replace(/^\uFEFF/, ''));
    const port = Number(process.env.AIHUB_PORT || 7710);
    const r = await fetch(`http://127.0.0.1:${port}/api/keys/${encodeURIComponent(name)}`, { headers: { 'x-hub-token': conf.token } });
    if (!r.ok) return null; const j = await r.json(); return j.value || null;
  } catch { return null; }
}
export function deleteKey(name) {
  if (!okName(name)) return false;
  if (PLATFORM === 'mac') return spawnSync('security', ['delete-generic-password', '-a', name, '-s', SERVICE]).status === 0;
  const f = path.join(winDir(), `${name}.dat`); if (fs.existsSync(f)) fs.rmSync(f); return true;
}

// 명령으로 쓸 때: 값은 절대 출력하지 않는다
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [cmd, name] = process.argv.slice(2);
  try {
    if (cmd === 'has') { const h = hasKey(name); console.log(h ? `${name}: 있음` : `${name}: 없음`); process.exit(h ? 0 : 1); }
    else if (cmd === 'set') { const v = fs.readFileSync(0, 'utf8'); setKey(name, v); console.log(`${name}: 저장함`); }
    else if (cmd === 'delete') { deleteKey(name); console.log(`${name}: 지움`); }
    else { console.log('사용: has <이름> | set <이름>(값은 표준입력) | delete <이름>'); process.exit(2); }
  } catch (e) { console.error(e.message); process.exit(1); }
}
