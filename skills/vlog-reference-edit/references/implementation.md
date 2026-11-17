# 실행 계약

## 입력과 의존성

Python 3, ffprobe/ffmpeg, HyperFrames CLI가 필요하다. 구절 전사와 꼬리물기 음성 마스터를 먼저 준비한다. 파일 경로는 plan 기준 상대 경로 또는 절대 경로다. 영상은 로컬 링크로 연결되므로 다른 컴퓨터에서는 재료 경로를 다시 연결해야 한다.

`edit-plan.json` 필수 입력:

- `duration`: 정리된 음성의 실제 길이(초). `width:1080`, `height:1920`, `fps:30`은 디자인 기준이다.
- `audio_path`, `captions_path`, `font_path`, `gsap_path`: 실제 로컬 파일. 폰트·GSAP은 원 프로젝트의 합법적인 설치본을 재사용한다.
- `shots`: `id`, `source`, `source_start`, `output_start`, `duration`, `focal_x`, `focal_y`. 화면 타임라인을 연속으로 덮고 소스의 유효 구간을 넘지 않는다.
- 자막 파일은 `{"captions":[{"start":0.04,"end":1.06,"text":"실제 발화"}]}` 구조다. 시간은 음성 마스터 기준이다.
- `caption_style`: 생략하면 production-profile 기본값. 필요한 경우 `center_y`, `font_size`, `text_shadow`를 재정의한다.
- `headline`: 생략하면 제목을 추가하지 않는다. 있으면 `lines`와 `font_path`를 제공한다. `design:"impact"`, `duration`, `font_size`, `last_line_font_size`는 프로필 기본값을 따른다. 두 줄 크기는 사용자가 달리 요청하지 않으면 동일하다.

4K 출력은 plan을 두 배 크기로 고쳐 자막만 작아지는 방식으로 만들지 않는다. 디자인 기준 1080×1920과 `--resolution portrait-4k`를 함께 사용한다.

## 작업 폴더 구성 예

- `edit-plan.json`: 위 필수 입력을 담은 정본. 수정은 이 파일과 생성기에서 하고, 렌더된 MP4나 HTML을 직접 고치지 않는다.
- `audio-prep/captions.json`, `audio-prep/provenance.json`: 실제 발화 자막과 음성 마스터의 출처 기록.
- `source-inventory.json`: 촬영 파일 목록과 해시(촬영 원본 파일은 공유하지 않는다).
- `verification/`: 렌더 후 검사 기록(해상도, fps, 길이, 대표 프레임).
- 글꼴(Pretendard, 무료 OFL)과 GSAP 파일은 `reel-reference-edit/assets/fonts/`와 그 폴더의 `scripts/resolve_dependencies.py`가 확인하는 고정 버전을 쓴다. 그 스킬이 없으면 학생 허락을 받고 공식 배포처에서 받은 뒤 해시를 기록한다.
