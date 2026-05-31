# =====================================================================
# import_academy.py
#
# UE5 Python script: consumes the Phase 5d academy layout JSON and
# assembles all 568 EnvCells of the Aluvian Training Academy
# (landblock 0x8602) into a single UE level.
#
# Run from the command line (the wrapper script run_import.ps1 does
# this for you):
#
#   UnrealEditor-Cmd.exe <uproject> -run=pythonscript
#       -script="pipeline\\ue-import\\import_academy.py"
#       -RenderOffScreen -nop4 -nosplash -stdout
#
# Inputs (configured via env vars or defaults below):
#   AC_LAYOUT_JSON   absolute path to academy_8602_layout.json
#   AC_OBJ_DIR       absolute dir containing cell_*.obj + cell_*.mtl + textures/
#   AC_LAYOUT_LIMIT  optional cap on cells imported (smoke testing)
#
# Outputs (UE asset paths):
#   /Game/Academy/Textures/T_<id>          -- Texture2D per unique PNG
#   /Game/Academy/Materials/MI_Surf_<id>   -- MaterialInstance per texture
#   /Game/Academy/Materials/M_AcademyBase  -- shared PBR master material
#   /Game/Academy/Cells/SM_<cellId>        -- StaticMesh per cell
#   /Game/Academy/Maps/AcademyMap          -- Level w/ all 568 actors
#                                              + skylight + dir light
#                                              + PostProcessVolume
#
# Coordinate contract: the layout JSON is already in UE space (cm,
# left-handed Z-up). Quaternion is also transformed. We pass values
# straight through with no conversion.
#
# Why we DON'T use the OBJ importer:
#   The Interchange OBJ pipeline (UE 5.7 default) creates one asset
#   per OBJ 'g surf_N' group, named "surf_0", "surf_1", ..., directly
#   in the destination path. When 568 cells all have a "surf_0" group
#   the names collide and UE pops Slate dialogs that crash a headless
#   editor. We instead parse the OBJ + MTL ourselves and build
#   StaticMesh assets via the MeshDescription Python API. This also
#   gives us proper control over material assignment.
# =====================================================================

import unreal
import json
import os
import re
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]

LAYOUT_JSON = os.environ.get(
    "AC_LAYOUT_JSON",
    str(REPO_ROOT / "pipeline" / "dat-extract" / "samples" / "academy_8602_layout.json"),
)
OBJ_DIR = os.environ.get(
    "AC_OBJ_DIR",
    str(REPO_ROOT / "pipeline" / "dat-extract" / "out" / "academy_8602"),
)

CELLS_PACKAGE     = "/Game/Academy/Cells"
TEXTURES_PACKAGE  = "/Game/Academy/Textures"
MATERIALS_PACKAGE = "/Game/Academy/Materials"
MAPS_PACKAGE      = "/Game/Academy/Maps"
LEVEL_NAME        = "AcademyMap"
LEVEL_PATH        = f"{MAPS_PACKAGE}/{LEVEL_NAME}"
MASTER_MATERIAL_NAME = "M_AcademyBase"
MASTER_MATERIAL_PATH = f"{MATERIALS_PACKAGE}/{MASTER_MATERIAL_NAME}"


def log(msg: str) -> None:
    unreal.log(f"[acdemyimport] {msg}")
    print(f"[acdemyimport] {msg}", flush=True)


# ---------------------------------------------------------------------
# OBJ + MTL parsers (intentionally minimal — we only need to handle
# what our exporter emits).
# ---------------------------------------------------------------------

class ObjGroup:
    """One material group's geometry in a parsed OBJ."""
    __slots__ = ("material", "triangles")
    def __init__(self, material: str):
        self.material = material
        self.triangles = []   # list of [(vi,ti,ni), (vi,ti,ni), (vi,ti,ni)] — 0-based


class ObjMesh:
    """Parsed OBJ. Vertices/normals/uvs are shared; groups carry per-mtl tris."""
    __slots__ = ("positions", "normals", "uvs", "groups", "mtllib")
    def __init__(self):
        self.positions = []     # list of (x,y,z)
        self.normals   = []     # list of (nx,ny,nz)
        self.uvs       = []     # list of (u,v)
        self.groups    = []     # list of ObjGroup
        self.mtllib    = None


