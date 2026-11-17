---
name: video-studio
description: 영상 편집·자동편집 지시를 구체화하고 촬영본의 컷·자막·색·사운드·쇼츠를 제작·검수한다. 모션그래픽·런치 영상·설명영상·쇼릴·쇼츠 그래픽처럼 코드로 새로 만드는 영상(code-film·HyperFrames·Remotion)에도 사용한다. "편집해줘", "쇼츠로 잘라", "자막 달아", "영상 만들어", "모션그래픽", "릴스", "유튜브 영상", 영상 파일(.mp4 .mov) 편집 요청에 적용한다.
---

# video-studio

영상 작업의 정본이다. 두 갈래다. 찍은 영상을 다듬는 **E(편집)**와, 코드로 새로 만드는 **G(코드 생성)**. 전사·표·코드로 판단하고, 실행은 스크립트가 하고, QA로 확인한다.
`$SK`는 이 SKILL.md가 있는 폴더다. 모든 참조·스크립트 경로는 이 폴더 기준 상대 경로다.

## 필요한 프로그램 (먼저 확인한다)

| 하려는 일 | 필요한 것 | 확인 |
|---|---|---|
| 모든 영상 | ffmpeg(ffprobe 포함), python 3 | `ffmpeg -version`, `python3 --version`(윈도우는 `python`) |
| E 편집(자막 받아쓰기) | Whisper가 설치된 python. 맥 Apple Silicon은 `scripts/edit/setup_asr.sh`(약 1.3GB), 윈도우는 별도 Whisper 도구 | `references/edit-manual.md` 3장 |
| G: code-film(단일 HTML) | Node 18 이상, Chrome 또는 Edge | `node -v` |
| G: HyperFrames | Node **22 이상**, ffmpeg, Chrome(렌더 때 자동 사용) | `node -v` |
| G: Remotion | Node 18 이상(권장 최신 LTS). 렌더용 브라우저는 처음 한 번 자동 다운로드(약 140MB, 프로젝트 폴더 안) | `node -v` |

- 없는 것이 있으면 **멈추고 무엇이 없는지 한 줄로 알린 뒤**, 학생이 설치해도 된다고 확인하면 AI가 설치한다. 설치는 맥은 Homebrew(`brew install node ffmpeg`), 윈도우는 `winget install OpenJS.NodeJS.LTS`, `winget install Gyan.FFmpeg`가 기본이다. 설치 뒤 새 터미널에서 다시 확인한다.
- npm 패키지(playwright-core, remotion, hyperframes)는 **작업 폴더 안에서만** 설치한다. 전역 설치(`-g`)와 사용자 설정 폴더(`.claude`, `.codex`, `.agents`) 변경은 하지 않는다.
- **주의: `npx hyperframes init`은 기본으로 AI 스킬을 사용자 홈 폴더의 `.agents/skills`, `.claude/skills`에 설치한다.** 항상 `HYPERFRAMES_SKIP_SKILLS=1`을 붙이거나 `--skip-skills`를 준다. 텔레메트리를 끄려면 `HYPERFRAMES_NO_TELEMETRY=1`도 같이 둔다. 자세한 절차는 `references/code-video-setup.md`.
- 한국어 글꼴은 Pretendard를 먼저 쓰고, 없으면 맥 `Apple SD Gothic Neo`, 윈도우 `Malgun Gothic`으로 대신한다. Pretendard가 필요하면(무료, OFL) 설치할지 학생에게 묻는다.
- 이 PC의 `python`은 맥에서는 `python3`로 바꿔 쓴다. `.sh` 스크립트는 맥(또는 윈도우의 Git Bash·WSL)에서 `bash`로 돈다. 윈도우 일반 터미널에서는 같은 ffmpeg 명령을 `references/qa-gate.md`·`edit-manual.md`에서 찾아 직접 실행한다. `mlx-whisper`는 Apple Silicon 맥 전용이다.

## 라이선스 (사용 전에 한 줄로 알린다)

