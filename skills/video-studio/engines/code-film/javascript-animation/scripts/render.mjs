#!/usr/bin/env node
// render.mjs: seek-render a canvas animation page to MP4, stills, or a contact sheet.
//
// The page must expose:  window.draw(frame)  window.FRAMES  window.FPS
// and optionally:        window.CUES = [seconds, ...]   (scene cuts / hit points for the soundtrack)
//                        window.SCORE = ac => {...}     (Web Audio soundtrack; rendered offline and muxed in)
// It is loaded with ?render so it can skip its own preview loop.
//
// Usage:
//   node render.mjs page.html out.mp4                  full render (H.264, yuv420p)
//   node render.mjs page.html shot --stills 0,150,300  -> shot-0000.jpg shot-0150.jpg ...  (frames; or seconds: 2.5s,7s)
//   node render.mjs page.html sheet.jpg --sheet [1]    one frame every N seconds, tiled into one image
//   node render.mjs page.html phone --phone [2]        one frame every N seconds at 360 px wide, 8-12 per page
//                                                      (-> phone-01.jpg ...): can you read it on a phone?
//   node render.mjs page.html strip --strip 4.2 [--count 12]   consecutive frames from 4.2 s (pops, overlaps)
//   node render.mjs page.html --check                  determinism (same frame twice, other order = same pixels)
//                                                      and loop seam (first vs last frame difference)
//   --sub N [--shutter 0.5]   motion blur for any mode: average N subframes per frame over the shutter
//                             (fraction of a frame). The page's draw() must accept fractional frames.
//                             Don't combine with a page that already blends its own subframes.
// Both are optional. On a full render, CUES are written to <out>.cues.json, and SCORE is rendered
// offline to <out>.wav and muxed into the MP4 (without SCORE the MP4 is silent).
// A full render needs an even canvas size (H.264); an output with no extension gets .mp4.
//
// Needs: node >= 18, `npm i playwright-core`, ffmpeg, and Chrome installed
// (or run `npx playwright install chromium` once).
import { createRequire } from 'node:module';
import { spawn, execFileSync } from 'node:child_process';
import { writeFileSync, mkdtempSync, rmSync, renameSync } from 'node:fs';
import { resolve, join, parse, format } from 'node:path';
import { tmpdir } from 'node:os';
import { pathToFileURL } from 'node:url';

// resolve playwright from the skill folder, else from the project you run it in (where you `npm i playwright-core`)
async function loadChromium() {
  for (const name of ['playwright-core', 'playwright']) {
    try { return (await import(name)).chromium; } catch {}
    try { return createRequire(process.cwd() + '/')(name).chromium; } catch {}
  }
  throw new Error('playwright-core not found: run `npm i playwright-core` in this folder');
}
const chromium = await loadChromium();

const args = process.argv.slice(2);
const [pagePath, outArg] = args;
const opt = name => { const i = args.indexOf(name); return i < 0 ? undefined : (args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true); };
const checkOnly = args.includes('--check');
if (!pagePath || (!outArg && !checkOnly) || (checkOnly && outArg?.startsWith('--') && outArg !== '--check')) { console.error('usage: node render.mjs page.html <out> [--stills f1,f2] [--sheet [s]] [--phone [s]] [--strip s [--count n]] [--sub n [--shutter f]] | page.html --check'); process.exit(1); }
const SUB = Math.max(1, Math.round(Number(opt('--sub')) || 1)), SHUTTER = Number(opt('--shutter')) || 0.5;

let browser;
try { browser = await chromium.launch({ channel: 'chrome' }); } catch { try { browser = await chromium.launch({ channel: 'msedge' }); } catch { browser = await chromium.launch(); } }
const page = await browser.newPage();
const errors = [];
page.on('pageerror', e => errors.push(e.message));
await page.goto(pathToFileURL(resolve(pagePath)).href + '?render');
const info = await page.evaluate(() => {
  const c = document.querySelector('canvas');
  return { FRAMES: window.FRAMES, FPS: window.FPS, CUES: window.CUES, w: c?.width, h: c?.height, hasDraw: typeof window.draw === 'function', hasScore: typeof window.SCORE === 'function' };
});
if (!info.hasDraw || !info.FRAMES || !info.FPS) { console.error('page must define window.draw(frame), window.FRAMES and window.FPS', errors); process.exit(1); }
const stillsOrSheet = opt('--stills') || opt('--sheet') || opt('--phone') || opt('--strip') || checkOnly;
if (!stillsOrSheet && (info.w % 2 || info.h % 2)) { console.error(`canvas is ${info.w}x${info.h}: H.264 needs even width and height; change the <canvas> size`); await browser.close(); process.exit(1); }
// a full render with no extension becomes .mp4; sidecars (.cues.json, .wav) sit next to the output
const out = !stillsOrSheet && !parse(outArg).ext ? outArg + '.mp4' : (checkOnly ? '' : outArg);
const sidecar = ext => { const p = parse(out); return format({ dir: p.dir, name: p.ext ? p.name : p.base, ext }); };

