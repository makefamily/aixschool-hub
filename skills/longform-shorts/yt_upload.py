# -*- coding: utf-8 -*-
"""완성한 쇼츠 1개를 학생 본인의 유튜브 채널에 '비공개'로 올리고, 원하면 공개 시각을 예약한다.

AI(스킬을 읽은 Claude·Codex)가 실행하는 도구다. 학생에게 이 명령을 보여주지 않는다.
  python yt_upload.py <영상.mp4> --title "제목" --desc "설명" [--publish-at 2026-12-01T18:30:00+09:00] --yes

필요한 값: 허브 설정 > 연결 > 유튜브 에 넣은 YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET (환경 변수로 전달됨).
처음 한 번은 브라우저가 열려 학생이 직접 구글 계정으로 허락한다. 허락 정보는 학생 PC 사용자 폴더에만 저장하고 어디에도 복사하지 않는다.
--yes 가 없으면 올리지 않고 무엇을 올릴지만 보여 준다(올리기 전 학생 확인용).
업로드 1건은 API 할당량을 크게 쓴다(하루 몇 건). 한도에 걸리면 멈추고 스튜디오 직접 올리기로 안내한다. 자동 재시도 없음.
"""
import argparse
import json
import os
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]
TOKEN = Path.home() / ".aixschool-hub" / "youtube-token.json"


def credentials():
    cid, secret = os.environ.get("YOUTUBE_CLIENT_ID"), os.environ.get("YOUTUBE_CLIENT_SECRET")
    if not cid or not secret:
        raise SystemExit("[연결 필요] 유튜브 연결 값이 비어 있어요. 허브 설정 > 연결 > 유튜브에 넣어야 해요. 없으면 AI가 만드는 순서를 안내해 드려요.")
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        conf = {"installed": {"client_id": cid, "client_secret": secret,
                              "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                              "token_uri": "https://oauth2.googleapis.com/token",
                              "redirect_uris": ["http://localhost"]}}
        creds = InstalledAppFlow.from_client_config(conf, SCOPES).run_local_server(port=0)
        TOKEN.parent.mkdir(parents=True, exist_ok=True)
        TOKEN.write_text(creds.to_json(), encoding="utf-8")
        try:
            os.chmod(TOKEN, 0o600)
        except OSError:
            pass
    return creds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--title", required=True)
    ap.add_argument("--desc", default="")
    ap.add_argument("--publish-at", help="공개 예약 시각(ISO 8601, 시간대 포함). 없으면 비공개로만 올린다")
    ap.add_argument("--yes", action="store_true", help="학생이 확인했을 때만")
    a = ap.parse_args()
    v = Path(a.video)
    if not v.is_file():
        raise SystemExit(f"파일이 없어요: {v}")
    title = a.title.strip()[:100]
    desc = a.desc if "#shorts" in a.desc.lower() else (a.desc + "\n\n#shorts").strip()
    status = {"privacyStatus": "private", "selfDeclaredMadeForKids": False}
    if a.publish_at:
        status["publishAt"] = a.publish_at
    body = {"snippet": {"title": title, "description": desc, "categoryId": "22"}, "status": status}
    print(json.dumps({"올릴 파일": v.name, "제목": title, "설명 글자 수": len(desc), "공개 예약": a.publish_at or "없음(비공개)"}, ensure_ascii=False))
    if not a.yes:
        print("[확인 대기] 학생이 확인하면 --yes 로 다시 실행해요. 아직 올리지 않았어요.")
        return
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    yt = build("youtube", "v3", credentials=credentials())
    ch = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
    if not ch:
        raise SystemExit("이 구글 계정에 유튜브 채널이 없어요")
    print("올릴 채널:", ch[0]["snippet"]["title"])
    try:
        req = yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(str(v), chunksize=-1, resumable=True))
        res = None
        while res is None:
            _, res = req.next_chunk()
    except HttpError as e:
        reason = str(e)
        if "quota" in reason.lower() or "uploadLimit" in reason:
            raise SystemExit("[한도] 오늘 올릴 수 있는 한도에 걸렸어요. 자동으로 다시 하지 않아요. 내일 이어 가거나 유튜브 스튜디오에서 직접 올리세요.")
        raise SystemExit(f"[실패] 올리지 못했어요: {reason[:300]}")
    print("올렸어요(비공개):", f"https://youtu.be/{res['id']}")


if __name__ == "__main__":
    main()
