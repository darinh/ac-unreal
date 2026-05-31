# pipeline/sim-core

**Standalone test rig** for the Phase 2 simulation core
(`Source/AcUnreal/{Public,Private}/SimCore/`). Same dual-build pattern
as `coord-transform/` and `asset-ingest/`: the SAME `.cpp` files that
UBT compiles into the UE module are also built into a standalone
`cl.exe` executable here, so movement-math regressions fail fast
independent of UE build state.

## Why a standalone rig

1. **Independence.** UBT failures can mask math regressions; this rig
   isolates the sim core.
2. **Determinism.** The sim is pure C++17 + IEEE-754; the standalone
   rig is the natural place to assert "same inputs → bit-identical
   state" — which is the brief invariant for re-simulatable movement.
3. **Speed.** cl.exe build + test run is sub-second; UE module build
   is tens of seconds.

## Usage

```powershell
.\build.ps1
```

Exits 0 on all-pass, non-zero on any failure. Output goes to `build/`
(gitignored).

## Coverage

See `tests/SimCoreTests.cpp`. Tests cover:

- **Determinism**: 600-tick varied input sequence runs 3× and produces
  bit-identical final state.
- **Gravity arc**: drop from rest, position matches semi-implicit Euler
  expectation; Vz = g·t (constant-accel result).
- **Jump arc**: airtime ≈ 2V₀/|g|; peak height ≈ V₀²/(2|g|); lands at
  Z=0 with Vz=0 and `bOnGround=true`.
- **Friction decay**: no input → velocity decays as `V₀ · friction^N`
  (geometric).
- **Speed caps**: walk/run/backward/sidestep produce ACE-derived
  speeds (`312, 400, 312×0.65, 125 cm/s`).
- **Yaw rotation**: facing east + forward input → +Y velocity.
- **Action stamp wrap**: increments masked to `0x7FFF` per ACE
  MotionInterp.cs:789-824.
- **Fixed-step accumulator**: variable frame dt over 10 s fires ~300
  ticks (= 10s @ 30Hz, ±3 for end-of-loop alignment).
- **Accumulator catch-up cap**: 60 s frame fires ≈ MaxAccumulator/dt
  ticks, not 1800 (spiral-of-death guard).
- **Accumulator alpha**: in [0, 1]; equals 0.5 after half a tick.
- **Accumulator bad input**: NaN / negative / zero dt → 0 ticks, no UB.

If you change anything in `SimCore/*.{h,cpp}`, run this first.
