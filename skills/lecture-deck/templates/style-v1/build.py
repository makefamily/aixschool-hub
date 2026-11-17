# -*- coding: utf-8 -*-
"""5차시 덱 v2 빌더 — 8/21 ASC 특강 build-v2(build2.py) 디자인 시스템을 옮겨 개조
   정본 콘텐츠: slides.py 의 D (번호 = src/slide-plan-v2.md)

   python3 build.py          → deck.html (df.css · motion.js · deck.js · media/ 상대경로)
   python3 build.py --share  → deck-share.html (CSS·JS·이미지·영상 전부 한 파일에)

   [pending] 미디어: media/<이름>.png 가 없으면 '준비 중' 자리표시를 그린다.
   같은 파일명으로 넣고 다시 빌드하면 바뀐다.
"""
import sys, html, pathlib, json, re, base64, math, importlib, hashlib, mimetypes

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slides
importlib.reload(slides)
from slides import D, META

SHARE = "--share" in sys.argv
CSS = (HERE / "df.css").read_text(encoding="utf-8")
MOTION = (HERE / "motion.js").read_text(encoding="utf-8")
NAV = (HERE / "deck.js").read_text(encoding="utf-8")
VER = hashlib.sha1((CSS + MOTION + NAV).encode()).hexdigest()[:8]

PENDING = []
NO_NEED = []   # 무엇이 필요한지 안 적은 자리표시
_b64 = {}

def src(rel):
    """덱 기준 상대경로. 공유본이면 자리표시만 두고 파일은 한 번씩만 싣는다(JS가 붙인다)."""
    if not SHARE:
        return rel
    _b64[rel] = True
    return "__SHARE__" + rel

def exists(rel):
    return (HERE / rel).exists()

def e(x):
    return html.escape(x or "", quote=False)

def rich(x):
    """<em> <b> <br> 만 통과시킨다."""
    if not x:
        return ""
    s = html.escape(x, quote=False)
    for tag in ("em", "b"):
        s = s.replace(f"&lt;{tag}&gt;", f"<{tag}>").replace(f"&lt;/{tag}&gt;", f"</{tag}>")
    return s.replace("&lt;br&gt;", "<br>")

def title_html(t, cls="action-title"):
    if not t:
        return ""
    lines = "".join(f'<span class="reveal"><span>{rich(l)}</span></span>' for l in t.split("|"))
    return f'<h1 class="{cls}">{lines}</h1>'

def sub_h(s):
    return f'<p class="subhead anim">{rich(s["sub"])}</p>' if s.get("sub") else ""

def eyebrow(x):
    return f'<div class="eyebrow ko anim fade">{rich(x)}</div>' if x else ""

def tail_html(t):
    return f'<div class="tail anim">{rich(t)}</div>' if t else ""

def chrome(part, page, total):
    return (
        f'<div class="deck-brand"><span class="mark"></span>'
        f'<span class="wm">{e(META["title"])}</span></div>'
        f'<div class="deck-meta">{e(part)}</div>'
        f'<div class="deck-author">강사 이름 · 소속</div>'
        f'<div class="deck-page"><b>{page:02d}</b> / {total}</div>'
    )

def stepattrs(s):
    steps = s.get("steps")
    if not steps:
        return "", ""
    attrs = f' data-steps="{len(steps)-1}" data-step="0" data-focus=\'{json.dumps(steps)}\''
    dots = '<div class="stepdots">' + "".join(
        f'<i class="{"on" if i == 0 else ""}"></i>' for i in range(len(steps))) + "</div>"
    return attrs, dots

def bg(grid=False):
    return ('<div class="bg"><div class="amb"></div>'
            + ('<div class="hairgrid"></div>' if grid else "")
            + '<div class="bg-grain"></div></div>')

def frame(inner, tail=None, cls=""):
    return (f'<div class="frame {cls}"><div class="spacer"></div>{inner}'
            f'<div class="spacer"></div>{tail_html(tail)}</div>')

def head(s, gap="gap-l"):
    eb = eyebrow(s.get("eyebrow"))
    t = title_html(s.get("title"))
    out = eb
    if eb and t:
        out += '<div class="gap-m"></div>'
    out += t
    if s.get("sub"):
        out += '<div class="gap-m"></div>' + sub_h(s)
    return out + (f'<div class="{gap}"></div>' if gap else "")

