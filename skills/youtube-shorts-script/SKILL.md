---
name: youtube-shorts-script
description: Create concise Korean YouTube Shorts/Reels scripts and matching head copy from attached or linked YouTube videos using an analysis-first workflow. Use when the user asks to turn a YouTube video, transcript, or video summary into a short-form Korean script with a strong hook, opening text/headline copy, compressed key points, CTA, video analysis, strategies, tips, or repeated Shorts script generation.
---

# YouTube Shorts Script

## Core Rule

Always analyze the source video or transcript before writing. Do not draft the script until the full analysis block is complete and explicitly says `분석 완료`.

Use only information confirmed in the video, transcript, captions, visible frame, title, or user-provided source material. If a detail cannot be confirmed, write `확인불가` or `언급없음` as appropriate.

The final script must be short-form first: concise, punchy, and suitable for Reels/Shorts narration. Prefer a tight 3-point script even when the original video contains more ideas.

Also provide head copywriting for the video's first screen/overlay. The head copy must hook viewers into the opening script and help retention by making the same promise the narration immediately begins to deliver.

## Required Workflow

### Step 1: Video Analysis

First produce this exact analysis structure:

```markdown
### 영상 분석 결과

📋 영상 분석 결과

1. 화자 성별: [남성/여성/확인불가]
   - 근거:

2. 화자 이름: [정확한 이름/언급없음]
   - 언급 위치:

3. 핵심 주제 (한 문장):

4. 전략/팁 개수: [정확한 숫자]개

5. 각 전략/팁:
   ① 제목:
      핵심 내용:
   ② 제목:
      핵심 내용:
   ③ 제목:
      핵심 내용:
   (계속...)

6. 언급된 구체적 수치:
   -
   -

7. 화자 배경/권위:
   - 경력:
   - 실적:

8. 영상 길이: [분:초]

✅ 분석 완료
```

Analysis rules:

- Determine speaker gender only from visible or spoken evidence. If uncertain, use `확인불가`.
- Use the exact spoken/displayed speaker name. If no name is present, write `언급없음`.
- Count all strategies or tips directly present in the source, but the final script may compress them into the best 3.
- Record only numbers directly present in the source.
- If video length is not available from the provided material, write `확인불가`.

### Step 2: Accuracy Check

Before writing, internally verify:

- Speaker gender was not guessed.
- Missing names are marked `언급없음`.
- Every strategy or tip is directly supported by the source.
- Numbers are recorded exactly.

If any item is uncertain, revise the analysis before continuing.

### Step 3: Format Selection

Select one format from the analysis:

- Format A: story-centered video.
- Format B: strategy or framework video.
- Format C: practical tips video with many small tactics.
- Format D: numbers or results are the strongest hook.

Output:

```markdown
### 선택한 포맷
포맷 [A/B/C/D]
```

### Step 4: Script Writing

Write head copy first, then the script after the selected format. The script itself must have no timestamps, section labels, meta comments, English name glosses, or Markdown bold.

### Head Copywriting

Before the script, output:

```markdown
### 헤드카피라이팅
1. [짧은 후보]
2. [짧은 후보]
3. [짧은 후보]
```

Head copy rules:

- Write 3 candidates.
- Prefer a 2-line overlay format like the user's examples. Write each candidate as two short lines separated by `/`.
- Keep each full candidate short enough for a Shorts/Reels first-screen overlay: usually 18-34 Korean characters total, up to about 40 characters when needed.
- Keep each line visually compact: usually 8-18 Korean characters per line.
- Use universal, everyday Korean. Avoid jargon, insider terms, platform-specific buzzwords, and words that only experts understand.
- Make the head copy connect directly to the first 1-2 sentences of the script. The viewer should feel the narration immediately continues the same promise.
- Focus on one clear curiosity gap, result, or transformation.
- Prefer concrete words over abstract words: `엑셀`, `파일`, `돈`, `앱`, `1시간`, `팔리는`, `바꾸는`, `월급`, `자동화`.
- Prefer spoken, viewer-facing phrasing over title-like phrasing. A good head copy should sound like a thought the viewer might say.
- Line 1 should usually trigger a reaction using a question, surprise, or bold judgment: `엑셀이 돈이 된다고?`, `이거 그냥 두면 손해`, `45분이면 충분합니다`.
- Line 2 should immediately explain the payoff in simple terms: `[도구/재료] + [방법] = [결과]`, `[시간] [도구]로 [결과]하는법`, or `[구체 대상] [수익화/자동화] 전략`.
- Use `하는법` rather than `하는 법` in head copy when the tighter visual rhythm helps the overlay fit.
- It is acceptable to use simple symbols such as `+`, `=`, `?!` when they make the meaning faster to understand.
- Prefer `수익화` when the source is about making money, but pair it with a concrete object such as `엑셀`, `파일`, `AI`, or `앱`.
- Do not overpromise beyond the source. If a result is not confirmed in Step 1, do not use it.
- Avoid vague clickbait such as `이거 모르면 손해`, `충격적인 진실`, `대박입니다` unless the actual video supports the claim.
- Avoid difficult or overly technical words in head copy even if they appear in the script.
- If using a number, use only a number recorded in Step 1.
- Avoid generic noun phrases that feel like a blog title: `팔리는 앱으로 바꾸는 법`, `미니 웹앱 구축 로드맵`, `AI 자동화 시스템 설계법`.

