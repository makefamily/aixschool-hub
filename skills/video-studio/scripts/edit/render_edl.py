#!/usr/bin/env python3
"""EDL(JSON)을 프레임 정확하게 렌더한다. 세그먼트별 재인코딩 + 30ms 오디오 페이드 + concat.
사용법: render_edl.py <edl.json> <out.mp4> [--draft] [--cutlist cuts.txt]
--draft: 720p veryfast. --cutlist: 결과 타임라인 기준 편집점(초) 목록을 저장(cut_strips.sh 입력).
"""
import json, sys, subprocess, argparse, tempfile, os
from fractions import Fraction
p = argparse.ArgumentParser(); p.add_argument("edl"); p.add_argument("out")
p.add_argument("--draft", action="store_true"); p.add_argument("--cutlist")
a = p.parse_args()
edl = json.load(open(a.edl)); fps = Fraction(edl["fps"])
segs = edl["segments"]
# 검증: 역전·초단편·중첩
for s in segs:
    assert s["out_frame"] > s["in_frame"], f"역전 구간 {s['id']}"
    if s["out_frame"] - s["in_frame"] < 12: print(f"경고: 12프레임 미만 {s['id']}", file=sys.stderr)
work = tempfile.mkdtemp(prefix="edl_", dir=os.path.dirname(os.path.abspath(a.out)))
vf = "scale=-2:720," if a.draft else ""
preset, crf = ("veryfast","23") if a.draft else ("medium","18")
parts, t, cuts = [], Fraction(0), []
for i, s in enumerate(segs):
    ss = Fraction(s["in_frame"])/fps; d = Fraction(s["out_frame"]-s["in_frame"])/fps
    fade = s.get("audio_fade_ms",30)/1000
    out = os.path.join(work, f"{i:04d}.mp4")
    subprocess.run(["ffmpeg","-v","error","-y","-ss",f"{float(ss):.6f}","-i",s["source"],"-t",f"{float(d):.6f}",
        "-vf",f"{vf}fps={fps},format=yuv420p","-af",f"afade=t=in:d={fade},afade=t=out:st={max(0,float(d)-fade):.6f}:d={fade},aresample=48000",
        "-c:v","libx264","-preset",preset,"-crf",crf,"-c:a","aac","-b:a","192k","-ac","2",out], check=True)
    parts.append(out); t += d; cuts.append(float(t))
lst = os.path.join(work,"list.txt")
open(lst,"w").write("".join(f"file '{x}'\n" for x in parts))
subprocess.run(["ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",lst,"-c","copy","-movflags","+faststart",a.out],check=True)
if a.cutlist: open(a.cutlist,"w").write("\n".join(f"{c:.3f}" for c in cuts[:-1])+"\n")
real = float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",a.out],capture_output=True,text=True).stdout)
print(f"렌더 {a.out}: 예상 {float(t):.3f}s / 실측 {real:.3f}s / 세그먼트 {len(parts)}개 (중간파일 {work})")
