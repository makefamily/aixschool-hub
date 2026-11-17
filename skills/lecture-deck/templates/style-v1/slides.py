# -*- coding: utf-8 -*-
"""5차시 덱 v2 슬라이드 정본 — 번호는 src/slide-plan-v2.md 와 1:1 (프롬프터 공용, 바꾸지 말 것)

문구 원칙
- 문구는 src/slides.json(v1) 그대로. <br> → '|' 줄바꿈, <span class='acc'> → <em> 만 바꾼다
- v1에 문구가 없는 결과 먼저 장(2·3)과 세션 재현 장(12)은 v1 kicker를 eyebrow로만 쓴다
- 강조색은 장당 한 곳. <em> 이 없으면 빌더가 eyebrow를 강조색으로 올린다

레이아웃: cover vside cards statement quote compare flow chapter demo shot stat cardsteps grid cycle closing
        + zoom(확대 장) screen(따라하기 화면 꽉 차게) market(시중 서비스 한 장) cal(달력) — 2026-11-13. shot 에 box=[(x,y,w,h)] 를 주면 빨간 박스
steps: 스텝마다 밝힐 .focusable 인덱스. prog=True 면 0번 스텝에서 전부 흐리게 시작한다
"""

META = {"title": "강의 하나를 만들고, 그 강의를 알리기까지"}

P0 = "오프닝"
P1 = "1부 · 제가 만든 순서 그대로"
PB = "휴식"
P2 = "2부 · 만들었으면 알려야 합니다"
P3 = "3부 · 오늘 본 걸 가져가는 법"

def prog(n):
    """목록 n개를 하나씩 쌓아 밝힌다: [[], [0], [0,1], ...]"""
    return [list(range(k)) for k in range(n + 1)]

# ── 1-A 작은 캡처 : 원본 글씨가 화면에서 70% 미만이면 '전체 + 빨간 박스' 장 → 다음 장 '박스 부분 확대' ──
# 좌표는 이미지 대비 비율 (x, y, w, h). 레티나(2배) 캡처는 실제 CSS 크기로 환산해서 잰다. D 안에서 *BOXED(...) 로 두 장을 펼쳐 넣는다
import os as _os
def ZOOM(img, region, name):
    """원본에서 region 만 잘라 media/zoom/<name>-<영역>.png 로 저장(영역이 바뀌면 새 파일)"""
    from PIL import Image
    base = _os.path.dirname(_os.path.abspath(__file__))
    name = name + "-" + "-".join(f"{v:.3f}"[2:] for v in region)
    out = _os.path.join(base, "media", "zoom", name + ".png")
    src = _os.path.join(base, img)
    if _os.path.exists(src) and (not _os.path.exists(out) or _os.path.getmtime(out) < _os.path.getmtime(src)):
        _os.makedirs(_os.path.dirname(out), exist_ok=True)
        with Image.open(src) as im:
            W, H = im.size; x, y, w, h = region
            im.crop((round(x * W), round(y * H), round((x + w) * W), round((y + h) * H))).save(out)
    return "media/zoom/" + name + ".png"

def BOXED(box, region, name, zoom_title=None, zoom_eyebrow="크게 보면", zoom_sub=None, **k):
    """[shot 장(box 포함), zoom 장] 두 개를 돌려준다. k 는 원래 shot 장 값(img 필수)"""
    z = dict(k="zoom", t=k.get("t", "") + "-확대", part=k.get("part", ""), eyebrow=zoom_eyebrow,
             title=zoom_title or k.get("title", ""), img=ZOOM(k["img"], region, name))
    if zoom_sub: z["sub"] = zoom_sub
    return [dict(box=box, **k), z]

CARDS = [f"../assets/cardnews/card-{i:02d}.png" for i in range(1, 9)]
VIDEO = "../assets/shortform/shortform.mp4"

