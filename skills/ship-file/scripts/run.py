"""ship-file: 표(CSV)를 읽어 결과 표와 화면(HTML)을 만든다. 아무 데도 보내거나 올리지 않는다. 작업 폴더는 --work 로 정한다."""
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
    return Path.cwd() / '출고-파일'


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

ORDERS = ROOT / '01_주문' / '주문_샘플.csv'
PACK = ROOT / '02_규칙' / '포장규칙.csv'
REMOTE = ROOT / '02_규칙' / '도서산간.csv'
HOLD = ROOT / '02_규칙' / '보류조건.csv'
UPLOAD = OUT / '택배사_업로드.csv'
HELD = OUT / '보류목록.csv'
SHOP = OUT / '쇼핑몰_송장등록.csv'
# 택배사 일괄 업로드 양식에서 흔히 쓰는 칸 이름. 내 택배사 양식이 다르면 이 줄만 바꾼다.
UPLOAD_HEADER = ['받는분', '받는분전화', '우편번호', '받는분주소', '품목명', '박스수량', '박스크기', '배송메세지', '도서산간', '추가배송비', '주문번호']


def same_place(o) -> tuple:
    """같은 사람 + 같은 주소면 한 박스로 묶는다. 띄어쓰기 차이는 같은 것으로 본다."""
    return (re.sub(r'\s+', '', o.get('받는 사람', '')), re.sub(r'\s+', '', o.get('주소', '')))


def box_rank(name: str) -> int:
    """박스 이름의 숫자가 클수록 큰 박스 (우체국 박스처럼 1호, 2호, 3호…)."""
    m = re.search(r'\d+', name)
    return int(m.group()) if m else 0


def pack_rules() -> dict:
    out = {}
    for r in read_csv(PACK):
        try:
            most = int(number(r['한 박스 최대 개수']))
            out[r['상품']] = (r['박스'], most)
        except (KeyError, ValueError):
            raise SystemExit('02_규칙/포장규칙.csv 에 상품·박스·한 박스 최대 개수 칸이 있어야 합니다.')
        if most < 1:
            raise SystemExit(f"02_규칙/포장규칙.csv 의 '{r['상품']}' 한 박스 최대 개수는 1 이상이어야 합니다.")
    return out


def remote_rules() -> list:
    out = []
    for r in read_csv(REMOTE):
        try:
            out.append((int(r['우편번호 시작']), int(r['우편번호 끝']), r['지역'], int(number(r.get('추가 배송비', 0)))))
        except (KeyError, ValueError):
            raise SystemExit('02_규칙/도서산간.csv 의 우편번호 칸에는 다섯 자리 숫자만 적어 주세요.')
    return out


def remote_of(zipcode: str, remote: list):
    z = re.sub(r'\D', '', zipcode or '')
    if not z:
        return None
    return next(((name, fee) for a, b, name, fee in remote if a <= int(z) <= b), None)


def hold_cols(orders: list) -> list:
    cols = [r['비어 있으면 보류할 칸'] for r in read_csv(HOLD) if r.get('비어 있으면 보류할 칸')]
    missing = [c for c in cols if orders and c not in orders[0]]
    if missing:
        raise SystemExit('02_규칙/보류조건.csv 의 칸 이름이 주문 파일에 없습니다: ' + ', '.join(missing))
    return cols


def plan(orders, pack, remote, cols):
    held, groups = [], {}
    for o in orders:
        empty = [c for c in cols if not o.get(c)]
        qty = int(number(o.get('수량'), 0))
        if empty:
            held.append(dict(o, 이유=' · '.join(f'{c} 비어 있음' for c in empty)))
        elif o.get('상품') not in pack:
            held.append(dict(o, 이유='포장규칙에 없는 상품'))
        elif qty < 1:
            held.append(dict(o, 이유='수량이 0'))
        else:
            groups.setdefault(same_place(o), []).append(o)
    ships = []
    for items in groups.values():
        first, count = items[0], {}
        for o in items:
            count[o['상품']] = count.get(o['상품'], 0) + int(number(o['수량']))
        fill = sum(q / pack[p][1] for p, q in count.items())  # 박스를 몇 칸 채우나 (쿠키 2개 / 한 박스 4개 = 0.5칸)
        boxes = int(fill) + (1 if fill - int(fill) > 1e-9 else 0)
        zipcode = re.sub(r'\D', '', first.get('우편번호', ''))
        zipcode = zipcode.zfill(5) if len(zipcode) == 4 else zipcode  # 엑셀이 앞자리 0을 지운 경우 (04500 → 4500)
        where = remote_of(zipcode, remote)
        memo = ' / '.join(dict.fromkeys(o['배송메모'] for o in items if o.get('배송메모')))
        ships.append({'받는분': first.get('받는 사람', ''), '받는분전화': first.get('전화', ''), '우편번호': zipcode, '받는분주소': first.get('주소', ''),
                      '품목명': ' + '.join(f'{p} {q}개' for p, q in count.items()), '박스수량': max(1, boxes),
                      '박스크기': max((pack[p][0] for p in count), key=box_rank), '배송메세지': memo,
                      '도서산간': where[0] if where else '', '추가배송비': where[1] if where else '',
                      '주문번호': ' '.join(o.get('주문번호', '') for o in items), '묶음': len(items)})
    return ships, held


