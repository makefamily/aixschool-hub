# -*- coding: utf-8 -*-
"""카드뉴스 템플릿 3종 만들기: deck.json -> cards/src/NN.html -> cards/NN.png (1080x1350)
 + 글자 넘침·겹침 검사 + 모아보기.png + 카드뉴스.zip

템플릿: 08-poster(포스터) / 09-editorial(에디토리얼) / 10-grunge(그런지)
외부 패키지 없이 Python 표준 라이브러리와 설치된 Chrome 또는 Edge만 쓴다.
사용(AI가 실행):
  python make_deck.py --dir <작업폴더> --template 08-poster            전부 만들기(검사·모아보기·ZIP까지)
  python make_deck.py --dir <작업폴더> --template 08-poster --only 3,5   검사에 걸린 장만 다시
  python make_deck.py --dir <작업폴더> --check-only                      원고 형식만 검사
  옵션: --out cards-b (다른 폴더에 저장) / --brand-color (brand.json 강조색을 템플릿 대표색 자리에 넣기)
종료 코드 0 = 모든 장이 1080x1350이고 검사 통과. 1 = 검사 탈락 장 있음(어느 장·왜인지 출력). 2 = 원고 형식 오류. 3 = 브라우저 없음.
"""
import argparse
import concurrent.futures
import html
import json
import pathlib
import re
import shutil
import sys
import tempfile

# 임시 폴더를 작업 폴더 안으로(AI 보호 구역에서 시스템 임시 폴더 쓰기가 막히는 경우 대비) AIHUB_LOCAL_TMP
import os as _os, tempfile as _tf
_loc = _os.path.join(_os.getcwd(), '.tmp'); _os.makedirs(_loc, exist_ok=True)
_tf.tempdir = _loc; _os.environ['TMP'] = _os.environ['TEMP'] = _os.environ['TMPDIR'] = _loc

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import deck_templates as T  # noqa: E402
from make_cards import find_browser, run_browser, png_size  # noqa: E402
import pack  # noqa: E402

SKILL = HERE.parent
FONT_DIR = SKILL / "assets" / "fonts"
W, H = 1080, 1350
KINDS = {
    "terminal": ["lines"], "code": ["title", "lines"], "flow": ["nodes"],
    "gauge": ["value", "max", "label", "bands"], "chat": ["messages"], "compare": ["left", "right"],
    "checklist": ["items"], "settings": ["title", "rows"],
}
CHECK_NAMES = {"safe": "글자가 안전 여백 밖으로 나감", "noOverflow": "글자가 상자를 넘침",
               "noTextOverlap": "글자끼리 겹침", "images": "이미지가 안 열림", "font": "글꼴이 안 열림"}


def clen(s):
    return len(str(s or "").replace(" ", ""))


def lines_of(s):
    return [l for l in str(s or "").split("\n") if l.strip()]


def validate(deck, template):
    """원고 형식 검사. 문제 목록을 돌려준다(빈 목록이면 통과)."""
    errs = []
    sl = deck.get("slides") or []
    n = len(sl)
    if n not in (5, 10):
        errs.append("장 수는 5장 또는 10장이어야 합니다(지금 %d장)" % n)
    if n < 3:
        return errs
    if sl[0].get("type") != "cover":
        errs.append("1장은 표지(cover)여야 합니다")
    if sl[-1].get("type") != "closing":
        errs.append("마지막 장은 마감(closing)이어야 합니다")
    for i, s in enumerate(sl[1:-1], 2):
        if s.get("type") != "body":
            errs.append("%d장은 본문(body)이어야 합니다" % i)
    cov = sl[0].get("f", {})
    for k in ("title", "sub"):
        if not cov.get(k):
            errs.append("표지에 %s가 없습니다" % k)
    if len(lines_of(cov.get("title"))) > 2 or any(clen(l) > 8 for l in lines_of(cov.get("title"))):
        errs.append("표지 제목은 두 줄까지, 한 줄 8자 이내로 줄이세요")
    if len(lines_of(cov.get("sub"))) > 2 or any(clen(l) > 14 for l in lines_of(cov.get("sub"))):
        errs.append("표지 부제는 두 줄까지, 한 줄 14자 이내로 줄이세요")
    if template == "10-grunge" and len(cov.get("rows") or []) < 3:
        errs.append("그런지 표지에는 본문 흐름을 대표하는 단어(rows) 3~4개가 필요합니다")
    V = (deck.get("visuals") or {}).get("slides") or {}
    kinds = []
    for i, s in enumerate(sl[1:-1], 2):
        f = s.get("f", {})
        for k in ("head", "desc", "word"):
            if not f.get(k):
                errs.append("%d장에 %s가 없습니다" % (i, k))
        if len(lines_of(f.get("head"))) > 2 or any(clen(l) > 9 for l in lines_of(f.get("head"))):
            errs.append("%d장 제목(head)은 두 줄까지, 한 줄 9자 이내로 줄이세요" % i)
        if clen(f.get("desc")) > 42:
            errs.append("%d장 설명(desc)은 42자 이내로 줄이세요" % i)
        v = V.get(str(i))
        if not v or v.get("kind") not in KINDS:
            errs.append("%d장 그림(visuals.slides.%d.kind)이 없거나 목록에 없는 종류입니다" % (i, i))
            continue
        miss = [x for x in KINDS[v["kind"]] if x not in v]
        if miss:
            errs.append("%d장 그림(%s)에 %s가 없습니다" % (i, v["kind"], ", ".join(miss)))
        if v["kind"] == "terminal":
            for l in map(str, v.get("lines") or []):
                if l.strip().startswith("$") and not re.match(r"^\$\s*[A-Za-z0-9./~_-]", l.strip()):
                    errs.append("%d장 터미널 그림의 명령은 실제 영문 명령이어야 합니다: %s" % (i, l))
        if v["kind"] == "settings":
            for r in v.get("rows") or []:
                lab, val = str(r.get("label", "")).strip(), str(r.get("value", "")).strip()
                if val not in ("on", "off") and (not val or val in lab or lab in val):
                    errs.append("%d장 설정 그림의 값이 이름을 되풀이합니다: %s" % (i, lab))
        kinds.append(v["kind"])
    if any(kinds.count(k) > 3 for k in kinds) or any(a == b for a, b in zip(kinds, kinds[1:])):
        errs.append("그림 종류가 같은 것이 3번 넘거나 연속됩니다: " + ",".join(kinds))
    cl = sl[-1].get("f", {})
    for k in ("title", "desc", "cta1", "cta2"):
        if not cl.get(k):
            errs.append("마감 장에 %s가 없습니다" % k)
    return errs


