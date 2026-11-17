"""cut-list: 표(CSV)를 읽어 결과 표와 화면(HTML)을 만든다. 아무 데도 보내거나 올리지 않는다. 작업 폴더는 --work 로 정한다."""
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
    return Path.cwd() / '컷-리스트'


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

import difflib
import shutil
import subprocess

SAMPLE = ROOT / '01_촬영본' / '촬영본_자막_샘플.srt'
WORDS = ROOT / '02_규칙' / '빼는말.csv'
RULES = ROOT / '02_규칙' / '자르기기준.csv'
CUTS = OUT / '컷리스트.csv'
CLEAN = OUT / '정리된자막.srt'
TIME = re.compile(r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)')
AUDIO_ONLY = ('.mp3', '.wav', '.m4a', '.aac', '.flac')


def sec(h, m, s, ms) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, '0')[:3]) / 1000


def srt_time(t: float) -> str:
    ms = int(round(max(t, 0) * 1000))
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'


def mmss(t: float) -> str:
    return f'{int(t // 60):02d}:{t % 60:04.1f}'


def read_srt(path: Path) -> list[dict]:
    """SRT 자막 파일을 읽어 (시작 초, 끝 초, 자막) 목록으로 만든다."""
    if not path.exists():
        raise SystemExit(f'자막 파일이 없습니다: {path}')
    raw = path.read_bytes()
    for enc in ('utf-8-sig', 'cp949'):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise SystemExit(f'{path.name} 글자가 깨져 있습니다. 자막을 UTF-8 로 다시 내보내 주세요.')
    items = []
    for block in re.split(r'\n\s*\n', text.replace('\r\n', '\n').replace('\r', '\n').strip()):
        lines = block.split('\n')
        for i, line in enumerate(lines):
            m = TIME.search(line)
            if m:
                g = m.groups()
                items.append(dict(시작=sec(*g[:4]), 끝=sec(*g[4:]), 자막=' '.join(x.strip() for x in lines[i + 1:] if x.strip())))
                break
    if not items:
        raise SystemExit(f'{path.name} 에서 자막을 찾지 못했습니다. "00:00:01,000 --> 00:00:03,000" 같은 시간 줄이 있는 SRT 파일인지 확인해 주세요.')
    items.sort(key=lambda x: x['시작'])
    for n, it in enumerate(items, 1):
        it.update(번호=n, 상태='남김', 이유='')
    return items


def settings() -> dict:
    rows = read_csv(RULES)

    def get(name):
        for r in rows:
            if r.get('항목', '').replace(' ', '').startswith(name.replace(' ', '')):
                try:
                    return float(r.get('값', '').replace('%', '').replace('초', '').strip())
                except ValueError:
                    raise SystemExit(f"02_규칙/자르기기준.csv 의 '{name}' 값이 숫자가 아닙니다. 숫자만 적어 주세요 (예: 1.5).")
        raise SystemExit(f"02_규칙/자르기기준.csv 에 '{name}' 줄이 없습니다. 지웠다면 다시 넣어 주세요.")
    return dict(pause=get('쉬는 시간'), pad=get('남길 여유'), like=get('비슷함 기준'), min=get('남은 길이 최소'))


def words() -> set:
    return {w['빼는말'] for w in read_csv(WORDS) if w.get('빼는말')}


def tokens(text: str) -> list[str]:
    return [t for t in re.split(r'[\s,.!?…~·\-]+', text) if t]


def plain(text: str) -> str:
    return re.sub(r'[\W_]+', '', text)


def decide(items, fillers, rule):
    """추임새만 있는 자막과, 바로 다음에 거의 같은 말을 다시 한 자막을 뺀다."""
    talk = []
    for it in items:
        toks = tokens(it['자막'])
        if toks and all(t in fillers for t in toks):
            it.update(상태='뺌', 이유=f"빼는 말만 있음 ('{' '.join(toks)}')")
        else:
            talk.append(it)
    for a, b in zip(talk, talk[1:]):
        like = difflib.SequenceMatcher(None, plain(a['자막']), plain(b['자막'])).ratio() * 100
        if like >= rule['like']:
            a.update(상태='뺌', 이유=f'다시 말함 (다음 자막과 {like:.0f}% 같음)')


