# -*- coding: utf-8 -*-
"""카드뉴스 만들기: cards.json + brand.json -> cards/src/NN.html -> cards/NN.png (1080x1350) + index.html + 규칙.md

외부 패키지 없이 Python 표준 라이브러리만 쓴다. 맥·윈도우에서 설치된 Chrome 또는 Edge를 헤드리스로 쓴다.
사용(AI가 실행):
  python make_cards.py --dir <작업폴더>                 전부 만들기
  python make_cards.py --dir <작업폴더> --cover-only    표지(1장)만
  python make_cards.py --dir <작업폴더> --only 3        3번 카드만 다시
  python make_cards.py --dir <작업폴더> --rules-only    규칙.md만 다시 쓰기
종료 코드 0 = 모든 카드가 1080x1350 PNG로 저장되고 글자 넘침 없음. 그 외는 메시지를 읽고 고친다.
브라우저를 억지로 끄지 않는다(실행 이미지 이름으로 종료 금지). 이 스크립트가 띄운 프로세스만 정리한다.
"""
import argparse
import html
import json
import os
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import tempfile

# 임시 폴더를 작업 폴더 안으로(AI 보호 구역에서 시스템 임시 폴더 쓰기가 막히는 경우 대비) AIHUB_LOCAL_TMP
import os as _os, tempfile as _tf
_loc = _os.path.join(_os.getcwd(), '.tmp'); _os.makedirs(_loc, exist_ok=True)
_tf.tempdir = _loc; _os.environ['TMP'] = _os.environ['TEMP'] = _os.environ['TMPDIR'] = _loc

W, H = 1080, 1350
HERE = pathlib.Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"

BROWSERS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
FONT_FALLBACK = '"Pretendard","Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR","Segoe UI",sans-serif'


def find_browser():
    env = os.environ.get("CARDNEWS_BROWSER")
    if env and os.path.exists(env):
        return env
    local = os.environ.get("LOCALAPPDATA")
    cands = list(BROWSERS)
    if local:
        cands.append(os.path.join(local, "Google", "Chrome", "Application", "chrome.exe"))
    for p in cands:
        if os.path.exists(p):
            return p
    for name in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge"):
        p = shutil.which(name)
        if p:
            return p
    return None