D = [
# ═════════ 오프닝 ═════════
dict(k="cover", t="표지", part=P0,                                                     # 1  v1#1
     eyebrow="클래스101 강사 과정 · 5차시",
     title="강의 하나를 만들고,|그 강의를 알리기까지",
     sub="제가 강의를 준비하는 과정을<br><em>처음부터 끝까지</em> 그대로 보여드립니다"),

dict(k="vside", t="결과-숏폼", part=P0, src=VIDEO,                                     # 2
     eyebrow="먼저 결과부터"),

dict(k="cards", t="결과-카드뉴스", part=P0, imgs=CARDS,                                # 3
     eyebrow="먼저 결과부터"),

dict(k="statement", t="지금보시는", part=P0,                                           # 4  v1#2
     eyebrow="먼저 결과부터",
     title="지금 보시는 이 장표,|제 대본, 나눠드릴 페이지",
     sub="그리고 이 강의를 알리는 카드뉴스와 숏폼까지<br><em>오늘 보여드릴 과정</em>으로 만들었습니다"),

dict(k="quote", t="대화한줄", part=P0,                                                 # 5  v1#3
     title="이 준비는|<em>AI와의 대화 한 줄</em>에서 시작했습니다",
     quote="\"내가 강의하기로 한 내용 먼저 찾아볼래?\"",
     tail="— 실제 첫 질문입니다."),

dict(k="compare", t="한번에vs단계", part=P0, hl=1,                                     # 6  v1#4
     eyebrow="같은 AI, 다른 결과",
     title="\"강의 만들어줘\" 한 번이면|남의 강의가 나옵니다",
     cols=[("한 번에 시키기", "그럴듯하지만 누구의 강의도 아닌 결과"),
           ("단계로 나눠 대화하기", "중간마다 내가 고치니까 내 강의가 됩니다")],
     steps=prog(2), prog=True),

dict(k="flow", t="오늘의지도", part=P0,                                                # 7  v1#5
     eyebrow="오늘의 지도",
     title="세 부분입니다",
     nodes=[("1부", "제가 이 강의를 만든 과정 6단계"),
            ("2부", "만든 강의를 알리는 콘텐츠, 소스 하나로"),
            ("3부", "오늘 본 걸 가져가는 두 가지 길")],
     sep=" · ", steps=prog(3), prog=True),

dict(k="statement", t="보기만", part=P0,                                               # 8  v1#6
     title="오늘은 따라 하지 않으셔도 됩니다|<em>보기만 하세요</em>",
     sub="가져가는 방법은 마지막에 정확히 드립니다."),

# ═════════ 1부 ═════════
dict(k="chapter", t="1부", part=P1, eyebrow="1부", title="제가 만든 순서 그대로"),     # 9  v1#7

dict(k="demo", t="표지판-자료조사", part=P1,                                           # 10 v1#8
     eyebrow="지금부터 볼 것 ①", title="자료조사를|대화로 합니다",
     sub="검색 대신 질문을 던집니다. 제가 어떻게 묻는지를 보세요."),

dict(k="flow", t="넓게좁혀확인", part=P1,                                              # 11 v1#9
     eyebrow="자료조사",
     title="주제 · 대상 · 지금 궁금한 것",
     nodes=[("넓게 묻고", "이 주제로 강의하려면 뭘 알아야 해?"),
            ("좁혀 묻고", "왕초보 강사님들이 제일 막히는 곳은?"),
            ("확인합니다", "그 말의 근거가 어디에 있어?")],
     steps=prog(3), prog=True),

dict(k="shot", t="첫질문재현", part=P1, wide=True, img="media/q1-transcript.png",      # 12
     eyebrow="자료조사"),

dict(k="statement", t="방금-질문", part=P1,                                            # 13 v1#10
     eyebrow="방금 본 것",
     title="답을 받은 게 아니라|<em>질문을 좁혀 갔습니다</em>"),

dict(k="demo", t="표지판-내데이터", part=P1,                                           # 14 v1#11
     eyebrow="지금부터 볼 것 ②", title="내 데이터를 넣습니다",
     sub="여기서부터 남의 강의가 아니라 제 강의가 됩니다."),

dict(k="compare", t="남의자료vs내자료", part=P1, hl=1,                                 # 15 v1#12
     eyebrow="같은 AI, 다른 재료",
     title="남의 자료로 만든 강의와|내 자료로 만든 강의",
     cols=[("인터넷에 있는 자료", "누가 물어도 비슷한 답"),
           ("내가 했던 강의·녹음·받았던 질문", "나만 할 수 있는 이야기")],
     steps=prog(2), prog=True),

dict(k="shot", t="자료폴더", part=P1, img="media/my-data-folder.png",                  # 16 v1#13
     eyebrow="제가 넣은 것",
     title="지난 강의자료와|강의 녹음을 받아쓴 글",
     sub="폴더 화면으로 보여드립니다."),

dict(k="shot", t="브레인목차", part=P1, img="media/brain-index.png",                   # 17 v1#14
     eyebrow="끝 모습 하나",
     title="녹음 305건에서 뽑은|<em>제 판단 기록</em>",
     sub="처음부터 이럴 필요 없습니다. 이런 데까지 갈 수 있다는 것만 보세요."),

dict(k="flow", t="내데이터3", part=P1,                                                 # 18 v1#15
     eyebrow="강사님이 내일부터 모을 것",
     title="내 데이터 세 가지",
     nodes=[("지난 강의자료", "장표·교안·메모 뭐든"),
            ("강의·상담 녹음을 받아쓴 글", "말로 한 게 제일 나다운 자료입니다"),
            ("자주 받는 질문", "수강생이 진짜 궁금한 것")],
     steps=prog(3), prog=True),

dict(k="statement", t="방금-알려주면", part=P1,                                        # 19 v1#16
     eyebrow="방금 본 것",
     title="AI는 여러분을 모릅니다|<em>알려주면 달라집니다</em>"),

dict(k="demo", t="표지판-설계서", part=P1,                                             # 20 v1#17
     eyebrow="지금부터 볼 것 ③", title="바로 장표를|만들지 않습니다",
     sub="먼저 뼈대 문서 한 장을 만듭니다. 몇 장, 몇 분, 무슨 순서인지."),

dict(k="shot", t="구조설계서", part=P1, img="media/design-doc.png",                    # 21 v1#18
     eyebrow="구조 설계서",
     title="오늘 강의의 뼈대였던|문서 한 장",
     items=[("몇 장인가", "오늘은 57장"),
            ("몇 분에 어디까지 가는가", "시간대별 장표 배분"),
            ("왜 이 순서인가", "설계 원칙을 문장으로")]),

dict(k="statement", t="방금-설계서", part=P1,                                          # 22 v1#19
     eyebrow="방금 본 것",
     title="설계서에서 고치는 게|<em>장표에서 고치는 것보다</em> 훨씬 쉽습니다",
     sub="실제로 이 강의도 설계서 단계에서 방향을 두 번 바꿨습니다."),

dict(k="demo", t="표지판-오픈소스", part=P1,                                           # 23 v1#20
     eyebrow="지금부터 볼 것 ④", title="장표 — 남이 만든 걸|가져다 씁니다",
     sub="만드는 동안 무엇을 가져왔는지 설명드릴게요."),

dict(k="shot", t="ReelForge", part=P1, img="media/reelforge-github.png",              # 24 v1#21
     eyebrow="가져다 쓴 오픈소스",
     title="이 장표 규칙은|제가 만든 게 아닙니다",
     items=[("ReelForge · 공냥", "영상 공장 저장소의 디자인 규칙 (Apache-2.0)"),
            ("박스 없음 · 글자 크기 3단 · 강조색 한 곳", "그 규칙을 제 장표 규칙으로 옮겼습니다")]),

dict(k="shot", t="장표결과", part=P1, img="media/deck-overview.png",                   # 25 v1#22
     eyebrow="장표",
     title="설계서를 넣으면|장표가 나옵니다",
     sub="한 장에 한 문장. 박스 없음. 지금 보시는 이 화면이 결과입니다."),

dict(k="demo", t="표지판-프롬프터", part=P1,                                           # 26 v1#23
     eyebrow="지금부터 볼 것 ⑤", title="프롬프터",
     sub="제가 옆 화면에 띄워 둔 대본이 어떻게 만들어졌는지 봅니다."),

dict(k="shot", t="프롬프터화면", part=P1, img="media/prompter.png",                    # 27 v1#24
     eyebrow="프롬프터",
     title="장표마다|말할 것 · 손으로 할 것 · 막혔을 때",
     sub="말로 설명 못 하는 자료는 완성이 아닙니다. 그래서 대본까지 만듭니다."),

dict(k="demo", t="표지판-배포자료", part=P1,                                           # 28 v1#25
     eyebrow="지금부터 볼 것 ⑥", title="배포자료",
     sub="수강생에게 나눠드릴 페이지입니다. 오늘 받으실 바로 그 페이지예요."),

dict(k="shot", t="프롬프트페이지", part=P1, img="media/prompt-page.png",               # 29 v1#26
     eyebrow="배포자료",
     title="단계마다|<em>복사 버튼</em>이 붙은 프롬프트",
     sub="링크 하나로 드립니다."),

dict(k="statement", t="휴식", part=PB, big=True,                                       # 30 v1#27
     title="10분 쉬었다 갈게요",
     sub="돌아오면 이 강의를 알리는 콘텐츠를 만듭니다"),

# ═════════ 2부 ═════════
dict(k="chapter", t="2부", part=P2, eyebrow="2부", title="만들었으면 알려야 합니다"),  # 31 v1#28

dict(k="statement", t="아무도모름", part=P2, big=True,                                 # 32 v1#29
     title="강의를 만들고 끝내면|<em>아무도 모릅니다</em>"),

dict(k="compare", t="채널마다vs소스하나", part=P2, hl=1,                               # 33 v1#30
     eyebrow="알리는 방법",
     title="채널마다 새로 쓰면|오래 못 갑니다",
     cols=[("채널마다 새로 쓰기", "블로그 따로, 스레드 따로, 카드뉴스 따로"),
           ("소스 하나에서 뽑기", "강의 원고 하나로 전부")],
     steps=prog(2), prog=True),

dict(k="cycle", t="원소스순환", part=P2,                                               # 34 v1#31
     eyebrow="소스 하나, 결과 여러 개",
     title="글이 영상이 되고|영상이 다시 글이 됩니다",
     nodes=["강의 원고", "블로그 긴 글 → 스레드 짧은 글", "카드뉴스", "숏폼",
            "강의 녹음 → 다시 글 · 전자책"],
     steps=prog(5), prog=True),

dict(k="demo", t="표지판-글", part=P2,                                                 # 35 v1#32
     eyebrow="지금부터 볼 것 ①", title="원고가|블로그 글과 스레드 글이 됩니다",
     sub="새로 쓰는 게 아니라 늘리고 줄이는 걸 보세요."),

dict(k="shot", t="블로그스레드", part=P2, img="media/blog-thread.png",                 # 36 v1#33
     eyebrow="글",
     title="같은 내용|다른 길이, 다른 말투",
     items=[("블로그 긴 글", "소제목 셋, 검색해서 들어오는 사람용"),
            ("스레드 짧은 글", "다섯 문장 안쪽, 지나가다 멈추는 사람용"),
            ("마지막 손질", "AI 티 나는 문장 걷어내기 — im-not-ai · k-skill")]),

dict(k="statement", t="방금-늘리고줄임", part=P2,                                      # 37 v1#34
     eyebrow="방금 본 것",
     title="새로 쓴 게 아니라|<em>늘리고 줄였습니다</em>"),

dict(k="demo", t="표지판-카드뉴스", part=P2,                                           # 38 v1#35
     eyebrow="지금부터 볼 것 ②", title="글이 카드뉴스가 됩니다",
     sub="먼저 지금 반응 좋은 카드뉴스를 조사한 것부터 보여드릴게요."),

dict(k="stat", t="209-14-9", part=P2,                                                  # 39 v1#36
     eyebrow="레퍼런스부터",
     title="지금 반응 좋은|카드뉴스를 먼저 봤습니다",
     stats=[("인스타그램 인기 게시물", 209, 0, "개", "해시태그 12개에서 카드뉴스만"),
            ("그중", 14, 209, "개를 장마다 캡처", "한국어 · 최근 · 주제가 맞는 것"),
            ("공통 규칙", 9, 14, "개로 정리", "첫 장 두 줄, 강조색 하나, 마지막은 저장")],
     hl=2, steps=prog(3), prog=True),

dict(k="cardsteps", t="카드8장", part=P2, imgs=CARDS,                                  # 40 v1#37
     eyebrow="카드뉴스",
     title="규칙을 그대로 적용한|이 강의의 카드뉴스 8장",
     sub="넘겨보면서 규칙 하나씩 짚습니다.",
     steps=[[i] for i in range(8)]),

dict(k="statement", t="한도경로", part=P2,                                             # 41 v1#38
     eyebrow="막혔을 때",
     title="이미지 생성이 한도에 걸리면|<em>경로를 바꿉니다</em>",
     sub="이번에도 걸렸습니다. 그래서 같은 규칙으로 직접 조판했습니다."),

dict(k="demo", t="표지판-숏폼", part=P2,                                               # 42 v1#39
     eyebrow="지금부터 볼 것 ③", title="숏폼 — 기획부터 제작까지",
     sub="미리 만들어 둔 영상입니다. 사람이 고르는 곳이 어디인지 보세요."),

dict(k="flow", t="사람이고르는3", part=P2,                                             # 43 v1#40
     eyebrow="숏폼 기획",
     title="사람이 고르는 건|세 가지뿐입니다",
     nodes=[("첫 3초에 던질 한 문장", ""), ("대본", ""), ("자막으로 강조할 단어", "")],
     steps=prog(3), prog=True),

dict(k="vside", t="숏폼재생", part=P2, src=VIDEO,                                      # 44 v1#41
     eyebrow="숏폼",
     title="오프닝에서 보신|그 영상입니다",
     sub="만든 방식과 쓴 도구는 영상 뒤에 정리합니다."),

dict(k="demo", t="표지판-영상글", part=P2,                                             # 45 v1#42
     eyebrow="지금부터 볼 것 ④", title="영상이 다시 글이 됩니다",
     sub="지금 이 강의 녹음도 다음 콘텐츠의 재료가 됩니다."),

dict(k="shot", t="받아쓰기", part=P2, img="media/transcript.png",                      # 46 v1#43
     eyebrow="영상에서 글로",
     title="녹음을 받아쓰고|글과 전자책으로",
     items=[("받아쓰기", "whisper.cpp — 내 컴퓨터에서"),
            ("전자책 조판", "bookforge — 공냥")]),

dict(k="statement", t="소스하나결과다섯", part=P2, big=True,                           # 47 v1#44
     eyebrow="방금 본 것",
     title="소스는 하나|<em>결과는 다섯</em>"),

dict(k="grid", t="오픈소스목록", part=P2,                                              # 48 v1#45
     eyebrow="가져다 쓴 오픈소스",
     title="직접 다 만들지 않았습니다",
     cells=[("장표 규칙", "ReelForge · 공냥"),
            ("글 손질", "im-not-ai · epoko77-ai<br>k-skill · NomaDamas"),
            ("이미지 프롬프트 · 대량 생성", "gongnyang-prompt-kit · codex-fleet · 공냥"),
            ("전자책", "bookforge · 공냥"),
            ("숏폼 · 받아쓰기", "HyperFrames · HeyGen<br>Qwen3-TTS · QwenLM<br>whisper.cpp · ggml-org")],
     tail="모두 공개 라이선스입니다. 이름과 만든 분을 밝히고 씁니다.",
     steps=prog(5), prog=True),

# ═════════ 3부 ═════════
dict(k="chapter", t="3부", part=P3, eyebrow="3부", title="오늘 본 걸 가져가는 법"),     # 49 v1#46

dict(k="compare", t="두가지길", part=P3,                                               # 50 v1#47
     eyebrow="두 가지 길",
     title="직접 만들고 싶은 분,|만들기 귀찮은 분",
     cols=[("길 1 · 다시보기 보며 따라 하기", "단계별 프롬프트를 복사해서 내 자료로"),
           ("길 2 · 제가 쓰는 걸 받아서 바로 쓰기", "깃헙에서 받아 설치")],
     steps=prog(2), prog=True),

dict(k="shot", t="길1페이지", part=P3, img="media/prompt-page.png",                    # 51 v1#48
     eyebrow="길 1",
     title="프롬프트 페이지",
     sub="단계마다 복사 버튼, 그리고 다시보기에서 그 장면이 나오는 시각을 적어 둡니다."),

dict(k="flow", t="길1순서", part=P3,                                                   # 52 v1#49
     eyebrow="길 1 순서",
     title="네 번이면 됩니다",
     nodes=[("다시보기에서 그 단계 찾기", ""), ("프롬프트 복사", ""),
            ("내 자료 붙여넣기", ""), ("마음에 안 들면 고쳐 달라고 말하기", "")],
     tail="\"더 짧게\" \"내 말투로\" \"없는 숫자는 빼줘\" — 이 정도면 충분합니다.",
     steps=prog(4), prog=True),

dict(k="shot", t="길2깃헙", part=P3, img="media/github-kit.png",                       # 53 v1#50
     eyebrow="길 2",
     title="제가 실제로 쓰는|설정과 규칙을 그대로",
     sub="깃헙 공개 저장소입니다."),

dict(k="flow", t="길2순서", part=P3,                                                   # 54 v1#51
     eyebrow="길 2 순서",
     title="받아서 AI에게 맡기세요",
     nodes=[("초록색 Code 버튼 → Download ZIP", ""), ("압축 풀기", ""),
            ("AI에게 \"이 폴더 안내문 읽고 설치해줘\"", "")],
     tail="깃헙 계정 없어도 됩니다. 필요한 것: Claude Code 또는 Codex.",
     steps=prog(3), prog=True),

dict(k="statement", t="내말투로", part=P3, big=True, cls="wide-title",                 # 55 v1#52
     title="받은 그대로 쓰지 말고|<em>내 말투로</em> 한 줄씩 고쳐 쓰세요"),

dict(k="statement", t="이번주", part=P3,                                               # 56 v1#53
     eyebrow="이번 주에 할 것 하나",
     title="내 강의 하나 골라서|1부 첫 단계부터",
     sub="자료조사 대화 한 번이면 시작입니다."),

dict(k="closing", t="봉인", part=P3,                                                   # 57 v1#54
     title="단계를 나누면 내 강의가 되고|소스 하나면 알리는 게 쉬워집니다"),
]
