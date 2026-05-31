"""No-render check: report current shading_model + blend_mode of the two
academy master materials, and whether the isolated CellInspect level exists.
Writes to pipeline/renders/_diag_shading.txt (unreal.log does not reach stdout).
"""
import unreal

EAL = unreal.EditorAssetLibrary
OUT = r"C:\Users\darin\repos\ac-unreal\pipeline\renders\_diag_shading.txt"
lines = []


def emit(m):
    lines.append(str(m))


for mp in ("/Game/Academy/Materials/M_AcademyBase",
           "/Game/Academy/Materials/M_AcademyColor"):
    if EAL.does_asset_exist(mp):
        m = EAL.load_asset(mp)
        emit(f"{mp}: shading={m.get_editor_property('shading_model')} "
             f"blend={m.get_editor_property('blend_mode')} "
             f"two_sided={m.get_editor_property('two_sided')}")
    else:
        emit(f"{mp}: MISSING")

emit(f"CellInspect exists: {EAL.does_asset_exist('/Game/_Inspect/CellInspect')}")
emit(f"AcademyMap exists: {EAL.does_asset_exist('/Game/Academy/Maps/AcademyMap')}")

with open(OUT, "w") as f:
    f.write("\n".join(lines) + "\n")
