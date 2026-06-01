# AGENTS.md — ac-unreal

Cross-agent entry point (Claude Code, GitHub Copilot, and any agent that reads
`AGENTS.md`). This repo recreates the **Asheron's Call retail client in Unreal
Engine 5** from the AC DAT files.

## Start here
1. **Project skills live in [`.claude/skills/`](.claude/skills/README.md)** and
   are read by both Claude Code and GitHub Copilot. Load **`ac-migration-overview`
   first**, then the relevant `ac-*` skill (`ac-dat-extraction`,
   `ac-world-streaming`, `ac-mmorpg-networking`, `ac-rendering-materials`,
   `ac-blueprints-vs-cpp`).
2. Machine-readable context: [`.agents/ue-project-context.md`](.agents/ue-project-context.md).
3. The plan and decisions: `docs/migration/` (README + `decisions/` ADRs +
   `notes/feature-disposition-and-design-gaps.md`).

## Non-negotiable rules
- **Data is truth; screenshots only confirm.** Derive everything from the DAT
  files; never reverse-engineer from a screenshot.
- **Two lanes:** simulation (`contract/`) MIRRORs the original and is parity-tested
  (no magic numbers — values from `UDataAsset`); presentation may IMPROVE but keeps
  data identity faithful.
- **Provenance:** tag "AC did X" claims `[DATA]/[REF-IMPL]/[DOC]/[COMMUNITY-VERIFY]/[DESIGN]`;
  verify against ACEmulator/ACViewer, not just our own tools.
- **Stop the line:** file cross-category blockers and halt; do not fix them in place.
- **Headless UE:** kill all `UnrealEditor*` processes first; invoke render scripts
  via PowerShell (Git Bash mangles `/Game/...` paths).
- **Git:** commit only when asked; never push without asking; trailer
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **No em-dashes** in code/scripts/PowerShell (cp1252 parse failures); prose is fine.
