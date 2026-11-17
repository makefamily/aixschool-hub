# -*- coding: utf-8 -*-
"""스타일 v2 예시 원고 — 11/14 RSA 특강 샘플 17장(2026-11-12). 새 덱은 이 파일을 고쳐 쓴다.
media/ 에 이미지가 없으면 그 장은 빈 칸이 된다. 자료가 아직 없으면 img 대신 need=("필요한 자료", "누구", "어떤 모양으로")를 넣는다.
V2_MULTI=1 환경변수는 비교 샘플용(강조 여러 곳). 실제 덱에서는 t() 없이 문구를 바로 쓴다.
"""
import os
MULTI = os.environ.get("V2_MULTI") == "1"
META = {"title": "AI 도구, 이제 내가 만들어 써요", "foot": "강사 이름 · 소속"}
P0, P1, P3, P5 = "오프닝", "왜 지금인가", "같이 만들기", "2주 과정 안내"
M = lambda n: f"media/{n}"
TALK = [("chat", "만들어 줘", "복사한 문장 붙여 넣기"), ("edit", "고쳐 줘", "대출 없음 버튼 넣기"), ("home", "우리 사무실로", "이름 넣기")]
def t(plain, multi):
    return multi if MULTI else plain

D = []
def add(**k): D.append(k)

# ── 1-A 작은 캡처 : 원본 글씨가 화면에서 70% 미만이면 '전체 + 빨간 박스' 장 → 다음 장 '박스 부분 확대' ──
# 좌표는 이미지 대비 비율 (x, y, w, h). 박스가 2개 이상이면 번호가 붙는다. 레티나(2배) 캡처는 실제 CSS 크기로 환산해서 잰다
def ZOOM(img, region, name):
    """원본 캡처에서 region 만 잘라 media/zoom/<name>-<영역>.png 로 저장하고 경로를 돌려준다(영역이 바뀌면 새 파일)"""
    from PIL import Image
    base = os.path.dirname(os.path.abspath(__file__))
    name = name + "-" + "-".join(f"{v:.3f}"[2:] for v in region)
    out = os.path.join(base, "media", "zoom", name + ".png")
    src = os.path.join(base, img)
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with Image.open(src) as im:
            W, H = im.size; x, y, w, h = region
            im.crop((round(x * W), round(y * H), round((x + w) * W), round((y + h) * H))).save(out)
    return M("zoom/" + name + ".png")

def BOXED(box, region, name, zoom_title=None, zoom_eyebrow="크게 보면", zoom_sub=None, **k):
    """add(box=...) 한 장 + 확대 장(proof, zoomed=True) 한 장을 함께 넣는다. k 는 원래 장 값(k="proof"/"qa"/"split" 등, img 필수)"""
    add(box=box, **k)
    z = dict(k="proof", part=k.get("part", ""), eyebrow=zoom_eyebrow, title=zoom_title or k["title"], img=ZOOM(k["img"], region, name), zoomed=True)
    if zoom_sub: z["sub"] = zoom_sub
    add(**z)
add(k="cover", part=P0, eyebrow="AI 특강 · 날짜", title="AI 도구,|이제 내가|<em>만들어 써요</em>", img=M("profile.jpg"))
add(k="proof", part=P0, eyebrow="오늘 만들 것", title=t("2시간 뒤면 여러분 화면에도 <em>이 계산기</em>가 있어요", "<em>2시간</em> 뒤면 여러분 화면에도 <em>이 계산기</em>가 있어요"), img=M("gem-final.png"))
add(k="gal", part=P0, lay="side", side="r", w=620, eyebrow="오늘 함께할 사람", title=t("소속과 직함|<em>강사 이름</em>이에요", "<em>소속</em>과 직함|<em>강사 이름</em>이에요"),
    rows=[[M("profile.jpg")]],
    items=[("AI 교육 운영", "비개발자 대표님들이 배우는 중"), ("우리 회사 도구", "직접 만들어 써요")])
add(k="hero", part=P0, bg="k", eyebrow="오늘 끝까지 들어 주시면", title=t("<em>선물 2개</em>를|드려요", "<em>선물</em> <em>2개</em>를|드려요"),
    sub="하나는 오늘 계산기 요청 문장 전체, 하나는 마지막에 공개해요")
