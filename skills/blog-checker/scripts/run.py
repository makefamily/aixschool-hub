"""blog-checker: 표(CSV)를 읽어 결과 표와 화면(HTML)을 만든다. 아무 데도 보내거나 올리지 않는다. 작업 폴더는 --work 로 정한다."""
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
    return Path.cwd() / '블로그-점검'


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

DRAFTS = ROOT / '01_원고'
KEYWORDS = ROOT / '02_규칙' / '키워드.csv'
RULES = ROOT / '02_규칙' / '글규칙.csv'
WORDS = ROOT / '02_규칙' / '쓰면안되는말.csv'
REPORT = OUT / '점검표.csv'
CLEAN = OUT / '정리본'

# 검수용: 규칙 표와 상관없이 광고 심의(과장 광고인지 따지는 기준)에서 거의 늘 걸리는 말.
RISKY = ['100%', '효과 보장', '완치', '부작용 없']


def flat(text: str) -> str:
    """띄어쓰기를 빼고 비교한다. '경량 캠핑의자'와 '경량캠핑의자'를 같은 말로 본다."""
    return re.sub(r'\s+', '', text or '')


def read_text(path: Path) -> str:
    for enc in ('utf-8-sig', 'cp949'):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    raise SystemExit(f'{path.name} 글자가 깨져 있습니다. 메모장에서 "UTF-8"로 다시 저장해 주세요.')


def load_drafts() -> list[dict]:
    """01_원고 폴더의 CSV(상품·제목·본문 칸)와 메모장 .txt(첫 줄이 제목)를 모두 읽는다."""
    out = []
    for p in sorted(DRAFTS.glob('*.csv')):
        for r in read_csv(p):
            if '본문' not in r or '제목' not in r:
                raise SystemExit(f'01_원고/{p.name} 에 "제목"과 "본문" 칸이 있어야 합니다.')
            if r['제목'] or r['본문']:
                out.append({'파일': p.name, '상품': r.get('상품', ''), '제목': r['제목'], '본문': r['본문'].replace('\\n', '\n')})
    for p in sorted(DRAFTS.glob('*.txt')):
        lines = read_text(p).strip().splitlines()
        if lines:
            out.append({'파일': p.name, '상품': '', '제목': lines[0].strip(), '본문': '\n'.join(lines[1:]).strip()})
    if not out:
        raise SystemExit('01_원고 폴더에 원고가 없습니다. CSV(제목·본문 칸)나 메모장 .txt(첫 줄이 제목)로 넣어 주세요.')
    for i, d in enumerate(out, 1):
        d['순서'] = i
    return out


def keywords() -> dict:
    out = {flat(r['상품']): r['메인 키워드'] for r in read_csv(KEYWORDS) if r.get('상품') and r.get('메인 키워드')}
    if not out:
        raise SystemExit('02_규칙/키워드.csv 에 상품과 메인 키워드를 한 줄 이상 적어 주세요.')
    return out


def post_rules() -> dict:
    """글규칙.csv 의 '규칙' 칸 이름으로 어떤 기준인지 알아본다."""
    rule = {'title': True, 'min': 3, 'max': 7, 'chars': 300, 'heads': 3}
    for r in read_csv(RULES):
        name, val = r.get('규칙', ''), r.get('값', '').strip()
        if '소제목' in name:
            key = 'heads'
        elif '제목' in name:
            rule['title'] = val not in ('아니오', '아니요', 'X', 'x', 'N', 'n', '')
            continue
        elif '글자' in name:
            key = 'chars'
        elif '최대' in name:
            key = 'max'
        elif '최소' in name:
            key = 'min'
        else:
            continue
        if not val.replace(',', '').isdigit():
            raise SystemExit(f"02_규칙/글규칙.csv 의 '{name}' 값에는 숫자만 적어 주세요 (지금: {val}).")
        rule[key] = int(val.replace(',', ''))
    return rule