def _parse_face_token(tok: str) -> tuple:
    """OBJ face token 'v', 'v/t', 'v//n', or 'v/t/n'. All 1-based; returns 0-based."""
    parts = tok.split("/")
    v = int(parts[0]) - 1
    t = int(parts[1]) - 1 if len(parts) > 1 and parts[1] else -1
    n = int(parts[2]) - 1 if len(parts) > 2 and parts[2] else -1
    return (v, t, n)


def parse_obj(path: Path) -> ObjMesh:
    mesh = ObjMesh()
    current = None
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            cmd = parts[0]
            if cmd == "v":
                mesh.positions.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif cmd == "vn":
                mesh.normals.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif cmd == "vt":
                mesh.uvs.append((float(parts[1]), float(parts[2])))
            elif cmd == "mtllib":
                mesh.mtllib = parts[1]
            elif cmd == "usemtl":
                current = ObjGroup(parts[1])
                mesh.groups.append(current)
            elif cmd == "f":
                if current is None:
                    current = ObjGroup("__default__")
                    mesh.groups.append(current)
                tokens = [_parse_face_token(t) for t in parts[1:]]
                # The exporter pre-triangulates, so len(tokens) == 3 always,
                # but handle n-gons defensively (fan triangulation).
                for i in range(1, len(tokens) - 1):
                    current.triangles.append([tokens[0], tokens[i], tokens[i + 1]])
    return mesh


class MtlMaterial:
    __slots__ = ("name", "kd_rgb", "map_kd")
    def __init__(self, name: str):
        self.name = name
        self.kd_rgb = (1.0, 1.0, 1.0)
        self.map_kd = None  # relative path string, or None for solid color


def parse_mtl(path: Path) -> dict:
    mats = {}
    cur = None
    if not path.exists():
        return mats
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            cmd = parts[0]
            if cmd == "newmtl":
                cur = MtlMaterial(parts[1])
                mats[cur.name] = cur
            elif cur is None:
                continue
            elif cmd == "Kd":
                cur.kd_rgb = (float(parts[1]), float(parts[2]), float(parts[3]))
            elif cmd == "map_Kd":
                # Strip the textures/ prefix; we manage texture paths manually.
                cur.map_kd = " ".join(parts[1:])
    return mats


# ---------------------------------------------------------------------
# Master material — created once, shared by all cell materials.
# ---------------------------------------------------------------------

def ensure_master_material():
    """Return None — we skip material wiring in headless mode because
    MaterialEditingLibrary + ContentBrowser ops crash Slate even with
    -RenderOffScreen. Cells get UE's default WorldGridMaterial, which
    is fine for verifying geometry. Texture/material binding happens
    in pipeline/ue-import/assign_materials.py — a follow-up that the
    user runs interactively in the Editor.
    """
    return None


# ---------------------------------------------------------------------
# Texture import — dedupes across cells by filename.
# Returns {filename: unreal.Texture2D}
# ---------------------------------------------------------------------

_texture_cache: dict = {}

