#!/usr/bin/env python3
"""단어 전사(transcribe_words.py 출력)를 에이전트가 읽기 쉬운 문구 단위로 묶는다(video-use의 takes_packed 방식).
무음 >= --gap 초 또는 문장부호에서 끊는다. 각 줄: [시작–끝] (단어번호 범위) 텍스트 | 앞 공백
사용법: pack_transcript.py <words.json> [--gap 0.5] > packed.md
"""
import json, sys, argparse
p = argparse.ArgumentParser(); p.add_argument("words"); p.add_argument("--gap", type=float, default=0.5)
a = p.parse_args()
W = json.load(open(a.words))
print(f"# packed transcript ({len(W)} words, split at gaps >= {a.gap}s)\n")
start = 0
for i in range(len(W)):
    last = i == len(W) - 1
    gap = None if last else W[i + 1]["s"] - W[i]["e"]
    if last or gap >= a.gap or W[i]["w"].rstrip().endswith((".", "?", "!", "다.", "요.")):
        seg = W[start:i + 1]
        pre = W[start]["s"] - W[start - 1]["e"] if start > 0 else W[start]["s"]
        print(f"[{seg[0]['s']:07.2f}–{seg[-1]['e']:07.2f}] (w{start}–w{i}) {' '.join(x['w'] for x in seg)}  | gap_before {pre:.2f}s")
        start = i + 1