- **Remotion**: 개인, 직원 3명 이하 영리 조직, 비영리, 평가 목적은 무료. 그 밖(직원 4명 이상 회사)은 Company License가 필요하다. 학생의 회사 규모를 확인하고, 해당되면 HyperFrames나 code-film로 바꾼다. https://www.remotion.dev/docs/license
- **HyperFrames**: Apache-2.0(상업 사용 가능). https://github.com/heygen-com/hyperframes/blob/main/LICENSE
- **code-film 엔진**(`engines/code-film`): MIT(iart.ai), `engines/code-film/LICENSE-iart`.
- **GSAP**(HyperFrames가 씀): Webflow 표준 무료 라이선스, 상업 사용 가능. https://gsap.com/standard-license
- 확인일 2026-11-18. 라이선스는 바뀔 수 있으니 회사 명의 납품 전에는 위 주소를 다시 연다.

## 키·계정은 빈칸 (본인 것만)

흐름은 그대로 두고 개인이 넣어야 할 것만 비운다. 유료 영상 생성 도구, 음성 합성, 음악 생성, 클라우드 렌더는 **학생 본인 구독·키가 있을 때만**, 비용과 대상을 알리고 확인받은 뒤에 쓴다(`references/optional-paid-generation.md`). 키가 없으면 그 단계는 건너뛰고(코드로 만들거나 무음으로 납품) 학생이 직접 채우는 방법을 안내한다. 키는 대화·파일에 적지 않고 맥 키체인·윈도우 자격 증명 관리자에 저장하게 한다.

## 0. 먼저 경로를 고른다

| 요청 | 경로 | 읽을 문서 |
|---|---|---|
| 찍은 영상 자르기·다듬기(강의, 토킹헤드, 인터뷰, 쇼츠 추출) | **E. 편집** | `references/edit-manual.md` |
| 영상을 새로 만들기(모션그래픽, 런치, 설명영상, 쇼릴, 캐릭터 단편, 쇼츠 그래픽) | **G. 코드 생성** | `references/generation-playbook.md`, `references/codefilm-rules.md`, `references/motion-references.md` |
| 촬영본 위에 그래픽·B롤·재구성 | E로 컷 → G로 오버레이 | 둘 다 |
| 세로 쇼츠·릴스(토킹헤드 + 그래픽, 자막, 효과음, 전후 비교 영상) | E + G | `references/shorts-rules.md` 먼저 |
| 남의 쇼츠·릴스 스타일로 내 원본 편집·같은 레이아웃 썸네일 | E + G | `references/reference-clone.md`(썸네일은 4장 체크리스트 전부 확인 후 보여준다) |
| 광고·홍보 영상 | G, 기획 먼저 | `references/ad-planning.md` |
| HTML+GSAP로 짜는 영상, 웹페이지·지도·차트·자막 오버레이, 3분 이상 서사·내레이션 영상 | G + HyperFrames | 스킬 `hyperframes`(짧은 모션그래픽은 `motion-graphics`, 긴 영상은 `general-video`, 얼굴 없는 설명 채널은 `faceless-explainer`) |
| 코드로 못 그리는 움직임(연기·빛·물, 실사 B롤) | 선택: 유료 생성 도구 | `references/optional-paid-generation.md`(본인 구독·키가 있을 때만, 비용 고지 후 확인) |

모든 경로의 공통 수치·프리셋: `references/cheatsheet.md`. 완료 조건: `references/qa-gate.md`.

### 0-1. 자연어 요청을 편집 지시로 구체화

