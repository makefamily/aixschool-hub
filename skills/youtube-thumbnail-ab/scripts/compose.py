#!/usr/bin/env python3
"""배경 이미지 + 한 줄 카피 -> 1280x720 썸네일 PNG, 그리고 3안 나란히 비교 이미지.
AI(스킬을 읽은 Claude·Codex)가 실행하는 도구다. 학생에게 이 명령을 보여주지 않는다.

  compose.py thumb --bg bg-a.png --copy "[[강조]] 한 줄 카피" --out thumb-a.png
  compose.py compare thumb-a.png thumb-b.png thumb-c.png --out compare-3up.jpg

[[단어]] 는 노란색 강조. 글자 크기는 화면 폭(1200px)에 맞게 자동으로 줄어든다.
필요: 파이썬 + Pillow(비교 이미지용), 크롬 또는 엣지(글자 합성용, 화면에 띄우지 않고 렌더). 맥·윈도우 공통.
"""
import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
FONT = SKILL / "assets/fonts/Pretendard-Black.woff2"

TPL = """<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><style>
@font-face{{font-family:'W';src:url('font.woff2') format('woff2');font-weight:900;font-display:block}}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1280px;height:720px;overflow:hidden;background:#000}}
.bg{{position:absolute;inset:0;background:url('bg.png') center/cover no-repeat}}
.sh{{position:absolute;left:0;right:0;bottom:0;height:260px;background:linear-gradient(0deg,rgba(0,0,0,.85),rgba(0,0,0,0))}}
.t{{position:absolute;left:0;right:0;bottom:{bottom}px;text-align:center}}
.t span.l{{display:inline-block;white-space:nowrap;font-family:'W';font-weight:900;font-size:{size}px;line-height:1;letter-spacing:-.04em;color:#fff;-webkit-text-stroke:14px #000;paint-order:stroke fill;text-shadow:0 8px 24px rgba(0,0,0,.7)}}
.y{{color:#ffe14d}}
</style></head><body><div class="bg"></div><div class="sh"></div><div class="t"><span class="l">{copy}</span></div>
<script>document.fonts.ready.then(()=>{{const l=document.querySelector('.l');let s={size};while(l.offsetWidth>1200&&s>60){{s-=2;l.style.fontSize=s+'px'}}}})</script>
</body></html>"""


def find_browser():
    env = os.environ.get("THUMB_BROWSER")
    cands = [env] if env else []
    cands += [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for c in cands:
        if c and Path(c).exists():
            return c
    for n in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge"):
        w = shutil.which(n)
        if w:
            return w
    sys.exit("[브라우저 없음] 크롬이나 엣지가 필요해요. 설치되어 있는지 학생에게 확인하세요.")


def render_copy(text):
    out = html.escape(text)
    return re.sub(r"\[\[(.+?)\]\]", r'<span class="y">\1</span>', out)


def thumb(a):
    out = Path(a.out).resolve()
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        shutil.copy(a.bg, d / "bg.png")
        shutil.copy(FONT, d / "font.woff2")
        (d / "t.html").write_text(TPL.format(copy=render_copy(a.copy), size=a.size, bottom=a.bottom), encoding="utf-8")
        cmd = [find_browser(), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
               "--window-size=1280,720", "--virtual-time-budget=4000", f"--screenshot={out}",
               f"--user-data-dir={d / 'profile'}", (d / "t.html").as_uri()]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if not out.exists() or out.stat().st_size < 1000:
            sys.exit(f"렌더 실패: {r.stderr[-400:]}")
    print(out)


def compare(a):
    from PIL import Image
    ims = [Image.open(p).convert("RGB").resize((640, 360)) for p in a.thumbs]
    o = Image.new("RGB", (660 * len(ims) - 20, 360), "white")
    for i, im in enumerate(ims):
        o.paste(im, (i * 660, 0))
    o.save(a.out, quality=88)
    m = Image.new("RGB", (256 * len(ims) - 10, 138), "white")  # 휴대폰 목록 크기 점검용
    for i, im in enumerate(ims):
        m.paste(im.resize((246, 138)), (i * 256, 0))
    mob = str(Path(a.out).with_name(Path(a.out).stem + "-mobile.jpg"))
    m.save(mob, quality=90)
    print(a.out, mob)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest="cmd", required=True)
    t = s.add_parser("thumb")
    t.add_argument("--bg", required=True)
    t.add_argument("--copy", required=True)
    t.add_argument("--out", required=True)
    t.add_argument("--size", type=int, default=128)
    t.add_argument("--bottom", type=int, default=34)
    c = s.add_parser("compare")
    c.add_argument("thumbs", nargs="+")
    c.add_argument("--out", required=True)
    a = p.parse_args()
    thumb(a) if a.cmd == "thumb" else compare(a)
