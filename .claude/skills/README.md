# Project skills (ac-unreal)

Original, project-specific Agent Skills for recreating the Asheron's Call retail
client in Unreal Engine 5. They are **read by both Claude Code and GitHub Copilot**
— per [GitHub Docs](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills),
Copilot scans `.github/skills`, **`.claude/skills`**, and `.agents/skills` for
project skills, so this one directory serves all agents. Skills are **dynamically
loaded** by description match — irrelevant ones do not enter context.

Each skill is a directory with a `SKILL.md` (YAML frontmatter `name` +
`description`, then Markdown). Authored from this repo's own docs and first-party
Unreal knowledge — **no third-party skill content is vendored** (so there is no
external attribution obligation; see note below).

## Skills
| Skill | When to use |
|-------|-------------|
| `ac-migration-overview` | **Read first.** Plan, two-lane rule, provenance discipline, where things live, process rules. |
| `ac-dat-extraction` | Extracting assets/data from the DAT files via `acdat`; coordinate transform; verification. |
| `ac-world-streaming` | Open world: landblock -> World Partition, the axis swap, terrain, HLOD, LWC (ADR-0009/0010/0013). |
| `ac-mmorpg-networking` | Live MMO client: Turbine UDP, ISAAC, GameAction/GameEvent, predict/reconcile vs ACEmulator. |
| `ac-rendering-materials` | Surfaces -> UE materials, lighting, day-night, and the render-harness footguns. |
| `ac-blueprints-vs-cpp` | Deciding C++ vs Blueprint; the data seam (ADR-0016). |

## Attribution note
These skills were written from scratch for this project. The external
collections reviewed during research (e.g. `quodsoler/unreal-engine-skills`, MIT;
`kevinpbuckley/unreal-engine-skills`, no license) were **not copied or
paraphrased** — vendoring the MIT one would carry an attribution obligation, and
the unlicensed one is all-rights-reserved. Topics (World Partition, replication,
etc.) are not copyrightable; the prose here is original. If you later want the
broad generic UE C++ coverage those libraries provide, install them separately
and honor their licenses rather than copying them in here.

Shared machine-readable context for all agents: [`/.agents/ue-project-context.md`](../../.agents/ue-project-context.md).
