#!/usr/bin/env python3
"""한국어 단어 단위 정밀 전사: MLX Whisper(전사) → WhisperX wav2vec2 정렬 → 오디오 에너지 경계 스냅.

2026-09-27 실측(100초 한국어 강의): 무음 덮음 2%, 경계 오차 median 0ms / p90 336ms, 100ms 이내 78%, 23초.
(whisper.cpp 98% / 339ms / 20%, WhisperX 단독 30% / 109ms / 46%)

실행 환경: whisperx, mlx_whisper 가 설치된 python (setup_asr.sh 로 생성하거나 이미 설치된 python 사용. 없으면 사용자에게 설치가 필요하다고 알린다)
사용법:
  <Whisper가 설치된 python> transcribe_words.py <영상|오디오> <출력접두사> [--lang ko] [--snap-ms 250]
출력: <접두사>.words.json  [{w, s, e}]  / <접두사>.srt(문장 단위) / <접두사>.silences.json
"""
import argparse, json, re, subprocess, sys, tempfile, os, time

p = argparse.ArgumentParser()
p.add_argument("src"); p.add_argument("out")
p.add_argument("--lang", default="ko")
p.add_argument("--model", default="mlx-community/whisper-large-v3-turbo")
p.add_argument("--snap-ms", type=int, default=250, help="단어 경계를 이 범위 안의 무음 경계로 스냅")
p.add_argument("--noise-db", type=int, default=-40)
a = p.parse_args()

t0 = time.time()
tmp = tempfile.mkdtemp(prefix="asr_")
wav = os.path.join(tmp, "a.wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.src, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav], check=True)

# 1) 전사 (MLX, 빠름). 도메인 프롬프트는 쓰지 않는다(조용한 구간 반복 환각 실측).
import mlx_whisper
r = mlx_whisper.transcribe(wav, path_or_hf_repo=a.model, language=a.lang, condition_on_previous_text=False)
segs = [{"start": s["start"], "end": s["end"], "text": s["text"]} for s in r["segments"]]
t1 = time.time()

# 반복 환각 스캔: 같은 문장 4회 이상 연속
rep, run = [], 1
for i in range(1, len(segs)):
    run = run + 1 if segs[i]["text"].strip() == segs[i - 1]["text"].strip() else 1
    if run == 4: rep.append(segs[i]["start"])
if rep: print(f"경고: 반복 환각 의심 {len(rep)}곳 {rep[:5]}", file=sys.stderr)

# 2) 강제 정렬 (WhisperX wav2vec2)
import whisperx
audio = whisperx.load_audio(wav)
am, meta = whisperx.load_align_model(language_code=a.lang, device="cpu")
al = whisperx.align(segs, am, meta, audio, "cpu", return_char_alignments=False)
words = [{"w": x["word"], "s": float(x["start"]), "e": float(x["end"])}
         for s in al["segments"] for x in s.get("words", []) if "start" in x and "end" in x]
t2 = time.time()

# 3) 오디오 에너지 경계 스냅
log = subprocess.run(["ffmpeg", "-nostats", "-i", wav, "-af", f"silencedetect=noise={a.noise_db}dB:d=0.15", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
S = [(float(x), float(y)) for x, y in zip(re.findall(r"silence_start: ([\d.]+)", log), re.findall(r"silence_end: ([\d.]+)", log))]
r_ = a.snap_ms / 1000
snapped = 0
for w in words:
    c = [s for s, e in S if abs(s - w["e"]) <= r_]
    if c: w["e"] = min(c, key=lambda v: abs(v - w["e"])); snapped += 1
    c = [e for s, e in S if abs(e - w["s"]) <= r_]
    if c: w["s"] = min(c, key=lambda v: abs(v - w["s"])); snapped += 1
    if w["e"] <= w["s"]: w["e"] = w["s"] + 0.02

json.dump(words, open(a.out + ".words.json", "w"), ensure_ascii=False, indent=0)
json.dump([{"start": s, "end": e, "dur": round(e - s, 3)} for s, e in S], open(a.out + ".silences.json", "w"), indent=0)

def ts(x):
    h, m = int(x // 3600), int(x % 3600 // 60); s = x % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")
with open(a.out + ".srt", "w") as f:
    for i, s in enumerate(al["segments"], 1):
        f.write(f"{i}\n{ts(s['start'])} --> {ts(s['end'])}\n{s['text'].strip()}\n\n")

print(f"단어 {len(words)}개, 스냅 {snapped}회 | 전사 {t1-t0:.1f}s 정렬 {t2-t1:.1f}s 총 {time.time()-t0:.1f}s → {a.out}.words.json")
