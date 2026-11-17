"""threads-schedule: 표(CSV)를 읽어 결과 표와 화면(HTML)을 만든다. 아무 데도 보내거나 올리지 않는다. 작업 폴더는 --work 로 정한다."""
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
    return Path.cwd() / '스레드-발행표'


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

DRAFTS = ROOT / '01_원고' / '스레드_원고_샘플.csv'
PLAN = ROOT / '02_규칙' / '발행시간.csv'
WORDS = ROOT / '02_규칙' / '빼는말.csv'
SCHEDULE = OUT / '발행예약표.csv'
LIMIT = 500  # 스레드 글 한 칸에 들어가는 최대 글자 수


def split_post(text: str) -> list[str]:
    """500자가 넘으면 문장 단위로 잘라 이어쓰기(댓글 타래)로 나눈다."""
    text = text.replace('\\n', '\n').strip()
    if len(text) <= LIMIT:
        return [text]
    parts, cur = [], ''
    for s in re.split(r'(?<=[.!?。…])\s+|\n+', text):
        if not s:
            continue
        if len(cur) + len(s) + 1 > LIMIT - 6:
            parts.append(cur.strip())
            cur = ''
        cur += s + ' '
    if cur.strip():
        parts.append(cur.strip())
    return [f'{p} ({i}/{len(parts)})' for i, p in enumerate(parts, 1)]


def slots() -> list[str]:
    rows = read_csv(PLAN)
    out = [r['올릴 시각'] for r in rows if r.get('올릴 시각')]
    if not out:
        raise SystemExit('02_규칙/발행시간.csv 에 올릴 시각을 한 줄 이상 적어 주세요 (예: 08:30).')
    return sorted(out)


def schedule(drafts, times, words):
    """원하는 시각이 비어 있으면 그대로, 겹치면 그다음 빈 시각으로 옮긴다."""
    rows, used, wait = [], set(), []
    for d in sorted(drafts, key=lambda x: (x.get('원하는 날짜', ''), x.get('원하는 시각', ''))):
        row = dict(d, 상태='', 이유='', 예약시각='', 칸수=0)
        rows.append(row)
        hit = next((w['빼는말'] for w in words if w.get('빼는말') and w['빼는말'] in d.get('본문', '')), None)
        if hit:
            row.update(상태='뺌', 이유=f"빼는말 '{hit}'")
            continue
        want = datetime.strptime(f"{d['원하는 날짜']} {d.get('원하는 시각') or '00:00'}", '%Y-%m-%d %H:%M')
        if want.strftime('%H:%M') in times and want not in used:
            used.add(want)
            book(row, want, '')
        else:
            wait.append((row, want))
    for row, want in wait:
        day, chosen = want.date(), None
        while not chosen:
            chosen = next((c for c in (datetime.strptime(f'{day} {t}', '%Y-%m-%d %H:%M') for t in times) if c >= want and c not in used), None)
            day += timedelta(days=1)
        used.add(chosen)
        book(row, chosen, ' · 겹쳐서 다음 빈 시간으로 옮김')
    return rows


def book(row, when, note):
    parts = split_post(row.get('본문', ''))
    row.update(상태='예약', 예약시각=when.strftime('%Y-%m-%d %H:%M'), 칸수=len(parts), 나눈글=json.dumps(parts, ensure_ascii=False),
               이유=(f'{len(parts)}칸 이어쓰기로 나눔' if len(parts) > 1 else '한 칸') + note)


def checks(rows, times):
    booked = [r for r in rows if r['상태'] == '예약']
    long_parts = [r['본문'][:18] for r in booked if any(len(p) > LIMIT for p in json.loads(r.get('나눈글') or '[]'))]
    off = [r['예약시각'] for r in booked if r['예약시각'][11:] not in times]
    dup = sorted({r['예약시각'] for r in booked if sum(x['예약시각'] == r['예약시각'] for x in booked) > 1})
    links = [r['본문'][:18] for r in booked if re.search(r'https?://', r['본문'])]
    return [
        (not long_parts, f'한 칸이 {LIMIT}자를 넘지 않나', '넘친 글: ' + ', '.join(long_parts) if long_parts else '모두 500자 안'),
        (not off and not dup, '정해둔 시간에 한 개씩만 올라가나', '어긋난 시각: ' + ', '.join(off + dup) if off or dup else '시간마다 한 개씩'),
        (not links, '본문에 링크를 넣지 않았나', '링크 있는 글: ' + ', '.join(links) if links else '링크는 댓글로 (본문에 없음)'),
    ]


def make(open_browser=True):
    times = slots()
    rows = schedule(read_csv(DRAFTS), times, read_csv(WORDS))
    write_csv(SCHEDULE, ['예약시각', '본문', '칸수', '나눈글', '상태', '이유'], rows)
    booked = sorted([r for r in rows if r['상태'] == '예약'], key=lambda r: r['예약시각'])
    results = checks(rows, times)
    cards = []
    for r in booked:
        parts = json.loads(r['나눈글'])
        cards.append(f"<article><small>{html.escape(r['예약시각'])} · {html.escape(r['이유'])}</small>" + ''.join(f"<div class='box'><b>{i}칸 · {len(p)}자</b>{html.escape(p)}</div>" for i, p in enumerate(parts, 1)) + '</article>')
    skipped = [(r['본문'][:30], r['이유']) for r in rows if r['상태'] != '예약']
    page = board(f'스레드 발행 예약 {len(booked)}개', '정해둔 시간에 하나씩 · 500자가 넘으면 이어쓰기로 나눕니다', results, cards, skipped, '발행예약.html')
    return finish(f'원고 {len(rows)}개를 읽었습니다. 발행 예약 {len(booked)}개, 뺀 원고 {len(rows) - len(booked)}개.', results, page, open_browser)


def main():
    p = argparse.ArgumentParser(description='스레드 글 발행 예약표')
    p.add_argument('--work', help='작업 폴더')
    p.add_argument('--no-open', action='store_true')
    p.parse_args()
    make(False)


if __name__ == '__main__':
    main()
