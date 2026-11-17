> 찾아 읽는 자료 — 전부 읽지 말고 아래 목차에서 필요한 절만 찾아 읽는다. (2026-11-15 문서 상한 규칙)
>
> 목차
> - 1. 전제: 에이전트는 영상을 "보지" 않는다
> - 2. 절대 규칙
> - 3. 표준 파이프라인 (9단계)
>   - 0단계. 브리프 (5분)
>   - 1단계. 인제스트
>   - 2단계. 이해 (중간 표현 만들기)
>   - 3단계. 편집안(EDL) 작성 — 첫 번째 승인 게이트
>   - 4단계. 러프컷 렌더
>   - 5단계. 컷 경계 자가 검수
>   - 6단계. 디자인 패스 (그래픽·자막·색·사운드)
>   - 7단계. QA 게이트 — 두 번째 승인 게이트
>   - 8단계. 딜리버리
> - 4. 도구 선택표
> - 5. 포맷별 빠른 결정 
> - 6. 주인 결정이 필요한 항목 (자동 진행 금지)
> - 7. 반복 실패 패턴 (사례 조사에서 추출)

# 영상 편집 운영 매뉴얼 (에이전트용 정본)

기준일 2026-09-27. 영상 편집을 맡으면 이 파일을 먼저 읽고, 세부는 `cheatsheet.md`, `qa-gate.md`에서 찾는다.
근거 사례는 `claude-edit-cases.md`에 있다.

---

## 1. 전제: 에이전트는 영상을 "보지" 않는다

- Claude(Opus 5.5 포함)는 영상 파일을 직접 입력받는 공식 기능이 확인되지 않았다. 이미지 입력만 공식이다. (Anthropic Vision 문서, 2026-09 조사)
- 그래서 편집 판단은 **중간 표현**을 읽고 내린다: 워드 타임스탬프 전사, 무음·장면 전환 목록, 타임코드가 박힌 콘택트시트, 컷 경계 필름스트립, 파형 이미지, ffprobe 메타데이터.
- 공개 사례 중 품질이 가장 검증된 흐름은 모두 같은 구조다: **전사·메타데이터 → 모델이 이유를 적은 EDL(JSON) → FFmpeg 같은 도구가 결정론적으로 실행 → 컷 경계 자가 검수 → 사람이 미감·최종본 승인.** (Fable 5 출시 영상 제작 덱, browser-use/video-use)
- 에이전트가 잘하는 것: 무음·필러 제거, 테이크 선택, 자막, 템플릿 모션그래픽, 반복 렌더, 기술 QA.
- 사람 판단이 남는 것: 감정 타이밍, 룩(색)의 의도, 멀티캠 서사, 발언 맥락 왜곡 여부, 최종 공개.

## 2. 절대 규칙

1. **원본 불가침.** 원본은 읽기 전용. 모든 산출물은 새 경로, 버전 번호를 올려 저장한다. 덮어쓰기 금지.
2. **판단과 실행 분리.** 모델은 EDL(JSON)을 만들고, 렌더는 스크립트가 한다. 모든 컷에 `reason`을 남긴다.
3. **시간은 프레임으로.** 초 float가 아니라 프레임 번호 + 유리수 fps(`30000/1001`)로 저장한다. 렌더 직전에만 초로 변환한다.
4. **단어 안에서 자르지 않는다.** 컷은 전사의 단어 경계에 맞추고(snap) 양쪽에 30~200ms 여유를 둔다. 전사 타임스탬프는 50~120ms 흔들린다(video-use·Cutback 보고). 무음 400ms 이상은 비교적 안전한 컷 후보, 150~400ms는 영상 확인 후, 150ms 미만은 위험. 모호하면 파형으로 확인한다.
   - **전사 도구 결정(2026-09-27 실측, 100초 한국어 강의)**: 무음 구간을 단어가 덮은 비율 / 경계 오차 median / 100ms 이내 비율
     - whisper.cpp large-v3-turbo: 98% / 339ms / 20% — 단어 끝을 다음 멈춤까지 늘려 잡아 스냅 불가
     - MLX Whisper 단독: 72% / 546ms / 15%
     - WhisperX 단독(CPU): 30% / 109ms / 46%, 100초에 246초로 느림
     - **채택: MLX 전사 + WhisperX 한국어 wav2vec2 정렬 + 오디오 에너지 스냅 = 2% / 0ms / 78%, 100초에 23~55초** (`scripts/edit/transcribe_words.py`)
     - 정렬기는 숫자·기호(예: "72.5%입니다")를 짧게 잡는다. 그래서 구간 끝은 단어 끝이 아니라 **그 뒤 첫 무음 시작**으로 정한다(`edl_from_keep.py`가 자동 처리). 한국어 어미는 끝이 흐려져 끝 여유(250ms)를 앞(120ms)보다 길게 둔다.
     - 유료 전사 API는 쓰지 않는다. 로컬 전사만 쓴다.
