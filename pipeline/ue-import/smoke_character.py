# smoke_character.py — verify AcAcademyCharacter spawns with proper CMC + camera.
# Assertions fail HARD (sys.exit non-zero) on regression so CI/runs detect breakage.
import sys
import unreal


def out(m): unreal.log(f"[smokechar] {m}")


def fail(msg):
    unreal.log_error(f"[smokechar] ASSERT FAILED: {msg}")
    sys.exit(1)


def _walk_parents_contains(cls, target):
    """Walk up the UE class chain looking for `target`. Returns True if found."""
    cur = cls
    while cur is not None:
        if cur == target:
            return True
        cur = cur.get_super_class()
    return False


LEVEL = "/Game/Academy/Maps/AcademyMap"
out(f"loading level: {LEVEL}")
if not unreal.EditorAssetLibrary.does_asset_exist(LEVEL):
    fail(f"level {LEVEL} does not exist")
unreal.EditorLevelLibrary.load_level(LEVEL)

out("checking PlayerStart present ...")
eas = unreal.EditorActorSubsystem()
starts = [a for a in eas.get_all_level_actors() if isinstance(a, unreal.PlayerStart)]
if not starts:
    fail("no PlayerStart in level — run add_player_start.py first")
out(f"  PlayerStarts in level: {len(starts)}")
for s in starts:
    loc = s.get_actor_location()
    out(f"    {s.get_actor_label()}: ({loc.x:.1f}, {loc.y:.1f}, {loc.z:.1f})")

out("loading expected classes ...")
char_class = unreal.load_class(None, "/Script/AcUnreal.AcAcademyCharacter")
if char_class is None:
    fail("AcAcademyCharacter class not loadable — build the C++ target?")
expected_cmc_class = unreal.load_class(None, "/Script/AcUnreal.AcCharacterMovementComponent")
if expected_cmc_class is None:
    fail("AcCharacterMovementComponent class not loadable")
gm_class = unreal.load_class(None, "/Script/AcUnreal.AcAcademyGameMode")
if gm_class is None:
    fail("AcAcademyGameMode class not loadable")
out("  all 3 classes loadable")

out("spawning a transient AAcAcademyCharacter to inspect components ...")
spawn_loc = starts[0].get_actor_location()
spawn_rot = starts[0].get_actor_rotation()
actor = eas.spawn_actor_from_class(char_class, spawn_loc, spawn_rot)
if actor is None:
    fail("spawn_actor_from_class returned None")
actor.set_actor_label("AcAcademyCharacter_SmokeTest")

try:
    cmc = actor.get_component_by_class(unreal.CharacterMovementComponent)
    if cmc is None:
        fail("character has no CharacterMovementComponent at all")
    cmc_cls_name = cmc.get_class().get_name()
    out(f"  CMC class: {cmc_cls_name}")
    # is_a accepts a class object and walks the inheritance chain.
    if not cmc.get_class() == expected_cmc_class and not _walk_parents_contains(cmc.get_class(), expected_cmc_class):
        fail(f"CMC is {cmc_cls_name} but expected AcCharacterMovementComponent — "
             f"SetDefaultSubobjectClass didn't take. Sim core won't be wired.")
    out("  CMC class matches expected (SetDefaultSubobjectClass took)")

    cam = actor.get_component_by_class(unreal.CameraComponent)
    if cam is None:
        fail("character has no CameraComponent — third-person view will be missing")
    out(f"  Camera present: {cam.get_name()}")

    sa = actor.get_component_by_class(unreal.SpringArmComponent)
    if sa is None:
        fail("character has no SpringArmComponent — camera won't behave correctly")
    arm_len = sa.get_editor_property('target_arm_length')
    if abs(arm_len - 400.0) > 0.1:
        fail(f"SpringArm.TargetArmLength = {arm_len}, expected 400")
    out(f"  SpringArm present, TargetArmLength = {arm_len}")
finally:
    # Always destroy the test actor, even on failure, so the level is clean.
    eas.destroy_actor(actor)

out("checking project GlobalDefaultGameMode is wired ...")
# DefaultGame.ini should reference AcAcademyGameMode. We read the config directly
# because the live editor world doesn't have a running GameMode (PIE-only).
import configparser
import pathlib
proj_root = pathlib.Path(unreal.Paths.project_dir())
default_game = proj_root / "Config" / "DefaultGame.ini"
text = default_game.read_text(encoding="utf-8")
if "GlobalDefaultGameMode=/Script/AcUnreal.AcAcademyGameMode" not in text:
    fail("DefaultGame.ini does not have GlobalDefaultGameMode=/Script/AcUnreal.AcAcademyGameMode")
if "GameDefaultMap=/Game/Academy/Maps/AcademyMap" not in text:
    fail("DefaultGame.ini does not point GameDefaultMap at AcademyMap")
out("  GlobalDefaultGameMode + GameDefaultMap correctly set")

out("ALL CHECKS PASSED.")
