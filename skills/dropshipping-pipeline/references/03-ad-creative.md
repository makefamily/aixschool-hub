# 3단계 — 광고 이미지·카피

## 5종 컨셉 프레임워크

소재는 항상 아래 5가지 각도로 뽑는다.

1. 문제 정면 노출
2. 해결 후 모습
3. 사용 전후 비교
4. 실제 사용 장면
5. 숫자·근거 앞세움

각 소재마다 세트로 산출:
- 영어 이미지 프롬프트 1줄 (사진 스타일·인물·조명·구도·렌즈감 포함)
- 한글 헤드라인 15자 이내
- 본문 카피 2문장

## 금지 표현

효능 단정, 의학적 표현, 과장된 수치, 비포/애프터 조작 암시.

## 이미지 생성 (Higgsfield CLI — MCP 아님)

### 필수 사전 순서

```bash
higgsfield account status          # 로그인 + 잔여 크레딧
higgsfield workspace list          # 필요 시 select
higgsfield model list              # 모델 확인
higgsfield generate cost <model> --prompt "..."   # 예상 크레딧 산정
```

→ **예상 크레딧 + 잔여 크레딧을 사용자에게 보고하고 명시 승인을 받은 뒤에만 생성한다.** 자동승인 권한은 비용 보고 면제가 아니다.

### 모델 선택

| 모델 | 크레딧 | 특징 |
|------|--------|------|
| `text2image_soul_v2` | 0.12 | 사실적 인물·라이프스타일. **기본값** |
| `nano_banana_pro` | 2 | 17배 비쌈. Soul 결과가 아쉬울 때만 |

### 생성·저장

```bash
higgsfield generate create text2image_soul_v2 \
  --prompt "<영어 프롬프트>" --aspect-ratio 4:5 --resolution 2k
higgsfield generate wait <job_id>
curl -fsS -o "claudedocs/<상품슬러그>/03-ad-01.png" "<결과 URL>"
```

기본 규격: 4:5, 2K (피드용). 스토리/릴스가 필요하면 9:16.

## 생성 후 자기검수 (생략 금지)

이미지를 실제로 확인하고 **헤드라인·본문이 이미지와 실제로 맞는지** 재점검한다.
어긋나면 재생성(추가 비용)보다 **카피를 이미지에 맞춰 재작성**하는 것을 우선 검토하고, 비용 대비 판단을 함께 보고한다.
대안 헤드라인 A/B 2개를 항상 함께 제시한다.

## 산출

- `claudedocs/<상품슬러그>/03-ad-01.png` …
- `claudedocs/<상품슬러그>/03-copy.md` — 소재별 헤드라인/본문 + A/B 대안 + 사용 프롬프트 원문
