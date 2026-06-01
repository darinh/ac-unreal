# 0023 - Asset cooking, packaging & distribution (legal-constrained cook)
Status: Proposed   Date: 2026-05-31

## Context
Category XV lists packaging/distribution/CI as `[OPEN]`. This project has a hard
IP constraint that shapes packaging more than performance does: **no AC-derived
assets may be committed or redistributed** — each user extracts from their **own**
retail DATs (LEGAL.md; ADR-0003). So a distributable UE client **cannot** bundle
the cooked AC content (meshes/textures/audio) the way a normal UE game ships its
`Content/`. The retail client shipped baked assets in the DAT files + an installer;
we cannot lawfully mirror that distribution model.

## Candidate (proposed, not decided)
Split the package into **engine/original content** vs **user-generated AC content**:
- **Distribute:** the UE app (engine content, *our* original materials/Blueprints/
  C++), plus the **extraction pipeline** (`acdat` + the `pipeline/ue-import`
  importers) and setup docs.
- **User-side generate:** on install / first run, the user points the pipeline at
  their own `C:\Turbine\Asheron's Call` DATs; it extracts + imports AC-derived
  assets into a **local, never-redistributed** `Content/Academy/...` (the same
  grandfather-clause area, kept out of the shipped package and git).
- **Cook scope:** cook only non-AC-derived assets into the package; AC-derived
  content is cooked **locally** after extraction (a post-install cook step, or a
  loose/late-imported content path). CI builds and tests must run **without** any
  AC DATs present (use synthetic/fixture assets), so CI never touches AC IP.

## Assumptions it depends on
- A1 [DESIGN]: UE can ship a runnable app whose AC `Content/` is populated
  post-install (loose cooked content, a user content dir, or a first-run cook).
- A2 [DOC]: LEGAL.md / ADR-0003 remain the governing constraint (no committed/
  shipped AC assets; grandfather area is local-only).

## Evidence required before Accepted
- A spike: package the app with **zero** AC content, run the extraction+import on a
  clean machine, and confirm the room renders from user-supplied DATs only.
- Confirm UE's cook/pak path supports the post-install content population chosen.

## Failure mode if an assumption is false
- If UE requires AC content present at cook time, the "ship empty + populate later"
  model breaks and we must redesign (e.g., a separate content-cook tool the user
  runs locally). Shipping AC content to dodge this would violate LEGAL.md — not an
  option.

## Alternatives still live
- A user-run **content-cook tool** (separate from the game) that produces a local
  pak from their DATs, which the game then mounts.
- Loose (uncooked) AC content for dev; decide the shipped form later.

## Disposition
**ADD** (no retail analogue): the retail client shipped baked assets; our legal
constraint forces a *user-side extraction + local cook* step that AC never had.

## Acceptance test
- Clean-machine install with only the user's DATs -> pipeline runs -> the first
  room renders; the distributed package and CI contain **no** AC-derived assets.

## Relationships
LEGAL.md / ADR-0003 (governing constraint); ADR-0001 (acdat extraction);
ADR-0009/0014 (what gets cooked — streamed cells, Nanite-readiness).
