#!/bin/bash
# AI 학교 허브 맥 설치. 묶음 파일을 푼 폴더에서 이 파일을 두 번 눌러 실행한다.
# 하는 일: Node 확인 → Codex(허브 폴더 안)·Claude 프로그램 확인 → 허브 폴더(~/AISchoolHub) 만들기 → 스킬·규칙 깔기 → 앱 설치·열기
# 학생 본인 계정으로만 로그인한다. 다른 사람 계정·키는 넣지 않는다. 자동 실행·예약 작업은 만들지 않는다.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
HUB_HOME="${AIHUB_HOME:-$HOME/AISchoolHub}"
APP_NAME="AI 학교 허브.app"
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"

say() { echo "[AI 학교 허브] $*"; }
need() { command -v "$1" >/dev/null 2>&1; }

say "맥 설치 시작 · 허브 폴더 $HUB_HOME"
if ! need node; then
  say "Node가 없어요. nodejs.org 에서 LTS 설치 파일을 받아 설치한 뒤 이 파일을 다시 실행하세요."
  open "https://nodejs.org/ko/download" 2>/dev/null || true
  exit 1
fi

# 0) 허브 앱이 켜져 있으면 끈다(새 코드로 다시 켜지게)
pkill -x aixschool-hub 2>/dev/null || true
pkill -f "$HUB_HOME/hub/app/server.mjs" 2>/dev/null || true
sleep 1

# 1) 허브 코드: 묶음의 hub 폴더를 그대로 옮긴다(이전 설치가 있으면 코드만 바꾸고 작업·설정은 남긴다)
mkdir -p "$HUB_HOME"
rm -rf "$HUB_HOME/hub.new"
cp -R "$HERE/hub" "$HUB_HOME/hub.new"
rm -rf "$HUB_HOME/hub"
mv "$HUB_HOME/hub.new" "$HUB_HOME/hub"

# 2) Codex 프로그램: 허브 폴더 안에만 깐다(관리자 권한 없이). 이미 있으면 건너뛴다.
if [ ! -f "$HUB_HOME/cli/node_modules/@openai/codex/bin/codex.js" ]; then
  say "Codex 프로그램 설치 중(허브 폴더 안)..."
  mkdir -p "$HUB_HOME/cli"
  npm install --prefix "$HUB_HOME/cli" --no-audit --no-fund @openai/codex >/dev/null 2>&1 || say "Codex 설치 실패 — Claude만으로도 허브는 돌아가요"
fi

# 3) Claude 프로그램: 없으면 공식 설치 파일로 설치
if ! need claude && [ ! -x "$HOME/.local/bin/claude" ]; then
  say "Claude 프로그램 설치 중(공식 설치 파일)..."
  curl -fsSL https://claude.ai/install.sh | bash || say "Claude 설치 실패 — Codex만으로도 허브는 돌아가요"
fi

# 4) 허브 폴더·스킬·규칙. Codex 로그인 창이 뜨면 학생 본인 계정으로 로그인한다.
AIHUB_HOME="$HUB_HOME" node "$HUB_HOME/hub/tools/setup.mjs"

# 5) 앱: ~/Applications 에 넣고 연다
mkdir -p "$HOME/Applications"
rm -rf "$HOME/Applications/$APP_NAME"
cp -R "$HERE/$APP_NAME" "$HOME/Applications/"
xattr -dr com.apple.quarantine "$HOME/Applications/$APP_NAME" 2>/dev/null || true
if [ -n "$AIHUB_OPEN_BG" ]; then open -g "$HOME/Applications/$APP_NAME"; else open "$HOME/Applications/$APP_NAME"; fi
say "끝. 허브 폴더: $HUB_HOME · 앱: ~/Applications/$APP_NAME"
say "앱에서 설정 > AI 로그인으로 Claude 로그인 상태를 확인하세요."