4-1. **구조 먼저, 스타일 나중.** 러프컷이 잠기기 전에는 그래픽·자막·색을 입히지 않는다. 러프컷과 그래픽은 별도 대화(세션)로 나눠 맥락 잡음을 줄인다.
4-2. **자막은 필터 체인의 마지막.** 모든 오버레이 뒤에 입힌다. SRT 시간은 출력 타임라인으로 다시 계산한다: `output_time = word.start - segment_start + segment_offset`.
5. **길이·수치는 코드로 계산.** EDL의 총 길이는 모델이 쓰지 않고 스크립트가 구간 합으로 계산하며, 렌더 후 `ffprobe`와 대조해 허용 오차를 넘으면 실패 처리한다. 모델 자기 보고를 믿지 않는다(Opus에게 300초 하이라이트를 시켰더니 299.32초라고 보고했지만 실제 합계 578.24초, 11개 컷 전부 문장 중간 절단 — Cutback 자체 실험, 2026-09-22).
6. **렌더 완료 ≠ 완료.** `qa-gate.md`의 기술 검사 + 컷 경계 시각 검사 + 최종 결과물 캡처를 보고서에 붙인 뒤에만 완료를 말한다.
7. **외부 효과는 사람 게이트.** 업로드·게시·유료 API(전사·TTS·생성형 영상)·클라우드 전송은 비용·대상 보고 후 승인. 업로드는 비공개가 먼저.
8. **권리 기록.** BGM·효과음·폰트·스톡마다 출처 URL, 라이선스, 다운로드 날짜를 `assets.json`에 남긴다. CC BY-NC는 수익화 영상에 넣지 않는다.
9. **표기 규칙(기본값).** 이모지 금지, 회차 표기(1화/EP1) 금지(재생목록으로 표현), 브랜드 색은 사용자가 정한 기본 강조색 계열, 자막은 Pretendard SemiBold 이상·박스 없음(요청 시에만 `--box`).

## 3. 표준 파이프라인 (9단계)

작업 폴더 구조:

```
<project>/
  01_source/        원본 (읽기 전용) + checksums.sha256
  02_analysis/      probe.json, words.json, silences.json, scenes.json, contact/*.jpg
  03_edl/           edl_v001.json ... (승인본은 approved: true)
  04_work/          세그먼트, 프록시, 중간 렌더
  05_graphics/      그래픽 소스와 렌더
  06_exports/       최종본 (파일명 규칙: 01-치트시트.md §8)
  07_qc/            QA 로그, 컷 경계 필름스트립, 보고서
  assets.json       음원·폰트·스톡 권리 기록
  brief.md          0단계 브리프
```

### 0단계. 브리프 (5분)

아래를 `brief.md`에 채운다. 비어 있으면 합리적 기본값을 쓰고 가정으로 기록한다. 질문은 주인 결정(공개 범위, 비용, 방향)만 한다.

