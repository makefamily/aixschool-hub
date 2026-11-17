"""reference-picker: 표(CSV)를 읽어 결과 표와 화면(HTML)을 만든다. 아무 데도 보내거나 올리지 않는다. 작업 폴더는 --work 로 정한다."""
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
    return Path.cwd() / '기획후보-보드'


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

SAMPLE = ROOT / '01_레퍼런스' / '레퍼런스_영상_샘플.csv'
FETCHED = ROOT / '01_레퍼런스' / '유튜브_검색결과.csv'
BASIS = ROOT / '02_규칙' / '고르는기준.csv'
TOPIC = ROOT / '02_규칙' / '내주제.csv'
TRAITS = ROOT / '02_규칙' / '제목특징.csv'
BOARD = OUT / '기획후보보드.csv'
HEADER = ['제목', '채널', '조회수', '구독자수', '올린 날짜', '길이', '모은 날짜', '주소']
NEED = {'떡상 기준(배)': 'ratio', '최근 며칠 안': 'days', '가장 짧은 길이(분)': 'min_len', '한 채널 최대': 'per_channel'}


def basis() -> dict:
    got = {r.get('기준', ''): r.get('값', '') for r in read_csv(BASIS)}
    out = {}
    for name, key in NEED.items():
        if name not in got:
            raise SystemExit(f"02_규칙/고르는기준.csv 에 '{name}' 줄이 없습니다. 줄은 지우지 말고 값만 바꿔 주세요.")
        try:
            out[key] = float(got[name].replace(',', ''))
        except ValueError:
            raise SystemExit(f"02_규칙/고르는기준.csv 의 '{name}' 값에는 숫자만 적어 주세요 (지금: {got[name]}).")
    return out


def keywords() -> list[str]:
    out = [r['키워드'] for r in read_csv(TOPIC) if r.get('키워드')]
    if not out:
        raise SystemExit('02_규칙/내주제.csv 에 키워드를 한 줄 이상 적어 주세요 (예: 자동화).')
    return out


def traits() -> list[tuple[str, list[str]]]:
    return [(r['특징'], [w.strip() for w in r.get('찾는 말', '').split('/') if w.strip()]) for r in read_csv(TRAITS) if r.get('특징')]


def found(title: str, words: list[str]):
    """제목에서 특징을 보여주는 말을 찾는다. [숫자] 는 아무 숫자."""
    for w in words:
        if w == '[숫자]':
            m = re.search(r'\d+', title)
            if m:
                return m.group()
        elif w.lower() in title.lower():
            return w
    return None


def minutes(text) -> float:
    """'11:42', '1:02:03' 같은 길이를 분으로. 숫자만 있으면 분으로 본다."""
    parts = [number(p) for p in str(text or '0').split(':')]
    if len(parts) == 1:
        return parts[0]
    s = 0.0
    for p in parts:
        s = s * 60 + p
    return s / 60


def pick(videos, b, kws, trs):
    rows = []
    for v in videos:
        row = dict(v, 점수='', 특징='', 상태='뺌', 이유='', 올린지='', 순위='', _marks=[])
        rows.append(row)
        title = v.get('제목', '')
        try:
            got = datetime.strptime(v.get('모은 날짜') or date.today().isoformat(), '%Y-%m-%d')
            days = (got - datetime.strptime(v.get('올린 날짜', ''), '%Y-%m-%d')).days
        except ValueError:
            row['이유'] = '날짜를 읽을 수 없음 (2026-10-05 처럼 적어 주세요)'
            continue
        views, subs = number(v.get('조회수')), number(v.get('구독자수'))
        row['올린지'] = days
        if subs <= 0:
            row['이유'] = '구독자수를 알 수 없음 (채널이 숨겨 둠)'
            continue
        score = views / subs
        row['점수'] = f'{score:.1f}'
        if minutes(v.get('길이')) < b['min_len']:
            row['이유'] = f"길이 {v.get('길이')} — {b['min_len']:g}분보다 짧음 (쇼츠)"
        elif days > b['days']:
            row['이유'] = f"{days}일 전 영상 — {b['days']:g}일보다 오래됨"
        elif not any(k.lower() in title.lower() for k in kws):
            row['이유'] = '내 주제 키워드가 제목에 없음'
        elif score < b['ratio']:
            row['이유'] = f"조회수가 구독자의 {score:.1f}배 — 떡상 기준 {b['ratio']:g}배보다 낮음"
        else:
            row['상태'] = '후보'
    per = {}
    rank = 0
    for r in sorted([r for r in rows if r['상태'] == '후보'], key=lambda r: -float(r['점수'])):
        ch = r.get('채널', '')
        per[ch] = per.get(ch, 0) + 1
        if per[ch] > b['per_channel']:
            r.update(상태='뺌', 이유=f"같은 채널 {per[ch]}번째 — 한 채널 최대 {b['per_channel']:g}개")
            continue
        rank += 1
        marks = [(name, w) for name, words in trs for w in [found(r.get('제목', ''), words)] if w]
        r.update(상태='보드', 순위=rank, 특징=' · '.join(n for n, _ in marks), _marks=marks, 이유=f"조회수가 구독자의 {r['점수']}배")
    return rows


