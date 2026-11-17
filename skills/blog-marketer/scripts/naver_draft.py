#!/usr/bin/env python3
"""네이버 블로그 작성창에 글을 넣고 '임시저장'까지만 하는 도우미.

학생이 쓰는 도구가 아니라 AI가 실행하는 도구다. 맥·윈도우 둘 다 된다.

하지 않는 것
- 아이디·비밀번호를 받거나 입력하지 않는다. 로그인은 열린 창에서 학생이 직접 한다.
- 발행·예약 발행 버튼을 누르지 않는다(이 파일에 그 코드가 없다).
- 캡차·보안 확인을 피해 가지 않는다. 막히면 멈추고 알린다.

명령
  check                    파이썬 패키지·브라우저가 준비됐는지 본다
  parse POST.md            원고를 어떻게 읽었는지 브라우저 없이 보여준다
  login [--probe]          로그인 창을 연다. --probe는 로그인 페이지가 열리는지만 보고 닫는다
  draft POST.md            작성창에 제목·본문·사진을 넣고 임시저장한다

원고 형식(POST.md)
  # 제목                       첫 제목 한 줄
  ## 소제목                    굵게 들어간다
  [사진: 설명]                 --images로 받은 사진을 순서대로 넣는다. 사진이 모자라면 자리 표시 글자로 남긴다
  <!-- 본문 끝 -->             이 줄 아래(확인 필요 목록 등)는 올리지 않는다
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import sys
import time
from pathlib import Path

try:  # 윈도우 콘솔에서도 한글이 깨지지 않게
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

WRITE_URL = os.environ.get("AIXSCHOOL_BLOG_WRITE_URL") or "https://blog.naver.com/GoBlogWrite.naver"  # 환경변수는 시험용
LOGIN_HOST = "nid.naver.com"
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
IMAGE_MAX_BYTES = 10 * 1024 * 1024
END_MARK = re.compile(r"<!--\s*본문\s*끝\s*-->")
STOP_HEADING = re.compile(r"^#{1,3}\s*(이\s*글에서\s*)?확인(이)?\s*필요")


def say(step: str, **kw) -> None:
    print(json.dumps({"step": step, **kw}, ensure_ascii=False), flush=True)


# ---------------------------------------------------------------- 원고 읽기

def parse_post(text: str) -> dict:
    """원고를 title + blocks 로 바꾼다. 브라우저가 필요 없다."""
    lines = text.replace("\r\n", "\n").split("\n")
    title = ""
    blocks: list[dict] = []
    para: list[str] = []

    def flush() -> None:
        if para:
            blocks.append({"type": "p", "text": " ".join(para).strip()})
            para.clear()

    for raw in lines:
        line = raw.strip()
        if END_MARK.search(line) or STOP_HEADING.match(line):
            break
        if line.startswith("<!--"):
            continue
        if not title and re.match(r"^#\s+\S", line):
            title = re.sub(r"^#\s+", "", line).strip()
            continue
        if not line:
            flush()
            continue
        m = re.match(r"^\[사진\s*[:：]\s*(.*?)\]$", line)
        if m:
            flush()
            blocks.append({"type": "image", "text": m.group(1).strip()})
            continue
        m = re.match(r"^#{2,4}\s+(.+)$", line)
        if m:
            flush()
            blocks.append({"type": "h", "text": clean_inline(m.group(1))})
            continue
        # 줄머리 기호는 네이버가 글머리 목록으로 바꿔 버리므로 점으로 바꾼다
        line = re.sub(r"^[-*]\s+", "· ", line)
        line = re.sub(r"^>\s*", "", line)
        para.append(clean_inline(line))
    flush()
    if not title:
        raise ValueError("원고 맨 위에 '# 제목' 한 줄이 필요합니다.")
    if not any(b["type"] == "p" for b in blocks):
        raise ValueError("본문 문단이 없습니다.")
    return {"title": title, "blocks": blocks}


def clean_inline(s: str) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    return s.strip()


def check_images(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        f = Path(p).expanduser()
        if not f.is_file():
            raise ValueError(f"사진 파일을 찾지 못했습니다: {f.name}")
        if f.suffix.lower() not in IMAGE_EXT:
            raise ValueError(f"사진 형식이 맞지 않습니다(jpg·png·gif·webp): {f.name}")
        if f.stat().st_size > IMAGE_MAX_BYTES:
            raise ValueError(f"사진이 10MB보다 큽니다: {f.name}")
        out.append(f.resolve())
    return out


# ---------------------------------------------------------------- 브라우저

def profile_dir() -> Path:
    env = os.environ.get("AIXSCHOOL_BLOG_PROFILE")
    if env:
        return Path(env)
    system = platform.system()
    if system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    elif system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return base / "AIxSCHOOL-Hub" / "naver-blog-profile"


def browser_candidates() -> list[tuple[str, str]]:
    """(playwright channel, 실행 파일 경로) 중 이 컴퓨터에 있는 것."""
    system = platform.system()
    found: list[tuple[str, str]] = []
    if system == "Darwin":
        probes = [
            ("chrome", "/Applications/Google Chrome.app"),
            ("msedge", "/Applications/Microsoft Edge.app"),
        ]
    elif system == "Windows":
        roots = [os.environ.get(k, "") for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
        probes = []
        for r in roots:
            if r:
                probes.append(("chrome", str(Path(r) / "Google/Chrome/Application/chrome.exe")))
                probes.append(("msedge", str(Path(r) / "Microsoft/Edge/Application/msedge.exe")))
    else:
        probes = [("chrome", shutil.which("google-chrome") or ""), ("msedge", shutil.which("microsoft-edge") or "")]
    for channel, path in probes:
        if path and Path(path).exists():
            found.append((channel, path))
    return found


def launch(pw, headless: bool = False):
    cands = browser_candidates()
    if not cands:
        raise RuntimeError("크롬이나 엣지가 설치돼 있지 않습니다.")
    prof = profile_dir()
    prof.mkdir(parents=True, exist_ok=True)
    last = None
    for channel, _ in cands:
        try:
            ctx = pw.chromium.launch_persistent_context(
                str(prof), channel=channel, headless=headless, locale="ko-KR",
                viewport={"width": 1280, "height": 900},
            )
            say("browser", channel=channel)
            return ctx
        except Exception as e:  # 이미 같은 프로필 창이 열려 있는 경우 등
            last = e
    raise RuntimeError(f"브라우저를 열지 못했습니다: {str(last)[:200]}")


def all_frames(page):
    return [page.main_frame] + [f for f in page.frames if f != page.main_frame]


def find_editor(page, timeout: float = 30.0):
    """제목 영역이 있는 프레임. 예전 에디터는 mainFrame 안에, 새 에디터는 바깥에 있다."""
    end = time.time() + timeout
    while time.time() < end:
        for fr in all_frames(page):
            try:
                if fr.locator(".se-section-documentTitle").count() > 0:
                    return fr
            except Exception:
                continue
        time.sleep(0.5)
    return None


def dismiss_popups(page, rounds: int = 6) -> None:
    """'작성 중인 글이 있습니다' 는 취소(= 새 글), 도움말 패널은 닫는다."""
    for _ in range(rounds):
        acted = False
        for fr in all_frames(page):
            for sel in (".se-popup-button-cancel", ".se-help-panel-close-button"):
                try:
                    loc = fr.locator(sel).first
                    if loc.count() and loc.is_visible():
                        loc.click(timeout=2000)
                        acted = True
                        time.sleep(0.6)
                except Exception:
                    pass
        if not acted:
            time.sleep(0.5)
            # 한 번 더 조용한지 확인한 뒤 끝낸다
            if not any(
                _visible(fr, ".se-popup-button-cancel") for fr in all_frames(page)
            ):
                return


def _visible(fr, sel: str) -> bool:
    try:
        loc = fr.locator(sel).first
        return bool(loc.count() and loc.is_visible())
    except Exception:
        return False


def ensure_login(page, wait_seconds: int) -> bool:
    """로그인 페이지로 튕기면 학생이 직접 로그인하길 기다린다. 입력은 하지 않는다."""
    page.goto(WRITE_URL, wait_until="domcontentloaded")
    time.sleep(2)
    if LOGIN_HOST not in page.url:
        return True
    say("login_required", message="열린 창에서 네이버에 직접 로그인해 주세요. 보안 확인이 나오면 직접 풀어 주세요.",
        wait_seconds=wait_seconds)
    end = time.time() + wait_seconds
    while time.time() < end:
        if LOGIN_HOST not in page.url:
            time.sleep(2)
            page.goto(WRITE_URL, wait_until="domcontentloaded")
            time.sleep(2)
            return LOGIN_HOST not in page.url
        time.sleep(2)
    return False


# ---------------------------------------------------------------- 작성창 입력

def shot(page, name: str, outdir: Path) -> str:
    outdir.mkdir(parents=True, exist_ok=True)
    p = outdir / name
    try:
        page.screenshot(path=str(p))
    except Exception:
        return ""
    return str(p)


def count_images(fr) -> int:
    try:
        return fr.locator(".se-component.se-image").count()
    except Exception:
        return 0


def read_draft_count(page):
    for fr in all_frames(page):
        try:
            label = fr.evaluate(
                """() => { for (const n of document.querySelectorAll('[aria-label*="임시저장"]')) {
                    const m=(n.getAttribute('aria-label')||'').match(/임시저장.*?(\\d+)\\s*개/);
                    if (m) return parseInt(m[1],10);} return null; }"""
            )
            if isinstance(label, int):
                return label
        except Exception:
            continue
    return None


def type_title(page, fr, title: str) -> None:
    fr.locator(".se-section-documentTitle").first.click()
    time.sleep(0.4)
    page.keyboard.insert_text(title)


def goto_body(page, fr) -> None:
    loc = fr.locator(".se-section-text .se-text-paragraph").first
    if loc.count():
        loc.click()
    else:
        fr.locator(".se-section-text").first.click()
    time.sleep(0.4)


def bold_active(fr) -> bool:
    """굵게 상태. 툴바 버튼의 선택 표시를 먼저 보고, 없으면 브라우저 상태를 본다."""
    try:
        return bool(fr.evaluate(
            """() => {
              const b = document.querySelector('.se-bold-toolbar-button, .se-toolbar-item-bold button, button[class*="bold"]');
              if (b) {
                const t = ((b.className||'') + ' ' + ((b.parentElement||{}).className||'')).toLowerCase();
                if (b.getAttribute('aria-pressed') === 'true') return true;
                return /(^|\\s)(active|selected|se-is-selected|se-is-active|se-selected|is-active|is-selected)(\\s|$)/.test(t);
              }
              return document.queryCommandState('bold');
            }"""
        ))
    except Exception:
        return False


def set_bold(page, fr, want: bool) -> None:
    """지금 상태와 다를 때만 굵게 키를 누른다(두 번 눌러 거꾸로 되는 것을 막는다)."""
    time.sleep(0.2)  # 줄바꿈 직후에는 상태 표시가 늦게 바뀐다
    if bold_active(fr) != want:
        page.keyboard.press("ControlOrMeta+b")
        time.sleep(0.15)


def type_paragraph(page, fr, text: str) -> None:
    set_bold(page, fr, False)
    page.keyboard.insert_text(text)
    page.keyboard.press("Enter")
    page.keyboard.press("Enter")


def type_heading(page, fr, text: str) -> None:
    set_bold(page, fr, True)
    page.keyboard.insert_text(text)
    set_bold(page, fr, False)
    page.keyboard.press("Enter")


def insert_image(page, fr, path: Path) -> bool:
    before = count_images(fr)
    btn = fr.locator(".se-toolbar-item-image button").first
    if not btn.count():
        btn = fr.locator(".se-toolbar-item-image").first
    try:
        with page.expect_file_chooser(timeout=8000) as chooser:
            btn.click()
        chooser.value.set_files(str(path))
    except Exception as e:
        say("image_failed", file=path.name, reason=str(e)[:120])
        return False
    end = time.time() + 20
    while time.time() < end:
        if count_images(fr) > before:
            time.sleep(1.0)
            page.keyboard.press("ControlOrMeta+End")
            page.keyboard.press("Enter")
            return True
        time.sleep(0.5)
    say("image_failed", file=path.name, reason="사진이 작성창에 나타나지 않았습니다")
    return False


def click_save(page) -> bool:
    for fr in all_frames(page):
        for sel in ('button[class*="save_btn"]', 'button:has-text("저장")'):
            try:
                locs = fr.locator(sel)
                for i in range(locs.count()):
                    b = locs.nth(i)
                    label = (b.inner_text() or "").replace(" ", "")
                    if b.is_visible() and "발행" not in label and "예약" not in label and "저장" in label:
                        b.click(timeout=3000)
                        return True
            except Exception:
                continue
    return False


def wait_saved(page, baseline, timeout: float = 12.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        for fr in all_frames(page):
            try:
                text = fr.evaluate("() => document.body ? document.body.innerText : ''") or ""
            except Exception:
                continue
            flat = re.sub(r"\s+", "", text)
            if any(k in flat for k in ("임시저장되었습니다", "저장되었습니다", "저장완료")):
                return True
        now = read_draft_count(page)
        if now is not None and baseline is not None and now > baseline:
            return True
        time.sleep(0.4)
    return False


def cmd_draft(args) -> int:
    from playwright.sync_api import sync_playwright

    post = parse_post(Path(args.post).read_text(encoding="utf-8"))
    images = check_images(args.images or [])
    out = Path(args.out).expanduser()
    n_slots = sum(1 for b in post["blocks"] if b["type"] == "image")
    say("parsed", title=post["title"], blocks=len(post["blocks"]), photo_slots=n_slots, photos=len(images))

    with sync_playwright() as pw:
        ctx = launch(pw)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            if not ensure_login(page, args.login_wait):
                say("result", ok=False, code="login_timeout",
                    message="로그인이 끝나지 않아 멈췄습니다. 다시 시작하면 같은 창에서 이어집니다.")
                return 3
            say("logged_in")
            fr = find_editor(page)
            if fr is None:
                say("result", ok=False, code="editor_not_found", screenshot=shot(page, "editor_not_found.png", out),
                    message="글쓰기 화면을 찾지 못했습니다. 블로그가 아직 없거나 화면이 바뀌었을 수 있습니다.")
                return 4
            dismiss_popups(page)
            fr = find_editor(page, 10) or fr
            baseline = read_draft_count(page)

            type_title(page, fr, post["title"])
            goto_body(page, fr)
            img_i = 0
            placed = 0
            left_as_text = 0
            for b in post["blocks"]:
                if b["type"] == "p":
                    type_paragraph(page, fr, b["text"])
                elif b["type"] == "h":
                    type_heading(page, fr, b["text"])
                else:
                    if img_i < len(images):
                        ok = insert_image(page, fr, images[img_i])
                        img_i += 1
                        placed += 1 if ok else 0
                        if not ok:
                            left_as_text += 1
                            type_paragraph(page, fr, f"[사진 자리: {b['text']}]")
                    else:
                        left_as_text += 1
                        type_paragraph(page, fr, f"[사진 자리: {b['text']}]")
                time.sleep(0.2)

            clicked = click_save(page)
            saved = clicked and wait_saved(page, baseline)
            snap = shot(page, "after_save.png", out)
            say("result", ok=bool(saved), save_clicked=clicked, save_confirmed=bool(saved),
                photos_placed=placed, photo_slots_left_as_text=left_as_text, screenshot=snap,
                published=False,
                message=("임시저장까지 확인했습니다. 발행은 하지 않았습니다." if saved else
                         "임시저장 버튼 확인에 실패했습니다. 화면을 직접 확인해 주세요."))
            if args.hold > 0:
                time.sleep(args.hold)
            return 0 if saved else 2
        finally:
            ctx.close()


def cmd_login(args) -> int:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        ctx = launch(pw)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            if args.probe:
                page.goto(WRITE_URL, wait_until="domcontentloaded")
                time.sleep(3)
                on_login = LOGIN_HOST in page.url
                snap = shot(page, "login_probe.png", Path(args.out).expanduser())
                say("result", ok=True, opened_login_page=on_login, final_host=re.sub(r"^https?://([^/]+).*", r"\1", page.url),
                    screenshot=snap)
                return 0
            ok = ensure_login(page, args.login_wait)
            say("result", ok=ok, message="로그인이 확인됐습니다." if ok else "로그인이 끝나지 않았습니다.")
            return 0 if ok else 3
        finally:
            ctx.close()


def cmd_check(_args) -> int:
    info = {"python": platform.python_version(), "os": platform.system(), "profile_dir": str(profile_dir())}
    try:
        import playwright  # noqa: F401
        info["playwright"] = True
    except Exception:
        info["playwright"] = False
    info["browsers"] = [c for c, _ in browser_candidates()]
    info["ready"] = bool(info["playwright"] and info["browsers"])
    say("check", **info)
    return 0 if info["ready"] else 1


def cmd_parse(args) -> int:
    post = parse_post(Path(args.post).read_text(encoding="utf-8"))
    n = sum(1 for b in post["blocks"] if b["type"] == "image")
    imgs = check_images(args.images or [])
    say("parsed", title=post["title"], paragraphs=sum(1 for b in post["blocks"] if b["type"] == "p"),
        headings=sum(1 for b in post["blocks"] if b["type"] == "h"), photo_slots=n, photos=len(imgs),
        photo_slots_without_file=max(0, n - len(imgs)))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    p = sub.add_parser("parse")
    p.add_argument("post")
    p.add_argument("--images", nargs="*")
    p = sub.add_parser("login")
    p.add_argument("--probe", action="store_true")
    p.add_argument("--login-wait", type=int, default=300)
    p.add_argument("--out", default="./blog-shots")
    p = sub.add_parser("draft")
    p.add_argument("post")
    p.add_argument("--images", nargs="*")
    p.add_argument("--login-wait", type=int, default=300)
    p.add_argument("--hold", type=int, default=15, help="저장 뒤 창을 열어 두는 초")
    p.add_argument("--out", default="./blog-shots")
    args = ap.parse_args()
    try:
        return {"check": cmd_check, "parse": cmd_parse, "login": cmd_login, "draft": cmd_draft}[args.cmd](args)
    except ValueError as e:
        say("result", ok=False, code="bad_input", message=str(e))
        return 1
    except RuntimeError as e:
        say("result", ok=False, code="runtime", message=str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
