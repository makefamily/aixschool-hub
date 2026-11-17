---
name: korean-docs
description: 한글 문서(HWP/HWPX)를 읽고, 양식의 빈칸을 채우고, 서명 이미지를 넣고, 페이지가 늘어나지 않았는지 검증한다. 트리거 - "한글 파일 채워줘", "hwp/hwpx 작성", "참가신청서/제출서류/신청서 작성", "공모전 양식", "한글 문서 읽어줘", ".hwp/.hwpx 첨부 파일 처리", "한글 문서 내용 뽑아줘". 맥에 한컴오피스가 없어도 전부 동작한다.
---

# 한글 문서 처리

한컴오피스 없이 macOS에서 HWP/HWPX를 읽고 쓴다. 도구 4개를 역할별로 나눠 쓴다.

## 도구 역할 (2026-08-01 실측 기준)

| 도구 | 스타 | 역할 | 호출 |
|---|---|---|---|
| **kordoc** | 1,575 | 읽기·SVG 렌더·표기법 lint·개인정보 마스킹 | `kordoc` CLI (MCP로 등록돼 있으면 MCP도 사용) |
| **rhwp** | 3,623 | 엔진(hwp/hwpx/hml 파싱·조판·저장·Field API) | npm `@rhwp/core`, Rust |
| **HOP** | 1,583 | 데스크탑 앱 — 사람이 열어보고 편집 | `/Applications/HOP.app` |
| **python-hwpx** | 102 | HWPX 셀 단위 정밀 편집 | `pip install python-hwpx` |

- **읽기만 필요하면 kordoc(MCP나 CLI)이 있으면 그것을 쓴다.** hwp/hwpx/pdf/xlsx/docx/이미지를 바로 읽는다. 없으면 python-hwpx로 읽는다.
- **양식 채우기는 python-hwpx + lxml.** kordoc에는 임의 셀 채우기 CLI가 없다.
- **육안 확인은 HOP** 또는 `kordoc render`(아래).
- 구형 `.hwp`에 **써서 저장**해야 하면 rhwp를 검토한다. python-hwpx는 HWPX 전용이다.

## 표준 절차

### 1. 구조 파악 (눈대중 금지)
```python
from hwpx import HwpxDocument
d = HwpxDocument.open(path)
for t in d.get_table_map()["tables"]:
    grid = {(c["row"], c["col"]): c["text"] for c in t["cells"]}
```
표 인덱스와 (row, col)을 **반드시 출력해서 확인한 뒤** 채운다.

### 2. 채우기
- 라벨이 유일하면 `d.fill_by_path({"곡 명 > right": "값"})`
- 라벨이 중복되거나(성명·생년월일 등) 빈 행이면 lxml로 `cellAddr`의 `rowAddr`/`colAddr`을 직접 짚는다
- 빈 셀은 `<hp:run charPrIDRef="9"/>` 자기닫힘 구조다. `<hp:t>`를 만들어 넣어야 한다

### 3. 예시 서식 제거
관공서 양식은 예시값이 **파란 이탤릭**(예: `charPr` textColor `#0000FF`)이다. 그 자리에 값을 쓰면 서식을 그대로 물려받는다.
`header.xml`에서 **같은 height·같은 fontRef의 검정 charPr을 찾아 교체**한다. 대개 짝이 이미 존재한다.

### 4. 검증 게이트 (건너뛰지 말 것)
```bash
python3 scripts/fit_check.py 결과.hwpx --baseline 원본.hwpx
kordoc render 결과.hwpx -o out.svg      # "렌더 (N페이지, ... 이미지 N)" 확인
```
- `fit_check.py`가 exit 1이면 셀이 넘쳐 **페이지가 늘어난다**. 텍스트를 줄이거나 작은 charPr을 쓴다
- `kordoc render` 출력의 **페이지 수와 이미지 수**를 눈으로 확인한다. `이미지 바이너리 누락` 경고가 뜨면 manifest가 깨진 것
- SVG를 PNG로 보려면 폰트를 치환한다(변환기에 한글 폰트가 없다):
  ```python
  s = re.sub(r'font-family="[^"]+"', 'font-family="AppleGothic"', open('out.svg').read())
  cairosvg.svg2png(bytestring=s.encode(), write_to='out.png', output_width=880)
  ```
- 마지막은 **HOP로 열어 사람이 확인**한다

### 5. 이미지 삽입
기존 `hp:pic`을 deepcopy해서 `binaryItemIDRef`·`orgSz`·`curSz`·`scaMatrix`·`imgRect`·`imgClip`·`imgDim`·`sz`를 일관되게 바꾼다. 그리고 **세 곳을 동시에** 맞춘다.
1. `BinData/imageN.BMP` 바이너리 추가
2. `Contents/content.hpf` manifest에 `<opf:item>` 추가(href·media-type·md5 hashkey)
3. 셀 문단에 `hp:pic` run 삽입

**확장자 대소문자를 원본과 맞춘다**(원본이 `.BMP`면 `.BMP`).

### 6. 재압축
```python
zi = zipfile.ZipInfo("mimetype"); zi.compress_type = zipfile.ZIP_STORED
zout.writestr(zi, data)          # mimetype은 반드시 무압축
```
나머지는 원본 항목 순서대로 DEFLATED. 네임스페이스는 lxml로 파싱→직렬화하면 보존된다.

## 지뢰 목록 (전부 2026-08-01에 실제로 밟은 것)

1. **조사 결과에 나온 모르는 이름은 반드시 한 번 실측한다.** "rhwp 기반"이라는 문구를 보고도 rhwp를 안 찍어봐서 스타 3,623개짜리 본체를 놓쳤다. 스타·연혁으로만 고르면 급성장 중인 신생을 통째로 놓친다
2. **lxml `iter()` 인덱스 ≠ 정규식 매칭 인덱스.** 자기닫힘 `<hp:t/>`가 iter에는 잡히고 정규식에는 안 잡혀 엉뚱한 셀을 덮어썼다. 인덱스 대신 **내용·좌표로 매칭**한다
3. **표 인덱스를 세어서 쓰지 말 것.** `tbls[1]`이 본표일 거라 가정했다가 7칸이 FAIL 났다. 실제로는 `tbls[2]`였다. 중첩 표가 있다
4. **manifest와 실제 바이너리 불일치.** 정규식 `[^/]*`가 href의 슬래시 때문에 매칭 실패해 manifest는 png, 파일은 bmp가 됐다. `[^>]*?`를 쓰고 **치환 건수를 반드시 출력해 확인**한다
5. **docx/Google Docs 경유 변환 금지.** HWPX를 Docs로 변환했더니 동의 조항 6개 항목이 통째로 사라졌다. 텍스트 상자·병합 셀이 유실된다
6. **PDF 오버레이는 최후 수단.** 좌표를 눈대중으로 찍으면 3회 이상 재작업한다. 꼭 해야 하면 마커 그리드를 먼저 렌더해 좌표를 실측한다
7. **`validate()` 통과 ≠ 열린다.** python-hwpx validate가 issues 0이어도 렌더 엔진이 못 읽을 수 있다. `kordoc render`까지 통과시킨다

## 산출물 규칙

- 제출용은 **원본 양식을 그대로 채운 HWPX**가 1순위다. 새로 만든 문서로 대체하지 않는다
- 원본 파일은 절대 덮어쓰지 않고 별도 이름으로 저장한다
- 완료 보고에 `file://` 절대경로 링크를 준다(한글·공백은 percent-encoding)
