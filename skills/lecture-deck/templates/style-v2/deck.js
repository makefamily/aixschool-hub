/* 덱 스타일 v2 — 넘김 · 단계 · 숫자 · 타이머 · 프롬프터 연결
   웨비나 덱(deck3.js)을 바탕으로, v1 틀의 프롬프터 연결(BroadcastChannel 'aix-deck')과 ?flat=1 한눈 보기를 합쳤다(2026-11-12).
   키: → / Space / Enter 다음 · ← 이전 · Home / End · F 전체화면 · G 장 번호로 이동
   프롬프터와 연결하려면 덱 폴더에서 python -m http.server 8765 --bind 127.0.0.1 (file:// 끼리는 연결 안 됨) */
(function () {
  const S = [...document.querySelectorAll('.sl')], deck = document.getElementById('deck');
  const FLAT = /(\?|&)flat/.test(location.search);
  let i = 0, timerId = null;
  S.forEach(s => { [...s.querySelectorAll('.a')].forEach((el, k) => { if (!el.style.getPropertyValue('--d')) el.style.setProperty('--i', k); }); });

  function fit() { if (FLAT) return; const k = Math.min(innerWidth / 1920, innerHeight / 1080); deck.style.transform = 'translate(-50%,-50%) scale(' + k + ')'; }
  addEventListener('resize', fit);

  /* 숫자: data-to 의 소수 자리수를 그대로 쓴다 (8.96 → 소수 둘째 자리) */
  function fmt(n, dec) { return n.toLocaleString('ko-KR', { minimumFractionDigits: dec, maximumFractionDigits: dec }); }
  function countUp(el) {
    const raw = el.dataset.to, to = +raw, dec = (raw.split('.')[1] || '').length, t0 = performance.now(), dur = 1100;
    if (el._raf) cancelAnimationFrame(el._raf);
    (function f(t) { const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3); el.textContent = fmt(to * e, dec); if (p < 1) el._raf = requestAnimationFrame(f); })(t0);
  }
  function applyStep(s) {
    const st = +(s.dataset.step || 0);
    s.querySelectorAll('[data-step]').forEach(el => el.classList.toggle('hide', +el.dataset.step > st));
  }
  function startTimer(s) {
    clearInterval(timerId); const el = s.querySelector('.timer'); if (!el) return;
    let left = +el.dataset.sec;
    const draw = () => { const m = Math.floor(left / 60), x = left % 60; el.textContent = String(m).padStart(2, '0') + ':' + String(x).padStart(2, '0'); };
    draw(); timerId = setInterval(() => { left = Math.max(0, left - 1); draw(); if (!left) clearInterval(timerId); }, 1000);
  }

  function go(n, back) {
    i = Math.max(0, Math.min(S.length - 1, n));
    S.forEach((s, k) => s.classList.toggle('on', k === i));
    const s = S[i]; s.dataset.step = back ? (s.dataset.steps || 0) : 0; applyStep(s);
    s.querySelectorAll('.cnt').forEach(countUp); startTimer(s);
    s.querySelectorAll('video').forEach(v => { try { v.currentTime = 0; v.play().catch(() => {}); } catch (_) {} });
    S.forEach((x, k) => { if (k !== i) x.querySelectorAll('video').forEach(v => v.pause()); });
    document.getElementById('cur').textContent = i + 1;
    document.querySelector('#prog i').style.width = ((i + 1) / S.length * 100) + '%';
    try { history.replaceState(null, '', location.search + '#' + (i + 1)); } catch (_) {}
    emit();
  }
  window.go = go;
  function next() { const s = S[i], st = +(s.dataset.step || 0), mx = +(s.dataset.steps || 0);
    if (st < mx) { s.dataset.step = st + 1; applyStep(s); emit(); } else go(i + 1); }
  function prev() { const s = S[i], st = +(s.dataset.step || 0);
    if (st > 0) { s.dataset.step = st - 1; applyStep(s); emit(); } else go(i - 1, true); }

  /* ── 프롬프터 연결: 장·단계가 바뀔 때마다 알리고, 프롬프터가 보내는 이동 요청을 받는다 ── */
  let bc = null;
  try { bc = new BroadcastChannel('aix-deck'); } catch (_) {}
  function emit() {
    if (FLAT) return;
    const s = S[i];
    const msg = { t: 'aix-deck', n: i + 1, step: +(s.dataset.step || 0), steps: +(s.dataset.steps || 0), total: S.length };
    try { if (window.opener && !window.opener.closed) window.opener.postMessage(msg, '*'); } catch (_) {}
    try { if (bc) bc.postMessage(msg); } catch (_) {}
  }
  function jump(n, st) {
    go(n - 1);
    const s = S[i], mx = +(s.dataset.steps || 0);
    if (mx) { s.dataset.step = Math.max(0, Math.min(mx, st || 0)); applyStep(s); }
    emit();
  }
  function onMsg(d) {
    if (!d || typeof d !== 'object') return;
    if (d.t === 'aix-goto') jump(+d.n, +d.step || 0);
    else if (d.t === 'aix-hello') emit();
  }
  addEventListener('message', e => onMsg(e.data));
  if (bc) bc.onmessage = e => onMsg(e.data);

  addEventListener('keydown', e => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (['ArrowRight', 'PageDown', ' ', 'Enter'].includes(e.key)) { e.preventDefault(); next(); }
    else if (['ArrowLeft', 'PageUp', 'Backspace'].includes(e.key)) { e.preventDefault(); prev(); }
    else if (e.key === 'Home') go(0); else if (e.key === 'End') go(S.length - 1);
    else if (e.key === 'f' || e.key === 'F') { document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen().catch(() => {}); }
    else if (e.key === 'g' || e.key === 'G') { const n = prompt('몇 번 장으로 갈까요? (1–' + S.length + ')'); if (n) go(+n - 1); }
  });
  let tt = 0;
  addEventListener('click', e => { if (FLAT || Date.now() - tt < 700) return; const v = e.target.closest && e.target.closest('video'); if (v) { v.paused ? v.play().catch(() => {}) : v.pause(); return; } (e.clientX > innerWidth * 0.3) ? next() : prev(); });
  let sx = null;
  addEventListener('touchstart', e => { sx = e.touches[0].clientX; }, { passive: true });
  addEventListener('touchend', e => { if (FLAT || sx === null) return; const dx = e.changedTouches[0].clientX - sx; tt = Date.now(); if (Math.abs(dx) > 40) (dx < 0 ? next() : prev()); else next(); sx = null; });

  /* 공유본: 한 번만 실린 이미지를 제자리에 붙인다 */
  if (window.SHARE_MEDIA) document.querySelectorAll('[data-share]').forEach(el => { el.src = SHARE_MEDIA[el.dataset.share]; });

  if (FLAT) {
    document.body.classList.add('flat');
    S.forEach(s => { s.classList.add('on'); s.dataset.step = s.dataset.steps || 0; applyStep(s); s.querySelectorAll('.cnt').forEach(el => { el.textContent = fmt(+el.dataset.to, (el.dataset.to.split('.')[1] || '').length); }); s.querySelectorAll('.timer').forEach(el => { const t = +el.dataset.sec; el.textContent = String(Math.floor(t / 60)).padStart(2, '0') + ':' + String(t % 60).padStart(2, '0'); }); });
  } else {
    fit();
    const h = parseInt(location.hash.slice(1), 10);
    go(isNaN(h) ? 0 : h - 1);
  }
})();