def boxes(box):
    """빨간 박스(1-A, 2026-11-13): box=[(x, y, w, h), ...] 이미지 대비 비율(0~1). 2개 이상이면 번호"""
    bs = box or []
    return "".join(f'<i class="bx" style="left:{x*100:.1f}%;top:{y*100:.1f}%;width:{w*100:.1f}%;height:{h*100:.1f}%">'
                   + (f'<b class="bxn">{i+1}</b>' if len(bs) > 1 else "") + '</i>' for i, (x, y, w, h) in enumerate(bs))

def media_box(rel, cls="shotimg", need=None, box=None):
    """이미지가 있으면 img, 없으면 준비 중 자리표시.
    need = 어떤 자료가 필요한지 한 줄(누가 무엇을 찍어 줄지). 비워두지 말 것
    box = 빨간 박스 좌표 목록(1-A). 다음 장에 k="zoom" 으로 확대 장을 둔다"""
    if exists(rel) and box:
        return f'<div class="{cls} focusable"><span class="bxw"><img src="{src(rel)}" alt="">{boxes(box)}</span></div>'
    if exists(rel):
        return f'<div class="{cls} focusable"><img src="{src(rel)}" alt=""></div>'
    PENDING.append(rel)
    if not need:
        NO_NEED.append(rel)
    need_h = f'<em class="need">{e(need)}</em>' if need else ""
    return (f'<div class="{cls} pending"><div class="pend"><b>준비 중</b>{need_h}'
            f'<span>{e(rel)}</span></div></div>')

# ───────────────────────── 레이아웃 ─────────────────────────

def r_cover(s):
    return bg() + frame(
        f'{eyebrow(s.get("eyebrow"))}<div class="gap-m"></div>'
        f'{title_html(s.get("title"), "action-title xl")}<div class="gap-m"></div>{sub_h(s)}')

def r_statement(s):
    big = " xl" if s.get("big") else ""
    eb = eyebrow(s.get("eyebrow"))
    inner = eb + ('<div class="gap-m"></div>' if eb else "")
    inner += title_html(s.get("title"), "action-title" + big)
    if s.get("sub"):
        inner += '<div class="gap-m"></div>' + sub_h(s)
    return bg() + frame(inner, s.get("tail"))

def r_chapter(s):
    return bg(grid=True) + frame(
        f'<div class="chap-k anim fade">{e(s["eyebrow"])}</div><div class="gap-m"></div>'
        f'{title_html(s["title"], "action-title xl")}')

def r_demo(s):
    m = re.search(r"[①-⑳]", s.get("eyebrow", ""))
    num = f'<div class="demo-num anim fade" aria-hidden="true">{m.group(0)}</div>' if m else ""
    return bg() + num + frame(
        f'{eyebrow(s["eyebrow"])}<div class="gap-m"></div>'
        f'{title_html(s["title"], "action-title xl")}<div class="gap-m"></div>'
        f'<div class="demo-rule anim fade"></div><div class="gap-s"></div>{sub_h(s)}')

def r_quote(s):
    return bg() + frame(
        f'{title_html(s["title"])}<div class="gap-l"></div>'
        f'<blockquote class="bigquote anim-say q-sm"><span class="reveal"><span>{rich(s["quote"])}</span></span></blockquote>'
        f'<div class="gap-s"></div><p class="subhead anim">{rich(s["tail"])}</p>')

def r_compare(s):
    hl = s.get("hl")
    cols = "".join(
        f'<div class="cmp-col focusable anim{" hl" if hl == i else ""}">'
        f'<div class="t">{rich(t)}</div><div class="d">{rich(d)}</div></div>'
        for i, (t, d) in enumerate(s["cols"]))
    return bg() + frame(head(s) + f'<div class="cmp">{cols}</div>', s.get("tail"))

def r_flow(s):
    nodes = "".join(
        f'<div class="node focusable anim-flow{" nod" if not d else ""}">'
        f'<div class="n">{i+1:02d}</div><div class="t">{rich(t)}</div>'
        + (f'<div class="d">{rich(d)}</div>' if d else "") + '</div>'
        for i, (t, d) in enumerate(s["nodes"]))
    cols = len(s["nodes"])
    return bg() + frame(head(s) +
        f'<div class="flow" style="grid-template-columns:repeat({cols},1fr)">{nodes}</div>', s.get("tail"))

