/* 5차시 덱 v2 모션 런타임 (8/21 ASC build-v2 motion.js 개조) — 라이브러리 없음, Chrome 기준
   1) 슬라이드 진입 시 요소를 등장 순서대로 지연 부여
   2) [data-to] 숫자를 촤르륵 카운트업 (콤마·소수점·접두 지원)
   3) 뒤로 갔다 다시 오면 다시 재생 */
(function () {
  const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* 등장 순서 = DOM 순서. 슬라이드마다 처음 한 번만 계산 */
  function stamp(slide) {
    if (slide.dataset.stamped) return;
    const seq = slide.querySelectorAll('.anim,.reveal,.eyebrow,.stat+.stat,.flow .node+.node,.anim-flow,.anim-stop,.anim-eq,.anim-row,.anim-pop,.cyn,.tail');
    let i = 0;
    seq.forEach(el => {
      const step = el.classList.contains('tail') ? 120 : 78;
      el.style.setProperty('--d', (i * step + 80) + 'ms');
      i++;
    });
    /* flow 화살표는 마지막 노드가 선 뒤에 */
    const arrows = slide.querySelectorAll('.flow .node+.node');
    arrows.forEach((el, k) => el.style.setProperty('--d', (arrows.length * 78 + 260 + k * 60) + 'ms'));
    slide.dataset.stamped = '1';
  }

  /* ── 카운트업 ──
     data-to    최종값 (필수)
     data-from  시작값 (기본 0)
     data-dur   ms (기본 1100)
     data-dec   소수 자릿수 (기본 0)
     data-delay 시작 지연 ms (기본 380) */
  function countUp(el) {
    const to = parseFloat(el.dataset.to);
    if (isNaN(to)) return;
    const from = parseFloat(el.dataset.from || 0);
    const dur = +(el.dataset.dur || 1100);
    const dec = +(el.dataset.dec || 0);
    const delay = +(el.dataset.delay || 380);
    const fmt = new Intl.NumberFormat('ko-KR', {
      minimumFractionDigits: dec, maximumFractionDigits: dec
    });

    if (RM) { el.textContent = fmt.format(to); return; }

    /* 자릿수가 늘어나며 레이아웃이 흔들리지 않게 최종 폭을 미리 잡는다 */
    if (!el.style.minWidth) {
      const probe = el.cloneNode(false);
      probe.textContent = fmt.format(to);
      probe.style.cssText = 'position:absolute;visibility:hidden;white-space:nowrap;min-width:0';
      el.parentNode.appendChild(probe);
      el.style.minWidth = probe.getBoundingClientRect().width + 'px';
      el.style.display = 'inline-block';
      el.style.textAlign = 'right';
      probe.remove();
    }

    el.textContent = fmt.format(from);
    if (el._raf) cancelAnimationFrame(el._raf);
    let t0 = null;
    const ease = p => 1 - Math.pow(1 - p, 3);   /* ease-out cubic */
    function tick(ts) {
      if (t0 === null) t0 = ts;
      const el2 = ts - t0 - delay;
      if (el2 < 0) { el._raf = requestAnimationFrame(tick); return; }
      const p = Math.min(1, el2 / dur);
      el.textContent = fmt.format(from + (to - from) * ease(p));
      if (p < 1) el._raf = requestAnimationFrame(tick);
      else el._raf = null;
    }
    el._raf = requestAnimationFrame(tick);
  }

  window.countUp = countUp;

  /* 슬라이드가 켜질 때 부르는 진입점 */
  window.playSlide = function (slide) {
    if (!slide) return;
    stamp(slide);
    slide.querySelectorAll('[data-to]').forEach(el => {
      const f = el.closest('.focusable');
      if (slide.dataset.steps && f && !f.classList.contains('act')) return;  /* 스텝으로 밝힐 때 센다 */
      countUp(el);
    });
  };

  /* 슬라이드를 떠날 때 되감기 — 다시 오면 처음부터 */
  window.rewindSlide = function (slide) {
    if (!slide) return;
    slide.querySelectorAll('[data-to]').forEach(el => {
      if (el._raf) { cancelAnimationFrame(el._raf); el._raf = null; }
      el.textContent = new Intl.NumberFormat('ko-KR', {
        minimumFractionDigits: +(el.dataset.dec || 0),
        maximumFractionDigits: +(el.dataset.dec || 0)
      }).format(parseFloat(el.dataset.from || 0));
    });
  };
})();
