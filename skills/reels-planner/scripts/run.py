"""reels-planner: 표(CSV)를 읽어 결과 표와 화면(HTML)을 만든다. 아무 데도 보내거나 올리지 않는다. 작업 폴더는 --work 로 정한다."""
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
    return Path.cwd() / '릴스-기획'


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

import math

PLAN = ROOT / '01_기획' / '릴스_기획표_샘플.csv'
TIMING = ROOT / '02_규칙' / '장면길이.csv'
CAPTION = ROOT / '02_규칙' / '캡션규칙.csv'
TAGS = ROOT / '02_규칙' / '해시태그.csv'
SCENES = OUT / '장면표.csv'
MORE = '(나머지는 영상에서)'


def setting(path, name, cast=float):
    for r in read_csv(path):
        if r.get('항목') == name:
            try:
                return cast(r.get('값', ''))
            except ValueError:
                break
    raise SystemExit(f"02_규칙/{path.name} 의 '{name}' 줄에 값을 적어 주세요. (숫자 칸에는 숫자만)")


def count(text: str) -> int:
    """읽는 글자 수. 띄어쓰기는 세지 않는다."""
    return len(re.sub(r'\s', '', text))


def split_scene(text: str, limit: int) -> list[str]:
    """한 장면에 다 못 읽을 만큼 길면 띄어쓰기 자리에서 비슷한 길이로 나눈다."""
    if count(text) <= limit:
        return [text]
    target = count(text) / math.ceil(count(text) / limit)
    parts, cur = [], []
    for w in text.split():
        if cur and (count(' '.join(cur + [w])) > limit or count(' '.join(cur)) >= target):
            parts.append(' '.join(cur))
            cur = []
        cur.append(w)
    if cur:
        parts.append(' '.join(cur))
    return parts


def stamp(sec: float) -> str:
    ms = int(round(sec * 1000))
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'


def clock(sec: float) -> str:
    return f'{int(sec // 60)}:{sec % 60:04.1f}'


def tag(word: str) -> str:
    word = re.sub(r'[\s,]', '', word)
    return ('#' + word.lstrip('#')) if word.strip('#') else ''


def read_plan():
    reels, skipped = [], []
    for i, r in enumerate(read_csv(PLAN), 2):
        title = r.get('릴스 제목', '')
        if not title:
            skipped.append((f'{i}번째 줄', '릴스 제목이 비어 있어 뺌'))
            continue
        reel = next((x for x in reels if x['제목'] == title), None)
        if not reel:
            reel = dict(제목=title, 주제=r.get('주제', ''), 문장=[], 추가=[])
            reels.append(reel)
        reel['추가'] += [t for t in (tag(w) for w in re.split(r'[\s,]+', r.get('추가 해시태그', ''))) if t]
        if r.get('장면 문장'):
            reel['문장'].append(r['장면 문장'])
        else:
            skipped.append((f'{i}번째 줄 ({title[:12]})', '장면 문장이 비어 있어 건너뜀'))
    return reels, skipped


def pick_tags(reel, table, most, skipped):
    """공통 → 주제 → 이 릴스에만 붙일 것 순서로 모으고, 겹친 건 하나로, 넘치면 뒤에서 뺀다."""
    topics = {r.get('주제') for r in table}
    wanted = [tag(r.get('해시태그', '')) for r in table if r.get('주제') == '공통']
    wanted += [tag(r.get('해시태그', '')) for r in table if r.get('주제') == reel['주제'] and reel['주제'] != '공통']
    wanted += reel['추가']
    out = []
    for t in wanted:
        if t and t not in out:
            out.append(t)
    for t in out[most:]:
        skipped.append((f"{t} ({reel['제목'][:12]})", f'해시태그 {most}개가 넘어서 뺌'))
    note = '' if reel['주제'] in topics else f"주제 '{reel['주제']}' 는 해시태그 표에 없어 공통 태그만"
    return out[:most], note


