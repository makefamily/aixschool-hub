# 영상 편집 수치 치트시트

기준일 2026-09-27. "공식"은 플랫폼·표준 문서에 명시된 값, "시작값"은 편집 프리셋(조정 전제)이다. 출처는 플랫폼·표준 공식 문서.

## 1. 프레임 환산

| 개념 | 값 |
|---|---|
| 프레임 수 | 초 × fps |
| 23.976 / 29.97 / 59.94 | `24000/1001` / `30000/1001` / `60000/1001` (float 누적 금지) |
| 1프레임 | 24fps 41.7ms · 30fps 33.3ms · 60fps 16.7ms |
| 180도 셔터 | 1/(2×fps): 24→1/48, 30→1/60, 60→1/120 (촬영 규칙) |
| 슬로모션 | 60fps 촬영을 30fps 타임라인에서 50% = 보간 없이 2배 느림 |
| 드롭프레임 TC | 번호만 건너뜀. 프레임 삭제 아님 |

## 2. 모션그래픽 타이밍 (시작값)

| 요소 | 초 | 30fps 프레임 |
|---|---|---|
| 작은 UI·아이콘 반응 | 0.10~0.22 | 3~7 |
| 텍스트 진입 | 0.20~0.45 | 6~14 |
| 대형 타이틀 리빌 | 0.45~0.90 | 14~27 |
| 스태거 간격 | 0.067~0.133 | 2~4 |
| 짧은 전환 | 0.20~0.50 | 6~15 |
| 로고 리빌 | 0.70~1.50 | 21~45 |
| 큰 제목 최소 체류 | 1.0~2.0 | 30~60 |
| 핵심 수치·차트 체류 | 1.5~3.0+ | 45~90+ |
| 앤티시페이션 | 반대 방향 | 2~5 |
| 로어서드 | 발화 시작 직후 등장, 8~12프레임 안에 식별 가능 | |
| 블랙/화이트 플래시 | 2프레임 = 24fps 83ms, 30fps 67ms (접근성 주의) | |

**이징**
- 진입: `cubic-bezier(0.16, 1, 0.3, 1)` 또는 `(0.22, 1, 0.36, 1)`
- 퇴장: `cubic-bezier(0.4, 0, 1, 1)`
- 표준 ease-out: `cubic-bezier(0, 0, 0.2, 1)`
- 등속(linear)은 기계적 움직임에만
- 스프링: stiffness↑ 빠르고 강함, damping↓ 진동 오래, mass↑ 묵직. 값의 의미는 라이브러리마다 다름(Remotion `spring({fps, frame, config:{damping:200}})` 은 오버슈트 없는 부드러운 정착)

## 3. 컷·오디오 경계

| 항목 | 값 |
|---|---|
| 컷 핸들 | 2~5프레임, 대화는 100~250ms부터 |
| 컷 오디오 페이드 | 30ms (팝 방지, 5~15ms도 가능) |
| 무음 감지 시작값 | -38~-45 dB, 0.4~0.8초 |
| 무음 제거 실측 | 3초 기준 → 84분이 41분(무음 57%) |
| 필러 | 어/음·더듬기 컷, 그/자/좀/약간/뭐 보존, "이제"는 0.8초 이상만 |
| silenceremove 시작값 | start 0.25s, stop 0.45s, -38dB |
| 박자 | 1박 = 60/BPM초 (120BPM = 0.5초, 4박 마디 2초) |

## 4. 오디오 믹스

| 항목 | 값 | 근거 |
|---|---|---|
| 온라인 통합 라우드니스 | -14 LUFS (-16~-14) | 업계 관행. 유튜브 공식 강제값 아님 |
| 트루피크 | -1 dBTP 이하 | EBU·관행 |
| 방송(EBU R128) | -23 LUFS, TP -1 | 공식 |
| 미국 방송 | -24 LKFS | ATSC A/85 (원문 대조 필요) |
| 보이스 하이패스 | 70~100Hz(80 기본), 저음 남성은 A/B | |
| 명료도 대역 | 2~5kHz, 탁함 200~500Hz, 치찰 4~10kHz | |
| 대화 컴프 | 2:1~3:1, attack 5~20ms, release 50~150ms | |
| BGM 덕킹 | sidechaincompress threshold 0.03, ratio 6, attack 20, release 250 | 시작값 |
| 샘플레이트 | 48kHz, AAC 192k(유튜브 권장 384k 스테레오) | 유튜브 공식 |

## 5. 자막

| 항목 | 값 |
|---|---|
| 넷플릭스 한국어 | 줄당 16자, 성인 12자/초, 아동 9자/초, 최대 2줄 |
| 넷플릭스 이벤트 길이 | 최소 5/6초, 최대 7초 |
| 우리 롱폼 정답지 | median 19자, 2.03초 → `--max-chars 32 --target-chars 20 --max-dur 4.8` |
| 세로 영상 한 줄 | 12~16자 |
| 쇼츠 자막 관행 | 1~2 단어 청크, 워드 하이라이트. 우리 규칙(한 단어씩·2어절 이하·위치 고정·84~93px)은 `shorts-rules.md` 2장 |
| 스타일 | Pretendard SemiBold 이상, 박스 없음(요청 시만 `--box`) |
| CPS | 표시 글자수 ÷ 표시 초 |

