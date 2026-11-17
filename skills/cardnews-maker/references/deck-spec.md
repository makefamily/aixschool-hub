# deck.json 쓰는 법 (템플릿 3종용)

기본 틀(cards.json)과 달리 템플릿 3종은 deck.json 하나에 글과 그림 계획을 같이 쓴다. 예시: `templates/deck.example.json`.

## 장 구성
- 5장: 표지 1 + 본문 3 + 마감 1 / 10장: 표지 1 + 본문 8 + 마감 1. 그 밖의 장 수는 만들지 않는다.
- 학생이 장 수를 말하지 않으면 10장을 기본으로 제안하고, 짧게 가고 싶다고 하면 5장.

## 글 칸과 길이 (넘기면 스크립트가 원고 형식 오류로 돌려보낸다)
- 표지 cover.f: title(두 줄, 한 줄 8자 이내), sub(두 줄까지, 한 줄 14자 이내), rows(본문 흐름 대표 단어 3~4개, 그런지 템플릿에서 씀)
- 본문 body.f: head(두 줄까지, 한 줄 9자 이내), desc(한 문장 42자 이내), word(핵심 2~7자)
- 마감 closing.f: title(두 줄), desc(한 줄), cta1(큰 버튼 글, 짧게), cta2(작은 안내 글)
- 바깥: topic, audience, handle(SNS 이름), brand_name(없으면 handle), caption(인스타 올릴 글, 선택)
- 줄바꿈은 `\n`. 글자 수는 공백을 뺀 수.

## 그림 계획 visuals
- cover_scene: 표지 이미지 장면(영어 1~2문장). 사물·풍경만. 글자·로고·사람·얼굴·손 금지.
- bg_scenes: 포스터 템플릿 본문 배경 사진 장면 3개(영어, 각 1문장, 사람 없음).
- slides.N.kind: 본문 장마다 하나. 같은 종류가 3번 넘거나 연속되면 안 된다.
  - chat: messages [{who: me|ai, text}] 2~4개
  - compare: left, right {label, lines[1~3]}
  - code: title(파일 이름), lines[4~8]
  - flow: nodes [{label, icon}] 3~5개 (icon은 숫자나 짧은 글자 한 칸)
  - checklist: items 3~5개, done(체크된 개수)
  - settings: title, rows [{label, value}] (value는 실제 값 또는 on/off, 이름 되풀이 금지)
  - gauge: value, max, label, bands [{label, upto}]
  - terminal: lines ($ 로 시작하는 줄은 원고에 나온 실제 영문 명령만)
- 그림 속 내용도 원고·학생 자료에 있는 사실만. 새 숫자·도구·효과를 지어내지 않는다.

## 템플릿
- 08-poster: 강한 색 바탕 + 초대형 노랑 제목. 이미지 4개(표지 1 + 배경 3) 있으면 가장 좋다. 없으면 이미지 없는 색 배경.
- 09-editorial: 밝은 바탕 + 예시 카드. 표지 이미지 1개 있으면 좋다. 없으면 어두운 배경.
- 10-grunge: 위쪽 화면 + 아래 검정 장체 글씨. 이미지 필요 없음.
- 내 브랜드 색을 템플릿 대표색 자리에 넣으려면 `brand.json`의 accent를 정하고 만들 때 브랜드 색 옵션을 켠다. 진한 색일수록 잘 맞는다.
