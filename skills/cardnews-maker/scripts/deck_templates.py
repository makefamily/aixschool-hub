# -*- coding: utf-8 -*-
"""카드뉴스 템플릿 3종(포스터·에디토리얼·그런지) 4:5(1080x1350). 주제 하나에 디자인 하나만 만든다.

  08-poster    @rkreate      빨강 바탕 노랑 초대형 제목 / 사진 위 노랑 제목 + 노랑 알약
  09-editorial @ggamang.zip  3D 장면 표지 + 하단 흰 제목 / 밝은 그라데이션 본문 + 예시 카드
  10-grunge    @nomadatoast  위 화면 캡처 / 아래 검정 그런지 + 장체 흰 글씨 + 보라 손그림

  이 파일은 make_deck.py 가 불러 쓴다(직접 실행하지 않는다).
"""
from pathlib import Path
import json, html, re, sys

W, H, M = 1080, 1350, 60
TEMPLATES = {
    '08-poster': '포스터 (강한 색 바탕 + 초대형 노랑 제목)',
    '09-editorial': '에디토리얼 (밝은 바탕 + 예시 카드)',
    '10-grunge': '그런지 (위 화면 + 아래 검정 장체 글씨)',
}
# 템플릿마다 필요한 생성 이미지 (deck_images.py 가 이 목록을 읽는다)
IMAGES = {'08-poster': ['cover', 'bg1', 'bg2', 'bg3'], '09-editorial': ['cover'], '10-grunge': []}
CTX = {'handle': '', 'name': '', 'initial': ''}


def esc(s):
    return html.escape(str(s))


def T(tag, cl, s, style='', fit=False):
    st = f' style="{style}"' if style else ''
    return f'<{tag} class="{cl}" data-text{" data-fit" if fit else ""}{st}>{esc(s)}</{tag}>'


# 렌더 직전: data-fit 상자가 넘치면 글자 크기를 줄인다(안쪽은 em 이라 같이 줄어든다). 그다음 겹침·넘침·안전영역을 잰다.
SCRIPT = ("<script>document.fonts.ready.then(()=>{"
          "const over=e=>{if(e.scrollHeight>e.clientHeight+2||e.scrollWidth>e.clientWidth+2)return true;const r=e.getBoundingClientRect();return [...e.querySelectorAll('[data-text]')].some(t=>{const q=t.getBoundingClientRect();return q.bottom>r.bottom+1||q.right>r.right+1||q.top<r.top-1||t.scrollWidth>t.clientWidth+2||t.scrollHeight>t.clientHeight+3})};"
          "for(const e of document.querySelectorAll('[data-grow]')){let s=parseFloat(getComputedStyle(e).fontSize),g=s*1.9;"
          "while(s<g&&!over(e)){s*=1.05;e.style.fontSize=s+'px'}}"
          "for(const e of document.querySelectorAll('[data-fit],[data-grow]')){let s=parseFloat(getComputedStyle(e).fontSize),m=s*.4;"
          "while(s>m&&over(e)){s*=.96;e.style.fontSize=s+'px'}}"
          "let a=[...document.querySelectorAll('[data-text]')].filter(e=>e.getBoundingClientRect().width>0).map(e=>{let r=e.getBoundingClientRect();"
          "return {text:e.innerText,box:[r.x,r.y,r.width,r.height],overflow:e.scrollWidth>e.clientWidth+2||e.scrollHeight>e.clientHeight+3,"
          f"safe:r.x>={M - 1}&&r.y>={M - 1}&&r.right<={W - M + 1}&&r.bottom<={H - M + 1}}}}});let overlaps=[];"
          "for(let i=0;i<a.length;i++)for(let j=i+1;j<a.length;j++){let x=a[i].box,y=a[j].box;"
          "if(Math.min(x[0]+x[2],y[0]+y[2])-Math.max(x[0],y[0])>3&&Math.min(x[1]+x[3],y[1]+y[3])-Math.max(x[1],y[1])>3)overlaps.push([i,j])}"
          "let s=document.createElement('script');s.id='render-metrics';s.type='application/json';"
          "s.textContent=JSON.stringify({checks:{safe:a.every(x=>x.safe),noOverflow:a.every(x=>!x.overflow),noTextOverlap:!overlaps.length,"
          "images:[...document.images].every(x=>x.complete&&x.naturalWidth>0),font:[...document.fonts].some(f=>f.status==='loaded')&&![...document.fonts].some(f=>f.status==='error')},overlaps,texts:a});"
          "document.body.append(s)});</script>")

FONTS = """@font-face{font-family:P5;src:url('@@FD@@/Pretendard-Medium.woff2')}
@font-face{font-family:P6;src:url('@@FD@@/Pretendard-SemiBold.woff2')}
@font-face{font-family:P7;src:url('@@FD@@/Pretendard-Bold.woff2')}
@font-face{font-family:P8;src:url('@@FD@@/Pretendard-ExtraBold.woff2')}
@font-face{font-family:P9;src:url('@@FD@@/Pretendard-Black.woff2')}
@font-face{font-family:BHS;src:url('@@FD@@/BlackHanSans-Regular.woff2')}
"""
NOISE = ("url(\"data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E"
         "%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3' stitchTiles='stitch'/%3E"
         "%3CfeColorMatrix values='0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 2.2 -1.25'/%3E%3C/filter%3E"
         "%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")")
