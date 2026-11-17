"""Deterministic offline formatting (marker insertion and manuscript integrity check)."""

import re

def pick_keywords(*args, **kwargs):
    raise ValueError("AI keyword calls are disabled in the portable formatter")

_MARKER_RE = re.compile(r'\[(?:/?BOLD|/?HIGHLIGHT|/?BLOCKQUOTE|IMAGE_HERE)\]')

def _canon(text):
    """마커·마크다운 기호·공백을 걷어낸 '순수 글자'만 남긴다 (비교용)."""
    text = _MARKER_RE.sub('', text)
    text = re.sub(r'^\s{0,3}#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = text.replace('**', '')
    return re.sub(r'\s+', '', text)

def verify_manuscript_intact(original, assembled):
    """마커를 제거한 결과가 원문과 동일한지 확인한다."""
    a, b = _canon(original), _canon(assembled)
    if a == b:
        return True, ''
    # 어디서 갈렸는지 알려준다
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            return False, f"{i}번째 글자부터 불일치\n  원문: ...{a[max(0,i-20):i+20]}...\n  결과: ...{b[max(0,i-20):i+20]}..."
    return False, f"길이 불일치 (원문 {len(a)}자 / 결과 {len(b)}자)"

_MD_HEADING = re.compile(r'^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$')

_BOLD_ONLY = re.compile(r'^\s*\*\*(.{2,40}?)\*\*\s*[:：]?\s*$')

_NUM_HEADING = re.compile(r'^\s*(\d{1,2})\s*[.)]\s*(.{2,40})$')

def _as_heading(block):
    """블록이 소제목이면 소제목 텍스트를, 아니면 None을 반환한다."""
    if '\n' in block:
        return None

    m = _MD_HEADING.match(block)
    if m:
        return m.group(1).replace('**', '').strip()

    m = _BOLD_ONLY.match(block)
    if m:
        return m.group(1).strip()

    m = _NUM_HEADING.match(block)
    if m and not re.search(r'[.!?…]$', block):
        return f"{m.group(1)}. {m.group(2).replace('**', '').strip()}"

    return None

def _as_heading_loose(block):
    """패턴형 소제목이 하나도 없을 때만 쓰는 완화 규칙 (짧은 독립 줄)."""
    if '\n' in block:
        return None
    t = block.strip()
    if not (2 <= len(t) <= 30):
        return None
    if re.search(r'[.!?…,]$', t):
        return None
    if t[0] in '-•·▪※"‘“(':
        return None
    return t.replace('**', '').strip()

def _isolate_heading_lines(text):
    """소제목 줄을 독립 블록으로 떼어낸다.

    노트북LM이 '## 소제목' 바로 다음 줄에 빈 줄 없이 본문을 붙여 쓸 때가 있다.
    그러면 소제목+본문이 한 덩어리가 되어 소제목으로 인식되지 않는다.
    빈 줄만 넣는 것이므로 글자는 하나도 안 바뀐다.
    """
    text = re.sub(r'(?m)^([ \t]{0,3}#{1,6}[ \t]+\S.*?)[ \t]*$', r'\n\1\n', text)
    text = re.sub(r'(?m)^[ \t]*(\*\*[^*\n]{2,40}\*\*)[ \t]*[:：]?[ \t]*$', r'\n\1\n', text)
    return text

def split_blocks(manuscript):
    """원고를 빈 줄 기준으로 나누고 각 블록을 heading/body로 분류한다."""
    manuscript = _isolate_heading_lines(manuscript)
    raw = [b.strip() for b in re.split(r'\n\s*\n', manuscript.strip()) if b.strip()]

    # The versioned column has one article title, then an introduction and ##
    # section headings. Keep the title's words in the body for exact lineage,
    # but do not turn it (or numbered instructions) into an extra quotation.
    column = bool(raw and re.fullmatch(r'# [^\n]+', raw[0])
                  and re.search(r'(?m)^## ', manuscript))
    blocks = []
    for i, block in enumerate(raw):
        if column:
            heading = re.fullmatch(r'## (.+)', block)
            blocks.append({'kind': 'heading' if heading else 'body',
                           'text': heading.group(1) if heading else
                           (block[2:] if i == 0 else block)})
        else:
            blocks.append({'kind': 'heading' if _as_heading(block) else 'body',
                           'text': _as_heading(block) or block})

    # 패턴형 소제목이 전혀 없으면 완화 규칙으로 한 번 더 시도
    if not any(b['kind'] == 'heading' for b in blocks):
        blocks = []
        for b in raw:
            h = _as_heading_loose(b)
            blocks.append({'kind': 'heading', 'text': h} if h
                          else {'kind': 'body', 'text': b})

    return blocks

def section_image_slots(blocks):
    """소제목 섹션마다 1장. 각 섹션의 마지막 본문 문단 뒤에 넣는다.

    (큰 의미 단위로 문단을 나누고 그 사이사이에 이미지)
    """
    if not blocks:
        return set()

    head_idx = [i for i, b in enumerate(blocks) if b['kind'] == 'heading']
    if not head_idx:
        return set()

    slots = set()
    for n, start in enumerate(head_idx):
        end = head_idx[n + 1] if n + 1 < len(head_idx) else len(blocks)
        # 이 섹션의 마지막 본문 블록
        last_body = None
        for j in range(start + 1, end):
            if blocks[j]['kind'] == 'body':
                last_body = j
        if last_body is not None:
            slots.add(last_body)
    return slots

def count_sections(manuscript):
    """원고의 소제목 개수. 칼럼 제목·도입은 소제목에 포함하지 않는다."""
    return sum(1 for b in split_blocks(manuscript) if b['kind'] == 'heading')

def column_image_slots(blocks, image_count):
    """Distribute the existing images without adding or repeating source assets."""
    ends = sorted(section_image_slots(blocks))
    if image_count <= 0:
        return set()
    if len(ends) >= image_count:
        return {ends[min(len(ends) - 1, int(len(ends) * (i + .5) / image_count))]
                for i in range(image_count)}
    first_heading = next((i for i, b in enumerate(blocks) if b['kind'] == 'heading'), len(blocks))
    extras = [i for i, b in enumerate(blocks)
              if i > first_heading and b['kind'] == 'body' and i not in ends]
    needed = image_count - len(ends)
    if len(extras) < needed:
        raise ValueError('Column has too few body paragraphs for the approved images')
    return set(ends + [extras[int(len(extras) * (i + .5) / needed)] for i in range(needed)])

def choose_image_slots(blocks, image_count):
    """[IMAGE_HERE]를 꽂을 블록 인덱스를 균등하게 고른다.

    - 맨 앞(첫 섹션 이전)에는 넣지 않는다
    - 마지막 블록 뒤에는 넣지 않는다 (CTA가 붙을 자리)
    - 소제목 바로 뒤에는 넣지 않는다 (소제목-이미지-본문은 어색)
    """
    if image_count <= 0:
        return set()

    slots = [i for i, b in enumerate(blocks)
             if b['kind'] == 'body' and i >= 1 and i < len(blocks) - 1]

    if not slots:
        return set()

    if len(slots) <= image_count:
        if len(slots) < image_count:
            print(f"  -> [주의] 문단이 부족해 이미지를 {len(slots)}장만 배치합니다 "
                  f"(요청 {image_count}장). 나머지는 사용하지 않습니다.")
        return set(slots)

    step = len(slots) / float(image_count)
    return {slots[min(len(slots) - 1, int(step * (i + 0.5)))] for i in range(image_count)}

def _marker_spans(text):
    """이미 마커로 감싸인 구간의 (start, end) 목록."""
    return [(m.start(), m.end()) for m in
            re.finditer(r'\[(?:BOLD|HIGHLIGHT)\].*?\[/(?:BOLD|HIGHLIGHT)\]', text, re.DOTALL)]

def _wrap_first(text, keyword, tag):
    """마커 밖에 있는 첫 등장 1회만 감싼다. 못 찾으면 원문 그대로 반환."""
    spans = _marker_spans(text)
    for m in re.finditer(re.escape(keyword), text):
        if any(s <= m.start() and m.end() <= e for s, e in spans):
            continue
        return (text[:m.start()] + f"[{tag}]{keyword}[/{tag}]" + text[m.end():]), True
    return text, False

def convert_markdown_bold(text, enabled=True):
    """원고의 **강조** 처리. 어느 쪽이든 ** 기호 자체는 반드시 없앤다.

    enabled=True  → [BOLD]로 변환
    enabled=False → 기호만 제거하고 평문으로 (볼드를 꺼도 ** 가 본문에 찍히면 안 된다)
    """
    if enabled:
        return re.sub(r'\*\*(.+?)\*\*', r'[BOLD]\1[/BOLD]', text, flags=re.DOTALL)
    return re.sub(r'\*\*(.+?)\*\*', r'\1', text, flags=re.DOTALL)

def build_body(manuscript, image_count, optional_config, use_ai_keywords=True):
    """원고 → 마커가 박힌 본문 문자열."""
    print("[본문 조립] 원고를 블록으로 분해하는 중...")

    blocks = split_blocks(manuscript)
    n_head = sum(1 for b in blocks if b['kind'] == 'heading')
    print(f"  -> 블록 {len(blocks)}개 (소제목 {n_head}개 / 본문 {len(blocks) - n_head}개)")

    # 소제목 섹션마다 1장이 기본. 섹션이 없으면 문단 균등 배치로 폴백.
    slots = section_image_slots(blocks)
    if optional_config.get('column_layout'):
        slots = column_image_slots(blocks, image_count)
    elif slots:
        slots = set(sorted(slots)[:image_count]) if image_count else set()
        print(f"  -> 이미지 위치(섹션 끝마다): {sorted(slots)} (총 {len(slots)}장)")
    else:
        slots = choose_image_slots(blocks, image_count)
        print(f"  -> 이미지 위치(문단 균등): {sorted(slots)} (총 {len(slots)}장)")

    bold_kws, hl_kws = [], []
    if use_ai_keywords and (optional_config.get('bold_enabled') or
                            optional_config.get('highlight_enabled')):
        print("  -> 볼드/음영 키워드 선별 중 (Gemini)...")
        bold_kws, hl_kws = pick_keywords(manuscript)
        if not optional_config.get('bold_enabled'):
            bold_kws = []
        if not optional_config.get('highlight_enabled'):
            hl_kws = []

    used = set()
    parts = []
    for i, blk in enumerate(blocks):
        if blk['kind'] == 'heading':
            parts.append(f"[BLOCKQUOTE]{blk['text']}[/BLOCKQUOTE]")
        else:
            t = convert_markdown_bold(
                blk['text'], enabled=bool(optional_config.get('bold_enabled')))
            for kw in bold_kws:
                if kw not in used:
                    t, hit = _wrap_first(t, kw, 'BOLD')
                    if hit:
                        used.add(kw)
            for kw in hl_kws:
                if kw not in used:
                    t, hit = _wrap_first(t, kw, 'HIGHLIGHT')
                    if hit:
                        used.add(kw)
            parts.append(t)

        if i in slots:
            parts.append('[IMAGE_HERE]')

    body = '\n\n'.join(parts)

    ok, detail = verify_manuscript_intact(manuscript, body)
    if ok:
        print("  -> [검증] 원문 무손실 확인 OK")
        return body

    print(f"  -> [경고] 원문이 변형되었습니다. 마커 없는 안전 버전으로 되돌립니다.\n{detail}")
    return build_body_safe(manuscript, image_count)

def build_body_safe(manuscript, image_count):
    """폴백: 소제목/키워드 없이 원고 + 이미지 자리만."""
    blocks = [{'kind': 'body', 'text': b.strip()}
              for b in re.split(r'\n\s*\n', manuscript.strip()) if b.strip()]
    slots = choose_image_slots(blocks, image_count)
    parts = []
    for i, blk in enumerate(blocks):
        parts.append(blk['text'])
        if i in slots:
            parts.append('[IMAGE_HERE]')
    return '\n\n'.join(parts)
