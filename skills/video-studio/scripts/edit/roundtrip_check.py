#!/usr/bin/env python3
"""완성본을 다시 전사해 EDL이 의도한 대사와 비교한다. 잘린 단어·빠진 문장을 자동으로 잡는다.
실행: <Whisper가 설치된 python> roundtrip_check.py <final.mp4> <edl.json> [--lang ko]
판정: 의도 대비 글자 일치율(공백·문장부호 무시) >= 0.95 이고 누락 어절이 없으면 PASS.
"""
import json, re, sys, argparse, difflib
p = argparse.ArgumentParser(); p.add_argument("video"); p.add_argument("edl"); p.add_argument("--lang", default="ko")
a = p.parse_args()
import mlx_whisper
got = mlx_whisper.transcribe(a.video, path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language=a.lang,
                             condition_on_previous_text=False)["text"]
want = " ".join(s.get("text", "") for s in json.load(open(a.edl))["segments"])
norm = lambda t: re.sub(r"[\s\.\,\?\!\"'…·~\-]", "", t)
ratio = difflib.SequenceMatcher(None, norm(want), norm(got)).ratio()
gw = norm(got)
missing = [w for w in want.split() if norm(w) and norm(w) not in gw]
print("의도:", want.strip()); print("실제:", got.strip())
print(f"일치율 {ratio:.3f} | 누락 어절 {len(missing)}개 {missing[:10]}")
ok = ratio >= 0.95 and not missing
print("roundtrip", "PASS" if ok else "FAIL (잘린 단어 또는 전사 차이 — 해당 편집점 파형 확인)")
sys.exit(0 if ok else 1)