def caption(title, lines, end, tags, limit):
    """첫 줄은 릴스 제목, 가운데는 장면 문장, 끝에 마무리 말과 해시태그. 길면 가운데를 줄인다."""
    tail = (f'\n\n{end}' if end else '') + ('\n\n' + ' '.join(tags) if tags else '')
    body, cut = [], 0
    for i, line in enumerate(lines):
        if len(f"{title}\n\n{chr(10).join(body + [line])}{tail}") > limit:
            while body and len(f"{title}\n\n{chr(10).join(body + [MORE])}{tail}") > limit:
                body.pop()
            body.append(MORE)
            cut = len(lines) - len(body) + 1
            break
        body.append(line)
    return f"{title}\n\n{chr(10).join(body)}{tail}", cut


def build():
    speed = setting(TIMING, '1초에 읽는 글자 수')
    lo, hi = setting(TIMING, '장면 최소 초'), setting(TIMING, '장면 최대 초')
    longest = setting(TIMING, '릴스 최대 초')
    first_max, total_max = setting(CAPTION, '첫 줄 최대 글자 수', int), setting(CAPTION, '캡션 전체 최대 글자 수', int)
    most, end = setting(CAPTION, '해시태그 최대 개수', int), setting(CAPTION, '마지막 줄', str)
    if speed <= 0 or lo <= 0 or hi < lo:
        raise SystemExit('02_규칙/장면길이.csv 의 숫자를 확인해 주세요. (읽는 글자 수는 0보다 크게, 최대 초는 최소 초보다 크게)')
    limit = int(hi * speed)
    reels, skipped = read_plan()
    table = read_csv(TAGS)
    for n, reel in enumerate(reels, 1):
        reel['번호'] = n
        t, scenes = 0.0, []
        for line in reel['문장']:
            parts = split_scene(line, limit)
            for part in parts:
                need = count(part) / speed
                sec = min(hi, max(lo, math.ceil(need * 10 - 1e-9) / 10))
                mark = '나눔' if len(parts) > 1 else ('늘림' if sec > math.ceil(need * 10 - 1e-9) / 10 else '')
                scenes.append(dict(릴스=n, 장면=len(scenes) + 1, 시작=round(t, 1), 끝=round(t + sec, 1), 초=sec, 필요=need, 글자수=count(part), 자막=part, 표시=mark))
                t = round(t + sec, 1)
        reel['장면'], reel['길이'] = scenes, t
        reel['태그'], reel['알림'] = pick_tags(reel, table, most, skipped)
        reel['캡션'], cut = caption(reel['제목'], reel['문장'], end, reel['태그'], total_max)
        if cut:
            skipped.append((f"캡션 문장 {cut}줄 ({reel['제목'][:12]})", f'캡션이 {total_max}자를 넘어서 줄이고 "{MORE}"로 바꿈'))
    return reels, skipped, dict(lo=lo, hi=hi, longest=longest, first_max=first_max, total_max=total_max, most=most)


def checks(reels, c):
    scenes = [s for r in reels for s in r['장면']]
    short = [f"릴스{s['릴스']} 장면{s['장면']}" for s in scenes if s['초'] + 1e-9 < s['필요'] or not c['lo'] <= s['초'] <= c['hi']]
    long_reels = [f"릴스{r['번호']} {r['길이']:g}초" for r in reels if r['길이'] > c['longest']]
    first = [f"릴스{r['번호']} 첫 줄 {len(r['제목'])}자" for r in reels if len(r['제목']) > c['first_max']]
    total = [f"릴스{r['번호']} {len(r['캡션'])}자" for r in reels if len(r['캡션']) > c['total_max']]
    tags = [f"릴스{r['번호']} {len(r['태그'])}개" for r in reels if not 1 <= len(r['태그']) <= c['most']]
    top = max((r['길이'] for r in reels), default=0)
    return [
        (not short and not long_reels, '장면마다 읽을 시간이 충분한가',
         '짧은 장면: ' + ', '.join(short + long_reels) if short or long_reels else f"장면 {len(scenes)}개 모두 충분 · 가장 긴 릴스 {top:g}초"),
        (not first and not total, '캡션이 길이 안인가',
         '넘친 캡션: ' + ', '.join(first + total) if first or total else f"첫 줄 {c['first_max']}자 · 전체 {c['total_max']}자 안"),
        (not tags, '해시태그 개수가 기준 안인가',
         '개수가 벗어난 릴스: ' + ', '.join(tags) if tags else f"릴스마다 1~{c['most']}개"),
    ]


