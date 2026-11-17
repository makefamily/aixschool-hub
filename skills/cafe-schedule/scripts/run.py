"""cafe-schedule: 표(CSV)를 읽어 결과 표와 화면(HTML)을 만든다. 아무 데도 보내거나 올리지 않는다. 작업 폴더는 --work 로 정한다."""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# 윈도우에서 출력이 다른 프로그램(Codex 등)으로 넘어갈 때 한글·기호 때문에 멈추지 않게 한다.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors='replace')
    except (AttributeError, ValueError):
        pass


def _work_dir():
    a = sys.argv
    if '--work' in a and a.index('--work') + 1 < len(a):
        return Path(a[a.index('--work') + 1]).expanduser().resolve()
    return Path.cwd() / '카페-발행표'


def _seed():
    """작업 폴더에 없는 연습 자료·규칙 표만 스킬의 samples 에서 복사한다. 있는 파일은 건드리지 않는다."""
    import shutil
    mark = _work_dir() / '.시작함'
    if mark.exists():
        return
    base = SKILL / 'samples'
    for p in base.rglob('*'):
        if p.is_file():
            to = _work_dir() / p.relative_to(base)
            if not to.exists():
                to.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, to)
    mark.write_text('연습 자료와 규칙 표를 한 번 복사했습니다. 이 파일이 있으면 다시 복사하지 않습니다.\n', encoding='utf-8')

SKILL = Path(__file__).resolve().parent.parent
HERE = ROOT = _work_dir()
_seed()
OUT = HERE / '결과'
PASS, FAIL = '통과', '확인 필요'


def say(text=''):
    print(text, flush=True)


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f'파일이 없습니다: {path}')
    for enc in ('utf-8-sig', 'cp949'):
        try:
            with open(path, newline='', encoding=enc) as f:
                return [{k.strip(): (v or '').strip() for k, v in row.items() if k} for row in csv.DictReader(f)]
        except UnicodeDecodeError:
            continue
    raise SystemExit(f'{path.name} 파일 글자가 깨져 있습니다. 엑셀에서 "CSV UTF-8"로 다시 저장해 주세요.')


