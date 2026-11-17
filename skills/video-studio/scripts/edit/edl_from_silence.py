#!/usr/bin/env python3
"""무음 목록으로 '말 구간 유지' 초안 EDL을 만든다. 판단 초안일 뿐이며 approved=false로 저장한다.
사용법: edl_from_silence.py <원본> <silences.json> <out_edl.json> [--words words.json] [--min-cut 0.6] [--handle-ms 120] [--fps 25/1]
--words: transcribe_words.py 결과(권장) 또는 whisper-cli -ojf 결과. 컷 구간이 단어 안을 침범하면 단어 경계 밖으로 밀어낸다(단어 안에서 자르지 않기).
"""
import json, sys, argparse, subprocess
from fractions import Fraction
p = argparse.ArgumentParser()
p.add_argument("src"); p.add_argument("silences"); p.add_argument("out")
p.add_argument("--min-cut", type=float, default=0.6, help="이보다 짧은 무음은 남긴다(호흡·강조)")
p.add_argument("--handle-ms", type=int, default=120, help="말 앞뒤로 남길 여유")
p.add_argument("--fps", default=None)
p.add_argument("--words", default=None)
a = p.parse_args()
probe = json.loads(subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries",
    "stream=r_frame_rate:format=duration","-of","json",a.src],capture_output=True,text=True,check=True).stdout)
fps = Fraction(a.fps or probe["streams"][0]["r_frame_rate"]); dur = float(probe["format"]["duration"])
h = a.handle_ms/1000
cuts = [(s["start"]+h, s["end"]-h) for s in json.load(open(a.silences)) if s["dur"] >= a.min_cut + 2*h]
snapped = 0
if a.words:
    raw = json.load(open(a.words))
    if isinstance(raw, list):   # transcribe_words.py 형식 [{w,s,e}] (정렬 전사, 권장)
        w = [(x["s"], x["e"]) for x in raw if x["w"].strip()]
    else:                        # whisper-cli -ojf 형식 (단어 끝이 무음을 덮어 대개 스냅 생략됨)
        w = [(x["offsets"]["from"]/1000, x["offsets"]["to"]/1000) for x in raw["transcription"] if x["text"].strip()]
    sil = json.load(open(a.silences)); sil_total = sum(x["dur"] for x in sil) or 1
    smear = sum(max(0, min(we, x["end"]) - max(ws, x["start"])) for x in sil for ws, we in w) / sil_total
    if smear > 0.5:
        # whisper.cpp 등은 단어 끝을 다음 멈춤까지 늘려 잡는다(실측 97%). 이런 전사로는 경계 스냅 불가 → 오디오 에너지 경계 유지
        print(f"경고: 단어 타임스탬프가 무음의 {smear:.0%}를 덮음 → 스냅 생략, 무음 경계+핸들 사용. 정밀 스냅은 WhisperX/Scribe 정렬 전사 필요", file=sys.stderr)
    else:
        fixed = []
        for cs, ce in cuts:
            for ws, we in w:
                if ws < cs < we: cs = we; snapped += 1      # 컷 시작이 단어 안 → 단어 끝으로
                if ws < ce < we: ce = ws; snapped += 1      # 컷 끝이 단어 안 → 단어 시작으로
            if ce - cs >= a.min_cut: fixed.append((cs, ce))
        cuts = fixed
keep, t = [], 0.0
for cs, ce in cuts:
    if cs > t: keep.append((t, cs))
    t = ce
if t < dur: keep.append((t, dur))
f = lambda sec: int(round(sec*fps))
segs = [{"id": f"s{i+1:03d}", "source": a.src, "in_frame": f(s), "out_frame": f(e),
         "reason": "무음 사이 발화 구간", "confidence": 0.7, "review": False, "audio_fade_ms": 30}
        for i,(s,e) in enumerate(keep) if f(e)-f(s) >= 3]
total = sum(s["out_frame"]-s["in_frame"] for s in segs)/fps
edl = {"version":1,"fps":f"{fps.numerator}/{fps.denominator}","source_duration_s":round(dur,3),
       "computed_s":round(float(total),3),"segments":segs,"approved":False}
json.dump(edl, open(a.out,"w"), ensure_ascii=False, indent=1)
print(f"단어 경계 보정 {snapped}회, 세그먼트 {len(segs)}개, {dur:.1f}s → {float(total):.1f}s (제거 {dur-float(total):.1f}s)")
