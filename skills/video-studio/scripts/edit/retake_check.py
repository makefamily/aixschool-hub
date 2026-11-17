#!/usr/bin/env python3
"""다시 말한 곳·반복·고쳐 말함 검사. 컷 전(원본)과 QA(완성본) 둘 다 쓴다.

왜 필요한가: 긴 구간을 한 번에 받아쓰면 Whisper가 "수준에, 답하는 수준을"을 "수준을" 한 단어로
뭉개서 반복이 전사에서 사라진다(2026-11-09 코워크 릴스 v006 실측). 그래서 짧은 창으로 겹쳐 자르고,
창마다 앞 문맥 없이 따로 받아써서 반복을 찾는다.

판정
  확정 = 겹치는 창 2개 이상에서 같은 반복이 나옴 → QA FAIL (컷 전이면 지울 후보)
  의심 = 창 1개에서만 나옴, 또는 고쳐 말함 모양(꾸밈말 두 개 연속 등) → WARN, 사람이 들어볼 곳

사용법 (Whisper가 설치된 python 으로 실행)
  $PY retake_check.py <영상|음성> [--out 보고서.json] [--win 4.0] [--step 0.5]
                      [--allow 띄우고,진짜] [--from 0] [--to 0]
  종료 코드: 확정 0건이면 0, 1건 이상이면 1, 실행 오류 2
"""
import argparse, json, re, subprocess, sys, tempfile, os
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("media")
ap.add_argument("--out")
ap.add_argument("--win", type=float, default=4.0, help="창 길이(초). 2.6초는 너무 짧아 문맥 부족으로 놓치고, 길면 반복을 뭉갠다(4초 실측 최적)")
ap.add_argument("--step", type=float, default=0.5, help="창 간격(초). 1.0이면 반복이 창 1개에만 잡혀 확정이 안 됨(v006 실측). 0.5면 한 지점이 창 8개에 들어간다")
ap.add_argument("--allow", default="", help="강조 반복으로 허용할 낱말(쉼표 구분)")
ap.add_argument("--from", dest="t0", type=float, default=0.0)
ap.add_argument("--to", dest="t1", type=float, default=0.0)
ap.add_argument("--model", default="mlx-community/whisper-large-v3-turbo")
ap.add_argument("--noise", type=float, default=-35, help="멈춤 판정 음량(dB). 배경음이 깔린 완성본은 조각 검사가 약하고 창 검사가 주력")
ap.add_argument("--pause", type=float, default=0.25, help="이보다 긴 멈춤에서 조각을 나눈다(초)")
a = ap.parse_args()

try:
    import mlx_whisper
except ImportError:
    print("mlx_whisper 없음: Whisper가 설치된 python 으로 실행(없으면 설치가 필요하다고 사용자에게 알린다)", file=sys.stderr); sys.exit(2)