def write_csv(path: Path, header: list[str], rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def number(text, default=0.0) -> float:
    try:
        return float(str(text).replace(',', '').replace('원', '').strip() or default)
    except ValueError:
        return default


def board(title: str, subtitle: str, results, cards: list[str], skipped: list[tuple[str, str]], filename: str) -> Path:
    """결과 화면(HTML). cards 는 이미 만든 HTML 조각, skipped 는 (제목, 이유)."""
    check = ''.join(f"<li class='{'pass' if ok else 'fail'}'><b>{PASS if ok else FAIL}</b> {html.escape(t)}<small>{html.escape(d)}</small></li>" for ok, t, d in results)
    out = ''.join(f"<li><b>{html.escape(a)}</b><span>{html.escape(b)}</span></li>" for a, b in skipped)
    page = f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>
<style>body{{margin:0;background:#f8fafc;color:#111827;font:16px/1.6 -apple-system,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;padding:32px 16px}}
.w{{max-width:800px;margin:auto}}h1{{font-size:28px;margin:0}}.src{{color:#6b7280;margin:4px 0 18px}}
ul.c{{list-style:none;padding:0;margin:0 0 22px;display:grid;gap:8px}}ul.c li{{background:#fff;border:1px solid #e5e7eb;padding:12px 14px}}ul.c li b{{margin-right:8px}}ul.c small{{display:block;color:#4b5563}}
.pass b{{color:#15803d}}.fail{{border-color:#f5c2bd!important;background:#fdecea!important}}.fail b{{color:#b42318}}
article{{background:#fff;border:1px solid #e5e7eb;border-left:4px solid #2563eb;padding:14px 16px;margin-bottom:10px}}
article h2{{font-size:18px;margin:0 0 4px}}article p{{margin:4px 0;color:#374151;white-space:pre-wrap}}article small{{color:#6b7280}}
.box{{background:#eff4ff;padding:10px 12px;margin-top:8px;white-space:pre-wrap}}.box b{{display:block;color:#2563eb;font-size:13px}}
table{{width:100%;border-collapse:collapse;background:#fff;margin:6px 0 16px}}th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid #e5e7eb;font-size:15px}}th{{background:#f3f4f6;font-size:13px;color:#4b5563}}
.note{{background:#111827;color:#fff;padding:12px 14px;margin-bottom:18px}}
details{{margin-top:22px}}details li{{margin:4px 0;color:#4b5563;font-size:14px}}details li span{{margin-left:8px;color:#9ca3af}}</style>
<div class="w"><h1>{html.escape(title)}</h1><p class="src">{html.escape(subtitle)}</p>
<p class="note">아직 아무 데도 보내거나 올리지 않았습니다.</p>
<ul class="c">{check}</ul>{''.join(cards)}
{f'<details><summary>빠진 것 {len(skipped)}개와 이유</summary><ul>{out}</ul></details>' if skipped else ''}</div>"""
    OUT.mkdir(exist_ok=True)
    path = OUT / filename
    path.write_text(page, encoding='utf-8')
    return path


def finish(summary: str, results, page: Path, open_browser: bool) -> int:
    say(summary)
    say('')
    for ok, title, detail in results:
        say(f"  [{PASS if ok else FAIL}] {title} — {detail}")
    fails = sum(not ok for ok, _, _ in results)
    say('')
    say(f'{FAIL} {fails}개. ' + ('세 가지 모두 통과했습니다.' if not fails else '02_규칙 표를 고친 뒤 다시 실행하세요.'))
    say(f'결과 화면: {page}')
    say('아직 아무 데도 보내거나 올리지 않았습니다.')
    return fails


# ================================================================ 이 스킬 고유 부분

DRAFTS = ROOT / '01_원고' / '원고_샘플.csv'
PLAN = ROOT / '02_규칙' / '발행규칙.csv'
BANNED = ROOT / '02_규칙' / '금지어.csv'
SCHEDULE = OUT / '발행예약표.csv'

# 검수용: 규칙 표와 상관없이 카페에서 광고로 신고당하기 쉬운 말.
RISKY = ['010-', '카톡 문의', '오픈채팅', '최저가', '무조건', '100% 보장']


def when(date_s: str, time_s: str) -> datetime:
    return datetime.strptime(f'{date_s} {time_s}', '%Y-%m-%d %H:%M')


def plan_rules() -> dict:
    out = {}
    for r in read_csv(PLAN):
        try:
            out[r['게시판']] = {'per_day': int(r['하루 최대']), 'start': int(r['올릴 수 있는 시작 시각']), 'end': int(r['올릴 수 있는 끝 시각']),
                               'gap': int(r['글 사이 간격(분)']), 'menu': r.get('메뉴번호', '')}
        except (KeyError, ValueError):
            raise SystemExit('02_규칙/발행규칙.csv 의 숫자 칸(하루 최대·시각·간격)에는 숫자만 적어 주세요.')
    return out


def schedule(drafts, rules, banned):
    rows, taken = [], {}
    for d in sorted(drafts, key=lambda x: (x.get('원하는 날짜', ''), x.get('원하는 시각', ''))):
        text = f"{d.get('제목', '')} {d.get('본문', '')}"
        row = dict(d, 상태='', 이유='', 예약시각='')
        bad = next((b['금지어'] for b in banned if b.get('금지어') and b['금지어'] in text), None)
        rule = rules.get(d.get('게시판', ''))
        if bad:
            row.update(상태='뺌', 이유=f"금지어 '{bad}'")
        elif not rule:
            row.update(상태='뺌', 이유='발행규칙에 없는 게시판')
        elif any(r['제목'] == d['제목'] and r['상태'] == '예약' for r in rows):
            row.update(상태='뺌', 이유='같은 제목이 이미 예약됨')
        else:
            t = when(d['원하는 날짜'], d['원하는 시각'])
            for _ in range(24 * 14):
                day = [x for x in taken.get(d['게시판'], []) if x.date() == t.date()]
                ok_hour = rule['start'] <= t.hour < rule['end']
                ok_gap = all(abs((t - x).total_seconds()) >= rule['gap'] * 60 for x in taken.get(d['게시판'], []))
                if ok_hour and ok_gap and len(day) < rule['per_day']:
                    break
                t = t + timedelta(minutes=30) if ok_hour and len(day) < rule['per_day'] else datetime.combine(t.date() + (timedelta(days=1) if t.hour >= rule['start'] or len(day) >= rule['per_day'] else timedelta()), datetime.min.time()).replace(hour=rule['start'])
            taken.setdefault(d['게시판'], []).append(t)
            moved = t != when(d['원하는 날짜'], d['원하는 시각'])
            row.update(상태='예약', 예약시각=t.strftime('%Y-%m-%d %H:%M'), 이유='규칙에 맞춰 옮김' if moved else '원하는 시각 그대로')
        rows.append(row)
    return rows


def checks(rows, rules):
    booked = [r for r in rows if r['상태'] == '예약']
    over, bad_time, gap = [], [], []
    for board_name, rule in rules.items():
        mine = sorted(datetime.strptime(r['예약시각'], '%Y-%m-%d %H:%M') for r in booked if r['게시판'] == board_name)
        for day in {x.date() for x in mine}:
            if sum(x.date() == day for x in mine) > rule['per_day']:
                over.append(f'{board_name} {day}')
        bad_time += [f'{board_name} {x:%H:%M}' for x in mine if not rule['start'] <= x.hour < rule['end']]
        gap += [f'{board_name} {a:%m-%d %H:%M}' for a, b in zip(mine, mine[1:]) if (b - a).total_seconds() < rule['gap'] * 60]
    risky = [r['제목'][:24] for r in booked if any(s in f"{r['제목']} {r.get('본문', '')}" for s in RISKY)]
    return [
        (not over, '게시판마다 하루에 올리는 글 수를 지켰나', '넘친 날: ' + ', '.join(over) if over else '하루 최대 글 수 지킴'),
        (not bad_time and not gap, '올리는 시간과 글 사이 간격을 지켰나', '어긋난 곳: ' + ', '.join(bad_time + gap) if bad_time or gap else '시간·간격 모두 지킴'),
        (not risky, '광고로 신고당하기 쉬운 말이 없나', '걸린 글: ' + ', '.join(risky) if risky else '위험한 말 없음'),
    ]


def make(open_browser=True):
    rules = plan_rules()
    rows = schedule(read_csv(DRAFTS), rules, read_csv(BANNED))
    write_csv(SCHEDULE, ['예약시각', '게시판', '제목', '본문', '상태', '이유'], rows)
    booked = sorted([r for r in rows if r['상태'] == '예약'], key=lambda r: r['예약시각'])
    results = checks(rows, rules)
    cards = [f"<article><small>{html.escape(r['예약시각'])} · {html.escape(r['게시판'])} · {html.escape(r['이유'])}</small><h2>{html.escape(r['제목'])}</h2><p>{html.escape(r.get('본문', '')[:90])}…</p></article>" for r in booked]
    skipped = [(r['제목'][:30], r['이유']) for r in rows if r['상태'] != '예약']
    page = board(f'발행 예약 {len(booked)}개', f'원고 {len(rows)}개 · 게시판별 하루 최대·시간·간격을 지켜 자리를 잡았습니다', results, cards, skipped, '발행예약.html')
    return finish(f'원고 {len(rows)}개를 읽었습니다. 발행 예약 {len(booked)}개, 뺀 원고 {len(rows) - len(booked)}개.', results, page, open_browser)


# ---------------------------------------------------------------- 실제로 올리기 (네이버 카페 글쓰기 API)
def main():
    p = argparse.ArgumentParser(description='카페 글 발행 예약표')
    p.add_argument('--work', help='작업 폴더')
    p.add_argument('--no-open', action='store_true')
    p.parse_args()
    make(False)


if __name__ == '__main__':
    main()