SCRATCH = ("url(\"data:image/svg+xml,%3Csvg viewBox='0 0 1080 800' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='s'%3E"
           "%3CfeTurbulence type='fractalNoise' baseFrequency='.004 .09' numOctaves='2' seed='7'/%3E"
           "%3CfeColorMatrix values='0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 3 -1.9'/%3E%3C/filter%3E"
           "%3Crect width='100%25' height='100%25' filter='url(%23s)'/%3E%3C/svg%3E\")")

BASE = FONTS + """*{box-sizing:border-box}body{margin:0;font-family:P6,'Apple SD Gothic Neo',sans-serif}h1,p,div{margin:0}
.slide{width:1080px;height:1350px;position:relative;overflow:hidden;word-break:keep-all;overflow-wrap:anywhere}
.full{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}.abs{position:absolute}.pre{white-space:pre-line}
.vx{position:absolute;overflow:hidden;display:flex;flex-direction:column;justify-content:center}.vx>*{flex:none;width:100%}.vx{overflow-wrap:normal}
.win{border-radius:.5em;overflow:hidden;display:flex;flex-direction:column}
.bar{height:2em;display:flex;align-items:center;gap:.45em;padding:0 .8em;flex:none}.bar i{width:.62em;height:.62em;border-radius:50%;display:block}
.bar i:nth-child(1){background:#ff5f57}.bar i:nth-child(2){background:#febc2e}.bar i:nth-child(3){background:#28c840}
.bar b{margin-left:.6em;font:500 .78em/1 P5,sans-serif;opacity:.7}
.term,.code{padding:.9em 1.1em 1.1em;font:500 .9em/1.6 Menlo,'SF Mono',monospace;white-space:pre-wrap}
.term div,.code div{min-height:1.6em}.term .cmd:before{content:'$ ';color:#5af78e}
.tbl{width:100%;border-collapse:collapse;font-size:.92em}.tbl th,.tbl td{padding:.62em .7em;text-align:left}
.flow{display:flex;align-items:center;justify-content:center;gap:.3em}
.node{flex:1;min-width:0;display:flex;flex-direction:column;align-items:center;gap:.5em;text-align:center}
.node .ic{width:2.6em;height:2.6em;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.25em}
.node .lb{font:700 .9em/1.3 P7,sans-serif;white-space:nowrap}.flow.vert{flex-direction:column;align-items:stretch;gap:.15em}.flow.vert .node{flex-direction:row;gap:.8em;text-align:left;flex:none}.flow.vert .node .ic{width:2.2em;height:2.2em;font-size:1.05em}.flow.vert .arrow{margin:0 0 0 .62em;transform:rotate(90deg);width:1em;text-align:center}.arrow{flex:none;font:700 1.3em/1 P7;opacity:.6;margin-bottom:1.6em}
.gauge .big{font:900 3.4em/1.22 P9,sans-serif;letter-spacing:-.02em;padding-right:.1em}.gauge .big small{font-size:.38em;opacity:.55;margin-left:.15em}
.gauge .gl{font:600 .9em/1.3 P6;opacity:.75;margin:.3em 0 1em}
.track{position:relative;display:flex;height:1.1em;gap:.2em}
.track span{display:block;height:100%;border-radius:.3em}.pin{position:absolute;top:-.55em;width:.28em;height:2.2em;border-radius:.2em;background:currentColor}
.bands{display:flex;gap:.2em;margin-top:.7em}.bands div{font:600 .78em/1.3 P6;opacity:.8}
.chat{display:flex;flex-direction:column;gap:.7em}.msg{max-width:80%;padding:.75em 1em;border-radius:1.1em;font:600 .92em/1.45 P6}
.msg.me{align-self:flex-end;border-bottom-right-radius:.3em}.msg.ai{align-self:flex-start;border-bottom-left-radius:.3em}
.cmp{display:flex;gap:.8em}.cmp>div{flex:1;min-width:0;padding:1em 1.1em;border-radius:.6em}
.cmp .cl{font:700 .78em/1.2 P7;margin-bottom:.7em;display:inline-block;padding:.3em .6em;border-radius:.3em}
.cmp .ct{font:700 1em/1.45 P7}
.chk{display:flex;flex-direction:column;gap:.15em}.chk .it{display:flex;align-items:center;gap:.8em;padding:.6em .2em;font:700 1em/1.35 P7}
.box{width:1.3em;height:1.3em;border-radius:.3em;border:.13em solid currentColor;flex:none;display:flex;align-items:center;justify-content:center;font-size:.9em}
.set .row{display:flex;justify-content:space-between;align-items:center;gap:1em;padding:.75em 1em;font:600 .92em/1.3 P6}
.tog{width:2.6em;height:1.45em;border-radius:1em;position:relative;flex:none}.tog:after{content:'';position:absolute;top:.17em;width:1.1em;height:1.1em;border-radius:50%;background:#fff}
.tog.on:after{right:.17em}.tog.off:after{left:.17em}
"""

