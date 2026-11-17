# -*- coding: utf-8 -*-
"""덱 스타일 v2 빌더 — 웨비나 덱(build3.py) 구조를 범용으로 뗀 것
python3 build.py               → deck.html (media/ 상대경로)
python3 build.py --share       → deck-share.html (이미지 내장 한 파일)
python3 build.py --src=slides_x → slides_x.py 를 읽어 deck-x.html
slides.py 에 D(장 목록)와 META 를 둔다:
  META = {"title": 탭 제목, "foot": 바닥줄 가운데(발표자), "theme": {CSS 변수: 값}(없으면 deck.css 기본 = 딥네이비·노랑),
          "labels": {라벨 바꾸기}(기본 한글), "nobox": True 면 카드 바탕을 뺀 변형}
장 유형은 README.md 표 참고. 강조: <em>(형광펜/색) · <mark>(칠한 띠). '|' = 줄바꿈
"""
import sys, html, pathlib, base64, json, re, importlib
HERE = pathlib.Path(__file__).parent
SHARE = "--share" in sys.argv
sys.path.insert(0, str(HERE))
SRC = next((a.split("=",1)[1] for a in sys.argv if a.startswith("--src=")), "slides")
_m = importlib.import_module(SRC); importlib.reload(_m)
D, META = _m.D, _m.META
LB = dict(chap="{n}부", q="질문", a="답", benefit="혜택 {n}", toc="오늘 순서", total="한눈에|보기", step="{n}단계",
          before="전", after="후", need="자료 요청", us="저희가", me="내가", price_unit="만 원", **META.get("labels", {}))
FOOT = META.get("foot", "")

def e(x): return html.escape(str(x), quote=True)
def rich(x):
    if x is None: return ""
    s = e(x)
    for t in ("em", "mark", "b", "s", "u"):
        s = s.replace(f"&lt;{t}&gt;", f"<{t}>").replace(f"&lt;/{t}&gt;", f"</{t}>")
    return s.replace("|", "<br>")

NEEDS = []
CUR = [0]
def img_src(rel):
    p = HERE / rel
    if SHARE:
        mt = {"png": "image/png", "svg": "image/svg+xml", "mp4": "video/mp4"}.get(rel.rsplit(".", 1)[-1], "image/jpeg")
        return f"data:{mt};base64," + base64.b64encode(p.read_bytes()).decode()
    return rel
def has(rel): return rel and (HERE / rel).exists()

# ── 아이콘 (선 아이콘, 24 그리드) ──
IC = {
 "compass": '<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5-5 2 2-5z"/>',
 "heart": '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
 "gift": '<rect x="4" y="9" width="16" height="11" rx="1"/><path d="M3 9h18M12 9v11M12 9c-2-4-6-4-6-1.5S10 9 12 9zM12 9c2-4 6-4 6-1.5S14 9 12 9z"/>',
 "hand": '<path d="M3 12l4-4 4 2 3-2 7 6-3 3-2-1-2 2-2-1-2 1z"/><path d="M7 8l5 5"/>',
 "alert": '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.5"/>',
 "check": '<path d="M5 12.5l4.5 4.5L19 7"/>',
 "phone": '<rect x="7" y="2.5" width="10" height="19" rx="2"/><path d="M11 18.5h2"/>',
 "chat": '<path d="M4 5h16v11H9l-5 4z"/>',
 "box": '<path d="M3 7l9-4 9 4v10l-9 4-9-4z"/><path d="M3 7l9 4 9-4M12 11v10"/>',
 "cart": '<path d="M3 4h3l2.5 11h10L21 7H7"/><circle cx="10" cy="19.5" r="1.3"/><circle cx="17" cy="19.5" r="1.3"/>',
 "star": '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>',
 "won": '<path d="M4 6l3.5 12L12 8l4.5 10L20 6M3 11h18M3 14h18"/>',
 "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c1-4.5 4.5-6.5 8-6.5s7 2 8 6.5"/>',
 "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2 20c.8-4 3.6-5.6 7-5.6s6.2 1.6 7 5.6"/><path d="M16 4.6a3.5 3.5 0 0 1 0 6.8M18.5 14.8c1.8.8 3 2.4 3.5 5.2"/>',
 "camera": '<rect x="3" y="7" width="18" height="13" rx="2"/><circle cx="12" cy="13.5" r="3.6"/><path d="M8.5 7l1.5-3h4l1.5 3"/>',
 "book": '<path d="M4 4h7a2 2 0 0 1 2 2v14a2 2 0 0 0-2-2H4zM20 4h-7a2 2 0 0 0-2 2v14a2 2 0 0 1 2-2h7z"/>',
 "play": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M10 9l5 3-5 3z"/>',
 "seat": '<path d="M6 21v-5h12v5M5 16V9a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v7"/>',
 "shield": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
 "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
 "x": '<path d="M6 6l12 12M18 6L6 18"/>',
 "arrow": '<path d="M4 12h15M13 6l6 6-6 6"/>',
 "spark": '<path d="M12 3v5M12 16v5M3 12h5M16 12h5M6 6l3 3M15 15l3 3M18 6l-3 3M9 15l-3 3"/>',
 "home": '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
 "calc": '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 7h8M8 11h2M12 11h2M8 15h2M12 15h2M8 18h2M12 18h2M16 11v7"/>',
 "edit": '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13 7l4 4"/>',
 "laptop": '<rect x="4" y="5" width="16" height="11" rx="1.5"/><path d="M2 19h20"/>',
 "map": '<path d="M9 4L3 6v14l6-2 6 2 6-2V4l-6 2z"/><path d="M9 4v14M15 6v14"/>',
 "doc": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h6M9 16h6"/>',
 "store": '<path d="M4 9l1.5-5h13L20 9M4 9h16v11H4zM4 9c0 2 3.5 2 4 0 .5 2 3.5 2 4 0 .5 2 3.5 2 4 0 .5 2 4 2 4 0"/><path d="M10 20v-5h4v5"/>',
}
def icon(n, cls="ic"):
    return f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{IC[n]}</svg>'

