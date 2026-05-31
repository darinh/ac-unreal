"""Find a PointLight and dump its world position."""
import unreal

unreal.EditorLevelLibrary.load_level("/Game/Academy/Maps/AcademyMap")
eas = unreal.EditorActorSubsystem()
actors = eas.get_all_level_actors()
pls = [a for a in actors if isinstance(a, unreal.PointLight)]
unreal.log(f"[pl] {len(pls)} PointLights total")
for i, pl in enumerate(pls[:5]):
    loc = pl.get_actor_location()
    c = pl.light_component
    unreal.log(f"[pl]   pl[{i}] @ ({loc.x:.0f}, {loc.y:.0f}, {loc.z:.0f}) intensity={c.intensity} att={c.attenuation_radius} units={c.intensity_units}")
