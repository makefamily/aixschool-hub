#!/usr/bin/env bash
# 단어 단위 정밀 전사 환경 설치 (무료·로컬, Apple Silicon 맥용 mlx-whisper 포함, uv 필요).
# 설치 위치는 환경변수 ASR_VENV 로 바꿀 수 있다. 제거: 그 폴더 삭제
set -euo pipefail
V="${ASR_VENV:-$HOME/video-editor-asr}"
[ -x "$V/bin/python" ] && "$V/bin/python" -c "import whisperx, mlx_whisper" 2>/dev/null && { echo "이미 설치됨: $V"; exit 0; }
mkdir -p "$(dirname "$V")"
uv venv -q -p 3.11 "$V"
uv pip install -q -p "$V/bin/python" whisperx mlx-whisper
"$V/bin/python" -c "import whisperx, mlx_whisper; print('설치 완료:', '$V')"