def need_box(nd, cls=""):
    """자료 요청 칸: 무엇이, 누가, 어떤 모양으로 필요한지"""
    title, who, desc = nd
    NEEDS.append((CUR[0], title, who, desc))
    if SHARE:  # 공유본: 담당자·내부 메모는 빼고 무엇이 들어올지만
        who, desc = "", "준비 중이에요"
    return (f'<div class="need {cls}"><div class="need-h">{icon("camera","nic")}<span>{LB["need"]}</span><i>{e(who)}</i></div>'
            f'<div class="need-t">{rich(title)}</div><div class="need-d">{rich(desc)}</div></div>')

def boxes(s):
    """빨간 박스(1-A): s["box"]=[(x, y, w, h), ...] 이미지 대비 비율(0~1). 번호는 2개 이상일 때만"""
    bs = s.get("box") or []
    return "".join(f'<i class="bx" style="left:{x*100:.1f}%;top:{y*100:.1f}%;width:{w*100:.1f}%;height:{h*100:.1f}%">'
                   + (f'<b class="bxn">{i+1}</b>' if len(bs) > 1 else "") + '</i>' for i, (x, y, w, h) in enumerate(bs))

def pic(s, cls="pic"):
    if s.get("img") and has(s["img"]):
        if s.get("box"):
            return f'<div class="{cls}"><span class="bxw"><img src="{img_src(s["img"])}" alt="">{boxes(s)}</span></div>'
        if s.get("zoomed"):  # 확대 장: 남는 칸 없이 이미지 크기를 직접 정한다(테두리가 이미지에 딱 붙게)
            w, h = _dim(s["img"])
            lines = rich(s["title"]).count("<br>") + 1
            H = 850 - (68 if s.get("eyebrow") else 0) - 84 * lines - 34 - (60 if s.get("sub") else 0)
            k = min(1620 / w, H / h)
            return f'<div class="{cls} zoomed"><img src="{img_src(s["img"])}" alt="" style="width:{w*k:.0f}px;height:{h*k:.0f}px"></div>'
        return f'<div class="{cls}"><img src="{img_src(s["img"])}" alt=""></div>'
    if s.get("need"):
        return need_box(s["need"], cls)
    if s.get("img"):  # 경로는 적었는데 파일이 아직 없을 때
        return need_box((s["img"], "", "파일 없음 — media/ 에 넣으면 바로 바뀌어요"), cls)
    return f'<div class="{cls}"></div>'

def eb(x, cls="eb"):
    return f'<div class="{cls} a">{rich(x)}</div>' if x else ""
def sub(x, cls="sub"):
    return f'<p class="{cls} a">{rich(x)}</p>' if x else ""

# ───────── 레이아웃 ─────────
def r_cover(s):
    return (f'<div class="cov-l">{eb(s.get("eyebrow"))}<h1 class="t-xl a">{rich(s["title"])}</h1>{sub(s.get("sub"))}</div>'
            f'<div class="cov-r a">{pic(s, "cov-pic")}</div>')

def r_hero(s):
    al = s.get("align", "c")
    size = {"xxl": "t-xxl", "xl": "t-xl", "l": "t-l"}[s.get("size", "xl")]
    return (f'<div class="hero al-{al}">{eb(s.get("eyebrow"))}'
            f'<h1 class="{size} a">{rich(s["title"])}</h1>{sub(s.get("sub"))}</div>')