SR = 16000
with tempfile.TemporaryDirectory() as td:
    wav = os.path.join(td, "a.raw")
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if a.t0: cmd += ["-ss", str(a.t0)]
    if a.t1: cmd += ["-to", str(a.t1)]
    cmd += ["-i", a.media, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", wav]
    if subprocess.run(cmd).returncode != 0:
        print("오디오 추출 실패", file=sys.stderr); sys.exit(2)
    audio = np.fromfile(wav, dtype=np.float32)

dur = len(audio) / SR
allow = {x.strip() for x in a.allow.split(",") if x.strip()}
HALLU = re.compile(r"구독|좋아요|시청해|다음 영상|자막|MBC|KBS")

def norm(t):
    return re.sub(r"[^\w]", "", t)

def is_adnominal(t):
    # 꾸밈말 끝 ~는/~은/~던만 본다. 받침 ㄴ 전체(만·면·한)로 넓히면 오탐이 쏟아진다(v006 실측 9건 중 8건 오탐)
    return len(t) >= 2 and t[-1] in "는은던"

def jamo(t):
    out = []
    for ch in t:
        c = ord(ch) - 0xAC00
        if 0 <= c < 11172:
            out += [chr(0x1100 + c // 588), chr(0x1161 + (c % 588) // 28)] + ([chr(0x11A7 + c % 28)] if c % 28 else [])
        else:
            out.append(ch)
    return out

def sound_like(x, y):
    # 조각 첫 낱말은 자주 잘못 들린다("답하는"→"타파늘"). 자모 유사도 0.5 이상이면 같은 말로 본다
    import difflib
    return x == y or difflib.SequenceMatcher(None, jamo(x), jamo(y)).ratio() >= 0.5

def stem_eq(x, y):
    # 같은 말에 조사·어미만 다른 경우: 수준에/수준을/수준으로 → 앞 2글자 이상, 짧은 쪽의 절반 이상 일치
    if x == y: return True
    k = 0
    while k < min(len(x), len(y)) and x[k] == y[k]: k += 1
    return k >= 2 and k * 2 >= min(len(x), len(y))

hits = {}  # key -> {kind, text, times:[...], windows}
def add(kind, text, t, wi):
    key = (kind, text, round(t / 1.0))  # 1초 단위로 같은 지점 묶기
    h = hits.setdefault(key, {"kind": kind, "text": text, "t": [], "win": set()})
    h["t"].append(t); h["win"].add(wi)

def words_of(s, e):
    seg = audio[int(s * SR):int(e * SR)]
    if len(seg) < SR * 0.3 or float(np.abs(seg).max()) < 0.01:
        return []
    r = mlx_whisper.transcribe(seg, path_or_hf_repo=a.model, language="ko",
                               condition_on_previous_text=False, word_timestamps=True,
                               no_speech_threshold=0.6, verbose=None)
    W = []
    for sg in r.get("segments", []):
        if HALLU.search(sg.get("text", "")): continue
        for w in sg.get("words", []):
            n = norm(w["word"])
            if n: W.append((n, s + float(w["start"]) + a.t0, w["word"].strip()))
    return W

# ── 검사 A. 멈춤으로 나눈 조각 비교 (원본 단계의 핵심) ──
# 두 테이크 사이 멈춤이 0.5초뿐이면 4초 창 안에서도 Whisper가 한 번으로 합친다(원본 실측).
# 멈춤에서 조각을 나눠 따로 받아쓰고, 앞 조각 끝 = 뒤 조각 시작이면 앞 테이크를 지울 후보로 본다.
def pauses():
    p = subprocess.run(["ffmpeg", "-hide_banner", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                        "-af", f"silencedetect=noise={a.noise}dB:d={a.pause}", "-f", "null", "-"],
                       input=audio.tobytes(), capture_output=True)
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", p.stderr.decode())]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", p.stderr.decode())]
    return list(zip(st, en))

frag_hits = []
P = pauses()
bounds = [0.0] + [(s + e) / 2 for s, e in P] + [dur]
frags = []
for i in range(len(bounds) - 1):
    s, e = bounds[i], bounds[i + 1]
    while e - s > 15:  # 너무 긴 조각은 15초씩
        frags.append((s, s + 15)); s += 15
    if e - s >= 0.3: frags.append((s, e))
FW = [words_of(s, e) for s, e in frags]
for i in range(len(FW) - 1):
    A, B = FW[i], FW[i + 1]
    if not A or not B: continue
    ta, tb = [x[0] for x in A], [x[0] for x in B]
    best = 0
    for k in range(1, min(4, len(ta), len(tb)) + 1):
        tail, head = ta[-k:], tb[:k]
        if k == 1 and len(tail[0]) < 2: continue
        if k == 1:
            ok = tail[0] == head[0]
        else:  # 마지막 낱말은 글자로(조사만 다를 수 있음), 앞 낱말은 소리 유사도로
            ok = len(tail[-1]) >= 2 and stem_eq(tail[-1], head[-1]) and all(sound_like(x, y) for x, y in zip(tail[:-1], head[:-1]))
        if ok:
            best = k
    # 앞 조각 전체가 뒤 조각 앞부분과 같으면(통째로 다시 말함)도 포함
    if best and not (set(ta[-best:]) & allow):
        cut_from = A[-best][1]
        frag_hits.append({"level": "확정", "kind": "다시 말함(조각)", "t": round(cut_from, 2),
                          "text": f"{' '.join(x[2] for x in A[-best:])} / {' '.join(x[2] for x in B[:best])}",
                          "windows": 0, "cut": [round(cut_from, 2), round(B[0][1], 2)]})

# ── 검사 B. 겹치는 짧은 창 (완성본 QA의 핵심) ──
starts = np.arange(0, max(dur - 0.3, 0.01), a.step)
for wi, s in enumerate(starts):
    W = words_of(s, min(s + a.win, dur))
    toks = [x[0] for x in W]
    # 1) 바로 이어진 같은 덩어리 반복(1~4어절): "수행하는 수행하는", "답하는 수준에 답하는 수준을"
    for n in range(1, 5):
        for i in range(len(toks) - 2 * n + 1):
            A, B = toks[i:i + n], toks[i + n:i + 2 * n]
            if max(len(x) for x in A) < 2 or all(x.isdigit() for x in A): continue  # "2 2 2 2"·"너 너" 같은 배경음 착각 제외
            # 마지막 어절은 조사·어미만 달라도 같은 것으로 본다(수준에/수준을)
            same = A[:-1] == B[:-1] and stem_eq(A[-1], B[-1])
            if n >= 2 and A[0] != B[0]: same = False
            if same and not (set(A) & allow):
                add("반복", " ".join(x[2] for x in W[i:i + 2 * n]), W[i][1], wi)
    # 2) 끊긴 낱말 뒤 온전한 낱말: "안전장, 안전장치"
    for i in range(len(toks) - 1):
        x, y = toks[i], toks[i + 1]
        if 2 <= len(x) < len(y) and y.startswith(x) and x not in allow:
            add("끊고 다시", f"{W[i][2]} {W[i+1][2]}", W[i][1], wi)
    # 3) 고쳐 말함 모양: 꾸밈말 두 개 연속("부르는 뽑은") — 문법상 가능해서 의심으로만
    for i in range(len(toks) - 1):
        if toks[i] != toks[i + 1] and is_adnominal(toks[i]) and is_adnominal(toks[i + 1]):
            add("고쳐 말함?", f"{W[i][2]} {W[i+1][2]}", W[i][1], wi)

out = []
for h in hits.values():
    n = len(h["win"])
    level = "확정" if (n >= 2 and h["kind"] != "고쳐 말함?") else "의심"
    out.append({"level": level, "kind": h["kind"], "t": round(float(np.median(h["t"])), 2),
                "text": h["text"], "windows": n})
out += frag_hits
# 같은 지점(±0.8초)의 반복 계열은 가장 강한 것 하나만 남긴다(조각 검사 결과 우선 — 지울 구간을 알려 줌)
out.sort(key=lambda x: (x["t"], -x["windows"]))
merged = []
for x in out:
    if merged and abs(merged[-1]["t"] - x["t"]) < 0.8 and merged[-1]["kind"] != "고쳐 말함?" and x["kind"] != "고쳐 말함?":
        if "cut" in x or ("cut" not in merged[-1] and x["windows"] > merged[-1]["windows"]): merged[-1] = x
        continue
    merged.append(x)

conf = [x for x in merged if x["level"] == "확정"]
sus = [x for x in merged if x["level"] == "의심"]
def mmss(t): return f"{int(t//60)}:{t%60:05.2f}"
print(f"retake_check  {a.media}  길이 {dur:.1f}s  조각 {len(frags)}개  창 {a.win}s/{a.step}s  창 수 {len(starts)}")
for x in conf:
    extra = f"  → 지울 후보 {x['cut'][0]}~{x['cut'][1]}초(앞 테이크)" if "cut" in x else f"  (창 {x['windows']}개)"
    print(f"  확정 FAIL  {mmss(x['t'])}  [{x['kind']}] {x['text']}{extra}")
for x in sus:  print(f"  의심 WARN  {mmss(x['t'])}  [{x['kind']}] {x['text']}  (창 {x['windows']}개) — 들어볼 것")
print(f"확정={len(conf)} 의심={len(sus)}")
if a.out:
    json.dump({"media": a.media, "duration": dur, "confirmed": conf, "suspect": sus}, open(a.out, "w"), ensure_ascii=False, indent=1)
sys.exit(1 if conf else 0)
