#!/bin/bash
# AI 학교 허브 맥 한 줄 설치: 최신 Releases 묶음을 받아 install-mac.command 를 실행한다.
# 자동 실행·예약 작업은 만들지 않는다. 다른 사람 계정·키는 넣지 않는다.
set -e
REPO="${AIHUB_REPO:-makefamily/aixschool-hub}"
URL="${AIHUB_ZIP_URL:-https://github.com/$REPO/releases/latest/download/AISchoolHub-mac.zip}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
echo "[AI 학교 허브] 최신 묶음 받는 중..."
curl -fL --progress-bar "$URL" -o "$TMP/hub.zip"
ditto -x -k "$TMP/hub.zip" "$TMP/x"
bash "$TMP/x/AISchoolHub-install/install-mac.command"