def plan(items, rule):
    """자를 곳(시작·끝·이유)과 남길 구간을 정한다. 자른 자리 앞뒤로 숨 쉴 틈을 남긴다."""
    kept = [it for it in items if it['상태'] == '남김']
    if not kept:
        raise SystemExit('남길 자막이 하나도 없습니다. 02_규칙/빼는말.csv 에 너무 많은 말이 들어 있지 않은지 확인해 주세요.')
    total = max(it['끝'] for it in items)
    half = rule['pad'] / 2
    cuts, prev = [], None
    for it in kept + [None]:
        left = prev['끝'] if prev else 0.0
        right = it['시작'] if it else total
        drop = [x for x in items if x['상태'] == '뺌' and x['시작'] >= left - 0.001 and x['끝'] <= right + 0.001]
        gap = right - left
        a = min(left + half, drop[0]['시작']) if prev and drop else (left + half if prev else 0.0)
        b = right if not it else (max(right - half, drop[-1]['끝']) if drop else right - half)
        if (drop or (it and gap > rule['pause'])) and b - a > 0.05:
            if drop:
                why = ' · '.join(x['이유'] for x in drop)
            else:
                why = f'앞부분 빈 시간 {gap:.1f}초' if not prev else f'쉬는 시간 {gap:.1f}초'
            cuts.append(dict(시작=a, 끝=b, 이유=why, 뺀자막=[x['자막'] for x in drop]))
        prev = it
    keeps, pos = [], 0.0
    for c in cuts:
        if c['시작'] > pos:
            keeps.append((pos, c['시작']))
        pos = c['끝']
    if total > pos:
        keeps.append((pos, total))
    return kept, cuts, keeps, total


def shift(t, cuts) -> float:
    return t - sum(c['끝'] - c['시작'] for c in cuts if c['끝'] <= t + 0.001)


def checks(items, kept, cuts, total, left, rule):
    new = [(shift(it['시작'], cuts), shift(it['끝'], cuts)) for it in kept]
    bad = [str(i) for i, (s, e) in enumerate(new, 1) if e <= s or (i > 1 and s < new[i - 2][1] - 0.001)]
    no_reason = [mmss(c['시작']) for c in cuts if not c['이유'].strip()]
    missed = [str(x['번호']) for x in items if x['상태'] == '뺌' and not any(c['시작'] <= x['시작'] + 0.001 and x['끝'] <= c['끝'] + 0.001 for c in cuts)]
    ratio = left / total * 100 if total else 0
    return [
        (not bad, '자막 시간이 겹치지 않나', f'겹친 자막 번호: {", ".join(bad)}' if bad else f'남긴 자막 {len(kept)}개, 겹치는 곳 없음'),
        (not no_reason and not missed, '잘린 곳마다 이유가 있나',
         ('이유 없는 곳: ' + ', '.join(no_reason) + ' ' if no_reason else '') + ('안 잘린 뺀 자막: ' + ', '.join(missed) if missed else '') if no_reason or missed else f'자른 곳 {len(cuts)}곳 모두 이유 있음'),
        (ratio >= rule['min'], '너무 많이 자르지 않았나', f"남은 길이 {ratio:.0f}% (기준 {rule['min']:.0f}% 이상)"),
    ]


def bar(keeps, cuts, total) -> str:
    parts = sorted([(a, b, '#16a34a', '남김') for a, b in keeps] + [(c['시작'], c['끝'], '#f87171', '자름') for c in cuts])
    seg = ''.join(f"<span title='{t} {mmss(a)}~{mmss(b)}' style='flex:{max(b - a, 0.01):.3f};background:{col}'></span>" for a, b, col, t in parts)
    return f"<div style='display:flex;height:18px;gap:1px;margin:8px 0 4px'>{seg}</div><small>초록 = 남긴 곳 · 빨강 = 자른 곳</small>"


