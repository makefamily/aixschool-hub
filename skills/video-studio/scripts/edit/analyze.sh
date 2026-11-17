#!/usr/bin/env bash
# 사용법: analyze.sh <원본영상> <출력폴더> [언어=ko]
# 편집 판단용 중간 표현 생성: probe, 16k wav, 워드 전사(JSON/SRT), 무음, 장면 전환, 타임코드 콘택트시트.
set -euo pipefail
src="$1"; out="$2"; lang="${3:-ko}"
model="${WHISPER_MODEL:?환경변수 WHISPER_MODEL 에 whisper.cpp 모델 파일(ggml-large-v3-turbo.bin) 경로를 지정한다}"
mkdir -p "$out/contact"
base=$(basename "${src%.*}")
ffprobe -v error -show_format -show_streams -of json "$src" > "$out/$base.probe.json"
r=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate,avg_frame_rate -of csv=p=0 "$src")
echo "fps(r,avg)=$r  (두 값이 다르면 VFR 의심 → CFR 중간본 권장)"
ffmpeg -v error -y -i "$src" -vn -ac 1 -ar 16000 -c:a pcm_s16le "$out/$base.wav"
whisper-cli -m "$model" -l "$lang" -f "$out/$base.wav" -ojf -osrt -of "$out/$base.words" -sow -ml 1 -np >/dev/null 2>"$out/whisper.log" || { echo "전사 실패: $out/whisper.log"; exit 1; }
whisper-cli -m "$model" -l "$lang" -f "$out/$base.wav" -osrt -of "$out/$base.sentences" -np >/dev/null 2>>"$out/whisper.log"
ffmpeg -nostats -i "$src" -af "silencedetect=noise=-40dB:d=0.5" -f null - 2> "$out/silence.log"
python3 - "$out/silence.log" "$out/silences.json" <<'PY'
import re,sys,json
s=open(sys.argv[1]).read(); st=[float(x) for x in re.findall(r'silence_start: ([\d.]+)',s)]
en=[(float(a),float(b)) for a,b in re.findall(r'silence_end: ([\d.]+) \| silence_duration: ([\d.]+)',s)]
json.dump([{"start":a,"end":e,"dur":d} for a,(e,d) in zip(st,en)],open(sys.argv[2],'w'),indent=1)
print(f"무음 {len(en)}구간, 합계 {sum(d for _,d in en):.1f}초")
PY
ffmpeg -nostats -i "$src" -vf "scdet=threshold=12,metadata=print:file=$out/scenes.txt" -an -f null - 2>/dev/null || true
echo "장면 전환 후보 $(grep -c 'lavfi.scd.time' "$out/scenes.txt" 2>/dev/null || echo 0)개"
ffmpeg -v error -y -i "$src" -vf "fps=1/2,scale=384:-2,drawtext=text='%{pts\:hms}':x=6:y=6:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6,tile=5x5" \
  -fps_mode vfr "$out/contact/sheet_%03d.jpg"
echo "콘택트시트 $(ls "$out/contact" | wc -l | tr -d ' ')장 (장당 50초)"
echo "완료: $out"
