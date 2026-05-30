"""Count all major actor types in the academy level."""
import unreal

eas = unreal.EditorActorSubsystem()
actors = eas.get_all_level_actors()
unreal.log(f"[count] total actors: {len(actors)}")
from collections import Counter
classnames = Counter(a.get_class().get_name() for a in actors)
for cn, n in classnames.most_common(20):
    unreal.log(f"[count]   {cn:30s} {n:5d}")
