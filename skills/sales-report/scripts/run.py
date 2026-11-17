"""sales-report: 표(CSV)를 읽어 결과 표와 화면(HTML)을 만든다. 아무 데도 보내거나 올리지 않는다. 작업 폴더는 --work 로 정한다."""
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
    return Path.cwd() / '매출-보고'


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

IN_DIR = ROOT / '01_주문'
SAMPLE = '주문내역_샘플.csv'
GROUPS = ROOT / '02_규칙' / '상품묶음.csv'
DROPS = ROOT / '02_규칙' / '빼는상태.csv'
GOALS = ROOT / '02_규칙' / '목표.csv'
DAYNAME = '월화수목금토일'
BASE_DROP = ('취소', '환불', '반품')  # 표를 고쳐도 이 말이 든 주문은 매출에 남으면 안 된다
# 쇼핑몰마다 칸 이름이 조금씩 달라서, 흔한 이름을 같이 찾아본다.
COLS = {
    '주문일시': ['주문일시', '주문일', '주문일자', '결제일시', '결제일'],
    '상품명': ['상품명', '상품명(한국어 쇼핑몰)', '주문상품명'],
    '옵션': ['옵션', '상품옵션', '옵션정보'],
    '수량': ['수량', '주문수량'],
    '결제금액': ['결제금액', '상품구매금액', '상품별 결제금액', '실결제금액', '총 결제금액'],
    '주문상태': ['주문상태', '주문 상태', '주문처리상태'],
}
NEED = ['주문일시', '상품명', '결제금액', '주문상태']


def won(x) -> str:
    return f'{int(round(x)):,}원'


def label(d) -> str:
    return f'{d.month}월 {d.day}일({DAYNAME[d.weekday()]})'


def pick_file() -> Path:
    """01_주문 폴더에 내 주문 파일이 있으면 그걸(가장 최근 것), 없으면 샘플을 읽는다."""
    files = sorted(IN_DIR.glob('*.csv'))
    mine = [f for f in files if f.name != SAMPLE]
    if mine:
        return max(mine, key=lambda p: p.stat().st_mtime)
    if files:
        return files[0]
    raise SystemExit('01_주문 폴더에 주문 파일(CSV)이 없습니다. 쇼핑몰 관리자 화면에서 주문 내역을 내려받아 넣어 주세요.')


def to_day(text):
    m = re.match(r'\s*(\d{4})[-./년 ]+(\d{1,2})[-./월 ]+(\d{1,2})', text or '')
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def load_orders(path: Path) -> list[dict]:
    raw = read_csv(path)
    if not raw:
        raise SystemExit(f'{path.name} 에 주문이 한 줄도 없습니다.')
    keys = list(raw[0].keys())
    use = {n: next((c for c in names if c in keys), None) for n, names in COLS.items()}
    miss = [n for n in NEED if not use[n]]
    if miss:
        raise SystemExit(f"{path.name} 에서 {', '.join(miss)} 칸을 찾지 못했습니다. 이 파일에 있는 칸: {', '.join(keys)}. "
                         "AI에게 '이 파일 칸 이름에 맞춰줘'라고 하세요.")
    rows = []
    for r in raw:
        o = {n: (r.get(c, '') if c else '') for n, c in use.items()}
        o['날짜'] = to_day(o['주문일시'])
        o['금액'] = number(o['결제금액'])
        rows.append(o)
    return rows


def group_of(o, groups) -> str:
    """위에서부터 먼저 걸리는 줄이 이긴다. 아무 줄에도 안 걸리면 '기타'."""
    text = f"{o['상품명']} {o['옵션']}"
    for g in groups:
        word = g.get('이 말이 들어가면', '')
        if word and word in text:
            return g.get('보고서 이름') or word
    return '기타'