| 항목 | 예시 |
|---|---|
| 목적·시청자 | AI 학교 설명회 유입, 40대 자영업자 |
| 플랫폼·비율 | YouTube 롱폼 16:9 / Shorts·Reels 9:16 |
| 목표 길이·허용 오차 | 8분 ±10% |
| 포맷 | 토킹헤드·튜토리얼·인터뷰·설명영상 등 |
| 톤·레퍼런스 | 레퍼런스 영상 URL 1~3개 |
| 브랜드 토큰 | 색, 폰트, 로어서드 위치, 자막 스타일 |
| 산출물 | 마스터 1 + 세로 클립 N + SRT |
| 승인 지점 | EDL 승인, 러프컷 승인, 최종 승인 |

### 1단계. 인제스트

```bash
mkdir -p 01_source 02_analysis 03_edl 04_work 05_graphics 06_exports 07_qc
shasum -a 256 01_source/* > 01_source/checksums.sha256
for f in 01_source/*.{mp4,mov,MP4,MOV}; do
  [ -e "$f" ] || continue
  ffprobe -v error -show_format -show_streams -of json "$f" > "02_analysis/$(basename "$f").probe.json"
done
```

확인할 것: `r_frame_rate` vs `avg_frame_rate`(다르면 VFR 의심 → CFR 변환), 회전 메타데이터, 색 태그(bt709 여부, Log 촬영 여부), 오디오 채널·샘플레이트, 카메라/화면 2트랙이면 싱크 필요.

- VFR(휴대폰·화면녹화)이면 편집 전 CFR 중간본을 만든다: `ffmpeg -i in.mov -vf fps=30 -fps_mode cfr -c:v libx264 -crf 16 -c:a copy work_cfr.mp4`
- 4K·고비트레이트면 540p~720p 프록시로 분석·미리보기하고 최종만 원본으로 렌더한다.
- 2트랙(카메라+화면) 싱크: 클랩/파형 상호상관으로 오프셋을 구한다. 실측 예: 카메라가 화면보다 1.410초 먼저 시작.

### 2단계. 이해 (중간 표현 만들기)

**전사 (로컬, 무료, 단어 단위 정밀)**

```bash
bash scripts/edit/setup_asr.sh                       # 최초 1회, 약 1.3GB. 이미 Whisper가 설치된 python이 있으면 생략
PY=<Whisper가 설치된 python 경로>     # 없으면 사용자에게 설치가 필요하다고 알린다
$PY scripts/edit/transcribe_words.py 01_source/a.mp4 02_analysis/a   # → a.words.json, a.srt, a.silences.json
python scripts/edit/pack_transcript.py 02_analysis/a.words.json > 02_analysis/a.packed.md
```

- 에이전트는 `a.packed.md`(문구 단위, 단어번호 `w12–w30`, 앞 공백 초)를 읽고 편집을 판단한다. 영상 전체를 보지 않는다.
- 도메인 프롬프트는 쓰지 않는다(조용한 구간 반복 환각 실측). 반복 환각(같은 문장 4회+ 연속)은 스크립트가 경고한다.
- 고유명사·숫자·브랜드명("Thariq→Sark", "ChatGPT", "Hormozi" 오인식 사례)은 교정표를 두고 자막 전 대조한다.
- 빠른 초벌만 필요하면 `analyze.sh`(whisper.cpp, 27분에 약 46초). 단, 이 결과로는 단어 경계 컷을 하지 않는다.

**무음·장면·시각 요약**

```bash
# 무음 후보 (토킹헤드 출발점: -38~-45dB, 0.4~0.8초)
ffmpeg -i a.mp4 -af "silencedetect=noise=-40dB:d=0.5" -f null - 2> 02_analysis/silence.log
# 장면 전환 후보 (scdet, 임계 10~15부터)
ffmpeg -i a.mp4 -vf "scdet=threshold=12,metadata=print:file=02_analysis/scenes.txt" -f null -
# 타임코드가 박힌 콘택트시트 (2초 간격, 5x5 = 50초 분량/장)
ffmpeg -i a.mp4 -vf "fps=1/2,scale=384:-1,drawtext=text='%{pts\:hms}':x=6:y=6:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.6,tile=5x5" \
  -vsync vfr 02_analysis/contact_%03d.jpg
```

