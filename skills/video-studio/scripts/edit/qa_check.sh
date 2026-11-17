#!/usr/bin/env bash
# 사용법: qa_check.sh <final.mp4> [목표초] [허용오차초] [목표LUFS] [목표해상도 예: 1080x1920] [silent]
# 기술 검사만 한다. 결과는 <파일>.qa/ 에 저장, 요약은 stdout. 자동 수정 없음.
set -uo pipefail
f="$1"; target="${2:-}"; tol="${3:-}"; lufs="${4:--14}"; res="${5:-}"; silent="${6:-}"   # 6번째 인자 silent: 소리 없는 영상(모션그래픽 등)
out="${f%.*}.qa"; mkdir -p "$out"
fail=0
say(){ printf '%-14s %-6s %s\n' "$1" "$2" "$3"; if [ "$2" = FAIL ]; then fail=$((fail+1)); fi; return 0; }

ffprobe -v error -show_entries format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt,sample_rate,channels,color_primaries,color_transfer,color_space \
  -of json "$f" > "$out/probe.json"
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
v=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,r_frame_rate,pix_fmt,color_primaries -of csv=p=0 "$f")
a=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels -of csv=p=0 "$f")
say stream INFO "video=$v audio=${a:-없음} dur=${dur}s"
if [ -z "$a" ]; then if [ "$silent" = silent ]; then say audio INFO "오디오 없음(silent 지정)"; else say audio FAIL "오디오 스트림 없음 (소리 없는 영상이면 6번째 인자에 silent)"; fi; fi
if [ -n "$res" ]; then wh=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$f" | head -1 | tr -d '\r' | sed 's/,*$//; s/,/x/'); [ "$wh" = "$res" ] && say resolution PASS "$wh" || say resolution FAIL "$wh (목표 $res)"; fi
pf=$(ffprobe -v error -select_streams v:0 -show_entries stream=pix_fmt -of csv=p=0 "$f"); [ "$pf" = yuv420p ] && say pix_fmt PASS yuv420p || say pix_fmt WARN "$pf (웹 납품은 yuv420p TV range)"
col=$(ffprobe -v error -select_streams v:0 -show_entries stream=color_primaries,color_transfer,color_space -of csv=p=0 "$f")
[ "$col" = "bt709,bt709,bt709" ] && say color PASS "primaries/trc/matrix=bt709" || say color WARN "색 태그 ${col:-없음} (SDR 웹은 bt709 3종 권장)"
if [ -n "$target" ] && [ -n "$tol" ]; then
  ok=$(echo "d=$dur-$target; if (d<0) d=-d; d<=$tol" | bc -l)
  [ "$ok" = 1 ] && say duration PASS "${dur}s (목표 ${target}±${tol})" || say duration FAIL "${dur}s (목표 ${target}±${tol})"
fi

if [ -n "$a" ]; then
  ffmpeg -nostats -i "$f" -af ebur128=peak=true -f null - 2> "$out/ebur128.log"
  I=$(grep -A12 'Summary' "$out/ebur128.log" | awk '/ I:/{print $2}' | head -1)
  TP=$(grep -A20 'Summary' "$out/ebur128.log" | awk '/Peak:/{print $2}' | head -1)
  okI=$(echo "d=$I-($lufs); if (d<0) d=-d; d<=1" | bc -l)
  [ "$okI" = 1 ] && say loudness PASS "I=${I} LUFS (목표 ${lufs}±1)" || say loudness FAIL "I=${I} LUFS (목표 ${lufs}±1)"
  okT=$(echo "$TP <= -1" | bc -l)
  [ "$okT" = 1 ] && say truepeak PASS "TP=${TP} dBTP" || say truepeak FAIL "TP=${TP} dBTP (> -1)"
  ffmpeg -nostats -i "$f" -af "silencedetect=noise=-45dB:d=0.8" -f null - 2> "$out/silence.log"
  ns=$(grep -c 'silence_end' "$out/silence.log"); [ "$ns" = 0 ] && say silence PASS "0.8초+ 무음 0건" || say silence WARN "0.8초+ 무음 ${ns}건 (silence.log 확인)"
fi

ffmpeg -nostats -i "$f" -vf "blackdetect=d=0.10:pix_th=0.04,freezedetect=n=-60dB:d=2" -an -f null - 2> "$out/video.log"
nb=$(grep -c 'black_start' "$out/video.log"); nf=$(grep -c 'freeze_start' "$out/video.log")
[ "$nb" = 0 ] && say black PASS "0건" || say black WARN "${nb}건 (video.log, 의도된 페이드인지 확인)"
[ "$nf" = 0 ] && say freeze PASS "0건" || say freeze WARN "${nf}건 (video.log — 끝 카드 등 의도된 정지면 정상)"

first=$(ffprobe -v trace "$f" 2>&1 | grep -o "type:'\(moov\|mdat\)'" | head -1)
[ "$first" = "type:'moov'" ] && say faststart PASS moov-first || say faststart WARN "moov가 뒤 (faststart 필요)"

for p in 0 0.25 0.5 0.75 0.98; do
  t=$(echo "$dur*$p" | bc -l)
  ffmpeg -v error -y -ss "$t" -i "$f" -frames:v 1 -vf scale=960:-1 "$out/frame_${p}.jpg"
done
say frames INFO "$out/frame_*.jpg 5장 — 직접 열어 확인"
echo "FAIL=$fail"
exit $fail
