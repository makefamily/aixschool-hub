#!/usr/bin/env bash
# 사용법: cut_strips.sh <렌더본.mp4> <편집점초 목록 파일(한 줄에 하나)> <출력폴더>
# 각 편집점 ±0.5초 6프레임 스트립 + 파형 이미지(빨간 세로선 = 편집점)를 만든다.
set -euo pipefail
f="$1"; list="$2"; out="$3"; mkdir -p "$out"; i=0
while read -r t; do
  [ -z "$t" ] && continue; i=$((i+1)); s=$(echo "x=$t-0.5; if (x<0) x=0; x" | bc -l)
  # -t 는 입력 옵션이어야 한다(출력에 두면 showwavespic이 파일 끝까지 읽는다)
  ffmpeg -v error -y -ss "$s" -t 1 -i "$f" -vf "fps=6,scale=320:-2,tile=6x1" -frames:v 1 "$out/cut_$(printf %03d $i)_frames.jpg"
  ffmpeg -v error -y -ss "$s" -t 1 -i "$f" -filter_complex "color=c=0x111111:s=1920x160:d=1[bg];[0:a]showwavespic=s=1920x160:colors=0x7FD4FF:scale=sqrt[w];[bg][w]overlay=format=auto,drawbox=x=959:y=0:w=3:h=160:color=red:t=fill" -frames:v 1 "$out/cut_$(printf %03d $i)_wave.png"
done < "$list"
echo "편집점 ${i}개 → $out"