CSS = {
'08-poster': BASE + """
.slide{background:#cf1820;color:#ffe94f}
.part{left:60px;right:60px;top:100px;text-align:center;font:700 25px/1.2 P7;letter-spacing:.14em}
.mega{left:70px;right:70px;top:150px;height:330px;text-align:center;font:800 150px/1.06 P8;letter-spacing:-.045em}
.smile{position:absolute;width:156px;height:156px;border-radius:50%;background:#ffe94f;right:118px;top:860px;transform:rotate(-14deg);box-shadow:0 14px 26px #0005}
.smile:before,.smile:after{content:'';position:absolute;top:44px;width:17px;height:33px;border-radius:50%;background:#191919}.smile:before{left:47px}.smile:after{right:47px}
.smile i{position:absolute;left:33px;right:33px;top:64px;height:52px;border-bottom:10px solid #191919;border-radius:0 0 80px 80px}
.body .shade{position:absolute;inset:0;background:linear-gradient(180deg,#000c 0%,#0007 22%,#0000 40%,#0000 75%,#0008 100%)}
.body .head{left:80px;right:80px;top:120px;height:160px;text-align:center;font:700 58px/1.2 P7;letter-spacing:-.03em;text-shadow:0 2px 18px #0006}
.pill{left:50%;transform:translateX(-50%);top:300px;background:#ffe94f;color:#141414;height:62px;padding:0 44px;border-radius:50%;display:flex;align-items:center;
 font:700 27px/1 'Courier New',P7,monospace;letter-spacing:.04em;white-space:nowrap;box-shadow:0 3px 0 #0003}
.prop{left:110px;right:110px;top:430px;height:760px;font-size:34px}
.prop .card,.prop .win{background:#fffdf6;color:#1d1d1d;border-radius:22px;box-shadow:0 30px 70px #0008,0 6px 16px #0004;overflow:hidden}
.prop .win.dark{background:#17181c;color:#eef0f3}.prop .win.dark .bar{background:#22242a}.prop .win .bar{background:#f0ece0}
.prop .tbl th{background:#1d1d1d;color:#ffe94f;font:700 .85em/1.2 P7}.prop .tbl td{border-bottom:2px solid #0000000f;font:600 .9em/1.3 P6}
.prop .win.dark .tbl th{background:#2b2d33}.prop .win.dark .tbl td{border-bottom-color:#ffffff14}
.prop .node .ic{background:#ffe94f;box-shadow:inset 0 0 0 .12em #1d1d1d}
.prop .track span:nth-child(1){background:#e2463c}.prop .track span:nth-child(2){background:#f3b81f}.prop .track span:nth-child(3){background:#2fb86b}.prop .track span:nth-child(4){background:#2d6be3}
.prop .msg.me{background:#cf1820;color:#fff}.prop .msg.ai{background:#efece3}
.prop .cmp>div:first-child{background:#efece3}.prop .cmp>div:last-child{background:#ffe94f}.prop .cmp .cl{background:#1d1d1d;color:#fff}
.prop .box.on{background:#cf1820;border-color:#cf1820;color:#fff}.prop .set .row{border-bottom:2px solid #0000000f}.prop .tog.on{background:#2fb86b}.prop .tog.off{background:#c9c4b8}
.prop .code .k{color:#ffcf5c}.prop .code .s{color:#8be28b}.prop .code .n{color:#ff9c7a}
.closing .mega{top:170px;height:310px;font-size:128px}
.closing .desc{left:100px;right:100px;top:520px;height:180px;text-align:center;font:700 38px/1.45 P7;letter-spacing:-.02em}
.closing .pill{top:760px;height:130px;padding:0 80px;font:800 70px/1 P8;letter-spacing:-.03em}
.closing .cta2{left:60px;right:60px;top:935px;text-align:center;font:700 38px/1.3 P7}
.closing .smile{top:1070px;right:130px}
.slide.noimg.cover{background:radial-gradient(ellipse 70% 40% at 50% 85%,#e9323b 0%,#cf182000 70%),#cf1820}
.slide.noimg.body{background:radial-gradient(ellipse 80% 50% at 50% 100%,#e9323b 0%,#cf182000 70%),#b3141b}
""",
'09-editorial': BASE + """
.slide{color:#161616;background:radial-gradient(ellipse 62% 42% at 72% 64%,#ffcfe0 0%,#ffcfe000 72%),radial-gradient(ellipse 60% 40% at 8% 0%,#d9d9d9 0%,#d9d9d900 70%),linear-gradient(175deg,#f1f1f1 0%,#fcfcfc 30%,#fff7fa 62%,#f0f0f0 100%)}
.slide.dark{color:#fff;background:radial-gradient(ellipse 85% 45% at 50% -5%,#444 0%,#44444400 70%),#171717}
.handle{left:81px;right:81px;top:62px;text-align:center;font:500 25px/1.2 P5;color:#a2a2a2;letter-spacing:.01em}
.cover .handle,.closing .handle{color:#fff;opacity:.92}
.cover .shade{position:absolute;inset:0;background:linear-gradient(180deg,#0000 0%,#0000 48%,#000b 74%,#000e 100%)}
.cover .tag{left:84px;top:930px;border:2px solid #fff;color:#fff;font:600 27px/1.2 P6;padding:8px 14px;background:#0005}
.cover .mega{left:84px;right:84px;top:1000px;height:230px;color:#fff;font:800 86px/1.17 P8;letter-spacing:-.035em}
.kick{left:81px;right:81px;top:150px;font:600 27px/1.2 P6;color:#4a4a4a}.dark .kick{color:#ff7fab}.kick b{font-family:P7;margin-right:12px}
.body .head{left:81px;right:81px;top:200px;height:180px;font:700 62px/1.27 P7;letter-spacing:-.035em}
.stage{left:81px;right:81px;top:430px;height:560px;font-size:31px}
.body .desc{left:81px;right:81px;top:1040px;height:170px;font:500 28px/1.62 P5;color:#4f4f4f;letter-spacing:-.01em}.dark .desc{color:#dcdcdc}
.page{right:81px;bottom:74px;font:500 22px/1.2 P5;color:#8f8f8f}
.shot{background:#1c1d21;color:#eceff3;box-shadow:0 18px 44px #0000002e}.shot .bar{background:#26272c}
.shot .tbl th{color:#9aa0aa;font:600 .78em/1.2 P6;border-bottom:1px solid #ffffff22}.shot .tbl td{border-bottom:1px solid #ffffff12;font:600 .9em/1.3 P6}
.shot .code .k{color:#ff8fb6}.shot .code .s{color:#9ee6a0}.shot .code .n{color:#ffd479}
.paper{background:#fff;color:#161616;border-radius:.5em;box-shadow:0 18px 44px #0000001f}.paper:not(.win){padding:1.1em 1.2em}
.paper .bar{background:#f3f3f3}.dark .paper{background:#232326;color:#fff}.dark .paper .bar{background:#2c2c30}
.node .ic{background:#fff;box-shadow:0 .25em .7em #0000001a}.dark .node .ic{background:#2b2b2f}
.track span:nth-child(1){background:#ff8fb6}.track span:nth-child(2){background:#ffc56b}.track span:nth-child(3){background:#7ad3a0}.track span:nth-child(4){background:#7aa7ff}
.msg.me{background:#161616;color:#fff}.msg.ai{background:#fff;box-shadow:0 .2em .6em #0000001a}.dark .msg.me{background:#ff7fab;color:#161616}.dark .msg.ai{background:#2b2b2f;color:#fff}
.chat{padding:.2em}
.set .row{border-bottom:1px solid #00000012}.dark .set .row{border-bottom-color:#ffffff14}.tog.on{background:#ff6f9f}.tog.off{background:#c9c9c9}
.ex .lab{font:600 .85em/1.2 P6;color:#666;margin-bottom:.35em}.dark .ex .lab{color:#aaa}
.ex .big{font:800 2.3em/1.18 P8;letter-spacing:-.035em;margin-bottom:.6em}.ex .big.after{color:#e8487f}
.list .it{display:flex;gap:1.6em;align-items:baseline;padding:.75em 0;border-top:1px solid #0000001a}.list .it:last-child{border-bottom:1px solid #0000001a}
.dark .list .it{border-color:#ffffff1f}.list .no{font:600 .8em/1.2 P6;color:#8a8a8a;flex:none;width:1.6em}.list .tt{font:700 1.15em/1.35 P7}
.closing .blur{position:absolute;inset:-90px;width:calc(100% + 180px);height:calc(100% + 180px);object-fit:cover;filter:blur(46px) brightness(.78) saturate(.9)}
.closing .head{left:110px;right:110px;top:440px;height:150px;text-align:center;color:#fff;font:700 44px/1.45 P7;letter-spacing:-.02em}
.closing .desc{left:110px;right:110px;top:610px;text-align:center;color:#fff;font:500 30px/1.5 P5;opacity:.92}
.slide.noimg.cover,.slide.noimg.closing{background:radial-gradient(ellipse 80% 45% at 72% 22%,#ff7fab66 0%,#0000 70%),linear-gradient(170deg,#2e2e33,#101012)}
.profile{position:absolute;left:150px;right:150px;top:745px;height:176px;border-radius:88px;background:#fff;display:flex;align-items:center;padding:0 34px;gap:26px;box-shadow:0 18px 50px #0003}
.avatar{width:112px;height:112px;border-radius:50%;background:#161616;color:#fff;font:900 46px/112px P9;text-align:center;flex:none}
.who{flex:1;min-width:0;color:#161616}.who b{display:block;font:700 36px/1.3 P7}.who span{display:block;font:500 26px/1.3 P5;color:#777}
.follow{background:#4766ff;color:#fff;font:700 27px/1.2 P7;padding:16px 24px;border-radius:40px;white-space:nowrap;flex:none}
""",
'10-grunge': BASE + f"""
.slide{{background:#0b0b0b;color:#f3f3f1}}
.screen{{position:absolute;left:0;top:0;width:1080px;height:600px;background:#121317;overflow:hidden}}
.screen .bar{{background:#1e1f24;height:56px;font-size:26px}}
.screen .vx{{left:70px;right:70px;top:90px;bottom:70px;font-size:31px;color:#eceff3}}
.screen .tbl th{{color:#8d93a0;font:600 .8em/1.2 P6;border-bottom:1px solid #ffffff22}}.screen .tbl td{{border-bottom:1px solid #ffffff10;font:600 .92em/1.3 P6}}
.screen .code .k{{color:#b89bff}}.screen .code .s{{color:#9ee6a0}}.screen .code .n{{color:#ffd479}}
.screen .node .ic{{background:#26272e;box-shadow:inset 0 0 0 .1em #8e6bff}}.screen .msg.me{{background:#8e6bff;color:#fff}}.screen .msg.ai{{background:#26272e}}
.screen .cmp>div{{background:#1c1d23}}.screen .cmp>div:last-child{{box-shadow:inset 0 0 0 .1em #8e6bff}}.screen .cmp .cl{{background:#8e6bff;color:#fff}}
.screen .set .row{{border-bottom:1px solid #ffffff12}}.screen .tog.on{{background:#8e6bff}}.screen .tog.off{{background:#3a3b42}}.screen .box.on{{background:#8e6bff;border-color:#8e6bff}}
.screen .track span:nth-child(1){{background:#ff5f6d}}.screen .track span:nth-child(2){{background:#ffc35a}}.screen .track span:nth-child(3){{background:#4fd18b}}.screen .track span:nth-child(4){{background:#6b9bff}}
.screen .glow{{position:absolute;inset:0;background:radial-gradient(ellipse at 80% 0%,#8e6bff33,#0000 55%);pointer-events:none}}
.tear{{position:absolute;left:0;top:560px;width:1080px;height:90px}}
.grain{{position:absolute;left:0;right:0;top:600px;bottom:0;background-image:{NOISE},{SCRATCH};background-size:400px 400px,100% 100%;opacity:.3;mix-blend-mode:screen}}
.cond{{font-family:BHS,P9,sans-serif;font-weight:400;transform:scaleX(.86);transform-origin:left top;width:1063px;letter-spacing:-.01em}}
.t1{{left:84px;top:680px;height:96px;font-size:80px;line-height:1.12;white-space:nowrap}}
.t2{{left:84px;top:780px;height:200px;font-size:168px;line-height:1.1}}
.t3{{left:84px;top:1000px;height:290px;font-size:62px;line-height:1.16}}
.ring,.crown,.under{{position:absolute;pointer-events:none}}
.note{{right:70px;top:640px;width:220px;text-align:center;font:500 25px/1.25 'Bradley Hand','Chalkboard SE',cursive;color:#cfcfcf;transform:rotate(-7deg)}}
.num{{left:84px;top:650px;font:400 50px/1.1 BHS;color:#9b7bff}}
.body .t2{{top:720px;height:320px;font-size:134px;line-height:1.1;white-space:pre-line}}
.body .t3{{top:1075px;height:215px;font-size:56px;color:#d4d4d4}}
.closing .t1{{top:120px}}.closing .t2{{top:220px;height:350px;font-size:140px;white-space:pre-line}}
.closing .t3{{top:610px;height:150px;color:#d4d4d4;font-size:56px}}
.closing .cta{{left:84px;top:850px;height:230px;font-size:190px;line-height:1.1;white-space:nowrap}}
.closing .cta2{{left:84px;top:1120px;height:100px;font-size:76px;line-height:1.15;color:#9b7bff}}
.closing .grain{{top:0}}
""",
}