- 편집 용어의 뜻·기법 선택·혼동을 확인할 때는 [영상편집 키워드](references/editing-vocabulary.md)의 관련 절만 읽는다. 컷 연결, 구도·움직임, 자막, 소리, 색, 출력 조건으로 나뉘어 있다.
- 자동편집을 지시하거나 브리프가 모호하면 [지시문 템플릿](references/editing-brief-templates.md)의 공통 조건과 해당 용도(강의·설명형 유튜브·쇼츠)만 읽는다. 두 참고자료 전체를 매번 로드하지 않는다.
- 요청을 **대상 구간 → 원하는 변화·기법 → 정도 → 보존할 내용 → 검수 방법**으로 정리한다. "지루해"는 반복 발언·실습 대기·정보량·화면 변화 중 근거가 있는 원인을 찾는다. 근거가 없으면 임의 삭제하지 말고 가정을 적은 시안을 만든다.
- 강의의 설명→클릭→결과 확인, 발화의 부정·조건·숫자·예외·호흡을 보존한다. 무음·확대·컷 간격의 수치는 시안용 선택값으로 구분하며 일괄 삭제 규칙으로 해석하지 않는다.
- 구체화한 결정을 기존 EDL·비트시트·그래픽·믹스 단계로 전달한다. 원본·출력 타임코드를 구분하고, EDL의 프레임 번호·유리수 FPS 원칙을 유지한다.
- J컷·L컷·덕킹·추적 등은 현재 렌더러·스크립트가 지원하는지 확인한다. 미지원 필드를 EDL에 넣거나 적용했다고 보고하지 않는다. 미지원 작업은 대안이나 편집 결정 목록으로 표시한다.
- 명령 예시의 `-14 LUFS`, 컷·무음 임계값, 세로 안전영역 좌표는 **출발 프리셋**이며 플랫폼 공통 의무값이 아니다. 요청·출력 환경에 맞게 고르고 마스터링과 QA에 같은 목표값을 전달한다.
- 모델별 기능·설치 버전·과거 실측은 실행 증거가 아니다. 현재 모델의 영상·음성 입력과 설치된 도구를 확인하고, 읽거나 듣거나 렌더하지 못한 항목을 명시한다. 외부로 나가는 효과(업로드·유료 도구)는 사용자 확인 후에만 한다.

## 1. 절대 규칙

1. 원본은 읽기 전용. 산출물은 새 경로에 버전 번호로 만든다(`_v001`).
2. 전사·무음·콘택트시트·필름스트립·파형 같은 중간 표현으로 판단하고 근거를 기록한다. 직접 보거나 듣지 못했으면 그렇게 밝힌다.
3. 판단은 모델이, 실행은 스크립트가 한다. EDL·비트시트·타이밍 표 같은 데이터로 결정을 남긴다.
4. 길이·수치는 코드로 계산하고 렌더 후 다시 잰다. 모델의 자기 보고를 믿지 않는다(299초라고 했는데 실제 578초였던 사례).
5. 단어 안에서 자르지 않는다. 정밀 전사(`transcribe_words.py`)와 `edl_from_keep.py`를 쓴다.
5-1. **무음 필터만으로 컷을 끝내지 않는다.** 말로 다시 한 곳은 무음 컷으로 절대 안 잘린다. 원본에 `retake_check.py`를 돌려 확정 항목을 keep.json에서 빼고, 완성본에 다시 돌려 확정 0건이어야 한다(강조 반복으로 남기면 `--allow`와 EDL `reason`에 이유). 긴 전사는 Whisper가 반복을 한 단어로 뭉개 전사만 읽어서는 안 보인다.
6. 구조 먼저, 스타일 나중. 러프컷이나 비트시트가 승인되기 전에는 그래픽·색·자막을 입히지 않는다.
6-1. **배경음악은 사용자가 권리를 확인해 받아 둔 파일만 쓴다.** 코드로 합성한 배경음은 쓰지 않고, 효과음만 코드로 만들 수 있다. 맞는 곡이 없으면 만들지 말고 사용자에게 말한다. 음악 생성 같은 유료 도구는 본인 구독·키가 있고 확인받았을 때만 쓴다.
7. 렌더 완료는 완료가 아니다. QA 게이트 FAIL 0과 실제 프레임 캡처가 있어야 완료다. 소리를 못 들었으면 "미청취"와 들어볼 시점 3~5개를 적는다.
8. 외부 효과는 사람 게이트: 유료 도구·API(음성 합성·전사·영상 모델), 업로드·게시(비공개 먼저), 원본 외부 전송.
9. 표기 기본값: 이모지 금지, 회차 표기 금지, 글꼴 Pretendard(없으면 대체 글꼴), 강조색은 사용자가 정한 색(없으면 파랑 계열 하나).

## 2. E. 편집 흐름 (요약)