def r_qa(s):
    if s.get("ask") and (s.get("img") or s.get("need")):  # 질문 → 답 + 그 답을 보여 주는 화면
        return (f'<div class="split sp-r qa-sp"><div class="sp-txt"><div class="qa-lab a">{LB["q"]}</div>'
                f'<div class="qa-ask a">{rich(s["ask"].replace("|", " "))}</div>'
                f'<h1 class="t-l a" data-step="1">{rich(s["title"])}</h1>{sub(s.get("sub"))}</div>'
                f'<div class="sp-pic" data-step="1">{pic(s, "pic frame")}</div></div>')
    if s.get("ask"):  # 질문과 답을 한 장에 (재구성안 원칙)
        return (f'<div class="hero al-c"><div class="qa-lab a">{LB["q"]}</div>'
                f'<div class="qa-ask a">{rich(s["ask"].replace("|", " "))}</div>'
                f'<h1 class="t-xl a" data-step="1">{rich(s["title"])}</h1>{sub(s.get("sub"))}</div>')
    lab = LB["q"] if s.get("q", "A") == "Q" else LB["a"]
    return (f'<div class="hero al-c"><div class="qa-lab a">{lab}</div>'
            f'<h1 class="t-xl a">{rich(s["title"])}</h1>{sub(s.get("sub"))}</div>')

def r_chap(s):
    return (f'<div class="hero al-c"><div class="chap-n a">{e(LB["chap"].format(n=s["n"]))}</div>'
            f'<h1 class="t-xl a">{rich(s["title"])}</h1>{sub(s.get("sub"))}</div>')

def r_split(s):
    side = s.get("side", "l")
    items = ""
    if s.get("items"):
        items = '<ul class="sp-items">' + "".join(
            f'<li class="a">{icon("check","ic-s")}<div><b>{rich(a)}</b><span>{rich(b)}</span></div></li>' for a, b in s["items"]) + "</ul>"
    txt = f'<div class="sp-txt">{eb(s.get("eyebrow"))}<h1 class="t-l a">{rich(s["title"])}</h1>{sub(s.get("sub"))}{items}</div>'
    wide = bool(s.get("img") and has(s["img"]) and _dim(s["img"])[0] / _dim(s["img"])[1] > 1.05)  # 가로 캡처: 칸을 캡처에 맞춘다(자르지 않음, 3-16)
    p = f'<div class="sp-pic a">{pic(s, "pic frame" if wide else "pic fill")}</div>'
    return f'<div class="split sp-{side}{" wide" if wide else ""}">{p + txt if side == "l" else txt + p}</div>'

def r_proof(s):
    cap = f'<div class="proof-cap a">{rich(s["cap"])}</div>' if s.get("cap") else ""
    return (f'<div class="proof"><div class="proof-h">{eb(s.get("eyebrow"))}<h1 class="t-m a">{rich(s["title"])}</h1>{sub(s.get("sub"), "sub sm")}</div>'
            f'<div class="proof-b a">{pic(s, "pic frame")}</div>{cap}</div>')

def r_phone(s):
    phones = "".join(
        f'<div class="phone a" style="--d:{i*120}ms"><div class="phone-in">'
        + (f'<video src="{img_src(x)}" poster="{img_src(x[:-4] + ".jpg")}" autoplay muted loop playsinline preload="auto"></video>' if isinstance(x, str) and x.endswith(".mp4") and has(x) else
           f'<img src="{img_src(x)}" alt=""{" class=fit" if _dim(x)[0] / _dim(x)[1] > .52 else ""}>' if isinstance(x, str) and has(x) else need_box(x if isinstance(x, tuple) else ("화면 캡처", "", ""), "inph"))
        + '</div></div>' for i, x in enumerate(s["shots"]))
    return (f'<div class="phwrap"><div class="ph-txt">{eb(s.get("eyebrow"))}<h1 class="t-l a">{rich(s["title"])}</h1>{sub(s.get("sub"))}</div>'
            f'<div class="phones n{len(s["shots"])}">{phones}</div></div>')

def r_case(s):
    tags = "".join(f'<span>{e(t)}</span>' for t in s.get("tags", []))
    aside = (f'<figure class="gl-i a ba-img">{_media(s["aside"], 560, 560 / (_dim(s["aside"])[0] / _dim(s["aside"])[1]))}</figure>' if s.get("aside") else "")
    ba = (f'<div class="ba">{aside}<div class="ba-b a"><i>{LB["before"]}</i>{rich(s["before"])}</div>'
          f'<div class="ba-arrow a">{icon("arrow","ic-a")}</div>'
          f'<div class="ba-a a"><i>{LB["after"]}</i><b>{rich(s["after"])}</b></div></div>')
    return (f'<div class="case"><div class="case-h"><h1 class="t-m a">{rich(s["who"])}</h1><div class="tags a">{tags}</div></div>'
            f'<div class="case-b"><div class="case-pic a">{pic(s, "pic frame") if not s.get("stack") else f'<div class="gl-b">{_stack(s["stack"], 820, 720)}</div>'}</div>{ba}</div></div>')

def fmt(n):
    return f"{n:,}"
def r_bars(s):
    mx = max(v for _, v, _ in s["rows"])
    rows = "".join(
        f'<div class="bar-row a" style="--d:{i*200}ms"><div class="bar-l">{rich(l)}</div>'
        f'<div class="bar-track"><div class="bar{" hl" if i == len(s["rows"]) - 1 else ""}" style="--w:{max(v / mx * 100, 1.2):.2f}%"></div></div>'
        f'<div class="bar-v">{rich(lab)}</div></div>' for i, (l, v, lab) in enumerate(s["rows"]))
    return (f'<div class="chart">{eb(s.get("eyebrow"))}<h1 class="t-l a">{rich(s["title"])}</h1>'
            f'<div class="bars">{rows}</div>{sub(s.get("sub"), "sub sm")}</div>')

