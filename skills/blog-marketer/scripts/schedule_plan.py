#!/usr/bin/env python3
"""여러 편을 올릴 때 예약 시각 제안표를 만든다. 예약을 거는 건 사용자가 발행 창에서 한다.

사용: schedule_plan.py N [--start "YYYY-MM-DD HH:MM"] [--interval-hours 9] [--per-day 2]

규칙(예리 방식을 가져옴: 시작 시각 + 간격 x 순번)
- 하루 최대 편수(기본 2)를 넘기지 않는다. 넘으면 다음 날 같은 시각대로 민다.
- 07:00~22:00 밖이면 다음 날 시작 시각으로 민다.
- 네이버 예약은 10분 단위라 분은 10의 배수로 맞춘다.
"""
import argparse
import datetime as dt
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

OPEN_H, CLOSE_H = 7, 22


def plan(n: int, start: dt.datetime, interval_h: float, per_day: int) -> list[dt.datetime]:
    out: list[dt.datetime] = []
    cur = start
    day_count: dict[dt.date, int] = {}
    while len(out) < n:
        cur = cur.replace(minute=(cur.minute // 10) * 10, second=0, microsecond=0)
        if cur.hour < OPEN_H:
            cur = cur.replace(hour=start.hour, minute=start.minute)
        if cur.hour >= CLOSE_H or day_count.get(cur.date(), 0) >= per_day:
            nxt = (cur + dt.timedelta(days=1)).replace(hour=start.hour, minute=start.minute)
            cur = nxt
            continue
        out.append(cur)
        day_count[cur.date()] = day_count.get(cur.date(), 0) + 1
        cur = cur + dt.timedelta(hours=interval_h)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("count", type=int)
    ap.add_argument("--start")
    ap.add_argument("--interval-hours", type=float, default=9)
    ap.add_argument("--per-day", type=int, default=2)
    a = ap.parse_args()
    if a.count < 1:
        print("편수는 1 이상이어야 합니다.")
        return 1
    if a.start:
        start = dt.datetime.strptime(a.start, "%Y-%m-%d %H:%M")
    else:
        t = dt.datetime.now() + dt.timedelta(days=1)
        start = t.replace(hour=9, minute=0, second=0, microsecond=0)
    wd = "월화수목금토일"
    for i, t in enumerate(plan(a.count, start, a.interval_hours, max(1, a.per_day)), 1):
        print(f"{i}번째 글  {t:%Y-%m-%d}({wd[t.weekday()]}) {t:%H:%M}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
