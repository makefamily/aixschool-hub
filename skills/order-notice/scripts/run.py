"""order-notice: 주문 표와 안내 규칙으로 주문 안내문을 만들고 검수한다. 메일을 보내지 않는다. 작업 폴더는 --work 로 정한다."""

import argparse
import csv
import html
import os
import re
import shutil
import sys
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
    return Path.cwd() / '주문-안내문'


def _seed():
    """작업 폴더에 없는 연습 자료·규칙 표만 스킬의 samples 에서 복사한다(처음 한 번만)."""
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
    mark.write_text('연습 자료와 규칙 표를 한 번 복사했습니다.\n', encoding='utf-8')


SKILL = Path(__file__).resolve().parent.parent
강의폴더 = _work_dir()
_seed()
주문파일 = 강의폴더 / "01_주문" / "주문_3건.csv"
규칙파일 = 강의폴더 / "02_규칙" / "안내규칙.csv"
결과폴더 = 강의폴더 / "결과"


def 표읽기(경로):
    """엑셀에서 저장한 CSV도 한글이 깨지지 않게 읽는다."""
    if not 경로.exists():
        raise SystemExit(f"[없음] 파일을 찾지 못했습니다: {경로}")
    for 인코딩 in ("utf-8-sig", "cp949", "utf-8"):
        try:
            with 경로.open(encoding=인코딩, newline="") as f:
                줄 = [r for r in csv.DictReader(f) if any((v or "").strip() for v in r.values())]
            if 줄:
                return 줄
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"[읽기 실패] 파일을 열었지만 글자가 깨집니다: {경로}")


def 안내문만들기(주문, 규칙):
    틀 = (규칙.get("안내문장틀") or "").strip()
    값 = {
        "구매자": (주문.get("구매자") or "").strip(),
        "상품명": (주문.get("상품명") or "").strip(),
        "옵션": (주문.get("옵션") or "").strip(),
        "주문번호": (주문.get("주문번호") or "").strip(),
        "주문일시": (주문.get("주문일시") or "").strip(),
        "자료링크": (규칙.get("자료링크") or "").strip(),
    }
    본문 = 틀
    for 이름, 내용 in 값.items():
        본문 = 본문.replace("{" + 이름 + "}", 내용)
    남은칸 = re.findall(r"\{([^}]+)\}", 본문)
    return 본문, 남은칸


def 검수하기(본문, 주문, 규칙):
    """세 가지를 본다. 통과하면 빈 목록을 돌려준다."""
    문제 = []

    링크 = (규칙.get("자료링크") or "").strip()
    if not 링크:
        문제.append("규칙에 자료 링크가 비어 있습니다")
    elif 링크 not in 본문:
        문제.append("안내문에 자료 링크가 안 들어갔습니다")

    주문에있는숫자 = set(re.findall(r"\d+", " ".join(str(v) for v in 주문.values())))
    for 숫자, 단위 in re.findall(r"(\d+)\s*(일|주|개월|시간|분|%)", 본문):
        if 숫자 not in 주문에있는숫자:
            문제.append(f"주문에 없는 말이 들어갔습니다: '{숫자}{단위}'")

    금지 = [w.strip() for w in (규칙.get("넣으면안되는말") or "").split("|") if w.strip()]
    for 말 in 금지:
        if 말 in 본문:
            문제.append(f"넣으면 안 되는 말이 들어갔습니다: '{말}'")

    return 문제


