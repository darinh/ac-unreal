# GitHub Copilot instructions — ac-unreal

Always-on guidance for GitHub Copilot in this repo (recreating the Asheron's Call
retail client in Unreal Engine 5 from the AC DAT files).

## Use the project skills
Project skills live in **`.claude/skills/`**, which Copilot scans for project
skills (alongside `.github/skills` and `.agents/skills`). Consult the relevant
`ac-*` skill before doing UE work; start with **`ac-migration-overview`**. Topics:
`ac-dat-extraction`, `ac-world-streaming`, `ac-mmorpg-networking`,
`ac-rendering-materials`, `ac-blueprints-vs-cpp`. Shared context:
`.agents/ue-project-context.md`. Plan + decisions: `docs/migration/`.

## Always apply
- **Data is the source of truth; reference screenshots only confirm** — never
  reverse-engineer from a screenshot.
- **Two lanes:** the simulation lane (`contract/`) must MIRROR the original and is
  parity-tested (no hard-coded magic numbers — load from `UDataAsset`); the
  presentation lane may modernize but keeps data identity faithful.
- **Provenance:** when stating what the AC client does, tag the claim
  `[DATA]/[REF-IMPL]/[DOC]/[COMMUNITY-VERIFY]/[DESIGN]` and verify against
  ACEmulator/ACViewer rather than asserting from memory.
- **Stop the line:** if a blocker belongs to another category, file it and halt;
  do not fix it in place.
- **Headless UE:** kill all `UnrealEditor*` processes before running; invoke render
  scripts via PowerShell (Git Bash rewrites `/Game/...` paths).
- **C++ vs Blueprint:** parity/perf/networking in C++, UI/designer-tunable/
  prototyping in Blueprint, the seam is data (`UDataAsset`/`DataTable`) — see
  `ac-blueprints-vs-cpp` / ADR-0016.
- **Git:** commit only when asked; never push without asking; no em-dashes in
  code/scripts/PowerShell.
