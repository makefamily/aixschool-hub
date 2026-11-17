# Claude로 영상 편집한 사례와 교훈

기준일 2026-09-27. 공개 사례를 조사한 요약이다.

## 결론 먼저

- **(2026-09-27 정정)** 처음 조사는 "편집"으로 범위를 좁혀 Opus 5.5 사례가 없다고 잘못 결론 냈다. 다시 조사해 보니 출시 5일 만에 X에만 영상 첨부 후보 1,511건이 있었고, 출처가 확인된 사례만 168건이었다. 영상 편집 사례도 유튜브 튜토리얼 여러 편(Mitchell Moses, Matt Penny, Nate Herk, Josh Simmons)과 X 사례(gregpr07 13테이크 편집, AxtonLiu 토킹헤드 재구성)가 있다. 생성 사례는 `generation-playbook.md`에 정리했다.
- 가장 잘 문서화된 사례는 **Fable 5 출시 영상**(Anthropic Thariq Shihipar, 2026-06)과 오픈소스 **browser-use/video-use**다. 둘 다 같은 구조를 쓴다: 전사 → 이유를 적은 EDL → FFmpeg/Remotion 결정론 실행 → 경계 검수 → 사람 선택.
- Opus 5.5 공식 발표에는 영상 입력·편집 전용 능력이 없다. 가격 입력 $4 / 출력 $20 (백만 토큰당), Opus 5 대비 비용 40% 절감·출력 30% 빠름. 쓸모는 긴 에이전트 세션과 도구 오케스트레이션이다.

## 사례 요약

| 사례 | 날짜 | 영상 | 스택 | 핵심 교훈 |
|---|---|---|---|---|
| Fable 5 출시 영상 (Thariq, 덱 공개) | 2026-06 | 4K 24fps 3분, S-Log3 17테이크 25GB → 4,334프레임 653MB, 재렌더 10회, 4일 | Claude Code, Whisper(로컬), JSON EDL, FFmpeg, 손으로 쓴 `.cube` LUT 7개, Remotion 그래픽 11개, Figma MCP 왕복 2회 | 후보 테이크·선택 이유를 EDL에 저장, 구조→LUT→그래픽 순서, 전역 타이밍 상수 파일, 전사 오인식("Thariq→Sark")이어도 타임코드는 쓸 만함 |
| browser-use/video-use | 2026-04~ | 토킹헤드·몽타주·튜토리얼 | 셸 에이전트, FFmpeg, 유료 전사 서비스, HyperFrames/Remotion/Manim 오버레이 | 하드 규칙 12개(단어 안 컷 금지, 30~200ms 패딩, 30ms 페이드, 자막 마지막, 실행 전 전략 확인, 자가 검수 최대 3회) |
| Jason Cooperson 자동 편집 | 2026-06-29 | 토킹헤드 4분10초 → 47초 | WhisperX, FFmpeg, HyperFrames, 브랜드 프리셋, (선택) Premiere MCP | Rough Cut → Graphics → **Second Pass** → Captions+Music → Export. 그래픽 초안 22분 + 다듬기 2시간. 러프컷과 그래픽을 별도 대화로 |
| Premiere MCP 무음 컷 (Aidan Stanik) | 2026-05-21 | 17분 영상 | Claude Code + Premiere MCP(도구 269개) | CEP 호환 문제로 일부 실패 댓글. 도구를 많이 준다고 올바르게 쓰는 게 아님, 복제 시퀀스에서만 |
| Cutback 비교 실험 (업체 자체) | 2026-09-22 | 30분 인터뷰 → 5분 하이라이트 | Opus via Claude Code, Scribe v2 | 모델 보고 299.32초 vs 실제 578.24초, 11컷 전부 문장 중간 절단. 서브에이전트 병렬은 더 느림(19.4초 vs 28.6초). **수치는 코드로 계산** |
| AI싱크클럽 (한국어) | 2026-01-22 | Remotion 텍스트 애니·아웃트로·주식 리포트 | Claude Code, Remotion, TTS | 데이터 영상은 원자료만 쓰고 렌더 후 숫자 대조 |
| 빌더 조쉬 (한국어) | 2026-01-13 | 명언 오디오북 롱폼 | 멀티에이전트, Gemini, Whisper, FFmpeg, TTS, 생성형 영상 도구 | 1~3차 테스트로 비율·자막 싱크 튜닝. 생성형 영상은 사실 증명이 아님 |
| Reddit 일일 쇼츠 파이프라인 | 2026 | 쇼츠 | faster-whisper, FFmpeg, Claude API | 첫 6초 훅, 2단어 자막, 셸 아포스트로피 오류 |

## Fable 사례 원문 프롬프트 (재사용 템플릿)