def r_grid(s):
    cells = "".join(
        f'<div class="cell focusable anim-stop"><div class="n">{i+1:02d}</div>'
        f'<div class="t">{rich(t)}</div><div class="d">{rich(d)}</div></div>'
        for i, (t, d) in enumerate(s["cells"]))
    return bg() + frame(head(s, "gap-m") + f'<div class="cellgrid">{cells}</div>', s.get("tail"))

def r_stat(s):
    cells = []
    for i, (lab, val, frm, unit, cap) in enumerate(s["stats"]):
        hl = " hl" if s.get("hl") == i else ""
        cells.append(
            f'<div class="stat focusable{hl}"><div class="k">{e(lab)}</div>'
            f'<div class="v"><span class="num" data-to="{val}" data-from="{frm}" data-dec="{len(str(val).split(".")[1]) if "." in str(val) else 0}" '
            f'data-dur="{900 + len(str(val)) * 120}" data-delay="120">{frm}</span>'
            f'<small>{e(unit)}</small></div>'
            f'<div class="c">{rich(cap)}</div></div>')
    return bg(grid=True) + frame(head(s) + f'<div class="stat-row">{"".join(cells)}</div>')

def r_cycle(s):
    n = len(s["nodes"])
    dots = []
    for i, lab in enumerate(s["nodes"]):
        a = -math.pi / 2 + i * 2 * math.pi / n
        x, y = 50 + 40 * math.cos(a), 50 + 42 * math.sin(a)
        dots.append(f'<div class="cyn focusable" style="left:{x:.1f}%;top:{y:.1f}%;--i:{i}">'
                    f'<b>{i+1:02d}</b>{e(lab)}</div>')
    ring = (f'<div class="cycle" data-n="{n}">'
            f'<svg class="cysvg" viewBox="0 0 100 100" preserveAspectRatio="none">'
            f'<ellipse cx="50" cy="50" rx="40" ry="42"/>'
            f'<ellipse class="cyarc" cx="50" cy="50" rx="40" ry="42" pathLength="100" '
            f'transform="rotate(-90 50 50)"/></svg>{"".join(dots)}</div>')
    left = f'<div>{head(s, None)}</div>'
    return bg() + frame(f'<div class="cyclewrap">{left}{ring}</div>')

def aspect(rel):
    try:
        from PIL import Image
        w, h = Image.open(HERE / rel).size
        return w / h
    except Exception:
        return 16 / 9          # 아직 없는 파일(pending)은 화면 캡처 비율로 잡는다

def r_shot(s):
    if s.get("wide"):
        return bg() + frame(f'{eyebrow(s.get("eyebrow"))}<div class="gap-m"></div>'
                            f'{media_box(s["img"], "shotimg wide", s.get("need"), s.get("box"))}', cls="frame-wide")
    items = ""
    if s.get("items"):
        items = '<ul class="sitems">' + "".join(
            f'<li class="anim"><b>{rich(t)}</b><span>{rich(d)}</span></li>' for t, d in s["items"]) + "</ul>"
    if aspect(s["img"]) >= 1.45:
        # 가로로 긴 화면: 제목 줄 아래에 화면을 폭 가득
        eb = eyebrow(s.get("eyebrow"))
        left = f'<div>{eb}{"<div class=gap-s></div>" if eb else ""}{title_html(s.get("title"))}</div>'
        right = f'<div class="stackright">{sub_h(s)}{items}</div>'
        return bg() + frame(f'<div class="shotstack"><div class="stacktop">{left}{right}</div>'
                            f'{media_box(s["img"], "shotimg stack", s.get("need"), s.get("box"))}</div>', cls="frame-wide")
    items = ('<div class="gap-m"></div>' + items) if items else ""
    left = f'<div class="shotleft">{head(s, None)}{items}</div>'
    return bg() + frame(f'<div class="shotwrap2">{left}{media_box(s["img"], need=s.get("need"), box=s.get("box"))}</div>')

def r_vside(s):
    v = f'<video data-src="{e(s["src"])}"' + (f' src="{src(s["src"])}"' if not SHARE else "")
    v += ' playsinline loop muted autoplay preload="auto"></video>'
    left = f'<div class="shotleft">{head(s, None)}</div>'
    return (bg() + frame(f'<div class="vwrap">{left}</div>')
            + f'<div class="vside anim fade">{v}<button class="soundbtn" aria-label="소리 켜기">소리 켜기</button></div>')

