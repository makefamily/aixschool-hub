"""kakao-notice: 표(CSV)를 읽어 결과 표와 화면(HTML)을 만든다. 아무 데도 보내거나 올리지 않는다. 작업 폴더는 --work 로 정한다."""
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
    return Path.cwd() / '톡방-공지시간표'


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

ITEMS = ROOT / '01_공지' / '이번주_공지홍보_샘플.csv'
TIMES = ROOT / '02_규칙' / '보낼시간표.csv'
ROOMS = ROOT / '02_규칙' / '방별규칙.csv'
QUIET = ROOT / '02_규칙' / '보내면안되는시간.csv'
TABLE = OUT / '발송시간표.csv'
COPY = OUT / '복사용_문안'
DAYS = '월화수목금토일'
LINK = re.compile(r'https?://[^\s<>"\']+')


def hm(text: str) -> int:
    """'08:35' 를 하루 시작부터 몇 분인지로 바꾼다."""
    try:
        h, m = str(text).strip().split(':')
        return int(h) * 60 + int(m)
    except ValueError:
        raise SystemExit(f"시각은 08:35 처럼 적어 주세요 (지금 적힌 값: '{text}').")


def label(t: datetime) -> str:
    return f'{t.month}월 {t.day}일({DAYS[t.weekday()]}) {t:%H:%M}'


def load_rules():
    times = {}
    for r in read_csv(TIMES):
        if r.get('종류') and r.get('보낼 시각'):
            hm(r['보낼 시각'])
            times.setdefault(r['종류'], []).append(r['보낼 시각'])
    if not times:
        raise SystemExit('02_규칙/보낼시간표.csv 에 종류와 보낼 시각을 한 줄 이상 적어 주세요 (예: 홍보, 11:30).')
    for kind in times:
        times[kind] = sorted(set(times[kind]), key=hm)
    rooms = {}
    for r in read_csv(ROOMS):
        if not r.get('방'):
            continue
        try:
            rooms[r['방']] = {'max': int(r['하루 최대']), 'must': r.get('꼭 넣을 말', ''), 'tag': r.get('링크 꼬리표', '') or 'kakao-room'}
        except (KeyError, ValueError):
            raise SystemExit('02_규칙/방별규칙.csv 의 하루 최대 칸에는 숫자만 적어 주세요.')
    quiet = [(hm(r['시작']), hm(r['끝'])) for r in read_csv(QUIET) if r.get('시작') and r.get('끝')]
    return times, rooms, quiet


def is_quiet(t: datetime, quiet) -> bool:
    m = t.hour * 60 + t.minute
    return any((s <= m < e) if s < e else (m >= s or m < e) for s, e in quiet)


def tag_links(text: str, tag: str, when: datetime):
    """링크 끝에 어느 방·어느 시각에서 눌렀는지 꼬리표(utm)를 붙인다. 이미 붙어 있으면 그대로 둔다."""
    count = [0]

    def one(m):
        raw = m.group(0)
        url = raw.rstrip('.,)!?')
        if 'utm_source=' in url:
            return raw
        count[0] += 1
        extra = urllib.parse.urlencode({'utm_source': 'kakao', 'utm_medium': 'openchat', 'utm_campaign': tag, 'utm_content': when.strftime('%m%d-%H%M')})
        return url + ('&' if '?' in url else '?') + extra + raw[len(url):]
    return LINK.sub(one, text), count[0]


def schedule(items, times, rooms, quiet):
    """종류별 시간표에 맞춰 자리를 잡는다. 겹치거나, 밤이거나, 방의 하루 최대가 차면 다음 가능한 시간으로 옮긴다."""
    rows, used, count = [], set(), {}
    for _, d in sorted(enumerate(items), key=lambda x: (x[1].get('날짜', ''), x[0])):
        row = dict(d, 상태='', 이유='', 보낼시각='', 보낼문안='')
        rows.append(row)
        room, kind, want = d.get('보낼 방', ''), d.get('종류', ''), d.get('원하는 시각', '')
        rule = rooms.get(room)
        if not rule:
            row.update(상태='뺌', 이유='방별규칙 표에 없는 방 (엉뚱한 방에 보낼 위험)')
            continue
        if kind not in times:
            row.update(상태='뺌', 이유=f"보낼시간표에 없는 종류 '{kind}'")
            continue
        try:
            day = datetime.strptime(d['날짜'], '%Y-%m-%d')
        except (KeyError, ValueError):
            raise SystemExit(f"날짜는 2026-10-05 처럼 적어 주세요 (지금 적힌 값: '{d.get('날짜', '')}').")
        start = day + timedelta(minutes=hm(want)) if want else day
        chosen, taken, full = None, [], False
        for n in range(14):
            cur = day + timedelta(days=n)
            if count.get((room, cur.date()), 0) >= rule['max']:
                full = True
                continue
            cands = ([start] if want and n == 0 else []) + [cur + timedelta(minutes=hm(t)) for t in times[kind]]
            for c in cands:
                if c < start or is_quiet(c, quiet):
                    continue
                if (room, c) in used:
                    taken.append(c)
                    continue
                chosen = c
                break
            if chosen:
                break
        if not chosen:
            row.update(상태='뺌', 이유='2주 안에 보낼 수 있는 시간이 없음 (시간표를 확인하세요)')
            continue
        used.add((room, chosen))
        count[(room, chosen.date())] = count.get((room, chosen.date()), 0) + 1
        why = []
        if want and is_quiet(start, quiet):
            why.append(f'{want} 은 보내면 안 되는 시간이라 옮김')
        elif full and chosen.date() > day.date():
            why.append(f"이 방은 하루 최대 {rule['max']}개가 차서 다음 날로 옮김")
        elif taken:
            why.append(f"{taken[0]:%H:%M} 은 이미 잡혀 있어서 옮김")
        else:
            why.append('원하는 시각 그대로' if want else '시간표대로')
        text = d.get('문안', '').replace('\\n', '\n').strip()
        if rule['must'] and rule['must'] not in text:
            text = f"{rule['must']} {text}"
            why.append('꼭 넣을 말 붙임')
        text, tagged = tag_links(text, rule['tag'], chosen)
        if tagged:
            why.append(f'링크 {tagged}개에 꼬리표')
        row.update(상태='예약', 보낼시각=chosen.strftime('%Y-%m-%d %H:%M'), 보낼문안=text, 이유=' · '.join(why), 옮김='옮김' in why[0])
    return rows


