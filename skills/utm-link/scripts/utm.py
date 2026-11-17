"""내 링크에 UTM(유입 표시)을 붙인다. AI(스킬을 읽은 Claude·Codex)가 실행하는 도구다. 학생에게 이 명령을 보여주지 않는다.

  python utm.py "<내 사이트 링크>" --host 내사이트.com --preset instagram --campaign 261201-event
  python utm.py "<링크>" --host 내사이트.com --all --campaign 261201-event      # 채널별 링크를 한 번에

규칙 두 개
1. 내 분석 도구(GA4 등)가 붙은 도메인에만 붙인다. --host 로 알려 준 도메인이 아니면 원본 그대로 돌려준다.
   (노션·구글폼처럼 내 분석이 없는 곳에 붙이면 주소만 지저분해지고 잡히는 것이 없다.)
2. 링크에 이미 utm_source 가 있으면 건드리지 않는다.
--host 대신 환경 변수 UTM_TRACKED_HOSTS(쉼표로 구분)를 써도 된다.
"""
import argparse
import os
import re
import sys
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

# 채널 프리셋. 이름 하나로 source/medium 을 고정한다(표기가 갈리면 분석에서 두 줄로 쪼개진다)
PRESETS = {
    "kakao": ("kakao", "message"),
    "openchat": ("kakao", "openchat"),
    "sms": ("sms", "sms"),
    "email": ("email", "email"),
    "newsletter": ("newsletter", "email"),
    "instagram": ("instagram", "bio"),
    "instagram-post": ("instagram", "post"),
    "instagram-story": ("instagram", "story"),
    "instagram-dm": ("instagram", "dm"),
    "threads": ("threads", "post"),
    "naver-cafe": ("naver-cafe", "post"),
    "naver-blog": ("naver-blog", "post"),
    "youtube": ("youtube", "description"),
    "meta-ads": ("meta", "paid_social"),
}


def normalize(value):
    """소문자·하이픈으로 맞춘다. 분석 도구는 대소문자를 다른 값으로 센다. 언더바는 그대로 둔다(paid_social 같은 관례값)."""
    if not value:
        return ""
    v = re.sub(r"\s+", "-", str(value).strip().lower())
    v = re.sub(r"[^a-z0-9가-힣._\-]", "", v)
    return re.sub(r"-{2,}", "-", v).strip("-")


def is_tracked(url, hosts):
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    return bool(host) and any(host == h or host.endswith("." + h) for h in hosts)


def tag(url, hosts, source, medium, campaign=None, content=None):
    """UTM 을 붙여 돌려준다. 대상이 아니면 원본 그대로(예외를 던지지 않는다)."""
    if not url or not is_tracked(url, hosts):
        return url
    try:
        parts = urlparse(url)
    except ValueError:
        return url
    query = parse_qsl(parts.query, keep_blank_values=True)
    if any(k.lower() == "utm_source" for k, _ in query):
        return url
    for key, value in (("utm_source", source), ("utm_medium", medium), ("utm_campaign", campaign), ("utm_content", content)):
        v = normalize(value)
        if v:
            query.append((key, v))
    return urlunparse(parts._replace(query=urlencode(query)))


def main(argv=None):
    p = argparse.ArgumentParser(description="링크에 UTM 붙이기")
    p.add_argument("url")
    p.add_argument("--host", action="append", default=[], help="내 분석이 붙은 도메인(여러 번 가능)")
    p.add_argument("--preset", help="채널 프리셋: " + ", ".join(PRESETS))
    p.add_argument("--source")
    p.add_argument("--medium")
    p.add_argument("--campaign", default="", help="YYMMDD-이름 (예: 261201-event)")
    p.add_argument("--content", default="")
    p.add_argument("--all", action="store_true")
    a = p.parse_args(argv)
    hosts = [h.strip().lower() for h in (a.host or os.environ.get("UTM_TRACKED_HOSTS", "").split(",")) if h.strip()]
    if not hosts:
        p.error("내 분석이 붙은 도메인을 --host 로 알려 줘야 해요(학생에게 먼저 물어보세요)")
    if not is_tracked(a.url, hosts):
        print(a.url)
        print(f"(태깅 안 함: {urlparse(a.url).hostname or '?'} 는 내 분석 대상으로 알려 준 도메인이 아닙니다)", file=sys.stderr)
        return 0
    if a.all:
        w = max(len(k) for k in PRESETS)
        for name, (s, m) in PRESETS.items():
            print(f"{name:<{w}}  {tag(a.url, hosts, s, m, a.campaign, a.content)}")
        return 0
    if a.preset:
        if a.preset not in PRESETS:
            p.error(f"모르는 프리셋 '{a.preset}'. 쓸 수 있는 것: {', '.join(PRESETS)}")
        source, medium = PRESETS[a.preset]
    elif a.source and a.medium:
        source, medium = a.source, a.medium
    else:
        p.error("--preset 이나 --source/--medium 중 하나는 있어야 합니다")
    out = tag(a.url, hosts, source, medium, a.campaign, a.content)
    print(out)
    if out == a.url:
        print("(태깅 안 함: 이미 utm_source 가 있습니다)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
