# Finding: cell-shell "no walls" was corrupt mesh bounds → frustum-cull (RESOLVED)

**Date:** 2026-06-01. **Status:** root cause confirmed; **system-wide fix already on
`main`** (via `d3995d9`); this note adds the durable audit/repair tooling + a
build-time guard so it cannot silently recur.

## Symptom
Only the first room (`0x860201AD`) showed walls/floor/ceiling in the editor;
"almost every other room" had no shell. It looked like a one-room custom fix that
wasn't applied everywhere.

## Root cause (data, not a per-room thing)
- The acdat-exported geometry is **clean** for every cell (verified the OBJ
  vertices of corrupt cells — all normal, e.g. `X[-500,500] Y[-500,500] Z[0,600]`).
- The **UE mesh build left corrupt bounding boxes** (`NaN` / `Inf` / `~3.7e48`) on
  a large fraction of cell meshes. A mesh with corrupt bounds is **frustum-culled**
  by UE → the room renders no shell. [DATA: `audit_cell_bounds.py` on the
  pre-fix state showed 224/568 corrupt: 117 `nan_inf` + 107 `huge`.]
- The first room rendered only because it had been rebuilt through the **fresh**
  `build_static_mesh` path, which computes valid bounds. The corrupt cells were
  stale leftovers from an older/in-place build that were never rebuilt.
- Rebuild via the fresh path is **deterministic and reliable** at producing
  finite bounds (verified by rebuilding corrupt cells repeatedly).

## Current state on `main` (verified `313258f`)
`audit_cell_bounds.py` → **567 finite / 1 zero / 0 nan-or-huge.** The other agent's
`d3995d9` ("skip NoPos portals across all stale cells") rebuilt 430 cells and, as a
side effect of the fresh rebuild, fixed the corrupt bounds system-wide. The single
zero-bounds cell `0x860202D1` is **legitimately empty** — its OBJ has 8 verts but
**0 faces** (an all-portal connector cell whose only polygons were `NoPos` portals,
correctly skipped per ADR-0008). Zero bounds is correct there; nothing to render.
**The cell-shell issue is resolved.**

## Prevention added here (so it cannot silently recur)
1. **Build-time bounds validation** in both build paths: `import_academy.py`
   `build_static_mesh` and `import_statics.py` `build_setup_mesh` log an ERROR if a
   mesh comes out of `build_from_static_mesh_descriptions` with NaN/Inf/~1e48
   bounds (`v == v and abs(v) < 1e7`). **This is ADVISORY only** — the asset is
   still saved (one ERROR line is easy to miss in a bulk build), so the
   authoritative gate is `audit_cell_bounds.py`. **Scope note:** this bounds check
   catches the **culled-shell** class (NaN/Inf/huge) — it does **NOT** catch a
   *collapsed* mesh, which has *finite* (~0..800) bounds. Collapsed/stale content
   is caught by (2), not this.
2. **Stale-detection guard** in `build_setup_mesh`: it previously did
   `if does_asset_exist: return load_asset` — silently reusing a stale cached
   asset across re-imports (review follow-up #1). A re-exported OBJ (e.g. after a
   placement fix that *un-collapses* a prop) was ignored, because a collapsed mesh
   has *finite* bounds. It now reuses an existing asset only if its bounds are
   finite **AND** it was built from the **same source OBJ** (sha1 stored as an
   asset metadata tag) — a changed OBJ forces a fresh rebuild. (This is the real
   fix for the finite-but-stale class the bounds check in (1) cannot see.)
3. **Reusable audits** (run after ANY bulk cell/setup operation — the gate):
   - `pipeline/ue-import/audit_cell_bounds.py` — per-cell bounds health (finite/nan/huge/zero).
   - `pipeline/ue-import/audit_cells.py` — per-cell wiring (actor→mesh→tris→materials).
   - `pipeline/ue-import/repair_cell_bounds.py` — idempotent: rebuild any corrupt-bounds cell.

## Other review follow-ups
- **#3 ExportSetup anchor skip (DONE, code):** `ExportSetup` now skips GfxObj
  `0x010001EC` (the empty anchor/locator part ACViewer omits), matching `ExportNpc`.
  No asset re-export needed — the anchor part is invisible, so the 18 rebuilt
  setups already render clean; this only cleans future OBJ exports.
- **#2 ExportNpc UVs[0] (DEFERRED → Step 4):** `ExportNpc` emits one `vt` per
  vertex from `UVs[0]`, ignoring per-corner `PosUVIndices` (the bug already fixed
  in `ExportEnvCell`/`ExportSetup`). NPCs are not rendered yet; fixing it needs a
  UV-emission restructure + build/verify, so it stays a Step-4 item.

## Process finding: worktree friction for this project
UE/acdat work in a git worktree hits three gaps the main checkout hides — recorded
so the next agent doesn't lose time:
1. **Compiled C++ module** (`Binaries/`) is gitignored → UE refuses to load the
   `AcUnreal` module in a fresh worktree ("Incompatible or missing module"). Copy
   `main`'s `Binaries/` into the worktree.
2. **`acdat` won't build** — its `.csproj` references `..\..\..\ACE` (a sibling
   repo), which only resolves from the main checkout. Workaround: a junction
   `<repo>/.claude/worktrees/ACE -> <ACE repo>`. **Recommended real fix:** make the
   ACE reference robust (e.g. a `Directory.Build.props` with a configurable ACE
   path) so acdat builds from any worktree.
3. **Generated intermediates** (`pipeline/**/out/` OBJs) are gitignored → not in a
   fresh worktree, so asset rebuilds need them copied or regenerated (which needs
   acdat → see #2).