## 6. 색·신호

| 항목 | 값 |
|---|---|
| SDR 웹 납품 | `yuv420p`, BT.709 태그 3종(`-color_primaries bt709 -color_trc bt709 -colorspace bt709`) |
| 리미티드 레인지 | Y 16~235, C 16~240 (8bit). 유튜브는 풀→리미티드 변환 |
| 밴딩 대응 순서 | 고정밀 유지 → 올바른 변환 → 디더 → 미세 그레인 (`deband`, `gradfun`) |
| 로그 순서 | 입력 변환 LUT 1회 → WB/노출 → 1차 → 2차 → 룩 → 출력 변환 |
| 태그 ≠ 변환 | 메타데이터만 바꾸면 색은 안 바뀐다 |

## 7. 플랫폼 내보내기

| 플랫폼 | 해상도 | fps | 비트레이트 | 기타 |
|---|---|---|---|---|
| YouTube 1080p SDR | 1920×1080 | 원본 유지 | 24~30fps 8Mbps / 48~60fps 12Mbps | H.264 High, closed GOP = fps/2, AAC 48kHz, faststart (공식) |
| YouTube 4K | 3840×2160 | 원본 | 35~45 / 53~68 Mbps | 공식 |
| YouTube Shorts | 1080×1920 | 30 또는 60 | 8~12Mbps 시작값 | 정사각·세로 3분 이하가 Shorts(2024-10-15 이후, 공식) |
| Instagram Reels | 1080×1920 | 30 CFR | 공식 미확인 | 광고 사양: H.264, AAC 128k+, 4GB, 15분 |
| TikTok | 1080×1920 | 30 | 공식 미확인 | 광고: 540×960 이상, 5~60초, 500MB |
| X | 최대 1920×1200 / 1200×1900 | 최대 40 | 최대 25Mbps | 비프리미엄 140초·512MB (공식) |
| LinkedIn | 1920×1080 | 30 | 미확인 | |
| 네이버 클립·카카오 | 미확인 | | | 업로드 화면에서 확인 |

**세이프존**: 공식 픽셀값 없음. 자막·얼굴·CTA는 가로 중앙 80% 안, 세로 영상은 하단 캡션·오른쪽 버튼 열 피함, 앱 미리보기로 최종 확인.

**FFmpeg 프리셋**

```bash
# YouTube 1080p30
ffmpeg -i in.mov -vf "fps=30,format=yuv420p" -fps_mode cfr \
  -c:v libx264 -preset slow -crf 18 -profile:v high -level:v 4.1 \
  -g 15 -keyint_min 15 -sc_threshold 0 -maxrate 12M -bufsize 24M \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
  -c:a aac -b:a 384k -ar 48000 -ac 2 -movflags +faststart yt_1080p30.mp4

# 세로 1080x1920 30fps (채우기 크롭. 얼굴 위치는 crop x 좌표로 조정)
ffmpeg -i in.mp4 -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,format=yuv420p" \
  -c:v libx264 -preset slow -crf 19 -c:a aac -b:a 192k -ar 48000 -movflags +faststart vertical.mp4

# 알파 중간물 (ProRes 4444)
ffmpeg -i rgba.mov -c:v prores_ks -profile:v 4 -pix_fmt yuva444p10le -c:a pcm_s24le alpha.mov

# 맥 하드웨어 인코딩(초안용. CRF와 품질 대응표 없음)
ffmpeg -i in.mov -c:v hevc_videotoolbox -q:v 60 -tag:v hvc1 -c:a aac draft.mp4

# 재인코딩 없이 faststart만
ffmpeg -i in.mp4 -c copy -movflags +faststart out.mp4
```

## 8. 파일명·폴더

```
{프로젝트}_{콘텐츠ID}_{비율}_{해상도}_{fps}_{코덱}_{색공간}_v{번호}.{확장자}
launch_042_reel_1080x1920_30p_h264_bt709_v03.mp4
```

## 9. 환경 참고(한 대의 실측 예시, 사람마다 다름)

| 항목 | 상태 |
|---|---|
| FFmpeg | 8.x 에서 실측. `ffmpeg -version`으로 확인 |
| 있는 필터 | lut3d, loudnorm, ebur128, sidechaincompress, afftdn, arnndn, dialoguenhance, speechnorm, silencedetect, blackdetect, freezedetect, scdet, xfade, tile, ssim, deband, tonemap, colortemperature, subtitles/ass, drawtext |
| 없는 필터 | zscale, libvmaf, vidstab (필요 시 다른 빌드) |
| 인코더 | libx264, libx265, h264/hevc_videotoolbox, prores_ks, libsvtav1, libaom-av1, libvpx-vp9 |
| 전사 | whisper-cli(ggml large-v3-turbo 모델 파일은 환경변수 `WHISPER_MODEL`로 지정), MLX whisper(Apple Silicon 맥) |
| Remotion | 설치 여부·버전은 프로젝트별로 확인한 뒤 사용 |
| 선택 도구 | auto-editor, WhisperX, pyannote, Demucs, PySceneDetect, MediaPipe, OTIO, HyperFrames (없으면 쓰지 않고 대안을 쓴다) |
