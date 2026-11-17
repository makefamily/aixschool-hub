---
name: hyperframes
description: HTML을 영상(MP4)으로 렌더하는 HyperFrames로 영상을 만들거나 고친다. 런치 영상, 설명영상, 뮤직비디오, 차트·지도, 세로 클립, 타이틀 카드, 자막·오버레이. HTML+GSAP로 모션그래픽을 짜서 mp4로 뽑아야 할 때 먼저 읽는다. 짧은 모션그래픽은 motion-graphics, 긴 서사·내레이션은 general-video, 얼굴 없는 설명 영상은 faceless-explainer로 이어진다.
---

# HyperFrames

HyperFrames는 HTML을 일시정지한 타임라인으로 프레임마다 이동시키며 영상으로 렌더한다. 같은 HTML은 항상 같은 영상이 된다. 출처: HeyGen의 오픈소스 HyperFrames 공식 스킬(Apache-2.0, https://github.com/heygen-com/hyperframes)을 허브용으로 줄이고 고쳤다. 라이선스 전문은 `NOTICE.md`.

## 허브에서 쓰는 방법 (먼저 읽는다)

필요한 것: Node **22 이상**, ffmpeg, Chrome. 확인과 설치 순서, 맥·윈도우 차이, 라이선스는 `../video-studio/SKILL.md`와 `../video-studio/references/code-video-setup.md`를 따른다. 이 스킬은 그 문서 위에서 돈다.

1. **스킬 자동 설치를 끈다.** `npx hyperframes init`은 그냥 돌리면 AI 스킬을 사용자 홈 폴더(`.agents/skills`, `.claude/skills`)에 설치한다. 모든 명령 앞에 `HYPERFRAMES_SKIP_SKILLS=1`, `HYPERFRAMES_NO_TELEMETRY=1`을 두고, init에는 `--skip-skills --non-interactive`를 준다(윈도우 PowerShell은 `$env:이름=1`).
2. **작업 폴더 안에서만** 만든다(`npx --yes hyperframes@0.9.61 init <이름> --skip-skills --resolution portrait`). 버전은 실측한 0.9.61 기준이다.
3. 아래 문서에 `/hyperframes-core`, `/hyperframes-cli`, `/hyperframes-registry`, `/media-use`, `/slideshow`처럼 슬래시로 적힌 스킬 이름이 나온다. 이 허브에서는 이렇게 읽는다.

   | 문서의 이름 | 허브에서 |
   |---|---|
   | `/hyperframes-core` | `references/core/`(`_core-skill.md`가 입구) |
   | `/hyperframes-cli` | `references/cli/`(`_cli-skill.md`가 입구) |
   | `/hyperframes-audio`, 소리 | `references/sound.md`, `references/sound-skill.md` |
   | `/media-use`, `/hyperframes-registry`, `/slideshow`, `/figma`, `/hyperframes-animation`, `/hyperframes-creative` | 허브에 없다. 필요하면 학생에게 말하고 확인받은 뒤 공식 스킬을 프로젝트에 설치한다(`npx skills add heygen-com/hyperframes`는 사용자 폴더에 설치되는 전역 변경이므로 확인 필수). 없으면 직접 짠다 |

4. HeyGen 로그인(음성·배경음·아바타)과 `GEMINI_API_KEY`(이미지 생성·위치 찾기)는 **학생 본인 계정·키가 있을 때만** 쓴다. 없으면 그 단계는 건너뛰고(무음 납품, 격자 수동 루프) 한 줄로 알린다. 키는 대화·파일에 적지 않는다. `npx hyperframes usage`, `auth`, `cloud`, `lambda`, `cloudrun`, `publish`는 계정·과금이 걸린 명령이니 학생이 시켰을 때만 쓴다.
5. 한국어 글꼴: HyperFrames는 번들 글꼴과 `@font-face`로 선언한 글꼴만 쓴다. OS에 설치된 Pretendard·맑은 고딕·Apple SD Gothic Neo는 `@font-face { font-family:"KRFont"; src: local("Pretendard"), local("Apple SD Gothic Neo"), local("Malgun Gothic"); }`로 선언하고 `font-family:"KRFont"`를 쓴다(린트 경고 `font_face_local_only`는 허용). 다른 PC로 옮길 프로젝트는 woff2를 `assets/fonts/`에 둔다.
6. `init`이 프로젝트에 `AGENTS.md`·`CLAUDE.md`를 만든다. 허브 규칙과 겹치면 허브 규칙이 우선한다.
7. GSAP는 HTML이 CDN에서 불러온다(인터넷 필요). 렌더 전에 `check`를 돌리고, 렌더 후 `ffprobe`로 길이·해상도를 잰다.
8. 이 맥에서 7초 1080x1920 30fps 글자 모션을 `check` → `render --quality draft`로 만들어 mp4가 나왔다(약 4~22초). 윈도우는 직접 돌려 보지 못했다.

## 이어지는 스킬

| 만들 영상 | 스킬 |
|---|---|
| 10초 안팎 글자 모션·숫자·차트·로고·지도·트윗·웹페이지 모션, 무음 | `motion-graphics` |
| 길고 내레이션이 있거나 여러 장면인 영상 | `general-video` |
| 얼굴 없는 채널식 설명 영상(음성·자막·장면 전환) | `faceless-explainer` |
| 웹 애니메이션 기법(GSAP·텍스트 효과·스크롤) | `awwwards-animations`(참고용) |
| 코드로 직접 그리는 캔버스 영상(HyperFrames가 과할 때) | `video-studio`의 code-film |

레퍼런스 사이트와 문법은 `../video-studio/references/motion-references.md`.

---

HyperFrames renders HTML to video by seeking a paused timeline frame by frame, so every render is identical. Use it unless another framework or a plain browser recording is asked for. Run the CLI as `npx hyperframes <command>` (see `references/cli/_cli-skill.md`).

`index.html` is the root composition: it declares the video's variables and mounts one scene per sub-composition from `compositions/`. Media and fonts live in `assets/`. A new project: `npx hyperframes init <dir> --skip-skills` (see above).

Build what was asked: no voiceover or captions and no new aspect ratio unless the request or the source calls for them; a film over ~15 s that tells something gets music and sound on its visible actions unless the person asked for silence (`references/sound.md`; in the hub, background music is only a file the student already has, see `../video-studio/SKILL.md` rule 6-1). A new video is 1920×1080 at 30 fps (1080×1920 for vertical). A question, a hold or a loose idea gets an answer or a proposal, not an edit. Show real things from their source (the product's screens, the brand's logo, a real place's imagery); draw only what has none.

## Contract

`npx hyperframes check --json` reports most violations with a `Fix:` line.

1. Every timed element has `class="clip"`, `data-start` and `data-duration` in seconds, and shows over `[start, start + duration)`: land an end state just before its end. `data-track-index` is only a Studio lane; paint order is `z-index`.
2. The video's length is the root's `data-duration`: overrun is cut, an early end holds the last frame.
3. Each composition builds one paused timeline and registers it after its tweens: `window.__timelines["<data-composition-id>"] = tl`.
4. No `Date.now()`, unseeded `Math.random()`, network fetches, timers or `repeat: -1`. Everything visible is a function of timeline time.
5. Never tween `display`, `visibility` or `autoAlpha` on a `.clip`; animate a child.
6. No CSS `transform` on an element GSAP transforms; animate transforms, not `left`/`top`/`width`/`height`.
7. Never `play()`, `pause()` or seek media. A `<video>` keeps its sound with `data-has-audio="true"`, else it is `muted`; music, voice, replacement sound and J/L cuts are a separate `<audio>`.
8. Every `<audio>` has an `id` or it is left out of the mix. No `crossorigin` on media. Time a `<video>` or its wrapper, never both.
9. Only the bundled fonts (`references/format.md`) resolve by name; any other family needs `@font-face` to a file in `assets/fonts/` (or `local()` for an installed font, see the hub note above).
10. Asset paths are root-relative (`assets/...`), in sub-compositions too.
11. Grades, grain, blur and vignettes on footage go through `npx hyperframes media-treatment`, never CSS filters.
12. A scene file puts its styles, markup and scripts inside `<template>` and styles its root as `#root`. Intended overflow or overlap: `data-layout-allow-overflow`, `data-layout-allow-overlap`.

Measured in this hub's test: a single-file composition with 4 timed elements passes `check` with warnings (`timeline_track_too_dense`, `nested_structure_needs_subcomposition`, `first_frame_empty`); errors must be 0. Put the title on screen at 0 s so the first frame is not just the background.

## Keep it editable

- One scene per sub-composition, short readable ids; the root holds only scene hosts, media and audio.
- Timed elements are written in the HTML, not made by script, each with a stable `id`.
- Copy, brand colours and swappable media are variables (`data-var-text`, `data-var-src`, `var(--id)`).
- One kind per track: `data-track-kind="graphics"` on scene and overlay hosts, `captions` on the one host that holds every caption group.
- Content stays inside the 90% action-safe box, captions and key text inside 80% title-safe.

## Work loop

- A new film over ~15 s that tells something: its type's file (below), then `references/story.md`: three storylines that are three different films, in words only; the person picks unless they asked for the file or no stops. Then `SPEC.md` (`references/spec.md`): every adjective as a number, the defaults banned by name, the shots by frame.
- After your last edit: `npx hyperframes check --json`; fix every error, weigh every warning. A film: `npx hyperframes snapshot --review` and `references/review.md`. A small edit: snapshot what you changed (`--at`, `--range`, `--composition`) and look at the PNGs before you reply.
- Render when the person approves the preview, asks for the file or asks for no stops, after your check and review pass: `npx hyperframes render --quality draft` while iterating, `looks` or `delivery` for the final. Then `ffprobe` the file and run the hub QA (`../video-studio/references/qa-gate.md`, `qa_check.sh ... silent` for silent films).
- Preview: `npx hyperframes preview --background`, give the person the local URL.

## What to read

| The request | Read |
| --- | --- |
| Launch, promo, feature | `references/types/launch.md` |
| Explainer, tutorial | `references/types/explainer.md` |
| Music video | `references/types/music.md` |
| Chart, numbers | `references/types/data.md` |
| Vertical or social clip | `references/types/vertical.md` |
| 3D, simulation, generative | `references/types/3d.md` |
| Character, mascot, story short | `references/types/character.md` |
| A real place or map; a website, PR or script; kinetic type | `references/film.md` |
| Captions; cards over a talking head | `references/captions.md`; `references/overlays.md` |
| Motion: eases, titles, cuts, punch-ins, speed, holds | `references/motion.md` |
| Scenes, attributes, media, lint; GSAP, Lottie, 3D, canvas | `references/format.md`; `references/runtimes.md`; `references/core/` |
| CLI commands, lint, preview, render, browser problems | `references/cli/` |