def checks(ships, remote):
    blank = [s['받는분'] or '(이름 없음)' for s in ships if not s['받는분주소'] or not s['받는분전화']]
    keys = [same_place({'받는 사람': s['받는분'], '주소': s['받는분주소']}) for s in ships]
    dup = sorted({k[0] for k in keys if keys.count(k) > 1})
    merged = sum(s['묶음'] > 1 for s in ships)
    miss = [s['받는분'] for s in ships if remote_of(s['우편번호'], remote) and not s['도서산간']]
    odd = [s['받는분'] for s in ships if not re.fullmatch(r'\d{5}', s['우편번호'])]
    marked = [f"{s['받는분']}({s['도서산간']})" for s in ships if s['도서산간']]
    return [
        (not blank, '업로드 파일에 주소·전화 빠진 줄이 없나', '빠진 줄: ' + ', '.join(blank) if blank else f'{len(ships)}줄 모두 주소·전화 있음'),
        (not dup, '합칠 수 있는 주문을 합쳤나', '따로 나간 곳: ' + ', '.join(dup) if dup else f'같은 사람·같은 주소는 한 줄 (합포장 {merged}곳)'),
        (not miss and not odd, '도서산간 표시가 빠지지 않았나', '표시 빠짐·우편번호 이상: ' + ', '.join(miss + odd) if miss or odd else ('표시함: ' + ', '.join(marked) if marked else '도서산간 주문 없음')),
    ]


def make(orders_path=None, open_browser=True):
    orders = read_csv(Path(orders_path) if orders_path else ORDERS)
    cols = hold_cols(orders)
    remote = remote_rules()
    ships, held = plan(orders, pack_rules(), remote, cols)
    write_csv(UPLOAD, UPLOAD_HEADER, ships)
    write_csv(HELD, ['주문번호', '받는 사람', '상품', '수량', '이유'], held)
    results = checks(ships, remote)
    boxes = sum(s['박스수량'] for s in ships)
    merged = sum(s['묶음'] > 1 for s in ships)
    cards = []
    for s in ships:
        tags = [f"주문 {s['묶음']}개 합포장"] if s['묶음'] > 1 else []
        if s['도서산간']:
            tags.append(f"도서산간 {s['도서산간']} · 추가 배송비 {s['추가배송비']:,}원")
        cards.append(f"<article><small>{html.escape(s['주문번호'])}{' · ' + html.escape(' · '.join(tags)) if tags else ''}</small>"
                     f"<h2>{html.escape(s['받는분'])} · {html.escape(s['박스크기'])} {s['박스수량']}개</h2>"
                     f"<p>{html.escape(s['품목명'])}\n{html.escape(s['우편번호'])} {html.escape(s['받는분주소'])}</p></article>")
    skipped = [(f"{h.get('주문번호', '')} {h.get('받는 사람', '')}".strip(), '보류 · ' + h['이유']) for h in held]
    page = board(f'출고 준비 {len(ships)}곳 · 박스 {boxes}개', f'주문 {len(orders)}개 · 같은 사람·같은 주소는 한 박스로 · 도서산간은 표시 · 빈칸은 보류',
                 results, cards, skipped, '출고준비.html')
    fails = finish(f'주문 {len(orders)}개를 읽었습니다. 택배 보낼 곳 {len(ships)}곳(박스 {boxes}개), 합포장 {merged}곳, 보류 {len(held)}개.', results, page, open_browser)
    say(f'택배사에 올릴 파일: {UPLOAD}')
    say(f'보류 목록: {HELD}')
    return fails


# ---------------------------------------------------------------- 택배사에서 받은 송장 파일 → 쇼핑몰 일괄 등록용 (올리지 않음)
def invoice(path):
    p = Path(path)
    if not p.exists() and (ROOT / path).exists():
        p = ROOT / path
    rows = read_csv(p)
    if not rows:
        raise SystemExit('송장 파일이 비어 있습니다.')
    col = next((c for c in ('운송장번호', '송장번호', '운송장 번호') if c in rows[0]), None)
    if not col or '주문번호' not in rows[0]:
        raise SystemExit('송장 파일에 "주문번호"와 "운송장번호" 칸이 있어야 합니다. 택배사에서 받은 파일의 칸 이름을 확인하세요.')
    out, empty = [], 0
    for r in rows:
        if not r[col]:
            empty += 1
            continue
        for no in r['주문번호'].split():  # 한 박스로 묶었던 주문은 주문번호마다 같은 송장번호를 적는다
            out.append({'주문번호': no, '송장번호': r[col]})
    write_csv(SHOP, ['주문번호', '송장번호'], out)
    say(f'송장 {len(rows) - empty}개를 주문 {len(out)}개에 나눠 적었습니다.' + (f' 송장번호가 빈 줄 {empty}개는 뺐습니다.' if empty else ''))
    say(f'쇼핑몰 송장 일괄 등록용: {SHOP}')
    say('아직 쇼핑몰에 올리지 않았습니다. 쇼핑몰 관리자 화면에서 이 파일로 일괄 등록하세요.')


def main():
    p = argparse.ArgumentParser(description='택배사 업로드 파일 만들기')
    p.add_argument('--work', help='작업 폴더')
    p.add_argument('--orders', help='주문 파일 경로 (없으면 01_주문/주문_샘플.csv)')
    p.add_argument('--invoice', help='택배사에서 받은 송장 파일을 쇼핑몰 일괄 등록용으로 바꾸기')
    p.add_argument('--no-open', action='store_true', help='결과 화면을 열지 않음')
    a = p.parse_args()
    invoice(a.invoice) if a.invoice else make(a.orders, not a.no_open)


if __name__ == '__main__':
    main()
