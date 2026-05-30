"""Probe StaticMesh API for bounds-related methods."""
import unreal

sm = unreal.EditorAssetLibrary.load_asset("/Game/Academy/Cells/SM_860201AD")
unreal.log(f"[probe] type={type(sm).__name__}")
names = sorted([n for n in dir(sm) if 'bound' in n.lower() or 'extend' in n.lower()])
for n in names:
    unreal.log(f"[probe]   {n}")