Good head copy patterns:

```markdown
엑셀이 돈이 된다고? / 1시간 AI로 수익화 하는법
이거 그냥 두면 손해 / 엑셀 + AI = 수익화
45분이면 충분합니다 / AI 엑셀 수익화 전략
내 파일도 팔릴 수 있다? / AI로 상품 만드는법
```

Bad head copy patterns:

```markdown
AI 아티팩트 MVP 구축 프로세스
초고도 자동화 수익화 시스템
이거 모르면 인생 망합니다
```

#### Length and Compression

- Default to exactly 3 body points: `첫째`, `둘째`, `셋째`.
- Each point should usually be 2-3 sentences.
- Total script target: about 650-950 Korean characters, roughly the length of the user's example.
- If the original video has more than 3 tips, choose the 3 most sellable, concrete, and causally connected tips. It is acceptable to merge related tips.
- Avoid exhaustive summaries. Shorts scripts should feel like a sharp sales/narration script, not a full lecture recap.
- Prefer concrete outcomes, numbers, and transformation language over long explanations.

#### Hook Copywriting

The opening must be strongly hook-driven. It should create curiosity, contrast, or a money/result angle in the first sentence.

Use this pattern as the default:

```markdown
여기, 이 [여자/남자/사람]는 [후킹성 정체성/수식어]입니다. [평범한 것]을 [짧은 시간/낮은 비용/뜻밖의 방식]으로 [돈 되는 결과]로 바꾼 [이름]. [이름]. 그[녀/가/사람이] 공개한 [강한 핵심 키워드]로 [결과]하는 3가지 필승 공식, 저장하고 끝까지 보세요!
```

Good hook qualities:

- Use a strong identity phrase: `비즈니스 천재`, `AI 수익화 고수`, `무자본 상품화 전문가`, `자동화 괴물` only when supported by the source.
- Use transformation copy: `잠자는 엑셀을 현금 인출기로 만드는`, `지루한 파일을 판매 상품으로 바꾸는`, `평범한 자료를 수익화 자산으로 바꾸는`.
- Lead with the most clickable confirmed number when available.
- Keep it punchy. Do not spend more than 3-4 sentences before `첫째`.

#### Script Rules

- No timestamps such as `(00:00)` or `(00:15)`.
- No section labels such as `[훅]`, `[본문]`, `[결론/CTA]`.
- No writing notes such as `권위 강조` or `임팩트 있게`.
- No English glosses after names, such as `사리아(Sariah)`.
- Do not use Markdown bold in the script body.
- The user prefers compact paragraph-style output. Do not force every sentence onto a separate line unless the user explicitly asks for line-by-line formatting.
- Use the confirmed gender wording only: 여성 speaker uses `이 여자는` and `그녀`; 남성 speaker uses `이 남자는` and `그가`.
- If gender is `확인불가`, avoid gendered wording; use `이 사람은` and `이 사람이`.
- If a name is `언급없음`, omit the standalone name line.
- Use only strategies, tips, numbers, and claims from Step 1.
- Do not add unsupported outcomes, credentials, numbers, or anecdotes.
- Natural Korean copywriting is allowed, but the factual substance must remain grounded in Step 1.

#### Body Pattern

Use this compressed pattern:

```markdown
첫째, [전략 제목]. [핵심 실행법]. [확인된 수치/결과/의미].
둘째, [전략 제목]. [핵심 실행법]. [확인된 수치/결과/의미].
셋째, [전략 제목]. [핵심 실행법]. [확인된 수치/결과/의미].
```

#### CTA Pattern

End with a quote or faithful core message, then CTA:

```markdown
"[화자가 말한 핵심 명언 또는 영상 핵심 메시지]" . 이런 [콘텐츠 카테고리] 이야기 도움됐다면 댓글에 [짧은 키워드] 남겨주세요. 무료 [관련 혜택]을 보내드립니다. 이 채널을 구독하고 [채널 가치 한 줄 요약]하세요!
```

Use one short comment keyword, such as `앱`, `AI`, `자동화`, `엑셀`, `수익화`.

### Step 5: Final Validation

Before finalizing, internally check:

- Speaker gender matches Step 1.
- Name matches Step 1, or is omitted when `언급없음`.
- The final script uses exactly 3 body points by default.
- Any merged point is supported by Step 1.
- No unsupported content was added.
- No timestamps are present.
- No script section labels are present.
- No meta comments are present.
- No English name glosses are present.
- The opening has clear hook copywriting with curiosity, contrast, or a money/result angle.
- The head copy uses universal language and connects directly to the opening script.
- The head copy does not promise anything unsupported by Step 1.
- The script is close to the user's example length and not a full-length recap.

If any check fails, rewrite the script before answering.

## Final Output

Always answer in this order:

```markdown
### 영상 분석 결과
[Step 1 content]

### 선택한 포맷
포맷 [A/B/C/D]

### 헤드카피라이팅
[3 short first-screen copy candidates]

### 스크립트
[Concise 3-point Shorts/Reels script with no internal labels]
```