// paint frame f into the page canvas; with --sub, average SUB subframes over the shutter into an accumulator
await page.evaluate(([SUB, SHUTTER]) => {
  const src = document.querySelector('canvas');
  let acc;
  window.__paint = f => {
    if (SUB === 1) { window.draw(f); return src; }
    if (!acc) { acc = document.createElement('canvas'); acc.width = src.width; acc.height = src.height; }
    const x = acc.getContext('2d');
    for (let k = 0; k < SUB; k++) {
      window.draw(Math.min(window.FRAMES - 1e-3, f + (k / SUB) * SHUTTER));
      x.globalAlpha = 1 / (k + 1); x.drawImage(src, 0, 0);          // running mean: sample k weighs 1/(k+1)
    }
    x.globalAlpha = 1; return acc;
  };
  // Chrome moves a canvas that is read back often from GPU to CPU raster, which changes text edges.
  // Read it a few times first so frame 0 is rasterized the same way as frame 900.
  const c2d = src.getContext('2d');
  if (c2d) for (let i = 0; i < 4; i++) { window.draw(0); c2d.getImageData(0, 0, src.width, src.height); }
}, [SUB, SHUTTER]);
if (SUB > 1) console.log(`motion blur: ${SUB} subframes, shutter ${SHUTTER}`);
const grab = f => page.evaluate(f => window.__paint(f).toDataURL('image/jpeg', 0.93).split(',')[1], f);
const jpg = async f => Buffer.from(await grab(f), 'base64');
// for contact sheets: stamp the timestamp in the browser (ffmpeg drawtext is missing from many builds)
const stamped = async (f, fps) => Buffer.from(await page.evaluate(([f, fps]) => {
  const src = window.__paint(f), c = document.createElement('canvas');
  c.width = src.width; c.height = src.height; const x = c.getContext('2d'); x.drawImage(src, 0, 0);
  const s = Math.round(src.width / 16); x.fillStyle = 'rgba(0,0,0,.65)'; x.fillRect(0, 0, s * 3.1, s * 1.3);
  x.fillStyle = '#fff'; x.font = `700 ${Math.round(s * .8)}px monospace`; x.textBaseline = 'middle'; x.fillText((f / fps).toFixed(2) + 's', s * .25, s * .66);
  return c.toDataURL('image/jpeg', .9).split(',')[1];
}, [f, fps]), 'base64');

const tile = (files, cols, rows, tw, file) => execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', files,
  '-vf', `scale=${tw}:-2,tile=${cols}x${rows}`, '-frames:v', '1', file]);