- 모든 프레임을 보지 않는다. 순서: 전체 콘택트시트(저해상도) → 전사에서 후보 구간 추림 → 후보 전후만 원해상도로 추출해 확인.
- 썸네일마다 타임코드를 박는다. 그리드에서 모델이 순서를 오독하는 문제를 막는다.
- 이해 결과를 시간축 세그먼트로 묶는다: `{start, end, speaker, text, asr_conf, scene_id, visual_note, audio{speech, peak}, decision{keep, reason}}`.

### 3단계. 편집안(EDL) 작성 — 첫 번째 승인 게이트

EDL 스키마 (`03_edl/edl_v001.json`):

```json
{
  "version": 1,
  "fps": "30000/1001",
  "target_duration_s": 480,
  "tolerance_s": 48,
  "segments": [
    {
      "id": "s001",
      "source": "01_source/take_03.mp4",
      "in_frame": 56,
      "out_frame": 367,
      "text": "첫 문장 전사",
      "reason": "문장 시작이 온전하고 필러 없음. 3번 테이크가 1번보다 발음 명확",
      "confidence": 0.82,
      "review": false,
      "audio_fade_ms": 30,
      "transition": "cut"
    }
  ],
  "rejected": [
    {"source": "take_01.mp4", "in_frame": 0, "out_frame": 400, "reason": "말 더듬음 2회"}
  ],
  "approved": false
}
```

추가 필드(필요할 때): 장면별 `candidate_takes`와 `selection_rationale`(Fable 사례: "C017은 문장 중간 5.8초 정지로 탈락, C003이 가장 깨끗한 완결 테이크"), 세그먼트별 `beat`(HOOK/PROBLEM/SOLUTION/CTA)와 `quote`(첫 몇 단어). 총 길이는 `model_estimate_s`와 스크립트가 계산한 `computed_s`를 따로 적는다.

판단 규칙:
- 테이크 선택: 같은 문장을 여러 번 말했으면 기본은 마지막 온전한 테이크(보통 뒤가 낫고 "음"이 적다). 예외를 허용하고 이유를 적는다.
- 다시 말한 곳은 `retake_check.py 원본`의 확정 목록으로 찾는다(전사만 읽으면 Whisper가 반복을 뭉개 안 보인다). `→ 지울 후보 a~b초`가 앞 테이크다. 무음 컷(`edl_from_silence.py`, select 필터)만으로 끝내지 않는다.
- 필러: "어/음", 더듬기, 반복은 컷. "그/자/좀·약간·뭐"는 보존. "이제"는 0.8초 이상일 때만 컷. 웅얼거림은 자동 컷 금지.
- 무음: 3초 이상은 거의 컷(실측: 84분 → 41분, 무음 57%). 1초 미만의 멈춤은 강조·호흡이면 남긴다. 리액션·웃음 전 침묵은 남긴다.
- 월터 머치 우선순위로 충돌을 푼다: 감정 > 이야기 > 리듬 > 시선 추적 > 2D 구도 > 3D 연속성.
- 발언 순서 재배열은 의미가 바뀌면 금지. 인터뷰·다큐는 재배열 전 사람 확인.
- EDL 검증기: 역전·음수 구간, 원본 길이 초과, 중첩, 12프레임 미만 초단편, 예상 총 길이 vs 목표를 자동 검사한다.
- 사람에게 보여줄 때: 총 길이, 제거한 분량, `review: true` 목록, 거절 사유 상위 5개만.

### 4단계. 러프컷 렌더

검증된 스크립트(`scripts/edit/`, 2026-09-27 실제 강의 영상 100초로 전 과정 PASS, 13.7초 하이라이트 roundtrip 일치율 1.000):