def scene_row(s) -> str:
    mark = f" <small>· {s['표시']}</small>" if s['표시'] else ''
    color = '#f59e0b' if s['표시'] else '#2563eb'
    return (f"<div style='display:flex;gap:10px;align-items:center;margin:5px 0'><small style='width:96px;flex:none'>{clock(s['시작'])}–{clock(s['끝'])}</small>"
            f"<span style='flex:none;height:12px;width:{int(s['초'] * 26)}px;background:{color}'></span><span>{html.escape(s['자막'])}{mark}</span></div>")


def make(open_browser=True):
    reels, skipped, c = build()
    if not reels:
        raise SystemExit('01_기획 기획표에 릴스가 없습니다. 릴스 제목과 장면 문장을 한 줄 이상 적어 주세요.')
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob('릴스*_*.*'):
        old.unlink()
    rows = []
    for r in reels:
        name = f"릴스{r['번호']:02d}"
        srt = '\n'.join(f"{s['장면']}\n{stamp(s['시작'])} --> {stamp(s['끝'])}\n{s['자막']}\n" for s in r['장면'])
        (OUT / f'{name}_자막.srt').write_text(srt, encoding='utf-8')
        (OUT / f'{name}_캡션.txt').write_text(r['캡션'] + '\n', encoding='utf-8')
        rows += [dict(s, 제목=r['제목'], 시작=clock(s['시작']), 끝=clock(s['끝'])) for s in r['장면']]
    write_csv(SCENES, ['릴스', '제목', '장면', '시작', '끝', '초', '글자수', '자막', '표시'], rows)
    results = checks(reels, c)
    cards = []
    for r in reels:
        line = ''.join(scene_row(s) for s in r['장면'])
        info = f"주제 {r['주제'] or '없음'} · {r['길이']:g}초 · 장면 {len(r['장면'])}개" + (f" · {r['알림']}" if r['알림'] else '')
        cards.append(f"<article><h2>릴스 {r['번호']} · {html.escape(r['제목'])}</h2><small>{html.escape(info)}</small>{line}"
                     f"<div class='box'><b>붙여넣을 캡션 · {len(r['캡션'])}자 · 해시태그 {len(r['태그'])}개 · 릴스{r['번호']:02d}_캡션.txt</b>{html.escape(r['캡션'])}</div></article>")
    page = board(f'릴스 {len(reels)}개 자막·캡션', '장면마다 읽을 시간만큼 · 캡션은 길이 안으로 · 해시태그는 기준 개수까지 (주황 = 나누거나 늘린 장면)', results, cards, skipped, '릴스타임라인.html')
    n = sum(len(r['장면']) for r in reels)
    return finish(f"기획표에서 릴스 {len(reels)}개를 읽었습니다. 자막 장면 {n}개, 자막 파일 {len(reels)}개, 캡션 {len(reels)}개를 만들었습니다.", results, page, open_browser)


def main():
    p = argparse.ArgumentParser(description='릴스 자막·캡션 만들기')
    p.add_argument('--work', help='작업 폴더')
    p.add_argument('--no-open', action='store_true', help='결과 화면을 열지 않음')
    a = p.parse_args()
    make(False)


if __name__ == '__main__':
    main()
