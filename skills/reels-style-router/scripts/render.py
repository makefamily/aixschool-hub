#!/usr/bin/env python3
import argparse
import sys
import importlib.util
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROUTER = HERE / "router.py"


def load_router():
    spec = importlib.util.spec_from_file_location("reels_style_router", ROUTER)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def probe(path: Path):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "stream=index,codec_type,codec_name,width,height,r_frame_rate:format=duration",
        "-of", "json", str(path),
    ]
    return json.loads(subprocess.check_output(cmd, text=True))


def ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def esc_ass(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")


def short_caption(text: str, max_chars: int = 18) -> str:
    text = " ".join(text.strip().split())
    if len(text) <= max_chars:
        return text
    words = text.split()
    if len(words) > 1:
        lines, cur = [], ""
        for w in words:
            nxt = (cur + " " + w).strip()
            if len(nxt) > max_chars and cur:
                lines.append(cur)
                cur = w
            else:
                cur = nxt
        if cur:
            lines.append(cur)
        return r"\N".join(lines[:2])
    cut = max_chars
    return text[:cut] + r"\N" + text[cut:cut * 2]


def build_ass(plan: dict, width: int, height: int, ass_path: Path):
    style = plan["style"]
    scale = width / 1080.0
    body_size = int((58 if style == "claim-numbers" else 52) * scale)
    title_size = int((90 if style == "info-visual" else 84) * scale)
    margin_v = int(250 * scale)
    # 글꼴: 맥은 Apple SD Gothic Neo, 윈도우는 맑은 고딕(Malgun Gothic). 학생이 Pretendard를 깔아 두었다면 그 이름으로 바꿔도 된다
    sans = "Malgun Gothic" if sys.platform.startswith("win") else "Apple SD Gothic Neo"
    if style == "info-visual":
        body_font, title_font = sans, sans
        primary, accent = "&H00FFFFFF", "&H0067C8FF"
    elif style == "tool-demo":
        body_font = title_font = sans
        primary, accent = "&H00FFFFFF", "&H0000D7FF"
    else:
        body_font = title_font = sans
        primary, accent = "&H00FFFFFF", "&H0000E6FF"

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Body,{body_font},{body_size},{primary},{primary},&H00151515,&H70000000,-1,0,0,0,100,100,0,0,1,{int(5*scale)},{int(2*scale)},2,{int(70*scale)},{int(70*scale)},{margin_v},1
Style: Accent,{body_font},{int(body_size*1.18)},{accent},{accent},&H00151515,&H70000000,-1,0,0,0,100,100,0,0,1,{int(5*scale)},{int(2*scale)},2,{int(70*scale)},{int(70*scale)},{margin_v},1
Style: Title,{title_font},{title_size},{primary},{primary},&H00151515,&H50000000,-1,0,0,0,100,100,0,0,1,{int(4*scale)},{int(2*scale)},8,{int(70*scale)},{int(70*scale)},{int(175*scale)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for i, scene in enumerate(plan["scenes"]):
        start, end = float(scene["start"]), float(scene["end"])
        text = short_caption(scene["dialogue"])
        scene_type = scene.get("scene_type", "talking_head")
        style_name = "Accent" if scene_type in {"big_type", "result"} else "Body"
        if i == 0 and style == "info-visual":
            style_name = "Title"
        lines.append(
            f"Dialogue: 0,{ass_time(start)},{ass_time(end)},{style_name},,0,0,0,,{esc_ass(text)}\n"
        )
    ass_path.write_text("".join(lines), encoding="utf-8")


def build_plan(transcript: Path, style: str, output_plan: Path):
    router = load_router()
    segs = router.load_segments(transcript)
    if not segs:
        raise SystemExit("no transcript segments found")
    joined = " ".join(s["text"] for s in segs)
    chosen, scores = router.score_style(joined)
    if style != "auto":
        chosen = style
    plan = router.build_plan(chosen, segs, scores)
    output_plan.parent.mkdir(parents=True, exist_ok=True)
    output_plan.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return plan


def render(input_path: Path, transcript: Path, style: str, output: Path, plan_path: Path, width: int, height: int):
    plan = build_plan(transcript, style, plan_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reels-style-render-") as tmp:
        tmp = Path(tmp)
        ass = tmp / "captions.ass"
        build_ass(plan, width, height, ass)
        ass_q = ass.as_posix().replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1,"
            f"subtitles='{ass_q}'"
        )
        cmd = [
            "ffmpeg", "-y", "-v", "error", "-i", str(input_path),
            "-map", "0:v:0", "-map", "0:a?", "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(output),
        ]
        subprocess.run(cmd, check=True)
    return plan


def main():
    ap = argparse.ArgumentParser(description="정보 시각화형 / 주장·숫자형 / 도구 설명형 마스터 릴스 렌더러")
    ap.add_argument("--input", default="input/raw.mp4")
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--style", default="auto", choices=["auto", "info-visual", "claim-numbers", "tool-demo"])
    ap.add_argument("--output", default="output/final.mp4")
    ap.add_argument("--plan", default="output/edit-plan.json")
    ap.add_argument("--width", type=int, default=2160)
    ap.add_argument("--height", type=int, default=3840)
    args = ap.parse_args()

    input_path = Path(args.input).resolve()
    transcript = Path(args.transcript).resolve()
    output = Path(args.output).resolve()
    plan_path = Path(args.plan).resolve()
    if not input_path.exists():
        raise SystemExit(f"input not found: {input_path}")
    if not transcript.exists():
        raise SystemExit(f"transcript not found: {transcript}")

    input_probe = probe(input_path)
    plan = render(input_path, transcript, args.style, output, plan_path, args.width, args.height)
    output_probe = probe(output)
    report = {
        "style": plan["style"],
        "input": str(input_path),
        "output": str(output),
        "plan": str(plan_path),
        "input_duration": float(input_probe["format"]["duration"]),
        "output_duration": float(output_probe["format"]["duration"]),
        "output_video": next((s for s in output_probe["streams"] if s.get("codec_type") == "video"), {}),
        "output_audio": next((s for s in output_probe["streams"] if s.get("codec_type") == "audio"), {}),
    }
    report_path = output.with_suffix(".verification.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
