---
name: detail-page
description: 이커머스 상품 상세페이지·썸네일을 1080px HTML로 만들어 전체 이미지로 렌더링하고 조각내서 카페24 등에 올리는 워크플로. "상세페이지 만들어줘", "썸네일 만들어줘", "판매페이지", "랜딩페이지 이미지", 가격 인상 반영, 디지털 상품 자동 수령 박스 작업일 때 사용.
---

# 상세페이지 제작

전자책·디지털 상품 상세페이지를 **1080px 고정폭 HTML → 롱이미지 렌더 → 조각 업로드**로 만든다.
포토샵 없이 HTML/CSS로 만들고, 수정은 텍스트만 고쳐 재렌더한다.

## 산출물 3종

```
detail_<상품>.html        편집 마스터 (1080px 고정폭)
detail_<상품>_full.png    렌더된 롱이미지 → 상세설명에 업로드
thumbnail_<상품>.html     1000×1000 썸네일 마스터 → 대표이미지
```

## 진행 순서

### 0. 정보 먼저 받기 (없으면 물어본다)

상품명 / 분량·형태 / **정가와 판매가** / 타깃 / 자랑할 실측 수치 / 보너스 /
수령 방식(이메일·링크) / 무료본 존재 여부 / 희소성 장치(한정가·인상).

수치가 없으면 상세페이지가 텅 빈다. **"신뢰도" 섹션에 넣을 숫자 3개는 반드시 확보.**

### 1. 섹션 설계

`references/sections.md` 를 읽고 랜딩 7단계 매핑에 맞춰 섹션 목록을 먼저 정한다.
무료 리드마그넷이면 7섹션, 유료 상품이면 13섹션이 기본. 무료본이 따로 있으면 비교표 필수.

### 2. HTML 작성

`references/template.html` 을 작업 폴더로 복사해서 문구만 교체한다. CSS는 검증된 세트라 건드리지 않는다.

지켜야 할 것:
- `body{ width:1080px; word-break:keep-all }` — 고정폭. 반응형 아님
- **Pretendard 로컬 `@font-face`.** CDN `<link>` 는 headless에서 안 붙어 맑은고딕으로 렌더된다.
  HTML 옆에 `assets/pretendard/*.woff2` 를 둘 것
  (Pretendard는 공개 오픈소스 폰트이므로 공식 배포본의 woff2를 내려받아 쓴다)
- `print-color-adjust:exact` — 배경색이 날아가는 걸 막는다
- 폰트는 웹 감각보다 크게. h1 104 / h2 66 / 본문 25~27px
- 밝은 섹션만 이어붙이지 말고 다크 섹션을 3~4개 간격으로 꽂는다

### 3. 렌더 + 검수

```bash
python <skill>/scripts/render_detail.py detail_x.html detail_x_full.png
# 옵션: --width 1080  --maxh 40000  --jpg
```

Edge headless로 캡처 후 하단 여백을 자동 트림한다. **반드시 눈으로 검수한다** —
긴 이미지는 Read로 한 번에 안 보이므로 4등분해서 각각 확인:

```python
from PIL import Image
im = Image.open("detail_x_full.png"); W,H = im.size; N = 4
for i in range(N):
    p = im.crop((0, i*H//N, W, H if i==N-1 else (i+1)*H//N))
    p.resize((760, round(p.height*760/W))).save(f"chk_{i}.png")
```

보는 항목: 폰트가 Pretendard인가(맑은고딕이면 폰트 로딩 실패) · 글자 넘침 ·
가격 숫자 일치 · 섹션 간 여백 리듬 · 다크/라이트 교차.

### 4. 썸네일

`thumbnail_premium.html` 패턴(1000×1000, flex column + `.spacer`)을 복사.
브랜드 → 배지 → spacer → 아이브로우 → h1 → 가격 → 하단 메타 3칸.
`render_detail.py ... --width 1000` 으로 렌더.

### 5. 조각내서 업로드

```bash
python <skill>/scripts/slice_detail.py detail_x_full.png ./slices --width 800 --chunk 1200
```

목표 높이 ±140px 안에서 여백 줄을 찾아 자르므로 글자가 안 잘린다.
여백을 못 찾으면 경고를 찍는다 — 그때만 눈으로 확인.
업로드 절차·규격은 `references/cafe24-ops.md`.

## 함정 (다 밟아본 것들)

- **`taskkill /IM msedge.exe` 절대 금지.** 유저가 열어둔 브라우저까지 죽는다.
  격리 프로필로 띄우고 자기 PID만 종료 — 스크립트에 이미 반영됨
- **Edge stale 렌더.** 이전 프로세스가 살아있으면 재렌더가 무시되고 이전 파일이 그대로 남는다.
  파일 크기가 그대로면 의심할 것
- **CDN 폰트는 headless에서 안 붙는다.** 무조건 로컬 woff2
- **가격은 3곳(카페24 판매가·상세이미지·썸네일)에 박혀 있다.** 세트로 안 바꾸면 클레임
- **"판매량 늘수록 인상"이라 썼으면 실제로 그렇게 운영해야 한다** (표시광고)
- 이모지·매끄러운 마케팅 카피는 AI티가 난다. 구어체로, 이모지 없이

## 참고 파일

- `references/template.html` — 1080px 전체 CSS + 섹션 골격
- `references/sections.md` — 랜딩 7단계 매핑, 무료/유료 차이, 카피 규칙
- `references/cafe24-ops.md` — 업로드 규격, 주문완료 자동수령 스크립트, 가격 인상 절차
- 사례 구성 예: 무료 7섹션 상세 / 유료 13섹션 상세 / 썸네일 / 주문완료 자동수령 스크립트 — 각각 `references/template.html`에서 파생한다