def checks(rows, rooms, quiet):
    booked = [r for r in rows if r['상태'] == '예약']
    per = {}
    for r in booked:
        key = (r['보낼 방'], r['보낼시각'][:10])
        per[key] = per.get(key, 0) + 1
    over = [f'{a} {b} {v}개' for (a, b), v in sorted(per.items()) if v > rooms.get(a, {}).get('max', 0)]
    night = [f"{r['보낼 방']} {r['보낼시각']}" for r in booked if is_quiet(datetime.strptime(r['보낼시각'], '%Y-%m-%d %H:%M'), quiet)]
    links = [u for r in booked for u in LINK.findall(r['보낼문안'])]
    bare = [u[:40] for u in links if 'utm_source=' not in u or 'utm_campaign=' not in u]
    span = ', '.join(f'{s // 60:02d}:{s % 60:02d}~{e // 60:02d}:{e % 60:02d}' for s, e in quiet) or '정해둔 시간 없음'
    return [
        (not over, '방마다 하루 최대를 지켰나', '넘친 방: ' + ', '.join(over) if over else '모든 방이 하루 최대 안'),
        (not night, '밤 시간에 잡힌 게 없나', '밤에 잡힌 것: ' + ', '.join(night) if night else f'{span} 사이에 잡힌 것 없음'),
        (not bare, '링크에 꼬리표가 붙었나', '꼬리표 없는 링크: ' + ', '.join(bare) if bare else f'링크 {len(links)}개 모두 꼬리표 있음'),
    ]


def write_copies(booked) -> list[Path]:
    """방마다 복사해 붙여넣을 문안 파일을 하나씩 만든다."""
    COPY.mkdir(parents=True, exist_ok=True)
    for old in COPY.glob('*.txt'):
        old.unlink()
    by_room = {}
    for r in booked:
        by_room.setdefault(r['보낼 방'], []).append(r)
    files = []
    for room, items in by_room.items():
        path = COPY / (re.sub(r'[\\/:*?"<>|]', '_', room) + '.txt')
        body = [f'{room} — 시간이 되면 아래 문안을 복사해서 이 방에 붙여넣으세요.', '']
        for r in items:
            body += [f"■ {label(datetime.strptime(r['보낼시각'], '%Y-%m-%d %H:%M'))} · {r['종류']}", r['보낼문안'], '']
        path.write_text('\n'.join(body), encoding='utf-8')
        files.append(path)
    return files


def make(open_browser=True):
    times, rooms, quiet = load_rules()
    rows = schedule(read_csv(ITEMS), times, rooms, quiet)
    booked = sorted([r for r in rows if r['상태'] == '예약'], key=lambda r: (r['보낼시각'], r['보낼 방']))
    write_csv(TABLE, ['보낼시각', '보낼 방', '종류', '보낼문안', '상태', '이유'], booked + [r for r in rows if r['상태'] != '예약'])
    files = write_copies(booked)
    results = checks(rows, rooms, quiet)
    cards = []
    for r in booked:
        when = datetime.strptime(r['보낼시각'], '%Y-%m-%d %H:%M')
        cards.append(f"<article><h2>{html.escape(label(when))} → {html.escape(r['보낼 방'])}</h2><small>{html.escape(r['종류'])} · {html.escape(r['이유'])}</small>"
                     f"<div class='box'><b>복사할 문안</b>{html.escape(r['보낼문안'])}</div></article>")
    skipped = [(f"{r.get('보낼 방', '')} · {r.get('문안', '')[:24]}", r['이유']) for r in rows if r['상태'] != '예약']
    moved = sum(1 for r in booked if r.get('옮김'))
    page = board(f'카톡 발송 시간표 {len(booked)}개', '시간이 되면 방별 문안 파일(결과/복사용_문안)을 열어 복사해서 붙여넣으세요', results, cards, skipped, '발송시간표.html')
    return finish(f'공지·홍보 {len(rows)}개를 읽었습니다. 발송 시간표 {len(booked)}개(그중 옮긴 것 {moved}개), 뺀 것 {len(rows) - len(booked)}개. 방별 문안 파일 {len(files)}개.',
                  results, page, open_browser)


def main():
    p = argparse.ArgumentParser(description='카톡 공지·홍보 발송 시간표 만들기')
    p.add_argument('--work', help='작업 폴더')
    p.add_argument('--no-open', action='store_true', help='결과 화면을 열지 않음')
    a = p.parse_args()
    make(False)


if __name__ == '__main__':
    main()
