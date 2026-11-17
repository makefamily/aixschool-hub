"""
긴 상세페이지 PNG -> 업로드용 조각 이미지로 분할.

사용:
  python slice_detail.py <full.png> <outdir> [--width 800] [--chunk 1000] [--q 88] [--b64]

왜 자르나:
  * 카페24 등 에디터/브라우저가 세로 1만px 넘는 단일 이미지를 버거워한다.
  * 조각당 용량이 작아 모바일 로딩이 빠르다.

똑똑한 절단:
  목표 높이 ±140px 안에서 '가로 한 줄이 단색인 지점'(섹션 사이 여백)을 찾아 자른다.
  글자·카드 중간이 잘리는 사고를 막는다.
"""
import os
import sys
from PIL import Image


def uniform_row(px, W, y):
    c = px[0, y]
    for x in range(0, W, 5):
        if px[x, y] != c:
            return False
    return True


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        raise SystemExit(__doc__)
    src, outdir = a[0], a[1]
    width = int(a[a.index("--width") + 1]) if "--width" in a else 800
    chunk = int(a[a.index("--chunk") + 1]) if "--chunk" in a else 1000
    q = int(a[a.index("--q") + 1]) if "--q" in a else 88
    os.makedirs(outdir, exist_ok=True)

    im = Image.open(src).convert("RGB")
    if im.width != width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    W, H = im.size
    px = im.load()

    cuts, y = [0], 0
    while H - y > chunk * 1.35:
        target = y + chunk
        best = None
        for d in range(0, 141):
            for cand in (target - d, target + d):
                if y + 200 < cand < H - 200 and uniform_row(px, W, cand):
                    best = cand
                    break
            if best:
                break
        if not best:
            print(f"[warn] y={target} 근처에 여백 줄이 없어 그대로 자름. 글자가 잘렸는지 눈으로 확인할 것")
        y = best or target
        cuts.append(y)
    cuts.append(H)

    for i in range(len(cuts) - 1):
        part = im.crop((0, cuts[i], W, cuts[i + 1]))
        p = os.path.join(outdir, f"s{i}.jpg")
        part.save(p, quality=q, subsampling=0, optimize=True)
        print(f"s{i}.jpg  {part.width}x{part.height}  {os.path.getsize(p)//1024}KB")
        if "--b64" in a:
            import base64
            with open(p, "rb") as f:
                with open(os.path.join(outdir, f"s{i}.b64"), "w") as g:
                    g.write(base64.b64encode(f.read()).decode())
    print(f"총 {len(cuts)-1}조각 -> {outdir}")


if __name__ == "__main__":
    main()
