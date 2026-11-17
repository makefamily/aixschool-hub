# -*- coding: utf-8 -*-
"""완성 덱 대표 9장 → media/deck-overview.png (3x3). 입력: qa/shoot.mjs 로 찍은 장별 PNG 폴더"""
import sys, pathlib
from PIL import Image
src = pathlib.Path(sys.argv[1]); out = pathlib.Path(__file__).resolve().parent.parent / "media/deck-overview.png"
fs = sorted(src.glob("*.png"))[:9]
W, H, G = 960, 540, 28
sheet = Image.new("RGB", (W * 3 + G * 4, H * 3 + G * 4), (231, 225, 211))
for i, f in enumerate(fs):
    sheet.paste(Image.open(f).convert("RGB").resize((W, H), Image.LANCZOS), (G + (i % 3) * (W + G), G + (i // 3) * (H + G)))
sheet.save(out, optimize=True)
print(out, sheet.size, [f.name for f in fs])
