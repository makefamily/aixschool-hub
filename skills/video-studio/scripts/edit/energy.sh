#!/usr/bin/env bash
# energy.sh: how dynamic a video is, in numbers. "다이내믹하다" is mostly cut rate and never standing still.
#
#   bash energy.sh video.mp4 [--mode dynamic|calm] [--endcard SEC]
#
# cuts/10s   hard scene changes per 10 s (ffmpeg scdet, threshold 10)
# motion     mean luma difference between consecutive frames at 30 fps, 320 px wide (0-255 scale)
# still%     share of frames that barely change (difference < 0.3)
# longest    longest run of near-still frames, in seconds (the end card is excluded with --endcard)
#
# Targets (--mode dynamic, the default), fitted 2026-09-28 to films the user called dynamic vs. flat:
#   liked:    one-line showreel v2  cuts 5.3  motion 7.6  still 3%   longest 0.2s  end card 0.0s
#             launch (nahid) v2     cuts 3.7  motion 5.0  still 20%  longest 0.3s  end card 0.0s
#             self-intro v3         cuts 5.3  motion 4.9  still 27%  longest 0.4s  end card 0.3s
#   flat:     live samples v1       cuts 0-4  motion 0.9-6.8  still 26-52%  longest 0.8-1.4s  end card up to 2.1s
#   Dynamic is not mainly cut count: it is never holding still (longest still, moving end card) plus motion.
#   cuts/10s >= 3.5, motion >= 4.5, still% <= 30, longest still <= 0.5 s, end card <= 1.0 s
# --mode calm only reports (explainers, lullabies, UI loops the user asked to keep calm).
set -euo pipefail
f="$1"; shift || true
mode=dynamic; endcard=1.0
while [ $# -gt 0 ]; do case "$1" in --mode) mode="$2"; shift 2;; --endcard) endcard="$2"; shift 2;; *) shift;; esac; done
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
ffmpeg -nostdin -v error -i "$f" -vf "scale=480:-2,scdet=threshold=10,metadata=print:file=$t/cut.txt" -an -f null -
ffmpeg -nostdin -v error -i "$f" -vf "fps=30,scale=320:-2,format=gray,tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=$t/e.txt" -an -f null -
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
cuts=$(grep -c "lavfi.scd.time" "$t/cut.txt" || true)
grep -o "YAVG=[0-9.]*" "$t/e.txt" | cut -d= -f2 > "$t/v.txt"
python3 - "$f" "$cuts" "$dur" "$t/v.txt" "$mode" "$endcard" <<'P'
import sys
f, cuts, dur, p, mode, endcard = sys.argv[1], int(sys.argv[2] or 0), float(sys.argv[3]), sys.argv[4], sys.argv[5], float(sys.argv[6])
v = [float(x) for x in open(p) if x.strip()]
body = v[:max(1, len(v) - int(endcard * 30))]          # the end card may hold still
still = sum(1 for x in v if x < 0.3) / len(v) * 100
run = best = 0
for x in body:
    run = run + 1 if x < 0.3 else 0; best = max(best, run)
tail = 0
for x in reversed(v):
    if x < 0.3: tail += 1
    else: break
c10 = cuts / dur * 10
print(f"{f}\n  {dur:.1f}s  cuts/10s={c10:.1f}  motion={sum(v)/len(v):.2f}  still%={still:.0f}  longest still={best/30:.1f}s  end card={tail/30:.1f}s")
if mode == 'dynamic':
    m = sum(v) / len(v)
    checks = [('cuts/10s >= 3.5', c10 >= 3.5), ('motion >= 4.5', m >= 4.5), ('still% <= 30', still <= 30),
              ('longest still <= 0.5s', best / 30 <= 0.5), ('end card <= 1.0s', tail / 30 <= 1.0)]
    for name, ok in checks: print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    fails = sum(1 for _, ok in checks if not ok); print(f"  ENERGY {'PASS' if not fails else f'FAIL={fails}'}")
    sys.exit(1 if fails else 0)
P
