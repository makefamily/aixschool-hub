#!/usr/bin/env python3
"""에이전트가 고른 '살릴 단어 범위'를 프레임 정확 EDL로 바꾼다. 단어 안에서 자르지 않고, 앞뒤 여유(pad)를 두되 이웃 단어를 침범하지 않는다.
keep 파일(JSON): [{"words":"w0-w11","reason":"...","beat":"HOOK"}, ...]  (순서대로 이어 붙임, 순서 바꾸기 허용)
사용법: edl_from_keep.py <원본> <words.json> <keep.json> <out_edl.json> [--pad-ms 120] [--pad-end-ms 250]
"""
import json, argparse, subprocess
from fractions import Fraction
p = argparse.ArgumentParser(); p.add_argument("src"); p.add_argument("words"); p.add_argument("keep"); p.add_argument("out")
p.add_argument("--pad-ms", type=int, default=120, help="단어 앞 여유")
p.add_argument("--pad-end-ms", type=int, default=250, help="단어 뒤 여유. 한국어 어미(-니다/-요)는 끝이 길게 흐려져 앞보다 길게"); p.add_argument("--fade-ms", type=int, default=30)
p.add_argument("--silences", default=None, help="transcribe_words.py의 .silences.json (기본: words 경로에서 자동)")
a = p.parse_args()
W = json.load(open(a.words)); K = json.load(open(a.keep))
pr = json.loads(subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=r_frame_rate:format=duration","-of","json",a.src],capture_output=True,text=True,check=True).stdout)
fps = Fraction(pr["streams"][0]["r_frame_rate"]); dur = float(pr["format"]["duration"]); pad = a.pad_ms/1000; pad_e = a.pad_end_ms/1000
import os
sp = a.silences or a.words.replace(".words.json", ".silences.json")
SIL = json.load(open(sp)) if os.path.exists(sp) else []
def audio_end(t, limit):   # 단어 끝 이후 첫 무음 시작 = 소리가 실제로 끝난 곳 (정렬기가 숫자·기호 단어를 짧게 잡는 문제 보정)
    c = [x["start"] for x in SIL if x["start"] >= t - 0.05 and x["start"] <= limit]
    return min(c) if c else t
def audio_start(t, limit): # 단어 시작 이전 마지막 무음 끝 = 소리가 실제로 시작된 곳
    c = [x["end"] for x in SIL if x["end"] <= t + 0.05 and x["end"] >= limit]
    return max(c) if c else t
segs = []
for n, k in enumerate(K, 1):
    i, j = [int(x.strip().lstrip("w")) for x in k["words"].split("-")]
    nxt = W[j+1]["s"] if j < len(W) - 1 else dur
    prv = W[i-1]["e"] if i > 0 else 0.0
    s = audio_start(W[i]["s"], prv) - pad
    e = audio_end(W[j]["e"], nxt) + pad_e
    if i > 0: s = max(s, (W[i-1]["e"] + W[i]["s"]) / 2)          # 이전 단어 침범 금지(간격 중앙까지만)
    if j < len(W) - 1: e = min(e, (W[j]["e"] + W[j+1]["s"]) / 2)  # 다음 단어 침범 금지
    s = max(0.0, s); e = min(dur, e)
    fi, fo = int(s * fps), int(-(-e * fps // 1))                 # in은 내림, out은 올림(단어 보존)
    segs.append({"id": f"s{n:03d}", "source": a.src, "in_frame": fi, "out_frame": fo,
                 "text": " ".join(x["w"] for x in W[i:j+1]), "reason": k.get("reason",""), "beat": k.get("beat",""),
                 "review": False, "audio_fade_ms": a.fade_ms})
comp = sum(x["out_frame"] - x["in_frame"] for x in segs) / fps
json.dump({"version":1,"fps":f"{fps.numerator}/{fps.denominator}","computed_s":round(float(comp),3),"segments":segs,"approved":False},
          open(a.out,"w"), ensure_ascii=False, indent=1)
print(f"세그먼트 {len(segs)}개, 계산 길이 {float(comp):.2f}s → {a.out}")
