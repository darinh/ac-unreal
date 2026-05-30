"""Clean up duplicate Cell_* actors created by re-running import_academy.py.
Each cell should appear exactly once. If more than one StaticMeshActor
shares the same Cell_XXXXXXXX label, keep the first and destroy the rest."""

import unreal
from collections import defaultdict


def log(m): unreal.log(f"[dedup] {m}")


unreal.EditorLevelLibrary.load_level("/Game/Academy/Maps/AcademyMap")
eas = unreal.EditorActorSubsystem()
all_actors = eas.get_all_level_actors()
log(f"loaded level with {len(all_actors)} actors")

by_label = defaultdict(list)
for a in all_actors:
    try:
        label = a.get_actor_label()
    except Exception:
        continue
    if label.startswith("Cell_"):
        by_label[label].append(a)

dupes = {l: actors for l, actors in by_label.items() if len(actors) > 1}
log(f"{len(by_label)} unique cell labels, {len(dupes)} have duplicates")

removed = 0
for label, actors in dupes.items():
    # Keep the first, destroy the rest.
    for a in actors[1:]:
        unreal.EditorLevelLibrary.destroy_actor(a)
        removed += 1

log(f"removed {removed} duplicate Cell_* actors")
unreal.EditorLevelLibrary.save_current_level()
log("level saved")