```bash
# SK = 이 SKILL.md가 있는 폴더, S = $SK/scripts/edit, PY = Whisper가 설치된 python
bash $S/setup_asr.sh                                        # 최초 1회(이미 Whisper python이 있으면 생략)
$PY $S/transcribe_words.py 원본.mp4 work/a                  # 단어 전사 + 무음 + SRT
python $S/pack_transcript.py work/a.words.json > work/a.packed.md   # 에이전트가 읽을 전사
$PY $S/retake_check.py 원본.mp4 --out work/retake_src.json          # 다시 말한 곳: 확정 항목의 앞 테이크를 keep에서 뺀다
# → packed.md를 읽고 살릴 구간을 keep.json으로 작성: [{"words":"w87-w93","reason":"질문형 훅","beat":"HOOK"}, ...]
python $S/edl_from_keep.py 원본.mp4 work/a.words.json work/keep.json work/edl_v001.json
python $S/render_edl.py work/edl_v001.json work/rough_v001.mp4 --draft --cutlist work/cuts.txt
bash $S/cut_strips.sh work/rough_v001.mp4 work/cuts.txt work/qc      # 편집점 필름스트립+파형, 직접 본다
python $S/render_edl.py work/edl_v001.json work/cut_v001.mp4        # 승인 후 최종 품질
python $S/master.py work/cut_v001.mp4 work/final_v001.mp4 --lufs -14
bash $S/qa_check.sh work/final_v001.mp4 <목표초> <허용오차초> -14
$PY $S/roundtrip_check.py work/final_v001.mp4 work/edl_v001.json   # 잘린 단어 자동 검출
$PY $S/retake_check.py work/final_v001.mp4                          # 남은 반복: 확정 0이어야 통과(종료 코드 1 = FAIL)
```

(맥에서는 `python`을 `python3`로 바꾼다.) 영상의 움직임 정도(컷 빈도·정지 구간)는 `bash $S/energy.sh 영상.mp4 [--mode calm]`으로 잰다. 강의·정보형·튜토리얼은 calm이 기본이다.

게이트: EDL 요약(총 길이·뺀 분량·review 목록)을 보여주고 승인 → 러프컷 → 디자인 패스(색→그래픽→자막→믹스) → QA.

세로 9:16 쇼츠·릴스는 `references/shorts-rules.md`를 먼저 읽는다. 세로 영상의 임시 배치 프리셋은 x 90~990, y 220~1500이다. 하단 캡션·버튼과 오른쪽 아이콘의 위치는 플랫폼·기기에 따라 달라지므로 실제 대상 UI에서 확인해 조정하며, 이 좌표만으로 안전영역 검수 통과를 선언하지 않는다. `qa_check.sh`의 5번째 인자 `1080x1920`은 해상도 검사, 6번째 인자 `silent`는 소리 없는 영상(모션그래픽)일 때 쓴다.

## 3. G. 코드 생성 흐름

Opus 5.5급 모델은 영상을 픽셀로 뽑지 않고 **코드로 프레임을 그려 렌더러로 MP4를 만든다.** 이 흐름은 그 사례 조사(`generation-playbook.md`)와 직접 렌더 실측으로 정리했다.

1. **브리프**: 목적·청중·플랫폼·길이·비율·입력 자료·금지. 비면 기본값(30~45초, 16:9 또는 9:16, 30fps)으로 가고 가정을 적는다. 모션그래픽 연습·짧은 쇼츠 그래픽은 5~15초로 시작한다.
2. **자료 조사**: 제품·주제 자료를 읽고, 화면에 나올 사실·수치와 출처를 표로 만든다. 없는 기능·수치·후기는 만들지 않는다. 예시 숫자는 화면에 "예시"로 표기한다.
3. **비트시트 → 승인**: 타임코드, 화면 텍스트(7단어 이하), 비주얼, 모션 기법, 전환, 사운드 큐. 여기서 한 번 멈춘다. 사용자가 "그냥 만들어"라고 명시하면 생략한다.
4. **엔진 선택**
   - 짧은 모션·손그림·인포그래픽·쇼릴·쇼츠 그래픽: `engines/code-film`(단일 HTML, 외부 자산 0, Web Audio 효과음). 먼저 `engines/code-film/javascript-animation/SKILL.md`와 `templates/starter.html`, `templates/motion.js`를 읽는다.
   - HTML+GSAP로 짜고 싶거나(런치·차트·지도·자막 오버레이·기존 영상 위 그래픽), 미리보기 화면에서 고치며 작업: HyperFrames(스킬 `hyperframes`).
   - 브랜드 시스템·데이터 영상·3분 이상, React 코드가 익숙한 경우: Remotion(라이선스 확인 필수).
   - 3D 크롬·클레이: Blender(없으면 쓰지 않고, 설치는 학생 확인 후).
   - 설치·실행 절차와 OS별 주의: `references/code-video-setup.md`.