# ---------- 글자 처리 ----------
def rich(text):
    """*강조* -> <em>, **굵게** -> <b>. 먼저 HTML 이스케이프."""
    s = html.escape(str(text or ""), quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    return s


def lines(text):
    return [l for l in str(text or "").split("\n") if l.strip() != ""]


def title_html(text, cls="title"):
    return '<h1 class="%s" data-fit>%s</h1>' % (
        cls, "".join('<span class="ln">%s</span>' % rich(l) for l in lines(text)))


def para_html(text, cls="body"):
    return '<p class="%s" data-shrink>%s</p>' % (cls, "<br>".join(rich(l) for l in lines(text)))


MOTIFS = {
    "stack": '<svg class="motif" viewBox="0 0 400 300" aria-hidden="true">'
             '<rect x="40" y="220" width="320" height="44" rx="14" fill="var(--ink)"/>'
             '<rect x="70" y="160" width="260" height="44" rx="14" fill="var(--ink)" opacity=".78"/>'
             '<rect x="100" y="100" width="200" height="44" rx="14" fill="var(--ink)" opacity=".56"/>'
             '<rect x="130" y="40" width="140" height="44" rx="14" fill="var(--accent)"/></svg>',
    "check": '<svg class="motif" viewBox="0 0 400 300" aria-hidden="true">'
             '<rect x="60" y="40" width="280" height="220" rx="32" fill="none" stroke="var(--ink)" stroke-width="14"/>'
             '<path d="M120 150 L175 205 L285 95" fill="none" stroke="var(--accent)" stroke-width="26" '
             'stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "arrow": '<svg class="motif" viewBox="0 0 400 300" aria-hidden="true">'
             '<rect x="40" y="125" width="250" height="50" rx="25" fill="var(--ink)"/>'
             '<path d="M270 70 L360 150 L270 230 Z" fill="var(--accent)"/></svg>',
}


# ---------- 카드 종류별 본문 ----------
def inner(card, i, n):
    t = card.get("type", "point")
    img = ""
    if card.get("image"):
        img = '<div class="imgbox"><img src="%s" alt=""></div>' % html.escape(card["image"], quote=True)
    motif = MOTIFS.get(card.get("motif", ""), "")
    if "*" in str(card.get("title", "")):  # 강조색은 한 장에 한 곳: 제목에 강조가 있으면 도식은 잉크색만
        motif = motif.replace("var(--accent)", "var(--ink)")
    if t == "cover":
        return ('<div class="main cover">%s%s%s%s</div>' % (
            title_html(card.get("title", ""), "title xl"), para_html(card.get("sub", ""), "sub"), img, motif))
    if t == "steps":
        items = card.get("items", [])
        rows = "".join(
            '<li><span class="no">%d</span><div><b class="ih" data-fit>%s</b><span class="it">%s</span></div></li>' % (
                k + 1, rich(it.get("head", "")), rich(it.get("text", ""))) for k, it in enumerate(items))
        return '<div class="main">%s<ol class="steps">%s</ol></div>' % (title_html(card.get("title", "")), rows)
    if t == "compare":
        def side(key, cls):
            d = card.get(key, {})
            lis = "".join("<li>%s</li>" % rich(x) for x in d.get("items", []))
            return '<div class="side %s"><div class="lab">%s</div><ul>%s</ul></div>' % (cls, rich(d.get("label", "")), lis)
        return '<div class="main">%s<div class="cmp">%s%s</div></div>' % (
            title_html(card.get("title", "")), side("left", "l"), side("right", "r"))
    if t == "closing":
        act = card.get("action", "")
        a = '<div class="action">%s</div>' % rich(act) if act else ""
        return '<div class="main closing">%s%s%s</div>' % (
            title_html(card.get("title", ""), "title"), para_html(card.get("body", "")), a)
    # point (기본): 큰 제목 + 어두운 패널 안 본문
    return '<div class="main">%s%s<div class="panel">%s</div></div>' % (
        title_html(card.get("title", "")), img, para_html(card.get("body", "")))


CSS = """
:root{--bg:%(bg)s;--ink:%(ink)s;--accent:%(accent)s;--panel:%(panel)s;--onpanel:%(onpanel)s}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1350px;overflow:hidden}
body{background:var(--bg);color:var(--ink);font-family:%(font)s;font-weight:700;position:relative;
  -webkit-font-smoothing:antialiased;word-break:keep-all;overflow-wrap:break-word}
body.dark{background:var(--panel);color:var(--onpanel)}
.top{position:absolute;left:84px;right:84px;top:64px;height:48px;display:flex;justify-content:space-between;align-items:center;
  font-size:28px;font-weight:800;letter-spacing:.02em}
.top .tag{padding:8px 22px;border:3px solid currentColor;border-radius:999px}
.top .pg{opacity:.55}
.bot{position:absolute;left:84px;right:84px;bottom:56px;display:flex;justify-content:space-between;font-size:26px;font-weight:700;opacity:.55}
.main{position:absolute;left:84px;right:84px;top:150px;bottom:130px;display:flex;flex-direction:column;justify-content:center;gap:44px}
.main.cover{justify-content:flex-start;padding-top:70px}
.title{font-size:116px;line-height:1.12;font-weight:900;letter-spacing:-.01em;width:912px}
.title.xl{font-size:148px;line-height:1.08}
.ln{display:block;white-space:nowrap}
em{font-style:normal;color:var(--accent)}
body.dark em,.panel em{color:color-mix(in srgb,var(--accent) 45%%,#fff)}
.sub{font-size:46px;line-height:1.45;font-weight:600;opacity:.82}
.body{font-size:46px;line-height:1.5;font-weight:600}
.panel{background:var(--panel);color:var(--onpanel);border-radius:40px;padding:60px 64px}
.panel .body b{font-weight:900}
.imgbox{height:420px;border-radius:36px;overflow:hidden;background:#0001}
.imgbox img{width:100%%;height:100%%;object-fit:cover;display:block}
.motif{width:360px;height:270px;margin-top:auto;align-self:flex-end}
.steps{list-style:none;display:flex;flex-direction:column;gap:30px}
.steps li{display:flex;gap:32px;align-items:flex-start}
.steps .no{flex:none;width:76px;height:76px;border-radius:24px;background:var(--panel);color:var(--onpanel);
  display:flex;align-items:center;justify-content:center;font-size:42px;font-weight:900}
.steps .ih{display:block;font-size:56px;line-height:1.2;font-weight:900;white-space:nowrap}
.steps .it{display:block;font-size:38px;line-height:1.4;font-weight:600;opacity:.8;margin-top:6px}
.cmp{display:flex;flex-direction:column;gap:28px}
.side{border-radius:36px;padding:44px 52px}
.side.l{border:4px solid var(--ink)}
.side.r{background:var(--panel);color:var(--onpanel)}
.side .lab{font-size:34px;font-weight:900;opacity:.7;margin-bottom:18px}
.side ul{list-style:none;font-size:46px;line-height:1.45;font-weight:700}
.closing .action{align-self:flex-start;background:var(--onpanel);color:var(--panel);border-radius:999px;padding:26px 54px;font-size:46px;font-weight:900}
body.dark .main .body{opacity:.9}
"""

FIT_JS = """
(function(){
  var rep=[];
  function run(){
    document.querySelectorAll('[data-fit]').forEach(function(el){
      var s=parseFloat(getComputedStyle(el).fontSize),n=0;
      while(el.scrollWidth>el.clientWidth+1&&s>44&&n<60){s-=4;el.style.fontSize=s+'px';n++;}
      if(el.scrollWidth>el.clientWidth+1)rep.push('가로 넘침:'+el.textContent.slice(0,12));
      else if(el.classList.contains('title')&&s<84)rep.push('제목이 너무 길어 글자가 작아짐:'+el.textContent.slice(0,12));
    });
    var m=document.querySelector('.main'),s=0;
    document.querySelectorAll('[data-shrink]').forEach(function(el){el._s=parseFloat(getComputedStyle(el).fontSize);});
    var n=0;
    while(m.scrollHeight>m.clientHeight+1&&n<14){
      document.querySelectorAll('[data-shrink]').forEach(function(el){if(el._s>30){el._s-=2;el.style.fontSize=el._s+'px';}});
      n++;
    }
    if(m.scrollHeight>m.clientHeight+1)rep.push('세로 넘침');
    document.body.setAttribute('data-report',rep.length?rep.join(' / '):'ok');
  }
  if(document.fonts&&document.fonts.ready){document.fonts.ready.then(run);}else{window.addEventListener('load',run);}
})();
"""


def card_html(card, i, n, brand, handle):
    css = CSS % dict(bg=brand["bg"], ink=brand["ink"], accent=brand["accent"], panel=brand["panel"],
                     onpanel=brand["onpanel"], font=(('"%s",' % brand["font"]) if brand.get("font") else "") + FONT_FALLBACK)
    cls = "dark" if card.get("dark") or card.get("type") == "closing" else ""
    tag = rich(card.get("tag", "")) if card.get("tag") else ""
    top = '<div class="top"><span class="tag">%s</span><span class="pg">%02d / %02d</span></div>' % (tag, i, n) \
        if tag else '<div class="top"><span></span><span class="pg">%02d / %02d</span></div>' % (i, n)
    bot = '<div class="bot"><span>%s</span><span>%s</span></div>' % (
        html.escape(handle), "" if i == n else "다음 장")
    return ('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=1080">'
            '<title>카드 %02d</title><style>%s</style></head><body class="%s">%s%s%s<script>%s</script></body></html>'
            % (i, css, cls, top, inner(card, i, n), bot, FIT_JS))


# ---------- 브라우저 ----------
def hub_browser(args, timeout=120):
    """AI 보호 구역 안에서 브라우저 실행이 막히면(윈도우 Codex 등) 이 PC의 허브 서버가 대신 렌더한다."""
    import json as _json, urllib.request as _u
    here = pathlib.Path(__file__).resolve()
    for up in here.parents:
        conf = up / "hub.json"
        if conf.exists() and (up / "hub").exists():
            break
    else:
        return None
    try:
        tok = _json.loads(conf.read_text(encoding="utf-8-sig"))["token"]
        port = int(os.environ.get("AIHUB_PORT", "7710"))
        req = _u.Request("http://127.0.0.1:%d/api/browser" % port, data=_json.dumps({"args": args}).encode("utf-8"),
                         headers={"content-type": "application/json", "x-hub-token": tok})
        with _u.urlopen(req, timeout=timeout) as r:
            return _json.loads(r.read().decode("utf-8")).get("out", "")
    except Exception:
        return None


def run_browser(browser, args, timeout=90):
    shot = next((a.split("=", 1)[1] for a in args if a.startswith("--screenshot=")), None)
    try:
        out = _run_browser_local(browser, args, timeout)
    except OSError:
        out = None
    ok = (out or "").strip() if "--dump-dom" in args else (shot and os.path.exists(shot) and os.path.getsize(shot) > 0)
    if ok:
        return out
    via = hub_browser(args)
    return via if via is not None else (out or "")


def _run_browser_local(browser, args, timeout=90):
    prof = tempfile.mkdtemp(prefix="cardnews_prof_")
    cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
           "--no-default-browser-check", "--force-device-scale-factor=1", "--allow-file-access-from-files",
           "--user-data-dir=" + prof] + args
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        out, _ = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        out = b""
    finally:
        shutil.rmtree(prof, ignore_errors=True)
    return out.decode("utf-8", "replace")