def headings(body: str) -> list[str]:
    """줄 앞에 # 이 붙은 줄을 소제목으로 본다 (예: ## 보관은 이렇게)."""
    return [s.lstrip('#').strip() for s in (x.strip() for x in body.splitlines()) if s.startswith('#')]


def inspect(drafts, kws, rule, words):
    seen = {}
    for d in drafts:
        title, body = d['제목'], d['본문']
        kw = kws.get(flat(d['상품'])) if d['상품'] else next((k for k in kws.values() if flat(k) in flat(title + body)), None)
        n = flat(body).count(flat(kw)) if kw else 0
        chars = len(flat(re.sub(r'^\s*#+', '', body, flags=re.M)))
        heads = headings(body)
        why = []
        if not kw:
            why.append('키워드 표에 없는 상품 (02_규칙/키워드.csv 에 한 줄 더하세요)')
        else:
            if rule['title'] and flat(kw) not in flat(title):
                why.append(f"제목에 '{kw}' 없음")
            if not rule['min'] <= n <= rule['max']:
                why.append(f"본문 키워드 {n}번 (기준 {rule['min']}~{rule['max']}번)")
        if chars < rule['chars']:
            why.append(f"{chars}자 (기준 {rule['chars']}자 이상)")
        if len(heads) < rule['heads']:
            why.append(f"소제목 {len(heads)}개 (기준 {rule['heads']}개 이상)")
        hits = [w for w in words if w.get('쓰면 안 되는 말') and w['쓰면 안 되는 말'] in title + body]
        if hits:
            why.append('쓰면 안 되는 말 ' + ', '.join(f"'{w['쓰면 안 되는 말']}'" + (f"→'{w['바꿔 쓸 말']}'" if w.get('바꿔 쓸 말') else '') for w in hits))
        if not why and flat(title) in seen:
            why.append(f'같은 제목 글이 이미 준비됨 ({seen[flat(title)]}번 원고)')
        if not why:
            seen[flat(title)] = d['순서']
        d.update(키워드=kw or '', 키워드수=n, 글자수=chars, 소제목수=len(heads), 상태='보류' if why else '준비',
                 이유=' · '.join(why) if why else f"키워드 {n}번 · {chars}자 · 소제목 {len(heads)}개")
    return drafts


def checks(rows, rule, words):
    ready = [r for r in rows if r['상태'] == '준비']
    bad_kw = [r['제목'][:16] for r in ready if not r['키워드'] or (rule['title'] and flat(r['키워드']) not in flat(r['제목']))
              or not rule['min'] <= int(r['키워드수']) <= rule['max']]
    risky = sorted({w for r in ready for w in RISKY + [x.get('쓰면 안 되는 말', '') for x in words] if w and w in r['제목'] + r['본문']})
    titles = [flat(r['제목']) for r in ready]
    dup = sorted({r['제목'][:16] for r in ready if titles.count(flat(r['제목'])) > 1})
    return [
        (not bad_kw, '준비된 글은 모두 키워드 기준을 지켰나', '어긋난 글: ' + ', '.join(bad_kw) if bad_kw else (f"준비된 글 {len(ready)}편 모두 제목에 키워드, 본문 {rule['min']}~{rule['max']}번" if ready else '준비된 글 없음')),
        (not risky, '위험 표현이 없나', '들어간 말: ' + ', '.join(risky) if risky else '과장 광고로 보일 말 없음'),
        (not dup, '같은 제목이 겹치지 않나', '겹친 제목: ' + ', '.join(dup) if dup else '제목이 모두 다름'),
    ]


def blocks(body: str):
    """정리본: 빈 줄은 버리고, 소제목과 문단을 나눈다."""
    out = []
    for line in body.splitlines():
        s = line.strip()
        if s:
            out.append(('h', s.lstrip('#').strip()) if s.startswith('#') else ('p', s))
    return out