4-0. **광고·홍보 영상은 기획이 먼저다**: `references/ad-planning.md`의 브리프(행동 하나, 타깃의 순간, 단 하나의 메시지, 믿을 이유, 보는 사람의 자리, 핵심 개념을 아는 사물로, 감정 곡선, 기억 장치, CTA, 금지)를 채우고 사용자에게 보여준 뒤 제작한다. 브랜드가 이미 쓰는 카피·캐릭터·색·그림을 먼저 찾아 쓴다. 실측: 기법만 좋은 영상보다 기획을 세운 영상이 메시지·행동·브랜드가 분명했다.
4-1. **품질 기준을 레퍼런스로 정한다(가장 효과 큼)**: 광고·쇼릴·런치처럼 "눈을 사로잡아야" 하는 영상은 9점급 레퍼런스 1~2개를 분해해 모션 사양서를 만들고 그 문법으로 만든다. 레퍼런스 목록과 문법: `references/motion-references.md`. 분해 절차·재구성 예시 코드: `references/reference-breakdown.md`, `examples/`. 실측: 규칙만 → 7점, 레퍼런스 문법 → 전환 기법 2종에서 8종, 한 흐름의 매치 컷.
5. **어려운 부분 먼저**: 가장 어려운 한 프레임과 비트당 스틸 → 확인 후 전체 렌더.
5-1. **디렉터 채점 루프(템플릿 느낌 탈출)**: 전체 렌더 전에 `references/qa-gate.md` E의 7개 항목을 1~10점으로 매기고, 최악 3개를 고친다. 전 항목 8점 이상이 될 때까지 반복하고(최소 2라운드) `review_log.md`에 남긴다. 확인할 것: 디자인 시스템(격자·HUD·고정 텍스트 위치), 컷을 가로지르는 주인공 오브젝트, 깊이(그림자·레이어·질감 3층), 단순 팝인 대신 형태 변형·카메라 이동, 컷 직후 빈 프레임 0.
6. **렌더와 QA (code-film)** — 작업 폴더에서 한 번 `npm i playwright-core`를 하고, 그 폴더에서 아래를 돌린다. 맥에서 브라우저를 띄우는 명령에 별도 실행 규칙이 있으면 그 규칙을 따른다.
   ```bash
   CF=$SK/engines/code-film/javascript-animation/scripts      # 윈도우는 경로 구분자만 다르다
   node $CF/asset-audit.mjs film.html                         # 외부 로드·임베드 0 확인
   node $CF/render.mjs film.html --check                      # 결정성(같은 프레임이 항상 같은지), 루프 영상만 이음매
   node $CF/render.mjs film.html sheet.jpg --sheet 0.5        # 0.5초 간격 컨택트시트
   node $CF/render.mjs film.html phone --phone 2              # 폭 360px 판독 시트
   node $CF/render.mjs film.html strip --strip 4.2            # 빠른 구간 연속 12프레임
   node $CF/render.mjs film.html film_raw.mp4                 # 전체 렌더(window.SCORE가 있으면 소리 포함)
   python3 $SK/scripts/edit/master.py film_raw.mp4 film.mp4 --lufs -14   # 소리 없는 영상은 색·형식만 맞춘다
   bash $SK/scripts/edit/qa_check.sh film.mp4 <길이초> 0.15 -14 1080x1920 silent   # 소리가 있으면 silent 빼기
   ```
   `layout-check.mjs`는 페이지가 `window.LAYOUT`을 내보낼 때만 의미가 있다(starter의 `claim()`). 안 쓰는 단순 페이지는 컨택트시트·스트립을 직접 본다. 소리가 있는 영상은 `engines/code-film/soundtrack/scripts/sync-check.mjs film.mp4`도 돌린다.
