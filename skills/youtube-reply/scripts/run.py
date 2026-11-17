"""youtube-reply: 표(CSV)를 읽어 결과 표와 화면(HTML)을 만든다. 아무 데도 보내거나 올리지 않는다. 작업 폴더는 --work 로 정한다."""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import html
import http.server
import json
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
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
    return Path.cwd() / '유튜브-답글'


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
SAMPLE = ROOT / '01_댓글' / '댓글_샘플.csv'
FETCHED = ROOT / '01_댓글' / '내영상_댓글.csv'
RULES = ROOT / '02_규칙' / '답글규칙.csv'
EXCLUDE = ROOT / '02_규칙' / '제외단어.csv'
REPLIES = OUT / '답글목록.csv'


# 검수용: 규칙 표와 상관없이 "광고·연락처 댓글"로 보는 표시. 여기에 걸리면 답글을 달면 안 됩니다.
SPAM_SIGNS = ['http', 'www.', '오픈채팅', '카톡', '텔레' + '그램', '수익 보장', '수익보장', '010-']

REPLY, SKIP = '답글 초안', '건너뜀'


def say(text=''):
    print(text, flush=True)


def read_csv(path: Path) -> list[dict]:
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
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------- 답글 초안 만들기

def decide(comments: list[dict], rules: list[dict], excludes: list[dict]) -> list[dict]:
    rows, answered = [], set()
    for c in comments:
        text, who = c.get('댓글', ''), c.get('작성자', '')
        row = {'댓글ID': c.get('댓글ID', ''), '작성자': who, '댓글': text, '상태': SKIP, '이유': '', '규칙줄': '', '답글': ''}
        rule_no, rule = next(((i, r) for i, r in enumerate(rules, start=2) if r.get('키워드') and r['키워드'].lower() in text.lower()), (None, None))
        hit_ex = next((e for e in excludes if e.get('제외단어') and e['제외단어'].lower() in text.lower()), None)
        if c.get('내댓글') == '예':
            row['이유'] = '내가 쓴 댓글'
        elif c.get('이미답함') == '예':
            row['이유'] = '이미 답글을 달았음'
        elif not rule:
            row['이유'] = '키워드 없음'
        elif hit_ex:
            row['이유'] = f"제외단어 '{hit_ex['제외단어']}'"
        elif who in answered:
            row['이유'] = '같은 사람에게 이미 답함'
        else:
            row.update(상태=REPLY, 이유=f"키워드 '{rule['키워드']}'", 규칙줄=f'답글규칙.csv {rule_no}번째 줄',
                       답글=rule['답글'].replace('{이름}', who))
            answered.add(who)
        rows.append(row)
    return rows


def checks(rows: list[dict], rules: list[dict]) -> list[tuple[bool, str, str]]:
    blank = [r for r in rows if r['상태'] == REPLY and re.search(r'\{[^}]*\}', r['답글'])]
    spam = [r for r in rows if r['상태'] == REPLY and any(s in r['댓글'].lower() for s in SPAM_SIGNS)]
    drafts = [r['작성자'] for r in rows if r['상태'] == REPLY]
    dup = sorted({w for w in drafts if drafts.count(w) > 1})
    return [
        (not blank, '답글에 못 채운 빈칸({이름} 같은)이 남지 않았나', '빈칸이 남은 답글: ' + ', '.join(r['댓글ID'] for r in blank) if blank else '빈칸 없음'),
        (not spam, '광고·연락처 댓글에는 답하지 않았나', '광고로 보이는 댓글에 답글 초안이 있음: ' + ', '.join(f"{r['댓글ID']}({r['작성자']})" for r in spam) if spam else '광고 댓글에 답하지 않음'),
        (not dup, '같은 사람에게 두 번 답하지 않았나', '두 번 답한 사람: ' + ', '.join(dup) if dup else '한 사람에게 한 번씩만 답함'),
    ]


