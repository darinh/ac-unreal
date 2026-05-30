// =====================================================================
// AcDatExtract — CLI for poking at and extracting content from AC's
// .dat files (client_portal.dat, client_cell_1.dat, client_highres.dat,
// client_local_English.dat).
//
// Layered on top of ACEmulator's ACE.DatLoader library — which is the
// canonical community implementation of the DAT format. All parsing
// logic lives there; this CLI is a thin extraction harness.
//
// Commands (see PrintUsage() below):
//   acdat info <datDir>
//   acdat list-landblocks <datDir>
//   acdat landblock-info <datDir> <hexId>
//   acdat export-landblock <datDir> <hexId> <outFile.aclb>
//
// "Phase 5 / content extraction" scaffold. Next steps (future sessions):
//   - Find the Aluvian Training Academy landblock(s) via list/search.
//   - export-mesh / export-texture / export-envcell for the indoor
//     cells of the academy.
//   - Hook the export pipeline up to UE's Interchange framework or
//     write a thin UE Editor commandlet that consumes our intermediate
//     files.
// =====================================================================

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using ACE.DatLoader;
using ACE.DatLoader.FileTypes;
using log4net.Appender;
using log4net.Config;
using log4net.Core;
using log4net.Layout;

namespace AcUnreal.DatExtract;

internal static class Program
{
    static int Main(string[] args)
    {
        // .NET Core / .NET 5+ ships only ASCII + a few Unicode codepages
        // by default. ACE.DatLoader.BinaryReaderExtensions.ReadObfuscatedString
        // calls Encoding.GetEncoding(1252) (Windows-1252) for AC's legacy
        // strings; without registering CodePagesEncodingProvider the call
        // throws NotSupportedException. Done once at startup.
        Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);

        // Configure log4net so ACE.DatLoader's log.Error/Warn messages
        // are visible. Without this, FileNotFound on the DATs silently
        // produces null PortalDat/CellDat with no diagnostic.
        ConfigureLog4Net();

        try
        {
            if (args.Length < 1)
            {
                PrintUsage();
                return 1;
            }

            return args[0].ToLowerInvariant() switch
            {
                "info"               => Commands.Info(args.AsSpan(1)),
                "list-landblocks"    => Commands.ListLandblocks(args.AsSpan(1)),
                "landblock-info"     => Commands.LandblockInfo(args.AsSpan(1)),
                "list-envcells"      => Commands.ListEnvCells(args.AsSpan(1)),
                "envcell-info"       => Commands.EnvCellInfo(args.AsSpan(1)),
                "export-envcell"     => Commands.ExportEnvCell(args.AsSpan(1)),
                "export-academy"     => Commands.ExportAcademy(args.AsSpan(1)),
                "dump-academy-layout" => Commands.DumpAcademyLayout(args.AsSpan(1)),
                "dump-starterareas"  => Commands.DumpStarterAreas(args.AsSpan(1)),
                "export-landblock"   => Commands.ExportLandblock(args.AsSpan(1)),
                "--help" or "-h"     => DoUsage(),
                _ => DoUnknown(args[0]),
            };
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"FAILED: {ex.GetType().Name}: {ex.Message}");
            Console.Error.WriteLine(ex.StackTrace);
            return 99;
        }
    }

    static int DoUsage() { PrintUsage(); return 0; }
    static int DoUnknown(string cmd)
    {
        Console.Error.WriteLine($"Unknown command: {cmd}");
        PrintUsage();
        return 1;
    }

    /// <summary>
    /// Wire a ConsoleAppender so ACE.DatLoader's log4net calls go
    /// somewhere visible. Done at startup; cheap.
    /// </summary>
    static void ConfigureLog4Net()
    {
        var hierarchy = (log4net.Repository.Hierarchy.Hierarchy)log4net.LogManager.GetRepository();
        var layout = new PatternLayout { ConversionPattern = "[%level] %logger - %message%newline" };
        layout.ActivateOptions();
        var appender = new ConsoleAppender { Layout = layout, Target = "Console.Error" };
        appender.ActivateOptions();
        BasicConfigurator.Configure(hierarchy, appender);
        hierarchy.Root.Level = Level.Info;
        hierarchy.Configured = true;
    }

    static void PrintUsage()
    {
        Console.WriteLine("""
            AcDatExtract — Asheron's Call .dat file extractor (via ACE.DatLoader)

            Usage:
              acdat info               <datDir>
                    Open all DATs in <datDir>, print iteration + record counts.

              acdat list-landblocks    <datDir>
                    Walk the Cell DAT and dump every landblock surface entry.

              acdat landblock-info     <datDir> <hexId>
                    Print summary of one landblock (height samples, texture
                    layers, building/object/EnvCell counts via LandblockInfo).
                    <hexId> e.g. A9B4 = the LandblockX/Y high 16 bits.

              acdat list-envcells      <datDir> <hexId>
                    List indoor EnvCell IDs in a landblock (cell IDs where
                    the high byte of low 16 != 0). This is how dungeon
                    interiors are addressed.

              acdat envcell-info       <datDir> <fullCellId>
                    Dump an indoor cell: position, portal exits, static
                    objects. <fullCellId> is the full 32-bit cell ID,
                    e.g. A9B40100 (landblock A9B4, env-cell 0x0100).

              acdat dump-starterareas  <datDir>
                    Read CharGen.StarterAreas from PortalDat and print the
                    canonical AC starter-town landblock IDs and locations.

              acdat export-landblock   <datDir> <hexId> <outFile.aclb>
                    Convert one landblock to our v1 .aclb intermediate format
                    (see pipeline/asset-ingest/FORMAT.md).

            <datDir> is the directory containing client_portal.dat,
            client_cell_1.dat, client_highres.dat, client_local_English.dat.
            Canonical install path: C:\Turbine\Asheron's Call\
            """);
    }
}

