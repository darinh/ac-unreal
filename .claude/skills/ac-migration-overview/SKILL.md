---
name: ac-migration-overview
description: "Read this FIRST when doing any work in the ac-unreal repo (recreating the Asheron's Call retail client in Unreal Engine 5). Orients you to the plan, the two-lane simulation/presentation rule, the data-is-truth + provenance (anti-hallucination) discipline, where everything lives, the mirror/improve/remove/add decision vocabulary, and the process rules. Routes you to the other ac-* skills."
metadata:
  category: project-context
---

# AC -> Unreal Engine migration: orientation

This repo recreates the **Asheron's Call (AC) retail client in Unreal Engine 5**,
derived from the AC DAT files, as a documented, replayable methodology. Use this
skill to get oriented before touching anything; it points to the deeper ac-*
skills and the canonical docs.

## The two rules that govern everything

1. **Data is the source of truth; screenshots are the answer key.** Everything
   must be derivable from the client DAT files. Reference screenshots (kept
   outside the repo) only *confirm* a derivation after the fact — they are never
   an input. Never reverse-engineer from a screenshot.

2. **Two lanes.** Keep them separate:
   - **Simulation lane** (`contract/`, `Source/AcUnreal` sim-core): movement,
     collision, physics-feel, networking, timing. This must **MIRROR** the
     original exactly — it is parity-tested against recorded traces, not
     modernized. No magic numbers; values load from data/`UDataAsset`.
   - **Presentation lane** (rendering, audio, UI): free to **IMPROVE** with
     modern UE tech, *but* data identity (which mesh/texture/timing) stays
     faithful. Fidelity is tiered, not pixel-perfect (T0 topology .. T4 timing;
     see `docs/migration/README.md`).

## Anti-hallucination / provenance discipline (REQUIRED)

We are largely in a requirements/design phase and prior guesses have cost real
money. When you state "AC did X," tag the claim:
- `[DATA]` confirmed from DAT / the `acdat` extractor / a committed artifact (cite it)
- `[REF-IMPL]` documented in ACEmulator `ACE.DatLoader`/`ACE.Server` or ACViewer (confirm the symbol)
- `[DOC]` asserted in this repo's design docs
- `[COMMUNITY/VERIFY]` widely-held AC lore, NOT yet confirmed here — verify before it drives a requirement
- `[DESIGN]` your engineering recommendation, not a retail fact

Cross-check against ACEmulator / ACViewer, not just by re-running our own tools.

## Disposition vocabulary (use it when proposing work)
**MIRROR** (reproduce as-is, default for simulation) · **IMPROVE/UPGRADE**
(retail had it; render/run it better — allowed in presentation, record the
deviation) · **REMOVE** (obsolete 1999 plumbing) · **ADD** (no retail analogue).
The full per-feature matrix is in
`docs/migration/notes/feature-disposition-and-design-gaps.md`.

## Where things live
- `docs/migration/README.md` — master plan: category taxonomy (I-XV), the
  dependency-ordered first-room milestone, status ledger.
- `docs/migration/extraction-methodology.md` — DAT taxonomy, the AC->UE
  coordinate transform, per-asset recipes, gotchas. (See skill `ac-dat-extraction`.)
- `docs/migration/glossary.md` — AC/DAT terms (ACEmulator vocabulary).
- `docs/migration/decisions/` — ADRs (the *why*; challenge the rationale, don't
  silently reverse). 0009-0020 are the open world-scale + Blueprint + collision/
  water/portal/networking decisions.
- `docs/migration/notes/feature-disposition-and-design-gaps.md` — what we
  mirror/improve/remove/add and the open design gaps.
- `contract/physics-feel-spec-request.md` — the simulation parity spec (mostly
  UNKNOWN, awaiting decompile).
- `pipeline/dat-extract/` — the `acdat` C# CLI (wraps `ACE.DatLoader`).
- `pipeline/ue-import/` — headless UE Python importers + the render harness.

## Process rules (non-negotiable)
- **Stop the line.** If you hit a blocker that belongs to another category, file
  it and halt — do not fix it in place (a lighting chase once derailed the
  geometry work).
- **Guard destructive ops** (`docs/migration/recovery.md`) — this project has
  lost work before.
- **Kill all `UnrealEditor*` processes before any headless run** — a stale one
  holds the project lock and makes scripts fail silently.
- **Commit only when asked**; never push without asking. Commit trailer:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **No em-dashes in code/scripts/PowerShell** (cp1252 parse failures); prose is fine.

## Sibling skills
`ac-dat-extraction` · `ac-world-streaming` · `ac-mmorpg-networking` ·
`ac-rendering-materials` · `ac-blueprints-vs-cpp`. Shared machine-readable
context for all agents: `.agents/ue-project-context.md`.