def r_cards(s):
    cards = "".join(f'<div class="card anim-stop"><img src="{src(r)}" alt=""></div>' for r in s["imgs"])
    return bg() + frame(f'{eyebrow(s.get("eyebrow"))}<div class="gap-m"></div>'
                        f'<div class="cards8">{cards}</div>', cls="frame-wide")

def r_cardsteps(s):
    big = "".join(f'<div class="cbig focusable"><img src="{src(r)}" alt=""></div>' for r in s["imgs"])
    thumbs = "".join(f'<i class="th"><img src="{src(r)}" alt=""></i>' for r in s["imgs"])
    left = f'<div class="shotleft">{head(s, None)}<div class="gap-l"></div><div class="thumbs anim">{thumbs}</div></div>'
    return bg() + frame(f'<div class="cstepwrap">{left}<div></div></div>') + f'<div class="cstack">{big}</div>'

def _size(rel):
    try:
        from PIL import Image
        return Image.open(HERE / rel).size
    except Exception:
        return (1600, 900)

def r_zoom(s):
    """1-A 확대 장(2026-11-13): 앞 장 빨간 박스 부분을 잘라 크게. 이미지 크기를 직접 계산해 빨간 테두리가 이미지에 딱 붙는다"""
    w, h = _size(s["img"])
    lines = (s.get("title") or "").count("|") + 1
    H = 1080 - 2 * 96 - 60 - (50 if s.get("eyebrow") else 0) - 92 * lines - (60 if s.get("sub") else 0) - 40
    k = min((1920 - 2 * 140) / w, H / h)
    img = f'<div class="zoomimg focusable"><img src="{src(s["img"])}" alt="" style="width:{w*k:.0f}px;height:{h*k:.0f}px"></div>'
    return bg() + frame(head(s, "gap-m") + img, cls="frame-wide")

def r_screen(s):
    """따라하기(가이드) 페이지 화면을 덱 전체에 꽉 차게(2026-11-13). 960×540·2배 캡처 = 1920×1080"""
    return f'<div class="scr"><img src="{src(s["img"])}" alt="">{boxes(s.get("box"))}</div>'

def r_market(s):
    """시중 서비스 한 장(2026-11-13): 공개 페이지 실제 캡처 + 가격 태그(공식 페이지 확인값만) → '이런 걸 돈 주고 써요 ↓ 우리는'"""
    m = s["img"]
    if m.endswith(".mp4"):
        vis = f'<video class="mk-img" src="{src(m)}" autoplay muted loop playsinline preload="auto"></video>'
    else:
        vis = f'<img class="mk-img" src="{src(m)}" alt="">'
    tag = f'<div class="mk-tag">{rich(s["tag"])}</div>' if s.get("tag") else ""
    srcl = f'<div class="mk-src">{rich(s["src"])}</div>' if s.get("src") else ""
    (a, ad), (b, bd) = s["side"]
    side = (f'<div class="mk-side"><div class="anim"><b>{rich(a)}</b><span>{rich(ad)}</span></div>'
            f'<div class="mk-ar anim">↓</div><div class="mk-s2 anim"><b>{rich(b)}</b><span>{rich(bd)}</span></div></div>')
    return bg() + frame(head(s, "gap-m") + f'<div class="mk-b"><div class="mk-vis"><div class="mk-wrap">{vis}{tag}</div>{srcl}</div>{side}</div>',
                        cls="frame-wide")