if (checkOnly) {
  // draw each probe frame twice, the second time in reverse order (catches Math.random, Date, carried state).
  // GPU canvas raster can differ by a level or two between identical draws, so judge by size, not by hash.
  const last = info.FRAMES - 1, probe = [0, Math.floor(info.FRAMES / 3), Math.floor(info.FRAMES / 2), last];
  const res = await page.evaluate(probe => {
    const px = f => { const c = window.__paint(f); return c.getContext('2d').getImageData(0, 0, c.width, c.height).data.slice(); };
    const first = {}; for (const f of probe) first[f] = px(f);
    const out = [];
    for (const f of [...probe].reverse()) {
      const A = first[f], B = px(f); let n = 0, big = 0, max = 0;
      for (let i = 0; i < A.length; i += 4) { const d = Math.max(Math.abs(A[i] - B[i]), Math.abs(A[i + 1] - B[i + 1]), Math.abs(A[i + 2] - B[i + 2])); if (d) { n++; if (d > 8) big++; if (d > max) max = d; } }
      out.push({ f, pct: n / (A.length / 4) * 100, bigPct: big / (A.length / 4) * 100, max });
    }
    return out.reverse();
  }, probe);
  const bad = res.filter(r => r.bigPct > 0.05);   // > 0.05% of pixels off by more than 8 levels = real change
  const noise = res.filter(r => r.pct > 0 && r.bigPct <= 0.05);
  console.log(bad.length ? `DETERMINISM FAIL: ${bad.map(r => `frame ${r.f} ${r.bigPct.toFixed(2)}% pixels changed (max ${r.max})`).join(', ')} when redrawn in another order (Math.random, Date, carried state?)`
    : `DETERMINISM PASS: frames ${probe.join(',')} identical in both orders` + (noise.length ? ` (GPU raster noise only: ${noise.map(r => `frame ${r.f} ${r.pct.toFixed(3)}% px, max ${r.max}`).join('; ')})` : ''));
  const seam = await page.evaluate(([a, b]) => {
    const px = f => { const c = window.__paint(f); return c.getContext('2d').getImageData(0, 0, c.width, c.height).data.slice(); };
    const A = px(a), B = px(b); let s = 0; for (let i = 0; i < A.length; i += 4) s += Math.abs(A[i] - B[i]) + Math.abs(A[i + 1] - B[i + 1]) + Math.abs(A[i + 2] - B[i + 2]);
    return s / (A.length / 4) / 3 / 255 * 100;
  }, [0, last]);
  console.log(`LOOP SEAM: first vs last frame differ by ${seam.toFixed(2)}% (loops want < 1%; ignore for non-loop films)`);
  if (bad.length) process.exitCode = 1;
} else if (opt('--phone')) {
  // a phone shows the film about 360 px wide: tile at that size and few per page so the viewer isn't downscaled again
  const every = opt('--phone') === true ? 2 : Number(opt('--phone'));
  const portrait = info.h > info.w, per = portrait ? 8 : 12, cols = 4, rows = per / cols;
  const frames = []; for (let t = every / 2; t * info.FPS < info.FRAMES; t += every) frames.push(Math.min(info.FRAMES - 1, Math.round(t * info.FPS)));
  const pages = Math.ceil(frames.length / per);
  for (let p = 0; p < pages; p++) {
    const dir = mkdtempSync(join(tmpdir(), 'phone-')), chunk = frames.slice(p * per, (p + 1) * per);
    for (let i = 0; i < chunk.length; i++) writeFileSync(join(dir, `f${String(i).padStart(4, '0')}.jpg`), await stamped(chunk[i], info.FPS));
    const file = `${out}-${String(p + 1).padStart(2, '0')}.jpg`;
    tile(join(dir, 'f%04d.jpg'), cols, Math.ceil(chunk.length / cols), 360, file); rmSync(dir, { recursive: true }); console.log(file);
  }
  console.log(`phone check: ${frames.length} frames at 360 px wide (every ${every}s), ${pages} page(s)`);
} else if (opt('--strip')) {
  // consecutive frames around a fast action: pops, one-frame overlaps and flicker that a sheet skips over
  const start = Math.round(Number(opt('--strip')) * info.FPS), count = Number(opt('--count')) || 12;
  const frames = []; for (let i = 0; i < count && start + i < info.FRAMES; i++) frames.push(start + i);
  const dir = mkdtempSync(join(tmpdir(), 'strip-'));
  for (let i = 0; i < frames.length; i++) writeFileSync(join(dir, `f${String(i).padStart(4, '0')}.jpg`), await stamped(frames[i], info.FPS));
  const file = parse(out).ext ? out : out + '.jpg', cols = Math.min(6, frames.length);
  tile(join(dir, 'f%04d.jpg'), cols, Math.ceil(frames.length / cols), 320, file); rmSync(dir, { recursive: true });
  console.log(`strip: ${frames.length} consecutive frames from ${(start / info.FPS).toFixed(2)}s -> ${file}`);
} else if (opt('--stills')) {
  for (const f of String(opt('--stills')).split(',').map(v => v.trim().endsWith('s') ? Math.round(parseFloat(v) * info.FPS) : Number(v))) {
    const file = `${out}-${String(f).padStart(4, '0')}.jpg`; writeFileSync(file, await jpg(f)); console.log(file);
  }
} else if (opt('--sheet')) {
  const every = opt('--sheet') === true ? 1 : Number(opt('--sheet'));
  // sample every N seconds, but step off scene cuts: a frame inside the dip-to-paper looks blank
  const near = t => (info.CUES || []).find(c => Math.abs(t - c) < .35);
  // start half a step in: frame 0 is often an empty fade-in, and cuts tend to sit on whole seconds
  // with dense cues several samples snap to the same cut: keep them in order and drop repeats
  const frames = []; for (let t = every / 2; t * info.FPS < info.FRAMES; t += every) {
    const c = near(t), f = Math.min(info.FRAMES - 1, Math.round((c !== undefined ? c + .45 : t) * info.FPS));
    if (!frames.length || f > frames[frames.length - 1]) frames.push(f);
  }
  const dir = mkdtempSync(join(tmpdir(), 'sheet-'));
  for (let i = 0; i < frames.length; i++) writeFileSync(join(dir, `f${String(i).padStart(4, '0')}.jpg`), await stamped(frames[i], info.FPS));
  const cols = Math.ceil(Math.sqrt(frames.length)), rows = Math.ceil(frames.length / cols);
  tile(join(dir, 'f%04d.jpg'), cols, rows, 360, out);
  rmSync(dir, { recursive: true });
  console.log(`contact sheet: ${frames.length} frames (every ${every}s) -> ${out}`);
} else {
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(info.FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  let ffDone = false, ffCode = null; const closed = new Promise(r => ff.on('close', c => { ffDone = true; ffCode = c; r(); }));
  ff.on('error', e => { console.error('ffmpeg failed to start:', e.message); process.exit(1); });
  ff.stdin.on('error', () => {}); // reported below via the exit code
  for (let f = 0; f < info.FRAMES; f++) {
    if (ffDone) break;
    if (!ff.stdin.write(await jpg(f))) await Promise.race([new Promise(r => ff.stdin.once('drain', r)), closed]);
    if (f % (info.FPS * 5) === 0) console.log(`frame ${f}/${info.FRAMES}`);
  }
  ff.stdin.end();
  await closed;
  if (ffCode !== 0) { console.error(`ffmpeg exited with code ${ffCode}; ${out} is incomplete`); await browser.close(); process.exit(1); }
  console.log(`rendered ${info.FRAMES} frames @ ${info.FPS}fps -> ${out}`);
  if (Array.isArray(info.CUES)) { writeFileSync(sidecar('.cues.json'), JSON.stringify(info.CUES)); console.log(`cues -> ${sidecar('.cues.json')}`); }
  if (info.hasScore) {
    // render the page's Web Audio score offline (deterministic, faster than real time) -> 16-bit WAV
    const wav64 = await page.evaluate(async secs => {
      const SR = 48000, ac = new OfflineAudioContext(2, Math.ceil(SR * secs), SR);
      window.SCORE(ac);
      const buf = await ac.startRendering(), n = buf.length, L = buf.getChannelData(0), R = buf.getChannelData(1);
      let peak = 1e-9; for (let i = 0; i < n; i++) peak = Math.max(peak, Math.abs(L[i]), Math.abs(R[i]));
      const g = .89 / peak, dv = new DataView(new ArrayBuffer(44 + n * 4)), w = (o, s) => [...s].forEach((c, i) => dv.setUint8(o + i, c.charCodeAt(0)));
      w(0, 'RIFF'); dv.setUint32(4, 36 + n * 4, true); w(8, 'WAVEfmt '); dv.setUint32(16, 16, true); dv.setUint16(20, 1, true); dv.setUint16(22, 2, true);
      dv.setUint32(24, SR, true); dv.setUint32(28, SR * 4, true); dv.setUint16(32, 4, true); dv.setUint16(34, 16, true); w(36, 'data'); dv.setUint32(40, n * 4, true);
      for (let i = 0; i < n; i++) { dv.setInt16(44 + i * 4, Math.max(-1, Math.min(1, L[i] * g)) * 32767, true); dv.setInt16(46 + i * 4, Math.max(-1, Math.min(1, R[i] * g)) * 32767, true); }
      const bytes = new Uint8Array(dv.buffer); let bin = ''; for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
      return btoa(bin);
    }, info.FRAMES / info.FPS);
    const wav = sidecar('.wav'), silent = sidecar('.silent.mp4');
    writeFileSync(wav, Buffer.from(wav64, 'base64'));
    renameSync(out, silent);
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', silent, '-i', wav, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', out]);
    rmSync(silent);
    console.log(`soundtrack (window.SCORE) -> ${wav}, muxed into ${out}`);
  }
}
if (errors.length) console.warn('page errors:', errors);
await browser.close();
