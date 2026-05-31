# pipeline/coord-transform

**Standalone test rig** for the canonical AC↔UE coordinate transform.

This is NOT a separate implementation. The transform's only source files
live in:

```
Source/AcUnreal/Public/CoordCore/CoordTransform.h
Source/AcUnreal/Private/CoordCore/CoordTransform.cpp
```

…where UnrealBuildTool picks them up as part of the `AcUnreal` module.
The script in this directory (`build.ps1`) compiles those **same files**
with `cl.exe` directly under vcvars64 — no UE, no UBT — and runs the
round-trip tests in `tests/CoordTransformTests.cpp`.

## Why a standalone rig at all?

1. **Independence from UE build state.** UBT failures can mask math
   regressions; this rig fails fast for math-only mistakes.
2. **Faster iteration.** cl.exe build of the core + tests is sub-second;
   a UE module build is tens of seconds at minimum.
3. **CI-friendly.** If we ever wire CI without an Epic UE install
   (e.g., a separate parity-math job), this rig works on any Windows box
   with VS Build Tools installed. The UE module build can come later
   in the pipeline.

## Usage

```powershell
.\build.ps1
```

Exits 0 on all-pass, non-zero if any test fails. Output goes to
`pipeline/coord-transform/build/` (gitignored).

## Coverage

See `tests/CoordTransformTests.cpp`. Covers:

- Point round-trip across all 4 (handedness × axis-swap) conventions.
- Vector round-trip across all 4 conventions.
- Unit-scale correctness for default and non-default AC unit.
- Landblock ID encode/decode round-trip.
- `LandblockIdForAcPoint` for inside, edge, and out-of-world points.
- Landblock origin consistency: a point inside a landblock resolves
  back to the same landblock when re-queried from `AcOriginOfLandblock`.
- `IsAcPointInsideWorld` boundary behavior.
- Handedness preservation: regardless of AC handedness convention,
  the transform's output basis vectors satisfy left-handed UE
  (X×Y = −Z).
- Degenerate-input smoke check (AC unit = 0 doesn't crash).

If you change anything in `CoordTransform.{h,cpp}`, run this first.
