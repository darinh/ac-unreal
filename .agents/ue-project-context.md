# Project context: ac-unreal (read before advising)

Machine-readable project context shared across AI agents (Claude Code, GitHub
Copilot, etc.). Skills and agents should read this before giving UE advice.

## What this project is
Recreating the **Asheron's Call (AC) retail client in Unreal Engine 5**, derived
from the AC DAT files, as a documented, replayable methodology. **The DAT data is
the source of truth; reference screenshots are an answer key to confirm
derivations, never an input.**

## Engine / build facts
- **Engine:** Unreal Engine **5.7**. Large World Coordinates active
  (`largeworldcoordinates="1"`).
- **Currently disabled** (interim, see ADR-0002/0015): Lumen, Nanite, hardware
  ray tracing, mesh distance fields, static lighting; auto-exposure off
  (deterministic renders). These are step-0 expedients, not world-scale decisions.
- **World scale:** seamless ~49 km world, 192 m landblocks (8x8 of 24 m cells).
- **Multiplayer:** server-authoritative; forward-compatible with **ACEmulator**
  (retail Turbine protocol must be mirrored).

## The two lanes (governing rule)
- **Simulation lane** (`contract/`, sim-core): MIRROR the original exactly;
  parity-tested; no magic numbers (values from `UDataAsset`).
- **Presentation lane** (rendering/audio/UI): may IMPROVE with modern UE tech, but
  keep data identity faithful (tiered fidelity T0-T4, not pixel-perfect).

## Provenance discipline (anti-hallucination)
Tag "AC did X" claims: `[DATA]` (DAT/extractor/artifact) · `[REF-IMPL]`
(ACEmulator/ACViewer) · `[DOC]` (repo docs) · `[COMMUNITY/VERIFY]` (verify before
it drives a requirement) · `[DESIGN]` (recommendation). Cross-check against
ACEmulator/ACViewer, not just our own tools.

## Where things live
- Plan + taxonomy + status: `docs/migration/README.md`
- Extraction how-to: `docs/migration/extraction-methodology.md`
- Terms: `docs/migration/glossary.md`
- Decisions: `docs/migration/decisions/` (ADRs; 0009-0016 are the open
  world-scale + Blueprint decisions)
- Feature dispositions + gaps: `docs/migration/notes/feature-disposition-and-design-gaps.md`
- Simulation spec: `contract/physics-feel-spec-request.md`
- Extraction CLI: `pipeline/dat-extract/` (`acdat`, wraps `ACE.DatLoader`)
- UE importers + render harness: `pipeline/ue-import/`
- Project skills: `.claude/skills/` (start with `ac-migration-overview`)

## Process rules
Stop the line (don't fix cross-category blockers in place) · guard destructive ops
(`docs/migration/recovery.md`) · kill all `UnrealEditor*` before headless runs ·
invoke render scripts via PowerShell (Git Bash mangles `/Game/...` paths) ·
commit only when asked, never push without asking · no em-dashes in code/scripts/
PowerShell.
