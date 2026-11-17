# 덱 스타일 v1 템플릿

검증된 강의 덱을 바탕으로 한 스타일 v1 틀이다.

- 새 강의 폴더에 이 폴더를 `deck-v1/`로 복사해서 쓴다.
- `slides.py` 의 `D` 가 장표 원고다(여기 들어 있는 것은 예시). 구조 설계서의 장 번호와 1:1로 맞춘다.
- `build.py` 에는 예시 전용 값이 있다: 공유판 경로, `../assets` 미디어 경로. 새 강의에 맞게 고친다. 장 수는 고정하지 않는다.
- 강조: 제목에 `<em>` 이 없어도 위쪽 라벨(1부·2부)을 강조색으로 올리지 않는다. 빌드가 '강조 없는 장'을 알려주면 제목 핵심어를 `<em>` 으로 감싼다. 제목 굵기 800.
- 프롬프터 연결: `deck.js` 에 BroadcastChannel 'aix-deck' 양방향 연결이 기본으로 들어 있다. 프롬프터 쪽도 같은 채널을 쓴다(10/12 설명회 덱 `build_prompter10.py` 참고). 로컬 서버로 열어야 연결된다.
- 팔레트: 아이보리 #F7F4EC · 글자 #131313 · 기본 강조색(파랑, df.css 의 --accent) (`data-pal="paper"`). 주황 금지.
- 레이아웃: cover · statement · quote · split · flow · cycle · stat(카운트업) · shot(캡처 풀화면) · video · grid · chapter · closing. 스텝은 누를 때 진행.
- 추가 장(스타일 v2와 같은 규칙):
  - `shot` 에 `box=[(x,y,w,h),...]`(이미지 대비 비율) → 빨간 박스. 2개 이상이면 번호. 바로 다음에 `k="zoom"` 확대 장(앞 장 박스 부분을 잘라 크게, 테두리가 이미지에 딱 붙음). `slides.py` 의 `*BOXED(박스, 확대영역, 이름, **원래shot장)` 으로 두 장을 한 번에 넣는다. 기준: 화면에서 원본 글씨가 70% 미만(레티나 2배는 CSS 크기로 환산), lint [3-17] WARN.
  - `screen`: 따라하기 페이지 화면을 덱 전체에 꽉 차게(`img`, `box`). 가이드 페이지에 가로 화면 미디어쿼리를 넣고 960×540·2배로 캡처 → 1920×1080. 브랜드·쪽번호 숨김. 짧은 주소는 `statement big=True` 한 장으로 따로. 방법은 `../style-v2/README.md` screen 절.
  - `market`: 시중 서비스 한 장 — 공개 페이지 실제 캡처 + `tag`(공식 페이지 확인 가격만, 없으면 생략) + `side=[(이런 걸 돈 주고 써요, 설명), (우리는, 설명)]`, `src` 출처 한 줄.
  - `cal`: 한 달 달력 — `year`, `month`, `marks={일:("today"|"class"|"span", 글)}`, `legend=[(종류, 이름)]`.
  - 투표(poll) 유형은 v1에 없다(v2 전용).
- 미디어: `media/` 에 캡처 PNG. 자료가 없으면 pending 자리표시가 나오고 같은 파일명으로 넣고 재빌드하면 바뀐다. 조판·캡처 스크립트는 `media-src/` (헤드리스 브라우저가 필요하다).
- 점검: `python qa.py`(이 덱 전용: 장 번호 대조·강조색 장당 1곳·pending·원고 대조) + `python ../../scripts/deck_lint.py deck.html [프롬프터.html]`(모든 덱 공통, `references/deck-checklist.md` 의 [자동] 항목). 빌드: `python build.py`, 공유용 한 파일: `python build.py --share`.
- 프롬프터: 파트별 [말]+[대기]+[복귀] 글자 수가 배정 시간×320자의 65~85%여야 완료.