def png_size(path):
    with open(path, "rb") as f:
        b = f.read(24)
    if b[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", b[16:24])


def shoot(browser, src, out):
    if out.exists():
        out.unlink()
    url = src.resolve().as_uri()
    run_browser(browser, ["--window-size=%d,%d" % (W, H), "--virtual-time-budget=5000",
                          "--screenshot=" + str(out.resolve()), url])
    return out.exists() and out.stat().st_size > 0


def check_dom(browser, src):
    dom = run_browser(browser, ["--window-size=%d,%d" % (W, H), "--virtual-time-budget=5000",
                                "--dump-dom", src.resolve().as_uri()])
    m = re.search(r'data-report="([^"]*)"', dom)
    return html.unescape(m.group(1)) if m else "측정 실패"


# ---------- 규칙.md / index.html ----------
def write_rules(d, brand, handle):
    p = d / "규칙.md"
    txt = f"""# 카드뉴스 규칙

이 규칙대로 모든 장을 만듭니다. 바꾸고 싶은 곳이 있으면 이 파일을 고쳐 달라고 말하면 됩니다.

- 크기: 4:5 세로, 1080 x 1350
- 배경: {brand['bg']} (강조가 필요한 장은 어두운 패널 {brand['panel']})
- 글자색: {brand['ink']} (어두운 패널 위에서는 {brand['onpanel']})
- 강조색: {brand['accent']} 하나만. 한 장에서 핵심 단어나 도식 한 곳에만 씁니다.
- 글꼴: {brand.get('font') or '기본 고딕'} (없으면 컴퓨터에 있는 굵은 고딕으로 대신 씁니다)
- 제목은 두 줄로 끊고 화면을 압도할 만큼 크게, 본문은 작게
- 한 장에 메시지 하나. 글자는 적게, 여백은 넉넉하게
- 사람 얼굴, 로고, 상표, 실제 서비스 화면은 그리지 않습니다. 단순한 도식과 아이콘만 씁니다.
- 아래쪽 이름 표시: {handle}
- 글자는 AI 그림이 아니라 화면 글자로 얹어서 오타와 깨짐이 없습니다.
"""
    p.write_text(txt, encoding="utf-8")
    return p


def write_index(d, pngs, topic):
    items = "".join(
        '<figure><img src="cards/%s" alt="카드 %s"><figcaption>%s</figcaption></figure>' % (p.name, p.stem, p.name)
        for p in pngs)
    txt = ('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           '<title>카드뉴스 미리보기</title><style>'
           ':root{--bg:#15161a;--fg:#e9e9ee;--mute:#9a9aa6}'
           '@media (prefers-color-scheme:light){:root{--bg:#f1f1f4;--fg:#1a1a1e;--mute:#6a6a74}}'
           'body{margin:0;padding:24px 16px 48px;background:var(--bg);color:var(--fg);font-family:"Pretendard","Apple SD Gothic Neo","Malgun Gothic",sans-serif}'
           'h1{font-size:20px;margin:0 0 4px}p{margin:0 0 20px;color:var(--mute);font-size:14px}'
           '.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}'
           'figure{margin:0}img{width:100%%;height:auto;display:block;border-radius:10px;box-shadow:0 2px 14px #0005}'
           'figcaption{margin-top:6px;font-size:13px;color:var(--mute);text-align:center}'
           '</style></head><body><h1>%s</h1><p>카드 %d장 / 1080 x 1350. 이미지를 눌러 저장하거나 cards 폴더에서 바로 쓰면 됩니다.</p>'
           '<div class="grid">%s</div></body></html>' % (html.escape(topic or "카드뉴스"), len(pngs), items))
    (d / "index.html").write_text(txt, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--cover-only", action="store_true")
    ap.add_argument("--only", type=int)
    ap.add_argument("--rules-only", action="store_true")
    a = ap.parse_args()
    d = pathlib.Path(a.dir).resolve()
    brand = json.loads((TEMPLATES / "brand.default.json").read_text(encoding="utf-8"))
    bp = d / "brand.json"
    if bp.exists():
        brand.update({k: v for k, v in json.loads(bp.read_text(encoding="utf-8")).items() if v not in (None, "")})
    spec = json.loads((d / "cards.json").read_text(encoding="utf-8"))
    cards = spec["cards"]
    n = len(cards)
    handle = spec.get("handle") or brand.get("handle") or ""
    write_rules(d, brand, handle)
    print("규칙.md 저장")
    if a.rules_only:
        return 0
    browser = find_browser()
    if not browser:
        print("브라우저 없음: Chrome 또는 Edge를 설치해야 합니다")
        return 3
    (d / "cards" / "src").mkdir(parents=True, exist_ok=True)
    if a.cover_only:
        todo = [1]
    elif a.only:
        todo = [a.only]
    else:
        todo = list(range(1, n + 1))
    bad = 0
    for i in todo:
        src = d / "cards" / "src" / ("%02d.html" % i)
        src.write_text(card_html(cards[i - 1], i, n, brand, handle), encoding="utf-8")
        rep = check_dom(browser, src)
        out = d / "cards" / ("%02d.png" % i)
        ok = shoot(browser, src, out)
        size = png_size(out) if ok else None
        state = "OK" if (ok and size == (W, H) and rep == "ok") else "FAIL"
        if state != "OK":
            bad += 1
        print("%s  카드 %02d  %s  크기=%s  글자검사=%s" % (state, i, out.name, "x".join(map(str, size)) if size else "없음", rep))
    pngs = sorted((d / "cards").glob("[0-9][0-9].png"))
    if pngs:
        write_index(d, pngs, spec.get("topic", ""))
        print("index.html 저장 (%d장)" % len(pngs))
    if not bad and not a.cover_only and not a.only and len(pngs) == n:
        import pack
        pack.pack(d, d / "cards", spec.get("topic", ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
