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
- **Known conflict to resolve:** prior commits already track AC-derived
  `Content/Academy/**` UAssets/UMaps. Reconciling that history (purge vs.
  accept) is an open item; do not add *new* AC assets meanwhile.

## Alternatives
- Commit assets for convenience: rejected (legal risk; LEGAL.md posture).
- Git LFS for assets: rejected for AC-derived content (same IP problem, just larger).
