"""news-digest: 표(CSV)를 읽어 결과 표와 화면(HTML)을 만든다. 아무 데도 보내거나 올리지 않는다. 작업 폴더는 --work 로 정한다."""
from __future__ import annotations

import argparse
import csv
import html
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
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
    return Path.cwd() / '글감-보드'


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
SAMPLE = ROOT / '01_소식' / '소식_샘플.csv'
TODAY_FILE = ROOT / '01_소식' / '오늘_소식.csv'
KEYWORDS = ROOT / '02_규칙' / '관심키워드.csv'
EXCLUDE = ROOT / '02_규칙' / '빼는말.csv'
SETTINGS = ROOT / '02_규칙' / '설정.csv'
SOURCES = ROOT / '02_규칙' / '모을곳.csv'
HEADER = ['제목', '출처', '날짜', '요약', '링크']

# 검수용: 규칙 표와 상관없이 "광고·협찬 글"로 보는 표시. 이런 글이 글감에 들어가면 안 됩니다.
AD_SIGNS = ['[광고]', '[협찬]', '[ad]', '[sponsored]', '무료 체험', '할인', '지금 가입']


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
        w = csv.DictWriter(f, fieldnames=header, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def settings() -> dict:
    s = {r['항목']: r['값'] for r in read_csv(SETTINGS)}
    try:
        return {'days': int(s.get('최근 며칠', 7)), 'count': int(s.get('글감 개수', 5))}
    except ValueError:
        raise SystemExit('02_규칙/설정.csv 의 값 칸에는 숫자만 적어 주세요.')


def norm(title: str) -> str:
    """같은 소식인지 비교할 때 쓰는 제목: 괄호·기호·띄어쓰기를 빼고 앞 18글자."""
    t = re.sub(r'\[[^\]]*\]|\([^)]*\)|["“”\'‘’…·,.:!?\-–—]', '', title)
    return re.sub(r'\s+', '', t)[:18]


def similar(a: str, b: str) -> bool:
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    common = len(set(a[i:i + 2] for i in range(len(a) - 1)) & set(b[i:i + 2] for i in range(len(b) - 1)))
    return common / max(1, min(len(a), len(b)) - 1) >= 0.5


# ---------------------------------------------------------------- 글감 고르기

def pick(items: list[dict], keywords: list[dict], excludes: list[dict], conf: dict) -> tuple[list[dict], list[dict], date]:
    dates = [datetime.strptime(i['날짜'][:10], '%Y-%m-%d').date() for i in items if re.match(r'\d{4}-\d{2}-\d{2}', i.get('날짜', ''))]
    base = max(dates) if dates else date.today()
    rows = []
    for it in items:
        text = f"{it.get('제목', '')} {it.get('요약', '')}"
        row = dict(it, 점수=0, 맞은키워드='', 상태='', 이유='')
        try:
            d = datetime.strptime(it.get('날짜', '')[:10], '%Y-%m-%d').date()
        except ValueError:
            d = None
        hit = [k for k in keywords if k.get('키워드') and k['키워드'].lower() in text.lower()]
        row['점수'] = sum(int(k.get('점수') or 0) for k in hit)
        row['맞은키워드'] = ', '.join(k['키워드'] for k in hit)
        ex = next((e['빼는말'] for e in excludes if e.get('빼는말') and e['빼는말'].lower() in text.lower()), None)
        if ex:
            row.update(상태='뺌', 이유=f"빼는말 '{ex}'")
        elif d is None or (base - d).days > conf['days']:
            row.update(상태='뺌', 이유=f"{conf['days']}일 넘은 소식")
        elif not hit:
            row.update(상태='뺌', 이유='관심 키워드 없음')
        rows.append(row)
    chosen = []
    for row in sorted([r for r in rows if not r['상태']], key=lambda r: (r['점수'], r['날짜']), reverse=True):
        dup = next((c for c in chosen if similar(c['제목'], row['제목'])), None)
        if dup:
            row.update(상태='뺌', 이유=f"같은 소식 ({dup['출처']})")
        elif len(chosen) < conf['count']:
            row.update(상태='글감', 이유=f"점수 {row['점수']}")
            chosen.append(row)
        else:
            row.update(상태='후보 밖', 이유=f"점수 {row['점수']} · 상위 {conf['count']}개 밖")
    return chosen, rows, base


def checks(chosen: list[dict], base: date, conf: dict) -> list[tuple[bool, str, str]]:
    dups = [(a['제목'], b['제목']) for i, a in enumerate(chosen) for b in chosen[i + 1:] if similar(a['제목'], b['제목'])]
    old = [c for c in chosen if (base - datetime.strptime(c['날짜'][:10], '%Y-%m-%d').date()).days > conf['days']]
    ads = [c for c in chosen if any(s.lower() in f"{c['제목']} {c.get('요약', '')}".lower() for s in AD_SIGNS)]
    return [
        (not dups, '같은 소식이 두 번 들어가지 않았나', '겹친 소식: ' + ' / '.join(a[:20] for a, _ in dups) if dups else '겹친 소식 없음'),
        (not old, f"{conf['days']}일 넘은 소식이 없나", '오래된 소식: ' + ', '.join(c['제목'][:20] for c in old) if old else '모두 최근 소식'),
        (not ads, '광고·협찬 글이 섞이지 않았나', '광고로 보이는 글: ' + ', '.join(c['제목'][:30] for c in ads) if ads else '광고 글 없음'),
    ]


def board(chosen, rows, results, base, source) -> Path:
    card = lambda i, r: (f"<article><div class='n'>{i}</div><div><h2><a href='{html.escape(r.get('링크', ''))}' target='_blank' rel='noopener'>{html.escape(r['제목'])}</a></h2>"
                         f"<p>{html.escape(r.get('요약', ''))}</p><small>{html.escape(r.get('출처', ''))} · {html.escape(r.get('날짜', '')[:10])} · 점수 {r['점수']} · {html.escape(r['맞은키워드'])}</small></div></article>")
    out = ''.join(f"<li><b>{html.escape(r['제목'][:40])}</b><span>{html.escape(r['이유'])}</span></li>" for r in rows if r['상태'] != '글감')
    check = ''.join(f"<li class='{'pass' if ok else 'fail'}'><b>{'통과' if ok else '확인 필요'}</b> {html.escape(t)}<small>{html.escape(d)}</small></li>" for ok, t, d in results)
    page = f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>오늘의 글감</title>
<style>body{{margin:0;background:#f8fafc;color:#111827;font:16px/1.6 -apple-system,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;padding:32px 16px}}
.w{{max-width:780px;margin:auto}}h1{{font-size:28px;margin:0}}.src{{color:#6b7280;margin:4px 0 18px}}
ul.c{{list-style:none;padding:0;margin:0 0 22px;display:grid;gap:8px}}ul.c li{{background:#fff;border:1px solid #e5e7eb;padding:12px 14px}}ul.c li b{{margin-right:8px}}ul.c small{{display:block;color:#4b5563}}
.pass b{{color:#15803d}}.fail{{border-color:#f5c2bd!important;background:#fdecea!important}}.fail b{{color:#b42318}}
article{{display:flex;gap:14px;background:#fff;border:1px solid #e5e7eb;border-left:4px solid #2563eb;padding:14px 16px;margin-bottom:10px}}.n{{font-weight:800;color:#2563eb;font-size:22px;width:28px}}
article h2{{font-size:18px;margin:0 0 4px}}article h2 a{{color:inherit;text-decoration:none}}article p{{margin:0 0 6px;color:#374151}}article small{{color:#6b7280}}
details{{margin-top:22px}}details li{{margin:4px 0;color:#4b5563;font-size:14px}}details li span{{margin-left:8px;color:#9ca3af}}</style>
<div class="w"><h1>오늘의 글감 {len(chosen)}개</h1><p class="src">기준일 {base} · 소식 파일: {html.escape(source)} · 아무 데도 올리지 않았습니다</p>
<ul class="c">{check}</ul>{''.join(card(i, r) for i, r in enumerate(chosen, 1))}
<details><summary>뺀 소식 {len(rows) - len(chosen)}개와 이유</summary><ul>{out}</ul></details></div>"""
    path = OUT / '오늘의글감.html'
    path.write_text(page, encoding='utf-8')
    return path


def make_board(source: Path, open_browser=True) -> int:
    if not source.exists():
        raise SystemExit(f'소식 파일이 없습니다: {source}')
    conf = settings()
    chosen, rows, base = pick(read_csv(source), read_csv(KEYWORDS), read_csv(EXCLUDE), conf)
    OUT.mkdir(exist_ok=True)
    write_csv(OUT / '글감목록.csv', ['상태', '이유', '점수', '맞은키워드'] + HEADER, rows)
    results = checks(chosen, base, conf)
    page = board(chosen, rows, results, base, source.name)
    say(f'소식 {len(rows)}건을 읽었습니다. 오늘의 글감 {len(chosen)}개, 뺀 소식 {len(rows) - len(chosen)}건.')
    for i, c in enumerate(chosen, 1):
        say(f"  {i}. [{c['점수']}점] {c['제목'][:50]}")
    say('')
    for ok, title, detail in results:
        say(f"  [{'통과' if ok else '확인 필요'}] {title} — {detail}")
    fails = sum(not ok for ok, _, _ in results)
    say('')
    say(f'확인 필요 {fails}개. ' + ('이대로 글감으로 써도 됩니다.' if not fails else '02_규칙 표를 고친 뒤 다시 실행하세요.'))
    say(f'글감 보드: {page}')
    return fails


# ---------------------------------------------------------------- 진짜 소식 모으기

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (AIxSCHOOL news-digest)'})
    for attempt in range(3):  # 유튜브 주소는 가끔 잠깐 실패한다. 잠시 쉬고 두 번 더 시도한다
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == 2:
                raise
            time.sleep(2)


def feed_items(xml_bytes: bytes, source_name: str) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    ns = {'a': 'http://www.w3.org/2005/Atom', 'media': 'http://search.yahoo.com/mrss/'}
    items = []
    for it in root.iter('item'):  # RSS (구글 뉴스·블로그)
        title = (it.findtext('title') or '').strip()
        when = it.findtext('pubDate') or ''
        try:
            d = parsedate_to_datetime(when).astimezone(timezone(timedelta(hours=9))).date().isoformat()
        except Exception:
            d = ''
        summary = re.sub('<[^>]+>', ' ', it.findtext('description') or '')
        src = it.findtext('source') or source_name
        items.append({'제목': title, '출처': src.strip(), '날짜': d, '요약': re.sub(r'\s+', ' ', html.unescape(summary)).strip()[:160], '링크': (it.findtext('link') or '').strip()})
    for e in root.findall('a:entry', ns):  # Atom (유튜브 채널)
        title = (e.findtext('a:title', default='', namespaces=ns) or '').strip()
        d = (e.findtext('a:published', default='', namespaces=ns) or '')[:10]
        link = e.find('a:link', ns)
        desc = e.find('media:group/media:description', ns)
        items.append({'제목': title, '출처': source_name, '날짜': d, '요약': ((desc.text or '') if desc is not None else '')[:160].replace('\n', ' '),
                      '링크': link.get('href') if link is not None else ''})
    return items


def source_url(kind: str, value: str) -> str:
    if kind == '구글뉴스':
        return 'https://news.google.com/rss/search?' + urllib.parse.urlencode({'q': value + ' when:7d', 'hl': 'ko', 'gl': 'KR', 'ceid': 'KR:ko'})
    if kind == '유튜브':
        return 'https://www.youtube.com/feeds/videos.xml?channel_id=' + value.strip()
    return value.strip()  # 블로그 등 RSS 주소 그대로


def collect() -> Path:
    all_items, ok, failed = [], 0, []
    for s in read_csv(SOURCES):
        name, kind, value = s.get('이름', ''), s.get('종류', ''), s.get('주소나 검색어', '')
        if not value:
            continue
        try:
            got = feed_items(fetch(source_url(kind, value)), name)
            all_items += got
            ok += 1
            say(f'  {name}: {len(got)}건')
        except (urllib.error.URLError, ET.ParseError, ValueError) as e:
            failed.append(name)
            say(f'  {name}: 못 가져옴 ({getattr(e, "reason", e)}) — 주소나 검색어를 확인하세요')
    if not all_items:
        raise SystemExit('소식을 하나도 가져오지 못했습니다. 인터넷 연결과 02_규칙/모을곳.csv 를 확인하세요.')
    write_csv(TODAY_FILE, HEADER, all_items)
    say(f'모을 곳 {ok}곳에서 소식 {len(all_items)}건을 모았습니다 → 01_소식/{TODAY_FILE.name}')
    return TODAY_FILE


def main():
    p = argparse.ArgumentParser(description='매일 글감 모으기')
    p.add_argument('--work', help='작업 폴더')
    p.add_argument('--live', action='store_true', help='모을곳.csv 에서 진짜 소식 모으기')
    p.add_argument('--input', help='글감을 고를 소식 CSV')
    p.add_argument('--no-open', action='store_true', help='글감 보드 창을 열지 않음')
    a = p.parse_args()
    source = collect() if a.live else (Path(a.input).resolve() if a.input else SAMPLE)
    make_board(source, False)


if __name__ == '__main__':
    main()