internal static class Commands
{
    /// <summary>Open all DATs and print top-level metadata.</summary>
    public static int Info(ReadOnlySpan<string> args)
    {
        if (args.Length < 1) { Console.Error.WriteLine("info: missing <datDir>"); return 1; }
        var datDir = args[0];
        if (!Directory.Exists(datDir)) { Console.Error.WriteLine($"DAT dir not found: {datDir}"); return 1; }

        Console.WriteLine($"Opening DATs in: {datDir}");
        DatManager.Initialize(datDir, keepOpen: false, loadCell: true);

        PrintDatInfo("client_cell_1.dat",          DatManager.CellDat);
        PrintDatInfo("client_portal.dat",          DatManager.PortalDat);
        PrintDatInfo("client_highres.dat",         DatManager.HighResDat);
        PrintDatInfo("client_local_English.dat",   DatManager.LanguageDat);
        return 0;
    }

    static void PrintDatInfo(string label, ACE.DatLoader.DatDatabase? db)
    {
        if (db is null) { Console.WriteLine($"  {label,-30} NOT LOADED"); return; }
        Console.WriteLine($"  {label,-30} iteration={db.Iteration,-6} records={db.AllFiles.Count,8}");
    }

    /// <summary>
    /// Walk Portal DAT for LandblockInfo files (0xXXXX_FFFE pattern) and Cell
    /// DAT for landblock surface files (0xXXXX_FFFF pattern). Print sorted
    /// list of unique landblock IDs found in each.
    /// </summary>
    public static int ListLandblocks(ReadOnlySpan<string> args)
    {
        if (args.Length < 1) { Console.Error.WriteLine("list-landblocks: missing <datDir>"); return 1; }
        var datDir = args[0];
        DatManager.Initialize(datDir, keepOpen: false, loadCell: true);

        // CellLandblock files in CellDat are keyed by ID where the low 16 bits
        // are 0xFFFF and the high 16 bits encode (LandblockX << 8) | LandblockY.
        var cellDb = DatManager.CellDat;
        if (cellDb is null) { Console.Error.WriteLine("CellDat failed to load."); return 2; }

        var landblockSurfaceIds = cellDb.AllFiles.Keys
            .Where(id => (id & 0xFFFFu) == 0xFFFFu)
            .OrderBy(id => id)
            .ToList();

        Console.WriteLine($"Cell DAT surface entries (low 16 = 0xFFFF): {landblockSurfaceIds.Count}");
        Console.WriteLine("First 30:");
        foreach (var id in landblockSurfaceIds.Take(30))
        {
            var lbx = (id >> 24) & 0xFF;
            var lby = (id >> 16) & 0xFF;
            Console.WriteLine($"  0x{id:X8}   LbX={lbx,3}  LbY={lby,3}");
        }
        if (landblockSurfaceIds.Count > 30)
        {
            Console.WriteLine($"  ... and {landblockSurfaceIds.Count - 30} more");
        }
        return 0;
    }

    /// <summary>
    /// Load one landblock by its (LbX,LbY) high 16 bits (e.g. "A9B4") and
    /// print a structured summary of its contents.
    /// </summary>
    public static int LandblockInfo(ReadOnlySpan<string> args)
    {
        if (args.Length < 2) { Console.Error.WriteLine("landblock-info: missing <datDir> <hexId>"); return 1; }
        var datDir = args[0];
        if (!TryParseLandblockHex(args[1], out var lbHigh16)) { Console.Error.WriteLine($"Bad hex landblock id: {args[1]}"); return 1; }

        DatManager.Initialize(datDir, keepOpen: false, loadCell: true);
        var cellDb = DatManager.CellDat;
        if (cellDb is null) { Console.Error.WriteLine("CellDat failed to load."); return 2; }

        var surfaceFileId = (lbHigh16 << 16) | 0xFFFFu;
        if (!cellDb.AllFiles.ContainsKey(surfaceFileId))
        {
            Console.Error.WriteLine($"No landblock surface entry for high-16 0x{lbHigh16:X4} (looked for {surfaceFileId:X8} in CellDat).");
            return 3;
        }

        var cell = cellDb.ReadFromDat<CellLandblock>(surfaceFileId);
        Console.WriteLine($"Landblock 0x{lbHigh16:X4} (LbX={(lbHigh16 >> 8) & 0xFF}, LbY={lbHigh16 & 0xFF}):");
        Console.WriteLine($"  HasObjects:     {cell.HasObjects}");
        Console.WriteLine($"  Terrain[]:      {cell.Terrain?.Count ?? 0} entries (9x9=81 expected)");
        Console.WriteLine($"  Height[]:       {cell.Height?.Count ?? 0} entries (81 expected)");

        // LandblockInfo (buildings + EnvCells + objects) lives in CellDat,
        // NOT PortalDat. File ID pattern per ACE.DatLoader docs:
        // CLandBlockInfo file id = (landblock_high16 << 16) | 0xFFFE.
        var infoFileId = (lbHigh16 << 16) | 0xFFFEu;
        if (cellDb.AllFiles.ContainsKey(infoFileId))
        {
            var info = cellDb.ReadFromDat<ACE.DatLoader.FileTypes.LandblockInfo>(infoFileId);
            Console.WriteLine($"  LandblockInfo:  present (file 0x{infoFileId:X8} in CellDat)");
            Console.WriteLine($"    NumCells:     {info.NumCells}   (= indoor EnvCells inside this landblock)");
            Console.WriteLine($"    Buildings:    {info.Buildings?.Count ?? 0}");
            Console.WriteLine($"    Objects:      {info.Objects?.Count ?? 0}");
            Console.WriteLine($"    PackMask:     0x{info.PackMask:X8}");
        }
        else
        {
            Console.WriteLine($"  LandblockInfo:  NONE (no 0x{infoFileId:X8} in CellDat — landblock has no buildings/EnvCells)");
        }
        return 0;
    }

