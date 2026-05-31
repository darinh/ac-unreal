#!/usr/bin/env python3
"""
test_renders.py - automated, evaluable checks on render PNGs so render quality
is a pass/fail FORMULA, not a judgment call.

Encodes the failure modes this project actually hit:
  - pure black / void-dominated (broken geometry, camera in void, lights off)
  - magenta error-material (M_HotPinkDiagnostic / failed material binding)
  - flat single-colour (untextured WorldGridMaterial / lost texture bindings)
  - blown white (over-exposed)
and asserts the positive signals of a real textured room (content, variety).

Usage:
  python test_renders.py <image.png> [<image2.png> ...]      # absolute checks
  python test_renders.py --baseline-save base.json <img>...  # record metrics
  python test_renders.py --baseline base.json <img>...       # + regression check
Exit code: 0 = all pass, 1 = any fail.  Prints a per-image, per-check table.
"""
import sys, os, json
from PIL import Image

# ---- absolute thresholds (the "formula"; tune with your eyes once) ----------
T = dict(
    mean_lum_min=15,        # below -> black / nearly black
    mean_lum_max=245,       # above -> blown white
    content_frac_min=0.45,  # fraction of non-near-black pixels; below -> void-dominated
    magenta_frac_max=0.015, # error-material magenta
    color_std_min=14,       # per-channel spread; below -> flat untextured fill
)
# regression tolerances vs a saved baseline
REG = dict(mean_lum=45.0, content_frac=0.20, magenta_frac=0.02, color_std=10.0)


def metrics(path):
    im = Image.open(path).convert("RGB")
    im = im.resize((160, 90))  # downsample for speed; structure preserved
    px = list(im.getdata())
    n = len(px)
    lums = [0.299*r + 0.587*g + 0.114*b for (r, g, b) in px]
    mean_lum = sum(lums) / n
    content = sum(1 for L in lums if L > 12) / n
    magenta = sum(1 for (r, g, b) in px if r > 170 and b > 170 and g < 100) / n
    # per-channel std as a flatness measure
    mr = sum(p[0] for p in px)/n; mg = sum(p[1] for p in px)/n; mb = sum(p[2] for p in px)/n
    var = sum((p[0]-mr)**2 + (p[1]-mg)**2 + (p[2]-mb)**2 for p in px) / (3*n)
    color_std = var ** 0.5
    # informational palette signals (room-dependent; not hard-failed)
    brown = sum(1 for (r, g, b) in px if r > g >= b and (r-b) > 18 and 35 < r < 170) / n
    blue = sum(1 for (r, g, b) in px if b > r and (b-r) > 10 and b > 30) / n
    return dict(mean_lum=round(mean_lum, 1), content_frac=round(content, 3),
                magenta_frac=round(magenta, 4), color_std=round(color_std, 1),
                brown_frac=round(brown, 3), blue_frac=round(blue, 3))


def check_absolute(m):
    fails = []
    if m["mean_lum"] < T["mean_lum_min"]: fails.append(f"BLACK (mean_lum {m['mean_lum']} < {T['mean_lum_min']})")
    if m["mean_lum"] > T["mean_lum_max"]: fails.append(f"BLOWN (mean_lum {m['mean_lum']} > {T['mean_lum_max']})")
    if m["content_frac"] < T["content_frac_min"]: fails.append(f"VOID (content {m['content_frac']} < {T['content_frac_min']})")
    if m["magenta_frac"] > T["magenta_frac_max"]: fails.append(f"ERROR-MAT (magenta {m['magenta_frac']} > {T['magenta_frac_max']})")
    if m["color_std"] < T["color_std_min"]: fails.append(f"FLAT (color_std {m['color_std']} < {T['color_std_min']})")
    return fails


def check_regression(m, base):
    fails = []
    for k, tol in REG.items():
        if k in base:
            d = abs(m[k] - base[k])
            if d > tol: fails.append(f"REGRESSED {k}: {base[k]} -> {m[k]} (Δ{d:.2f} > {tol})")
    return fails


def main():
    args = sys.argv[1:]
    base = None; base_save = None
    if args and args[0] == "--baseline-save":
        base_save = args[1]; args = args[2:]
    elif args and args[0] == "--baseline":
        base = json.load(open(args[1])); args = args[2:]
    if not args:
        print(__doc__); return 2

    all_ok = True; saved = {}
    print(f"{'image':46} {'mean':>5} {'cont':>5} {'mgta':>6} {'cstd':>5} {'brn':>5} {'blu':>5}  result")
    for p in args:
        if not os.path.exists(p):
            print(f"{os.path.basename(p):46} MISSING"); all_ok = False; continue
        m = metrics(p)
        fails = check_absolute(m)
        if base is not None:
            key = os.path.basename(p)
            if key in base: fails += check_regression(m, base[key])
        saved[os.path.basename(p)] = m
        status = "PASS" if not fails else "FAIL: " + "; ".join(fails)
        if fails: all_ok = False
        print(f"{os.path.basename(p):46} {m['mean_lum']:5} {m['content_frac']:5} {m['magenta_frac']:6} {m['color_std']:5} {m['brown_frac']:5} {m['blue_frac']:5}  {status}")

    if base_save:
        json.dump(saved, open(base_save, "w"), indent=2)
        print(f"\nbaseline written: {base_save}")
    print(f"\n{'ALL PASS' if all_ok else 'FAILURES PRESENT'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
