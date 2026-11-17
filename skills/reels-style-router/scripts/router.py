#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

TOOL_WORDS = {
    "ai", "챗gpt", "chatgpt", "클로드", "claude", "노션", "notion", "캡컷",
    "툴", "도구", "앱", "웹사이트", "대시보드", "자동화", "기능", "프롬프트", "클릭",
    "tool", "software", "dashboard", "prompt", "click", "website", "app ", "feature",
}
NUMBER_WORDS = {"매출", "조회수", "가격", "퍼센트", "%", "배", "명", "만원", "원", "초", "분"}
STORY_WORDS = {"처음", "그때", "결국", "경험", "생각", "이유", "문제", "사실", "예를", "왜", "때문"}
JACK_WORDS = {
    "content", "brand", "posting", "post ", "hook", "audience", "creator", "marketing",
    "result", "example", "story", "views", "followers", "sales", "viral",
}


def load_segments(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        raw = data
    elif isinstance(data, dict):
        raw = data.get("segments") or data.get("captions") or data.get("items") or []
    else:
        raw = []
    segs = []
    for i, s in enumerate(raw):
        if isinstance(s, str):
            segs.append({"start": float(i), "end": float(i + 1), "text": s})
            continue
        text = str(s.get("text") or s.get("dialogue") or s.get("caption") or "").strip()
        if not text:
            continue
        start = float(s.get("start", i))
        end = float(s.get("end", start + 1.5))
        segs.append({"start": start, "end": end, "text": text})
    return segs


def score_style(text: str):
    low = text.lower()
    tool = sum(low.count(w) for w in TOOL_WORDS)
    numbers = len(re.findall(r"\d+(?:[.,]\d+)?", low)) + sum(low.count(w) for w in NUMBER_WORDS)
    story = sum(low.count(w) for w in STORY_WORDS)
    jack = sum(low.count(w) for w in JACK_WORDS)
    scores = {"tool": tool, "numbers": numbers, "story": story, "jack": jack}
    # UI/도구 시연 가능성이 충분하면 숫자가 많아도 도구 설명형이 우선이다.
    if tool >= 4:
        return "tool-demo", scores
    # 마케팅 사례·결과·숫자·강한 주장 밀도가 높으면 Jack 문법이 더 잘 맞는다.
    if jack >= 3 or numbers >= 3:
        return "claim-numbers", scores
    return "info-visual", scores


def classify_scene(style: str, text: str):
    low = text.lower()
    has_num = bool(re.search(r"\d", low)) or any(w in low for w in NUMBER_WORDS)
    has_tool = any(w in low for w in TOOL_WORDS)
    if style == "tool-demo":
        if has_tool:
            return "ui"
        if has_num:
            return "result"
        return "talking_head"
    if style == "claim-numbers":
        if has_num:
            return "big_type"
        if any(w in low for w in ("예를", "사례", "실제로", "결과")):
            return "proof_overlay"
        if any(w in low for w in ("그때", "결국", "느낌", "상황")):
            return "broll_burst"
        return "talking_head"
    if has_num or any(w in low for w in ("자료", "결과", "증거", "출처")):
        return "evidence"
    if has_tool:
        return "ui"
    if any(w in low for w in ("예를", "장소", "제품", "사람", "방법")):
        return "broll"
    return "talking_head"


def build_plan(style, segs, scores):
    scenes = []
    for s in segs:
        scene_type = classify_scene(style, s["text"])
        scenes.append({
            "start": round(s["start"], 3),
            "end": round(s["end"], 3),
            "dialogue": s["text"],
            "scene_type": scene_type,
            "asset_query": s["text"] if scene_type not in {"talking_head", "big_type"} else "",
            "transition": "hard_cut",
        })
    return {"style": style, "router_scores": scores, "scenes": scenes}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--style", default="auto", choices=["auto", "info-visual", "claim-numbers", "tool-demo"])
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    segs = load_segments(Path(args.transcript))
    if not segs:
        raise SystemExit("no transcript segments found")
    joined = " ".join(s["text"] for s in segs)
    chosen, scores = score_style(joined)
    if args.style != "auto":
        chosen = args.style
    Path(args.output).write_text(json.dumps(build_plan(chosen, segs, scores), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"style": chosen, "scores": scores, "scenes": len(segs)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