    /// <summary>
    /// List indoor EnvCell IDs in a landblock. EnvCells are the indoor
    /// cells that make up dungeon / building interiors. Their full
    /// cell ID is `(landblockHigh16 &lt;&lt; 16) | envCellLow16` where
    /// envCellLow16 has its high byte >= 0x01 (outdoor cells use
    /// 0x0001..0x00FE in the low 16; EnvCells use 0x0100..0xFFFE).
    /// </summary>
    public static int ListEnvCells(ReadOnlySpan<string> args)
    {
        if (args.Length < 2) { Console.Error.WriteLine("list-envcells: missing <datDir> <hexId>"); return 1; }
        var datDir = args[0];
        if (!TryParseLandblockHex(args[1], out var lbHigh16)) { Console.Error.WriteLine($"Bad hex landblock id: {args[1]}"); return 1; }

        DatManager.Initialize(datDir, keepOpen: false, loadCell: true);
        var cellDb = DatManager.CellDat ?? throw new InvalidOperationException("CellDat unavailable.");

        var minId = (lbHigh16 << 16) | 0x0100u;     // first EnvCell low-16
        var maxId = (lbHigh16 << 16) | 0xFFFDu;     // last EnvCell (0xFFFE = LandblockInfo, 0xFFFF = surface)
        var envCellIds = cellDb.AllFiles.Keys
            .Where(id => id >= minId && id <= maxId)
            .OrderBy(id => id)
            .ToList();

        Console.WriteLine($"Landblock 0x{lbHigh16:X4}: {envCellIds.Count} EnvCells (indoor cells).");
        if (envCellIds.Count == 0)
        {
            Console.WriteLine("  (no EnvCells — landblock has no indoor environments.)");
            return 0;
        }
        Console.WriteLine("First 40:");
        foreach (var id in envCellIds.Take(40))
        {
            var envLow = id & 0xFFFFu;
            Console.WriteLine($"  0x{id:X8}   env-cell 0x{envLow:X4}");
        }
        if (envCellIds.Count > 40) Console.WriteLine($"  ... and {envCellIds.Count - 40} more");
        return 0;
    }

    /// <summary>
    /// Dump one indoor cell's geometry-relevant fields.
    /// </summary>
    public static int EnvCellInfo(ReadOnlySpan<string> args)
    {
        if (args.Length < 2) { Console.Error.WriteLine("envcell-info: missing <datDir> <fullCellId>"); return 1; }
        var datDir = args[0];
        if (!TryParseLandblockHex(args[1], out var fullId)) { Console.Error.WriteLine($"Bad hex cell id: {args[1]}"); return 1; }

        DatManager.Initialize(datDir, keepOpen: false, loadCell: true);
        var cellDb = DatManager.CellDat ?? throw new InvalidOperationException("CellDat unavailable.");

        if (!cellDb.AllFiles.ContainsKey(fullId)) { Console.Error.WriteLine($"No cell at 0x{fullId:X8}."); return 3; }
        var ec = cellDb.ReadFromDat<EnvCell>(fullId);
        Console.WriteLine($"EnvCell 0x{fullId:X8}:");
        Console.WriteLine($"  EnvironmentId:  0x{ec.EnvironmentId:X8}   (-> Environment file in PortalDat)");
        Console.WriteLine($"  CellStructure:  0x{ec.CellStructure:X8}");
        Console.WriteLine($"  Position:       ({ec.Position?.Origin.X:F2}, {ec.Position?.Origin.Y:F2}, {ec.Position?.Origin.Z:F2})");
        Console.WriteLine($"  StaticObjects:  {ec.StaticObjects?.Count ?? 0}");
        Console.WriteLine($"  Portals:        {ec.CellPortals?.Count ?? 0}   (= exits to adjacent cells)");
        Console.WriteLine($"  RestrictionObj: 0x{ec.RestrictionObj:X8}");
        Console.WriteLine($"  Surfaces:       {ec.Surfaces?.Count ?? 0}");
        Console.WriteLine($"  VisibleCells:   {ec.VisibleCells?.Count ?? 0}");
        return 0;
    }

