# 덱 스타일 v2 틀 (2026-11-12)

뿌리: 검증된 전환형 웨비나 덱. 가져온 것은 구조·레이아웃·구성·글꼴·흐름이고, 색과 내용은 덱마다 바꾼다.

## 쓰는 법

1. 새 덱 폴더에 `build.py deck.css deck.js slides.py`를 복사하고 `media/`를 만든다.
2. `slides.py`의 `META`와 `D`를 고친다.
3. `python build.py` → `deck.html`. 공유용 한 파일은 `--share`. 자료 요청 목록은 `--needs`.
4. 검사: 덱 폴더에서 `python -m http.server 8765 --bind 127.0.0.1` 후 `python ../../scripts/deck_lint.py deck.html [프롬프터.html] --render <브라우저 주소창에 뜨는 로컬 주소>/deck.html` FAIL 0.

## META

```python
META = {
  "title": "탭 제목",
  "foot": "강사 이름 · 소속",          # 바닥줄 가운데
  "theme": {"--brand": "#7A22B5", ...},       # 없으면 deck.css 기본(딥네이비·노랑)
  "labels": {"chap": "CHAPTER {n}"},          # 라벨 바꾸기. 기본은 한글(1부·질문·답·혜택 1·1단계·오늘 순서)
  "nobox": False,                             # True면 카드 바탕을 뺀 변형(스타일 v1의 박스 금지를 적용한 모양)
}
```

색 변수(`deck.css` 맨 위): `--ink` 글자 · `--brand` 강조 칸 · `--acc` 어두운 칸 위 숫자·라벨 · `--tint` 연한 칸 · `--k` 어두운 바탕 · `--p`/`--p-ink` 브랜드 바탕과 그 위 글자 · `--em`/`--em-bg` 흰 바탕 강조(기본은 노랑 형광펜 밑줄) · `--em-k` 어두운 바탕 강조 · `--mark*` 칠한 띠.

보라로 바꾸는 예: `{"--brand":"#7A22B5","--acc":"#FFD84D","--k":"#140D19","--p":"#7A22B5","--p-ink":"#fff","--em":"#7A22B5","--em-bg":"none","--em-k":"#D29BFF","--em-p":"#FFD84D","--em-p-bg":"none","--tint":"#F3E8FB","--tint-k":"#21172A","--label":"#7A22B5","--label-p":"rgba(255,255,255,.85)","--mark":"#7A22B5","--mark-ink":"#fff","--mark-p":"#fff","--mark-p-ink":"#7A22B5"}`

## 장 유형 (`k`)

| k | 쓰임 | 주요 값 |
|---|---|---|
| cover | 표지(글+사진) | eyebrow, title, sub, img |
| hero | 큰 글자 한 장 | title, sub, eyebrow, size(xxl·xl·l), align, bg |
| chap | 부 전환 | n, title |
| qa | 질문 → 누르면 답 (img·need 주면 옆에 화면) | n, ask, title, img, need |
| proof | 제목 + 큰 캡처 | title, img 또는 need, cap |
| gal | 원본 비율 이미지 모음 / 옆 배치 / 배경 | rows, lay(top·side·bg), items |
| phone | 휴대폰 틀 1~3개(이미지·mp4) | shots |
| case | 사례(이름·태그·전후) | who, tags, before, after, img |
| split | 사진 + 글·체크 | img, items, side |
| poll | 번호 투표(손들기·채팅) — 보기 4개면 2×2, 5~6개면 3열 격자로 자동 줄바꿈 | options |
| screen | 따라하기(가이드) 페이지 화면을 덱 전체에 꽉 차게. 제목·바닥줄 없음 | img(960×540·2배 캡처 = 1920×1080), box |
| market | 시중 서비스 한 장: 공개 페이지 실제 캡처 + 가격 태그 → '이런 걸 돈 주고 써요 ↓ 우리는' | img(png·jpg·mp4), tag(공식 페이지 확인 가격만, 없으면 생략), tag_alt, src, side=[(제목,설명),(제목,설명)] |
| cal | 한 달 달력: 오늘·수업·기간 띠 | year, month, marks={일:(today·class·span, 글)}, legend, sub |
| vs | 비교(누르면 하나씩) | left, right |
| steps4 | 단계 칸, 지금 위치 밝히기 | steps=[(아이콘,제목,설명)], active |
| chain | 흐름 사슬(누르면 하나씩) | nodes |
| flow | 역할이 갈리는 진행 순서 | steps=[("저희"/"내가", 아이콘, 제목, 설명)], band |
| stats | 숫자 칸(올라가는 숫자, 소수 가능) | items=[(아이콘,라벨,값,단위,설명)] |
| bars | 막대 비교 | rows=[(라벨,값,표시)] |
| equation | A × B = C | parts |
| timeline | 시간 순서 | items=[(시점,내용,나쁨)], active |
| reasons | 이유·문제 목록(빨강) | items, icon |
| checklist | 체크 목록(누르면 하나씩) | items |
| countdown | 실습 타이머 | sec |
| toc | 오늘 순서 | items=[(제목,설명)] |
| benefit | 혜택 한 장 | n, icon, title, img |
| total | 혜택 합계 | rows |
| price | 가격 카드 | cards=[{name,price,items,hl,stamp,unit}] |
| plan | 과정표 칸 | cols |
| mosaic | 사진 격자 | imgs |
| logos | 로고 보드 | groups |
| closing | 마무리 | title |

