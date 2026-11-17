// Threads 게시 도구 (메이크패밀리 스레드 운영 흐름: 글 만들기 → 처리 확인 → 게시 → 링크 확인)
// 키: 허브 연결 화면에서 넣은 THREADS_ACCESS_TOKEN (각자 PC 금고). 키 값은 출력하지 않는다.
// 사용: node threads-post.mjs check                 연결 확인(내 계정 이름)
//       node threads-post.mjs post <글파일> --yes   글 파일 내용을 게시(사람이 확인한 뒤에만 --yes)
//       node threads-post.mjs refresh               장기 토큰 연장(60일)
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HOST = 'https://graph.threads.net/v1.0';
// 허브 폴더의 키 보관함 찾기(스킬 위치에서 위로 올라가며 hub/tools/keys.mjs)
async function keys() {
  let d = path.dirname(fileURLToPath(import.meta.url));
  for (let i = 0; i < 8; i++) { const f = path.join(d, 'hub', 'tools', 'keys.mjs'); if (fs.existsSync(f)) return import(pathToFileURL(f).href); d = path.dirname(d); }
  if (process.env.AIHUB_HOME) return import(pathToFileURL(path.join(process.env.AIHUB_HOME, 'hub', 'tools', 'keys.mjs')).href);
  throw new Error('허브 키 보관함을 찾지 못했어요');
}
const hide = (s) => String(s).replace(/(access_token=)[^&\s]+/g, '$1[가림]');
async function call(method, url, params) {
  const u = new URL(url);
  const opt = { method };
  if (method === 'GET') for (const [k, v] of Object.entries(params)) u.searchParams.set(k, v);
  else opt.body = new URLSearchParams(params);
  const r = await fetch(u, opt); const j = await r.json().catch(() => ({}));
  if (!r.ok || j.error) { const m = j.error?.message || r.statusText; const e = new Error(`${r.status} ${hide(m)}`); e.status = r.status; e.code = j.error?.code; throw e; }
  return j;
}
function why(e) {
  if (e.status === 401 || e.code === 190) return '토큰이 없거나 만료됐어요. 허브 설정 › 연결 › Threads 에서 새 토큰을 넣어 주세요.';
  if (e.status === 429 || e.code === 4) return '게시 한도에 걸렸어요(하루 250개 등). 잠시 뒤 다시 해 주세요.';
  return '게시하지 못했어요: ' + e.message;
}

const [cmd, file, ...rest] = process.argv.slice(2);
try {
  const k = await keys();
  const token = await k.fetchKey('THREADS_ACCESS_TOKEN');
  if (!token) { console.log('연결 필요: Threads 토큰이 아직 없어요. 허브 설정 › 연결 › Threads 에서 "AI에게 연결 도와 달라"를 눌러 주세요.'); process.exit(3); }
  if (cmd === 'check') { const me = await call('GET', `${HOST}/me`, { fields: 'id,username', access_token: token }); console.log(`연결됨: @${me.username}`); }
  else if (cmd === 'refresh') { const r = await call('GET', 'https://graph.threads.net/refresh_access_token', { grant_type: 'th_refresh_token', access_token: token }); k.setKey('THREADS_ACCESS_TOKEN', r.access_token); console.log(`토큰 연장함 · 약 ${Math.round((r.expires_in || 0) / 86400)}일`); }
  else if (cmd === 'post') {
    const text = fs.readFileSync(file, 'utf8').trim();
    if (!text) throw new Error('글이 비어 있어요');
    if ([...text].length > 500) { console.log(`글이 ${[...text].length}자예요. Threads는 500자까지라 줄여야 해요.`); process.exit(4); }
    if (!rest.includes('--yes')) { console.log(`미리보기(${[...text].length}자)\n---\n${text}\n---\n사람이 "올려도 돼"라고 확인한 뒤 --yes 를 붙여 다시 실행하세요.`); process.exit(0); }
    const c = await call('POST', `${HOST}/me/threads`, { media_type: 'TEXT', text, access_token: token });
    for (let i = 0; i < 10; i++) { const s = await call('GET', `${HOST}/${c.id}`, { fields: 'status,error_message', access_token: token }); if (s.status === 'FINISHED' || !s.status) break; if (s.status === 'ERROR') throw new Error(s.error_message || '처리 실패'); await new Promise((r) => setTimeout(r, 2000)); }
    const p = await call('POST', `${HOST}/me/threads_publish`, { creation_id: c.id, access_token: token });
    const info = await call('GET', `${HOST}/${p.id}`, { fields: 'permalink,timestamp', access_token: token }).catch(() => ({}));
    const log = path.join(path.dirname(path.resolve(file)), 'posted.json');
    const list = fs.existsSync(log) ? JSON.parse(fs.readFileSync(log, 'utf8')) : [];
    list.push({ file: path.basename(file), id: p.id, permalink: info.permalink || '', at: new Date().toISOString() });
    fs.writeFileSync(log, JSON.stringify(list, null, 2));
    console.log(`게시함: ${info.permalink || p.id}`);
  } else { console.log('사용: check | post <글파일> [--yes] | refresh'); process.exit(2); }
} catch (e) { console.log(why(e)); process.exit(1); }
