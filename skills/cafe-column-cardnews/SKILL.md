---
name: cafe-column-cardnews
description: Convert Korean Naver Cafe column drafts into 10-card cardnews scripts and image-generation plans for Instagram, Reels covers, or carousel posts. Use when the user provides a Cafe-style educational column, long-form Korean article, YouTube Cafe column draft, curriculum/checklist article, or AI monetization/automation column and wants concise card-by-card copy, a hook, practical body cards, CTA, design notes, image prompts, or generated card visual assets.
---

# Cafe Column Cardnews

## Overview

Turn a Korean Naver Cafe column into a 10-card educational cardnews draft and matching image-generation plan. Preserve the column's information quality while rewriting it into short, visual, save-worthy cards.

Prefer this source order:

1. Naver Cafe column body
2. Column title and recommended title
3. Curriculum/checklist section
4. CTA section
5. Image capture list or image placeholders
6. Reels/Shorts script only when no column exists

## Workflow

1. Identify the column's core promise, target reader, problem, method, examples, cautions, and CTA.
2. Extract only claims supported by the column. Do not invent tool names, numbers, prices, earnings, credentials, or outcomes.
3. Build exactly 10 cards by default:
   - Card 1: strong hook based on the column's core promise.
   - Card 2: reader problem or market/context shift.
   - Card 3: core insight or positioning shift.
   - Cards 4-8: practical steps, framework, checklist, or comparison points from the body.
   - Card 9: summary, application example, or expected change.
   - Card 10: CTA based on the column's CTA.
4. Rewrite each card as one clear message, not a paragraph summary.
5. Add design notes and image suggestions using the column's image placeholders or capture list when available.
6. If the user asks for image generation, create one image prompt per card or one reusable visual style prompt plus card-specific scene prompts.
7. Finish with a short quality check.

## Output Format

Use this structure when the user asks for a plan or draft:

```markdown
# 카드뉴스 기획안

## 1장. [짧은 카드 제목]
- 메인 카피:
- 보조 문구:
- 디자인 메모:
- 이미지 제안:

...

## 10장. CTA
- 메인 카피:
- 보조 문구:
- 디자인 메모:
- 이미지 제안:

# 품질 체크
- 원문 기반 수치/도구만 사용:
- 1장 후킹 여부:
- 10장 CTA 여부:
- 과장된 수익 보장 제거:
```

Use this expanded structure when the user asks for image generation or final production:

```markdown
# 카드뉴스 제작안

## 공통 비주얼 스타일
- 스타일:
- 색감:
- 인물/오브젝트:
- 금지 요소:
- 텍스트 처리 원칙:

## 1장. [짧은 카드 제목]
- 메인 카피:
- 보조 문구:
- 디자인 메모:
- 이미지 생성 프롬프트:
- 최종 카드 편집 메모:

...

## 10장. CTA
- 메인 카피:
- 보조 문구:
- 디자인 메모:
- 이미지 생성 프롬프트:
- 최종 카드 편집 메모:
```

## Writing Rules

- Write in Korean unless the user asks otherwise.
- Keep each card concise enough for a square carousel card.
- Make the first card hooky but believable. Use contrast, curiosity, or a concrete result from the column.
- Use short line breaks in `메인 카피` when it helps visual rhythm.
- Keep `보조 문구` to 1-3 short sentences.
- Prefer practical, educational, Naver Cafe-friendly copy over shallow clickbait.
- Preserve nuance around money claims. Use "가능성", "설계 가능", "가격 포지션" when the column avoids guarantees.
- If the column includes a table, convert it into one comparison card or split it into multiple cards only when necessary.
- If the column includes steps, keep their order unless a stronger cardnews flow requires moving context before steps.
- If the column includes image placeholders, map them to the closest card. If no image is available, suggest a simple visual direction.
- CTA should reuse the user's CTA direction, keyword, link, or offer. Do not create a new offer unless the user asks.

## Image Generation Rules

- Use AI image generation for backgrounds, conceptual visuals, product scenes, workflow scenes, device mockups, or section illustrations.
- Do not rely on generated images to render Korean card text accurately. Generate clean visuals with no embedded text, then place `메인 카피` and `보조 문구` separately in the card design.
- Keep visual prompts text-free unless the user explicitly asks for visible text inside the image.
- Prefer square card visuals for Instagram carousel use.
- Keep a consistent style across all 10 cards: same palette, lighting, medium, composition logic, and level of realism.
- For AI monetization and automation topics, prefer modern workspace, dashboard, spreadsheet, web app, laptop, phone, sticky-note, workflow, and clean interface metaphors.
- Avoid fake logos, brand marks, watermarks, unreadable UI text, exaggerated money imagery, or unsupported income proof.
- When source image capture notes exist, use them as visual references for scene selection, but still generate polished card-friendly visuals unless the user asks to use screenshots directly.
- For final production, generate or request image assets first, then compose final cards with readable typography in a deterministic design tool or layout step.

## Image Prompt Pattern

Use this prompt pattern for each card:

```text
Square Instagram carousel background image, no text, no letters, no logos, no watermark.
Topic: [card topic].
Scene: [specific visual scene from the column].
Style: [consistent style across the deck].
Composition: leave clean negative space for Korean headline overlay, subject placed [left/right/center] as appropriate.
Mood: practical, polished, educational, modern.
Colors: [consistent palette].
Avoid: visible text, fake UI labels, brand logos, exaggerated cash, clutter.
```

If the user wants complete images, generate the visual assets with the image generation tool and then provide the final card copy and layout notes. If the user wants editable cards, prepare image prompts plus layout instructions rather than flattening all text into generated images.

## Default Tone

- Practical and conversational.
- Information-dense but easy to scan.
- Slightly persuasive, not hype-heavy.
- Suitable for AI automation, AI monetization, productivity, side-hustle, creator education, and digital product topics.

## Compression Guide

When the column is long, prioritize:

1. The main transformation promised by the article.
2. The market or reader pain point.
3. The framework or steps readers can follow.
4. Concrete examples, numbers, and tool roles.
5. Cautions that prevent overpromising.
6. CTA.

Omit repeated explanation, intro padding, and source-video attribution unless it strengthens credibility.

## Quality Check

Before finalizing, verify:

- The draft has exactly 10 cards unless the user requested a different count.
- Card 1 is a hook, not a generic title.
- Card 10 is a CTA.
- Each body card has one primary message.
- All numbers, prices, tools, and claims come from the column.
- The copy does not guarantee income or results beyond the source.
- Design notes are actionable and do not describe features as visible instructional text.
- Image prompts ask for text-free visuals unless visible text is explicitly required.
- The visual direction stays consistent across the 10-card set.