    /// <summary>
    /// Export a single indoor cell's geometry to a Wavefront OBJ file.
    /// Resolves EnvCell → EnvironmentId → Environment.Cells[CellStructure]
    /// → CellStruct with vertices + polygons. Triangulates quads and
    /// emits one OBJ group per surface (material) index.
    ///
    /// **Coordinate system: UE-ready** (left-handed Z-up, centimetres).
    /// AC native is right-handed Z-up metres; we apply the Phase 0
    /// coord transform at export time — X/Y swap (the odd permutation
    /// that flips chirality from AC RH → UE LH) plus ×100 metre→cm.
    /// Triangle winding is also swapped (v1 ↔ v2 in face output) so
    /// the chirality flip preserves outward-facing normals. The
    /// resulting OBJ drag-and-drops into UE5 at scale 1.0 with no
    /// import-dialog tweaks needed.
    ///
    /// Trade-off: emitting in UE coords means these OBJs aren't
    /// directly usable by a non-UE consumer (Blender, Maya) without
    /// inverse-mapping. Acceptable — this pipeline targets UE5.
    /// </summary>
    public static int ExportEnvCell(ReadOnlySpan<string> args)
    {
        if (args.Length < 3) { Console.Error.WriteLine("export-envcell: missing <datDir> <fullCellId> <out.obj>"); return 1; }
        var datDir = args[0];
        if (!TryParseLandblockHex(args[1], out var fullId)) { Console.Error.WriteLine($"Bad hex cell id: {args[1]}"); return 1; }
        var outPath = args[2];

        DatManager.Initialize(datDir, keepOpen: false, loadCell: true);
        var cellDb = DatManager.CellDat ?? throw new InvalidOperationException("CellDat unavailable.");
        var portalDb = DatManager.PortalDat ?? throw new InvalidOperationException("PortalDat unavailable.");

        if (!cellDb.AllFiles.ContainsKey(fullId)) { Console.Error.WriteLine($"No cell at 0x{fullId:X8}."); return 3; }
        var ec = cellDb.ReadFromDat<EnvCell>(fullId);

        if (!portalDb.AllFiles.ContainsKey(ec.EnvironmentId))
        {
            Console.Error.WriteLine($"EnvironmentId 0x{ec.EnvironmentId:X8} not in PortalDat.");
            return 4;
        }
        var env = portalDb.ReadFromDat<ACE.DatLoader.FileTypes.Environment>(ec.EnvironmentId);

        if (!env.Cells.TryGetValue(ec.CellStructure, out var cs))
        {
            Console.Error.WriteLine($"Environment 0x{ec.EnvironmentId:X8} has no CellStructure {ec.CellStructure}. Available: {string.Join(",", env.Cells.Keys)}");
            return 5;
        }

        var vertCount = cs.VertexArray.Vertices.Count;
        var polyCount = cs.Polygons.Count;
        if (vertCount == 0 || polyCount == 0)
        {
            Console.Error.WriteLine($"CellStruct has {vertCount} verts and {polyCount} polys; nothing to export.");
            return 6;
        }

        var outDir = Path.GetDirectoryName(outPath);
        if (!string.IsNullOrEmpty(outDir)) Directory.CreateDirectory(outDir);
        // Textures are shared across cells in the same export run, so we
        // dedupe by texture-id into a sibling "textures/" directory.
        var texDir = Path.Combine(string.IsNullOrEmpty(outDir) ? "." : outDir, "textures");
        Directory.CreateDirectory(texDir);

        // Conversion constants (single source of truth: Phase 0 coord transform):
        //   UE.X = AC.Y * 100   (AC north → UE forward, scaled to cm)
        //   UE.Y = AC.X * 100   (AC east  → UE right,   scaled to cm)
        //   UE.Z = AC.Z * 100   (AC up    → UE up,      scaled to cm)
        //   Triangle winding flipped (v1 ↔ v2) because the X-Y swap is
        //   an odd permutation that would otherwise invert face normals.
        // See Source/AcUnreal/Public/CoordCore/CoordTransform.h and
        // README decision #9 for the full reasoning.
        const float kCmPerMetre = 100.0f;

        // Sidecar paths.
        var objBaseName = Path.GetFileNameWithoutExtension(outPath);
        var mtlPath = Path.Combine(outDir ?? ".", objBaseName + ".mtl");

        using var sw = new StreamWriter(outPath);
        sw.WriteLine($"# Exported by acdat from EnvCell 0x{fullId:X8}");
        sw.WriteLine($"# EnvironmentId=0x{ec.EnvironmentId:X8}  CellStructure={ec.CellStructure}");
        sw.WriteLine($"# {vertCount} verts, {polyCount} polys");
        sw.WriteLine($"# UE-ready coords: left-handed Z-up, centimetres. UE.X=AC.Y*100, UE.Y=AC.X*100, UE.Z=AC.Z*100.");
        sw.WriteLine($"# Triangle winding flipped (v1<->v2) to preserve outward normals through the X-Y swap.");
        sw.WriteLine($"mtllib {objBaseName}.mtl");
        sw.WriteLine($"o cell_{fullId:X8}");

        // Map original vertex ID -> OBJ 1-based index (positions + normals share the same map).
        var vertOrder = cs.VertexArray.Vertices.Keys.OrderBy(k => k).ToList();
        var idToObjIndex = new Dictionary<ushort, int>(vertOrder.Count);
        for (int i = 0; i < vertOrder.Count; i++)
        {
            var sv = cs.VertexArray.Vertices[vertOrder[i]];
            // AC (X, Y, Z) → UE (Y*100, X*100, Z*100) — swap X↔Y then scale m→cm.
            sw.WriteLine($"v {sv.Origin.Y * kCmPerMetre:R} {sv.Origin.X * kCmPerMetre:R} {sv.Origin.Z * kCmPerMetre:R}");
            idToObjIndex[vertOrder[i]] = i + 1; // OBJ is 1-based
        }
        for (int i = 0; i < vertOrder.Count; i++)
        {
            var sv = cs.VertexArray.Vertices[vertOrder[i]];
            // Normals: same X↔Y swap, no scale (normals are unitless directions).
            sw.WriteLine($"vn {sv.Normal.Y:R} {sv.Normal.X:R} {sv.Normal.Z:R}");
        }
        for (int i = 0; i < vertOrder.Count; i++)
        {
            var sv = cs.VertexArray.Vertices[vertOrder[i]];
            if (sv.UVs != null && sv.UVs.Count > 0)
            {
                sw.WriteLine($"vt {sv.UVs[0].U:R} {sv.UVs[0].V:R}");
            }
            else
            {
                sw.WriteLine($"vt 0 0");
            }
        }

        // Group polygons by PosSurface (index into EnvCell.Surfaces) and emit each group.
        int triEmitted = 0;
        int polysSkipped = 0;
        var groups = cs.Polygons.Values
            .GroupBy(p => (int)p.PosSurface)
            .OrderBy(g => g.Key);
        var surfaceIndicesUsed = new HashSet<int>();
        foreach (var grp in groups)
        {
            surfaceIndicesUsed.Add(grp.Key);
            sw.WriteLine($"g surf_{grp.Key}");
            sw.WriteLine($"usemtl surf_{grp.Key}");
            foreach (var poly in grp)
            {
                if (poly.NumPts < 3) { polysSkipped++; continue; }
                if (poly.VertexIds == null || poly.VertexIds.Count < poly.NumPts) { polysSkipped++; continue; }

                int v0 = idToObjIndex[(ushort)poly.VertexIds[0]];
                for (int i = 1; i + 1 < poly.NumPts; i++)
                {
                    int va = idToObjIndex[(ushort)poly.VertexIds[i]];
                    int vb = idToObjIndex[(ushort)poly.VertexIds[i + 1]];
                    // Winding swap: emit (v0, vb, va) instead of (v0, va, vb)
                    // to compensate for the chirality flip from the X-Y axis swap.
                    sw.WriteLine($"f {v0}/{v0}/{v0} {vb}/{vb}/{vb} {va}/{va}/{va}");
                    triEmitted++;
                }
            }
        }

        sw.Flush();

        // ---- Material sidecar (.mtl) + texture extraction --------------
        //
        // EnvCell.Surfaces is the per-cell surface palette; each Polygon's
        // PosSurface field is a *signed-short index* into it (not a raw
        // Surface ID). We resolve each used index to its real Surface
        // (0x08xxxxxx), then follow the well-known chain:
        //   Surface (0x08) → OrigTextureId → SurfaceTexture (0x05)
        //                                  → Textures[0]    (0x06)
        // PFID_CUSTOM_RAW_JPEG textures are JPGs, everything else is PNG.
        // Texture.ExportTexture writes by Texture.Id so multiple cells
        // that share a surface share the on-disk image file too.
        //
        // TODO Phase 5e: honor Surface.OrigPaletteId override (apply a
        // non-default Palette via Texture.CustomPaletteColors before
        // export) so palette-swapped variants don't all collide on the
        // same default-palette PNG.
        int texturesWritten = 0, solidColors = 0, missing = 0;
        using (var mtl = new StreamWriter(mtlPath))
        {
            mtl.WriteLine($"# Materials for cell_{fullId:X8}");
            mtl.WriteLine($"# Generated by acdat. Each surf_N maps to EnvCell.Surfaces[N] (PortalDat 0x08xxxxxx).");
            mtl.WriteLine($"# TODO: palette overrides (Surface.OrigPaletteId) not yet honored.");
            mtl.WriteLine();

            foreach (var surfIdx in surfaceIndicesUsed.OrderBy(i => i))
            {
                mtl.WriteLine($"newmtl surf_{surfIdx}");
                mtl.WriteLine("Ka 0.1 0.1 0.1");
                mtl.WriteLine("Kd 1.0 1.0 1.0");
                mtl.WriteLine("Ks 0.0 0.0 0.0");
                mtl.WriteLine("d  1.0");
                mtl.WriteLine("illum 1");

                // Valid surface index?
                if (surfIdx < 0 || surfIdx >= ec.Surfaces.Count)
                {
                    mtl.WriteLine($"# (no Surfaces[{surfIdx}] in cell — keeping default white)");
                    mtl.WriteLine();
                    missing++;
                    continue;
                }
                uint surfaceId = ec.Surfaces[surfIdx];
                mtl.WriteLine($"# Surfaces[{surfIdx}] = 0x{surfaceId:X8}");

                if (!portalDb.AllFiles.ContainsKey(surfaceId))
                {
                    mtl.WriteLine($"# (Surface 0x{surfaceId:X8} not in PortalDat)");
                    mtl.WriteLine();
                    missing++;
                    continue;
                }

                var surface = portalDb.ReadFromDat<Surface>(surfaceId);
                var isImage = surface.Type.HasFlag(ACE.Entity.Enum.SurfaceType.Base1Image)
                           || surface.Type.HasFlag(ACE.Entity.Enum.SurfaceType.Base1ClipMap);

                if (isImage && surface.OrigTextureId != 0
                    && portalDb.AllFiles.ContainsKey(surface.OrigTextureId))
                {
                    var sfcTex = portalDb.ReadFromDat<SurfaceTexture>(surface.OrigTextureId);
                    if (sfcTex.Textures.Count > 0)
                    {
                        // Highest-detail texture is the last entry per AC convention
                        // (Textures[0] is the lowest mipmap). Use the last one.
                        uint textureId = sfcTex.Textures[sfcTex.Textures.Count - 1];
                        if (portalDb.AllFiles.ContainsKey(textureId))
                        {
                            var tex = portalDb.ReadFromDat<Texture>(textureId);
                            string ext = tex.Format == ACE.Entity.Enum.SurfacePixelFormat.PFID_CUSTOM_RAW_JPEG ? ".jpg" : ".png";
                            string texFileName = $"{textureId:X8}{ext}";
                            string texPath = Path.Combine(texDir, texFileName);
                            try
                            {
                                if (!File.Exists(texPath))
                                {
                                    tex.ExportTexture(texDir);
                                    texturesWritten++;
                                }
                                mtl.WriteLine($"# Texture 0x{textureId:X8}  {tex.Width}x{tex.Height}  {tex.Format}");
                                mtl.WriteLine($"map_Kd textures/{texFileName}");
                            }
                            catch (Exception ex)
                            {
                                mtl.WriteLine($"# (texture export failed: {ex.Message})");
                                missing++;
                            }
                        }
                        else
                        {
                            mtl.WriteLine($"# (Texture 0x{textureId:X8} not in PortalDat)");
                            missing++;
                        }
                    }
                    else
                    {
                        mtl.WriteLine($"# (SurfaceTexture 0x{surface.OrigTextureId:X8} has no Textures)");
                        missing++;
                    }
                }
                else
                {
                    // Solid-color surface. ColorValue is BGRA-packed.
                    uint c = surface.ColorValue;
                    float b = ((c >> 0) & 0xFF) / 255.0f;
                    float g = ((c >> 8) & 0xFF) / 255.0f;
                    float r = ((c >> 16) & 0xFF) / 255.0f;
                    mtl.WriteLine($"# Solid color (no texture). BGRA=0x{c:X8}");
                    // Overwrite the default-white Kd above by writing it again — last one wins.
                    mtl.WriteLine($"Kd {r:F4} {g:F4} {b:F4}");
                    solidColors++;
                }
                mtl.WriteLine();
            }
        }

        var bytes = new FileInfo(outPath).Length;
        Console.WriteLine($"Wrote {bytes} bytes to {outPath}");
        Console.WriteLine($"  Cell 0x{fullId:X8}: {vertCount} verts, {polyCount} polys -> {triEmitted} triangles ({polysSkipped} skipped)");
        Console.WriteLine($"  Materials: {surfaceIndicesUsed.Count} unique surfaces  ({texturesWritten} new textures, {solidColors} solid colors, {missing} missing/failed)");
        Console.WriteLine($"  Sidecar: {mtlPath}");
        return 0;
    }

