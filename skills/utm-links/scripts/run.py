"""utm-links: 표(CSV)를 읽어 결과 표와 화면(HTML)을 만든다. 아무 데도 보내거나 올리지 않는다. 작업 폴더는 --work 로 정한다."""
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
    return Path.cwd() / '링크-꼬리표'


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

REQUESTS = ROOT / '01_자료' / '링크요청_샘플.csv'
VISITS = ROOT / '01_자료' / '방문매출_샘플.csv'
CHANNELS = ROOT / '02_규칙' / '채널표기.csv'
CAMPAIGNS = ROOT / '02_규칙' / '캠페인이름.csv'
LINKS = OUT / '꼬리표링크.csv'
REPORT = OUT / '채널성적표.csv'
UNKNOWN = ('(direct)', '(none)')  # 꼬리표가 없어서 어디서 왔는지 모르는 방문

# GA4 에서 내려받은 파일은 칸 이름이 조금씩 다르다. 아래 이름 중 하나면 알아듣는다.
COLUMNS = {
    '소스/매체': ['소스/매체', '세션 소스/매체', '세션 소스 / 매체', 'Session source / medium', 'Session source/medium'],
    '방문': ['방문', '세션', 'Sessions'],
    '구매': ['구매', '전자상거래 구매', 'Ecommerce purchases', 'Purchases'],
    '매출': ['매출', '총 수익', '구매 수익', 'Total revenue', 'Purchase revenue'],
}


def clean(value) -> str:
    """꼬리표 표기 규칙: 소문자로, 띄어쓰기는 -, 쓸 수 없는 기호는 뺀다."""
    v = str(value or '').strip().lower()
    v = re.sub(r'\s+', '-', v)
    v = re.sub(r'[^a-z0-9가-힣._\-]', '', v)
    return re.sub(r'-{2,}', '-', v).strip('-')


def key(text) -> str:
    return str(text or '').replace(' ', '')


def channel_table() -> dict:
    rows = [r for r in read_csv(CHANNELS) if r.get('올릴 곳')]
    if not rows:
        raise SystemExit('02_규칙/채널표기.csv 에 올릴 곳을 한 줄 이상 적어 주세요 (예: 인스타 프로필, instagram, profile).')
    return {key(r['올릴 곳']): r for r in rows}


def campaign_table() -> dict:
    return {key(r['캠페인']): r for r in read_csv(CAMPAIGNS) if r.get('캠페인')}


def campaign_name(row) -> str:
    """캠페인 이름 규칙: 시작일(260915) - 영어로 짧게. 소문자, 띄어쓰기는 -."""
    day = re.sub(r'\D', '', row.get('시작일', ''))[-6:]
    return clean(f"{day} {row.get('영어로 짧게') or row['캠페인']}")


def tag(url, source, medium, campaign) -> str:
    base, _, frag = url.partition('#')
    sep = '&' if '?' in base else '?'
    return f'{base}{sep}utm_source={source}&utm_medium={medium}&utm_campaign={campaign}' + (f'#{frag}' if frag else '')


def tags_of(url) -> dict:
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    return {k: v[0] for k, v in q.items() if k.startswith('utm_')}


def make_links(chans, camps):
    rows, seen = [], {}
    for i, r in enumerate(read_csv(REQUESTS), 1):
        row = dict(r, 번호=i, 상태='', 이유='', 꼬리표링크='')
        rows.append(row)
        url, where = r.get('원래 링크', ''), r.get('올릴 곳', '')
        if not re.match(r'https?://', url):
            row.update(상태='뺌', 이유='원래 링크가 http 로 시작하지 않음')
            continue
        if 'utm_source=' in url.lower():
            row.update(상태='그대로', 이유='이미 꼬리표가 붙어 있어 손대지 않음', 꼬리표링크=url)
            continue
        ch, cp = chans.get(key(where)), camps.get(key(r.get('캠페인')))
        if not ch:
            row.update(상태='뺌', 이유=f"채널표기.csv 에 '{where}' 이(가) 없음 — 표에 한 줄 더하세요")
            continue
        if not cp:
            row.update(상태='뺌', 이유=f"캠페인이름.csv 에 '{r.get('캠페인')}' 이(가) 없음 — 표에 한 줄 더하세요")
            continue
        src, med, name = clean(ch['어디서(source)']), clean(ch['어떤 모양(medium)']), campaign_name(cp)
        same = (src, med, name, url)
        if same in seen:
            row.update(상태='묶음', 이유=f"{seen[same]}번과 같은 링크 ('{where}' 도 {src} / {med})")
            continue
        seen[same] = i
        row.update(상태='만듦', 꼬리표링크=tag(url, src, med, name), 이유=f'{where} → {src} / {med} · 캠페인 {name}')
    return rows