| 스크립트 | 역할 |
|---|---|
| `analyze.sh <원본> <출력폴더>` | probe, 16k wav, 단어·문장 전사(JSON/SRT), 무음 JSON, 장면 후보, 타임코드 콘택트시트 |
| `transcribe_words.py <원본> <접두사>` (asr-venv) | 단어 단위 정밀 전사 + 무음 목록 + 문장 SRT |
| `pack_transcript.py words.json` | 에이전트가 읽는 문구 단위 전사(단어번호 포함) |
| `edl_from_keep.py <원본> words.json keep.json edl.json` | **주력**: 에이전트가 고른 살릴 단어 범위(`[{"words":"w87-w93","reason":..,"beat":"HOOK"}]`) → 프레임 정확 EDL. 단어 침범 금지, 끝은 실제 무음까지 |
| `edl_from_silence.py <원본> silences.json edl.json --words words.json` | 무음만 빼는 기계 초안(approved=false) |
| `render_edl.py edl.json out.mp4 [--draft] --cutlist cuts.txt` | 프레임 정확 세그먼트 렌더 + 30ms 페이드 + concat, 예상/실측 길이 대조, 편집점 목록 저장 |
| `cut_strips.sh out.mp4 cuts.txt qc/` | 편집점별 필름스트립 + 파형(빨간 선) |
| `master.py in.mp4 final.mp4 [--lufs -14]` | 2-pass loudnorm + BT.709 실제 변환(601 소스는 colorspace 변환) + faststart |
| `qa_check.sh final.mp4 목표초 허용초 목표LUFS` | 기술 QA 표 + 5지점 프레임 캡처, FAIL 개수로 종료 코드 |
| `roundtrip_check.py final.mp4 edl.json` (asr-venv) | 완성본을 다시 전사해 의도한 대사와 비교. 잘린 단어를 자동 검출(실측: "72.5%입니다." 절단을 FAIL로 잡음) |

수동으로 할 때:

- 프레임 정확 컷이 필요하면 재인코딩한다. `-c copy`는 키프레임 경계에서만 잘린다(실측: 키프레임 불일치로 재인코딩 불가피).
- 세그먼트 렌더 후 concat. 모든 세그먼트의 코덱·해상도·fps·샘플레이트를 통일한 뒤 이어 붙인다.

```bash
# 세그먼트 1개 (in/out은 프레임→초로 변환한 값)
ffmpeg -ss 1.868 -i take_03.mp4 -t 10.377 \
  -af "afade=t=in:d=0.03,afade=t=out:st=10.347:d=0.03" \
  -c:v libx264 -preset veryfast -crf 18 -r 30000/1001 -c:a aac -ar 48000 -b:a 192k 04_work/s001.mp4
# 이어 붙이기
printf "file '%s'\n" 04_work/s*.mp4 > 04_work/list.txt
ffmpeg -f concat -safe 0 -i 04_work/list.txt -c copy 04_work/rough_v001.mp4
```

- 컷마다 30ms 오디오 페이드로 팝을 막는다(video-use 기본값). 룸톤이 이어지는 구간은 크로스페이드가 이중 소리를 낼 수 있으니 청취 확인.
- 러프컷은 `--draft`(720p, veryfast)로 먼저 보여주고 승인 후 최종 품질로 다시 렌더한다.
- 수정은 바뀐 세그먼트만 다시 렌더한다(부분 재렌더로 약 10배 단축 주장 사례, 캐시 키에 소스 해시·EDL 버전 포함).

### 5단계. 컷 경계 자가 검수

모든 편집점에서 앞 0.5초·뒤 0.5초 프레임 스트립과 파형을 만들어 직접 본다(`scripts/edit/cut_strips.sh`, 빨간 선 = 편집점). 오버레이·자막이 들어간 뒤에는 범위를 ±1.5초로 넓혀 자막이 그래픽에 가리는지, 오버레이가 엉뚱한 프레임에 붙었는지까지 본다. 공개용이면 첫 2초·끝 2초·중간 2~3점도 샘플링한다(video-use 자가 검수 규칙).