def checks(rows, b, kws):
    on = [r for r in rows if r['상태'] == '보드']
    old = [r['제목'][:16] for r in on if int(r['올린지']) > b['days']]
    off = [r['제목'][:16] for r in on if not any(k.lower() in r['제목'].lower() for k in kws)]
    per = {}
    for r in on:
        per[r.get('채널', '')] = per.get(r.get('채널', ''), 0) + 1
    crowded = [f'{c} {n}개' for c, n in per.items() if n > b['per_channel']]
    return [
        (not old, '오래된 영상이 없나', '오래된 영상: ' + ', '.join(old) if old else f"모두 {b['days']:g}일 안에 올라온 영상"),
        (not off, '내 주제와 맞나', '주제 밖 영상: ' + ', '.join(off) if off else '모두 제목에 내 주제 키워드가 있음'),
        (not crowded, '한 채널에 몰리지 않았나', '몰린 채널: ' + ', '.join(crowded) if crowded else f"채널 {len(per)}곳 · 한 채널 최대 {b['per_channel']:g}개"),
    ]


def make(path, open_browser=True):
    b, kws, trs = basis(), keywords(), traits()
    rows = pick(read_csv(path), b, kws, trs)
    on = sorted([r for r in rows if r['상태'] == '보드'], key=lambda r: r['순위'])
    write_csv(BOARD, ['순위', '제목', '채널', '점수', '조회수', '구독자수', '올린지', '길이', '특징', '상태', '이유', '주소'], on + [r for r in rows if r['상태'] != '보드'])
    results = checks(rows, b, kws)
    tally = {}
    for r in on:
        for n, _ in r['_marks']:
            tally[n] = tally.get(n, 0) + 1
    top = sorted(tally.items(), key=lambda x: -x[1])
    if on:
        common = ' · '.join(f'{n} {c}개' for n, c in top) or '제목특징 표에 걸린 것이 없습니다'
        tip = (f"다음 기획 제목에는 '{top[0][0]}'" + (f", '{top[1][0]}'" if len(top) > 1 else '') + ' 부터 넣어 보세요.') if top else '눈에 띄는 점이 있으면 제목특징 표에 한 줄 더하세요.'
        cards = [f"<article><h2>보드 {len(on)}개 제목의 공통점</h2><p>{html.escape(common)}</p><div class='box'><b>기획할 때</b>{html.escape(tip)}</div></article>"]
    else:
        cards = ["<article><h2>보드에 올라간 영상이 없습니다</h2><p>아래 '빠진 것'에서 이유를 보고 02_규칙 표를 고쳐 보세요.</p></article>"]
    for r in on:
        t = html.escape(r['제목'])
        if r.get('주소', '').startswith('http'):
            t = f"<a href='{html.escape(r['주소'])}'>{t}</a>"
        why = ' · '.join(f"{n}('{w}')" for n, w in r['_marks']) or '제목특징 표에 걸린 말이 없습니다'
        cards.append(f"<article><small>{r['순위']}위 · {html.escape(r.get('채널', ''))} · {r['올린지']}일 전 · 길이 {html.escape(r.get('길이', ''))}</small><h2>{t}</h2>"
                     f"<p>조회수 {number(r['조회수']):,.0f} ÷ 구독자 {number(r['구독자수']):,.0f} = <b>{r['점수']}배</b></p>"
                     f"<div class='box'><b>왜 잘됐나 · 제목에서 보이는 특징</b>{html.escape(why)}</div></article>")
    skipped = [(r.get('제목', '')[:30], r['이유']) for r in rows if r['상태'] != '보드']
    page = board(f'기획 후보 보드 {len(on)}개', f"영상 {len(rows)}개 중 조회수가 구독자수의 {b['ratio']:g}배 넘은 것 · 점수 높은 순", results, cards, skipped, '기획후보보드.html')
    return finish(f'영상 {len(rows)}개를 읽었습니다. 기획 후보 {len(on)}개, 뺀 영상 {len(rows) - len(on)}개.', results, page, open_browser)


# ---------------------------------------------------------------- 실제로 모으기 (유튜브 데이터 API, 읽기만)
def main():
    p = argparse.ArgumentParser(description='잘된 영상으로 기획 후보 보드 만들기')
    p.add_argument('--work', help='작업 폴더')
    p.add_argument('--file', help='01_레퍼런스 안의 다른 CSV 이름')
    p.add_argument('--no-open', action='store_true')
    a = p.parse_args()
    if a.file:
        path = Path(a.file) if Path(a.file).exists() else ROOT / '01_레퍼런스' / a.file
    else:
        path = SAMPLE
    make(path, False)


if __name__ == '__main__':
    main()