def code_line(s):
    """JSON 한 줄에 색만 입힌다 (키·문자열·숫자)."""
    out = esc(s)
    out = re.sub(r'(&quot;[^&]*?&quot;)(\s*:)', r'<span class="k">\1</span>\2', out)
    out = re.sub(r':(\s*)(&quot;[^&]*?&quot;)', r':\1<span class="s">\2</span>', out)
    out = re.sub(r':(\s*)(-?\d+(?:\.\d+)?)', r':\1<span class="n">\2</span>', out)
    return out


def window(title, inner, cls):
    return f'<div class="win {cls}"><div class="bar"><i></i><i></i><i></i><b>{esc(title)}</b></div>{inner}</div>'


def visual(v, theme):
    """theme: 'paper'(에디토리얼) / 'card'(포스터 위 소품) / 'screen'(그런지 상단 화면, 창틀 없음)"""
    k = v['kind']
    framed = theme != 'screen'
    box = 'paper' if theme == 'paper' else 'card'
    dark_win = 'shot dark' if theme == 'paper' else 'dark'
    if k == 'terminal':
        lines = ''.join(f'<div class="{"cmd" if l.startswith("$") else ""}" data-text>{esc(l[1:].lstrip() if l.startswith("$") else l)}</div>'
                        for l in v['lines'])
        body = f'<div class="term">{lines}</div>'
        return window('terminal', body, dark_win) if framed else body
    if k == 'code':
        lines = ''.join(f'<div data-text>{code_line(l)}</div>' for l in v['lines'])
        body = f'<div class="code">{lines}</div>'
        return window(v.get('title', 'file.json'), body, dark_win) if framed else body
    if k == 'table':
        head = ''.join(f'<th data-text>{esc(c)}</th>' for c in v['columns'])
        rows = ''.join('<tr>' + ''.join(f'<td data-text>{esc(c)}</td>' for c in r) + '</tr>' for r in v['rows'])
        body = f'<table class="tbl"><tr>{head}</tr>{rows}</table>'
        return window(v.get('title', 'sheet'), f'<div style="padding:.6em .8em 1em">{body}</div>', dark_win) if framed else body
    if k == 'flow':
        parts = []
        for j, n in enumerate(v['nodes']):
            if j:
                parts.append('<div class="arrow">→</div>')
            parts.append(f'<div class="node"><div class="ic">{esc(n.get("icon", "•"))}</div><div class="lb" data-text>{esc(n["label"])}</div></div>')
        body = f'<div class="flow{" vert" if len(v["nodes"]) >= 4 else ""}">{"".join(parts)}</div>'
        return f'<div class="{box}" style="padding:1.6em 1em">{body}</div>' if framed else body
    if k == 'gauge':
        mx = float(v.get('max') or 100) or 100
        val = max(0.0, min(float(v.get('value') or 0), mx))
        prev, segs, labs = 0.0, '', ''
        for b in v['bands']:
            up = min(float(b.get('upto', mx)), mx)
            w = max(up - prev, 0) / mx * 100
            segs += f'<span style="width:{w:.1f}%"></span>'
            # 구간이 아주 좁아도 이름은 읽혀야 하므로 이름 칸은 같은 너비로 나눈다
            labs += f'<div data-text style="flex:1;min-width:0">{esc(b["label"])}</div>'
            prev = up
        num = int(val) if val == int(val) else val
        body = (f'<div class="gauge"><div class="big" data-text>{num}<small>/ {int(mx)}</small></div><div class="gl" data-text>{esc(v["label"])}</div>'
                f'<div class="track">{segs}<div class="pin" style="left:calc({val / mx * 100:.1f}% - .14em)"></div></div><div class="bands">{labs}</div></div>')
        return f'<div class="{box}" style="padding:1.4em 1.4em 1.6em">{body}</div>' if framed else body
    if k == 'chat':
        body = '<div class="chat">' + ''.join(f'<div class="msg {"me" if m.get("who") == "me" else "ai"}" data-text>{esc(m["text"])}</div>'
                                              for m in v['messages']) + '</div>'
        if theme == 'paper':
            return body
        return f'<div class="card" style="padding:1.2em">{body}</div>' if framed else body
    if k == 'compare':
        L, R = v['left'], v['right']
        if theme == 'paper':   # 에디토리얼은 레퍼런스 7장 문법(작은 라벨 + 큰 글씨)
            return ('<div class="ex">' + T('div', 'lab', L['label']) + T('div', 'big pre', '\n'.join(L['lines'])) +
                    T('div', 'lab', R['label']) + T('div', 'big after pre', '\n'.join(R['lines'])) + '</div>')
        cell = lambda s: (f'<div><div class="cl" data-text>{esc(s["label"])}</div>' +
                          ''.join(f'<div class="ct" data-text>{esc(x)}</div>' for x in s['lines']) + '</div>')
        body = f'<div class="cmp">{cell(L)}{cell(R)}</div>'
        return f'<div class="card" style="padding:1em">{body}</div>' if framed else body
    if k == 'checklist':
        done = int(v.get('done', 0) or 0)
        if theme == 'paper':   # 레퍼런스 10장 체크리스트
            return '<div class="list">' + ''.join(f'<div class="it"><span class="no" data-text>{j + 1:02}</span><span class="tt" data-text>{esc(x)}</span></div>'
                                                  for j, x in enumerate(v['items'])) + '</div>'
        body = '<div class="chk">' + ''.join(f'<div class="it"><span class="box{" on" if j < done else ""}">{"✓" if j < done else ""}</span><span data-text>{esc(x)}</span></div>'
                                             for j, x in enumerate(v['items'])) + '</div>'
        return f'<div class="card" style="padding:1.1em 1.3em">{body}</div>' if framed else body
    if k == 'settings':
        def val(x):
            x = str(x)
            if x.lower() in ('on', 'off'):
                return f'<span class="tog {x.lower()}"></span>'
            return f'<b data-text style="font-family:P7">{esc(x)}</b>'
        rows = ''.join(f'<div class="row"><span data-text>{esc(r["label"])}</span>{val(r["value"])}</div>' for r in v['rows'])
        body = f'<div class="set">{rows}</div>'
        return window(v.get('title', 'settings'), body, box) if framed else body
    raise ValueError('모르는 kind: ' + k)