공통 값: `box=[(x,y,w,h),...]` 이미지 위 빨간 박스(비율 좌표, 2개 이상이면 번호) · `zoomed=True` 확대 장(proof, 이미지 크기를 계산해 빨간 테두리가 딱 붙음). 보통은 `slides.py` 의 `BOXED(박스, 확대영역, 이름, **원래장)` 헬퍼로 두 장을 한 번에 넣는다.

### 1-A 작은 캡처 → 빨간 박스 + 확대 
- 기준: `?flat=1` 렌더에서 (화면 표시 폭 ÷ 원본 CSS 폭)이 0.7 미만인 캡처. 레티나 2배 캡처는 원본 폭을 2로 나눠 잰다. `deck_lint.py --render` 가 [3-17] WARN 으로 알려 준다.
- 실습 화면(누를 곳을 찾아야 하는 장)부터 나눈다. 결과 미리 보기처럼 위치를 찾을 필요 없는 장은 그대로 둬도 된다.

### screen — 따라하기 화면 꽉 차게 
- 가이드 페이지에 가로 화면 미디어쿼리를 넣는다(폭을 다 쓰고 글자를 창 높이에 맞춰 키움): `@media (min-width:900px) and (orientation:landscape){html{font-size:clamp(18px,3.1vh,30px)} .top-in,.nav-in,.step{max-width:min(1180px,94vw)} footer{display:none}}` .
- 캡처: 브라우저 뷰포트를 960×540, 배율 2로 맞추고 화면마다 `#번호` 로 열고 screenshot → 1920×1080 그대로 `media/follow/fN.png`. 화면이 넘치면(스크롤 생기면) 페이지 쪽을 줄인다.
- 페이지 번호(2/12)가 수강생 화면과 같으니 덱에 따로 번호를 달지 않는다. 짧은 주소는 `hero size="xxl"` 한 장으로 따로 크게.
- 같은 유형 4장 연속은 lint FAIL(2-8). 주소 장과 겹치는 첫 화면은 빼고 3장 이하로 끊는다.

바탕 `bg`: `w` 흰 · `k` 어두운 · `p` 브랜드. 기본값은 cover·countdown=k, chap·closing=p, 나머지 w.
아이콘: compass heart gift hand alert check phone chat box cart star won user users camera book play seat shield clock x arrow spark home calc edit laptop map doc store.

## 연결·검수

- 프롬프터 연결: `deck.js`가 BroadcastChannel `aix-deck`으로 장·단계를 보내고 `aix-goto`를 받는다(v1과 같은 규약). 장마다 `data-n`, 단계 수는 `data-steps`.
- `?flat=1`: 전 장을 세로로 쌓아 한눈에 본다(검사기 `--render`가 쓴다). 화면 캡처는 브라우저 최대 높이(16,384px) 때문에 한 장씩 `go(n)`으로 넘기며 찍는다.