```text
I'm processing the recording of a bunch of videos in @Fable-Full-Recording/ the script for them is in
@Fable-Full-Recording/fable5script.md. I want you to run the eleven labs transcription service on them.
Then stitch together the best shots, into one final clip. A few notes: there are multiple take per scene,
the best takes are usually the ones at the end with the fewest ums, but that can change. I also re-shot
the first scene at the end. They should all be organized by timeline. For a few of them I start the video
saying "Hey [name]" as a way of starting the sentence warm, we should cut that out. Create a JSON file for
the video that shows per scene, each clip we're using and the time ranges from them. Then, create a final
scene using ffmpeg. Orchestrate this all using workflows. /goal dont stop until you have a final video
```

좋은 프롬프트의 구성 요소: 소스 위치 + 대본 위치 + 테이크 선택 휴리스틱(예외 허용) + 재촬영 정보 + 잘라낼 패턴 + 결정 기록 형식(JSON) + 실행 도구 + 완료 조건.

한국어 템플릿:

```text
<폴더>의 원본을 편집해줘. 대본은 <파일>. 목표: <플랫폼> <길이>±<오차>, 톤 <레퍼런스>.
장면마다 테이크가 여러 개 있고 보통 뒤 테이크가 낫지만 예외 가능. <재촬영 정보>.
잘라낼 것: <인사말/필러/특정 패턴>. 남길 것: <강조 전 멈춤/리액션>.
먼저 EDL(JSON: 장면별 후보, 선택 이유, 구간)만 만들고 멈춰. 내가 승인하면 러프컷을 렌더해.
총 길이는 스크립트로 계산하고, 모든 편집점은 필름스트립+파형으로 자가 검수해서 보고해.
```

## video-use 하드 규칙 (원문 인용)

- "Subtitles are applied LAST in the filter chain, after every overlay."
- "30ms audio fades at every segment boundary"
- "Never cut inside a word. Snap every cut edge to a word boundary from the Scribe transcript."
- "Pad every cut edge. Working window: 30–200ms."
- "Word-level verbatim ASR only. Never SRT/phrase mode"
- "Strategy confirmation before execution."
- "Audio is primary, visuals follow."
- 파이프라인: Transcribe → Pack(0.5초 침묵·화자 변경으로 문구 묶기) → LLM Reasons → EDL → Render → Self-Eval(이슈 시 수정·재렌더, 최대 3회)
- 산출물은 원본 옆 `edit/` 폴더: `project.md`(전략·결정·미완료 누적), `takes_packed.md`, `edl.json`, `transcripts/`, `animations/slot_<id>/`, `master.srt`, `verify/`, `preview.mp4`, `final.mp4`

## 다른 공개 스킬 저장소 (참고용)

| 저장소 | 쓸 만한 것 |
|---|---|
| [remotion-dev/skills](https://github.com/remotion-dev/skills) (공식) | 작업 유형별 하위 스킬 라우팅, 사용자 변경 보존 |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | 계획→HTML→lint/check→preview→render, seek 결정성, `class="clip"` 계약. 로컬은 jp-auto-youtube 프로젝트 전용 설치(전역 부작용 주의) |
| [haidrrrry/claude-remotion-skill](https://github.com/haidrrrry/claude-remotion-skill) | linear 금지, 2~3 속성 조합 진입, 3~6프레임 스태거, 렌더→프레임 확인 루프 (커뮤니티 스타일) |
| [ychoi-kr/claude-ffmpeg-skill](https://github.com/ychoi-kr/claude-ffmpeg-skill) | ffprobe 먼저, 짧은 테스트, 출력 검증 |
| [AgriciDaniel/claude-video](https://github.com/AgriciDaniel/claude-video) | 15개 하위 스킬, 배경 휘도 분석으로 자막 대비 조정 |
| [affaan-m/ecc video-editing](https://github.com/affaan-m/ecc/tree/main/skills/video-editing) | "Structure before style", 층별 도구 분리 |
| [digitalsamba/claude-code-video-toolkit](https://github.com/digitalsamba/claude-code-video-toolkit) | 생성형 제작 툴킷(편집보다 제작) |

## 우리 실측 (2026-09-27, 100초 한국어 강의 영상)

| 단계 | 결과 |
|---|---|
| 분석(`analyze.sh`) | 8초. 문장·단어 전사, 무음 11구간(11.8초), 장면 후보 2, 콘택트시트 2장 |
| 초안 EDL → 렌더 | 100.0초 → 92.5초(7구간), 예상 92.480 / 실측 92.501초 |
| 컷 경계 검수 | 6개 편집점 파형 모두 발화 소멸 후 컷, 다음 단어 어택 보존 |
| 마스터 → QA | -17.8 → -14.1 LUFS, TP -1.5, BT.709 변환, faststart, FAIL 0 |
| 발견한 문제 | whisper.cpp 단어 타임스탬프가 무음 97% 덮음(스냅 불가), BT.601 소스에 709 태그만 붙이면 primaries가 안 바뀜(실제 변환으로 해결), showwavespic는 `-t`를 입력 옵션으로 둬야 함 |
| 못 한 것 | 귀로 듣는 청취 검수, 그래픽·자막 번인 단계 실측, WhisperX·Scribe 비교 |
