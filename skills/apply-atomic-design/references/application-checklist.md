# Atomic Design UI/UX 적용 체크리스트

## 목차

1. [작업 크기 라우팅](#작업-크기-라우팅)
2. [시작 전 브리프](#시작-전-브리프)
3. [기존 UI inventory](#기존-ui-inventory)
4. [계층 매핑](#계층-매핑)
5. [컴포넌트 계약](#컴포넌트-계약)
6. [페이지 시나리오와 상태 매트릭스](#페이지-시나리오와-상태-매트릭스)
7. [협업 워크플로](#협업-워크플로)
8. [검증 게이트](#검증-게이트)
9. [Governance](#governance)
10. [AI 구현 규칙](#ai-구현-규칙)
11. [한국어 타이포그래피·줄바꿈](#한국어-타이포그래피줄바꿈)
12. [최종 보고 템플릿](#최종-보고-템플릿)

## 작업 크기 라우팅

| 작업 | 필수 적용 | 생략 가능한 것 |
|---|---|---|
| 단일 스타일·상태 수정 | 기존 pattern/consumer 확인, 가장 가까운 상태·화면 재검증 | 전체 inventory, 정식 governance 문서 |
| 새 컴포넌트 | 책임·재사용 근거, variants/states, content extremes, a11y, responsive, consumers | 조직 전체 workshop |
| 새 화면·기능 | template 구조, 기존 패턴 재사용, 대표 page scenarios, 흐름 검증 | 전사 governance 재설계 |
| 기존 UI 리뷰 | 불일치 inventory, system/page 원인 분리, 영향도와 수정 범위 | 새 구현(요청이 review뿐이면 하지 않음) |
| 리디자인·새 제품 | 핵심 흐름/pattern inventory, taxonomy, 방향 설정, system+page 병행, 운영 계획 | 없음. 단, pilot 범위로 쪼갤 수 있음 |
| 디자인 시스템 구축 | maker/user, source of truth, 문서, lineage, 변경·배포·폐기·지원 | 없음 |

## 시작 전 브리프

다음 질문 중 답이 작업에 필요한 것만 채운다.

```text
사용자와 핵심 과업:
사용자에게 약속할 결과:
사업 목표와 측정값:
대상 플랫폼/화면/입력/네트워크:
핵심 콘텐츠 유형과 데이터 출처:
기존 디자인 시스템·컴포넌트·토큰:
참고할 출처와 참고 목적:
복제하지 않고 변형하거나 배제할 요소:
자료가 없을 때 provisional로 둘 foundations:
반드시 재사용하거나 보존할 패턴:
접근성·성능·법적·브랜드 제약:
이번 변경의 소비 화면과 제외 범위:
완료를 증명할 사용자 시나리오:
```

페이지 수만 받은 경우 다음으로 다시 해석한다.

- 사용자 행동과 흐름 수.
- 고유 template 수.
- 고유 organism/molecule 수.
- 콘텐츠 유형과 데이터 계약 수.
- 외부 서비스·인증·결제 등 통합 수.
- 상태, 권한, 오류, 반응형 변형 수.

## 기존 UI inventory

### 무엇을 모을지

- Foundations: 색, 타입, 간격, 크기, 반경, 그림자, 모션, iconography.
- Global: app shell, header, footer, navigation, search.
- Input: field, textarea, select, checkbox, radio, switch, date, upload.
- Action: primary/secondary/destructive/text/icon buttons와 모든 상태.
- Feedback: validation, alert, toast, loader, progress, empty, error, success.
- Content: heading, body, metadata, avatar, thumbnail, media, card, list, table.
- Interaction: tab, accordion, menu, dialog, tooltip, carousel, drag/drop.
- Edge surfaces: 404, access denied, session expiry, legal, help, third-party embeds.
- Motion: enter/exit, loading, transition, gesture feedback.

### Inventory record

```text
현재 이름:
후보 공통 이름:
스크린샷/경로:
패턴 유형:
구조와 책임:
variants/states:
콘텐츠 제약:
접근성·성능 이슈:
같아 보이지만 다른 패턴:
중복/불일치:
소비 화면:
결정: 유지 / 통합 / 수정 / 폐기 / 추가 조사
```

### Inventory 판단 질문

- 같은 책임인데 모양만 조금 다른가?
- 같은 모양인데 행동·의미가 다른가?
- 차이가 사용자·브랜드·플랫폼 요구에서 비롯됐는가, 우연히 생겼는가?
- 하나로 통합하면 상태 폭발이나 이해 난도가 더 커지는가?
- 변경하면 어떤 화면·흐름·팀이 영향을 받는가?

## 계층 매핑

팀의 기존 이름을 우선한다. 아래는 사고용 기본 mapping이다.

| 계층 | 질문 | 예시 | 검증 초점 |
|---|---|---|---|
| Foundation / properties | 무엇이 일관된 속성을 공급하는가? | color, type, spacing, radius, motion token | 명도, scale, theme, platform mapping |
| Atom | 더 나누면 기능 의미가 사라지는가? | label, input, button, icon, text style | semantics, states, focus, intrinsic size |
| Molecule | 한 가지 작은 책임을 완수하는가? | search field, labeled input, action group | API clarity, validation, composition |
| Organism | 독립적인 화면 구역인가? | header, product grid, checkout summary | hierarchy, internal layout, repeated use |
| Template | 콘텐츠 구조와 배치 규칙이 보이는가? | article, dashboard, checkout shell | slots, priority, optional regions, responsiveness |
| Page / scenario | 실제 사용자·데이터 조건을 나타내는가? | new user, admin, long cart, payment failure | realism, flow, resilience, acceptance |

다음 조건이면 경계를 다시 본다.

- Molecule이 너무 많은 독립 책임과 조건부 영역을 가진다.
- Organism이 한 페이지 이름과 데이터에 지나치게 결합된다.
- Template이 단순 스크린샷이고 slot·content contract가 없다.
- Page가 happy path 한 개뿐이라 패턴의 회복력을 증명하지 못한다.
- Atom 분류를 위해 실제 코드와 협업이 더 어려워진다.

## 컴포넌트 계약

새로 추가하거나 공용 동작이 바뀌는 패턴에 작성한다.

```text
Name:
Purpose / single responsibility:
Anatomy and dependencies:
Inputs / slots / events:
Variants:
Interactive states:
Content rules and extremes:
Responsive/container behavior:
Keyboard and focus behavior:
Screen-reader semantics and announcements:
Motion and reduced-motion behavior:
Performance considerations:
Allowed and disallowed uses:
Representative examples:
Known consumers / lineage:
Owner and change status:
```

### 이름 규칙

- 위치보다 구조·책임: `homepage-promo-card`보다 재사용 가능한 책임을 표현한다.
- 현재 데이터보다 구조: `product-card`가 정말 상품 전용인지, 범용 `card`가 맞는지 검토한다.
- 그러나 `container`, `box`, `thing`처럼 책임이 사라지는 과도한 일반화도 피한다.
- 팀이 이미 사용하는 용어가 합리적이면 Atomic 명칭으로 강제 변경하지 않는다.

## 페이지 시나리오와 상태 매트릭스

### 기본 시나리오 후보

```text
대표 정상 상태
최소 데이터 / 최대 데이터
짧은 텍스트 / 긴 텍스트 / 줄바꿈
이미지 있음 / 없음 / 잘못된 비율 / 로드 실패
첫 사용자 / 재방문자
권한 없음 / 일반 / 관리자
빈 목록 / 한 항목 / 많은 항목 / pagination 또는 virtualization
loading / partial loading / retry
validation error / server error / offline / timeout
success / destructive confirmation / undo
한국어 / 영문·숫자·긴 단어 / 현지화 확장
small container / intermediate width / wide container
keyboard / touch / pointer / screen reader
reduced motion / high contrast / zoom
```

모든 후보를 기계적으로 만들지 않는다. 사용자의 과업과 실제 위험에 해당하는 행을 선택하고, 제외 이유가 중요한 경우 기록한다.

### 상태 매트릭스

| Scenario | Data | Role | Viewport/container | Interaction | Expected outcome | Verified |
|---|---|---|---|---|---|---|
| 대표 정상 | realistic | user | small/medium/large | primary flow | 과업 완료 | |
| 콘텐츠 극단 | long/missing/many | user | narrow | browse/submit | 깨짐 없이 이해·완료 | |
| 실패 | rejected/offline | user | representative | retry/recover | 원인·다음 행동 명확 | |
| 권한 | realistic | admin/non-admin | representative | gated action | 올바른 노출·차단 | |

## 협업 워크플로

### 1. 방향 게이트

- 사용자 과업과 성공 기준이 합의됐다.
- 핵심 콘텐츠와 대략적 순서가 저해상도에서 합의됐다.
- 미적 방향이 특정 완성 화면에 과도하게 고정되지 않았다.
- 기술·접근성·성능 제약이 초기에 드러났다.

### 2. 병렬 탐색

- UX: 정보 위계, content/display patterns, 주요 흐름을 저해상도로 만든다.
- Visual: reference 근거, 스타일 타일, 요소 단위 탐색으로 방향을 좁힌다.
- Frontend: 기존 system 조사, shell/primitive, 동작 proof, 데이터 fixture를 준비한다.
- Content: 실제 필드, 길이, 빈 값, 오류 문구, tone을 제공한다.
- 전원이 정기적으로 같은 prototype과 scenarios를 보고 결정한다.

### 3. 패턴-페이지 왕복

1. 위험도나 재사용성이 높은 패턴 하나를 선택한다.
2. 격리된 anatomy와 states를 만든다.
3. 대표 template/page에 즉시 넣는다.
4. 실제 콘텐츠와 interaction으로 실패를 찾는다.
5. 하위 패턴 또는 template contract를 수정한다.
6. 다른 소비 화면에서 regression을 확인한다.

### 4. 완성도 상승

- broad direction → functional structure → representative scenarios → visual polish 순으로 위험을 줄인다.
- full comp가 필요한 경우 방향 합의와 대화에 쓰고, 이후 동작 판단은 실제 환경에서 한다.
- rolling update로 보여주며 현재 완성도와 아직 미정인 부분을 구분한다.

## 검증 게이트

### Component gate

- [ ] 책임과 이름이 명확하다.
- [ ] 기존 패턴으로 해결할 수 없는 이유가 있다.
- [ ] 상태와 variant가 실제 필요에 맞고 중복되지 않는다.
- [ ] representative/extreme content로 확인했다.
- [ ] keyboard, focus, semantics, announcements를 확인했다.
- [ ] container/viewport 변화에서 확인했다.
- [ ] 성능과 motion 영향을 확인했다.
- [ ] 소비처와 변경 영향이 기록됐다.

### Template/page gate

- [ ] 사용자 과업과 콘텐츠 위계가 분명하다.
- [ ] 동일한 의미와 행동에 동일한 패턴을 사용한다.
- [ ] loading, empty, error, success, role 중 관련 상태가 있다.
- [ ] 실제 데이터 길이와 밀도를 견딘다.
- [ ] small부터 intermediate, wide까지 자연스럽다.
- [ ] keyboard/touch/pointer/assistive technology 중 관련 입력을 확인했다.
- [ ] 성능, 네트워크, third-party 실패가 과업을 막지 않는다.
- [ ] 한 화면의 수정이 시스템에 반영돼야 할지 판단했다.

### Release gate

- [ ] 핵심 사용자 흐름을 실제 실행했다.
- [ ] 변경 컴포넌트의 대표 소비 화면을 재검증했다.
- [ ] 시각 검증과 기능 검증을 모두 수행했다.
- [ ] 구현과 문서/예시가 일치한다.
- [ ] breaking change의 migration 또는 deprecation이 있다.
- [ ] 알려진 한계, owner, 다음 조치가 기록됐다.

## Governance

공용 pattern을 추가·수정·제거할 때 답한다.

```text
문제와 사용자/팀 증거:
기존 패턴으로 해결되지 않는 이유:
제안: 수정 / 추가 / 제거:
재사용 예상 소비처:
접근성·성능·콘텐츠·기술 영향:
승인자와 구현 owner:
문서와 tests:
버전·배포 방식:
영향받는 제품/팀:
변경 공지:
migration/deprecation 계획:
효과를 다시 볼 날짜와 지표:
```

### 새 패턴 승인 휴리스틱

- 사용자 문제 또는 반복되는 제품 요구가 명확한가?
- 다른 팀·화면·콘텐츠에서도 같은 책임이 재사용되는가?
- 기존 패턴의 variant로 넣을 때 복잡도가 더 커지지 않는가?
- 공용 패턴이 되면 quality best practices를 실제로 확산하는가?
- 일회성이라면 local pattern으로 두고 두 번째 유사 사용을 기다리는 편이 나은가?

## AI 구현 규칙

- 파일을 만들기 전에 기존 components, tokens, stories, tests, docs를 검색한다.
- 브랜드·기존 시스템·reference 근거가 없으면 시각 토큰을 임의의 최종값으로 확정하지 않는다. 동작 검증용 중립 임시값은 `provisional`로 표시하고 교체 지점을 한곳에 모은다.
- 스크린샷을 좌표와 픽셀 값으로만 복제하지 말고 의미 있는 구조와 재사용 가능한 책임으로 구현한다.
- 디자인 reference에서 시각 언어와 interaction rationale를 추출하되 제품 맥락에 맞게 변환한다.
- reference를 사용했다면 출처·확인 시점, 가져온 원리, 프로젝트에 맞게 변형하거나 배제한 부분을 최종 보고에 남긴다.
- 한 화면을 빠르게 통과하려고 공용 component에 page-specific 조건을 계속 추가하지 않는다.
- 반대로 실제 한 번만 쓰이는 구조를 억지로 범용화해 API를 복잡하게 만들지 않는다.
- generated UI에도 focus, label, error association, contrast, motion preference, responsive overflow를 확인한다.
- representative fixtures와 failure states를 함께 만든다.
- 구현 뒤 isolated component와 end-to-end user flow를 모두 실행·렌더 검증한다.
- 변경된 공용 pattern, 영향 consumer, 미검증 항목을 최종 보고에 남긴다.

## 방향 3안 게이트

고객 대면 신규 디자인(랜딩·시안·제품 데모)은 완성본 직행 금지 — 무드·레이아웃이 실제로 차별화된 방향 3안을 먼저 제시하고, 사용자가 선택한 뒤 완성한다. 스타일 참조가 주어져도 그 안에서 3가지 해석을 제시한다(참조는 해석 공간을 좁힐 뿐 선택권을 없애지 않는다). 기존 디자인의 수정·개선 패스는 제외.

## 한국어 타이포그래피·줄바꿈

한국어 텍스트가 있는 모든 화면·산출물(랜딩·미리보기 HTML·위임 산출물 포함)에 적용한다.

- 본문 기본값: `word-break: keep-all`. 긴 URL·영문 토큰이 실제로 넘치는 요소에만 `overflow-wrap: anywhere`를 개별 적용한다.
- 제목(h1·h2): `text-wrap: balance` 적용 후 의미 구 단위로 검수한다. 수식어-핵심 명사, 조건-결론을 줄바꿈으로 가르지 않는다. 의미가 고정된 히어로 문구만 `<br>`로 구 단위 개행한다.
- 행 끝이나 다음 행 첫 글자에 조사만 남는 고아 줄바꿈 금지.
- 행간: 제목 1.2~1.4, 본문 1.55~1.7. CJK 본문 줄 길이는 40자 안팎을 상한으로 잡는다.
- 줄 길이 상한은 **산문에만** 건다. 카드·표·목록처럼 훑어보는 탐색 UI까지 산문 폭에 가두지 않는다. 산문 블록에 `max-width`를 걸고 컨테이너는 넓게 둔다(데스크톱 1100~1200px 선에서 상한). 페이지 전체를 한 폭으로 묶으면 본문은 오히려 길어지고 목록은 좁아진다.
- 검증 뷰포트: 320·375·768px·데스크톱에서 제목·히어로 줄바꿈을 확인한다. 이때 한 줄 글자 수를 실제로 측정한다 — 눈대중으로 넘기지 않는다.
- 위임 스펙 필수 포함: 이 섹션의 규칙과 검증 뷰포트를 위임 스펙에 명시한다 — 위임 산출물의 줄바꿈 미검증 재발 방지.

## 최종 보고 템플릿

작은 작업은 필요한 줄만 쓴다.

```text
결과: 사용자가 무엇을 할 수 있게 되었는가
재사용: 유지한 기존 patterns
시스템 변경: 추가·수정·폐기한 patterns와 이유
시나리오: 확인한 대표/극단/실패/권한 states
품질: responsive, accessibility, performance, visual checks
참고 근거: 출처 / 가져온 원리 / 변형·배제한 부분
영향 범위: 재검증한 consumers와 남은 위험
운영: 문서, owner, migration, 다음 측정
```