def IM(cls, src):
    return f'<img class="{cls}" src="{src}">' if src else ''


def NI(src):
    return '' if src else ' noimg'


def poster(i, typ, f, n, V, img):
    if typ == 'cover':
        lab = (f.get('sub') or '').replace('\n', ' ')
        return ('<div class="slide cover' + NI(img('cover')) + '">' + IM('full', img('cover')) + T('div', 'abs part', lab) +
                T('h1', 'abs mega pre', f['title'], fit=True) + '<div class="smile"><i></i></div></div>')
    if typ == 'closing':
        return ('<div class="slide closing">' + T('h1', 'abs mega pre', f['title'], fit=True) + T('p', 'abs desc', f['desc'], fit=True) +
                T('div', 'abs pill', f['cta1']) + T('div', 'abs cta2', f['cta2'] + ' ↗') + '<div class="smile"><i></i></div></div>')
    return ('<div class="slide body' + NI(img('bg1')) + '">' + IM('full', img('bg' + str((i - 2) % 3 + 1))) + '<div class="shade"></div>' +
            T('h1', 'abs head pre', f['head'], fit=True) + T('div', 'abs pill', f'STEP {i - 1:02}: {f["word"]}') +
            f'<div class="vx prop" data-grow>{visual(V[str(i)], "card")}</div></div>')