def import_texture(png_path: Path) -> unreal.Texture2D:
    asset_name = "T_" + png_path.stem  # T_06003C9A
    asset_path = f"{TEXTURES_PACKAGE}/{asset_name}"
    if asset_name in _texture_cache:
        return _texture_cache[asset_name]
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        tex = unreal.EditorAssetLibrary.load_asset(asset_path)
        _texture_cache[asset_name] = tex
        return tex

    unreal.EditorAssetLibrary.make_directory(TEXTURES_PACKAGE)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(png_path))
    task.set_editor_property("destination_path", TEXTURES_PACKAGE)
    task.set_editor_property("destination_name", asset_name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks([task])

    tex = unreal.EditorAssetLibrary.load_asset(asset_path)
    if tex is None:
        unreal.log_warning(f"texture import failed for {png_path}")
        return None
    _texture_cache[asset_name] = tex
    return tex


# ---------------------------------------------------------------------
# Material Instance — dedupes per (texture_id or color).
# ---------------------------------------------------------------------

_mi_cache: dict = {}

def ensure_mi_for_texture(master: unreal.Material, png_path: Path) -> unreal.MaterialInstanceConstant:
    key = "tex:" + png_path.name
    if key in _mi_cache:
        return _mi_cache[key]
    asset_name = "MI_Surf_" + png_path.stem
    asset_path = f"{MATERIALS_PACKAGE}/{asset_name}"
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        mi = unreal.EditorAssetLibrary.load_asset(asset_path)
        _mi_cache[key] = mi
        return mi

    tex = import_texture(png_path)
    if tex is None:
        return None

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    factory = unreal.MaterialInstanceConstantFactoryNew()
    factory.set_editor_property("initial_parent", master)
    mi = asset_tools.create_asset(
        asset_name=asset_name,
        package_path=MATERIALS_PACKAGE,
        asset_class=unreal.MaterialInstanceConstant,
        factory=factory)

    mel = unreal.MaterialEditingLibrary
    mel.set_material_instance_texture_parameter_value(mi, "BaseColorTex", tex)
    mel.set_material_instance_static_switch_parameter_value(mi, "UseTexture", True)
    unreal.EditorAssetLibrary.save_asset(asset_path)
    _mi_cache[key] = mi
    return mi


def ensure_mi_for_color(master: unreal.Material, rgb: tuple) -> unreal.MaterialInstanceConstant:
    r, g, b = rgb
    key = f"col:{int(r*255)}_{int(g*255)}_{int(b*255)}"
    if key in _mi_cache:
        return _mi_cache[key]
    asset_name = f"MI_Color_{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}"
    asset_path = f"{MATERIALS_PACKAGE}/{asset_name}"
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        mi = unreal.EditorAssetLibrary.load_asset(asset_path)
        _mi_cache[key] = mi
        return mi
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    factory = unreal.MaterialInstanceConstantFactoryNew()
    factory.set_editor_property("initial_parent", master)
    mi = asset_tools.create_asset(
        asset_name=asset_name,
        package_path=MATERIALS_PACKAGE,
        asset_class=unreal.MaterialInstanceConstant,
        factory=factory)
    mel = unreal.MaterialEditingLibrary
    mel.set_material_instance_vector_parameter_value(
        mi, "BaseColor", unreal.LinearColor(r, g, b, 1.0))
    mel.set_material_instance_static_switch_parameter_value(mi, "UseTexture", False)
    unreal.EditorAssetLibrary.save_asset(asset_path)
    _mi_cache[key] = mi
    return mi


# ---------------------------------------------------------------------
# Build a StaticMesh asset directly from parsed OBJ data, using
# MeshDescription. Side-steps Interchange entirely.
# ---------------------------------------------------------------------

def build_static_mesh(obj_mesh: ObjMesh, mtl_map: dict, asset_name: str,
                       master_material) -> unreal.StaticMesh:
    """Create a StaticMesh asset via the StaticMeshDescription Python API.
    No material binding in this pass — geometry only. Materials are
    assigned by the follow-up assign_materials.py script."""
    asset_path = f"{CELLS_PACKAGE}/{asset_name}"
    # Rebuild in place if the asset already exists (so a re-run actually
    # applies geometry/UV fixes) instead of early-returning. Capture any
    # existing material-slot bindings so the rebuild preserves them rather
    # than wiping them back to WorldGridMaterial.
    prev_mats = {}
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        sm = unreal.EditorAssetLibrary.load_asset(asset_path)
        for s in (sm.get_editor_property("static_materials") or []):
            prev_mats[str(s.material_slot_name)] = s.material_interface
    else:
        unreal.EditorAssetLibrary.make_directory(CELLS_PACKAGE)
        at = unreal.AssetToolsHelpers.get_asset_tools()
        sm = at.create_asset(
            asset_name=asset_name,
            package_path=CELLS_PACKAGE,
            asset_class=unreal.StaticMesh,
            factory=None)
    if sm is None:
        unreal.log_error(f"create_asset returned None for {asset_path}")
        return None

    # Create the StaticMeshDescription via the static factory method on
    # StaticMesh, passing `sm` as the outer. Plain `unreal.StaticMeshDescription()`
    # creates an unparented description whose internal MeshAttributesRef
    # is null — that crashes build_from_static_mesh_descriptions with an
    # access violation at offset 0x38. The factory wires up the attribute
    # registries we need (positions / UVs / material slot names).
    desc = unreal.StaticMesh.create_static_mesh_description(sm)
    slot_names = []

    for surf_idx, grp in enumerate(obj_mesh.groups):
        if not grp.triangles:
            continue

        # Slot name records which surface this group represents so the
        # post-import material assignment script knows what texture
        # belongs here. We embed the OBJ "usemtl" name (e.g. "surf_0").
        slot_name = unreal.Name(grp.material if grp.material else f"Slot_{surf_idx:03d}")
        pg_id = desc.create_polygon_group()
        desc.set_polygon_group_material_slot_name(pg_id, slot_name)
        slot_names.append(slot_name)

        vid_for_pos: dict = {}
        def vid(pos_idx, _desc=desc, _positions=obj_mesh.positions, _cache=vid_for_pos):
            v = _cache.get(pos_idx)
            if v is None:
                v = _desc.create_vertex()
                _desc.set_vertex_position(v, unreal.Vector(*_positions[pos_idx]))
                _cache[pos_idx] = v
            return v

        for tri in grp.triangles:
            v_ids = [vid(t[0]) for t in tri]
            vi_ids = []
            for (pi, ti, ni), v in zip(tri, v_ids):
                vi = desc.create_vertex_instance(v)
                if 0 <= ti < len(obj_mesh.uvs):
                    u, vv = obj_mesh.uvs[ti]
                    # AC uses a DirectX-style top-left UV origin (V increasing
                    # downward), same as UE — so do NOT flip V. The previous
                    # `1.0 - vv` rendered every wall texture upside-down
                    # (verified: the brick trim band sat at the top instead of
                    # the floor). Use vv directly.
                    desc.set_vertex_instance_uv(vi, unreal.Vector2D(u, vv), 0)
                vi_ids.append(vi)
            desc.create_triangle(pg_id, vi_ids)

    sm.build_from_static_mesh_descriptions([desc])

    # Stamp material slots by slot_name, preserving any binding the mesh
    # already had (prev_mats) so a geometry/UV rebuild doesn't wipe assigned
    # materials. Newly-built meshes get None → WorldGridMaterial until the
    # material-assignment pass runs.
    sm.set_editor_property("static_materials",
        [unreal.StaticMaterial(material_interface=prev_mats.get(str(n)),
                               material_slot_name=n)
         for n in slot_names])

    unreal.EditorAssetLibrary.save_asset(asset_path)
    return sm


# ---------------------------------------------------------------------
# Layout JSON
# ---------------------------------------------------------------------

def load_layout() -> dict:
    p = Path(LAYOUT_JSON)
    if not p.exists():
        unreal.log_error(f"Layout JSON not found: {p}")
        sys.exit(1)
    data = json.loads(p.read_text(encoding="utf-8"))
    log(f"loaded {data['cell_count']} cells from {p.name} "
        f"(schema_version={data.get('schema_version')})")
    if data.get("schema_version", 0) < 3:
        unreal.log_warning(
            f"layout schema_version is {data.get('schema_version')} < 3 — "
            "quaternion may still be in AC basis; rotations will be wrong."
        )
    limit_str = os.environ.get("AC_LAYOUT_LIMIT")
    if limit_str:
        try:
            limit = int(limit_str)
            if 0 < limit < len(data["cells"]):
                log(f"AC_LAYOUT_LIMIT={limit} — capping cell list "
                    f"({len(data['cells'])} -> {limit})")
                data["cells"] = data["cells"][:limit]
                data["cell_count"] = limit
        except ValueError:
            pass
    return data


# ---------------------------------------------------------------------
# Per-cell pipeline: parse OBJ+MTL, build mesh, spawn actor.
# ---------------------------------------------------------------------

def process_cells(cells: list, master_material: unreal.Material) -> tuple:
    eas = unreal.EditorActorSubsystem()
    obj_dir = Path(OBJ_DIR)
    built = 0
    spawned = 0
    skipped = 0

    t0 = time.time()
    for i, cell in enumerate(cells):
        cell_id = cell["cell_id"]            # "0x860201AD"
        short_id = cell_id[2:]
        obj_path = obj_dir / cell["obj_file"]
        mtl_path = obj_path.with_suffix(".mtl")
        if not obj_path.exists():
            unreal.log_warning(f"OBJ missing: {obj_path}")
            skipped += 1
            continue

        try:
            obj_mesh = parse_obj(obj_path)
            mtl_map = parse_mtl(mtl_path)
            sm = build_static_mesh(obj_mesh, mtl_map,
                                    f"SM_{short_id}", master_material)
            built += 1
        except Exception as e:
            unreal.log_error(f"build failed for {cell_id}: {e}")
            skipped += 1
            continue

        pos = cell["position"]
        loc = unreal.Vector(float(pos["x"]), float(pos["y"]), float(pos["z"]))
        q = cell["orientation"]
        rot = unreal.Quat(float(q["x"]), float(q["y"]),
                          float(q["z"]), float(q["w"])).rotator()
        actor = eas.spawn_actor_from_class(unreal.StaticMeshActor, loc, rot)
        if actor is None:
            skipped += 1
            continue
        actor.set_actor_label(f"Cell_{short_id}")
        actor.static_mesh_component.set_static_mesh(sm)
        z_m = round(float(pos["z"]) / 100)
        actor.set_folder_path(f"Academy/Floor_{z_m:+04d}m")
        spawned += 1

        if (i + 1) % 32 == 0:
            log(f"  cell {i+1}/{len(cells)}: built={built} spawned={spawned} skipped={skipped} "
                f"({time.time() - t0:.1f}s)")

    log(f"cells done: built={built} spawned={spawned} skipped={skipped} "
        f"({time.time() - t0:.1f}s)")
    return built, spawned, skipped


# ---------------------------------------------------------------------
# Level + lighting
# ---------------------------------------------------------------------

def ensure_level() -> None:
    els = unreal.EditorLevelLibrary  # still works in 5.7, just deprecated
    if unreal.EditorAssetLibrary.does_asset_exist(LEVEL_PATH):
        log(f"opening existing level {LEVEL_PATH}")
        els.load_level(LEVEL_PATH)
        return
    log(f"creating new level {LEVEL_PATH}")
    unreal.EditorAssetLibrary.make_directory(MAPS_PACKAGE)
    els.new_level(LEVEL_PATH)


def setup_baseline_lighting() -> None:
    eas = unreal.EditorActorSubsystem()
    existing = {a.get_actor_label() for a in eas.get_all_level_actors()}

    if "AcademySkyLight" not in existing:
        sky = eas.spawn_actor_from_class(
            unreal.SkyLight,
            unreal.Vector(0, 0, 5000), unreal.Rotator(0, 0, 0))
        sky.set_actor_label("AcademySkyLight")
        sky.set_folder_path("Academy/Lighting")
        sky_comp = sky.get_editor_property("light_component")
        sky_comp.set_editor_property("real_time_capture", True)
        sky_comp.set_editor_property("intensity", 1.0)
        log("spawned SkyLight (real-time capture)")

    if "AcademySun" not in existing:
        sun = eas.spawn_actor_from_class(
            unreal.DirectionalLight,
            unreal.Vector(0, 0, 8000), unreal.Rotator(-50, 30, 0))
        sun.set_actor_label("AcademySun")
        sun.set_folder_path("Academy/Lighting")
        sun_comp = sun.get_editor_property("light_component")
        sun_comp.set_editor_property("intensity", 3.0)
        log("spawned DirectionalLight")

    if "AcademyPostProcess" not in existing:
        ppv = eas.spawn_actor_from_class(
            unreal.PostProcessVolume,
            unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
        ppv.set_actor_label("AcademyPostProcess")
        ppv.set_folder_path("Academy/Lighting")
        ppv.set_editor_property("unbound", True)
        ppv_settings = ppv.get_editor_property("settings")
        ppv_settings.set_editor_property("auto_exposure_method",
            unreal.AutoExposureMethod.AEM_HISTOGRAM)
        ppv_settings.set_editor_property("override_auto_exposure_method", True)
        ppv.set_editor_property("settings", ppv_settings)
        log("spawned PostProcessVolume (unbound, histogram exposure)")


def save_level() -> None:
    log(f"saving level {LEVEL_PATH}")
    unreal.EditorLevelLibrary.save_current_level()


def main() -> int:
    log(f"layout JSON: {LAYOUT_JSON}")
    log(f"OBJ dir:     {OBJ_DIR}")
    log(f"target level: {LEVEL_PATH}")

    data = load_layout()

    ensure_level()
    master_material = ensure_master_material()

    built, spawned, skipped = process_cells(data["cells"], master_material)
    if built == 0:
        unreal.log_error("no cells built; aborting before saving level")
        return 2

    setup_baseline_lighting()
    save_level()

    log(f"DONE. {built} meshes built, {spawned} actors spawned, "
        f"{skipped} skipped. level saved at {LEVEL_PATH}.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
