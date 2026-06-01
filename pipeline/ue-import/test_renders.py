#!/usr/bin/env python3
"""
test_renders.py - automated, evaluable checks on render PNGs so render quality
is a pass/fail FORMULA, not a judgment call.

Encodes the failure modes this project actually hit:
  - pure black / void-dominated (broken geometry, camera in void, lights off)
  - magenta error-material (M_HotPinkDiagnostic / failed material binding)
  - flat single-colour (untextured WorldGridMaterial / lost texture bindings)
  - blown white (over-exposed)
  - SKY-LEAK: blue atmosphere showing through a gap/opening (a NoPos portal into a
    cell that is not present, or missing geometry). NOT black, so the black/void
    checks miss it -- this is the "blue sky through the ceiling" defect.
and asserts the positive signals of a real textured room (content, variety).

The MANIFEST mode closes a hole the per-image checks cannot: a single passing
render proves only that ONE angle looks fine -- it does NOT prove walls + floor +
ceiling COEXIST. Step 0/1's acceptance bar is "the whole room shell renders from a
consistent set of fixed views" (see render_firstroom_sweep.ps1). Manifest mode
requires ALL six named views to be present AND each to pass, so you cannot "pass"
with only the floor in frame.

Usage:
  python test_renders.py <image.png> [<image2.png> ...]      # absolute checks
  python test_renders.py --baseline-save base.json <img>...  # record metrics
  python test_renders.py --baseline base.json <img>...       # + regression check
  python test_renders.py --manifest <sweep_dir>              # require+check all 6 views
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
    sky_frac_max=0.30,      # MANIFEST-mode: fraction of sky-blue pixels above this
                            # = atmosphere leaking through a gap (indoor views only)
)
# regression tolerances vs a saved baseline
REG = dict(mean_lum=45.0, content_frac=0.20, magenta_frac=0.02, color_std=10.0)

# The fixed-camera sweep that proves the shell coexists (render_firstroom_sweep.ps1).
# A view name maps to the surface it must show; ALL must be present in a manifest.
EXPECTED_VIEWS = ("wall_n", "wall_e", "wall_s", "wall_w", "ceiling", "floor")


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
    # sky-leak: bright, blue-dominant pixels (the SkyAtmosphere through a gap).
    # blue clearly above red and green, and not dark -> reads as open sky, not stone.
    sky = sum(1 for (r, g, b) in px if b > 110 and b > r + 25 and b > g + 12) / n
    # informational palette signals (room-dependent; not hard-failed)
    brown = sum(1 for (r, g, b) in px if r > g >= b and (r-b) > 18 and 35 < r < 170) / n
    blue = sum(1 for (r, g, b) in px if b > r and (b-r) > 10 and b > 30) / n
    return dict(mean_lum=round(mean_lum, 1), content_frac=round(content, 3),
                magenta_frac=round(magenta, 4), color_std=round(color_std, 1),
                sky_frac=round(sky, 3), brown_frac=round(brown, 3), blue_frac=round(blue, 3))


def check_absolute(m, sky=False):
    fails = []
    if m["mean_lum"] < T["mean_lum_min"]: fails.append(f"BLACK (mean_lum {m['mean_lum']} < {T['mean_lum_min']})")
    if m["mean_lum"] > T["mean_lum_max"]: fails.append(f"BLOWN (mean_lum {m['mean_lum']} > {T['mean_lum_max']})")
    if m["content_frac"] < T["content_frac_min"]: fails.append(f"VOID (content {m['content_frac']} < {T['content_frac_min']})")
    if m["magenta_frac"] > T["magenta_frac_max"]: fails.append(f"ERROR-MAT (magenta {m['magenta_frac']} > {T['magenta_frac_max']})")
    if m["color_std"] < T["color_std_min"]: fails.append(f"FLAT (color_std {m['color_std']} < {T['color_std_min']})")
    # SKY-LEAK is only meaningful for indoor views (manifest mode); opt-in via `sky`.
    if sky and m["sky_frac"] > T["sky_frac_max"]: fails.append(f"SKY-LEAK (sky {m['sky_frac']} > {T['sky_frac_max']})")
    return fails


def check_regression(m, base):
    fails = []
    for k, tol in REG.items():
        if k in base:
            d = abs(m[k] - base[k])
            if d > tol: fails.append(f"REGRESSED {k}: {base[k]} -> {m[k]} (Δ{d:.2f} > {tol})")
    return fails


HDR = (f"{'image':28} {'mean':>5} {'cont':>5} {'mgta':>6} {'cstd':>5} "
       f"{'sky':>5} {'brn':>5} {'blu':>5}  result")


def row(name, m, status):
    return (f"{name:28} {m['mean_lum']:5} {m['content_frac']:5} {m['magenta_frac']:6} "
            f"{m['color_std']:5} {m['sky_frac']:5} {m['brown_frac']:5} {m['blue_frac']:5}  {status}")


def run_manifest(sweep_dir):
    """Require ALL EXPECTED_VIEWS present in sweep_dir and each to pass absolute +
    sky-leak checks. Proves walls+floor+ceiling coexist, not just one angle."""
    print(f"MANIFEST: {sweep_dir}  (require all {len(EXPECTED_VIEWS)} views)")
    print(HDR)
    all_ok = True
    for view in EXPECTED_VIEWS:
        path = os.path.join(sweep_dir, f"{view}.png")
        if not os.path.exists(path):
            print(f"{view:28} {'MISSING - view not rendered (coexistence FAIL)':>0}")
            all_ok = False
            continue
        m = metrics(path)
        fails = check_absolute(m, sky=True)
        status = "PASS" if not fails else "FAIL: " + "; ".join(fails)
        if fails: all_ok = False
        print(row(view, m, status))
    print(f"\n{'MANIFEST PASS (room shell coexists)' if all_ok else 'MANIFEST FAIL'}")
    return 0 if all_ok else 1


def main():
    args = sys.argv[1:]
    if args and args[0] == "--manifest":
        if len(args) < 2:
            print("--manifest needs a sweep directory"); return 2
        return run_manifest(args[1])

    base = None; base_save = None
    if args and args[0] == "--baseline-save":
        base_save = args[1]; args = args[2:]
    elif args and args[0] == "--baseline":
        base = json.load(open(args[1])); args = args[2:]
    if not args:
        print(__doc__); return 2

    all_ok = True; saved = {}
    print(HDR)
    for p in args:
        if not os.path.exists(p):
            print(f"{os.path.basename(p):28} MISSING"); all_ok = False; continue
        m = metrics(p)
        # In single-file mode sky-leak is opt-out (a lone view may be outdoor);
        # the manifest mode is where the indoor sky-leak gate is enforced.
        fails = check_absolute(m, sky=False)
        if base is not None:
            key = os.path.basename(p)
            if key in base: fails += check_regression(m, base[key])
        saved[os.path.basename(p)] = m
        status = "PASS" if not fails else "FAIL: " + "; ".join(fails)
        if fails: all_ok = False
        print(row(os.path.basename(p), m, status))

    if base_save:
        json.dump(saved, open(base_save, "w"), indent=2)
        print(f"\nbaseline written: {base_save}")
    print(f"\n{'ALL PASS' if all_ok else 'FAILURES PRESENT'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
