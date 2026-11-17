# 코드로 영상 만들기: 설치와 실행 (맥·윈도우)

G 경로의 세 가지 엔진을 학생 PC에서 돌리는 절차다. 이 PC(맥, Node 22, ffmpeg 8, Chrome)에서 같은 7초 1080x1920 30fps 글자 모션을 세 엔진으로 렌더해 확인했다(2026-11-18). 윈도우는 직접 돌려 보지 못했다(맨 아래 "윈도우에서 막힐 수 있는 곳").

## 0. 공통 준비

1. 프로그램 확인: `node -v`(22 이상이면 세 엔진 모두 가능), `ffmpeg -version`, 브라우저(Chrome 또는 Edge) 설치 여부. 없는 것은 학생에게 알리고 확인받은 뒤 설치한다(맥 `brew install node ffmpeg`, 윈도우 `winget install OpenJS.NodeJS.LTS`, `winget install Gyan.FFmpeg`).
2. 작업 폴더를 하나 정한다(허브의 현재 작업 폴더 안 `video/<이름>/`). 설치는 전부 이 폴더 안에서만 한다. `npm i -g`, 사용자 설정 폴더(`.claude`·`.codex`·`.agents`) 변경은 하지 않는다.
3. 라이선스를 한 줄로 알린다(`SKILL.md`의 라이선스 절). Remotion은 회사 규모를 먼저 묻는다.
4. 엔진 고르기: 5~15초 모션·쇼츠 그래픽은 code-film, HTML/GSAP·미리보기 편집은 HyperFrames, 긴 영상·데이터·React는 Remotion.

## 1. code-film (기본, 가장 가볍다)

단일 HTML 파일의 `window.draw(frame)`이 프레임을 그리고, `render.mjs`가 브라우저로 한 프레임씩 읽어 ffmpeg로 MP4를 만든다.

```bash
mkdir -p video/test && cd video/test
npm init -y && npm i playwright-core          # 작업 폴더 안에서만
CF=<이 스킬 폴더>/engines/code-film/javascript-animation/scripts
# film.html 작성: window.draw(frame), window.FRAMES, window.FPS (templates/starter.html 또는 아래 최소 계약)
node $CF/asset-audit.mjs film.html            # CLEAN
node $CF/render.mjs film.html --check         # DETERMINISM PASS
node $CF/render.mjs film.html sheet.jpg --sheet 0.5     # 컨택트시트를 직접 본다
node $CF/render.mjs film.html film_raw.mp4
python3 <스킬 폴더>/scripts/edit/master.py film_raw.mp4 film.mp4      # 소리 없으면 색·형식만 변환
bash <스킬 폴더>/scripts/edit/qa_check.sh film.mp4 7 0.15 -14 1080x1920 silent
ffprobe -v error -show_entries stream=width,height,r_frame_rate,nb_frames,duration -of default=nw=1 film.mp4
```

최소 계약(세로 7초 30fps): `<canvas width="1080" height="1920">`, `window.FPS=30; window.FRAMES=210; window.draw=function(frame){ const t=frame/30; ... }`. 시간 t만으로 그린다(`Math.random`·`Date`·CSS 애니메이션 금지). 스프링은 `templates/motion.js`를 페이지에 붙여 쓴다. 가져온 규칙은 `references/codefilm-rules.md`.

실측(이 맥): 렌더 약 3초, `--check` DETERMINISM PASS, `qa_check` FAIL 0(소리 없는 영상은 `silent`), 출력 1080x1920 h264 yuv420p bt709 30fps 210프레임 7.000초.

주의
- 엔진의 `render.mjs`가 `master.py`를 거치기 전에는 `yuvj420p`·색 태그 bt470bg로 나온다. 납품은 반드시 `master.py`를 거친다.
- 큰 글자 여러 줄에 playful 스프링을 쓰면 줄이 겹친다. heavy를 쓴다.
- 브라우저는 시스템 Chrome → Edge → playwright 번들 순서로 찾는다. 셋 다 없으면 `npx playwright install chromium`(작업 폴더 안 캐시).
- 맥에서 브라우저를 띄우는 명령에 별도 실행 규칙이 있으면 그 규칙으로 감싼다.

## 2. HyperFrames

HTML에 `data-start`·`data-duration`을 적고 GSAP 타임라인을 등록하면 렌더러가 프레임 단위로 MP4를 만든다. 자세한 계약과 작업 순서는 스킬 `hyperframes`.

```bash
# 모든 명령 앞에 둔다: 스킬 자동 설치(전역 변경)와 텔레메트리를 끈다
export HYPERFRAMES_SKIP_SKILLS=1 HYPERFRAMES_NO_TELEMETRY=1      # 윈도우 PowerShell: $env:HYPERFRAMES_SKIP_SKILLS=1
mkdir -p video/hf && cd video/hf
npx --yes hyperframes@0.9.61 init my-video --skip-skills --resolution portrait --non-interactive
cd my-video
# index.html을 고쳐 쓴다(루트 data-width=1080 data-height=1920, data-duration=초)
npx --yes hyperframes@0.9.61 check --json      # 오류 0이 될 때까지 고친다
npx --yes hyperframes@0.9.61 render --quality draft --output out.mp4     # 최종은 --quality looks 또는 delivery
```