def checks(rows, chans, camps):
    links = [r for r in rows if r['상태'] in ('만듦', '그대로')]
    table = {(c['어디서(source)'], c['어떤 모양(medium)']) for c in chans.values()}
    off = []
    for r in links:
        t = tags_of(r['꼬리표링크'])
        pair = (t.get('utm_source', ''), t.get('utm_medium', ''))
        if pair not in table:
            off.append(f"{r['올릴 곳']}({pair[0]} / {pair[1]})")
    bad = [r['올릴 곳'] for r in links if re.search(r'[가-힣\s]', r['꼬리표링크'])]
    names = {}
    for c in camps.values():
        names.setdefault(campaign_name(c), []).append(c['캠페인'])
    dup = [f"'{n}' = " + ', '.join(v) for n, v in names.items() if len(v) > 1]
    return [
        (not off, '채널 표기가 표와 같나', '표와 다른 표기: ' + ', '.join(off) + ' — 채널표기.csv 는 영어 소문자로 적어 주세요' if off else '모든 링크가 채널표기.csv 의 표기 그대로'),
        (not bad, '링크에 한글·띄어쓰기가 그대로 들어가지 않았나', '한글·띄어쓰기가 남은 링크: ' + ', '.join(bad) + ' — 캠페인이름.csv 의 영어로 짧게 칸을 채워 주세요' if bad else '영어 소문자·숫자·- 만 들어감'),
        (not dup, '같은 캠페인 이름이 다른 뜻으로 겹치지 않나', '겹친 이름: ' + ' / '.join(dup) if dup else f'캠페인 이름 {len(names)}개가 모두 다름'),
    ]


def read_export(path: Path):
    """GA4 에서 내려받은 CSV: 맨 위 # 줄은 설명이라 건너뛰고, 첫 번째 표만 읽는다."""
    if not path.exists():
        alt = ROOT / '01_자료' / path.name
        if not alt.exists():
            raise SystemExit(f'방문·매출 파일이 없습니다: {path}')
        path = alt
    text = None
    for enc in ('utf-8-sig', 'cp949'):
        try:
            text = path.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise SystemExit(f'{path.name} 파일 글자가 깨져 있습니다. 엑셀에서 "CSV UTF-8"로 다시 저장해 주세요.')
    lines = [l for l in text.splitlines() if not l.lstrip().startswith('#')]
    while lines and not lines[0].strip():
        lines.pop(0)
    if '' in [l.strip() for l in lines]:
        lines = lines[:[l.strip() for l in lines].index('')]
    raw = list(csv.DictReader(lines))
    head = [h.strip() for h in (raw[0].keys() if raw else [])]
    pick = {}
    for want, names in COLUMNS.items():
        pick[want] = next((h for h in head if h in names), None)
    missing = [w for w in ('소스/매체', '방문', '매출') if not pick[w]]
    if missing:
        raise SystemExit(f"{path.name} 에 '{', '.join(missing)}' 칸이 없습니다. GA4 에서 세션 소스/매체 기준으로 내려받았는지 확인하세요.")
    out = []
    for r in raw:
        r = {k.strip(): (v or '').strip() for k, v in r.items() if k}
        sm = r.get(pick['소스/매체'], '')
        if not sm or sm in ('총계', '합계', 'Total', 'Grand total'):
            continue
        out.append({'소스/매체': sm, '방문': number(r.get(pick['방문'])), '구매': number(r.get(pick['구매'])) if pick['구매'] else 0, '매출': number(r.get(pick['매출']))})
    return out, path


