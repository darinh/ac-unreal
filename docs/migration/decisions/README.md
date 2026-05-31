# Architecture Decision Records (ADRs)

One file per significant, contestable decision, so the *why* survives and the
next agent challenges the rationale instead of silently reversing it.

**Status values:** `Proposed` (open, needs a call) - `Accepted` (in force) -
`Superseded by NNNN` - `Deprecated`.

**Format (keep it short):**
```
# NNNN - Title
Status: <status>   Date: YYYY-MM-DD
## Context     (the forces / constraints)
## Decision    (what we chose)
## Consequences (trade-offs, what this commits us to, revisit trigger)
## Alternatives (what we rejected and why)
```

When a `Proposed` ADR is decided, flip its status and note the date. When you
reverse a decision, add a new ADR and mark the old one `Superseded by NNNN`;
never edit history away.

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-ace-datloader-via-acdat.md) | Use ACE.DatLoader (via the `acdat` CLI) for DAT extraction | Accepted |
| [0002](0002-lumen-nanite-rt-disabled.md) | Lumen / Nanite / HW ray tracing disabled for now | Accepted |
| [0003](0003-no-committed-ac-assets.md) | No AC-derived assets committed; users supply their own DATs | Accepted |
| [0004](0004-obj-transitional-gltf.md) | OBJ is a transitional intermediate; glTF for skinned/multi-UV | Proposed |
| [0006](0006-ace-linking-stance.md) | ACE.DatLoader linking stance (AGPL obligations) | Accepted |
| [0007](0007-indoor-lighting-unlit-emissive.md) | Indoor lighting: unlit emissive textures (point-light accents deferred) | Accepted |
| [0008](0008-skip-portal-polygons-on-export.md) | Skip portal polygons (`Stippling == NoPos`) on EnvCell export | Accepted |

Option analysis for the lighting decision is at
[`../notes/lighting-options.md`](../notes/lighting-options.md); the call is
recorded in ADR-0007.