- **`init`은 `--skip-skills` 없이 돌리면 AI 스킬 6개를 사용자 홈 폴더의 `.agents/skills`, `.claude/skills`에 설치한다.** 이 맥에서 실제로 일어났다. 항상 위처럼 끈다.
- 버전은 실측한 0.9.61로 고정해 적었다. 새 버전을 쓸 때는 `npx hyperframes --version`으로 확인한다.
- 한국어 글꼴: HyperFrames는 번들 글꼴과 `@font-face`로 선언한 글꼴만 쓴다. `font-family: Pretendard`만 쓰면 `font_family_without_font_face` 오류가 난다. OS에 있는 글꼴은 `@font-face { font-family:"KRFont"; font-weight:900; src: local("Pretendard Black"), local("Pretendard"), local("Apple SD Gothic Neo"), local("Malgun Gothic"); }`로 선언한다(경고 `font_face_local_only`는 나오지만 통과). 다른 PC로 프로젝트를 옮길 때는 woff2 파일을 `assets/fonts/`에 두고 `src: url('assets/fonts/x.woff2')`로 바꾼다.
- GSAP는 HTML의 `<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/...">`로 부른다. 인터넷이 있어야 한다.
- 실측(이 맥): `check` 통과(경고 3: 첫 프레임이 빈 배경, 요소 4개가 한 파일, 안전영역), `render --quality draft` 4~22초, 출력 1080x1920 h264 30fps 210프레임 7.000초.
- `check`가 `first_frame_empty`를 경고하면 0초에 제목이 이미 보이게 고친다(썸네일이 된다).

## 3. Remotion

React 컴포넌트가 프레임 번호를 받아 그린다. 회사 규모에 따라 라이선스가 필요하다(`SKILL.md`).

```bash
mkdir -p video/remotion && cd video/remotion
npm init -y && npm i remotion @remotion/cli react react-dom typescript @types/react
# src/index.ts(registerRoot), src/Root.tsx(Composition: id, durationInFrames, fps, width, height), src/Film.tsx(useCurrentFrame + spring)
npx remotion render src/index.ts Film out.mp4
```

- 처음 렌더 때 렌더용 브라우저(Chrome Headless Shell, 약 140MB)를 프로젝트 `node_modules` 안에 내려받는다. 인터넷이 필요하고 시간이 걸린다. 사용자 폴더는 건드리지 않는다.
- 실측(이 맥): 7초 1080x1920 30fps, 210프레임, 렌더 성공(h264, 7.000초).
- `npx remotion render`가 설치를 묻거나 `remotion`·`@remotion/*` 버전이 어긋나면 모두 같은 버전으로 맞춘다.
- Remotion 공식 에이전트 지침(`npx skills add remotion-dev/skills`)은 사용자 폴더에 설치하는 전역 변경이므로 학생 확인 후에만 한다.

## 4. 윈도우에서 막힐 수 있는 곳

- `.sh` 스크립트(`qa_check.sh` 등)는 Git Bash·WSL이 있어야 돈다. 없으면 같은 ffprobe·ffmpeg 명령(`qa-gate.md`)을 직접 실행한다. `master.py`·`render.mjs`는 윈도우에서도 돈다(경로는 `pathToFileURL`로 처리했다).
- `python3` 대신 `python` 또는 `py -3`.
- 경로에 한글·공백이 있으면 따옴표로 감싼다. 작업 폴더는 짧은 영문 경로를 권한다(Remotion·HyperFrames가 긴 경로에서 실패할 수 있다).
- Chrome이 없으면 Edge를 쓴다(code-film). HyperFrames·Remotion은 자체 브라우저를 받는다.
- Pretendard가 없으면 `Malgun Gothic`으로 대신 렌더된다(글자 모양이 다르다). 최종 캡처에서 글꼴을 확인한다.
- 윈도우에서 직접 렌더해 본 기록이 없다. 처음 돌릴 때 위 순서로 한 번 확인하고 결과를 학생에게 알린다.

## 5. 키·계정이 필요한 선택 기능 (빈칸)

- HyperFrames의 음성·배경음·아바타는 HeyGen 로그인이나 로컬 모델이 있을 때만 쓴다. 없으면 무음으로 납품하고 한 줄로 알린다.
- 이미지 생성·위치 찾기(motion-graphics의 `asset-fusion` 등)는 `GEMINI_API_KEY`가 있을 때만 자동으로 돌고, 없으면 격자 루프(수동)로 바꾼다.
- 클라우드 렌더, 유료 영상 생성: `optional-paid-generation.md`.
키는 파일·대화에 적지 않는다. 학생이 맥 키체인·윈도우 자격 증명 관리자에 저장하도록 안내한다.