def editorial(i, typ, f, n, V, img):
    if typ == 'cover':
        lab = (f.get('sub') or '').replace('\n', ' ')
        return ('<div class="slide cover' + NI(img('cover')) + '">' + IM('full', img('cover')) + '<div class="shade"></div>' +
                T('div', 'abs handle', CTX['handle']) + T('div', 'abs tag', lab) + T('h1', 'abs mega pre', f['title'], fit=True) + '</div>')
    if typ == 'closing':
        return ('<div class="slide closing' + NI(img('cover')) + '">' + IM('blur', img('cover')) + T('div', 'abs handle', CTX['handle']) +
                T('h1', 'abs head pre', f['title'], fit=True) + T('p', 'abs desc', f['desc']) +
                f'<div class="profile"><div class="avatar">{esc(CTX["initial"])}</div><div class="who"><b data-text>{esc(CTX["name"])}</b>'
                f'<span data-text>{esc(f["cta1"])}</span></div><div class="follow" data-text>{esc(f["cta2"])}</div></div></div>')
    dark = i % 3 == 1 and i < n
    return (f'<div class="slide body{" dark" if dark else ""}">' + T('div', 'abs handle', CTX['handle']) +
            f'<div class="abs kick" data-text><b>{i - 1:02}</b>{esc(f["word"])}</div>' + T('h1', 'abs head pre', f['head'], fit=True) +
            f'<div class="vx stage" data-grow>{visual(V[str(i)], "paper")}</div>' +
            T('p', 'abs desc', f['desc'], fit=True) + T('div', 'abs page', f'{i:02} / {n}') + '</div>')