def r_stats(s):
    cells = "".join(
        f'<div class="st a" style="--d:{i*150}ms">{icon(ic,"ic-st")}<div class="st-l">{rich(l)}</div>'
        f'<div class="st-v"><span class="cnt" data-to="{v}">0</span><small>{e(u)}</small></div><div class="st-c">{rich(c)}</div></div>'
        for i, (ic, l, v, u, c) in enumerate(s["items"]))
    return (f'<div class="stats-w">{eb(s.get("eyebrow"))}<h1 class="t-l a">{rich(s["title"])}</h1>'
            f'<div class="stats n{len(s["items"])}">{cells}</div>{sub(s.get("sub"), "sub sm")}</div>')

def r_equation(s):
    a, b, c = s["parts"]
    return (f'<div class="hero al-c">{eb(s.get("eyebrow"))}<div class="eq a">'
            f'<div class="eq-c"><b>{rich(a[0])}</b><span>{rich(a[1])}</span></div><div class="eq-o">×</div>'
            f'<div class="eq-c"><b>{rich(b[0])}</b><span>{rich(b[1])}</span></div><div class="eq-o">=</div>'
            f'<div class="eq-c res"><b>{rich(c[0])}</b><span>{rich(c[1])}</span></div></div>{sub(s.get("sub"))}</div>')

def r_timeline(s):
    act = s.get("active", len(s["items"]) - 1)
    its = "".join(
        f'<div class="tl-i a{" on" if i == act else ""}{" bad" if bad else ""}" style="--d:{i*120}ms"><div class="tl-dot"></div>'
        f'<div class="tl-k">{rich(k)}</div><div class="tl-t">{rich(t)}</div></div>'
        for i, (k, t, bad) in enumerate(s["items"]))
    return (f'<div class="tlw">{eb(s.get("eyebrow"))}<h1 class="t-l a">{rich(s["title"])}</h1>'
            f'<div class="tl">{its}</div>{sub(s.get("sub"), "sub sm")}</div>')

def r_steps4(s):
    """단계 칸: s["steps"]=[(아이콘, 제목, 설명)], s["active"]=켜 둘 칸(0부터, 없으면 모두 같게). 같은 단계표를 여러 번 넣어 지금 위치를 보여 준다"""
    act = s.get("active")
    STEPS = s["steps"]
    cells = "".join(
        f'<div class="s4 a{" on" if act == i else ""}{" dim" if act is not None and act != i else ""}" style="--d:{i*140}ms">'
        f'<div class="s4-n">{e(LB["step"].format(n=i+1))}</div>{icon(ic,"ic-s4")}<div class="s4-t">{e(t)}</div><div class="s4-d">{e(d)}</div></div>'
        + (f'<div class="s4-ar a" style="--d:{i*140+70}ms">{icon("arrow","ic-a")}</div>' if i < len(STEPS) - 1 else "")
        for i, (ic, t, d) in enumerate(STEPS))
    return (f'<div class="s4w">{eb(s.get("eyebrow"))}<h1 class="t-l a">{rich(s["title"])}</h1>'
            f'<div class="s4row">{cells}</div></div>')

def r_reasons(s):
    its = "".join(
        f'<div class="rs" data-step="{i+1}"><div class="rs-n">0{i+1}</div>{icon(s.get("icon","alert"),"ic-rs")}'
        f'<div><b>{rich(t)}</b><span>{rich(d)}</span></div></div>' for i, (t, d) in enumerate(s["items"]))
    return (f'<div class="rsw">{eb(s.get("eyebrow"))}<h1 class="t-l a">{rich(s["title"])}</h1><div class="rsl">{its}</div></div>')

def r_vs(s):
    (lt, ld), (rt, rd) = s["left"], s["right"]
    return (f'<div class="vsw">{eb(s.get("eyebrow"))}<h1 class="t-l a">{rich(s["title"])}</h1><div class="vs">'
            f'<div class="vs-c no" data-step="1"><div class="vs-m">{icon("x","ic-vs")}</div><b>{rich(lt)}</b><span>{rich(ld)}</span></div>'
            f'<div class="vs-mid a">{icon("arrow","ic-a")}</div>'
            f'<div class="vs-c yes" data-step="2"><div class="vs-m">{icon("check","ic-vs")}</div><b>{rich(rt)}</b><span>{rich(rd)}</span></div></div>{sub(s.get("sub"), "sub sm")}</div>')

