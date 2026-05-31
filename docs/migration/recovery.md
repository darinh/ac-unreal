# Backup & recovery runbook

This project has lost work before (a ~387-actor purge and a ~1487-actor
level wipe scare during import iteration). Treat destructive pipeline ops as
guarded operations. Keep this short and follow it.

## Before any destructive op
"Destructive" = anything that deletes/regenerates actors or assets in bulk:
`import_academy.py` re-spawn, level rebuilds, `purge_*`, bulk UAsset rewrites,
`git clean`, `git reset --hard`, `git rm` of tracked content.

```powershell
# 1. checkpoint the working tree
git stash push -u -m "pre-<op>-$(Get-Date -Format yyyyMMdd-HHmmss)"
git stash apply            # keep the changes in the tree, but now saved in stash
# 2. tag a restore point on HEAD
git tag -f restore/<op>
```
For UE level/asset state specifically, also note the `.umap` mtime (the render
harness already checks this) so you can tell whether a save actually happened.

## After the op succeeds
```powershell
git stash drop             # drop the safety stash
git tag -d restore/<op>    # optional: clear the restore point
```

## If the op fails or corrupts assets
```powershell
# revert only the affected paths to the restore point
git checkout restore/<op> -- <paths>          # e.g. Content/Academy/ or a script
# or, for uncommitted working-tree damage, recover from the safety stash
git stash list ; git stash apply stash@{N}
```
UE asset corruption / half-written map:
1. Kill the editor that holds the lock: `Stop-Process -Name UnrealEditor-Cmd -Force` (this is the documented "stale lock" gotcha).
2. `git checkout HEAD -- Content/` to restore tracked assets (grandfathered; see LEGAL.md).
3. Re-run the **idempotent** importer (`import_academy.py`, etc.) to regenerate.

## Data that is regenerable vs. precious
- **Regenerable (don't panic):** anything under `pipeline/**/out/` (git-ignored),
  any UAsset produced by an importer, the lights/layout JSON (re-run `acdat`).
- **Precious (protect):** source under `pipeline/*/` and `Source/`, the `docs/`,
  and uncommitted experiment notes. Commit or stash these before destructive ops.

## Periodic
- Cold-archive the repo + the pinned `~/repos/ACE` SHA off-disk at milestone boundaries.
- The DAT files themselves are the user's own client install (LEGAL.md); back those up independently.

> Linked from README §intro and §4 (runbook). If you skip these steps and lose
> work, add the incident to the README §6 changelog so the next agent learns.
