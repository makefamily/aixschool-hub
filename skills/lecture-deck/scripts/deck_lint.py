#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""덱 확인 목록 [자동] 항목 검사 — 어떤 덱이든 완성된 deck.html 하나로 돈다.

실행:  python deck_lint.py <deck.html> [prompter.html] [--strict] [--render <로컬 서버 주소>/deck.html]   (맥은 python3)
       --render: 덱 폴더에서 python -m http.server PORT --bind 127.0.0.1 을 띄운 뒤 그 주소를 주면
                 Playwright(python) 헤드리스 브라우저로 펼쳐 줄바꿈(1~2글자만 남은 줄)을 실제로 잰다
기준:  ../references/deck-checklist.md (지적 낱말 목록은 거기서 읽는다)
결과:  FAIL 이 하나라도 있으면 종료코드 1. WARN 은 사람이 보고 판단한다.

정적 검사라 화면 렌더링이 필요한 것(실제 글자 크기, 두 창 연결 동작)은 '눈으로 확인할 것'에 남긴다.
줄바꿈은 --render 로 잰다. 프롬프터를 넣으면 덱 (장, 단계)마다 대본 덩어리(data-n·data-s)가 있는지 대조한다. 연결 동작은 두 창을 로컬 서버로 띄워 직접 넘겨 봐야 한다.
"""
import html as H
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
CHECKLIST = HERE.parent / "references" / "deck-checklist.md"

FAIL, WARN, INFO = [], [], []


def text_of(fragment):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", fragment, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>", " ", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", H.unescape(t)).strip()


def strip_data(t):
    return re.sub(r"data:[a-z0-9.+/-]+;base64,[A-Za-z0-9+/=]+", "data:", t)


def split_slides(doc):
    secs = re.findall(r"<section\b[^>]*>.*?</section>", doc, flags=re.S | re.I)
    return secs


def attr(tag_html, name):
    m = re.search(name + r'="([^"]*)"', tag_html[:400])
    return m.group(1) if m else ""


def layout_of(sec):
    cls = attr(sec, "class")
    m = re.search(r"\bk-([a-z0-9-]+)", cls)
    if m:
        return m.group(1)
    m = re.search(r'data-(?:layout|k)="([^"]+)"', sec[:400])
    if m:
        return m.group(1)
    return "+".join(sorted(c for c in cls.split() if c not in ("slide", "on", "prog"))) or "기본"


EXEMPT = re.compile(r"^(cover|chapter|chap|closing|demo|break|title)$")
VISUAL = re.compile(r"<(img|video|svg|canvas|iframe|picture)\b|data-to=|class=\"[^\"]*\b(pending|shot|chart|bar|cyc|cycle|stat|cards?|thumbs|timer|phone|cal)\b", re.I)  # cal = 달력 그림(3-13, 2026-11-13)


def load_banned():
    words = []
    if not CHECKLIST.exists():
        WARN.append(f"확인 목록 파일이 없음: {CHECKLIST}")
        return words
    t = CHECKLIST.read_text(encoding="utf-8")
    m = re.search(r"## 지적 낱말 목록.*?\n(.*?)(\n## |\Z)", t, flags=re.S)
    if not m:
        return words
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line.startswith("- ") or line.startswith("- 한글 수사") or line.startswith("- 오래된"):
            continue
        for w in line[2:].split("·"):
            w = re.sub(r"\(.*?\)", "", w).strip().strip('"')
            if w and w != "손":
                words.append(w)
    return words


KNUM = re.compile(r"(?:^|[\s(\"'“])((?:두|세|네|다섯|여섯|일곱|여덟|아홉|스물|서른)\s?(?:명|개|가지|달|주|주일|시간|분|장|단계|배|곳|권|편|년|일))|석\s?달|절반")  # 순서 '첫·두·세 번째'는 한글이 맞다(5-11)
ORDINAL_DIGIT = re.compile(r"[0-9]+\s?번째")  # 5-11: 1번째 → 첫 번째
KO_TERMS = re.compile(r"코덱스|미디엄|클로드|제미나이|챗GPT|챗지피티|오퍼스|소네트|캔버스|솔,\s|솔\s미디엄")  # 5-12: 화면의 영어 이름은 영어로(Codex, Sol, Medium)
HAND = re.compile(r"(?:^|[\s\"'“(])손(?:으로|을|이|에|만|이\s?가는|을\s?대)?(?=[\s.,!?\"'”)]|$)")
OLD_FRAMES = [r"나는\s*_{2,}", r"나는\s+\S+\s+하는\s+사람이야", r"^안녕$"]
ORANGE = re.compile(r"ff8a3d|#ff7[0-9a-f]{3}\b|#ff8[0-9a-f]{3}\b|#f97316|#fb923c|#ea580c|\borange\b", re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def linked_assets(doc, base):
    """덱이 따로 불러오는 로컬 css·js 를 같이 읽는다(df.css?v=…, deck.js 등)."""
    out = []
    for m in re.finditer(r'<(?:link[^>]+href|script[^>]+src)="([^"#]+)"', doc):
        ref = m.group(1).split("?")[0]
        if re.match(r"^(https?:|data:|//)", ref):
            continue
        f = (base / ref)
        if f.suffix in (".css", ".js") and f.exists():
            out.append(f.read_text(encoding="utf-8", errors="ignore"))
    return strip_data(" ".join(out))


def css_weight(doc, selector_pat):
    ws = []
    for m in re.finditer(selector_pat + r"[^{]*\{([^}]*)\}", doc):
        w = re.search(r"font-weight:\s*(\d{3})", m.group(1))
        if w:
            ws.append(int(w.group(1)))
    return ws


def main():
    argv = sys.argv[1:]
    render_url = None
    if "--render" in argv:
        k = argv.index("--render")
        render_url = argv[k + 1] if k + 1 < len(argv) else None
        argv = argv[:k] + argv[k + 2:]
    args = [a for a in argv if not a.startswith("--")]
    strict = "--strict" in sys.argv
    if not args:
        print(__doc__)
        sys.exit(2)
    deck_p = pathlib.Path(args[0]).resolve()
    doc = strip_data(deck_p.read_text(encoding="utf-8"))
    assets = linked_assets(doc, deck_p.parent)
    prm_p = pathlib.Path(args[1]).resolve() if len(args) > 1 else None
    prm = strip_data(prm_p.read_text(encoding="utf-8")) if prm_p else ""

    S = split_slides(doc)
    if not S:
        FAIL.append("<section> 슬라이드를 찾지 못함")
        report(deck_p, 0)
        return
    n = len(S)
    lays = [layout_of(s) for s in S]

    # 3-1 글자만 있는 장
    textonly = []
    for i, s in enumerate(S, 1):
        if EXEMPT.match(lays[i - 1]):
            continue
        if not VISUAL.search(s):
            textonly.append(i)
    body_n = sum(1 for l in lays if not EXEMPT.match(l)) or 1
    ratio = len(textonly) / body_n
    run, best, best_end = 0, 0, 0
    for i in range(1, n + 1):
        run = run + 1 if i in textonly else 0
        if run > best:
            best, best_end = run, i
    msg = f"글자만 있는 장 {len(textonly)}/{body_n}장 ({ratio:.0%}): {fmt(textonly)}"
    if ratio > 0.5 or best >= 3:
        FAIL.append(f"[3-1] {msg} · 최장 연속 {best}장(~{best_end})")
    elif ratio > 0.3 or best >= 2:
        WARN.append(f"[3-1] {msg} · 최장 연속 {best}장")
    else:
        INFO.append(f"[3-1] {msg}")

    # 2-8 같은 레이아웃 연속
    run, start = 1, 1
    for i in range(2, n + 2):
        if i <= n and lays[i - 1] == lays[i - 2]:
            run += 1
            continue
        if run >= 3:
            (FAIL if run >= 4 else WARN).append(f"[2-8] 같은 레이아웃 '{lays[i - 2]}' {run}장 연속: {start}~{i - 1}")
        run, start = 1, i

    # 4-3 강조 위치: 라벨만 강조되고 제목은 강조가 없는 장
    label_acc, multi_acc, no_acc = [], [], []
    for i, s in enumerate(S, 1):
        cls = attr(s, "class")
        title = re.search(r"<h1\b.*?</h1>|<h2\b.*?</h2>", s, flags=re.S)
        t_acc = bool(title and re.search(r"<em\b|<mark\b|class=\"[^\"]*\bacc\b", title.group(0)))
        lab = re.findall(r'<div class="(?:eyebrow|kicker|eb)\b[^"]*">(.*?)</div>', s, flags=re.S)
        lab_acc = any(re.search(r"<em\b|\bacc\b", x) for x in lab)
        if ("eb-acc" in cls.split() or lab_acc) and not t_acc:
            label_acc.append(i)
        n_acc = len(re.findall(r"<em\b|<mark\b|class=\"[^\"]*\bacc\b", re.sub(r'<div class="(?:deck|pend)[^"]*".*?</div>', "", s, flags=re.S)))
        steps = int(attr(s, "data-steps") or 0)
        if n_acc > 1 and not steps:
            multi_acc.append(f"{i}({n_acc})")
        if n_acc == 0 and not EXEMPT.match(lays[i - 1]) and "eb-acc" not in cls.split():
            no_acc.append(i)
    if label_acc:
        FAIL.append(f"[4-3] 제목 대신 위쪽 라벨(1부·2부 등)이 강조된 장: {fmt(label_acc)}")
    if multi_acc:
        WARN.append(f"[4-3] 강조가 두 곳 이상인 장(스텝 없는 장): {', '.join(multi_acc)}")
    if no_acc:
        INFO.append(f"[4-3] 강조가 없는 장(괜찮은지 확인): {fmt(no_acc)}")

    # 4-1 제목 굵기
    ws = css_weight(doc + " " + assets, r"(?:\.action-title|(?<![\w-])h1)\b")
    if ws and max(ws) < 800 and min(ws) < 700:
        FAIL.append(f"[4-1] 제목 굵기 {sorted(set(ws))} — 800 이상으로")
    elif ws and min(ws) < 800:
        WARN.append(f"[4-1] 제목 굵기에 800 미만 규칙이 섞여 있음 {sorted(set(ws))}")

    # 4-5·4-6 색·글꼴·금칙
    css_js = " ".join(re.findall(r"<(?:style|script)[^>]*>(.*?)</(?:style|script)>", doc, flags=re.S)) + " " + assets
    if ORANGE.search(css_js):
        FAIL.append(f"[4-5] 주황색 코드: {ORANGE.findall(css_js)[:3]}")
    if "pretendard" not in (doc + assets).lower():
        WARN.append("[4-6] Pretendard 글꼴 지정이 없음")
    if re.search(r"animation:[^;}]*infinite", css_js):
        WARN.append("[덱 규칙] 상시 반복 애니메이션(infinite) 있음 — 의도한 것인지 확인")

    # 3-8 자리표시: 무엇이 필요한지 적었나
    pend = []
    for i, s in enumerate(S, 1):
        for m in re.finditer(r'<div class="pend">(.*?)</div>', s, flags=re.S):
            inner = m.group(1)
            if not re.search(r'class="need"', inner):
                fname = text_of(inner).replace("준비 중", "").strip()
                pend.append(f"{i}({fname})")
    if pend:
        FAIL.append(f"[3-8] 필요한 자료 설명 없이 파일 이름만 있는 자리표시 {len(pend)}곳: {', '.join(pend)} — slides.py 에 need='무엇을 누가' 추가")

    # 3-9 영상
    if re.search(r"<video\b", doc):
        if re.search(r"video[^{]*\{[^}]*object-fit:\s*cover", doc):
            WARN.append("[3-9] 영상에 object-fit:cover 가 있음 — 잘려 보일 수 있음(contain 권장)")
        if not re.search(r"\.paused", css_js):
            WARN.append("[3-9] 영상 클릭 정지 처리가 안 보임")

    # 8-9 QR
    qr = [i for i, s in enumerate(S, 1) if re.search(r"<img[^>]+(?:src|alt)=\"[^\"]*qr", s, flags=re.I) or re.search(r"QR\s?코드", text_of(s))]
    if qr:
        WARN.append(f"[8-9] QR 이 있는 장: {fmt(qr)} — 노트북 화면이면 짧은 주소로")

    # 7-5 덱↔프롬프터 연결
    if "aix-deck" not in doc + assets or "BroadcastChannel" not in doc + assets:
        FAIL.append("[7-5] 덱에 프롬프터 연결 코드(BroadcastChannel 'aix-deck')가 없음 — templates/style-v1/deck.js · templates/style-v2/deck.js 참고")
    if prm:
        if "aix-deck" not in prm:
            FAIL.append("[7-5] 프롬프터에 덱 연결 코드('aix-deck')가 없음")
        if not re.search(r"toc|목차", prm, flags=re.I):
            WARN.append("[7-7] 프롬프터에 목차 접기 토글이 안 보임 — assets/prompter-toc-toggle.html")
        check_press(S, prm)
    else:
        INFO.append("[7-x] 프롬프터 파일을 안 넣어서 프롬프터 검사(연결·목차·분량)는 건너뜀")

    # 1-9 장 수 고정
    b = deck_p.parent / "build.py"
    if b.exists() and re.search(r"assert\s+(?:total|len\(D\))\s*==\s*\d+", b.read_text(encoding="utf-8")):
        WARN.append("[1-9] build.py 에 장 수 고정 assert 가 있음 — 장 수는 제약이 아님")

    # 5-x 낱말 (덱 + 프롬프터 본문)
    for label, src in (("덱", doc), ("프롬프터", prm)):
        if not src:
            continue
        body = text_of(re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", src, flags=re.S))
        hits = []
        for w in load_banned():
            c = body.count(w)
            if c:
                hits.append(f"'{w}'×{c}")
        if hits:
            FAIL.append(f"[5-1·10-3] {label}에 지적받은 낱말: {', '.join(hits)}")
        od = ORDINAL_DIGIT.findall(body)
        if od:
            FAIL.append(f"[5-11] {label}에 숫자+번째 {len(od)}곳({', '.join(sorted(set(od))[:6])}) — 첫 번째·두 번째·세 번째로")
        if label == "덱":
            kt = KO_TERMS.findall(body)
            if kt:
                FAIL.append(f"[5-12] 덱에 영어 이름을 한글로 쓴 곳: {', '.join(sorted(set(kt)))} — 화면 표기 그대로 영어로(Codex, Sol, Medium …)")
        h = HAND.findall(body)
        if h:
            FAIL.append(f"[5-2] {label}에 '손' 표현 {len(h)}곳 — 직접·AI 직원으로")
        k = sorted(set(x.group(0).strip(" (\"'“") for x in KNUM.finditer(body)))
        if k:
            WARN.append(f"[5-3] {label}에 한글 숫자: {', '.join(k[:12])} — 아라비아 숫자로")
        old = [p for p in OLD_FRAMES if re.search(p, body, flags=re.M)]
        if old:
            FAIL.append(f"[8-3] {label}에 오래된 지시 틀: {old}")
        if EMOJI.search(body) or "마법" in body:
            FAIL.append(f"[덱 규칙] {label}에 이모지 또는 '마법'")

    if render_url:
        render_check(render_url)
    report(deck_p, n, strict)


def check_press(S, prm):
    """7-2·7-4 화살표 한 번에 멘트 한 덩어리 — 덱 (장, 단계)마다 프롬프터 대본 덩어리가 하나씩 있어야 한다.
    표준 표기(10/12 설명회 프롬프터): 대본 덩어리 요소에 data-n="장 번호" data-s="단계(0부터)"."""
    have = {}
    for m in re.finditer(r'<[a-z]+\b[^>]*\bdata-n="(\d+)"[^>]*>', prm):
        tag = m.group(0)
        s = re.search(r'\bdata-s="(\d+)"', tag)
        key = (int(m.group(1)), int(s.group(1)) if s else 0)
        have[key] = have.get(key, 0) + 1
    if not have:
        WARN.append("[7-2] 프롬프터 대본에 장·단계 표시(data-n·data-s)가 없어 덱 스텝과 비교하지 못함 — 덩어리마다 붙일 것")
        return
    want = set()
    for i, s in enumerate(S, 1):
        steps = int(attr(s, "data-steps") or 0)
        for k in range(steps + 1):
            want.add((i, k))
    missing = sorted(want - set(have))
    extra = sorted(set(have) - want)
    dup = sorted(k for k, c in have.items() if c > 1)
    if missing:
        FAIL.append(f"[7-2] 덱에서 누르는 단계인데 프롬프터 대본이 없는 곳 {len(missing)}개: " + ", ".join(f"{n}장-{k}" for n, k in missing[:20]))
    if extra:
        WARN.append(f"[7-4] 덱에 없는 장·단계를 가리키는 대본 {len(extra)}개: " + ", ".join(f"{n}장-{k}" for n, k in extra[:20]))
    if dup:
        WARN.append(f"[7-2] 한 번 누를 때 대본이 두 덩어리인 곳: " + ", ".join(f"{n}장-{k}" for n, k in dup[:20]))
    if not (missing or extra or dup):
        INFO.append(f"[7-2] 덱 스텝 {len(want)}개 = 프롬프터 대본 {sum(have.values())}덩어리")


CROP_JS = r"""(() => {
  const secs = [...document.querySelectorAll('section')], out = [];
  secs.forEach((sec, i) => sec.querySelectorAll('img,video').forEach(el => {
    if (el.closest('.cov-pic,.phone-in,.gb-i,[data-crop-ok]')) return;   // 인물 사진·휴대폰 틀·배경 모자이크는 일부러 맞춘 것
    const cs = getComputedStyle(el); if (cs.objectFit !== 'cover') return;
    const b = el.getBoundingClientRect(), nw = el.naturalWidth || el.videoWidth, nh = el.naturalHeight || el.videoHeight;
    if (!nw || !nh || !b.width || !b.height) return;
    const ia = nw / nh, ba = b.width / b.height, vis = Math.min(ia / ba, ba / ia);
    if (vis < 0.9) out.push({n: i + 1, vis: Math.round(vis * 100), src: (el.getAttribute('src') || '').slice(-40)});
  }));
  return JSON.stringify(out);
})()"""

SMALL_JS = r"""(() => {
  // 3-17: 캡처 글씨가 화면에서 원본의 70% 미만으로 보이는 곳. 원본 폭 1800px 이상은 레티나 2배 캡처로 보고 절반을 원본 CSS 폭으로 친다
  const out = [];
  document.querySelectorAll('section').forEach((sec, i) => sec.querySelectorAll('.proof-b img, .sp-pic img, .shotimg img, .zoomimg img').forEach(el => {
    if (el.closest('.bxw,.zoomed,.scr,.phone-in,.cov-pic,.gb-i,.gl-i,[data-small-ok]')) return;  // 박스 장(다음 장이 확대)·확대 장·꽉 찬 화면·휴대폰·사진 모음은 제외
    const nw = el.naturalWidth, w = el.getBoundingClientRect().width;
    if (!nw || !w) return;
    const css = nw >= 1800 ? nw / 2 : nw, r = w / css;
    if (r < 0.7) out.push({n: i + 1, r: Math.round(r * 100), src: (el.getAttribute('src') || '').slice(-40)});
  }));
  return JSON.stringify(out);
})()"""

RENDER_JS = r"""
(() => {
  const out = [];
  const sel = 'h1 .reveal > span, h1, .subhead, .lead, .bigquote, .cmp-col .d, .node .d, .cell .d, .stat .c, .pend .need, .sub, .qa-ask, .vs-c b, .vs-c span, .s4-t, .s4-d, .rs b, .rs span, .ck li span, .fl-t, .fl-d, .po span, .sp-items b, .sp-items span, .need-t, .st-c, .tl-t';
  document.querySelectorAll('.slide').forEach((sl, si) => {
    const seen = new Set();
    sl.querySelectorAll(sel).forEach(el => {
      if ([...seen].some(p => p.contains(el))) return;
      seen.add(el);
      const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      const chars = [];
      let t;
      while ((t = tw.nextNode())) {
        for (let i = 0; i < t.length; i++) {
          if (!t.data[i].trim()) { if (chars.length) chars[chars.length - 1][1] += ' '; continue; }
          const r = document.createRange(); r.setStart(t, i); r.setEnd(t, i + 1);
          const b = r.getClientRects()[0];
          if (b && b.width > 0) chars.push([Math.round(b.top), t.data[i], b.height]);
        }
      }
      if (chars.length < 4) return;
      const lines = [];
      chars.forEach(([top, ch, h]) => {
        const L = lines.find(l => Math.abs(l.top - top) < h * 0.5);
        if (L) L.s += ch; else lines.push({top, s: ch});
      });
      if (lines.length > 1) {
        const last = lines[lines.length - 1].s;
        if (last.replace(/[\s.,!?·)\]"'”]/g, '').length <= 2)
          out.push({n: si + 1, kind: 'orphan', text: lines.map(l => l.s).join(' / ')});
      }
    });
  });
  return JSON.stringify(out);
})()
"""


def render_check(url):
    """4-4 줄바꿈: 덱을 ?flat=1 로 펼쳐 실제 줄 단위로 재고, 마지막 줄에 1~2글자만 남은 곳을 찾는다.
    Playwright(python)로 이 검사 전용 브라우저를 띄우고 끝나면 그 브라우저만 닫는다.
    Playwright 가 없으면 건너뛰고 WARN 으로 알린다(사용자에게 설치가 필요하다고 알릴 것)."""
    import json
    sep = "&" if "?" in url else "?"
    flat = url.split("#")[0] + sep + "flat=1"
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        WARN.append("[4-4] 렌더 검사 건너뜀 — Playwright(python)가 설치돼 있지 않다. 사용자에게 설치가 필요하다고 알리고, 그 전에는 눈으로 줄바꿈을 확인한다")
        return
    try:
        with sync_playwright() as pw:
            br = pw.chromium.launch()
            pg = br.new_page(viewport={"width": 1920, "height": 1080})
            pg.goto(flat, timeout=90000)
            pg.wait_for_timeout(1500)
            r, rc, rs = (pg.evaluate(js) for js in (RENDER_JS, CROP_JS, SMALL_JS))
            br.close()
        data = json.loads(r) if isinstance(r, str) else r
    except Exception as e:
        WARN.append(f"[4-4] 렌더 검사 실패({type(e).__name__}) — 로컬 서버 주소인지, Playwright 브라우저가 설치돼 있는지 확인")
        return
    try:
        crop = json.loads(rc) if isinstance(rc, str) else rc
        if crop:
            FAIL.append(f"[3-16] 캡처가 칸에 맞춰 잘린 곳 {len(crop)}개(원본의 90% 미만만 보임) — 캡처에 맞춰 레이아웃을 바꾸세요: " +
                        " | ".join(f"{d['n']}장 {d['vis']}% …{d['src']}" for d in crop[:12]))
        else:
            INFO.append("[3-16] 렌더 검사: 잘린 캡처 없음")
    except Exception as e:
        WARN.append(f"[3-16] 잘림 검사 실패({type(e).__name__})")
    try:
        small = json.loads(rs) if isinstance(rs, str) else rs
        if small:
            WARN.append(f"[3-17] 캡처 글씨가 원본의 70% 미만으로 보이는 곳 {len(small)}개 — 누를 곳을 찾아야 하는 화면이면 빨간 박스 장 → 확대 장으로 나누세요(BOXED): " +
                        " | ".join(f"{d['n']}장 {d['r']}% …{d['src']}" for d in small[:12]))
        else:
            INFO.append("[3-17] 렌더 검사: 작게 보이는 캡처 없음")
    except Exception as e:
        WARN.append(f"[3-17] 작은 캡처 검사 실패({type(e).__name__})")
    if data:
        FAIL.append(f"[4-4] 마지막 줄에 1~2글자만 남은 곳 {len(data)}개: " +
                    " | ".join(f"{d['n']}장 「…{d['text'][-30:]}」" for d in data[:12]))
    else:
        INFO.append("[4-4] 렌더 검사: 1~2글자만 남은 줄 없음")


def fmt(nums):
    if not nums:
        return "없음"
    out, a = [], nums[0]
    prev = a
    for x in nums[1:] + [None]:
        if x is not None and x == prev + 1:
            prev = x
            continue
        out.append(f"{a}" if a == prev else f"{a}-{prev}")
        if x is not None:
            a = prev = x
    return ", ".join(out)


def report(deck_p, n, strict=False):
    print(f"덱 검사: {deck_p.name} · {n}장")
    print(f"■ FAIL {len(FAIL)}건")
    for x in FAIL:
        print("  " + x)
    print(f"□ WARN {len(WARN)}건")
    for x in WARN:
        print("  " + x)
    for x in INFO:
        print("  · " + x)
    print("눈으로 확인할 것: 줄바꿈(4-4, --render 안 했으면) · 실제 글자 크기(4-2) · 두 창 연결 동작(7-5) · 화면 점유(3-2·3-15) · 나머지 확인 목록 수동 항목")
    sys.exit(1 if FAIL or (strict and WARN) else 0)


if __name__ == "__main__":
    main()