def r_chain(s):
    n = len(s["nodes"])
    cells = "".join(
        f'<div class="ch-i" data-step="{i+1}">{icon(ic,"ic-ch")}<b>{rich(t)}</b><span>{rich(d)}</span></div>'
        + (f'<div class="ch-ar" data-step="{i+2}">{icon("arrow","ic-a")}</div>' if i < n - 1 else "")
        for i, (ic, t, d) in enumerate(s["nodes"]))
    return (f'<div class="chw">{eb(s.get("eyebrow"))}<h1 class="t-l a">{rich(s["title"])}</h1>'
            f'<div class="chain">{cells}</div>{sub(s.get("sub"), "sub sm")}</div>')

def r_benefit(s):
    p = pic(s, "pic frame") if (s.get("img") or s.get("need")) else ""
    body = (f'<div class="bn-txt"><div class="bn-lab a">{e(LB["benefit"].format(n=s["n"]))}</div>'
            f'<div class="bn-ic a">{icon(s.get("icon","gift"),"ic-bn")}</div>'
            f'<h1 class="t-l a">{rich(s["title"])}</h1>{sub(s.get("sub"))}</div>')
    return f'<div class="bn{" with" if p else ""}">{body}{f"<div class=bn-pic>{p}</div>" if p else ""}</div>'

def r_total(s):
    rows = "".join(f'<div class="tt-r" data-step="{i+1}"><span>{i+1:02d}</span><b>{rich(t)}</b><i>{rich(d)}</i></div>'
                   for i, (t, d) in enumerate(s["rows"]))
    return (f'<div class="tt"><div class="tt-h"><div class="tt-big a">{rich(LB["total"])}</div>{sub(s.get("sub"), "sub sm")}</div>'
            f'<div class="tt-l">{rows}</div></div>')

def r_price(s):
    cards = "".join(
        f'<div class="pc{" hl" if c.get("hl") else ""}" data-step="{i+1}"><div class="pc-h">{e(c["name"])}</div>'
        f'<div class="pc-p"><span class="cnt" data-to="{c["price"]}">0</span><small>{e(c.get("unit", LB["price_unit"]))}</small></div>'
        + '<ul>' + "".join('<li>' + icon("check", "ic-s") + rich(x) + '</li>' for x in c["items"]) + '</ul>'
        + (f'<div class="pc-stamp">{e(c["stamp"])}</div>' if c.get("stamp") else "") + '</div>'
        for i, c in enumerate(s["cards"]))
    return f'<div class="pw"><h1 class="t-l a al-c">{rich(s["title"])}</h1><div class="pcs">{cards}</div>{sub(s.get("sub"), "sub sm al-c")}</div>'

def r_checklist(s):
    its = "".join(f'<li data-step="{i+1}">{icon("check","ic-ck")}<span>{rich(x)}</span></li>' for i, x in enumerate(s["items"]))
    return f'<div class="ckw"><div class="ck-l">{eb(s.get("eyebrow"))}<h1 class="t-l a">{rich(s["title"])}</h1></div><ul class="ck">{its}</ul></div>'

def r_countdown(s):
    return (f'<div class="hero al-c">{eb(s.get("eyebrow"))}<h1 class="t-l a">{rich(s["title"])}</h1>'
            f'<div class="timer a" data-sec="{s["sec"]}">--:--</div>{sub(s.get("sub"))}</div>')

def r_poll(s):
    ops = "".join(f'<div class="po a" style="--d:{i*150}ms"><b>{i+1}</b><span>{rich(o)}</span></div>' for i, o in enumerate(s["options"]))
    return (f'<div class="pollw">{eb(s.get("eyebrow"))}<h1 class="t-l a al-c">{rich(s["title"])}</h1>'
            f'<div class="polls">{ops}</div>{sub(s.get("sub"), "sub sm al-c")}</div>')

def r_mosaic(s):
    cells = []
    for i, x in enumerate(s["imgs"]):
        if isinstance(x, str) and has(x):
            cells.append(f'<div class="mo a" style="--d:{i*80}ms"><img src="{img_src(x)}" alt=""></div>')
        else:
            cells.append(f'<div class="mo a" style="--d:{i*80}ms">{need_box(x, "inmo")}</div>')
    return (f'<div class="mow">{eb(s.get("eyebrow"))}<h1 class="t-m a">{rich(s["title"])}</h1>'
            f'<div class="mos n{len(s["imgs"])}">{"".join(cells)}</div></div>')

def r_logos(s):
    cols = []
    for gi, (cat, items) in enumerate(s["groups"]):
        lg = "".join(
            f'<div class="lg-i {it[2]}"><div class="lg-m"><img src="{img_src(it[0])}" alt="{e(it[1])}"></div>'
            f'<div class="lg-t">{"".join(f"<span>{e(t)}</span>" for t in it[3])}</div></div>'
            for it in items if has(it[0]))
        cols.append(f'<div class="lg-c a" style="--d:{gi*120}ms"><div class="lg-h">{rich(cat)}</div><div class="lg-l">{lg}</div></div>')
    return (f'<div class="proof"><div class="proof-h">{eb(s.get("eyebrow"))}<h1 class="t-m a">{rich(s["title"])}</h1>{sub(s.get("sub"), "sub sm")}</div>'
            f'<div class="lgs n{len(cols)}">{"".join(cols)}</div></div>')