    /// <summary>
    /// Bulk-export every EnvCell in a landblock to individual OBJ files
    /// under &lt;outDir&gt;. Each cell becomes &lt;outDir&gt;\cell_&lt;hexId&gt;.obj.
    /// </summary>
    public static int ExportAcademy(ReadOnlySpan<string> args)
    {
        if (args.Length < 3) { Console.Error.WriteLine("export-academy: missing <datDir> <hexLandblockId> <outDir>"); return 1; }
        var datDir = args[0];
        if (!TryParseLandblockHex(args[1], out var lbHigh16)) { Console.Error.WriteLine($"Bad hex landblock id: {args[1]}"); return 1; }
        var outDir = args[2];
        Directory.CreateDirectory(outDir);

        DatManager.Initialize(datDir, keepOpen: false, loadCell: true);
        var cellDb = DatManager.CellDat ?? throw new InvalidOperationException("CellDat unavailable.");

        var minId = (lbHigh16 << 16) | 0x0100u;
        var maxId = (lbHigh16 << 16) | 0xFFFDu;
        var envCellIds = cellDb.AllFiles.Keys.Where(id => id >= minId && id <= maxId).OrderBy(id => id).ToList();

        Console.WriteLine($"Exporting {envCellIds.Count} EnvCells in landblock 0x{lbHigh16:X4} to {outDir} ...");
        int ok = 0, failed = 0;
        foreach (var id in envCellIds)
        {
            var path = Path.Combine(outDir, $"cell_{id:X8}.obj");
            // Reuse the single-cell logic by invoking it directly.
            int rc;
            try
            {
                rc = ExportEnvCell(new[] { datDir, $"{id:X8}", path });
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"  FAILED 0x{id:X8}: {ex.Message}");
                rc = 99;
            }
            if (rc == 0) ok++; else failed++;
        }
        Console.WriteLine($"Done. {ok} OK, {failed} failed.");
        return failed == 0 ? 0 : 1;
    }

    /// <summary>
    /// Dump per-cell world-space layout for a landblock as JSON. UE-side
    /// import consumes this to position imported OBJ meshes correctly
    /// in world space (the OBJ files themselves contain local-to-cell
    /// vertices). Pair this with export-academy.
    /// </summary>
    public static int DumpAcademyLayout(ReadOnlySpan<string> args)
    {
        if (args.Length < 3) { Console.Error.WriteLine("dump-academy-layout: missing <datDir> <hexLandblockId> <out.json>"); return 1; }
        var datDir = args[0];
        if (!TryParseLandblockHex(args[1], out var lbHigh16)) { Console.Error.WriteLine($"Bad hex landblock id: {args[1]}"); return 1; }
        var outPath = args[2];

        DatManager.Initialize(datDir, keepOpen: false, loadCell: true);
        var cellDb = DatManager.CellDat ?? throw new InvalidOperationException("CellDat unavailable.");

        var minId = (lbHigh16 << 16) | 0x0100u;
        var maxId = (lbHigh16 << 16) | 0xFFFDu;
        var envCellIds = cellDb.AllFiles.Keys.Where(id => id >= minId && id <= maxId).OrderBy(id => id).ToList();

        var cells = envCellIds.Select(id =>
        {
            var ec = cellDb.ReadFromDat<EnvCell>(id);
            // Apply the same AC→UE coord transform we apply at OBJ export:
            // X↔Y swap + m→cm. So the position in this JSON is in the
            // SAME coordinate space as the OBJ vertices — UE-side import
            // can drop a StaticMeshActor at this position directly.
            const float kCmPerMetre = 100.0f;
            return new
            {
                cell_id = $"0x{id:X8}",
                cell_id_decimal = id,
                obj_file = $"cell_{id:X8}.obj",
                environment_id = $"0x{ec.EnvironmentId:X8}",
                cell_structure = (int)ec.CellStructure,
                // UE-coords (cm). UE.X = AC.Y * 100, UE.Y = AC.X * 100, UE.Z = AC.Z * 100.
                position = new
                {
                    x = ec.Position.Origin.Y * kCmPerMetre,
                    y = ec.Position.Origin.X * kCmPerMetre,
                    z = ec.Position.Origin.Z * kCmPerMetre,
                },
                // Quaternion: AC's right-handed (X-east, Y-north, Z-up)
                // basis differs from UE's left-handed (X-fwd, Y-right,
                // Z-up) by an X↔Y swap, which is an *improper* rotation
                // (det = -1) that flips chirality. For a quaternion
                // (w, x, y, z) representing a rotation in AC, the
                // equivalent UE rotation is (w, -y, -x, -z): swap the
                // X and Y components (basis change) and negate the
                // vector part (compensate for the chirality flip so
                // the rotation direction stays consistent with the
                // handedness flip). Derivation:
                //   AC rot_z(θ)  →  UE rot_z(-θ)
                //   AC rot_x(θ)  →  UE rot_y(-θ)
                //   AC rot_y(θ)  →  UE rot_x(-θ)
                // Verified by hand against the identity, pure-Z, and
                // pure-X cases; matches our Phase 0 CoordTransform.
                orientation = new
                {
                    w =  ec.Position.Orientation.W,
                    x = -ec.Position.Orientation.Y,
                    y = -ec.Position.Orientation.X,
                    z = -ec.Position.Orientation.Z,
                },
                portals = ec.CellPortals?.Count ?? 0,
                static_objects = ec.StaticObjects?.Count ?? 0,
                surfaces = ec.Surfaces?.Count ?? 0,
                visible_cells = ec.VisibleCells?.Count ?? 0,
            };
        }).ToList();

        var doc = new
        {
            schema_version = 3,
            landblock_id = $"0x{lbHigh16:X4}",
            landblock_id_decimal = lbHigh16,
            coordinate_system = "UE-ready: left-handed Z-up, centimetres. UE.X = AC.Y*100, UE.Y = AC.X*100, UE.Z = AC.Z*100. Matches the per-cell OBJ files (drag-and-drop into UE5 at scale 1.0). Quaternion is also transformed into UE basis (w_ue, x_ue, y_ue, z_ue) = (w_ac, -y_ac, -x_ac, -z_ac) — see comments in Program.cs DumpAcademyLayout for the derivation.",
            cell_count = cells.Count,
            cells = cells,
        };

        var json = JsonSerializer.Serialize(doc, new JsonSerializerOptions { WriteIndented = true });
        var dir = Path.GetDirectoryName(outPath);
        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
        File.WriteAllText(outPath, json);

        Console.WriteLine($"Wrote layout JSON ({new FileInfo(outPath).Length} bytes) for {cells.Count} cells in landblock 0x{lbHigh16:X4} to {outPath}");
        return 0;
    }

    public static int DumpStarterAreas(ReadOnlySpan<string> args)
    {
        if (args.Length < 1) { Console.Error.WriteLine("dump-starterareas: missing <datDir>"); return 1; }
        var datDir = args[0];
        DatManager.Initialize(datDir, keepOpen: false, loadCell: false);
        var portalDb = DatManager.PortalDat ?? throw new InvalidOperationException("PortalDat unavailable.");
        var cg = portalDb.CharGen;
        Console.WriteLine($"CharGen.StarterAreas: {cg.StarterAreas?.Count ?? 0} entries");
        if (cg.StarterAreas == null) return 0;
        for (int i = 0; i < cg.StarterAreas.Count; i++)
        {
            var sa = cg.StarterAreas[i];
            Console.WriteLine($"  [{i}] Name='{sa.Name}'   Locations: {sa.Locations?.Count ?? 0}");
            if (sa.Locations != null)
            {
                foreach (var loc in sa.Locations)
                {
                    var lbHigh = (loc.ObjCellID >> 16) & 0xFFFFu;
                    var cellLow = loc.ObjCellID & 0xFFFFu;
                    var indoorOutdoor = (cellLow >= 0x0100) ? "INDOOR" : "outdoor";
                    Console.WriteLine($"        cell=0x{loc.ObjCellID:X8} (lb=0x{lbHigh:X4} {indoorOutdoor})  pos=({loc.Frame.Origin.X:F2}, {loc.Frame.Origin.Y:F2}, {loc.Frame.Origin.Z:F2})");
                }
            }
        }
        return 0;
    }

    /// <summary>
    /// Export one landblock's heightfield + terrain-texture indices to a
    /// v1 .aclb file (see pipeline/asset-ingest/FORMAT.md).
    /// </summary>
    public static int ExportLandblock(ReadOnlySpan<string> args)
    {
        if (args.Length < 3) { Console.Error.WriteLine("export-landblock: missing <datDir> <hexId> <outFile.aclb>"); return 1; }
        var datDir = args[0];
        if (!TryParseLandblockHex(args[1], out var lbHigh16)) { Console.Error.WriteLine($"Bad hex landblock id: {args[1]}"); return 1; }
        var outFile = args[2];

        DatManager.Initialize(datDir, keepOpen: false, loadCell: true);
        var cellDb = DatManager.CellDat ?? throw new InvalidOperationException("CellDat unavailable.");

        var surfaceFileId = (lbHigh16 << 16) | 0xFFFFu;
        if (!cellDb.AllFiles.ContainsKey(surfaceFileId))
        {
            Console.Error.WriteLine($"No landblock surface entry for high-16 0x{lbHigh16:X4}.");
            return 3;
        }
        var cell = cellDb.ReadFromDat<CellLandblock>(surfaceFileId);

        // Build the .aclb v1 byte layout. AC's native landblock vertex
        // grid is 9x9; our format spec accepts [2..65].
        const uint kMagic = 0x424C4341; // 'ACLB' little-endian
        const uint kVersion = 1u;
        const uint kSide = 9u;
        const uint kTexLayers = 1u; // ACE CellLandblock.Terrain is a single layer of terrain-type indices
        // .aclb LandblockId must have low-16 == 0 (see FORMAT.md "LandblockId semantics" + ACE-encoding note).
        var aclbLandblockId = (uint)lbHigh16 << 16;

        if ((cell.Height?.Count ?? 0) != 81)
            throw new InvalidDataException($"Expected 81 height samples, got {cell.Height?.Count ?? 0}.");
        if ((cell.Terrain?.Count ?? 0) != 81)
            throw new InvalidDataException($"Expected 81 terrain entries, got {cell.Terrain?.Count ?? 0}.");

        using var stream = File.Create(outFile);
        using var writer = new BinaryWriter(stream);

        // 32-byte header
        writer.Write(kMagic);
        writer.Write(kVersion);
        writer.Write(aclbLandblockId);
        writer.Write(kSide);
        writer.Write(kTexLayers);
        writer.Write(0u);  // Flags
        writer.Write(0u);  // Reserved[0]
        writer.Write(0u);  // Reserved[1]

        // ACE CellLandblock.Height is byte[] of indices into PortalDat.RegionDesc.LandDefs.LandHeightTable.
        // For an honest extraction, we'd resolve those indices into actual metre values via the height table.
        // For Phase 5 scaffold, we emit raw bytes as floats (0..N indices) — a follow-up pass will multiply
        // by the LandHeightTable values from PortalDat. See "TODO: height table resolution" below.
        for (int i = 0; i < 81; i++)
        {
            writer.Write((float)cell.Height![i]);  // PLACEHOLDER conversion; see TODO.
        }
        // Texture layer 0: terrain-type byte per cell (already in the right shape).
        for (int i = 0; i < 81; i++)
        {
            writer.Write((byte)cell.Terrain![i]);  // ACE Terrain is uint; truncated to byte for .aclb v1
        }

        writer.Flush();
        Console.WriteLine($"Wrote {stream.Length} bytes to {outFile}");
        Console.WriteLine($"  Magic    0x{kMagic:X8}");
        Console.WriteLine($"  Version  {kVersion}");
        Console.WriteLine($"  LbId     0x{aclbLandblockId:X8} (LbX={(lbHigh16 >> 8) & 0xFF}, LbY={lbHigh16 & 0xFF})");
        Console.WriteLine($"  Side     {kSide}x{kSide}");
        Console.WriteLine($"  Layers   {kTexLayers}");
        Console.WriteLine("");
        Console.WriteLine("TODO: height samples currently written as raw ACE indices cast to float.");
        Console.WriteLine("      Real metres require PortalDat.RegionDesc.LandDefs.LandHeightTable lookup.");
        Console.WriteLine("      Tracked for the next Phase 5 iteration.");
        return 0;
    }

    static bool TryParseLandblockHex(string s, out uint high16)
    {
        if (s.StartsWith("0x", StringComparison.OrdinalIgnoreCase)) s = s.Substring(2);
        return uint.TryParse(s, System.Globalization.NumberStyles.HexNumber, null, out high16);
    }
}
