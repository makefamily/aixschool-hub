# -*- coding: utf-8 -*-
"""주제 맞춤 이미지(표지·배경)를 준비한다. 글자·로고·사람 얼굴이 없는 그림만 만든다.

사용(AI가 실행):
  python gen_images.py --dir <작업폴더> --template 08-poster --list        필요한 이미지와 설명을 images/prompts.json 에 쓰고 보여 준다(돈 안 든다)
  python gen_images.py --dir <작업폴더> --template 08-poster --run         Codex 이미지 생성으로 만든다(구독 한도를 쓴다. 학생 허락을 받은 뒤에만)
  python gen_images.py --dir <작업폴더> --template 08-poster --from-folder <사진 폴더>   학생 사진을 순서대로 cover, bg1, bg2, bg3 로 복사
  옵션: --only cover   (그 이미지만) / --model <이름> (넣지 않으면 학생 Codex 기본값)
Codex 안에서 일하고 있으면 --run 대신 prompts.json 의 설명으로 AI가 내장 이미지 기능을 직접 쓰고 images/ 에 저장해도 된다.
자동 재시도는 하지 않는다. 실패하면 이유만 알리고 멈춘다.
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys

# 임시 폴더를 작업 폴더 안으로(AI 보호 구역에서 시스템 임시 폴더 쓰기가 막히는 경우 대비) AIHUB_LOCAL_TMP
import os as _os, tempfile as _tf
_loc = _os.path.join(_os.getcwd(), '.tmp'); _os.makedirs(_loc, exist_ok=True)
_tf.tempdir = _loc; _os.environ['TMP'] = _os.environ['TEMP'] = _os.environ['TMPDIR'] = _loc

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import deck_templates as T  # noqa: E402

NO_TEXT = ("NO TEXT, letters, numbers, logos, brand marks or readable UI writing anywhere (screens show only abstract blurred shapes). "
           "NO people, NO human faces, NO hands or body parts.")


def prompts(v, slug, accent):
    bg = accent or "#D3151C"
    out = {}
    if slug == "09-editorial":
        out["cover"] = ("Cinematic, vivid 3D animated-film style (glossy, detailed, dramatic lighting). " + v["cover_scene"] +
                        " Subject in the upper-middle; keep the bottom 35% darker and visually simple for a headline added later.")
    elif slug == "08-poster":
        out["cover"] = ("Realistic editorial still-life photograph. " + v["cover_scene"] +
                        " One main object, standing in the LOWER 55%% of the frame. Background is a perfectly flat, seamless solid color studio backdrop (%s) "
                        "filling the whole frame; the TOP 45%% must be empty flat color for a headline." % bg)
        for j, scene in enumerate((v.get("bg_scenes") or [])[:3], 1):
            out["bg%d" % j] = "Realistic magazine-quality photograph, rich warm colors, shallow depth of field. " + scene
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--template", default="08-poster", choices=list(T.TEMPLATES))
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--from-folder")
    ap.add_argument("--only", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--timeout", type=int, default=1500)
    ap.add_argument("--brand-color", action="store_true")
    a = ap.parse_args()
    d = pathlib.Path(a.dir).resolve()
    need = T.IMAGES[a.template]
    if not need:
        print("이 템플릿(%s)은 이미지가 필요 없습니다." % a.template)
        return 0
    img = d / "images"
    img.mkdir(exist_ok=True)
    have = [k for k in need if any((img / ("%s.%s" % (k, e))).is_file() for e in ("png", "jpg", "jpeg", "webp"))]
    if a.from_folder:
        files = sorted(p for p in pathlib.Path(a.from_folder).iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"))
        if not files:
            print("사진 폴더에 이미지가 없습니다")
            return 1
        for k, f in zip(need, files):
            shutil.copy(f, img / (k + f.suffix.lower()))
            print("복사: %s -> %s" % (f.name, k))
        return 0
    deck = json.loads((d / "deck.json").read_text(encoding="utf-8"))
    v = deck.get("visuals") or {}
    brand = {}
    if (d / "brand.json").exists():
        brand = json.loads((d / "brand.json").read_text(encoding="utf-8"))
    p = prompts(v, a.template, brand.get("accent") if a.brand_color else None)
    todo = {k: p[k] for k in need if k in p and (not a.only or k in a.only.split(","))}
    if not a.only:
        todo = {k: x for k, x in todo.items() if k not in have}
    (img / "prompts.json").write_text(json.dumps({"no_text_rule": NO_TEXT, "images": p}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("필요한 이미지:", ", ".join(need), "/ 이미 있음:", ", ".join(have) or "없음")
    if a.list or not a.run:
        for k, x in todo.items():
            print("- %s: %s" % (k, x))
        return 0
    if not todo:
        print("만들 이미지가 없습니다.")
        return 0
    codex = shutil.which("codex")
    if not codex:
        print("Codex가 설치돼 있지 않습니다. 이미지 없는 배경이나 사진 폴더로 진행하세요.")
        return 4
    st = subprocess.run([codex, "login", "status"], capture_output=True, text=True)
    if st.returncode:
        print("Codex에 로그인돼 있지 않습니다. 이미지 없는 배경이나 사진 폴더로 진행하세요.")
        return 4
    raw = img / "raw"
    raw.mkdir(exist_ok=True)
    lines = ["%d) %s.png - %s" % (n, k, x) for n, (k, x) in enumerate(todo.items(), 1)]
    prompt = ("Use your built-in image generation tool to create %d portrait images (1024x1536 or larger, vertical) and save them in the current "
              "directory with exactly these names. %s\n\n" % (len(todo), NO_TEXT) + "\n\n".join(lines) +
              "\n\nAfter saving, print the absolute paths. Do not modify any other files.")
    cmd = [codex, "exec"] + (["-m", a.model] if a.model else []) + ["-s", "workspace-write", "--skip-git-repo-check", "-"]
    log = raw / "codex.log"
    with log.open("w", encoding="utf-8") as fh:
        try:
            done = subprocess.run(cmd, input=prompt, cwd=raw, stdout=fh, stderr=subprocess.STDOUT, text=True, timeout=a.timeout)
            code = done.returncode
        except subprocess.TimeoutExpired:
            code = -1
    miss = []
    for k in todo:
        src = raw / ("%s.png" % k)
        if src.is_file() and src.stat().st_size > 10000:
            shutil.copy(src, img / ("%s.png" % k))
            print("만들어짐: images/%s.png" % k)
        else:
            miss.append(k)
    if miss:
        print("이미지 생성 실패: %s (종료 %s). 자동으로 다시 시도하지 않습니다." % (", ".join(miss), code))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