TEAR = ('<svg class="tear" viewBox="0 0 1080 90" preserveAspectRatio="none"><path d="M0 40 L60 28 L120 46 L180 30 L250 50 L320 34 L390 52 L450 36 L520 55 '
        'L590 38 L660 50 L720 30 L800 48 L860 33 L930 52 L1000 36 L1080 46 L1080 90 L0 90 Z" fill="#0b0b0b"/></svg>')


def ring(x, y, w, h):
    W2, H2 = w + 70, h + 50
    d = (f'M{W2 * .09:.0f} {H2 * .58:.0f} C {W2 * .04:.0f} {H2 * .14:.0f}, {W2 * .52:.0f} {H2 * .02:.0f}, {W2 * .9:.0f} {H2 * .12:.0f} '
         f'C {W2:.0f} {H2 * .2:.0f}, {W2 * .99:.0f} {H2 * .8:.0f}, {W2 * .82:.0f} {H2 * .92:.0f} C {W2 * .58:.0f} {H2:.0f}, {W2 * .12:.0f} {H2 * .98:.0f}, '
         f'{W2 * .03:.0f} {H2 * .68:.0f} C 0 {H2 * .48:.0f}, {W2 * .08:.0f} {H2 * .3:.0f}, {W2 * .24:.0f} {H2 * .2:.0f}')
    return (f'<svg class="ring" style="left:{x - 35:.0f}px;top:{y - 25:.0f}px" width="{W2:.0f}" height="{H2:.0f}"><path d="{d}" fill="none" stroke="#8e6bff" '
            'stroke-width="8" stroke-linecap="round"/></svg>')


def crown(x, y):
    return (f'<svg class="crown" style="left:{x}px;top:{y}px;transform:rotate(14deg)" width="96" height="72" viewBox="0 0 120 90"><path d="M10 78 L18 22 L42 52 L60 10 '
            'L78 52 L102 22 L110 78 Z" fill="none" stroke="#8e6bff" stroke-width="6" stroke-linejoin="round"/></svg>')


def cond_w(line, size):
    """Black Han Sans 장체(가로 86%)로 쓴 한 줄의 대략 너비."""
    return sum(0.42 if c == ' ' else (0.72 if c.isascii() else 0.96) for c in line) * size * 0.86


def under(left, top, w):
    return (f'<svg class="under" style="left:{left}px;top:{top:.0f}px" width="{w:.0f}" height="34"><path d="M6 22 C {w * .3:.0f} 6, {w * .62:.0f} 30, {w - 8:.0f} 12" '
            'fill="none" stroke="#8e6bff" stroke-width="8" stroke-linecap="round"/></svg>')


def screen(v):
    return ('<div class="screen"><div class="bar"><i></i><i></i><i></i></div>'
            f'<div class="vx" data-grow>{visual(v, "screen")}</div><div class="glow"></div></div>' + TEAR + '<div class="grain"></div>')