add(k="poll", part=P0, eyebrow="채팅창에 숫자로 답해 주세요", title="AI로 뭔가 만들어 본 적 있으세요?", options=["있어요", "아직이요"])
add(k="chap", part=P1, n=1, title=t("왜 <mark>지금</mark>인가", "왜 <mark>지금</mark>인가"))
add(k="qa", part=P1, n=1, ask="수익률 계산, 시세 정리|매번 처음부터 하시죠?", title=t("이제 AI한테|<em>만들어 달라고</em> 하면 돼요", "이제 <em>AI</em>한테|<em>만들어 달라고</em> 하면 돼요"))
add(k="vs", part=P1, eyebrow="지금까지 쓰던 AI, 오늘 쓸 AI", title=t("물어보던 AI가|<em>만들어 주는 AI</em>로", "<em>물어보던 AI</em>가|<em>만들어 주는 AI</em>로"),
    left=("물어보는 AI", "답을 읽고 내가 다시 정리"), right=("만들어 주는 AI", "계산기가 바로 화면에"))
add(k="steps4", part=P3, eyebrow="같이 만들기", title=t("AI한테 <em>3번</em> 말하면 끝나요", "AI한테 <em>3번</em> 말하면 <em>끝나요</em>"), steps=TALK)
add(k="steps4", part=P3, eyebrow="지금 여기", title="1번째 말: <em>만들어 줘</em>", steps=TALK, active=0)
add(k="countdown", part=P3, eyebrow="지금 해 보세요", title=t("복사한 문장을|<em>붙여 넣어</em> 보세요", "<em>복사한 문장</em>을|<em>붙여 넣어</em> 보세요"), sec=180)
add(k="stats", part=P3, bg="k", eyebrow="숫자를 넣어 보세요", title=t("<em>맞게</em> 나오나요?", "<em>맞게</em> 나오나요?"),
    items=[("home", "매매가", 1.34, "억원", "넣은 값"), ("won", "월세", 100, "만원", "넣은 값"), ("calc", "수익률", 8.96, "%", "이렇게 나오면 맞아요")])
add(k="reasons", part="혼자 하면 어디서 멈추나", eyebrow="집에 가서 혼자 하면", title=t("여기서 <em>멈춰요</em>", "여기서 <em>멈춰요</em>"), icon="alert",
    items=[("내 컴퓨터에 설치", "인터넷 창 밖으로 나가는 순간 막혀요"), ("내 자료 넣기", "매물 목록·엑셀을 붙이는 법"), ("물어볼 곳", "막힌 화면을 보여 줄 사람이 없어요")])
add(k="flow", part=P5, eyebrow="2주 이렇게 가요", title=t("<em>같이 2번</em>, 사이엔 질문방", "<em>같이 2번</em>, 사이엔 <em>질문방</em>"),
    steps=[("내가", "doc", "사전 과제", "주제 하나 고르기"), ("저희", "laptop", "1회 · 설치", "내 노트북에 직접 깔고 첫 화면"),
           ("저희", "chat", "질문방", "막힌 화면 캡처로 물어보기"), ("저희", "edit", "2회 · 완성", "내 자료 넣어 실제로 써 보기"), ("내가", "home", "사무실에서", "다음 상담부터 쓰기")])
add(k="benefit", part=P5, n=1, icon="users", title=t("옆에서 봐 드리는|<em>오프라인 2번</em>", "<em>옆에서</em> 봐 드리는|<em>오프라인 2번</em>"), sub="서울대입구 RSA 사무실")
add(k="checklist", part=P5, eyebrow="솔직하게 말씀드릴게요", title=t("이런 분께는|<em>안 맞아요</em>", "이런 분께는|<em>안 맞아요</em>"),
    items=["대신 만들어 주길 원하시는 분", "2주 동안 한 번도 직접 해 볼 시간이 없는 분"])
add(k="closing", part="마무리", title=t("오늘 만든 계산기,|다음 상담에서|<em>바로 써 보세요</em>", "<em>오늘 만든 계산기</em>,|다음 상담에서|<em>바로 써 보세요</em>"))
