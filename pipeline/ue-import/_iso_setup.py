import unreal, math, os

LEVEL = "/Game/Academy/Maps/AcademyMap"
HEX = os.environ.get("AC_ISO_SETUP", "020005DA").upper().replace("0X", "")
MESH = f"/Game/Academy/Setups/SM_Setup_{HEX}"
SPAWN = unreal.Vector(15000, -5000, 0)   # far from academy

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level(LEVEL)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

mesh = unreal.load_asset(MESH)
sma = eas.spawn_actor_from_class(unreal.StaticMeshActor, SPAWN, unreal.Rotator(0, 0, 0))
sma.set_actor_label("ISO_DOOR")
smc = sma.static_mesh_component
smc.set_static_mesh(mesh)
unreal.log("[iso] spawned %s nmat=%d" % (HEX, smc.get_num_materials()))

cam = unreal.Vector(14250, -5950, 360)
d = SPAWN - cam
yaw = math.degrees(math.atan2(d.y, d.x))
pitch = math.degrees(math.atan2(d.z, math.sqrt(d.x*d.x + d.y*d.y)))
rot = unreal.Rotator(0.0, pitch, yaw)
for a in eas.get_all_level_actors():
    if a.get_class().get_name() == "PlayerStart":
        a.set_actor_location_and_rotation(cam, rot, False, False)
        break

les.save_current_level()
unreal.log("[iso] saved")