def render_one(browser, src, out):
    if out.exists():
        out.unlink()
    dom = run_browser(browser, ["--allow-file-access-from-files", "--window-size=%d,%d" % (W, H), "--virtual-time-budget=4000",
                                "--screenshot=" + str(out.resolve()), "--dump-dom", src.resolve().as_uri()])
    m = re.search(r'<script id="render-metrics" type="application/json">(.*?)</script>', dom, re.S)
    if not m:
        return {"ok": False, "reasons": ["검사값을 못 읽음(화면이 안 열렸을 수 있음)"]}
    import json as _j
    data = _j.loads(html.unescape(m.group(1)) if "&quot;" in m.group(1) else m.group(1))
    size = png_size(out) if out.exists() else None
    reasons = [CHECK_NAMES.get(k, k) for k, v in data["checks"].items() if not v]
    texts = data.get("texts") or []
    for t in texts:
        if t.get("overflow"):
            reasons.append("넘친 글: " + str(t["text"]).replace("\n", " ")[:20])
    for a, b in (data.get("overlaps") or [])[:3]:
        reasons.append("겹친 글: [%s] / [%s]" % (str(texts[a]["text"]).replace("\n", " ")[:12], str(texts[b]["text"]).replace("\n", " ")[:12]))
    if size != (W, H):
        reasons.append("크기가 %s" % ("x".join(map(str, size)) if size else "없음"))
    return {"ok": not reasons, "reasons": reasons, "size": size}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--template", default="08-poster", choices=list(T.TEMPLATES))
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default="cards")
    ap.add_argument("--images", default="images")
    ap.add_argument("--brand-color", action="store_true")
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--no-pack", action="store_true")
    a = ap.parse_args()
    d = pathlib.Path(a.dir).resolve()
    deck = json.loads((d / "deck.json").read_text(encoding="utf-8"))
    errs = validate(deck, a.template)
    if errs:
        print("원고 형식 오류 %d건:" % len(errs))
        for e in errs:
            print(" - " + e)
        return 2
    print("원고 형식 OK (%d장, 템플릿 %s)" % (len(deck["slides"]), a.template))
    if a.check_only:
        return 0
    browser = find_browser()
    if not browser:
        print("브라우저 없음: Chrome 또는 Edge를 설치해야 합니다")
        return 3
    brand = {}
    bp = d / "brand.json"
    if bp.exists():
        brand = json.loads(bp.read_text(encoding="utf-8"))
    out = d / a.out
    accent = brand.get("accent") if a.brand_color else None
    pages = T.generate(deck, out, a.template, d / a.images, FONT_DIR, brand, accent)
    n = len(pages)
    only = {int(x) for x in a.only.split(",") if x.strip()} if a.only else set(range(1, n + 1))
    todo = [(i, p) for i, p in enumerate(pages, 1) if i in only]
    if deck.get("caption"):
        (d / "caption.txt").write_text(deck["caption"], encoding="utf-8")
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futs = {pool.submit(render_one, browser, p, out / ("%02d.png" % i)): i for i, p in todo}
        for fu in concurrent.futures.as_completed(futs):
            results[futs[fu]] = fu.result()
    bad = []
    for i in sorted(results):
        r = results[i]
        size = "x".join(map(str, r["size"])) if r.get("size") else "없음"
        if r["ok"]:
            print("OK    카드 %02d  크기=%s" % (i, size))
        else:
            bad.append(i)
            print("FAIL  카드 %02d  크기=%s  이유: %s" % (i, size, " / ".join(r["reasons"])))
    allp = sorted(out.glob("[0-9][0-9].png"))
    if bad:
        print("검사 탈락 장: %s  -> 그 장 글을 줄이거나 그림을 바꾸고 --only %s 로 다시 만든다" % (",".join(map(str, bad)), ",".join(map(str, bad))))
        return 1
    if len(allp) != n:
        print("카드가 %d장 중 %d장만 있음. --only 없이 전체를 다시 만드세요" % (n, len(allp)))
        return 1
    if not a.no_pack:
        pack.pack(d, out, deck.get("topic", ""))
    print("전체 %d장 통과" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