# ── 원본 비율 그대로 보여 주는 갤러리 (자르지 않고 칸을 이미지에 맞춘다) ──
def _dim(rel):
    from PIL import Image
    p = rel[:-4] + ".jpg" if rel.endswith(".mp4") else rel
    if not (HERE / p).exists():
        return (1600, 900)  # 아직 없는 이미지: 16:9 빈 칸으로 자리만 잡는다
    with Image.open(HERE / p) as im: return im.size
def _media(rel, w, h):
    st = f'width:{w:.0f}px;height:{h:.0f}px'
    if not has(rel):
        NEEDS.append((CUR[0], rel, "", "파일 없음"))
        return f'<div class="need" style="{st};min-height:0"><div class="need-h">{icon("camera","nic")}<span>{LB["need"]}</span></div><div class="need-t">{e(rel)}</div></div>'
    if rel.endswith(".mp4"):
        return (f'<video src="{img_src(rel)}" poster="{img_src(rel[:-4] + ".jpg")}" autoplay muted loop playsinline '
                f'preload="auto" style="{st}"></video>')
    return f'<img src="{img_src(rel)}" alt="" style="{st}">'
def _rows(rows, W, H, gap=24, caph=0):
    """행마다 높이를 맞추고, 폭은 원본 비율대로. 상자(W×H)를 넘지 않는 가장 큰 크기"""
    rows = [[x if isinstance(x, dict) else {"src": x} for x in r] for r in rows]
    for r in rows:
        for x in r:
            w, h = _dim(x["src"]); x["ar"] = w / h; x["nat"] = h
    nr = len(rows)
    share = (H - gap * (nr - 1)) / nr - caph
    html_rows, d = [], 0
    for r in rows:
        h = min(share, (W - gap * (len(r) - 1)) / sum(x["ar"] for x in r))
        h = min(h, max(x["nat"] for x in r) * 1.6)  # 원본보다 1.6배 넘게 키우지 않는다
        cells = ""
        for x in r:
            cap = f'<figcaption>{rich(x["cap"])}</figcaption>' if x.get("cap") else ""
            cells += f'<figure class="gl-i a" style="--d:{d*90}ms">{_media(x["src"], h * x["ar"], h)}{cap}</figure>'
            d += 1
        html_rows.append(f'<div class="gl-r">{cells}</div>')
    return "".join(html_rows)

def _stack(items, W, H, gap=24):
    """세로로 쌓되 폭을 같게. 높이 합이 H를 넘지 않는 가장 큰 폭"""
    xs = [{"src": x} if isinstance(x, str) else x for x in items]
    for x in xs:
        w, h = _dim(x["src"]); x["ar"] = w / h; x["natw"] = w
    w = min(W, (H - gap * (len(xs) - 1)) / sum(1 / x["ar"] for x in xs), max(x["natw"] for x in xs) * 1.6)
    return "".join(f'<figure class="gl-i a" style="--d:{i*120}ms">{_media(x["src"], w, w / x["ar"])}</figure>' for i, x in enumerate(xs))

def r_gal(s):
    lay = s.get("lay", "top")
    rows = s["rows"]
    caph = 44 if any(isinstance(x, dict) and x.get("cap") for r in rows for x in r) else 0
    if lay == "bg":
        imgs = [x if isinstance(x, str) else x["src"] for r in rows for x in r]
        bgs = "".join(f'<div class="gb-i"><img src="{img_src(x)}" alt=""></div>' for x in imgs)
        return (f'<div class="gb">{bgs}</div><div class="gb-sh"></div>'
                f'<div class="gb-t">{eb(s.get("eyebrow"))}<h1 class="t-xl a">{rich(s["title"])}</h1>{sub(s.get("sub"))}</div>')
    items = ""
    if s.get("items"):
        items = '<ul class="sp-items">' + "".join(
            f'<li class="a">{icon("check","ic-s")}<div><b>{rich(a)}</b><span>{rich(b)}</span></div></li>' for a, b in s["items"]) + "</ul>"
    if lay == "side":
        W = s.get("w", 900)
        txt = f'<div class="gl-txt">{eb(s.get("eyebrow"))}<h1 class="t-l a">{rich(s["title"])}</h1>{sub(s.get("sub"))}{items}</div>'
        box = f'<div class="gl-b" style="width:{W}px">{_rows(rows, W, 850, caph=caph)}</div>'
        return f'<div class="gal side">{box + txt if s.get("side", "r") == "l" else txt + box}</div>'
    lines = rich(s["title"]).count("<br>") + 1
    H = 850 - (68 if s.get("eyebrow") else 0) - 84 * lines - 34 - (60 if s.get("sub") else 0)
    return (f'<div class="gal top"><div class="proof-h">{eb(s.get("eyebrow"))}<h1 class="t-m a">{rich(s["title"])}</h1>{sub(s.get("sub"), "sub sm")}</div>'
            f'<div class="gl-b">{_rows(rows, 1620, H, caph=caph)}</div></div>')

