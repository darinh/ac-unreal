"""Count all major actor types in the academy level."""
import unreal

# CRITICAL: in commandlet mode the editor world is EMPTY until we
# explicitly load_level. Without this, get_all_level_actors() returns 0
# even though the level on disk is fully populated.
unreal.EditorLevelLibrary.load_level("/Game/Academy/Maps/AcademyMap")

eas = unreal.EditorActorSubsystem()
actors = eas.get_all_level_actors()
unreal.log(f"[count] total actors: {len(actors)}")
from collections import Counter
classnames = Counter(a.get_class().get_name() for a in actors)
for cn, n in classnames.most_common(20):
    unreal.log(f"[count]   {cn:30s} {n:5d}")