7. **playwright-core**: 엔진 SKILL.md의 "`npm i playwright-core` in your project"는 작업 폴더 안에서 한다. 브라우저는 시스템 Chrome → Edge → playwright 번들 순서로 찾는다(윈도우에서 Chrome이 없어도 Edge로 돈다).
8. **세로 9:16**: 스타터는 1080x1080 정사각이다. `W=1080,H=1920`, `<canvas width="1080" height="1920">`, CSS `canvas{height:100vh;width:auto}`로 바꾼다. 임시 배치 프리셋은 x 90~990, y 220~1500이다(위 2장 주의와 같다).
9. **길이 허용 오차**: AAC 인코더 지연 때문에 소리가 있는 파일은 약 0.1초 길어진다. 코드 영상은 허용 오차 0.15초로 잰다.
10. **한국어 텍스트**: 캔버스 폰트 스택 `700 80px Pretendard, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif`. `@font-face`·data URI로 폰트를 임베드하지 않는다(asset-audit가 FAIL 처리). 렌더 캡처에서 실제 글꼴과 글자 깨짐을 확인한다. HyperFrames는 OS 글꼴을 `local()`로 선언하거나 woff2 파일을 `assets/fonts/`에 둔다(`hyperframes` 스킬).
11. **움직임은 스프링으로**: 이징 곡선 대신 `engines/code-film/javascript-animation/templates/motion.js`를 페이지에 붙인다. 프리셋은 snappy(UI·커서)·base(카드·카메라)·heavy(큰 글자·로고, 오버슈트 0)·playful(마스코트)이다. **큰 글자 여러 줄에 playful을 쓰면 줄끼리 겹친다(실측)**: 큰 글자는 heavy.
12. **캐릭터는 사용자가 준 이미지만**: 캐릭터는 학생이 가진 이미지(배경 뗀 포즈 PNG)를 얹는다. 코드로 새로 그려 만들지 않는다. 포즈 교체 + 코드로 이동·점프·좌우 반전만 준다. 단일 HTML에는 base64로 넣는다.

잘 나온 영상의 공통점(직접 본 14편): 첫 프레임부터 끝까지 유지되는 디자인 시스템(격자·HUD·고정 텍스트 위치·2~3색), 컷을 가로질러 이어지는 주인공 오브젝트, 장르에 맞는 컷 속도(쇼릴 10초당 11~20컷, 설명·서사 0~2컷. 광고·소개·쇼릴의 기본은 다이내믹, 강의·튜토리얼·설명은 차분 — `energy.sh` 기준. 쇼츠·릴스는 `references/shorts-rules.md` 3장), -16~-13 LUFS 마스터링. 상세는 `generation-playbook.md` 6장.

## 4. 프롬프트를 받았을 때

- 사용자가 짧게 요청하면 그대로 따르되, 구조 요소(역할·규격·입력·렌더 방식·금지·스타일·리듬·검수) 중 빠진 것을 기본값으로 채워 브리프에 적는다.
- 검증된 프롬프트 형태는 `references/prompt-originals.md`. 한국어 템플릿은 `generation-playbook.md` 3.3.
- 레퍼런스 사이트의 프롬프트를 쓸 때는 문법(샷 순서·타이밍·전환)만 가져오고 내용·브랜드·캐릭터는 학생 것으로 바꾼다(`motion-references.md`).

## 5. 보고 형식

1. 결론 한 줄(PASS/FAIL 수)과 산출물 절대 경로
2. QA 표 원값, 컨택트시트 경로
3. 요청 → 결과 → 수정 → 수정 결과
4. 못 한 것: 청취, 사실 검증, 플랫폼 앱 미리보기 등

## 6. 환경 참고

| 항목 | 설명 |
|---|---|
| ffmpeg | `zscale`·`libvmaf`·`vidstab`이 없는 빌드가 흔하다. 필요한 필터는 `ffmpeg -filters`로 먼저 확인한다 |
| 정밀 전사 | whisperx + mlx-whisper가 설치된 python(`setup_asr.sh`). 없으면 사용자에게 알린다 |
| code-film 렌더 속도 | 맥 한 대 실측: 7초 1080x1920 30fps 영상이 약 3초, 42초 영상이 26초 |
| 유료 도구 | 유료 API·생성 도구는 쓰지 않는 것이 기본이다. 본인 구독·키가 있고 확인받았을 때만 |