def report(orders, groups, drops, goals):
    good = [o for o in orders if o['날짜']]
    if not good:
        raise SystemExit('주문일시를 읽을 수 있는 주문이 없습니다. 날짜가 2026-10-07 처럼 적혀 있는지 확인해 주세요.')
    day = max(o['날짜'] for o in good)  # 보고 기준일 = 파일에서 가장 늦은 주문 날짜
    week0 = day - timedelta(days=day.weekday())
    month0 = day.replace(day=1)
    start = min(week0, month0)
    periods = [('오늘', day), ('이번 주', week0), ('이번 달', month0)]
    kept, skipped = [], []
    for o in orders:
        o['묶음'] = group_of(o, groups)
        hit = next((w for w in drops if w in o['주문상태']), None)
        if not o['날짜']:
            skipped.append((o['상품명'][:30], f"주문일시를 읽지 못함 ('{o['주문일시']}')"))
        elif hit:
            o['이유'] = o['주문상태']
            skipped.append((o['상품명'][:30], f"{o['주문상태']} · 빼는 주문상태 '{hit}'"))
        elif not start <= o['날짜'] <= day:
            skipped.append((o['상품명'][:30], f"보고 기간 밖 ({o['날짜']})"))
        else:
            kept.append(o)
    table = {}
    for name in goals:
        table.setdefault(name, {p: [0.0, 0] for p, _ in periods})
    for o in kept:
        t = table.setdefault(o['묶음'], {p: [0.0, 0] for p, _ in periods})
        for p, s in periods:
            if s <= o['날짜']:
                t[p][0] += o['금액']
                t[p][1] += 1
    total = {p: [sum(o['금액'] for o in kept if s <= o['날짜']), sum(1 for o in kept if s <= o['날짜'])] for p, s in periods}
    days = [start + timedelta(days=i) for i in range((day - start).days + 1)]
    daily = {d: [0.0, 0] for d in days}
    for o in kept:
        daily[o['날짜']][0] += o['금액']
        daily[o['날짜']][1] += 1
    return dict(day=day, start=start, kept=kept, skipped=skipped, table=table, total=total, daily=daily,
                dropped=[o for o in orders if o.get('이유')], bad=[o for o in orders if not o['날짜']])


def checks(R, drops):
    left = [o for o in R['kept'] if any(w in o['주문상태'] for w in set(drops) | set(BASE_DROP))]
    dropped = R['dropped']
    kinds = {}
    for o in dropped:
        kinds[o['이유']] = kinds.get(o['이유'], 0) + 1
    diff = [p for p, (amt, cnt) in R['total'].items()
            if round(sum(t[p][0] for t in R['table'].values())) != round(amt) or sum(t[p][1] for t in R['table'].values()) != cnt]
    days = list(R['daily'])
    gap = [d for a, d in zip(days, days[1:]) if (d - a).days != 1]
    zero = [d for d, (amt, cnt) in R['daily'].items() if cnt == 0]
    month = R['total']['이번 달'][0]
    return [
        (not left, '취소·환불·반품 주문을 뺐나',
         '매출에 남은 주문: ' + ', '.join(o['상품명'][:15] + ' ' + o['주문상태'] for o in left) if left
         else f'뺀 주문 {len(dropped)}건 (' + ' · '.join(f'{k} {v}' for k, v in kinds.items()) + ')' if dropped else '뺄 주문이 없었음'),
        (not diff, '상품별 합계가 전체 합계와 맞나',
         '안 맞는 기간: ' + ', '.join(diff) if diff else f'이번 달 상품별 합 {won(month)} = 전체 {won(month)}'),
        (not gap and not R['bad'], '날짜가 빠진 날이 없나',
         f"날짜를 못 읽은 주문 {len(R['bad'])}건" if R['bad'] else '빠진 날짜: ' + ', '.join(map(str, gap)) if gap
         else f"{label(days[0])}~{label(days[-1])} {len(days)}일 모두 있음" + (f' · 주문 0건인 날 {len(zero)}일도 0으로 표시' if zero else '')),
    ]


def morning(R, goals) -> str:
    day, t, table = R['day'], R['total'], R['table']
    import calendar
    passed = day.day / calendar.monthrange(day.year, day.month)[1] * 100
    goal = sum(goals.values())
    lines = [f"[{label(day)} 매출]",
             f"오늘 {t['오늘'][1]}건 {won(t['오늘'][0])}, 이번 주 {t['이번 주'][1]}건 {won(t['이번 주'][0])}."]
    if goal:
        lines.append(f"이번 달 {won(t['이번 달'][0])}, 목표의 {t['이번 달'][0] / goal * 100:.0f}%입니다. (이번 달은 {passed:.0f}% 지났어요)")
    else:
        lines.append(f"이번 달 {won(t['이번 달'][0])}.")
    best = max(table.items(), key=lambda kv: kv[1]['이번 달'][0], default=None)
    if best and best[1]['이번 달'][0]:
        lines.append(f"이번 달 가장 많이 판 상품은 {best[0]}입니다.")
    slow = sorted(((v['이번 달'][0] / goals[k] * 100, k) for k, v in table.items() if goals.get(k)), key=lambda x: x[0])
    if slow and slow[0][0] < passed:
        lines.append(f"목표보다 느린 상품: {slow[0][1]} ({slow[0][0]:.0f}%).")
    return '\n'.join(lines)


