"""shorts-cutter: 표(CSV)를 읽어 결과 표와 화면(HTML)을 만든다. 아무 데도 보내거나 올리지 않는다. 작업 폴더는 --work 로 정한다."""
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
    return Path.cwd() / '숏폼-후보'


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

SRT_IN = ROOT / '01_자막' / '라이브_자막_샘플.srt'
LENGTH = ROOT / '02_규칙' / '숏폼길이.csv'
HOOKS = ROOT / '02_규칙' / '훅말.csv'
CUT = ROOT / '02_규칙' / '빼는구간.csv'
LIST = OUT / '숏폼후보.csv'
PAUSE = 2.0     # 자막 사이가 이만큼(초) 비면 이야기가 끊긴 자리로 본다
HOOK_SEC = 3.0  # 첫 몇 초 안에 시작하는 자막으로 점수를 매길지


def sec(ts: str) -> float:
    h, m, s = ts.strip().replace('.', ',').split(':')
    s, _, ms = s.partition(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int((ms or '0').ljust(3, '0')[:3]) / 1000


def stamp(x: float) -> str:
    ms = int(round(max(0.0, x) * 1000))
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'


def clock(x: float) -> str:
    x = int(x)
    return f'{x // 3600:02d}:{x // 60 % 60:02d}:{x % 60:02d}'


def read_srt(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f'자막 파일이 없습니다: {path}')
    raw = None
    for enc in ('utf-8-sig', 'cp949'):
        try:
            raw = path.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if raw is None:
        raise SystemExit(f'{path.name} 파일 글자가 깨져 있습니다. 자막 앱에서 UTF-8 로 다시 내보내 주세요.')
    cues = []
    for block in re.split(r'\n\s*\n', raw.replace('\r\n', '\n').replace('\r', '\n').strip()):
        lines = [x.strip() for x in block.split('\n') if x.strip()]
        at = next((i for i, x in enumerate(lines) if '-->' in x), None)
        if at is None:
            continue
        a, b = lines[at].split('-->')
        text = re.sub(r'<[^>]+>', '', ' '.join(lines[at + 1:])).strip()
        try:
            start, end = sec(a), sec(b.split()[0])
        except (ValueError, IndexError):
            continue
        if text and end > start:
            cues.append({'시작': start, '끝': end, '자막': text})
    if not cues:
        raise SystemExit(f'{path.name} 에서 자막을 한 줄도 읽지 못했습니다. .srt 파일이 맞는지 확인해 주세요.')
    return sorted(cues, key=lambda c: c['시작'])


def length_rules() -> dict:
    rows = {r.get('항목', ''): r.get('값', '') for r in read_csv(LENGTH)}
    need = {'가장 짧게(초)': 'short', '가장 길게(초)': 'long', '자막 한 줄 글자 수': 'line', '뽑을 개수': 'count'}
    out = {}
    for name, key in need.items():
        v = number(rows.get(name, ''), -1)
        if v <= 0:
            raise SystemExit(f"02_규칙/숏폼길이.csv 의 '{name}' 칸에 0보다 큰 숫자를 적어 주세요.")
        out[key] = v
    if out['short'] >= out['long']:
        raise SystemExit('02_규칙/숏폼길이.csv 에서 가장 짧게(초)는 가장 길게(초)보다 작아야 합니다.')
    out['line'], out['count'] = max(4, int(out['line'])), int(out['count'])
    return out


def hook_hits(text: str, hooks) -> list:
    hits = []
    for h in hooks:
        word = h.get('훅 말', '')
        if word and (re.search(r'\d', text) if word == '(숫자)' else word in text):
            hits.append((word, number(h.get('점수'), 1)))
    return hits


def pieces(cues, cut_words):
    """빼는 말이 든 자막을 빼고, 2초 넘게 말이 끊긴 자리에서 이야기 덩어리로 나눈다."""
    groups, cur, dropped = [], [], []
    for c in cues:
        bad = next((w for w in cut_words if w in c['자막']), None)
        if bad:
            dropped.append((c['자막'][:30], f"빼는 말 '{bad}' · {clock(c['시작'])}"))
            if cur:
                groups.append(cur)
            cur = []
            continue
        if cur and c['시작'] - cur[-1]['끝'] >= PAUSE:
            groups.append(cur)
            cur = []
        cur.append(c)
    if cur:
        groups.append(cur)
    return groups, dropped


def candidates(groups, rules, hooks):
    """덩어리마다 가장 길게 안으로 줄이고, 가장 짧게보다 짧으면 버리고, 첫 3초 훅 말로 점수를 매긴다."""
    found, skipped = [], []
    for g in groups:
        start = g[0]['시작']
        keep = [c for c in g if c['끝'] - start <= rules['long']]
        if not keep:
            skipped.append((g[0]['자막'][:30], f"자막 한 줄이 {rules['long']:g}초보다 김 · {clock(start)}"))
            continue
        if keep[-1]['끝'] - start < rules['short']:
            skipped.append((g[0]['자막'][:30], f"너무 짧음 ({keep[-1]['끝'] - start:.0f}초) · {clock(start)}"))
            continue
        hits = hook_hits(' '.join(c['자막'] for c in keep if c['시작'] - start < HOOK_SEC), hooks)
        note = f"{g[-1]['끝'] - start:.0f}초짜리 이야기에서 {rules['long']:g}초 안으로 줄임" if len(keep) < len(g) else '이야기 한 덩어리 그대로'
        found.append({'시작초': start, '끝초': keep[-1]['끝'], '길이': keep[-1]['끝'] - start, '자막들': keep, '첫 문장': keep[0]['자막'],
                      '점수': sum(p for _, p in hits), '훅 말': '·'.join(w for w, _ in hits), '메모': note})
    return found, skipped


def pick(found, count):
    chosen, rest = [], []
    for f in sorted(found, key=lambda x: (-x['점수'], x['시작초'])):
        if len(chosen) >= count:
            rest.append((f['첫 문장'][:30], f"점수 {f['점수']:g}점 · {count}개 안에 못 듦 · {clock(f['시작초'])}"))
        elif any(f['시작초'] < c['끝초'] and c['시작초'] < f['끝초'] for c in chosen):
            rest.append((f['첫 문장'][:30], '앞 후보와 겹침'))
        else:
            chosen.append(f)
    return chosen, rest


def wrap(text: str, width: int) -> list[str]:
    lines, cur = [], ''
    for w in text.split():
        while len(w) > width:
            if cur:
                lines.append(cur)
                cur = ''
            lines.append(w[:width])
            w = w[width:]
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f'{cur} {w}'.strip()
    if cur:
        lines.append(cur)
    return lines


def short_srt(f, width):
    """세로 영상용: 0초부터 다시 매기고, 한 줄 글자 수를 넘으면 자막을 쪼갠다."""
    out = []
    for c in f['자막들']:
        a, b = c['시작'] - f['시작초'], c['끝'] - f['시작초']
        parts = wrap(c['자막'], width)
        total = sum(len(p) for p in parts) or 1
        t = a
        for p in parts:
            e = t + (b - a) * len(p) / total
            out.append((t, e, p))
            t = e
    return out


def checks(chosen, rules):
    bad_len = [f"{i}번 {x['길이']:.0f}초" for i, x in enumerate(chosen, 1) if not rules['short'] <= x['길이'] <= rules['long'] + 0.001]
    over = [f'{i}번·{j}번' for i, x in enumerate(chosen, 1) for j, y in enumerate(chosen, 1) if i < j and x['시작초'] < y['끝초'] and y['시작초'] < x['끝초']]
    nohook = [f'{i}번' for i, x in enumerate(chosen, 1) if not x['훅 말']]
    return [
        (bool(chosen) and not bad_len, '숏폼 길이가 정해둔 범위 안인가',
         ('범위 밖: ' + ', '.join(bad_len)) if bad_len else (f"모두 {rules['short']:g}~{rules['long']:g}초 안" if chosen else '후보가 하나도 없습니다. 길이 범위를 넓혀 보세요')),
        (not over, '후보끼리 겹치지 않나', '겹친 후보: ' + ', '.join(over) if over else '겹치는 구간 없음'),
        (not nohook, '첫 3초 안에 훅 말이 있나', '훅 말 없는 후보: ' + ', '.join(nohook) if nohook else '모든 후보의 첫 3초에 훅 말 있음'),
    ]


def make(srt_path=None, open_browser=True):
    rules = length_rules()
    hooks = read_csv(HOOKS)
    cut_words = [r['빼는 말'] for r in read_csv(CUT) if r.get('빼는 말')]
    src = Path(srt_path).expanduser().resolve() if srt_path else SRT_IN
    cues = read_srt(src)
    groups, dropped = pieces(cues, cut_words)
    found, too_short = candidates(groups, rules, hooks)
    chosen, rest = pick(found, rules['count'])
    OUT.mkdir(exist_ok=True)
    for old in list(OUT.glob('숏폼_*.srt')):
        old.unlink()
    rows, cards = [], []
    for i, f in enumerate(chosen, 1):
        subs = short_srt(f, rules['line'])
        name = f'숏폼_{i}.srt'
        (OUT / name).write_text(''.join(f'{n}\n{stamp(a)} --> {stamp(b)}\n{t}\n\n' for n, (a, b, t) in enumerate(subs, 1)), encoding='utf-8')
        rows.append({'순위': i, '시작': clock(f['시작초']), '끝': clock(f['끝초']), '길이(초)': f"{f['길이']:.1f}", '첫 문장': f['첫 문장'],
                     '점수': f"{f['점수']:g}", '훅 말': f['훅 말'], '자막 파일': name, '메모': f['메모'], '시작초': f"{f['시작초']:.3f}", '끝초': f"{f['끝초']:.3f}"})
        preview = '\n'.join(f'{a:4.1f}초  {t}' for a, _, t in subs[:6]) + ('\n…' if len(subs) > 6 else '')
        cards.append(f"<article><small>{i}번 · {clock(f['시작초'])} ~ {clock(f['끝초'])} · {f['길이']:.0f}초 · 점수 {f['점수']:g}"
                     f"{' (' + html.escape(f['훅 말']) + ')' if f['훅 말'] else ''} · {html.escape(f['메모'])}</small>"
                     f"<h2>{html.escape(f['첫 문장'])}</h2><div class='box'><b>세로 자막 {len(subs)}줄 · {name} · 한 줄 {rules['line']}자 이하</b>{html.escape(preview)}</div></article>")
    write_csv(LIST, ['순위', '시작', '끝', '길이(초)', '첫 문장', '점수', '훅 말', '자막 파일', '메모', '시작초', '끝초'], rows)
    results = checks(chosen, rules)
    page = board(f'숏폼 후보 {len(chosen)}개', f"{src.name} · 자막 {len(cues)}줄 · {rules['short']:g}~{rules['long']:g}초 · 첫 3초 훅 말 점수 순",
                 results, cards, dropped + too_short + rest, '숏폼후보.html')
    return finish(f'자막 {len(cues)}줄을 읽었습니다. 이야기 덩어리 {len(groups)}개 중 숏폼 후보 {len(chosen)}개를 골랐습니다.', results, page, open_browser)


# ---------------------------------------------------------------- 선택: 원본 영상에서 세로(9:16)로 자르기 (ffmpeg 필요)
def render(video):
    import shutil
    import subprocess
    ff = shutil.which('ffmpeg')
    if not ff:
        say('ffmpeg(무료 영상 도구)가 이 컴퓨터에 없어서 영상을 자르지 않았습니다.')
        say('ffmpeg(영상 자르는 프로그램)가 필요합니다. 설치해도 되는지 사용자에게 먼저 묻고, 허락을 받으면 AI가 설치한 뒤 다시 실행하세요. 숏폼 후보표와 자막 파일은 지금도 그대로 쓸 수 있습니다.')
        return
    src = Path(video).expanduser()
    if not src.exists():
        raise SystemExit(f'영상 파일이 없습니다: {src}')
    if not LIST.exists():
        raise SystemExit('먼저 숏폼 후보표를 만드세요.')
    picked = [{'시작초': number(r['시작초']), '끝초': number(r['끝초']), '길이': number(r['길이(초)']), '훅 말': r.get('훅 말', ''), '자막 파일': r['자막 파일']}
              for r in read_csv(LIST)]
    fails = [t for ok, t, _ in checks(picked, length_rules()) if not ok]
    if fails:
        raise SystemExit('확인 필요가 남아 있어 자르지 않습니다: ' + ' / '.join(fails))
    say(f'숏폼 {len(picked)}개를 세로(9:16)로 자릅니다. 원본 영상은 건드리지 않습니다.')
    for i, p in enumerate(picked, 1):
        out = OUT / p['자막 파일'].replace('.srt', '.mp4')
        cmd = [ff, '-y', '-loglevel', 'error', '-ss', f"{p['시작초']:.3f}", '-i', str(src), '-t', f"{p['끝초'] - p['시작초']:.3f}",
               '-vf', "crop='min(iw,ih*9/16)':'min(ih,iw*16/9)',scale=1080:1920,setsar=1",
               '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', str(out)]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if r.returncode:
            raise SystemExit(f'{out.name} 을 만들지 못했습니다: {r.stderr.strip()[-300:]}')
        say(f"  {i}/{len(picked)} {out.name} ({p['길이']:.0f}초)")
    say(f'다 잘랐습니다. 결과 폴더: {OUT}')
    say('자막은 같은 이름의 .srt 파일을 영상 앱에 불러와 얹으세요. 올리는 건 직접 합니다.')


def main():
    p = argparse.ArgumentParser(description='긴 영상 자막에서 숏폼 후보 고르기')
    p.add_argument('--work', help='작업 폴더')
    p.add_argument('--srt', help='내 영상 자막(.srt) 경로. 없으면 샘플 자막을 씁니다')
    p.add_argument('--render', metavar='영상파일', help='고른 후보를 원본 영상에서 세로(9:16)로 자르기 (ffmpeg 필요)')
    p.add_argument('--no-open', action='store_true', help='결과 화면을 열지 않음')
    a = p.parse_args()
    render(a.render) if a.render else make(a.srt, not a.no_open)


if __name__ == '__main__':
    main()
