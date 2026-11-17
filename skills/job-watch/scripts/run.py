"""job-watch: 표(CSV)를 읽어 결과 표와 화면(HTML)을 만든다. 아무 데도 보내거나 올리지 않는다. 작업 폴더는 --work 로 정한다."""
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
    return Path.cwd() / '작업-감시'


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

LOGS = ROOT / '01_기록'
JOBS = ROOT / '02_규칙' / '지켜볼작업.csv'
WORDS = ROOT / '02_규칙' / '실패로볼말.csv'
STATUS = OUT / '작업상태표.csv'
ALERTS = OUT / '보낼알림.txt'
STAMP = re.compile(r'^\[?(\d{4}-\d{2}-\d{2})[ T](\d{1,2}:\d{2})')
LATE = 2  # 마지막 기록이 '몇 분마다'의 이 배수보다 오래되면 멈춤으로 봅니다
PROBLEM = ('실패', '멈춤')
COLOR = {'실패': '#dc2626', '멈춤': '#d97706', '정상': '#16a34a'}


def read_log(path: Path) -> list[str]:
    raw = path.read_bytes()
    for enc in ('utf-8-sig', 'cp949'):
        try:
            return raw.decode(enc).splitlines()
        except UnicodeDecodeError:
            continue
    return raw.decode('utf-8', errors='replace').splitlines()


def last_record(lines):
    """시각이 적힌 마지막 줄부터 끝까지를 '마지막 기록'으로 본다. (Traceback 처럼 시각 없는 줄도 포함)"""
    for i in range(len(lines) - 1, -1, -1):
        m = STAMP.match(lines[i].strip())
        if not m:
            continue
        try:
            when = datetime.strptime(f'{m.group(1)} {m.group(2)}', '%Y-%m-%d %H:%M')
        except ValueError:
            continue
        return when, [x for x in lines[i:] if x.strip()], lines[:i]
    return None, [x for x in lines[-3:] if x.strip()], []