def 미리보기저장(결과들, 경로):
    조각 = []
    for r in 결과들:
        상태 = "통과" if not r["문제"] else "확인 필요"
        색 = "#1a7f37" if not r["문제"] else "#c4320a"
        문제줄 = "".join(f"<li>{html.escape(m)}</li>" for m in r["문제"]) or "<li>세 가지 모두 통과</li>"
        조각.append(f"""
        <section class="mail">
          <div class="head">
            <div><b>받는 사람</b> {html.escape(r['받는사람'] or '(아직 안 적음)')}</div>
            <div><b>제목</b> {html.escape(r['제목'])}</div>
            <div class="tag" style="background:{색}">{상태}</div>
          </div>
          <pre>{html.escape(r['본문'])}</pre>
          <div class="check"><b>검수</b><ul>{문제줄}</ul></div>
        </section>""")

    문서 = f"""<!doctype html><html lang="ko"><meta charset="utf-8">
<title>주문 안내문 미리보기</title>
<style>
 body{{font-family:-apple-system,'Malgun Gothic',sans-serif;background:#f4f5f7;margin:0;padding:32px 16px;color:#1c1c1e}}
 h1{{font-size:20px;margin:0 auto 6px;max-width:760px}}
 p.lead{{max-width:760px;margin:0 auto 24px;color:#555;font-size:14px}}
 .mail{{max-width:760px;margin:0 auto 20px;background:#fff;border:1px solid #e3e5e8;border-radius:10px;overflow:hidden}}
 .head{{padding:14px 18px;border-bottom:1px solid #eee;font-size:13px;color:#444;position:relative}}
 .head b{{color:#888;font-weight:600;margin-right:8px}}
 .tag{{position:absolute;top:14px;right:18px;color:#fff;font-size:12px;padding:3px 10px;border-radius:99px}}
 pre{{margin:0;padding:18px;white-space:pre-wrap;font-family:inherit;font-size:15px;line-height:1.7}}
 .check{{padding:12px 18px;border-top:1px solid #eee;background:#fafbfc;font-size:13px;color:#444}}
 .check ul{{margin:6px 0 0;padding-left:18px}}
</style>
<h1>주문 안내문 미리보기</h1>
<p class="lead">메일로 보내기 전 화면입니다. 실제로 발송된 것이 아닙니다.
아래 세 가지를 보세요 — 상품에 맞는 자료 링크가 붙었는지, 주문에 없는 말이 있는지, 넣으면 안 되는 말이 있는지.</p>
{''.join(조각)}
</html>"""
    경로.write_text(문서, encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="주문 안내문을 만들고 검수합니다.")
    p.add_argument("--work", help="작업 폴더")
    아규 = p.parse_args()

    주문들 = 표읽기(주문파일)
    규칙들 = {(r.get("상품명") or "").strip(): r for r in 표읽기(규칙파일)}

    결과폴더.mkdir(exist_ok=True)
    결과들, 막힌곳 = [], []

    print(f"주문 {len(주문들)}건을 읽었습니다. 안내문을 만듭니다.\n")
    for 주문 in 주문들:
        상품 = (주문.get("상품명") or "").strip()
        규칙 = 규칙들.get(상품)
        if not 규칙:
            막힌곳.append(f"'{상품}' 은 안내 규칙에 없습니다. 02_규칙/안내규칙.csv 에 한 줄 추가하세요.")
            continue

        본문, 남은칸 = 안내문만들기(주문, 규칙)
        문제 = 검수하기(본문, 주문, 규칙)
        if 남은칸:
            문제.append("문장 틀에 채우지 못한 칸이 있습니다: " + ", ".join(남은칸))

        제목 = f"[{상품}] 주문해 주셔서 감사합니다"
        결과들.append({
            "주문번호": (주문.get("주문번호") or "").strip(),
            "상품명": 상품,
            "받는사람": (주문.get("받을메일") or "").strip(),
            "제목": 제목,
            "본문": 본문,
            "문제": 문제,
            "쓴규칙": (규칙.get("안내종류") or "").strip(),
            "쓴링크": (규칙.get("자료링크") or "").strip(),
        })

        표시 = "OK" if not 문제 else "확인 필요"
        print(f"[{표시}] {주문.get('주문번호')} · {상품}")
        print(f"       쓴 규칙: {규칙.get('안내종류')} / 붙인 자료: {규칙.get('자료링크')}")
        for m in 문제:
            print(f"       - {m}")
        (결과폴더 / f"{주문.get('주문번호')}_{상품}.txt").write_text(
            제목 + "\n\n" + 본문 + "\n", encoding="utf-8")

    for m in 막힌곳:
        print(f"[막힘] {m}")

    미리보기 = 결과폴더 / "미리보기.html"
    미리보기저장(결과들, 미리보기)

    확인필요 = sum(1 for r in 결과들 if r["문제"])
    print(f"\n안내문 {len(결과들)}개를 만들었습니다. 확인 필요 {확인필요}개.")
    print(f"저장한 곳: {결과폴더}")

    print("아직 아무 데도 보내지 않았습니다. 안내문은 결과 폴더의 파일과 미리보기 화면으로 확인합니다.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