def preview(rows: list[dict], results: list[tuple[bool, str, str]], source: str) -> Path:
    card = lambda r: (f"<article class='{'on' if r['상태'] == REPLY else 'off'}'><header><b>{html.escape(r['작성자'])}</b>"
                      f"<span>{html.escape(r['상태'])} · {html.escape(r['이유'])}</span></header><p>{html.escape(r['댓글'])}</p>"
                      + (f"<div class='reply'><small>보낼 답글 · {html.escape(r['규칙줄'])}</small>{html.escape(r['답글'])}</div>" if r['답글'] else '')
                      + '</article>')
    check = ''.join(f"<li class='{'pass' if ok else 'fail'}'><b>{'통과' if ok else '확인 필요'}</b> {html.escape(t)}<small>{html.escape(d)}</small></li>" for ok, t, d in results)
    page = f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>답글 미리보기</title>
<style>body{{margin:0;background:#f8fafc;color:#111827;font:16px/1.6 -apple-system,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;padding:32px 16px}}
.w{{max-width:760px;margin:auto}}h1{{font-size:28px;margin:0 0 4px}}.src{{color:#6b7280;margin:0 0 20px}}
ul{{list-style:none;padding:0;margin:0 0 24px;display:grid;gap:8px}}li{{background:#fff;border:1px solid #e5e7eb;padding:12px 14px}}li b{{margin-right:8px}}li small{{display:block;color:#4b5563}}
.pass b{{color:#15803d}}.fail{{border-color:#f5c2bd;background:#fdecea}}.fail b{{color:#b42318}}
article{{background:#fff;border:1px solid #e5e7eb;border-left:4px solid #2563eb;padding:14px 16px;margin-bottom:10px}}article.off{{border-left-color:#d1d5db;opacity:.75}}
header{{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}}header span{{color:#6b7280;font-size:14px}}article p{{margin:6px 0}}
.reply{{background:#eff4ff;padding:10px 12px;margin-top:8px}}.reply small{{display:block;color:#2563eb;font-weight:700}}
.note{{background:#111827;color:#fff;padding:12px 14px;margin-bottom:20px}}</style>
<div class="w"><h1>답글 미리보기</h1><p class="src">댓글 파일: {html.escape(source)}</p>
<p class="note">아직 아무 데도 게시하지 않았습니다. 확인 필요가 0개일 때만 게시하세요.</p>
<ul>{check}</ul>{''.join(card(r) for r in rows)}</div>"""
    path = OUT / '답글미리보기.html'
    path.write_text(page, encoding='utf-8')
    return path


def make_drafts(source: Path, open_browser=True):
    if not source.exists():
        raise SystemExit(f'댓글 파일이 없습니다: {source}')
    comments, rules, excludes = read_csv(source), read_csv(RULES), read_csv(EXCLUDE)
    rows = decide(comments, rules, excludes)
    OUT.mkdir(exist_ok=True)
    write_csv(REPLIES, ['댓글ID', '작성자', '댓글', '상태', '이유', '규칙줄', '답글'], rows)
    results = checks(rows, rules)
    page = preview(rows, results, source.name)
    drafts = sum(r['상태'] == REPLY for r in rows)
    say(f'댓글 {len(rows)}개를 읽었습니다. 답글 초안 {drafts}개, 건너뜀 {len(rows) - drafts}개.')
    say('')
    for ok, title, detail in results:
        say(f"  [{'통과' if ok else '확인 필요'}] {title} — {detail}")
    fails = sum(not ok for ok, _, _ in results)
    say('')
    say(f'확인 필요 {fails}개. ' + ('게시해도 되는 상태입니다.' if not fails else '02_규칙 표를 고친 뒤 다시 실행하세요.'))
    say(f'미리보기: {page}')
    say('아직 아무 데도 게시하지 않았습니다.')
    return fails


# ---------------------------------------------------------------- 내 영상 댓글 불러오기

def main():
    p = argparse.ArgumentParser(description='유튜브 댓글 키워드 답글 초안')
    p.add_argument('--work', help='작업 폴더')
    p.add_argument('--input', help='답글 초안을 만들 댓글 CSV')
    p.add_argument('--no-open', action='store_true')
    a = p.parse_args()
    source = Path(a.input).resolve() if a.input else SAMPLE
    make_drafts(source, False)


if __name__ == '__main__':
    main()
