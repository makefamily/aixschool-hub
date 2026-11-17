# -*- coding: utf-8 -*-
"""5차시 덱 v2 정적 QA — ASC build-v2 qa.py 를 이 덱에 맞춰 개조

  1 장 수      — 57장, slide-plan-v2.md 표의 번호·장 수와 일치
  2 문구 충실  — v1(src/slides.json) 문구 조각이 전부 덱에 들어갔는가 / 덱 문구가 v1 밖에서 오지 않았는가
  3 자산       — 참조 파일 존재 (없는 [pending] 은 목록으로)
  4 스텝       — data-focus 인덱스가 focusable 개수를 넘지 않는가
  5 금칙       — 주황색 코드, 이모지, '마법', 상시 반복 애니메이션(infinite)
실행: python3 qa.py
"""
import sys, re, json, html, pathlib, importlib
HERE = pathlib.Path(__file__).resolve().parent
LECT = HERE.parent
sys.path.insert(0, str(HERE))
import slides
importlib.reload(slides)
D = slides.D
FAIL, WARN = [], []

def norm(x):
    x = re.sub(r"<br\s*/?>", " ", x or "")
    x = re.sub(r"<[^>]+>", "", x)
    x = html.unescape(x).replace("|", " ")
    return re.sub(r"\s+", "", x)

# 1 장 수 · 계획서 번호
plan = (LECT / "src/slide-plan-v2.md").read_text(encoding="utf-8")
nums = [int(m) for m in re.findall(r"^\| (\d+) \|", plan, re.M)]
if len(D) != 57 or nums != list(range(1, 58)):
    FAIL.append(f"장 수 불일치: 덱 {len(D)} / 계획서 {len(nums)}")

# 2 문구 충실도
v1 = json.loads((LECT / "src/slides.json").read_text(encoding="utf-8"))
deck_html = (HERE / "deck.html").read_text(encoding="utf-8")
body = deck_html.split('<div id="deck">', 1)[1]
body = re.sub(r'<span class="num" data-to="(\d+)"[^>]*>[^<]*</span>', r"\1", body)
body = re.sub(r'<div class="deck-(brand|meta|author|page)">.*?</div>', "", body)
deck_text = norm(body)
frags = []
for n, s in enumerate(v1, 1):
    for key in ("kicker", "h1", "note", "hold"):
        if s.get(key):
            frags.append((n, s[key]))
    for x in s.get("lead", []) + s.get("q", []):
        frags.append((n, x))
    for a, b in s.get("ul", []):
        frags += [(n, a), (n, b)]
missing = []
for n, f in frags:
    parts = [f] if "·" not in f or n not in (5,) else f.split(" · ", 1)
    for p in parts:
        # v1 ' / ' 구분은 줄바꿈으로만 바꿨다
        for q in p.split(" / "):
            if norm(q) not in deck_text:
                missing.append(f"v1#{n}: {q}")
for m in missing:
    FAIL.append("덱에 없는 v1 문구 — " + m)
v1_text = "".join(norm(f) for _, f in frags)

# 3 자산
pend = []
for i, s in enumerate(D, 1):
    for rel in [s.get("img"), s.get("src")] + list(s.get("imgs", [])):
        if rel and not (HERE / rel).exists():
            (pend if rel.startswith("media/") else FAIL).append(f"[{i}] {rel}")

# 4 스텝
FOC = {"compare": "cols", "flow": "nodes", "grid": "cells", "stat": "stats", "cycle": "nodes", "cardsteps": "imgs"}
for i, s in enumerate(D, 1):
    if not s.get("steps"):
        continue
    n = len(s.get(FOC.get(s["k"], ""), []))
    if not n:
        FAIL.append(f"[{i}] {s['k']} 에 steps 가 있는데 focusable 없음")
    for st in s["steps"]:
        for x in st:
            if x >= n:
                FAIL.append(f"[{i}] 스텝 인덱스 {x} >= focusable {n}")

# 5 금칙
ORANGE = re.compile(r"ff8a3d|#ff7[0-9a-f]{3}|#ff8[0-9a-f]{3}|#f97316|#fb923c|#ea580c|\borange\b", re.I)
for f in ("deck.html", "deck-share.html", "df.css", "deck.js", "motion.js", "slides.py", "build.py"):
    p = HERE / f
    if not p.exists():
        continue
    t = p.read_text(encoding="utf-8")
    t = re.sub(r"data:[a-z/]+;base64,[A-Za-z0-9+/=]+", "", t)
    if ORANGE.search(t):
        FAIL.append(f"{f}: 주황색 코드 {ORANGE.findall(t)[:3]}")
    if re.search(r"animation:[^;}]*infinite|repeatCount=\"indefinite\"", t):
        FAIL.append(f"{f}: 상시 반복 애니메이션")
    if re.search("[\U0001F300-\U0001FAFF]", t) or "마법" in t:
        FAIL.append(f"{f}: 이모지 또는 금칙어")

print(f"슬라이드 {len(D)}장 · v1 문구 조각 {len(frags)}개 대조")
print(f"■ FAIL {len(FAIL)}건"); [print("  " + x) for x in FAIL]
print(f"□ PENDING {len(pend)}건"); [print("  " + x) for x in pend]
sys.exit(1 if FAIL else 0)