def grunge(i, typ, f, n, V, img):
    if typ == 'closing':
        cta = f['cta1']
        size = min(190, int(900 / max(cond_w(cta, 1), 1)))
        return ('<div class="slide closing"><div class="grain"></div>' + T('div', 'abs cond t1', CTX['name']) +
                T('h1', 'abs cond t2 pre', f['title'], fit=True) + T('p', 'abs cond t3', f['desc'], fit=True) +
                T('div', 'abs cond cta', cta, f'font-size:{size}px') + ring(84, 850 + size * .1, cond_w(cta, size), size * .95) +
                T('div', 'abs cond cta2', f['cta2'] + ' ↗') + '</div>')
    if typ == 'cover':
        first = next((V[str(k)] for k in range(2, n) if V[str(k)]['kind'] in ('terminal', 'code', 'settings')), V['2'])
        title = f['title'].replace('\n', ' ')
        one = cond_w(title, 150) <= 912
        lines = [title] if one else f['title'].split('\n')
        widest = max(lines, key=lambda x: cond_w(x, 1))
        size = int(min(168 if one else 150, 912 / max(cond_w(widest, 1), 0.01)))
        top, th = 780, int(size * 1.1 * len(lines)) + 10
        rows = ' / '.join(f.get('rows') or [])
        sub = (f.get('sub') or '').replace('\n', ' ')
        lw = cond_w(lines[0], size)
        return ('<div class="slide cover">' + screen(first) +
                T('div', 'abs cond t1', sub, fit=True) +
                T('h1', 'abs cond t2', '\n'.join(lines), f'font-size:{size}px;height:{th}px;white-space:pre') +
                ring(84, top + size * .12, lw, size * .92) + crown(int(84 + lw + 18), top - 52) +
                T('div', 'abs cond t3', rows, f'top:{top + th + 20}px;height:{1290 - top - th - 20}px', fit=True) + '</div>')
    head = f['head']
    last = head.split('\n')[-1]
    uw = min(cond_w(last, 134), 900)
    return ('<div class="slide body">' + screen(V[str(i)]) +
            T('div', 'abs num', f'#{i - 1:02}') + T('div', 'abs note', f['word']) +
            T('h1', 'abs cond t2', head, fit=True) + under(76, 720 + 134 * 1.1 * len(head.split('\n')) - 18, uw) +
            T('p', 'abs cond t3', f['desc'], fit=True) + '</div>')


BUILD = {'08-poster': poster, '09-editorial': editorial, '10-grunge': grunge}


def recolor(text, slug, accent):
    """내 브랜드 색 하나를 템플릿 대표색 자리에 넣는다. 진한 색일수록 잘 맞는다."""
    if not accent:
        return text
    a = accent.lstrip('#')
    if not re.fullmatch(r'[0-9a-fA-F]{6}', a):
        return text
    a = '#' + a
    swap = {'08-poster': ['#cf1820', '#b3141b', '#e9323b'],
            '09-editorial': ['#ff7fab', '#e8487f', '#ff6f9f', '#ff8fb6'],
            '10-grunge': ['#8e6bff', '#9b7bff', '#b89bff']}[slug]
    for old in swap:
        text = text.replace(old, a)
    return text


def page_html(slug, i, s, n, V, img):
    body = BUILD[slug](i, s['type'], s['f'], n, V, img)
    return ('<!doctype html><html lang="ko"><meta charset="utf-8"><link rel="stylesheet" href="style.css"><body>' + body + SCRIPT + '</body></html>')


def generate(deck, out_dir, slug, images_dir, font_dir, brand=None, accent=None):
    """out_dir/src/style.css 와 NN.html 을 쓴다. 이미지는 images_dir 에 있는 것만 쓴다(없으면 이미지 없는 배경)."""
    brand = brand or {}
    CTX['handle'] = deck.get('handle') or brand.get('handle') or ''
    CTX['name'] = deck.get('brand_name') or brand.get('name') or CTX['handle'].lstrip('@') or ''
    CTX['initial'] = (CTX['name'][:1] or '').upper()
    V = (deck.get('visuals') or {}).get('slides') or {}
    out = Path(out_dir) / 'src'
    out.mkdir(parents=True, exist_ok=True)
    font_uri = Path(font_dir).resolve().as_uri()
    css = CSS[slug].replace('@@FD@@', font_uri)
    (out / 'style.css').write_text(recolor(css, slug, accent), encoding='utf-8')
    images_dir = Path(images_dir).resolve()
    import os

    def img(key):
        for ext in ('png', 'jpg', 'jpeg', 'webp'):
            f = images_dir / f'{key}.{ext}'
            if f.is_file():
                return os.path.relpath(f, out).replace(os.sep, '/')
        return None
    slides = deck['slides']
    n = len(slides)
    pages = []
    for i, s in enumerate(slides, 1):
        (out / f'{i:02}.html').write_text(recolor(page_html(slug, i, s, n, V, img), slug, accent), encoding='utf-8')
        pages.append(out / f'{i:02}.html')
    return pages
