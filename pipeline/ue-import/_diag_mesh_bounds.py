"""Check cell mesh bounds — if (0,0,0) extent or NaN, meshes get
frustum-culled even when in view."""
import unreal

def log(m): unreal.log(f"[bounds] {m}")

samples = [
    "/Game/Academy/Cells/SM_860201AD",   # spawn cell
    "/Game/Academy/Cells/SM_86020100",
    "/Game/Academy/Cells/SM_86020200",
    "/Game/Academy/Setups/SM_Setup_0200007C",  # chest (KNOWN to render)
    "/Game/Academy/Setups/SM_Setup_02000001",  # NPC body
]

for path in samples:
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        log(f"  MISSING {path}")
        continue
    sm = unreal.EditorAssetLibrary.load_asset(path)
    if not isinstance(sm, unreal.StaticMesh):
        continue
    b = sm.get_bounds()
    tri_count = sm.get_num_triangles(0) if sm.get_num_lods() > 0 else "?"
    vert_count = sm.get_num_vertices(0) if sm.get_num_lods() > 0 else "?"
    log(f"  {sm.get_name():28s} tris={tri_count} verts={vert_count} "
        f"box_extent=({b.box_extent.x:.1f}, {b.box_extent.y:.1f}, {b.box_extent.z:.1f}) "
        f"origin=({b.origin.x:.1f}, {b.origin.y:.1f}, {b.origin.z:.1f}) "
        f"sphere_radius={b.sphere_radius:.1f}")
