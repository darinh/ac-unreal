# 0003 - No AC-derived assets committed; users supply their own DATs
Status: Accepted   Date: 2026-05-30

## Context
Asheron's Call content is owned by its rights holders (see
[LEGAL.md](../../../LEGAL.md)). Committing extracted models/textures/world data
(as binaries or derived OBJ/PNG/JSON/UAsset) creates takedown and
publishability risk and is not necessary: the pipeline can regenerate assets
from a user-supplied client install.

## Decision
No AC-derived assets are committed. Extraction output lives only in git-ignored
`pipeline/**/out/`. Committed `samples/` is limited to tiny technical fixtures
needed to test the *pipeline* (e.g. a few-vertex layout), never bulk content.
Reference screenshots stay outside the repo. Each user extracts from DATs they
legally own.

## Consequences
- Reviewers/CI need their own DATs to regenerate assets; the repo stays clean and publishable-adjacent.
- **Known conflict to resolve (grandfather clause):** prior commits already
  track AC-derived content in **two** places: ~1,364 `Content/Academy/**`
  UAssets/UMaps (some via Git LFS), *and* bulk `pipeline/dat-extract/samples/`
  (`academy_8602_layout.json` ~274 KB, `academy_8602_statics.json` ~221 KB,
  `academy_8602_lights.json`, `academy_8602_npcs.json`, `cell_860201AD.obj/.mtl`,
  `textures/*.png`). Per LEGAL.md current-state rules: no *new* AC content;
  existing is grandfathered and may be *updated*; full removal + history scrub
  is a **pending decision** (strict purge vs. accept-with-grandfather), to be
  recorded as its own ADR when the user calls it. Do not purge unilaterally.

## Alternatives
- Commit assets for convenience: rejected (legal risk; LEGAL.md posture).
- Git LFS for assets: rejected for AC-derived content (same IP problem, just larger).
