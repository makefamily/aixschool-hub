"""fix-playbook: 표(CSV)를 읽어 결과 표와 화면(HTML)을 만든다. 아무 데도 보내거나 올리지 않는다. 작업 폴더는 --work 로 정한다."""
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
    return Path.cwd() / '문제-조치카드'


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

REPORTS = ROOT / '01_신고' / '문제신고_샘플.csv'
PLAYBOOK = ROOT / '02_규칙' / '조치표.csv'
RISKY = ROOT / '02_규칙' / '위험조치.csv'
TODAY = OUT / '오늘처리목록.csv'
MEMO = OUT / '담당자별_전달문.txt'
STEPS = ['먼저 해볼 것', '두 번째', '세 번째']
NEW = '새 증상'
NEW_OWNER = '조치표 관리자'


def squash(text) -> str:
    """띄어쓰기를 빼고 비교한다 ('자동문자' 와 '자동 문자' 를 같게 본다)."""
    return re.sub(r'\s+', '', text or '')


def clock(rep) -> str:
    t = rep.get('신고 시각', '')
    return t[11:16] if len(t) >= 16 else t


def playbook() -> list[dict]:
    rows = [r for r in read_csv(PLAYBOOK) if r.get('증상 단어')]
    if not rows:
        raise SystemExit('02_규칙/조치표.csv 에 증상 단어를 한 줄 이상 적어 주세요 (예: 프린터/인쇄).')
    return rows


def find(symptom, rows):
    """증상 문장에 들어 있는 증상 단어 중 가장 긴 것이 있는 줄을 고른다."""
    s, best, size = squash(symptom), None, 0
    for r in rows:
        for word in r['증상 단어'].split('/'):
            w = squash(word)
            if w and w in s and len(w) > size:
                best, size = r, len(w)
    return best


def danger(step, risky):
    return next((w for w in risky if w.get('위험한 말') and squash(w['위험한 말']) in squash(step)), None)


def group(reports, rows, risky):
    """같은 문제로 들어온 신고는 카드 한 장에 묶는다. 표에 없는 증상은 새 증상 목록으로."""
    cards, new = {}, []
    for rep in sorted(reports, key=lambda x: x.get('신고 시각', '')):
        hit = find(rep.get('증상', ''), rows)
        if not hit:
            new.append(rep)
            continue
        name = hit.get('문제') or hit['증상 단어']
        card = cards.get(name)
        if not card:
            steps = []
            for i, col in enumerate(STEPS, 1):
                todo = hit.get(col, '')
                if todo:
                    w = danger(todo, risky)
                    steps.append(dict(순서=i, 할일=todo, 사람확인=bool(w), 이유=w.get('이유', '') if w else ''))
            card = cards[name] = dict(문제=name, 담당=hit.get('담당', ''), 조치=steps, 신고=[], 줄=[])
        card['신고'].append(rep)
        card['줄'].append(hit)
    order = sorted(cards.values(), key=lambda c: (-len(c['신고']), c['신고'][0].get('신고 시각', '')))
    return order, new


def checks(reports, cards, new, risky):
    placed = sum(len(c['신고']) for c in cards) + len(new)
    empty = [c['문제'] for c in cards if not c['조치'] or not c['담당']]
    missed = [f"{c['문제']} {s['순서']}번" for c in cards for s in c['조치'] if danger(s['할일'], risky) and not s['사람확인']]
    first = [c['문제'] for c in cards if c['조치'] and c['조치'][0]['사람확인']]
    marked = sum(s['사람확인'] for c in cards for s in c['조치'])
    split = [c['문제'] for c in cards if any([h.get(k, '') for k in STEPS + ['담당']] != [c['줄'][0].get(k, '') for k in STEPS + ['담당']] for h in c['줄'])]
    biggest = cards[0] if cards else None
    ok1 = placed == len(reports) and not empty
    ok2 = bool(risky) and not missed and not first
    if not risky:
        d2 = '02_규칙/위험조치.csv 가 비어 있음'
    elif missed or first:
        d2 = ('표시 빠짐: ' + ', '.join(missed) + ' ' if missed else '') + ('첫 번째 조치가 위험함: ' + ', '.join(first) if first else '')
    else:
        d2 = f"위험한 조치 {marked}개 모두 '사람 확인' · 첫 번째 조치로 두지 않음"
    return [
        (ok1, '모든 신고에 조치나 담당이 정해졌나',
         f'신고 {len(reports)}건 모두 · 조치 카드로 {placed - len(new)}건, 새 증상 {len(new)}건' if ok1 else '담당이나 조치가 빈 문제: ' + ', '.join(empty or ['빠진 신고 있음'])),
        (ok2, '위험한 조치에 사람 확인 표시가 붙었나', d2.strip()),
        (not split, '같은 증상을 한 번에 묶었나',
         f"신고 {placed - len(new)}건 → 카드 {len(cards)}장" + (f" ({biggest['문제']} {len(biggest['신고'])}건을 한 장으로)" if biggest and len(biggest['신고']) > 1 else '')
         if not split else '같은 문제 이름에 조치가 다른 줄: ' + ', '.join(split)),
    ]