def plain(r) -> str:
    lines = [r['제목'], '']
    for kind, text in blocks(r['본문']):
        lines += ['', f'■ {text}', ''] if kind == 'h' else [text]
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip() + '\n'


def rich(r) -> str:
    return ''.join(f"<h3 style='font-size:19px;margin:18px 0 6px;color:#111827'><strong>{html.escape(t)}</strong></h3>" if k == 'h' else f'<p>{html.escape(t)}</p>' for k, t in blocks(r['본문']))


COPY_JS = """<script>function cp(id,b){var el=document.getElementById(id),r=document.createRange(),s=window.getSelection();
r.selectNodeContents(el);s.removeAllRanges();s.addRange(r);var ok=false;try{ok=document.execCommand('copy')}catch(e){}
s.removeAllRanges();b.textContent=ok?'복사됨':'직접 드래그해서 복사하세요'}</script>"""
BTN = "style='margin:6px 6px 0 0;padding:6px 12px;border:1px solid #2563eb;background:#fff;color:#2563eb;cursor:pointer;font-size:14px'"


def make(open_browser=True):
    words = read_csv(WORDS)
    rule = post_rules()
    rows = inspect(load_drafts(), keywords(), rule, words)
    write_csv(REPORT, ['순서', '파일', '상품', '제목', '키워드', '키워드수', '글자수', '소제목수', '상태', '이유'], rows)
    ready = [r for r in rows if r['상태'] == '준비']
    CLEAN.mkdir(parents=True, exist_ok=True)
    for old in CLEAN.glob('*.txt'):
        old.unlink()
    for r in ready:
        name = re.sub(r'[\\/:*?"<>|]', '', r['제목'])[:40].strip()
        (CLEAN / f"{r['순서']:02d}_{name}.txt").write_text(plain(r), encoding='utf-8')
    results = checks(rows, rule, words)
    table = ''.join(f"<tr><td>{r['순서']}</td><td>{html.escape(r['제목'])}</td><td>{r['키워드수']}번</td><td>{r['글자수']}자</td><td>{r['소제목수']}개</td>"
                    f"<td><b style='color:{'#15803d' if r['상태'] == '준비' else '#b45309'}'>{r['상태']}</b></td></tr>" for r in rows)
    cards = [COPY_JS, f"<article><h2>원고 {len(rows)}편 점검표</h2><table><tr><th>순서</th><th>제목</th><th>키워드</th><th>글자 수</th><th>소제목</th><th>상태</th></tr>{table}</table></article>"]
    for r in ready:
        n = r['순서']
        cards.append(f"<article><small>{n}번 원고 · {html.escape(r['키워드'])} · {html.escape(r['이유'])}</small><h2 id='t{n}'>{html.escape(r['제목'])}</h2>"
                     f"<button {BTN} onclick=\"cp('t{n}',this)\">제목 복사</button><button {BTN} onclick=\"cp('b{n}',this)\">본문 복사</button>"
                     f"<div class='box' id='b{n}' style='white-space:normal'>{rich(r)}</div></article>")
    skipped = [(f"{r['순서']}. {r['제목'][:28]}", r['이유']) for r in rows if r['상태'] != '준비']
    page = board(f'올릴 준비된 글 {len(ready)}편', '키워드·글자 수·소제목 기준을 지킨 글만 · 복사 버튼을 눌러 네이버 블로그 글쓰기에 붙여넣으세요', results, cards, skipped, '블로그_점검.html')
    return finish(f'원고 {len(rows)}편을 점검했습니다. 올릴 준비 {len(ready)}편, 보류 {len(rows) - len(ready)}편. 정리본: 결과/정리본', results, page, open_browser)


def main():
    p = argparse.ArgumentParser(description='블로그 원고 점검과 붙여넣기용 정리본')
    p.add_argument('--work', help='작업 폴더')
    p.add_argument('--no-open', action='store_true', help='결과 화면을 열지 않음')
    a = p.parse_args()
    make(False)


if __name__ == '__main__':
    main()
