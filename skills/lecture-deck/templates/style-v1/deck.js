/* 5차시 덱 v2 — 내비게이션 · 스텝 포커스 · 영상 제어 (8/21 ASC build-v2 deck2.js 개조)
   무대에서 쓰는 키:  → / ← / Space   ·  R 모션 다시  ·  F 전체화면
   G 로 슬라이드 번호 이동. 프롬프터와 양방향 연결(BroadcastChannel 'aix-deck' + postMessage, 10/12 설명회 덱에서 가져옴)
   file:// 끼리는 연결이 안 되니 수업 땐 덱 폴더에서 python -m http.server 8765 --bind 127.0.0.1 */
(function () {
  const S = [...document.querySelectorAll('.slide')];
  const deck = document.getElementById('deck');
  let i = 0;

  function fit() {
    if (document.body.classList.contains('flat')) return;
    const s = Math.min(innerWidth / 1920, innerHeight / 1080);
    deck.style.transform = 'translate(-50%,-50%) scale(' + s + ')';
  }
  addEventListener('resize', fit);

  /* ── 스텝 포커스 ── */
  function applyStep(sl) {
    const st = +(sl.dataset.step || 0);
    let map = [];
    try { map = JSON.parse(sl.dataset.focus || '[]'); } catch (_) {}
    const F = [...sl.querySelectorAll('.focusable')];
    const on = new Set(map[st] || []);
    F.forEach((el, k) => {
      const was = el.classList.contains('act'), now = on.has(k);
      el.classList.toggle('act', now);
      /* 새로 밝혀진 칸의 숫자를 촤르륵 */
      if (now && !was && window.countUp && sl.classList.contains('on'))
        el.querySelectorAll('[data-to]').forEach(window.countUp);
      if (!now && was) el.querySelectorAll('[data-to]').forEach(n => {
        if (n._raf) { cancelAnimationFrame(n._raf); n._raf = null; }
        n.textContent = n.dataset.from || 0;
      });
    });
    /* 순환도: 강조색 호가 밝혀진 마지막 지점까지 그어진다 */
    const arc = sl.querySelector('.cyarc');
    if (arc) {
      const n = +sl.querySelector('.cycle').dataset.n, lit = map[st] || [];
      const frac = lit.length === 0 ? 0 : (lit.length >= n ? 1 : Math.max(...lit) / n);
      arc.style.strokeDashoffset = 100 - frac * 100;
    }
    /* 카드 한 장씩: 썸네일 현재 위치 */
    sl.querySelectorAll('.thumbs .th').forEach((t, k) => t.classList.toggle('cur', on.has(k)));
    sl.querySelectorAll('.stepdots i').forEach((d, k) => d.classList.toggle('on', k <= st));
  }
  function stepFwd() {
    const sl = S[i], max = +(sl.dataset.steps || 0), st = +(sl.dataset.step || 0);
    if (st < max) { sl.dataset.step = st + 1; applyStep(sl); emit(); return true; }
    return false;
  }
  function stepBack() {
    const sl = S[i], st = +(sl.dataset.step || 0);
    if (st > 0) { sl.dataset.step = st - 1; applyStep(sl); emit(); return true; }
    return false;
  }

  /* ── 영상: 켜진 장만 무음 자동재생·반복. 소리 켜기 버튼을 누르면 소리 ── */
  function media(cur) {
    S.forEach(x => {
      const v = x.querySelector('.vside video');
      if (!v) return;
      if (x === cur) {
        try { v.currentTime = 0; } catch (_) {}
        v.play().catch(() => { v.muted = true; v.play().catch(() => {}); });
      } else {
        v.pause();
      }
    });
  }

  function go(n) {
    const prev = i;
    i = Math.max(0, Math.min(S.length - 1, n));
    if (prev !== i) {
      if (window.rewindSlide) rewindSlide(S[prev]);
      if (S[prev].dataset.steps) { S[prev].dataset.step = 0; applyStep(S[prev]); }
      /* 뒤로 왔으면 그 장의 스텝은 끝난 상태로 */
      if (S[i].dataset.steps && i < prev) S[i].dataset.step = S[i].dataset.steps;
    }
    if (S[i].dataset.steps) applyStep(S[i]);
    S.forEach((s, k) => s.classList.toggle('on', k === i));
    /* SVG 타임라인 되감기 — 지도 카메라가 중간부터 돌지 않게 */
    S[i].querySelectorAll('svg').forEach(sv => {
      try { sv.setCurrentTime(0); } catch (_) {}
      sv.querySelectorAll('animateMotion,animate,animateTransform')
        .forEach(a => { try { a.beginElement(); } catch (_) {} });
    });
    document.getElementById('cur').textContent = i + 1;
    media(S[i]);
    if (window.playSlide) playSlide(S[i]);
    try { location.hash = i + 1; } catch (_) {}
    emit();
  }
  window.go = go;

  /* ── 프롬프터 연동: 장·단계가 바뀔 때마다 알리고, 프롬프터가 보내는 이동 요청을 받는다 ── */
  let bc = null;
  try { bc = new BroadcastChannel('aix-deck'); } catch (_) {}
  function emit() {
    const sl = S[i];
    const msg = { t: 'aix-deck', n: i + 1, step: +(sl.dataset.step || 0), steps: +(sl.dataset.steps || 0), total: S.length };
    try { if (window.opener && !window.opener.closed) window.opener.postMessage(msg, '*'); } catch (_) {}
    try { if (bc) bc.postMessage(msg); } catch (_) {}
  }
  function jump(n, st) {
    go(n - 1);
    const sl = S[i], max = +(sl.dataset.steps || 0);
    if (max) { sl.dataset.step = Math.max(0, Math.min(max, st || 0)); applyStep(sl); }
    emit();
  }
  addEventListener('message', e => {
    const d = e.data;
    if (!d || typeof d !== 'object') return;
    if (d.t === 'aix-goto') jump(+d.n, +d.step || 0);
    else if (d.t === 'aix-hello') emit();
  });
  if (bc) bc.onmessage = e => {
    const d = e.data;
    if (d && d.t === 'aix-goto') jump(+d.n, +d.step || 0);
    else if (d && d.t === 'aix-hello') emit();
  };

  /* 소리 켜기 — 한 번 켜면 그 영상은 계속 소리 */
  document.addEventListener('click', e => {
    const b = e.target.closest('.soundbtn');
    if (!b) return;
    e.stopPropagation();
    const v = b.parentElement.querySelector('video');
    v.muted = false;
    v.play().then(() => b.classList.add('hide')).catch(() => { v.muted = true; });
  }, true);

  addEventListener('keydown', e => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const k = e.key;
    if (k === 'ArrowRight' || k === ' ' || k === 'PageDown') { e.preventDefault(); if (!stepFwd()) go(i + 1); }
    else if (k === 'ArrowLeft' || k === 'PageUp') { e.preventDefault(); if (!stepBack()) go(i - 1); }
    else if (k === 'Home') go(0);
    else if (k === 'End') go(S.length - 1);
    else if (k === 'r' || k === 'R') {
      const c = S[i];
      if (window.rewindSlide) rewindSlide(c);
      c.classList.remove('on'); void c.offsetWidth; c.classList.add('on');
      if (window.playSlide) playSlide(c);
    }
    else if (k === 'f' || k === 'F') {
      if (document.fullscreenElement) document.exitFullscreen();
      else document.documentElement.requestFullscreen().catch(() => {});
    }
    else if (k === 'g' || k === 'G') {
      const n = prompt('몇 번 장으로 갈까요? (1–' + S.length + ')');
      if (n) go(+n - 1);
    }
  });

  /* 클릭 — 왼쪽 30%는 뒤로, 나머지는 앞으로 */
  addEventListener('click', e => {
    if (e.target.closest('.soundbtn')) return;
    if (e.clientX < innerWidth * 0.3) { if (!stepBack()) go(i - 1); }
    else { if (!stepFwd()) go(i + 1); }
  });

  /* 공유본: 한 번만 실린 이미지·영상을 제자리에 붙인다 */
  if (window.SHARE_MEDIA) {
    document.querySelectorAll('[data-share]').forEach(el => { el.src = SHARE_MEDIA[el.dataset.share]; });
    document.querySelectorAll('video[data-src]').forEach(v => { v.src = SHARE_MEDIA[v.dataset.src]; });
  }

  /* ?flat=1 — 전 장을 세로로 쌓아 한눈에 검수 */
  if (/(\?|&)flat/.test(location.search)) {
    document.body.classList.add('flat');
    S.forEach(x => {
      x.classList.add('on');
      if (x.dataset.steps) { x.dataset.step = x.dataset.steps; applyStep(x); }
      if (window.playSlide) playSlide(x);
    });
  } else {
    fit();
    const start = parseInt(location.hash.slice(1), 10);
    go(Number.isFinite(start) && start > 0 ? start - 1 : 0);
  }
})();