```bash
# 편집점 t(초) 주변 6프레임 스트립
ffmpeg -ss $(echo "$t-0.5" | bc) -i rough.mp4 -t 1 -vf "fps=6,scale=320:-1,tile=6x1" -frames:v 1 07_qc/cut_${i}.jpg
# 같은 구간 파형
ffmpeg -ss $(echo "$t-0.5" | bc) -i rough.mp4 -t 1 -filter_complex "showwavespic=s=960x160:colors=white" -frames:v 1 07_qc/wave_${i}.png
```

검사: 단어·받침 잘림, 팝, 시선·손 위치의 큰 점프(점프컷이 의도인지), 검은/정지 프레임. 문제는 핸들을 늘리거나 컷을 옮겨 해당 세그먼트만 재렌더한다. 자동 수정은 최대 3회, 이후 사람에게 보고.

### 6단계. 디자인 패스 (그래픽·자막·색·사운드)

순서를 지킨다: **구조(컷) → 색 → 그래픽 → 자막 → 사운드 믹스.** 한 번에 "예쁘게"를 요청하지 않고 항목별로 한다.

- **색**: Log 원본이면 먼저 카메라 변환 LUT(1회만), 그다음 룩. LUT 후보를 3개 렌더해 사람이 고른다. `format=gbrp,lut3d=file=look.cube:interp=tetrahedral,format=yuv420p`. 로컬 FFmpeg에는 `zscale`이 없으므로 HDR→SDR 톤매핑은 `colorspace`/`tonemap` 필터 또는 Resolve로 한다.
- **모션그래픽**: 브랜드 토큰(색·폰트·이징·위치)을 파일로 고정하고 Remotion 또는 HyperFrames로 만든다(설치돼 있지 않으면 사용자에게 설치가 필요하다고 알린다). 타이밍 표는 `cheatsheet.md §2`.
  - 전역 타이밍 상수를 한 파일에 모은다(Fable 사례 `anim.tsx`, 24fps 프레임): `reveal 13, stagger 4, overlayIn 10, overlayOut 8, emphasisDelay 3`, `EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1)`.
  - 그래픽 등장은 큐 시트로 관리한다: `CUES = [{id:'lower-third', at:1.2, dur:4.5}, ...]`. `at`은 전사에서 해당 단어를 찾아 출력 타임라인 초로 넣는다. fps를 바꾸면 프레임 숫자를 다시 계산한다.
  - 오버레이 합성은 `setpts=PTS-STARTPTS+T/TB`로 출력 시작점에 맞춘다.
  - 1차 그래픽은 초안이다. **Second Pass**로 그래픽을 하나씩 보며 위치·크기·색·모션을 고친다(사례: 첫 패스 22분, 다듬기 2시간). 요청은 "얼굴 가리지 않게 하단으로, 조금 작게, 브랜드 색으로"처럼 목적·위치·크기·색을 함께 지정한다.
  - 애니메이션은 임의 프레임으로 seek해도 같은 그림이어야 한다(랜덤 시드 고정, 렌더 중 네트워크·시계 금지).
  - Remotion 공식 에이전트 스킬: `npx skills add remotion-dev/skills` (설치는 전역 변경이므로 승인 후). 핵심 규칙: 사용자가 바꾼 코드는 덮어쓰지 말고 의도로 간주하거나 확인한다.
- **자막**: ASS로 만들어 번인 + SRT 별도 보관. 롱폼 권장 조합 `--max-chars 32 --target-chars 20 --max-dur 4.8`(정답지 분포 median 19자·2.03초), 접속사로 끝나는 줄 0%. 세로 영상은 한 줄 12~16자.
- **사운드**: 보이스 하이패스 80Hz → 가벼운 컴프(2.5:1) → BGM 사이드체인 덕킹 → 2-pass loudnorm(온라인 -14 LUFS, TP -1 dBTP). SFX는 의미 있는 전환·강조에만.

