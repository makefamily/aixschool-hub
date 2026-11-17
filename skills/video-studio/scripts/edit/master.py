#!/usr/bin/env python3
"""최종 마스터: 2-pass loudnorm(선형 모드 보장) + BT.709/TV range 실제 변환 + faststart + 인코딩 후 트루피크 재측정.
사용법: master.py <in.mp4> <out.mp4> [--lufs -14] [--tp -1.5] [--copy-video]
--copy-video: 영상 스트림 복사(색 태그는 원본 유지). 기본은 libx264 crf18 + bt709 태그.

실측으로 고친 함정(2026-09-27):
- 코드 렌더 영상은 full range(pc)다. 입력 범위를 선언하지 않고 TV로 바꾸면 흰색이 ebebeb 회색이 된다 → irange/in_range 명시.
- 소스 LRA가 목표 LRA보다 크면 loudnorm이 조용히 동적 모드로 바뀌어 조용한 구간을 끌어올리고, AAC 인코딩에서 트루피크가 +6.9dBTP까지 튀었다 → LRA를 소스보다 크게 잡아 선형 모드를 유지하고, 인코딩 뒤 TP를 다시 재서 넘으면 목표를 낮춰 재인코딩(최대 3회).
"""
import json, re, subprocess, argparse, sys
p = argparse.ArgumentParser(); p.add_argument("src"); p.add_argument("out")
p.add_argument("--lufs", type=float, default=-14); p.add_argument("--tp", type=float, default=-1.5)
p.add_argument("--copy-video", action="store_true")
a = p.parse_args()

def measure(path):
    r = subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",path,"-af",f"loudnorm=I={a.lufs}:TP={a.tp}:print_format=json","-f","null","-"],
                       capture_output=True, text=True)
    return json.loads(re.findall(r"\{[^{}]*\}", r.stderr)[-1])

def out_tp(path):
    e = subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",path,"-af","ebur128=peak=true","-f","null","-"],capture_output=True,text=True).stderr
    s = e[e.rfind("Summary"):]
    I = float(re.search(r"I:\s+(-?[\d.]+) LUFS", s).group(1)); TP = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", s).group(1))
    return I, TP

pr = json.loads(subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries",
    "stream=color_space,color_primaries,color_transfer,color_range,pix_fmt","-of","json",a.src],capture_output=True,text=True).stdout)["streams"][0]
full = pr.get("color_range") == "pc" or pr.get("pix_fmt","").startswith("yuvj")
ir = "pc" if full else "tv"
# 색 변환은 swscale(scale)로 한다. colorspace 필터는 전체 길이 렌더에서 범위를 두 번 압축해 흰색을 e9e9e9로 만든 실측이 있다(짧은 구간에선 정상이라 놓치기 쉬움).
sd = {"bt470bg":"bt601","smpte170m":"bt601","bt709":"bt709"}
im = sd.get(pr.get("color_space")) or ("bt601" if pr.get("color_primaries") in ("bt470bg","smpte170m") else "bt709")
vf = (f"scale=in_color_matrix={im}:out_color_matrix=bt709:in_range={ir}:out_range=tv,format=yuv420p,"
      "setparams=range=tv:colorspace=bt709:color_primaries=bt709:color_trc=bt709")
v = ["-c:v","copy"] if a.copy_video else ["-vf",vf,"-c:v","libx264","-preset","medium","-crf","18",
     "-color_primaries","bt709","-color_trc","bt709","-colorspace","bt709","-color_range","tv"]
print("입력 색:", pr, "→ 영상 필터:", "copy" if a.copy_video else vf)

has_audio = bool(subprocess.run(["ffprobe","-v","error","-select_streams","a:0","-show_entries","stream=codec_type","-of","csv=p=0",a.src],capture_output=True,text=True).stdout.strip())
if not has_audio:   # 소리 없는 영상(모션그래픽 등): 색·형식만 맞춰 인코딩한다
    r = subprocess.run(["ffmpeg","-y","-hide_banner","-nostats","-i",a.src,*v,"-an","-movflags","+faststart",a.out],capture_output=True,text=True)
    if r.returncode: sys.exit(r.stderr[-2000:])
    print(f"완료(소리 없는 영상, 라우드니스 생략): {a.out}"); sys.exit(0)

m = measure(a.src)
lra = max(11.0, float(m["input_lra"]) + 1.0)   # 선형 모드 유지
tp = a.tp
for attempt in range(1, 4):
    af = (f"loudnorm=I={a.lufs}:TP={tp}:LRA={lra}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true:print_format=summary,aresample=48000")
    r = subprocess.run(["ffmpeg","-y","-hide_banner","-nostats","-i",a.src,"-af",af,*v,"-c:a","aac","-b:a","192k","-ar","48000",
                        "-movflags","+faststart",a.out], capture_output=True, text=True)
    if r.returncode: sys.exit(r.stderr[-2000:])
    mode = "dynamic" if re.search(r"Normalization Type:\s+Dynamic", r.stderr) else "linear"
    I, TPo = out_tp(a.out)
    print(f"[{attempt}] 입력 I={m['input_i']} TP={m['input_tp']} LRA={m['input_lra']} → 출력 I={I} TP={TPo} (loudnorm {mode}, 목표 TP {tp})")
    if TPo <= -1.0: break
    tp -= (TPo + 1.0) + 0.5          # 초과분 + 여유만큼 목표를 낮춰 재인코딩
else:
    print("경고: 3회 후에도 트루피크 -1dBTP 초과. 음원 자체 피크(하이햇 등)를 줄여야 함", file=sys.stderr)
if abs(I - a.lufs) > 1.0:
    print(f"경고: 출력 {I} LUFS가 목표 {a.lufs}에서 1LU 이상 벗어남. 순간 피크(하이햇·클릭·효과음)가 커서 트루피크를 지키며 키울 수 없다 → 음원에서 해당 피크를 줄이거나 음악 레이어를 다시 믹스", file=sys.stderr)
print(f"완료: {a.out}")
