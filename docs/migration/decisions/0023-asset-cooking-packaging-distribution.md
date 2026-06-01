# 0023 - Asset cooking, packaging & distribution (legal-constrained cook)
Status: Proposed   Date: 2026-06-01

## Context
Category XV lists packaging/distribution/CI as `[OPEN]`. The governing constraint
is IP, not performance: **no AC-derived assets may be committed or redistributed
going forward** — each user extracts from their **own** retail DATs [DOC:
LEGAL.md:23-32; ADR-0003]. A retail install contains DAT **content databases**
(models, textures, world/spatial data, etc.) [DATA: methodology §1]; how the retail
client was *distributed* (installer, etc.) is `[COMMUNITY-VERIFY]` and not needed
here. We cannot mirror a "ship the baked assets" distribution model **under this
repo's LEGAL.md posture** (LEGAL.md is a project posture, **not legal advice** —
LEGAL.md:81-82).

**Current-state nuance (do NOT invert):** the **grandfather clause** covers
AC-derived `Content/Academy/**` that is **already committed to git** (~1,364
UAssets/UMaps, some via Git LFS); full removal + history scrub is a **pending
decision** [DOC: LEGAL.md:36-43 "Current state"; ADR-0003]. The **local-only,
git-ignored** location for freshly-extracted assets is **`pipeline/**/out/`** [DOC:
LEGAL.md:28] — NOT the Academy tree.

## Candidate (proposed, not decided)
Split the package into **engine/original content** vs **user-generated AC content**:
- **Distribute:** the UE app (engine content, *our* original materials/Blueprints/
  C++) + the extraction pipeline (`acdat` + `pipeline/ue-import`) + setup docs.
- **User-side generate:** on install / first run, the user points the pipeline at
  their own DATs; it extracts into the git-ignored `pipeline/**/out/`, then imports
  into UE content. New AC-derived content must NOT be written to a *tracked* path
  (that would violate ADR-0003); targeting `Content/Academy/**` is gated on the
  pending purge/gitignore decision (ADR-0003) being resolved first.
- **Cook scope:** cook only non-AC-derived assets into the shipped package; AC
  content is populated locally post-install. **CI builds + tests must run without
  any AC DATs present** (synthetic/fixture assets), so CI never touches AC IP.

## Assumptions it depends on
- A1 [DESIGN]: UE can ship a runnable app whose AC content is populated
  post-install (loose cooked content / a user content dir / a first-run cook).
- A2 [DOC]: LEGAL.md / ADR-0003 remain governing; the grandfathered
  (already-committed) `Content/Academy/**` purge is a separate pending decision.

## Evidence required before Accepted
- A spike: package with **zero** AC content, run extraction+import on a clean
  machine, confirm the room renders from user DATs only; confirm UE's cook/pak path
  supports the chosen post-install population.

## Failure mode if an assumption is false
- If UE requires AC content present at cook time, "ship empty + populate later"
  breaks (redesign to a user-run content-cook tool). Shipping AC content to dodge
  this would violate LEGAL.md — not an option.

## Alternatives still live
- A user-run content-cook tool (separate from the game) producing a local pak the
  game mounts.
- Loose (uncooked) AC content for dev; decide the shipped form later.

## Disposition
**ADD** (no retail analogue under this repo's posture): a user-side extraction +
local population step AC's distribution did not require.

## Acceptance test
- Clean-machine install with only the user's DATs -> pipeline runs -> first room
  renders; the distributed package and CI contain **no** AC-derived assets.

## Relationships
LEGAL.md / ADR-0003 (governing constraint); ADR-0001 (acdat extraction);
ADR-0009 (streamed-content boundary); ADR-0014 (Nanite-readiness affects cook-time
mesh settings).