def r_flow(s):
    """역할이 갈리는 진행 순서: 저희가 하는 칸은 보라, 내가 하는 칸은 연보라"""
    cells = []
    for i, (who, ic, t, d) in enumerate(s["steps"]):
        us = who == "저희"
        cells.append(f'<div class="fl-c a{" us" if us else ""}" style="--d:{i*130}ms"><div class="fl-top"><span class="fl-n">{i+1:02d}</span>'
                     f'<span class="fl-who">{LB["us"] if us else LB["me"]}</span></div>{icon(ic, "fl-ic")}'
                     f'<div class="fl-t">{rich(t)}</div><div class="fl-d">{rich(d)}</div></div>')
        if i < len(s["steps"]) - 1:
            cells.append(f'<div class="fl-ar a" style="--d:{i*130+60}ms">{icon("arrow", "ic-a")}</div>')
    band = "".join(f'<div class="fl-b a" style="--d:{700+i*120}ms"><b>{rich(k)}</b><span>{rich(v)}</span></div>' for i, (k, v) in enumerate(s.get("band", [])))
    return (f'<div class="flw"><div class="proof-h">{eb(s.get("eyebrow"))}<h1 class="t-m a">{rich(s["title"])}</h1>{sub(s.get("sub"), "sub sm")}</div>'
            f'<div class="fl-row">{"".join(cells)}</div><div class="fl-band">{band}</div></div>')

def r_toc(s):
    its = "".join(f'<div class="toc-i" data-step="{i+1}"><span>0{i+1}</span><b>{rich(t)}</b><i>{rich(d)}</i></div>'
                  for i, (t, d) in enumerate(s["items"]))
    return (f'<div class="tocw"><div class="toc-h"><div class="toc-big a">{rich(LB["toc"])}</div>{sub(s.get("sub"), "sub sm")}</div>'
            f'<div class="toc-l">{its}</div></div>')

def r_plan(s):
    cols = "".join(
        f'<div class="pl-c{" hl" if c.get("hl") else ""}" data-step="{i+1}"><div class="pl-k">{e(c["k"])}</div>'
        f'<div class="pl-t">{rich(c["t"])}</div><ul>' + "".join(f'<li>{icon("check","ic-s")}<span>{rich(x)}</span></li>' for x in c["items"]) + '</ul></div>'
        for i, c in enumerate(s["cols"]))
    return f'<div class="plw">{eb(s.get("eyebrow"))}<h1 class="t-l a">{rich(s["title"])}</h1><div class="pl n{len(s["cols"])}">{cols}</div>{sub(s.get("sub"), "sub sm")}</div>'

def r_closing(s):
    return f'<div class="hero al-c"><h1 class="t-xxl a">{rich(s["title"])}</h1>{sub(s.get("sub"))}</div>'

def r_market(s):
    """3-A 시중 서비스 한 장: 실제 화면(또는 영상) + 가격 태그 → 오른쪽에 '이런 걸 돈 주고 써요 ↓ 우리는'"""
    m = s["img"]
    if m.endswith(".mp4"):
        vis = (f'<div class="phone mk-ph"><div class="phone-in"><video src="{img_src(m)}" poster="{img_src(m[:-4] + ".jpg")}" '
               f'autoplay muted loop playsinline preload="auto"></video></div></div>')
    else:
        vis = f'<img class="mk-img" src="{img_src(m)}" alt="">'
    tag = f'<div class="mk-tag{" alt" if s.get("tag_alt") else ""}">{rich(s["tag"])}</div>' if s.get("tag") else ""
    src = f'<div class="mk-src">{rich(s["src"])}</div>' if s.get("src") else ""
    (a, ad), (b, bd) = s["side"]
    side = (f'<div class="mk-side"><div class="mk-s1" data-step="1"><b>{rich(a)}</b><span>{rich(ad)}</span></div>'
            f'<div class="mk-ar" data-step="2">{icon("arrow","ic-a")}</div>'
            f'<div class="mk-s2" data-step="2"><b>{rich(b)}</b><span>{rich(bd)}</span></div></div>')
    return (f'<div class="mk"><div class="proof-h">{eb(s.get("eyebrow"))}<h1 class="t-m a">{rich(s["title"])}</h1></div>'
            f'<div class="mk-b"><div class="mk-vis a"><div class="mk-wrap">{vis}{tag}</div>{src}</div>{side}</div></div>')