### 7단계. QA 게이트 — 두 번째 승인 게이트

`qa-gate.md`를 그대로 실행한다. 기술 검사(길이·코덱·fps·LUFS·블랙·무음·클리핑) + 시각 검사(시작·중간·끝·모든 전환·가장 긴 자막·세이프존) + 청취 검사. 보고서에는 판정표만이 아니라 **실제 출력 캡처와 요청→결과→수정→수정결과**를 붙인다.

### 8단계. 딜리버리

플랫폼별 프리셋은 `cheatsheet.md §7`. 파일명 규칙, `export_manifest.json`(소스 해시·EDL 버전·명령행·FFmpeg 버전·자산 라이선스·최종 해시)을 남긴다. 업로드는 사람 승인 후 비공개로.

## 4. 도구 선택표

| 작업 | 1순위 | 대안 | 주의 |
|---|---|---|---|
| 컷·트림·합치기·인코딩 | FFmpeg 8.1(로컬) | MoviePy, PyAV | `-c copy`는 키프레임 컷 |
| 전사·워드 타임스탬프 | whisper-cli large-v3-turbo(로컬) | MLX whisper, WhisperX, 유료 전사 서비스(사용자 확인 후) | 고유명사 교정표 필수 |
| 화자 분리 | WhisperX+pyannote(미설치) | NeMo, FunASR | HF 토큰·약관 |
| 무음 컷 자동화 | `youtube edit/scripts/longform_*.py`(보유) | auto-editor(미설치) | 데드에어는 1차 렌더 후 `--spans`로만 |
| 장면 전환 | FFmpeg `scdet` | PySceneDetect, TransNetV2 | 페이드·플래시 오탐 |
| 모션그래픽·자막 애니 | Remotion 4.x | HyperFrames(HTML), Motion Canvas | Remotion 라이선스(§6), seek 결정성 |
| 수식·도식 애니 | Manim Community | Motion Canvas | |
| 3D·제품 | Blender bpy | Three.js/R3F | 렌더 시간 |
| 노이즈 제거 | FFmpeg `afftdn`/`arnndn`(로컬 있음) | DeepFilterNet, Adobe Enhance(업로드) | 과하면 자음 손상 |
| 음원 분리 | Demucs(미설치) | UVR | 목적이 노이즈 제거와 다름 |
| 세로 리프레임 | 얼굴 추적(MediaPipe)+EMA 스무딩 | 중앙 크롭 | 얼굴이 가장자리 5~10% 안에 붙지 않게 |
| 배경 제거 | RobustVideoMatting, SAM2 | rembg(이미지용) | 시간적 일관성 |
| 업스케일·보간 | Real-ESRGAN, RIFE | FFmpeg `minterpolate` | 컷 경계 넘는 보간 금지 |
| NLE 넘기기 | OTIO → Premiere/Resolve, FCPXML | EDL(CMX3600) | 효과·색은 안 넘어감 |
| NLE 직접 조작 | Resolve MCP, Premiere MCP | | 복제 프로젝트에서만, 버전 회귀 잦음 |
| 영상 의미 분석 보조 | 콘택트시트 + Claude 비전 | Gemini 영상 입력(외부 전송, 승인 필요) | 1fps 샘플링은 빠른 동작 놓침 |

## 5. 포맷별 빠른 결정 

