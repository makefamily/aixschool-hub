# -*- coding: utf-8 -*-
"""완성된 카드 PNG를 한눈에 보는 모아보기 이미지 한 장과 ZIP 한 개로 묶는다. 표준 라이브러리와 설치된 Chrome/Edge만 쓴다."""
import html
import pathlib
import sys
import zipfile

# 임시 폴더를 작업 폴더 안으로(AI 보호 구역에서 시스템 임시 폴더 쓰기가 막히는 경우 대비) AIHUB_LOCAL_TMP
import os as _os, tempfile as _tf
_loc = _os.path.join(_os.getcwd(), '.tmp'); _os.makedirs(_loc, exist_ok=True)
_tf.tempdir = _loc; _os.environ['TMP'] = _os.environ['TEMP'] = _os.environ['TMPDIR'] = _loc

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from make_cards import find_browser, run_browser, png_size  # noqa: E402

CELL_W, CELL_H, GAP, PAD, HEAD = 432, 540, 8, 32, 96
PER_ROW = 5


def contact_sheet(png_dir, out_png, title, work_html_dir):
    """카드 PNG 전부를 5열 격자로 놓은 1장짜리 이미지를 만든다. 성공하면 경로, 실패하면 None."""
    pngs = sorted(pathlib.Path(png_dir).glob("[0-9][0-9].png"))
    if not pngs:
        return None
    browser = find_browser()
    if not browser:
        return None
    rows = (len(pngs) + PER_ROW - 1) // PER_ROW
    cols = min(PER_ROW, len(pngs))
    width = PAD * 2 + cols * CELL_W + (cols - 1) * GAP
    height = HEAD + PAD + rows * CELL_H + (rows - 1) * GAP
    work = pathlib.Path(work_html_dir)
    work.mkdir(parents=True, exist_ok=True)
    page = work / "contact.html"
    import os
    cells = "".join('<div class="c"><img src="%s"><i>%s</i></div>' % (
        os.path.relpath(p, work).replace(os.sep, "/"), p.stem) for p in pngs)
    page.write_text(
        '<!doctype html><meta charset="utf-8"><style>'
        '*{margin:0;box-sizing:border-box}body{width:%dpx;height:%dpx;background:#16171b;color:#f1f1f3;'
        'font-family:"Pretendard","Apple SD Gothic Neo","Malgun Gothic",sans-serif;padding:%dpx;overflow:hidden}'
        'h1{font-size:34px;height:%dpx;line-height:%dpx;font-weight:800}'
        '.g{display:grid;grid-template-columns:repeat(%d,%dpx);gap:%dpx}'
        '.c{position:relative;width:%dpx;height:%dpx;border-radius:8px;overflow:hidden;background:#000}'
        '.c img{width:100%%;height:100%%;object-fit:cover;display:block}'
        '.c i{position:absolute;left:8px;top:8px;background:#000a;color:#fff;font:700 18px/1 sans-serif;font-style:normal;padding:5px 9px;border-radius:6px}'
        '</style><body><h1>%s</h1><div class="g">%s</div></body>' % (
            width, height, PAD, HEAD - PAD, HEAD - PAD, cols, CELL_W, GAP, CELL_W, CELL_H,
            html.escape(title or "카드뉴스") + " / %d장" % len(pngs), cells), encoding="utf-8")
    out = pathlib.Path(out_png)
    if out.exists():
        out.unlink()
    run_browser(browser, ["--window-size=%d,%d" % (width, height), "--virtual-time-budget=3000",
                          "--screenshot=" + str(out.resolve()), page.resolve().as_uri()])
    if out.exists() and out.stat().st_size > 0:
        return out
    return None


def make_zip(png_dir, out_zip, extra=()):
    pngs = sorted(pathlib.Path(png_dir).glob("[0-9][0-9].png"))
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in pngs:
            zf.write(p, "카드뉴스/" + p.name)
        for e in extra:
            e = pathlib.Path(e)
            if e.is_file():
                zf.write(e, "카드뉴스/" + e.name)
    return pathlib.Path(out_zip), len(pngs)


def pack(work_dir, png_dir, title):
    work = pathlib.Path(work_dir)
    sheet = contact_sheet(png_dir, work / "모아보기.png", title, pathlib.Path(png_dir) / "src")
    z, n = make_zip(png_dir, work / "카드뉴스.zip", extra=[work / "caption.txt"])
    sz = png_size(sheet) if sheet else None
    print("모아보기: %s" % (("%s (%dx%d)" % (sheet.name, sz[0], sz[1])) if sheet and sz else "만들지 못함"))
    print("ZIP: %s (카드 %d장)" % (z.name, n))
    return sheet, z


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--cards", default="cards")
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    d = pathlib.Path(a.dir).resolve()
    pack(d, d / a.cards, a.title)