def r_cal(s):
    """2-A 달력: s["year"], s["month"], s["marks"]={일: (종류, 글)} 종류 = today·class·span"""
    import calendar
    first, ndays = calendar.monthrange(s["year"], s["month"])  # 월=0
    lead = (first + 1) % 7  # 일요일 시작
    cells = "".join(f'<div class="cal-h">{d}</div>' for d in "일월화수목금토")
    tot = lead + ndays
    for i in range((tot + 6) // 7 * 7):
        d = i - lead + 1
        if d < 1 or d > ndays:
            cells += '<div class="cal-d off"></div>'; continue
        kind, txt = s["marks"].get(d, ("", ""))
        cells += f'<div class="cal-d {kind}"><span>{d}</span>{f"<i>{rich(txt)}</i>" if txt else ""}</div>'
    leg = "".join(f'<span class="lg-{k}">{e(t)}</span>' for k, t in s.get("legend", []))
    return (f'<div class="calw"><div class="cal-top"><div class="proof-h">{eb(s.get("eyebrow"))}<h1 class="t-m a">{rich(s["title"])}</h1></div>'
            f'<div class="cal-leg a">{leg}</div></div><div class="cal a">{cells}</div>{sub(s.get("sub"), "sub sm al-c")}</div>')

def r_screen(s):
    """따라하기 페이지 화면을 덱 전체에 꽉 차게. 캡처는 960×540 2배라 16:9 그대로 맞는다"""
    return f'<div class="scr"><img src="{img_src(s["img"])}" alt="">{boxes(s)}</div>'

R = dict(screen=r_screen, market=r_market, cal=r_cal, flow=r_flow, gal=r_gal, logos=r_logos, cover=r_cover, hero=r_hero, qa=r_qa, chap=r_chap, split=r_split, proof=r_proof, phone=r_phone,
         case=r_case, bars=r_bars, stats=r_stats, equation=r_equation, timeline=r_timeline, steps4=r_steps4,
         reasons=r_reasons, vs=r_vs, chain=r_chain, benefit=r_benefit, total=r_total,
         price=r_price, checklist=r_checklist, toc=r_toc, plan=r_plan, countdown=r_countdown, poll=r_poll, mosaic=r_mosaic, closing=r_closing)
DEFBG = dict(cover="k", chap="p", closing="p", qa=None, countdown="k", total="w", price="w")

out = []
for i, s in enumerate(D):
    CUR[0] = i + 1
    k = s["k"]
    bg = s.get("bg") or ("k" if s.get("lay") == "bg" else None) or DEFBG.get(k) or ("k" if (k == "qa" and s.get("q") == "Q") else "w")
    body = R[k](s)
    steps = len(re.findall(r'data-step="(\d+)"', body))
    mx = max([int(x) for x in re.findall(r'data-step="(\d+)"', body)] or [0])
    foot = (f'<div class="foot"><span>{e(s.get("part",""))}</span><span>{e(FOOT)}</span>'
            f'<span class="pg">{i+1:03d}</span></div>')
    out.append(f'<section class="sl slide k-{k} bg-{bg}" data-steps="{mx}" data-n="{i+1}">{body}{foot}</section>')

CSS = (HERE / "deck.css").read_text()
if META.get("theme"):
    CSS += ":root{" + ";".join(f"{k}:{v}" for k, v in META["theme"].items()) + "}"
JS = (HERE / "deck.js").read_text()
font = ('<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">')
doc = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">{'<meta name="robots" content="noindex,nofollow">' if SHARE else ""}
<title>{e(META['title'])}</title><link rel="icon" href="data:,">{font}<style>{CSS}</style></head>
<body class="{'nobox' if META.get('nobox') else ''}"><div id="deck">{''.join(out)}</div><div id="prog"><i></i></div><div id="hud"><span id="cur">1</span> / {len(D)}</div>
<script>{JS}</script></body></html>"""
_suf = "" if SRC == "slides" else "-" + SRC.replace("slides", "").strip("_-")
name = ("deck-share" if SHARE else "deck") + _suf + ".html"
(HERE / name).write_text(doc)
print(f"생성: {name} · {len(D)}장 · {len(doc)//1024}KB · 자료 요청 {len(NEEDS)}칸")
if "--needs" in sys.argv:
    import collections
    by = collections.OrderedDict()
    for n, t, w, d in NEEDS:
        by.setdefault(w, []).append((n, t, d))
    lines = [f"# {META['title']} · 자료 요청 목록", "", f"덱 {len(D)}장 기준. 장 번호는 공유 링크 오른쪽 아래 번호와 같아요.", ""]
    for w, rows in by.items():
        lines += [f"## {w} ({len(rows)}건)", "", "| 장 | 필요한 자료 | 어떤 모양으로 |", "|---|---|---|"]
        lines += [f"| {n} | {t.replace('|',' ')} | {d.replace('|',' ')} |" for n, t, d in rows]
        lines.append("")
    ap = HERE / "needs-appendix.md"
    def _num(m):  # {{#키워드;키워드}} → 그 문구가 들어 있는 장 번호
        hits = sorted({i + 1 for k in m.group(1).split(";") for i, s in enumerate(D) if k in " ".join(str(v) for v in s.values())})
        if not hits: raise SystemExit(f"needs-appendix: 장을 못 찾음 → {m.group(1)}")
        return "·".join(map(str, hits))
    apx = re.sub(r"\{\{#(.+?)\}\}", _num, ap.read_text()) if ap.exists() else ""
    (HERE.parent / "자료요청-목록.md").write_text("\n".join(lines) + apx)
    print("자료요청-목록.md 저장")