| 포맷 | 구조 | 평균 샷 길이 시작값 | 핵심 |
|---|---|---|---|
| 유튜브 롱폼 | 콜드오픈→약속→맥락→챕터→전환점→결과→다음 행동 | 3~7초(B롤 2~5초) | 첫 30초에 제목·썸네일 약속을 실현 |
| 쇼츠·릴스 | 첫 이미지·첫 말→갈등 1개→증거 1개→펀치라인→루프 | 0.5~2초 | 1~2초 안에 주제, 첫 프레임 검정 금지, 끝 빈 프레임 금지 |
| 토킹헤드·강의 | 목표→설명→예시→오해→요약 | 4~10초 | 의미 단위 컷, 1초마다 기계적 컷 금지 |
| 튜토리얼·화면녹화 | 결과→준비물→단계→문제해결→결과 | 3~8초 | 클릭 지점 줌, 토큰·이메일 노출 마스킹 |
| 인터뷰·팟캐스트 | 강한 발언 콜드오픈→질문→답→후속→결론 | 4~12초 | 리액션을 다른 발언에 붙이지 않기 |
| 설명영상(일러스트) | 질문→단순 모델→단계→한계→요약 | 2~6초 | 비유와 사실 구분, 축·단위 명시 |
| 한국 예능형 | 인물·상황→규칙→반응→러닝개그→결과 | 0.5~2초(리액션) | 자막 위계(화자/강조/상황/농담), 효과음 선택적 |
| 광고 15/30초 | 욕구→가치→증거→CTA | 1~3초(디테일) | 가격·조건 읽을 시간, 원천 데이터 치환 |
| 뮤직비디오 | 곡 구조에 맞춘 에너지 | 0.5~2초(비트) | 1박 = 60/BPM초, 모든 박에 컷 금지 |
| 제품 데모·런치 | 문제→실제 UI 행동→결과→가치→CTA | 2~6초 | 실제 없는 기능 합성 금지 |

모든 수치는 공식 표준이 아니라 편집 시작 프리셋이다. 채널 리텐션 그래프로 조정한다.

## 6. 주인 결정이 필요한 항목 (자동 진행 금지)

- **Remotion 라이선스**: 무료 대상은 개인, 직원 3명 이하 영리 조직, 비영리, 평가 목적이다(공식 LICENSE.md). 규모가 큰 회사 명의로 쓰려면 Company License를 확인한다.
- 유료 전사·음성 합성·생성형 영상 도구 호출(유료 도구는 사용자 확인 후), Adobe Enhance 같은 업로드형 처리.
- 게시·업로드·공개 전환, 고객 원본의 외부 전송.
- 원본 삭제·정리.

## 7. 반복 실패 패턴 (사례 조사에서 추출)

1. 전사 타임코드로 바로 잘라 단어 중간이 잘림 → 핸들 + 파형 확인.
2. 목표 길이를 말로만 요청하고 검증 안 함 → `ffprobe`로 판정.
3. 모델이 영상을 봤다고 가정하지만 전사만 읽음 → 판단 근거(어느 프레임·발화)를 기록.
4. 셸 명령에 따옴표·공백·한글 경로가 들어가 깨짐 → 배열 인자(`subprocess.run([...])`), 경로는 항상 따옴표.
5. 고유명사 오인식을 자막에 그대로 번인 → 교정표.
6. Log 러프컷이 밋밋한 것을 오류로 착각 / LUT 이중 적용 → 입력 해석 먼저.
7. NLE·MCP 버전 차이로 일부 기능만 실패 → 복제 프로젝트에서 회귀 테스트.
8. 서브에이전트 수를 늘리면 품질이 오른다고 기대 → 병렬은 속도용, 판정은 메인.
9. 조회수·제작자 주장("10분 만에", "10배")을 품질 근거로 씀 → 우리 실측만 인정.
10. 편집 자동화와 자동 게시를 한 권한으로 묶음 → 게시는 별도 게이트.
11. Python 3.9로 렌더 막판 `zip(strict=)` 오류 → 3.13 이상 가상환경.
12. 알파 PNG가 체크무늬를 그린 "가짜 투명" → 알파 채널 실측 검사.
13. 웹폰트 404로 대체 폰트 렌더 → 렌더 전 폰트 로드 확인, 캡처로 글꼴 대조.
14. Qwen3-TTS 100자 초과 시 말속도 폭주 → 문장 단위 생성.