def card_html(c) -> str:
    reps = ''.join(f"<li>{html.escape(clock(r))} · {html.escape(r.get('신고한 사람', ''))} — {html.escape(r.get('증상', ''))}</li>" for r in c['신고'])
    boxes = ''
    for s in c['조치']:
        if s['사람확인']:
            head = f"{s['순서']}. 사람 확인 먼저 — {html.escape(s['이유'])}"
            style = " style='background:#fdecea'"
        else:
            head = f"{s['순서']}. {STEPS[s['순서'] - 1]}"
            style = ''
        boxes += f"<div class='box'{style}><b>{head}</b>{html.escape(s['할일'])}</div>"
    tag = " · 사람 확인 필요한 조치 있음" if any(s['사람확인'] for s in c['조치']) else ''
    return (f"<article><small>신고 {len(c['신고'])}건 · 담당 {html.escape(c['담당'])}{tag}</small><h2>{html.escape(c['문제'])}</h2>"
            f"<ul style='margin:4px 0 0;padding-left:18px;color:#4b5563;font-size:14px'>{reps}</ul>{boxes}</article>")


def new_html(new) -> str:
    if not new:
        return ''
    items = ''.join(f"<li>{html.escape(clock(r))} · {html.escape(r.get('신고한 사람', ''))} — {html.escape(r.get('증상', ''))}</li>" for r in new)
    return (f"<article style='border-left-color:#9ca3af'><small>{NEW} {len(new)}건 · 오류가 아니라 결과입니다</small><h2>조치표에 한 줄 추가가 필요합니다</h2>"
            f"<ul style='margin:4px 0;padding-left:18px'>{items}</ul><p>02_규칙/조치표.csv 에 증상 단어와 먼저 해볼 조치를 적으면 다음부터 카드가 나옵니다.</p></article>")


def memo(cards, new) -> str:
    lines = ['담당자별 전달문 — 복사해서 메신저에 붙여넣으세요.', '(아직 아무에게도 보내지 않았습니다)', '']
    owners = []
    for c in cards:
        if c['담당'] not in owners:
            owners.append(c['담당'])
    for owner in owners:
        mine = [c for c in cards if c['담당'] == owner]
        lines.append(f'[{owner}] 오늘 처리할 것 {len(mine)}건')
        for i, c in enumerate(mine, 1):
            who = ', '.join(f"{r.get('신고한 사람', '')} {clock(r)}" for r in c['신고'])
            lines.append(f"{i}. {c['문제']} — 신고 {len(c['신고'])}건 ({who})")
            for s in c['조치']:
                warn = f"  <- 하기 전에 사람 확인 ({s['이유']})" if s['사람확인'] else ''
                lines.append(f"   {s['순서']}) {s['할일']}{warn}")
        lines.append('')
    if new:
        lines.append(f'[{NEW_OWNER}] {NEW} {len(new)}건 — 조치표에 한 줄씩 추가해 주세요')
        for r in new:
            lines.append(f"- {r.get('증상', '')} ({r.get('신고한 사람', '')} {clock(r)})")
    return '\n'.join(lines) + '\n'


def make(open_browser=True):
    reports = [r for r in read_csv(REPORTS) if r.get('증상')]
    rows, risky = playbook(), [w for w in read_csv(RISKY) if w.get('위험한 말')]
    cards, new = group(reports, rows, risky)
    results = checks(reports, cards, new, risky)
    today = []
    for c in cards:
        step = {STEPS[s['순서'] - 1]: s['할일'] for s in c['조치']}
        today.append(dict(step, 순서=len(today) + 1, 문제=c['문제'], 담당=c['담당'], **{
            '신고 건수': len(c['신고']), '신고한 사람': ', '.join(f"{r.get('신고한 사람', '')} {clock(r)}" for r in c['신고']),
            '사람 확인': ' / '.join(f"{s['순서']}번: {s['이유']}" for s in c['조치'] if s['사람확인'])}))
    for r in new:
        today.append({'순서': len(today) + 1, '문제': NEW, '담당': NEW_OWNER, '신고 건수': 1, '신고한 사람': f"{r.get('신고한 사람', '')} {clock(r)}",
                      '먼저 해볼 것': '조치표에 한 줄 추가 — ' + r.get('증상', '')})
    write_csv(TODAY, ['순서', '문제', '신고 건수', '신고한 사람', '먼저 해볼 것', '두 번째', '세 번째', '사람 확인', '담당'], today)
    MEMO.write_text(memo(cards, new), encoding='utf-8')
    page = board(f'조치 카드 {len(cards)}장', f'신고 {len(reports)}건 · 같은 증상은 한 장으로 묶고, 되돌릴 수 없는 조치에는 사람 확인을 붙였습니다',
                 results, [card_html(c) for c in cards] + [new_html(new)], [], '조치카드.html')
    summary = f'신고 {len(reports)}건을 읽었습니다. 조치 카드 {len(cards)}장, {NEW} {len(new)}건.'
    fails = finish(summary, results, page, open_browser)
    say(f'오늘 처리 목록: {TODAY}')
    say(f'담당자별 전달문(복사해서 붙여넣기용): {MEMO}')
    return fails


def main():
    p = argparse.ArgumentParser(description='문제 신고를 조치 카드로 정리')
    p.add_argument('--work', help='작업 폴더')
    p.add_argument('--no-open', action='store_true', help='결과 화면을 열지 않음')
    a = p.parse_args()
    make(False)


if __name__ == '__main__':
    main()