def r_cal(s):
    """한 달 달력(2026-11-13): marks={일: (today·class·span, 글)}, legend=[(종류, 이름)]"""
    import calendar
    first, ndays = calendar.monthrange(s["year"], s["month"])
    lead = (first + 1) % 7
    cells = "".join(f'<div class="cal-h">{d}</div>' for d in "일월화수목금토")
    tot = lead + ndays
    for i in range((tot + 6) // 7 * 7):
        d = i - lead + 1
        if d < 1 or d > ndays:
            cells += '<div class="cal-d off"></div>'; continue
        kind, txt = s.get("marks", {}).get(d, ("", ""))
        cells += f'<div class="cal-d {kind}"><span>{d}</span>{f"<i>{rich(txt)}</i>" if txt else ""}</div>'
    leg = "".join(f'<span class="lg-{k}">{e(t)}</span>' for k, t in s.get("legend", []))
    return bg() + frame(head(s, "gap-s") + f'<div class="cal-leg">{leg}</div><div class="cal anim">{cells}</div>', cls="frame-wide")

def r_closing(s):
    return bg() + frame(title_html(s["title"], "action-title xl seal"), cls="closing")

R = dict(cover=r_cover, statement=r_statement, chapter=r_chapter, demo=r_demo, quote=r_quote,
         compare=r_compare, flow=r_flow, grid=r_grid, stat=r_stat, cycle=r_cycle, shot=r_shot,
         vside=r_vside, cards=r_cards, cardsteps=r_cardsteps, closing=r_closing,
         zoom=r_zoom, screen=r_screen, market=r_market, cal=r_cal)

# 레이아웃 자체가 강조색 한 곳을 갖는 경우 (eyebrow 는 강조색을 양보한다)
def has_accent(s):
    blob = json.dumps(s, ensure_ascii=False)
    return ("<em>" in blob or s["k"] in ("closing", "cycle", "cardsteps", "screen")
            or (s["k"] in ("compare", "stat") and s.get("hl") is not None))

# ───────────────────────── 조립 ─────────────────────────
out = []
total = len(D)
# 장 수는 고정하지 않는다(이해가 우선, 늘어나도 된다). 설계서·덱·프롬프터 번호 1:1 만 qa 에서 본다
NO_ACC = []
for i, s in enumerate(D):
    k = s["k"]
    attrs, dots = stepattrs(s)
    cls = ["slide", f"k-{k}"]
    if s.get("prog"):
        cls.append("prog")
    # 제목에 강조가 없다고 위쪽 라벨(1부·2부)을 강조색으로 올리지 않는다 (라벨보다 제목이 중요).
    # 강조가 필요한 장이면 title 안 핵심어를 <em> 으로 감싼다
    if not has_accent(s) and s["k"] not in ("cover", "chapter"):
        NO_ACC.append(i + 1)
    if s.get("cls"):
        cls.append(s["cls"])
    out.append(
        f'<section class="{" ".join(cls)}" data-t="{e(s.get("t", k))}" data-n="{i+1}"{attrs}>'
        f'{R[k](s)}{chrome(s.get("part", ""), i+1, total)}{dots}</section>')

if SHARE:
    for s_ in D:
        if s_["k"] == "vside":
            _b64[s_["src"]] = True
    def data_uri(rel):
        mt = mimetypes.guess_type(rel)[0] or "application/octet-stream"
        return f"data:{mt};base64," + base64.b64encode((HERE / rel).read_bytes()).decode()
    missing = [r for r in sorted(_b64) if not (HERE / r).exists()]
    if missing:
        print("경고: 공유본에 못 실은 파일(없음):", ", ".join(missing))
    vjs = "window.SHARE_MEDIA=" + json.dumps({r: data_uri(r) for r in sorted(_b64) if r not in missing}) + ";"
    out = [re.sub(r'src="__SHARE__([^"]+)"', r'data-share="\1"', x) for x in out]
    headx = f"<style>{CSS}</style><script>{MOTION}</script><script>{vjs}</script>"
    tailx = f"<script>{NAV}</script>"
    name = "deck-share.html"
else:
    headx = f'<link rel="stylesheet" href="df.css?v={VER}"><script src="motion.js?v={VER}"></script>'
    tailx = f'<script src="deck.js?v={VER}"></script>'
    name = "deck.html"

doc = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(META['title'])}</title>
<link rel="icon" href="data:,">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.css">
{headx}</head>
<body data-pal="paper">
<div id="stage"><div id="deck">
{chr(10).join(out)}
</div></div>
<div id="hud"><b id="cur">1</b>/{total}</div>
{tailx}
</body></html>"""
(HERE / name).write_text(doc, encoding="utf-8")
print(f"생성: {name} · {total}장 · {len(doc)//1024}KB")
print("pending:", ", ".join(sorted(set(PENDING))) or "없음")
if NO_ACC:
    print("강조 없는 장(제목 핵심어를 <em> 으로):", ", ".join(map(str, NO_ACC)))
if NO_NEED:
    print("경고: 필요한 자료 설명(need) 없는 자리표시:", ", ".join(sorted(set(NO_NEED))))