def cell(v) -> str:
    return f"{won(v[0])}<small> · {v[1]}건</small>"


def make(open_browser=True):
    path = pick_file()
    orders = load_orders(path)
    groups = read_csv(GROUPS)
    drops = [d['빼는 주문상태'] for d in read_csv(DROPS) if d.get('빼는 주문상태')]
    goals = {g['보고서 이름']: number(g.get('이번 달 목표(원)')) for g in read_csv(GOALS) if g.get('보고서 이름')}
    R = report(orders, groups, drops, goals)
    results = checks(R, drops)
    note = morning(R, goals)
    OUT.mkdir(exist_ok=True)
    (OUT / '아침요약.txt').write_text(note + '\n', encoding='utf-8')
    names = sorted(R['table'], key=lambda k: (k == '기타', -R['table'][k]['이번 달'][0]))
    prod = []
    for k in names:
        v = R['table'][k]
        pct = f"{v['이번 달'][0] / goals[k] * 100:.0f}%" if goals.get(k) else '-'
        prod.append({'상품': k, '오늘 금액': int(v['오늘'][0]), '오늘 건수': v['오늘'][1], '이번 주 금액': int(v['이번 주'][0]), '이번 주 건수': v['이번 주'][1],
                     '이번 달 금액': int(v['이번 달'][0]), '이번 달 건수': v['이번 달'][1], '이번 달 목표': int(goals.get(k, 0)), '목표 대비': pct})
    write_csv(OUT / '상품별매출.csv', list(prod[0]) if prod else ['상품'], prod)
    write_csv(OUT / '날짜별매출.csv', ['날짜', '건수', '금액'], [{'날짜': str(d), '건수': c, '금액': int(a)} for d, (a, c) in R['daily'].items()])
    rows = ''.join(f"<tr><td>{html.escape(p['상품'])}</td><td>{cell(R['table'][p['상품']]['오늘'])}</td><td>{cell(R['table'][p['상품']]['이번 주'])}</td>"
                   f"<td>{cell(R['table'][p['상품']]['이번 달'])}</td><td><b>{p['목표 대비']}</b></td></tr>" for p in prod)
    t = R['total']
    rows += f"<tr><th>전체</th><th>{cell(t['오늘'])}</th><th>{cell(t['이번 주'])}</th><th>{cell(t['이번 달'])}</th><th></th></tr>"
    days = ''.join(f"<tr><td>{label(d)}</td><td>{c}건</td><td>{won(a)}</td></tr>" for d, (a, c) in R['daily'].items())
    cards = [f"<article><h2>사장님 아침 요약</h2><small>결과/아침요약.txt · 복사해서 카톡에 붙여넣으면 됩니다</small><div class='box'>{html.escape(note)}</div></article>",
             f"<article><h2>상품별 매출</h2><small>목표 대비 = 이번 달 금액 ÷ 02_규칙/목표.csv</small><table><tr><th>상품</th><th>오늘</th><th>이번 주</th><th>이번 달</th><th>목표 대비</th></tr>{rows}</table></article>",
             f"<article><h2>날짜별 매출</h2><small>주문이 없는 날도 0으로 적습니다</small><table><tr><th>날짜</th><th>건수</th><th>금액</th></tr>{days}</table></article>"]
    page = board(f"{label(R['day'])} 매출 보고", f'{path.name} · 취소·환불은 빼고 · 상품별로 묶어서 · 주문 없는 날도 0으로', results, cards, R['skipped'], '매출보고.html')
    return finish(f"주문 {len(orders)}건을 읽었습니다 ({path.name}). 매출로 센 주문 {len(R['kept'])}건, 뺀 주문 {len(R['skipped'])}건.", results, page, open_browser)


def main():
    p = argparse.ArgumentParser(description='쇼핑몰 매출 보고')
    p.add_argument('--work', help='작업 폴더')
    p.add_argument('--no-open', action='store_true', help='결과 화면을 열지 않음')
    a = p.parse_args()
    make(False)


if __name__ == '__main__':
    main()