def report(rows, chans):
    names = {}
    for c in chans.values():
        names.setdefault((clean(c['어디서(source)']), clean(c['어떤 모양(medium)'])), c['올릴 곳'])
    groups, merged = {}, 0
    for r in rows:
        s, _, m = r['소스/매체'].partition('/')
        k = (s.strip().lower(), m.strip().lower())
        if k in groups:
            merged += 1
        g = groups.setdefault(k, {'어디서 왔나': '어디서 왔는지 모름' if k == UNKNOWN else names.get(k, '표에 없는 곳 (검색·다른 사이트)'),
                                  '소스/매체': f'{k[0]} / {k[1]}', '방문': 0, '구매': 0, '매출': 0})
        for n in ('방문', '구매', '매출'):
            g[n] += r[n]
    for g in groups.values():
        for n in ('방문', '구매', '매출'):
            g[n] = int(round(g[n]))
    out = sorted(groups.values(), key=lambda g: -g['매출'])
    total = sum(g['매출'] for g in out) or 1
    visits = sum(g['방문'] for g in out) or 1
    for g in out:
        g['매출 몫'] = f"{round(g['매출'] * 100 / total)}%"
    unknown = groups.get(UNKNOWN, {'매출': 0, '방문': 0})
    return out, round(unknown['매출'] * 100 / total), round(unknown['방문'] * 100 / visits), merged


def won(n) -> str:
    return f'{int(n):,}'


def make(visits_path: Path, open_browser=True):
    chans, camps = channel_table(), campaign_table()
    rows = make_links(chans, camps)
    write_csv(LINKS, ['번호', '올릴 곳', '캠페인', '원래 링크', '꼬리표링크', '상태', '이유'], rows)
    results = checks(rows, chans, camps)
    export, used = read_export(visits_path)
    groups, money_pct, visit_pct, merged = report(export, chans)
    write_csv(REPORT, ['어디서 왔나', '소스/매체', '방문', '구매', '매출', '매출 몫'], groups)
    made = [r for r in rows if r['상태'] == '만듦']
    trs = ''.join(f"<tr{' style=background:#fdecea' if g['소스/매체'] == ' / '.join(UNKNOWN) else ''}><td>{html.escape(g['어디서 왔나'])}<br><small>{html.escape(g['소스/매체'])}</small></td><td>{won(g['방문'])}</td><td>{won(g['구매'])}</td><td>{won(g['매출'])}원</td><td><b>{g['매출 몫']}</b></td></tr>" for g in groups)
    cards = [f"<article><h2>어디서 왔는지 모르는 매출 {money_pct}%</h2>"
             f"<p>{html.escape(used.name)} · 방문의 {visit_pct}% · 매출의 {money_pct}%가 (direct) / (none) 칸에 묶여 있습니다. 링크에 꼬리표가 없으면 여기로 들어갑니다."
             + (f" 대소문자만 다르게 적혀 갈라진 줄 {merged}개는 하나로 묶었습니다." if merged else '') + '</p>'
             f"<table><tr><th>어디서 왔나</th><th>방문</th><th>구매</th><th>매출</th><th>매출 몫</th></tr>{trs}</table></article>"]
    for r in made:
        cards.append(f"<article><h2>{html.escape(r['올릴 곳'])} · {html.escape(r['캠페인'])}</h2><small>{html.escape(r['이유'])}</small>"
                     f"<div class='box' style='word-break:break-all'><b>꼬리표 붙인 링크 (복사해서 쓰기)</b>{html.escape(r['꼬리표링크'])}</div></article>")
    skipped = [(f"{r['번호']}. {r['올릴 곳']} · {r['캠페인']}", r['이유']) for r in rows if r['상태'] != '만듦']
    page = board(f'꼬리표 링크 {len(made)}개 · 채널 성적표', "꼬리표(utm) = 링크 끝에 붙이는 '어디서 왔는지 이름표' · 채널마다 몇 명이 와서 얼마나 샀는지 봅니다", results, cards, skipped, '링크와성적표.html')
    return finish(f'링크 요청 {len(rows)}개를 읽었습니다. 꼬리표 링크 {len(made)}개, 묶거나 그대로 둔 것 {len(rows) - len(made)}개.\n'
                  f'방문·매출 파일 {used.name}: 어디서 왔는지 모르는 매출 {money_pct}% (방문 {visit_pct}%).', results, page, open_browser)


def main():
    p = argparse.ArgumentParser(description='링크 꼬리표 붙이기와 채널 성적표')
    p.add_argument('--work', help='작업 폴더')
    p.add_argument('--visits', help='GA4 에서 내려받은 방문·매출 CSV 파일 (없으면 샘플)')
    p.add_argument('--no-open', action='store_true', help='결과 화면을 열지 않음')
    a = p.parse_args()
    make(Path(a.visits) if a.visits else VISITS, not a.no_open)


if __name__ == '__main__':
    main()