def make(srt=None, open_browser=True):
    path = Path(srt).expanduser() if srt else SAMPLE
    rule = settings()
    items = read_srt(path)
    decide(items, words(), rule)
    kept, cuts, keeps, total = plan(items, rule)
    left = sum(b - a for a, b in keeps)
    rows = []
    for a, b in keeps:
        inside = [str(it['번호']) for it in kept if a - 0.001 <= it['시작'] and it['끝'] <= b + 0.001]
        rows.append(dict(구분='남김', 이유=f"자막 {inside[0]}~{inside[-1]}번" if len(inside) > 1 else (f'자막 {inside[0]}번' if inside else '앞뒤 여유'), a=a, b=b))
    rows += [dict(구분='자름', 이유=c['이유'], a=c['시작'], b=c['끝']) for c in cuts]
    rows.sort(key=lambda r: r['a'])
    for r in rows:
        r.update({'시작 시각': mmss(r['a']), '끝 시각': mmss(r['b']), '시작(초)': f"{r['a']:.3f}", '끝(초)': f"{r['b']:.3f}", '길이(초)': f"{r['b'] - r['a']:.2f}"})
    write_csv(CUTS, ['구분', '시작 시각', '끝 시각', '길이(초)', '이유', '시작(초)', '끝(초)'], rows)
    blocks = [f"{n}\n{srt_time(shift(it['시작'], cuts))} --> {srt_time(shift(it['끝'], cuts))}\n{it['자막']}\n" for n, it in enumerate(kept, 1)]
    CLEAN.write_text('\n'.join(blocks), encoding='utf-8')
    results = checks(items, kept, cuts, total, left, rule)
    cut_len = total - left
    cards = [f"<article><h2>원래 {total:.1f}초 → 남은 {left:.1f}초 ({left / total * 100:.0f}%)</h2>"
             f"<p>자른 곳 {len(cuts)}곳 · 잘라낸 길이 {cut_len:.1f}초 · 뺀 자막 {len(items) - len(kept)}개</p>{bar(keeps, cuts, total)}</article>"]
    for i, c in enumerate(cuts, 1):
        cards.append(f"<article><small>자른 곳 {i} · {mmss(c['시작'])} ~ {mmss(c['끝'])} ({c['끝'] - c['시작']:.1f}초)</small><h2>{html.escape(c['이유'])}</h2>"
                     + ''.join(f"<div class='box'><b>뺀 자막</b>{html.escape(t)}</div>" for t in c['뺀자막']) + '</article>')
    skipped = [(it['자막'], it['이유']) for it in items if it['상태'] == '뺌']
    page = board(f'컷 편집 {len(cuts)}곳 · {total:.1f}초 → {left:.1f}초', '자막을 보고 군더더기를 자른 컷 리스트 · 영상 파일은 건드리지 않았습니다', results, cards, skipped, '컷편집.html')
    say(f'컷 리스트: {CUTS}')
    say(f'정리된 자막: {CLEAN}')
    return finish(f'자막 {len(items)}개를 읽었습니다. 남긴 자막 {len(kept)}개, 뺀 자막 {len(items) - len(kept)}개, 자른 곳 {len(cuts)}곳. 길이 {total:.1f}초 → {left:.1f}초.', results, page, open_browser)


def render(video):
    src = Path(video).expanduser()
    if not src.exists():
        raise SystemExit(f'영상 파일이 없습니다: {src}')
    if not CUTS.exists():
        raise SystemExit('먼저 컷 리스트를 만드세요.')
    ff = shutil.which('ffmpeg')
    if not ff:
        say('영상을 실제로 자르려면 ffmpeg 라는 무료 프로그램이 필요합니다. 지금 이 컴퓨터에는 없어요.')
        say('컷 리스트(결과/컷리스트.csv)와 정리된 자막은 이미 만들어져 있으니 그것만 써도 됩니다.')
        say('ffmpeg(영상 자르는 프로그램)가 필요합니다. 설치해도 되는지 사용자에게 먼저 묻고, 허락을 받으면 AI가 설치합니다.')
        sys.exit(1)
    keeps = [(float(r['시작(초)']), float(r['끝(초)'])) for r in read_csv(CUTS) if r.get('구분') == '남김']
    if not keeps:
        raise SystemExit('컷 리스트에 남길 구간이 없습니다. 컷 리스트를 다시 만들어 주세요.')
    expr = '+'.join(f'between(t,{a:.3f},{b:.3f})' for a, b in keeps)
    out = OUT / f'{src.stem}_컷편집{src.suffix or ".mp4"}'
    cmd = [ff, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(src)]
    if src.suffix.lower() not in AUDIO_ONLY:
        cmd += ['-vf', f"select='{expr}',setpts=N/FRAME_RATE/TB"]
    cmd += ['-af', f"aselect='{expr}',asetpts=N/SR/TB", str(out)]
    say(f'남길 구간 {len(keeps)}개로 자르는 중입니다. 영상 길이에 따라 몇 분 걸릴 수 있어요.')
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode:
        raise SystemExit('ffmpeg 가 멈췄습니다. 아래 내용을 AI에게 보여주세요.\n' + r.stderr[-800:])
    say(f'잘린 파일: {out}')
    say('원본 파일은 그대로 두었습니다. 자막은 결과/정리된자막.srt 를 함께 쓰세요.')


def main():
    p = argparse.ArgumentParser(description='촬영본 자막으로 컷 리스트 만들기')
    p.add_argument('--work', help='작업 폴더')
    p.add_argument('--srt', metavar='자막파일', help='내 촬영본 자막(SRT) 파일로 만들기 (없으면 샘플)')
    p.add_argument('--render', metavar='영상파일', help='컷 리스트대로 영상 자르기 (ffmpeg 필요, 선택)')
    p.add_argument('--no-open', action='store_true', help='결과 화면을 열지 않음')
    a = p.parse_args()
    render(a.render) if a.render else make(a.srt, not a.no_open)


if __name__ == '__main__':
    main()