def ago(minutes) -> str:
    m = max(0, int(minutes))
    if m == 0:
        return '방금'
    if m == 1440:
        return '하루'
    if m < 60:
        return f'{m}분'
    if m < 1440:
        return f'{m // 60}시간' + (f' {m % 60}분' if m % 60 else '')
    return f'{m // 1440}일' + (f' {m % 1440 // 60}시간' if m % 1440 // 60 else '')


def jobs() -> list[dict]:
    out = []
    for r in read_csv(JOBS):
        if not r.get('작업 이름'):
            continue
        every = number(r.get('몇 분마다'))
        if every <= 0:
            raise SystemExit(f"02_규칙/지켜볼작업.csv 의 '{r['작업 이름']}' 줄 '몇 분마다' 칸에 숫자를 적어 주세요 (예: 60, 하루 한 번이면 1440).")
        out.append(dict(r, every=every))
    if not out:
        raise SystemExit('02_규칙/지켜볼작업.csv 에 지켜볼 작업을 한 줄 이상 적어 주세요.')
    return out


def fail_hit(lines, words):
    """실패로 볼 말을 찾는다. '이렇게 쓰였으면 괜찮음' 에 적힌 말은 먼저 지우고 찾는다."""
    text, passed = '\n'.join(lines).lower(), []
    for w in words:
        word = (w.get('실패로 볼 말') or '').strip()
        if not word:
            continue
        t = text
        for ok in (w.get('이렇게 쓰였으면 괜찮음') or '').split('/'):
            ok = ok.strip().lower()
            if ok and ok in t:
                t = t.replace(ok, '')
                passed.append(ok)
        if word.lower() in t:
            line = next((x.strip() for x in lines if word.lower() in x.lower()), '')
            return word, line, passed
    return None, '', passed


SAMPLE_LOGS = {'리뷰답글.txt', '매출보고.txt', '스레드발행.txt', '연습_테스트.txt', '재고확인.txt', '주문안내.txt', '카페글.txt'}  # 연습용 기록 파일 이름. 이것만 보고 있으면 샘플 기준 시각을 쓴다


def base_time(arg: str, seen, sample=False):
    if arg in ('지금', 'now') or (not arg and not sample):
        return datetime.now().replace(second=0, microsecond=0), '이 컴퓨터의 지금 시각'
    if arg:
        try:
            return datetime.strptime(arg, '%Y-%m-%d %H:%M'), '직접 정한 시각'
        except ValueError:
            raise SystemExit('--now 는 "지금" 또는 "2026-10-05 18:30" 처럼 적어 주세요.')
    if not seen:
        return datetime.now().replace(second=0, microsecond=0), '이 컴퓨터의 지금 시각 (기록에서 시각을 못 읽음)'
    return max(seen), '연습용 기록이라 기록 안에서 가장 늦은 시각'


def watch(now_arg=''):
    table, words = jobs(), read_csv(WORDS)
    rows = []
    for j in table:
        path = LOGS / j.get('기록 파일', '')
        row = dict(작업=j['작업 이름'], 기록파일=j.get('기록 파일', ''), 주기=('하루에 한 번' if j['every'] == 1440 else ago(j['every']) + '마다'),
                   담당자=j.get('담당자', ''), 상태='', 마지막기록='', 이유='', 알림='', every=j['every'], when=None, block=[], before=[])
        if not row['기록파일'] or not path.is_file():
            row.update(상태='기록 없음', 이유='01_기록 폴더에서 이 기록 파일을 찾지 못함')
        else:
            when, block, before = last_record(read_log(path))
            row.update(when=when, block=block, before=before)
            if when is None:
                row.update(상태='시각 없음', 이유='기록에서 시각(예: 2026-10-05 18:30)을 읽지 못함')
        rows.append(row)
    sample = bool(rows) and all(r['기록파일'] in SAMPLE_LOGS for r in rows)
    base, note = base_time(now_arg, [r['when'] for r in rows if r['when']], sample)
    for r in rows:
        if r['when'] is None:
            continue
        gone = (base - r['when']).total_seconds() / 60
        hit, line, passed = fail_hit(r['block'], words)
        r['마지막기록'] = r['when'].strftime('%m-%d %H:%M')
        if hit:
            r.update(상태='실패', 이유=f"마지막 기록에 '{hit}' — {line[:70]}")
        elif gone > r['every'] * LATE:
            r.update(상태='멈춤', 이유=f"{ago(gone)} 동안 새 기록 없음 ({r['주기']} 도는 작업이라 {ago(r['every'] * LATE)} 넘으면 멈춤)")
        else:
            why = f'{ago(gone)} 전 기록 · {r["주기"]} 도는 작업'
            if passed:
                why += f" · '{passed[0]}'은 괜찮은 말이라 넘김"
            old, _, _ = fail_hit(r['before'], words)
            if old:
                why += f" · 앞선 기록에 '{old}'가 있었지만 그 뒤로 다시 정상"
            r.update(상태='정상', 이유=why)
        if r['상태'] in PROBLEM:
            r['알림'] = '\n'.join([f"[{r['상태']}] {r['작업']}", f"마지막 기록: {r['마지막기록']} ({ago(gone)} 전)", r['이유'],
                                  f"담당: {r['담당자'] or '(없음)'}", "기록 파일: " + (r['기록파일'] if os.path.isabs(r['기록파일']) else '01_기록/' + r['기록파일'])])
    return rows, base, note


def checks(rows):
    missing = [r['작업'] for r in rows if r['상태'] == '기록 없음']
    notime = [r['작업'] for r in rows if r['상태'] == '시각 없음']
    problem = [r for r in rows if r['상태'] in PROBLEM]
    nobody = [r['작업'] for r in problem if not r['담당자']]
    return [
        (not missing, '지켜볼 작업을 빠짐없이 봤나', '기록 파일을 못 찾은 작업: ' + ', '.join(missing) if missing else f'작업 {len(rows)}개 모두 기록 파일을 찾음'),
        (not notime, '기록 시각을 전부 읽었나', '시각을 못 읽은 작업: ' + ', '.join(notime) if notime else f"기록 {sum(1 for r in rows if r['when'])}개 모두 마지막 기록 시각을 읽음"),
        (not nobody, '문제 작업마다 알릴 담당자가 있나', '담당자 없는 작업: ' + ', '.join(nobody) if nobody else (f'문제 {len(problem)}개 모두 담당자 있음' if problem else '문제 작업 없음')),
    ]


def make(open_browser=True, now_arg=''):
    rows, base, note = watch(now_arg)
    stamp = base.strftime('%Y-%m-%d %H:%M')
    for r in rows:
        r['기준시각'] = stamp
    write_csv(STATUS, ['작업', '상태', '마지막기록', '주기', '담당자', '이유', '기록파일', '알림', '기준시각'], rows)
    problem = [r for r in rows if r['상태'] in PROBLEM]
    ALERTS.parent.mkdir(parents=True, exist_ok=True)
    ALERTS.write_text('\n\n'.join(r['알림'] for r in problem) + '\n' if problem else '보낼 알림이 없습니다.\n', encoding='utf-8')
    order = {'실패': 0, '멈춤': 1, '기록 없음': 2, '시각 없음': 3, '정상': 4}
    cards = []
    for r in sorted(rows, key=lambda x: order.get(x['상태'], 9)):
        color = COLOR.get(r['상태'], '#6b7280')
        box = f"<div class='box'><b>보낼 알림</b>{html.escape(r['알림'])}</div>" if r['알림'] else ''
        cards.append(f"<article style='border-left-color:{color}'><small>마지막 기록 {html.escape(r['마지막기록'] or '-')} · {html.escape(r['주기'])} · 담당 {html.escape(r['담당자'] or '(없음)')}</small>"
                     f"<h2><span style='color:{color}'>{html.escape(r['상태'])}</span> · {html.escape(r['작업'])}</h2><p>{html.escape(r['이유'])}</p>{box}</article>")
    watched = {r['기록파일'] for r in rows}
    skipped = [(p.name, '지켜볼 작업표에 없는 기록이라 보지 않음') for p in sorted(LOGS.glob('*')) if p.suffix in ('.txt', '.log') and p.name not in watched]
    count = {s: sum(r['상태'] == s for r in rows) for s in ('정상', '멈춤', '실패')}
    title = f'작업 {len(rows)}개 중 문제 {len(problem)}개' if problem else f'작업 {len(rows)}개 모두 정상'
    page = board(title, f'기준 시각 {stamp} ({note}) · 기록이 주기의 {LATE}배 넘게 끊기면 멈춤, 마지막 기록에 실패로 볼 말이 있으면 실패', checks(rows), cards, skipped, '작업감시.html')
    say(f'기준 시각: {stamp} ({note})')
    return finish(f"작업 {len(rows)}개를 봤습니다. 정상 {count['정상']}개, 멈춤 {count['멈춤']}개, 실패 {count['실패']}개. 보낼 알림 {len(problem)}개 → 결과/보낼알림.txt",
                  checks(rows), page, open_browser)


def main():
    p = argparse.ArgumentParser(description='자동화 작업 감시')
    p.add_argument('--work', help='작업 폴더')
    p.add_argument('--now', default='', help='기준 시각. 비우면 연습 기록 안에서 가장 늦은 시각, "지금"이면 이 컴퓨터 시각, 또는 "2026-10-05 18:30"')
    p.add_argument('--no-open', action='store_true')
    a = p.parse_args()
    make(False, a.now)


if __name__ == '__main__':
    main()
