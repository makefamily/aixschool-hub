#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HWPX 셀 넘침·색상 검사기 — 페이지 증가와 파란 예시 서식을 저장 전에 잡는다.

사용법:
    python3 fit_check.py <파일.hwpx> [--baseline 원본.hwpx] [--all]

--baseline 을 주면 원본 양식에도 원래 있던 넘침(제목·안내문 등)은 빼고
내가 채운 값 때문에 새로 생긴 넘침만 보여준다. 실무에서는 항상 주는 게 좋다.

출력: 넘치는 셀(줄 수·필요 높이·셀 높이)과 비검정 텍스트 목록.
새로 생긴 넘침이 있으면 exit 1.
"""
import sys, zipfile, unicodedata
from lxml import etree


def wide(ch):
    return unicodedata.east_asian_width(ch) in ("W", "F")


def load(path):
    z = zipfile.ZipFile(path)
    hdr = etree.fromstring(z.read("Contents/header.xml"))
    HH = hdr.nsmap.get("hh")
    cp = {}
    for c in hdr.iter(f"{{{HH}}}charPr"):
        cp[c.get("id")] = (int(c.get("height")), c.get("textColor"))
    secs = [n for n in z.namelist() if n.startswith("Contents/section")]
    roots = [etree.fromstring(z.read(s)) for s in sorted(secs)]
    return cp, roots


def scan(path):
    """(넘침 목록, 비검정 목록) 반환"""
    cp, roots = load(path)
    over, colored = [], []
    for root in roots:
        HP = root.nsmap["hp"]
        q = lambda t: f"{{{HP}}}{t}"
        for ti, tbl in enumerate(root.iter(q("tbl"))):
            for tc in tbl.iter(q("tc")):
                a = tc.find(q("cellAddr"))
                s = tc.find(q("cellSz"))
                m = tc.find(q("cellMargin"))
                if a is None or s is None:
                    continue
                pad = (int(m.get("left")) + int(m.get("right"))) if m is not None else 1020
                W = int(s.get("width")) - pad
                H = int(s.get("height"))
                key = (ti, int(a.get("rowAddr")), int(a.get("colAddr")))
                for r in tc.iter(q("run")):
                    txt = "".join(t.text or "" for t in r.findall(q("t")))
                    if not txt.strip():
                        continue
                    h, color = cp.get(r.get("charPrIDRef"), (1100, "#000000"))
                    w = sum(h if wide(c) else h * 0.5 for c in txt)
                    lines = max(1, -(-int(w) // max(1, W)))
                    need = lines * int(h * 1.32)
                    if need > H:
                        over.append((key, lines, need, H, txt[:30]))
                    if color != "#000000":
                        colored.append((key, color, txt[:30]))
    return over, colored


def check(path, baseline=None, show_all=False):
    over, colored = scan(path)
    if baseline:
        base_keys = {k for k, *_ in scan(baseline)[0]}
        over = [row for row in over if row[0] not in base_keys]
        label = "새로 생긴 넘침"
    else:
        label = "넘치는 셀(원본 고유 포함)"

    print(f"\n[{label}] {len(over)}건")
    for k, ln, need, H, t in over:
        print(f"  tbl{k[0]}({k[1]},{k[2]}) {ln}줄 필요h={need} > 셀h={H}  {t!r}")
    print(f"[비검정 텍스트] {len(colored)}건")
    for k, c, t in colored:
        print(f"  tbl{k[0]}({k[1]},{k[2]}) {c}  {t!r}")
    if show_all:
        print("\n(--all: 전수 출력은 scan() 직접 호출)")
    return 1 if over else 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(2)
    base = None
    if "--baseline" in sys.argv:
        i = sys.argv.index("--baseline")
        base = sys.argv[i + 1] if len(sys.argv) > i + 1 else None
        args = [a for a in args if a != base]
    sys.exit(check(args[0], base, "--all" in sys.argv))
