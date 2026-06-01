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
//   acdat find-building-blocks <datDir>
//   acdat dump-envcell-positions <datDir> <hexId>
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
using ACE.Entity.Enum;
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
                "find-building-blocks" => Commands.FindBuildingBlocks(args.AsSpan(1)),
                "dump-envcell-positions" => Commands.DumpEnvCellPositions(args.AsSpan(1)),
                "list-envcells"      => Commands.ListEnvCells(args.AsSpan(1)),
                "envcell-info"       => Commands.EnvCellInfo(args.AsSpan(1)),
                "export-envcell"     => Commands.ExportEnvCell(args.AsSpan(1)),
                "dump-poly-uvs"      => Commands.DumpPolyUVs(args.AsSpan(1)),
                "dump-poly-stippling" => Commands.DumpPolyStippling(args.AsSpan(1)),
                "audit-portals"      => Commands.AuditPortals(args.AsSpan(1)),
                "export-academy"     => Commands.ExportAcademy(args.AsSpan(1)),
                "dump-academy-layout" => Commands.DumpAcademyLayout(args.AsSpan(1)),
                "dump-academy-statics" => Commands.DumpAcademyStatics(args.AsSpan(1)),
                "dump-academy-lights" => Commands.DumpAcademyLights(args.AsSpan(1)),
                "export-setup"       => Commands.ExportSetup(args.AsSpan(1)),
                "export-npc"         => Commands.ExportNpc(args.AsSpan(1)),
                "export-academy-statics" => Commands.ExportAcademyStatics(args.AsSpan(1)),
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

              acdat find-building-blocks <datDir>
                    Scan every LandblockInfo in the Cell DAT and list the
                    landblocks whose Buildings count > 0 (building-interior
                    blocks), with their Buildings and NumCells. Used to pick
                    building-interior samples for the ADR-0009 EnvCell census.

              acdat dump-envcell-positions <datDir> <hexId>
                    Full single-process EnvCell.Position census for one
                    landblock: every indoor cell's landblock-local Frame.Origin,
                    composed world position (LbX*192+x, LbY*192+y, z), and
                    whether it falls inside the [0,192] footprint. Auditable
                    artifact source for ADR-0009.

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
    /// Single-process scan of EVERY LandblockInfo (0xXXXXFFFE) in CellDat,
    /// reporting landblocks whose Buildings.Count > 0 (i.e. building-interior
    /// landblocks, as opposed to zero-building dungeon blocks). Used to widen
    /// the ADR-0009 EnvCell co-location census beyond a single town block.
    /// Output is hex landblock id + Buildings + NumCells, sorted by id.
    /// </summary>
    public static int FindBuildingBlocks(ReadOnlySpan<string> args)
    {
        if (args.Length < 1) { Console.Error.WriteLine("find-building-blocks: missing <datDir>"); return 1; }
        var datDir = args[0];
        DatManager.Initialize(datDir, keepOpen: false, loadCell: true);
        var cellDb = DatManager.CellDat;
        if (cellDb is null) { Console.Error.WriteLine("CellDat failed to load."); return 2; }

        // LandblockInfo files have low 16 bits == 0xFFFE; high 16 = (LbX<<8)|LbY.
        var infoIds = cellDb.AllFiles.Keys
            .Where(id => (id & 0xFFFFu) == 0xFFFEu)
            .OrderBy(id => id)
            .ToList();

        Console.WriteLine($"LandblockInfo entries (low 16 = 0xFFFE): {infoIds.Count}");
        Console.WriteLine("Landblocks with Buildings > 0 (hex high16, Buildings, NumCells):");
        int withBuildings = 0;
        foreach (var id in infoIds)
        {
            var info = cellDb.ReadFromDat<ACE.DatLoader.FileTypes.LandblockInfo>(id);
            var bcount = info.Buildings?.Count ?? 0;
            if (bcount > 0)
            {
                withBuildings++;
                var high16 = (id >> 16) & 0xFFFFu;
                Console.WriteLine($"  0x{high16:X4}  Buildings={bcount,-4}  NumCells={info.NumCells}");
            }
        }
        Console.WriteLine($"Total landblocks with Buildings>0: {withBuildings} of {infoIds.Count}");
        return 0;
    }

    /// <summary>
    /// List indoor EnvCell IDs in a landblock. EnvCells are the indoor
    /// cells that make up dungeon / building interiors. Their full
    /// cell ID is `(landblockHigh16 &lt;&lt; 16) | envCellLow16` where
    /// envCellLow16 selects the cell. Outdoor land cells occupy the
    /// 0x0001..0x0040 range (8x8 = 64 surface cells; ACE EnvCell.cs:12,
    /// ACViewer LandDefs LastLandCellID = 64); indoor EnvCells use
    /// 0x0100..0xFFFD; 0xFFFE = LandblockInfo.
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
    /// Full single-process EnvCell.Position census for one landblock, for the
    /// ADR-0009 co-location evidence. Enumerates EVERY indoor EnvCell that
    /// actually exists in CellDat (real file keys 0x0100..0xFFFD — not a probe,
    /// not a first-N slice), prints each cell's landblock-local Frame.Origin,
    /// the composed world position per ACViewer PositionExtensions.GetWorldPos
    /// (world = lbX*192 + Fx, lbY*192 + Fy, Fz), and whether Frame.Origin's
    /// X,Y fall inside the [0,192] landblock footprint. Also prints the
    /// Buildings count so building-interior vs zero-building blocks are labeled.
    /// Opens DATs once, so it is ~3 orders of magnitude faster than per-cell
    /// invocation. Output is the auditable artifact for ADR-0009.
    /// </summary>
    public static int DumpEnvCellPositions(ReadOnlySpan<string> args)
    {
        if (args.Length < 2) { Console.Error.WriteLine("dump-envcell-positions: missing <datDir> <hexId>"); return 1; }
        var datDir = args[0];
        if (!TryParseLandblockHex(args[1], out var lbHigh16)) { Console.Error.WriteLine($"Bad hex landblock id: {args[1]}"); return 1; }

        const int BlockLength = 192;   // ACViewer Physics/Common/LandDefs.cs:102 BlockLength
        var lbX = (int)((lbHigh16 >> 8) & 0xFF);
        var lbY = (int)(lbHigh16 & 0xFF);

        DatManager.Initialize(datDir, keepOpen: false, loadCell: true);
        var cellDb = DatManager.CellDat ?? throw new InvalidOperationException("CellDat unavailable.");

        int buildings = 0, numCells = 0;
        var infoFileId = (lbHigh16 << 16) | 0xFFFEu;
        if (cellDb.AllFiles.ContainsKey(infoFileId))
        {
            var info = cellDb.ReadFromDat<ACE.DatLoader.FileTypes.LandblockInfo>(infoFileId);
            buildings = info.Buildings?.Count ?? 0;
            numCells = (int)info.NumCells;
        }

        var minId = (lbHigh16 << 16) | 0x0100u;
        var maxId = (lbHigh16 << 16) | 0xFFFDu;
        var ids = cellDb.AllFiles.Keys.Where(id => id >= minId && id <= maxId).OrderBy(id => id).ToList();

        Console.WriteLine("================================================================");
        Console.WriteLine($"LANDBLOCK 0x{lbHigh16:X4}  (LbX={lbX}, LbY={lbY})  Buildings={buildings}  NumCells={numCells}  EnvCellFiles={ids.Count}");
        Console.WriteLine("----------------------------------------------------------------");
        Console.WriteLine("  CellId        Frame.Origin(x,y,z)              World(x,y,z)        InFootprint?");

        double minX = double.PositiveInfinity, maxX = double.NegativeInfinity;
        double minY = double.PositiveInfinity, maxY = double.NegativeInfinity;
        double minZ = double.PositiveInfinity, maxZ = double.NegativeInfinity;
        int inFoot = 0, outFoot = 0, n = 0;
        foreach (var id in ids)
        {
            var ec = cellDb.ReadFromDat<EnvCell>(id);
            if (ec.Position is null) continue;
            double fx = ec.Position.Origin.X, fy = ec.Position.Origin.Y, fz = ec.Position.Origin.Z;
            double wx = lbX * BlockLength + fx, wy = lbY * BlockLength + fy, wz = fz;
            bool isIn = fx >= 0 && fx <= BlockLength && fy >= 0 && fy <= BlockLength;
            if (isIn) inFoot++; else outFoot++;
            if (fx < minX) minX = fx; if (fx > maxX) maxX = fx;
            if (fy < minY) minY = fy; if (fy > maxY) maxY = fy;
            if (fz < minZ) minZ = fz; if (fz > maxZ) maxZ = fz;
            n++;
            Console.WriteLine($"  0x{id:X8}   ({fx,8:F2},{fy,9:F2},{fz,8:F2})   ({wx,10:F2},{wy,11:F2},{wz,8:F2})   {(isIn ? "IN" : "OUT")}");
        }

        Console.WriteLine();
        Console.WriteLine($"  SUMMARY 0x{lbHigh16:X4}: cells_with_position={n}");
        if (n > 0)
            Console.WriteLine($"  Frame.Origin bbox: X[{minX:F2}..{maxX:F2}] Y[{minY:F2}..{maxY:F2}] Z[{minZ:F2}..{maxZ:F2}]");
        Console.WriteLine($"  Cells with Frame.Origin inside [0,{BlockLength}] on BOTH X and Y: {inFoot}");
        Console.WriteLine($"  Cells with Frame.Origin OUTSIDE that footprint: {outFoot}");
        Console.WriteLine();
        return 0;
    }

    /// <summary>
    /// Academy-wide invariant check: for every EnvCell in a landblock, verify that
    /// the set of polygons with Stippling == NoPos equals CellStruct.Portals equals
    /// the set of EnvCell.CellPortals PolygonIds. Proves the render-skip criterion
    /// (Stippling == NoPos, used by ExportEnvCell, mirroring ACViewer) is exactly the
    /// portal set, so skipping NoPos drops portals and only portals — academy-wide,
    /// not just for one room. Read-only.
    /// </summary>
    public static int AuditPortals(ReadOnlySpan<string> args)
    {
        if (args.Length < 2) { Console.Error.WriteLine("audit-portals: missing <datDir> <hexLandblockId>"); return 1; }
        var datDir = args[0];
        if (!TryParseLandblockHex(args[1], out var lbHigh16)) { Console.Error.WriteLine($"Bad hex landblock id: {args[1]}"); return 1; }

        DatManager.Initialize(datDir, keepOpen: false, loadCell: true);
        var cellDb = DatManager.CellDat ?? throw new InvalidOperationException("CellDat unavailable.");
        var portalDb = DatManager.PortalDat ?? throw new InvalidOperationException("PortalDat unavailable.");

        var minId = (lbHigh16 << 16) | 0x0100u;
        var maxId = (lbHigh16 << 16) | 0xFFFDu;
        var ids = cellDb.AllFiles.Keys.Where(id => id >= minId && id <= maxId).OrderBy(id => id).ToList();

        int cells = 0, notSubset = 0, totalNoPos = 0, totalPortals = 0, renderedPortals = 0;
        foreach (var id in ids)
        {
            var ec = cellDb.ReadFromDat<EnvCell>(id);
            var env = portalDb.ReadFromDat<ACE.DatLoader.FileTypes.Environment>(ec.EnvironmentId);
            if (!env.Cells.TryGetValue(ec.CellStructure, out var cs)) continue;
            cells++;

            var noPos = cs.Polygons.Where(kv => kv.Value.Stippling == StipplingType.NoPos)
                                   .Select(kv => kv.Key).OrderBy(k => k).ToList();
            var structPortals = new HashSet<ushort>(cs.Portals);
            totalNoPos += noPos.Count;
            totalPortals += structPortals.Count;
            // Every NoPos polygon must be a declared portal. (The reverse need NOT
            // hold: a portal has two sides — the see-through side is NoPos and is
            // skipped; the opposite side is a normal rendered surface, e.g. the
            // wood-beam floor of the cell above appears through the room's ceiling.)
            renderedPortals += structPortals.Count(p => !noPos.Contains(p));
            var notPortal = noPos.Where(p => !structPortals.Contains(p)).ToList();
            if (notPortal.Count > 0)
            {
                notSubset++;
                Console.WriteLine($"  NOT-A-PORTAL 0x{id:X8}: NoPos polys not in Portals = [{string.Join(",", notPortal)}]");
            }
        }
        Console.WriteLine($"Audited {cells} EnvCells in landblock 0x{lbHigh16:X4}: {totalNoPos} NoPos(skipped) polys, {totalPortals} portal polys ({renderedPortals} rendered portal sides), {notSubset} cell(s) where a skipped poly is NOT a portal.");
        Console.WriteLine(notSubset == 0
            ? "  INVARIANT HOLDS: every skipped (NoPos) polygon is a declared portal — the fix never drops real geometry. (Portals are a superset; their rendered sides are kept.)"
            : "  INVARIANT VIOLATED: some NoPos polygons are NOT portals (see above) — skipping them could drop real geometry.");
        return notSubset == 0 ? 0 : 2;
    }

    /// <summary>
    /// Verification tool: dump each polygon's Stippling flag, sidedness,
    /// surfaces, and vertex Z-range (AC native coords) for one EnvCell, plus
    /// the CellStruct.Portals list (portal polygon ids) and EnvCell.CellPortals
    /// (PolygonId -> OtherCellId). Used to confirm which polygons are the
    /// see-through portal faces that ACViewer's renderer skips
    /// (Stippling == NoPos). Read-only; no files written.
    /// </summary>
    public static int DumpPolyStippling(ReadOnlySpan<string> args)
    {
        if (args.Length < 2) { Console.Error.WriteLine("dump-poly-stippling: missing <datDir> <fullCellId>"); return 1; }
        var datDir = args[0];
        if (!TryParseLandblockHex(args[1], out var fullId)) { Console.Error.WriteLine($"Bad hex cell id: {args[1]}"); return 1; }

        DatManager.Initialize(datDir, keepOpen: false, loadCell: true);
        var cellDb = DatManager.CellDat ?? throw new InvalidOperationException("CellDat unavailable.");
        var portalDb = DatManager.PortalDat ?? throw new InvalidOperationException("PortalDat unavailable.");
        if (!cellDb.AllFiles.ContainsKey(fullId)) { Console.Error.WriteLine($"No cell at 0x{fullId:X8}."); return 3; }
        var ec = cellDb.ReadFromDat<EnvCell>(fullId);
        var env = portalDb.ReadFromDat<ACE.DatLoader.FileTypes.Environment>(ec.EnvironmentId);
        if (!env.Cells.TryGetValue(ec.CellStructure, out var cs))
        { Console.Error.WriteLine($"No CellStructure {ec.CellStructure}."); return 5; }

        Console.WriteLine($"EnvCell 0x{fullId:X8}  Env 0x{ec.EnvironmentId:X8}  CellStruct {ec.CellStructure}");
        Console.WriteLine($"  polys={cs.Polygons.Count}  verts={cs.VertexArray.Vertices.Count}");
        Console.WriteLine($"  CellStruct.Portals (portal polygon ids): [{string.Join(",", cs.Portals)}]");
        if (ec.CellPortals != null && ec.CellPortals.Count > 0)
        {
            Console.WriteLine($"  EnvCell.CellPortals ({ec.CellPortals.Count}):");
            foreach (var cp in ec.CellPortals)
                Console.WriteLine($"    Flags={cp.Flags} PolygonId={cp.PolygonId} OtherCellId=0x{cp.OtherCellId:X4} OtherPortalId={cp.OtherPortalId}");
        }
        Console.WriteLine($"  per-polygon (key id : Stippling SidesType PosSurf NegSurf NumPts Zrange[AC]):");
        foreach (var kv in cs.Polygons.OrderBy(k => k.Key))
        {
            var p = kv.Value;
            float zmin = float.MaxValue, zmax = float.MinValue;
            foreach (var vid in p.VertexIds)
            {
                var z = cs.VertexArray.Vertices[(ushort)vid].Origin.Z;
                if (z < zmin) zmin = z;
                if (z > zmax) zmax = z;
            }
            bool isPortal = cs.Portals.Contains(kv.Key);
            Console.WriteLine($"    id={kv.Key,-3} Stippling={p.Stippling}(0x{(int)p.Stippling:X}) Sides={p.SidesType} PosSurf={p.PosSurface} NegSurf={p.NegSurface} NumPts={p.NumPts} Z=[{zmin:F1},{zmax:F1}]{(isPortal ? "  <-- in Portals" : "")}");
        }
        return 0;
    }

    /// <summary>
    /// Verification tool: report each polygon's VertexIds + PosUVIndices and
    /// how many UVs each vertex carries, for one EnvCell. If PosUVIndices are
    /// all 0 and every vertex has a single UV, the old UVs[0] export happened
    /// to be correct for this cell; otherwise per-corner UV selection matters.
    /// </summary>
    public static int DumpPolyUVs(ReadOnlySpan<string> args)
    {
        if (args.Length < 2) { Console.Error.WriteLine("dump-poly-uvs: missing <datDir> <fullCellId>"); return 1; }
        var datDir = args[0];
        if (!TryParseLandblockHex(args[1], out var fullId)) { Console.Error.WriteLine($"Bad hex cell id: {args[1]}"); return 1; }

        DatManager.Initialize(datDir, keepOpen: false, loadCell: true);
        var cellDb = DatManager.CellDat ?? throw new InvalidOperationException("CellDat unavailable.");
        var portalDb = DatManager.PortalDat ?? throw new InvalidOperationException("PortalDat unavailable.");
        if (!cellDb.AllFiles.ContainsKey(fullId)) { Console.Error.WriteLine($"No cell at 0x{fullId:X8}."); return 3; }
        var ec = cellDb.ReadFromDat<EnvCell>(fullId);
        var env = portalDb.ReadFromDat<ACE.DatLoader.FileTypes.Environment>(ec.EnvironmentId);
        if (!env.Cells.TryGetValue(ec.CellStructure, out var cs))
        { Console.Error.WriteLine($"No CellStructure {ec.CellStructure}."); return 5; }

        int multiUvVerts = 0, maxUVs = 0;
        foreach (var kv in cs.VertexArray.Vertices)
        {
            int n = kv.Value.UVs?.Count ?? 0;
            if (n > 1) multiUvVerts++;
            if (n > maxUVs) maxUVs = n;
        }
        int nonZeroCorners = 0, totalCorners = 0, maxIdx = 0;
        foreach (var poly in cs.Polygons.Values)
        {
            var ids = poly.PosUVIndices;
            int corners = poly.VertexIds?.Count ?? 0;
            for (int i = 0; i < corners; i++)
            {
                totalCorners++;
                int uvi = (ids != null && i < ids.Count) ? ids[i] : 0;
                if (uvi != 0) nonZeroCorners++;
                if (uvi > maxIdx) maxIdx = uvi;
            }
        }
        Console.WriteLine($"EnvCell 0x{fullId:X8}  Env 0x{ec.EnvironmentId:X8}  CellStruct {ec.CellStructure}");
        Console.WriteLine($"  vertices={cs.VertexArray.Vertices.Count}  polys={cs.Polygons.Count}");
        Console.WriteLine($"  verts with >1 UV: {multiUvVerts}  (max UVs on a vertex: {maxUVs})");
        Console.WriteLine($"  polygon corners with non-zero PosUVIndex: {nonZeroCorners}/{totalCorners}  (max index: {maxIdx})");
        Console.WriteLine(nonZeroCorners == 0 && maxUVs <= 1
            ? "  => UVs[0] export was CORRECT for this cell (no per-corner UV selection needed)."
            : "  => per-corner PosUVIndices MATTER for this cell; the old UVs[0] export would mismap.");
        int shown = 0;
        foreach (var poly in cs.Polygons.Values)
        {
            if (shown++ >= 8) break;
            var vids = poly.VertexIds != null ? string.Join(",", poly.VertexIds) : "";
            var uvis = poly.PosUVIndices != null ? string.Join(",", poly.PosUVIndices) : "(none)";
            Console.WriteLine($"  poly surf={poly.PosSurface} V=[{vids}] PosUV=[{uvis}]");
        }
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
        // UVs: emit one vt per (vertex, UV-index). An SWVertex can carry several
        // UVs; each polygon corner selects which one via PosUVIndices. The old
        // code emitted only UVs[0] per vertex and ignored PosUVIndices, which
        // mismaps any face referencing a non-zero UV index. Correct behavior
        // confirmed against ACViewer FileExport.cs (it emits vt per v.UVs[j]
        // and indexes faces by poly.PosUVIndices[i]). Position/normal stay
        // indexed by vertex id; only vt uses uvKeyToObjVt.
        var uvKeyToObjVt = new Dictionary<(ushort vid, int uvi), int>();
        int nextVt = 1;
        for (int i = 0; i < vertOrder.Count; i++)
        {
            ushort vid = vertOrder[i];
            var sv = cs.VertexArray.Vertices[vid];
            if (sv.UVs != null && sv.UVs.Count > 0)
            {
                for (int j = 0; j < sv.UVs.Count; j++)
                {
                    sw.WriteLine($"vt {sv.UVs[j].U:R} {sv.UVs[j].V:R}");
                    uvKeyToObjVt[(vid, j)] = nextVt++;
                }
            }
            else
            {
                sw.WriteLine($"vt 0 0");
                uvKeyToObjVt[(vid, 0)] = nextVt++;
            }
        }

        // Group polygons by PosSurface (index into EnvCell.Surfaces) and emit each group.
        // Skip portal polygons: a polygon whose Stippling == NoPos has no positive
        // surface to draw — it is a see-through cell-to-cell connection (doorway /
        // floor-ceiling opening). AC's renderer never draws these; the adjacent
        // EnvCell is what you see through the opening. Confirmed against ACViewer
        // Render/R_CellStruct.cs Draw(): `if (polygon._polygon.Stippling ==
        // StipplingType.NoPos) continue;`. Cross-checked against the DAT: for cell
        // 0x860201AD the only NoPos polys (ids 12,13, surface "surf_2") are exactly
        // CellStruct.Portals=[12,13] — poly 12 -> OtherCellId 0x01B4 (hallway), poly
        // 13 -> OtherCellId 0x02E2 (the wood-beam cell above). Emitting them as solid
        // surfaces was occluding the adjacent cells (the black "ceiling"/doorway bug).
        // This is the GENERAL rule for every academy cell, not a per-room patch.
        int triEmitted = 0;
        int polysSkipped = 0;
        var renderPolys = cs.Polygons.Values
            .Where(p => p.Stippling != StipplingType.NoPos)
            .ToList();
        int portalPolysSkipped = cs.Polygons.Count - renderPolys.Count;
        var groups = renderPolys
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

                // Resolve the OBJ vt slot for polygon corner c. AC selects the
                // per-corner UV via PosUVIndices[c] (parallel to VertexIds); when
                // that array is absent (NoPos stippling) the vertex's sole UV
                // (index 0) is used. Position/normal stay indexed by vertex id;
                // only the texture coordinate uses uvKeyToObjVt. Mirrors ACViewer
                // FileExport.cs: vertexUVs[(v, i < PosUVIndices.Count ? PosUVIndices[i] : 0)].
                int VtForCorner(int c)
                {
                    ushort cvid = (ushort)poly.VertexIds[c];
                    int uvi = (poly.PosUVIndices != null && c < poly.PosUVIndices.Count)
                        ? poly.PosUVIndices[c]
                        : 0;
                    if (!uvKeyToObjVt.TryGetValue((cvid, uvi), out int vt))
                        vt = uvKeyToObjVt[(cvid, 0)]; // fallback to first UV emitted for this vertex
                    return vt;
                }

                int p0 = idToObjIndex[(ushort)poly.VertexIds[0]];
                int t0 = VtForCorner(0);
                for (int i = 1; i + 1 < poly.NumPts; i++)
                {
                    int pa = idToObjIndex[(ushort)poly.VertexIds[i]];
                    int pb = idToObjIndex[(ushort)poly.VertexIds[i + 1]];
                    int ta = VtForCorner(i);
                    int tb = VtForCorner(i + 1);
                    // Winding swap: emit (v0, vb, va) instead of (v0, va, vb)
                    // to compensate for the chirality flip from the X-Y axis swap.
                    sw.WriteLine($"f {p0}/{t0}/{p0} {pb}/{tb}/{pb} {pa}/{ta}/{pa}");
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
        Console.WriteLine($"  Cell 0x{fullId:X8}: {vertCount} verts, {polyCount} polys -> {triEmitted} triangles ({polysSkipped} degenerate skipped, {portalPolysSkipped} portal/NoPos skipped)");
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

    // =========================================================================
    // Phase 5f: static-objects extraction.
    //
    // EnvCell.StaticObjects (the "Stab" list) is the per-cell prop array:
    // fireplaces, chairs, signs, tables, beds, lecterns, training dummies, etc.
    // Each Stab is { Id = SetupModel ID (0x02), Frame = position+orientation
    // *relative to the cell origin* }.
    //
    // A SetupModel (0x02) is itself a multi-part container: it owns a list of
    // GfxObj (0x01) "Parts", a per-part PlacementFrame within the setup, and
    // per-part DefaultScale. Most academy props are single-part, but some
    // (fireplaces with andirons + grates + logs) decompose into 3+ parts.
    //
    // For UE we merge a Setup's parts into one StaticMesh, pre-transforming
    // each part by its placement frame + scale. Surfaces are dedup'd across
    // parts so a sign with two repeated panels emits one texture, not two.
    // =========================================================================

    /// <summary>
    /// Walk every EnvCell in a landblock and emit one JSON file enumerating
    /// the StaticObjects in each cell (with their setup IDs and world-space
    /// position/orientation in UE coords). UE-side import consumes this to
    /// spawn one StaticMeshActor per Stab.
    /// </summary>
    public static int DumpAcademyStatics(ReadOnlySpan<string> args)
    {
        if (args.Length < 3) { Console.Error.WriteLine("dump-academy-statics: missing <datDir> <hexLandblockId> <out.json>"); return 1; }
        var datDir = args[0];
        if (!TryParseLandblockHex(args[1], out var lbHigh16)) { Console.Error.WriteLine($"Bad hex landblock id: {args[1]}"); return 1; }
        var outPath = args[2];

        DatManager.Initialize(datDir, keepOpen: false, loadCell: true);
        var cellDb = DatManager.CellDat ?? throw new InvalidOperationException("CellDat unavailable.");

        var minId = (lbHigh16 << 16) | 0x0100u;
        var maxId = (lbHigh16 << 16) | 0xFFFDu;
        var envCellIds = cellDb.AllFiles.Keys.Where(id => id >= minId && id <= maxId).OrderBy(id => id).ToList();

        const float kCmPerMetre = 100.0f;

        // BUGFIX 2026-05-31: EnvCell.StaticObjects[].Frame is landblock-ABSOLUTE
        // (same as the lights fix in DumpAcademyLights). The old code composed
        // cell.world ⊕ stab.local (cellPos + RotateAcVec(cellOrient, localPos)),
        // which doubled coordinates because stab.Frame already includes the cell
        // offset (verified: identity-orientation cells placed stabs at 2× cellPos).
        // Use stab.Frame directly; only the AC→UE axis swap is applied below.
        // cellPos/cellOrient and the quaternion/rotation helpers are no longer
        // needed here.

        var allInstances = new List<object>();
        var uniqueSetups = new HashSet<uint>();
        int cellsWithStatics = 0;

        foreach (var id in envCellIds)
        {
            var ec = cellDb.ReadFromDat<EnvCell>(id);
            if (ec.StaticObjects == null || ec.StaticObjects.Count == 0) continue;
            cellsWithStatics++;

            foreach (var stab in ec.StaticObjects)
            {
                uniqueSetups.Add(stab.Id);

                // stab.Frame is landblock-absolute (see BUGFIX note above): use it directly.
                var worldPosAc = (x: stab.Frame.Origin.X, y: stab.Frame.Origin.Y, z: stab.Frame.Origin.Z);
                var worldOrientAc = (
                    x: stab.Frame.Orientation.X,
                    y: stab.Frame.Orientation.Y,
                    z: stab.Frame.Orientation.Z,
                    w: stab.Frame.Orientation.W);

                allInstances.Add(new
                {
                    cell_id = $"0x{id:X8}",
                    setup_id = $"0x{stab.Id:X8}",
                    setup_asset_name = $"SM_Setup_{stab.Id:X8}",
                    // UE-coords (cm).
                    position = new
                    {
                        x = worldPosAc.y * kCmPerMetre,
                        y = worldPosAc.x * kCmPerMetre,
                        z = worldPosAc.z * kCmPerMetre,
                    },
                    // UE-basis quaternion (w, -y, -x, -z).
                    orientation = new
                    {
                        w =  worldOrientAc.w,
                        x = -worldOrientAc.y,
                        y = -worldOrientAc.x,
                        z = -worldOrientAc.z,
                    },
                });
            }
        }

        var doc = new
        {
            schema_version = 1,
            landblock_id = $"0x{lbHigh16:X4}",
            coordinate_system = "UE-ready: left-handed Z-up, centimetres. World-space positions; stab.local has been composed with cell.world before the AC->UE transform.",
            instance_count = allInstances.Count,
            unique_setup_count = uniqueSetups.Count,
            cells_with_statics = cellsWithStatics,
            unique_setups = uniqueSetups.OrderBy(x => x).Select(x => $"0x{x:X8}").ToList(),
            instances = allInstances,
        };

        var json = JsonSerializer.Serialize(doc, new JsonSerializerOptions { WriteIndented = true });
        var dir = Path.GetDirectoryName(outPath);
        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
        File.WriteAllText(outPath, json);

        Console.WriteLine($"Wrote statics JSON to {outPath}");
        Console.WriteLine($"  {allInstances.Count} instances across {cellsWithStatics} cells");
        Console.WriteLine($"  {uniqueSetups.Count} unique setups");
        return 0;
    }

    /// <summary>
    /// Walk every Stab in a landblock, look up its SetupModel's Lights,
    /// compose cell.world * setup.local * light.local frames, emit a
    /// JSON with world-space point/spot light data in UE coords.
    /// Bare-GfxObj stabs (0x01 Id) have no lights and are skipped.
    /// </summary>
    public static int DumpAcademyLights(ReadOnlySpan<string> args)
    {
        if (args.Length < 3) { Console.Error.WriteLine("dump-academy-lights: missing <datDir> <hexLandblockId> <out.json>"); return 1; }
        var datDir = args[0];
        if (!TryParseLandblockHex(args[1], out var lbHigh16)) { Console.Error.WriteLine($"Bad hex landblock id: {args[1]}"); return 1; }
        var outPath = args[2];

        DatManager.Initialize(datDir, keepOpen: false, loadCell: true);
        var cellDb = DatManager.CellDat ?? throw new InvalidOperationException("CellDat unavailable.");
        var portalDb = DatManager.PortalDat ?? throw new InvalidOperationException("PortalDat unavailable.");

        var minId = (lbHigh16 << 16) | 0x0100u;
        var maxId = (lbHigh16 << 16) | 0xFFFDu;
        var envCellIds = cellDb.AllFiles.Keys.Where(id => id >= minId && id <= maxId).OrderBy(id => id).ToList();

        const float kCmPerMetre = 100.0f;

        // (Lights use only RotateAcVec — the stab frame is landblock-absolute,
        // so there is no cell-orientation quaternion to compose here.)
        static (float x, float y, float z) RotateAcVec((float x, float y, float z, float w) q, (float x, float y, float z) v)
        {
            float qx = q.x, qy = q.y, qz = q.z, qw = q.w;
            float tx = 2 * (qy * v.z - qz * v.y);
            float ty = 2 * (qz * v.x - qx * v.z);
            float tz = 2 * (qx * v.y - qy * v.x);
            return (
                v.x + qw * tx + (qy * tz - qz * ty),
                v.y + qw * ty + (qz * tx - qx * tz),
                v.z + qw * tz + (qx * ty - qy * tx));
        }

        // Cache: setup_id -> (has_lights, lights_data)
        var setupLightsCache = new Dictionary<uint, List<(System.Numerics.Vector3 pos, System.Numerics.Quaternion orient, uint color, float intensity, float falloff, float cone)>>();

        List<(System.Numerics.Vector3 pos, System.Numerics.Quaternion orient, uint color, float intensity, float falloff, float cone)> GetLights(uint setupId)
        {
            if (setupLightsCache.TryGetValue(setupId, out var cached)) return cached;
            var list = new List<(System.Numerics.Vector3, System.Numerics.Quaternion, uint, float, float, float)>();
            uint typeNibble = (setupId >> 24) & 0xFFu;
            if (typeNibble == 0x02 && portalDb.AllFiles.ContainsKey(setupId))
            {
                try
                {
                    var setup = portalDb.ReadFromDat<SetupModel>(setupId);
                    if (setup.Lights != null)
                    {
                        foreach (var kv in setup.Lights)
                        {
                            var li = kv.Value;
                            list.Add((li.ViewerSpaceLocation.Origin, li.ViewerSpaceLocation.Orientation,
                                      li.Color, li.Intensity, li.Falloff, li.ConeAngle));
                        }
                    }
                }
                catch { /* swallow; skip lights for malformed setups */ }
            }
            setupLightsCache[setupId] = list;
            return list;
        }

        // Decode AC's _RGB color: bytes are [00 RR GG BB] (high byte usually 0xFF or 0x00).
        // Return (r, g, b) in 0..1.
        static (float r, float g, float b) DecodeAcColor(uint c)
        {
            float r = ((c >> 16) & 0xFF) / 255.0f;
            float g = ((c >> 8) & 0xFF) / 255.0f;
            float b = ((c >> 0) & 0xFF) / 255.0f;
            return (r, g, b);
        }

        var allLights = new List<object>();
        int warmLightCount = 0;
        foreach (var cellId in envCellIds)
        {
            var ec = cellDb.ReadFromDat<EnvCell>(cellId);
            if (ec.StaticObjects == null || ec.StaticObjects.Count == 0) continue;

            foreach (var stab in ec.StaticObjects)
            {
                var lights = GetLights(stab.Id);
                if (lights.Count == 0) continue;

                // BUGFIX 2026-05-30: stab.Frame is ALREADY landblock-absolute
                // for EnvCell StaticObjects -- it is NOT cell-local. Verified:
                // for identity-orientation cells stab.Frame.Origin equals the
                // cell's EnvCell.Position.Origin, and the previous
                // "cellPos + RotateAcVec(cellOrient, stabLocalPos)" form placed
                // every light at exactly 2x the cell position (doubling cellPos).
                // So use the stab frame directly -- do NOT re-add cellPos or
                // re-apply cellOrient. (ec.Position is intentionally unused now.)
                var stabWorldPos = (x: stab.Frame.Origin.X, y: stab.Frame.Origin.Y, z: stab.Frame.Origin.Z);
                var stabWorldOrient = (
                    x: stab.Frame.Orientation.X,
                    y: stab.Frame.Orientation.Y,
                    z: stab.Frame.Orientation.Z,
                    w: stab.Frame.Orientation.W);

                foreach (var light in lights)
                {
                    var lightLocalPos = (x: light.pos.X, y: light.pos.Y, z: light.pos.Z);
                    // Light world position: stabWorld.pos + stabWorld.rot * light.local.pos
                    var rotLight = RotateAcVec(stabWorldOrient, lightLocalPos);
                    var lightWorldPosAc = (x: stabWorldPos.x + rotLight.x, y: stabWorldPos.y + rotLight.y, z: stabWorldPos.z + rotLight.z);

                    var (r, g, b) = DecodeAcColor(light.color);
                    // Tag "fire-like" lights for Phase 5h to attach effects.
                    bool isWarm = r >= 0.4f && r >= g && g >= b && (r - b) >= 0.15f;
                    if (isWarm) warmLightCount++;

                    allLights.Add(new
                    {
                        cell_id = $"0x{cellId:X8}",
                        setup_id = $"0x{stab.Id:X8}",
                        // UE-coords (cm).
                        position = new
                        {
                            x = lightWorldPosAc.y * kCmPerMetre,
                            y = lightWorldPosAc.x * kCmPerMetre,
                            z = lightWorldPosAc.z * kCmPerMetre,
                        },
                        color_rgb = new { r, g, b },
                        color_raw = $"0x{light.color:X8}",
                        intensity = light.intensity,
                        falloff = light.falloff,
                        cone_angle_degrees = light.cone * 180.0f / (float)Math.PI,
                        is_point_light = light.cone <= 0.001f,
                        is_warm_for_fire_fx = isWarm,
                    });
                }
            }
        }

        var doc = new
        {
            schema_version = 1,
            landblock_id = $"0x{lbHigh16:X4}",
            coordinate_system = "UE-ready: left-handed Z-up, centimetres. World-space.",
            light_count = allLights.Count,
            warm_light_count = warmLightCount,
            unique_setup_count = setupLightsCache.Count,
            lights = allLights,
        };

        var json = JsonSerializer.Serialize(doc, new JsonSerializerOptions { WriteIndented = true });
        var dir = Path.GetDirectoryName(outPath);
        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
        File.WriteAllText(outPath, json);

        Console.WriteLine($"Wrote lights JSON to {outPath}");
        Console.WriteLine($"  {allLights.Count} lights ({warmLightCount} warm/fire-like)");
        return 0;
    }

    /// <summary>
    /// Export a SetupModel (0x02xxxxxx) as a single merged OBJ.
    /// Each Part (a GfxObj 0x01) is pre-transformed by its PlacementFrame
    /// (key = Placement.Resting = 0x65) and DefaultScale before emission, so
    /// the resulting OBJ is in setup-local UE coords (cm, left-handed Z-up).
    /// </summary>
    public static int ExportSetup(ReadOnlySpan<string> args)
    {
        if (args.Length < 3) { Console.Error.WriteLine("export-setup: missing <datDir> <hexSetupId> <out.obj>"); return 1; }
        var datDir = args[0];
        if (!TryParseLandblockHex(args[1], out var setupId)) { Console.Error.WriteLine($"Bad hex setup id: {args[1]}"); return 1; }
        var outPath = args[2];

        DatManager.Initialize(datDir, keepOpen: false, loadCell: false);
        var portalDb = DatManager.PortalDat ?? throw new InvalidOperationException("PortalDat unavailable.");

        if (!portalDb.AllFiles.ContainsKey(setupId))
        {
            Console.Error.WriteLine($"Setup 0x{setupId:X8} not in PortalDat.");
            return 3;
        }

        // Stab.Id can reference either:
        //   0x02xxxxxx — SetupModel (multi-part container)
        //   0x01xxxxxx — GfxObj (raw single mesh, no setup wrapper)
        // For the GfxObj case we synthesize a 1-part "virtual setup" with
        // identity placement and unit scale so the rest of the loop just
        // works.
        uint typeNibble = (setupId >> 24) & 0xFFu;

        List<uint> parts;
        ACE.DatLoader.Entity.PlacementType? placement;
        List<System.Numerics.Vector3>? defaultScales;

        if (typeNibble == 0x02)
        {
            var setup = portalDb.ReadFromDat<SetupModel>(setupId);
            if (setup.Parts == null || setup.Parts.Count == 0)
            {
                Console.Error.WriteLine($"Setup 0x{setupId:X8} has no Parts.");
                return 4;
            }
            parts = setup.Parts;
            const int RestingPlacement = 0x65;
            placement = setup.PlacementFrames.TryGetValue(RestingPlacement, out var pf) ? pf : null;
            defaultScales = (setup.DefaultScale != null && setup.DefaultScale.Count == parts.Count) ? setup.DefaultScale : null;
        }
        else if (typeNibble == 0x01)
        {
            // Bare GfxObj — wrap as one-part synthetic setup.
            parts = new List<uint> { setupId };
            placement = null;
            defaultScales = null;
        }
        else
        {
            Console.Error.WriteLine($"Id 0x{setupId:X8} is not a SetupModel (0x02) or GfxObj (0x01).");
            return 5;
        }

        var outDir = Path.GetDirectoryName(outPath);
        if (!string.IsNullOrEmpty(outDir)) Directory.CreateDirectory(outDir);
        var texDir = Path.Combine(string.IsNullOrEmpty(outDir) ? "." : outDir, "textures");
        Directory.CreateDirectory(texDir);

        const float kCmPerMetre = 100.0f;
        var objBaseName = Path.GetFileNameWithoutExtension(outPath);
        var mtlPath = Path.Combine(outDir ?? ".", objBaseName + ".mtl");

        var hasDefaultScale = defaultScales != null;

        using var sw = new StreamWriter(outPath);
        sw.WriteLine($"# Exported by acdat from 0x{setupId:X8} (type 0x{typeNibble:X2}: {(typeNibble == 0x02 ? "SetupModel" : "GfxObj")})");
        sw.WriteLine($"# {parts.Count} parts, merged into one OBJ");
        sw.WriteLine($"# UE-ready coords: left-handed Z-up, centimetres. Setup-local origin.");
        sw.WriteLine($"mtllib {objBaseName}.mtl");
        sw.WriteLine($"o setup_{setupId:X8}");

        int globalVertOffset = 0;
        var allMtls = new Dictionary<string, (uint surfaceId, uint? textureId)>();
        int totalTris = 0;

        for (int partIdx = 0; partIdx < parts.Count; partIdx++)
        {
            uint gfxId = parts[partIdx];
            if (!portalDb.AllFiles.ContainsKey(gfxId))
            {
                Console.Error.WriteLine($"  WARN: GfxObj 0x{gfxId:X8} (part {partIdx}) not in PortalDat — skipping");
                continue;
            }
            var gfx = portalDb.ReadFromDat<GfxObj>(gfxId);
            if (gfx.VertexArray.Vertices.Count == 0 || gfx.Polygons.Count == 0)
                continue;

            float fx = 0, fy = 0, fz = 0;
            float qx = 0, qy = 0, qz = 0, qw = 1;
            if (placement != null && partIdx < placement.AnimFrame.Frames.Count)
            {
                var f = placement.AnimFrame.Frames[partIdx];
                fx = f.Origin.X; fy = f.Origin.Y; fz = f.Origin.Z;
                qx = f.Orientation.X; qy = f.Orientation.Y; qz = f.Orientation.Z; qw = f.Orientation.W;
            }
            float sx = 1, sy = 1, sz = 1;
            if (hasDefaultScale && defaultScales != null)
            {
                var s = defaultScales[partIdx];
                sx = s.X; sy = s.Y; sz = s.Z;
            }

            static (float x, float y, float z) RotAcQ(float qx, float qy, float qz, float qw, float vx, float vy, float vz)
            {
                float tx = 2 * (qy * vz - qz * vy);
                float ty = 2 * (qz * vx - qx * vz);
                float tz = 2 * (qx * vy - qy * vx);
                return (
                    vx + qw * tx + (qy * tz - qz * ty),
                    vy + qw * ty + (qz * tx - qx * tz),
                    vz + qw * tz + (qx * ty - qy * tx));
            }

            var vertOrder = gfx.VertexArray.Vertices.Keys.OrderBy(k => k).ToList();
            var idToObjIndex = new Dictionary<ushort, int>(vertOrder.Count);

            for (int i = 0; i < vertOrder.Count; i++)
            {
                var sv = gfx.VertexArray.Vertices[vertOrder[i]];
                float lx = sv.Origin.X * sx, ly = sv.Origin.Y * sy, lz = sv.Origin.Z * sz;
                var rotated = RotAcQ(qx, qy, qz, qw, lx, ly, lz);
                float ax = rotated.x + fx, ay = rotated.y + fy, az = rotated.z + fz;
                sw.WriteLine($"v {ay * kCmPerMetre:R} {ax * kCmPerMetre:R} {az * kCmPerMetre:R}");
                idToObjIndex[vertOrder[i]] = globalVertOffset + i + 1;
            }
            for (int i = 0; i < vertOrder.Count; i++)
            {
                var sv = gfx.VertexArray.Vertices[vertOrder[i]];
                var rn = RotAcQ(qx, qy, qz, qw, sv.Normal.X, sv.Normal.Y, sv.Normal.Z);
                sw.WriteLine($"vn {rn.y:R} {rn.x:R} {rn.z:R}");
            }
            for (int i = 0; i < vertOrder.Count; i++)
            {
                var sv = gfx.VertexArray.Vertices[vertOrder[i]];
                if (sv.UVs != null && sv.UVs.Count > 0)
                    sw.WriteLine($"vt {sv.UVs[0].U:R} {sv.UVs[0].V:R}");
                else
                    sw.WriteLine($"vt 0 0");
            }

            var groups = gfx.Polygons.Values
                .GroupBy(p => (int)p.PosSurface)
                .OrderBy(g => g.Key);

            foreach (var grp in groups)
            {
                int surfIdx = grp.Key;
                string mtlName = $"part{partIdx:D2}_surf{surfIdx}";
                if (!allMtls.ContainsKey(mtlName))
                {
                    uint surfaceId = (surfIdx >= 0 && surfIdx < gfx.Surfaces.Count) ? gfx.Surfaces[surfIdx] : 0u;
                    uint? textureId = null;
                    if (surfaceId != 0 && portalDb.AllFiles.ContainsKey(surfaceId))
                    {
                        var surface = portalDb.ReadFromDat<Surface>(surfaceId);
                        var isImage = surface.Type.HasFlag(ACE.Entity.Enum.SurfaceType.Base1Image)
                                   || surface.Type.HasFlag(ACE.Entity.Enum.SurfaceType.Base1ClipMap);
                        if (isImage && surface.OrigTextureId != 0
                            && portalDb.AllFiles.ContainsKey(surface.OrigTextureId))
                        {
                            var sfcTex = portalDb.ReadFromDat<SurfaceTexture>(surface.OrigTextureId);
                            if (sfcTex.Textures.Count > 0)
                                textureId = sfcTex.Textures[sfcTex.Textures.Count - 1];
                        }
                    }
                    allMtls[mtlName] = (surfaceId, textureId);
                }

                sw.WriteLine($"g {mtlName}");
                sw.WriteLine($"usemtl {mtlName}");
                foreach (var poly in grp)
                {
                    if (poly.NumPts < 3) continue;
                    if (poly.VertexIds == null || poly.VertexIds.Count < poly.NumPts) continue;

                    int v0 = idToObjIndex[(ushort)poly.VertexIds[0]];
                    for (int i = 1; i + 1 < poly.NumPts; i++)
                    {
                        int va = idToObjIndex[(ushort)poly.VertexIds[i]];
                        int vb = idToObjIndex[(ushort)poly.VertexIds[i + 1]];
                        sw.WriteLine($"f {v0}/{v0}/{v0} {vb}/{vb}/{vb} {va}/{va}/{va}");
                        totalTris++;
                    }
                }
            }

            globalVertOffset += vertOrder.Count;
        }
        sw.Flush();

        int texturesWritten = 0;
        using (var mtl = new StreamWriter(mtlPath))
        {
            mtl.WriteLine($"# Materials for setup_{setupId:X8}");
            mtl.WriteLine();
            foreach (var kvp in allMtls)
            {
                mtl.WriteLine($"newmtl {kvp.Key}");
                mtl.WriteLine("Ka 0.1 0.1 0.1");
                mtl.WriteLine("Kd 1.0 1.0 1.0");
                mtl.WriteLine("d  1.0");
                mtl.WriteLine("illum 1");
                if (kvp.Value.textureId.HasValue && portalDb.AllFiles.ContainsKey(kvp.Value.textureId.Value))
                {
                    var tex = portalDb.ReadFromDat<Texture>(kvp.Value.textureId.Value);
                    string ext = tex.Format == ACE.Entity.Enum.SurfacePixelFormat.PFID_CUSTOM_RAW_JPEG ? ".jpg" : ".png";
                    string texFileName = $"{kvp.Value.textureId.Value:X8}{ext}";
                    string texPath = Path.Combine(texDir, texFileName);
                    if (!File.Exists(texPath))
                    {
                        try { tex.ExportTexture(texDir); texturesWritten++; }
                        catch (Exception ex) { mtl.WriteLine($"# (texture export failed: {ex.Message})"); }
                    }
                    mtl.WriteLine($"# Texture 0x{kvp.Value.textureId.Value:X8} {tex.Width}x{tex.Height} {tex.Format}");
                    mtl.WriteLine($"map_Kd textures/{texFileName}");
                }
                else
                {
                    mtl.WriteLine($"# Surface 0x{kvp.Value.surfaceId:X8} (no extractable texture)");
                }
                mtl.WriteLine();
            }
        }

        Console.WriteLine($"Wrote {new FileInfo(outPath).Length} bytes to {outPath}");
        Console.WriteLine($"  0x{setupId:X8}: {parts.Count} parts -> {totalTris} triangles, {allMtls.Count} mtls, {texturesWritten} new textures");
        return 0;
    }

    /// <summary>
    /// Assemble an NPC body OBJ from a base SetupModel plus a weenie-derived
    /// appearance overlay (anim_part GfxObj overrides + per-part texture_map
    /// substitution). Mirrors ExportSetup's geometry emission but applies the
    /// ACE/ACViewer ObjDesc model:
    ///   * for each base part index, the weenie AnimationId (anim_parts)
    ///     replaces the base GfxObj at that index;
    ///   * GfxObj 0x010001EC is the empty/invisible placeholder and is skipped
    ///     (ACViewer Model/Setup.cs);
    ///   * each part's Surface.OrigTextureId (a 0x05 SurfaceTexture id) is
    ///     remapped via texture_map[partIndex] old->new before the SurfaceTexture
    ///     is read (ACViewer Render/TextureCache.cs 0x08 branch).
    /// Palette recolours are intentionally NOT applied (tracked as Phase-9).
    /// Usage: export-npc &lt;datDir&gt; &lt;appearanceJson&gt; &lt;out.obj&gt;
    /// </summary>
    public static int ExportNpc(ReadOnlySpan<string> args)
    {
        if (args.Length < 3) { Console.Error.WriteLine("export-npc: missing <datDir> <appearanceJson> <out.obj>"); return 1; }
        var datDir = args[0];
        var jsonPath = args[1];
        var outPath = args[2];

        if (!File.Exists(jsonPath)) { Console.Error.WriteLine($"Appearance JSON not found: {jsonPath}"); return 1; }

        static bool TryParseHexId(string? s, out uint id)
        {
            id = 0;
            if (string.IsNullOrEmpty(s)) return false;
            var t = s.Trim();
            if (t.StartsWith("0x", StringComparison.OrdinalIgnoreCase)) t = t.Substring(2);
            return uint.TryParse(t, System.Globalization.NumberStyles.HexNumber, System.Globalization.CultureInfo.InvariantCulture, out id);
        }

        // Parse the appearance overlay.
        uint setupId;
        var partOverrides = new Dictionary<int, uint>();
        var texMap = new Dictionary<int, Dictionary<uint, uint>>();
        try
        {
            using var doc = System.Text.Json.JsonDocument.Parse(File.ReadAllText(jsonPath));
            var root = doc.RootElement;
            if (!TryParseHexId(root.GetProperty("setup_id").GetString(), out setupId))
            {
                Console.Error.WriteLine($"Bad setup_id in {jsonPath}"); return 1;
            }
            if (root.TryGetProperty("anim_parts", out var ap) && ap.ValueKind == System.Text.Json.JsonValueKind.Object)
            {
                foreach (var prop in ap.EnumerateObject())
                {
                    if (int.TryParse(prop.Name, out var idx) && TryParseHexId(prop.Value.GetString(), out var gid))
                        partOverrides[idx] = gid;
                }
            }
            if (root.TryGetProperty("texture_map", out var tm) && tm.ValueKind == System.Text.Json.JsonValueKind.Array)
            {
                foreach (var entry in tm.EnumerateArray())
                {
                    int idx = entry.GetProperty("index").GetInt32();
                    if (TryParseHexId(entry.GetProperty("old").GetString(), out var oldId)
                        && TryParseHexId(entry.GetProperty("new").GetString(), out var newId))
                    {
                        if (!texMap.TryGetValue(idx, out var sub)) { sub = new Dictionary<uint, uint>(); texMap[idx] = sub; }
                        sub[oldId] = newId;
                    }
                }
            }
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"Failed to parse appearance JSON: {ex.Message}");
            return 2;
        }

        // GfxObj id used by AC as the empty/invisible part placeholder.
        const uint EmptyPartGfx = 0x010001EC;

        DatManager.Initialize(datDir, keepOpen: false, loadCell: false);
        var portalDb = DatManager.PortalDat ?? throw new InvalidOperationException("PortalDat unavailable.");

        if (((setupId >> 24) & 0xFFu) != 0x02)
        {
            Console.Error.WriteLine($"setup_id 0x{setupId:X8} is not a SetupModel (0x02)."); return 3;
        }
        if (!portalDb.AllFiles.ContainsKey(setupId))
        {
            Console.Error.WriteLine($"Setup 0x{setupId:X8} not in PortalDat."); return 3;
        }

        var setup = portalDb.ReadFromDat<SetupModel>(setupId);
        if (setup.Parts == null || setup.Parts.Count == 0)
        {
            Console.Error.WriteLine($"Setup 0x{setupId:X8} has no Parts."); return 4;
        }
        var parts = setup.Parts;
        // Match ACViewer (Model/Setup.cs): prefer the Resting (0x65) placement,
        // but fall back to Default (0x00) when Resting is absent. Character
        // setups (e.g. 0x02000001) often have only Default; without this
        // fallback every part collapses to the setup origin, producing a tiny
        // jumbled blob instead of a full-height standing body.
        const int RestingPlacement = 0x65;
        const int DefaultPlacement = 0x00;
        ACE.DatLoader.Entity.PlacementType? placement = null;
        if (setup.PlacementFrames.TryGetValue(RestingPlacement, out var pfRest))
            placement = pfRest;
        else if (setup.PlacementFrames.TryGetValue(DefaultPlacement, out var pfDef))
            placement = pfDef;
        var defaultScales = (setup.DefaultScale != null && setup.DefaultScale.Count == parts.Count) ? setup.DefaultScale : null;
        var hasDefaultScale = defaultScales != null;

        var outDir = Path.GetDirectoryName(outPath);
        if (!string.IsNullOrEmpty(outDir)) Directory.CreateDirectory(outDir);
        var texDir = Path.Combine(string.IsNullOrEmpty(outDir) ? "." : outDir, "textures");
        Directory.CreateDirectory(texDir);

        const float kCmPerMetre = 100.0f;
        var objBaseName = Path.GetFileNameWithoutExtension(outPath);
        var mtlPath = Path.Combine(outDir ?? ".", objBaseName + ".mtl");

        using var sw = new StreamWriter(outPath);
        sw.WriteLine($"# Exported by acdat export-npc from base setup 0x{setupId:X8} + appearance overlay");
        sw.WriteLine($"# {parts.Count} base parts, {partOverrides.Count} anim_part overrides, {texMap.Count} textured part-maps");
        sw.WriteLine($"# Palette recolours NOT applied (Phase-9). UE-ready coords: left-handed Z-up, cm. Setup-local origin.");
        sw.WriteLine($"mtllib {objBaseName}.mtl");
        sw.WriteLine($"o npc_{setupId:X8}");

        int globalVertOffset = 0;
        var allMtls = new Dictionary<string, (uint surfaceId, uint? textureId)>();
        int totalTris = 0;
        int partsEmitted = 0, partsSkipped = 0;

        for (int partIdx = 0; partIdx < parts.Count; partIdx++)
        {
            uint gfxId = partOverrides.TryGetValue(partIdx, out var ov) ? ov : parts[partIdx];
            if (gfxId == EmptyPartGfx) { partsSkipped++; continue; }
            if (!portalDb.AllFiles.ContainsKey(gfxId))
            {
                Console.Error.WriteLine($"  WARN: GfxObj 0x{gfxId:X8} (part {partIdx}) not in PortalDat — skipping");
                partsSkipped++;
                continue;
            }
            var gfx = portalDb.ReadFromDat<GfxObj>(gfxId);
            if (gfx.VertexArray.Vertices.Count == 0 || gfx.Polygons.Count == 0) { partsSkipped++; continue; }

            float fx = 0, fy = 0, fz = 0;
            float qx = 0, qy = 0, qz = 0, qw = 1;
            if (placement != null && partIdx < placement.AnimFrame.Frames.Count)
            {
                var f = placement.AnimFrame.Frames[partIdx];
                fx = f.Origin.X; fy = f.Origin.Y; fz = f.Origin.Z;
                qx = f.Orientation.X; qy = f.Orientation.Y; qz = f.Orientation.Z; qw = f.Orientation.W;
            }
            float sx = 1, sy = 1, sz = 1;
            if (hasDefaultScale && defaultScales != null)
            {
                var s = defaultScales[partIdx];
                sx = s.X; sy = s.Y; sz = s.Z;
            }

            static (float x, float y, float z) RotAcQ(float qx, float qy, float qz, float qw, float vx, float vy, float vz)
            {
                float tx = 2 * (qy * vz - qz * vy);
                float ty = 2 * (qz * vx - qx * vz);
                float tz = 2 * (qx * vy - qy * vx);
                return (
                    vx + qw * tx + (qy * tz - qz * ty),
                    vy + qw * ty + (qz * tx - qx * tz),
                    vz + qw * tz + (qx * ty - qy * tx));
            }

            var vertOrder = gfx.VertexArray.Vertices.Keys.OrderBy(k => k).ToList();
            var idToObjIndex = new Dictionary<ushort, int>(vertOrder.Count);

            for (int i = 0; i < vertOrder.Count; i++)
            {
                var sv = gfx.VertexArray.Vertices[vertOrder[i]];
                float lx = sv.Origin.X * sx, ly = sv.Origin.Y * sy, lz = sv.Origin.Z * sz;
                var rotated = RotAcQ(qx, qy, qz, qw, lx, ly, lz);
                float ax = rotated.x + fx, ay = rotated.y + fy, az = rotated.z + fz;
                sw.WriteLine($"v {ay * kCmPerMetre:R} {ax * kCmPerMetre:R} {az * kCmPerMetre:R}");
                idToObjIndex[vertOrder[i]] = globalVertOffset + i + 1;
            }
            for (int i = 0; i < vertOrder.Count; i++)
            {
                var sv = gfx.VertexArray.Vertices[vertOrder[i]];
                var rn = RotAcQ(qx, qy, qz, qw, sv.Normal.X, sv.Normal.Y, sv.Normal.Z);
                sw.WriteLine($"vn {rn.y:R} {rn.x:R} {rn.z:R}");
            }
            for (int i = 0; i < vertOrder.Count; i++)
            {
                var sv = gfx.VertexArray.Vertices[vertOrder[i]];
                if (sv.UVs != null && sv.UVs.Count > 0)
                    sw.WriteLine($"vt {sv.UVs[0].U:R} {sv.UVs[0].V:R}");
                else
                    sw.WriteLine($"vt 0 0");
            }

            var partTexMap = texMap.TryGetValue(partIdx, out var ptm) ? ptm : null;

            var groups = gfx.Polygons.Values
                .GroupBy(p => (int)p.PosSurface)
                .OrderBy(g => g.Key);

            foreach (var grp in groups)
            {
                int surfIdx = grp.Key;
                // MTL name is per-part so substituted textures never collide
                // with another part that shares a base surface index.
                string mtlName = $"part{partIdx:D2}_surf{surfIdx}";
                if (!allMtls.ContainsKey(mtlName))
                {
                    uint surfaceId = (surfIdx >= 0 && surfIdx < gfx.Surfaces.Count) ? gfx.Surfaces[surfIdx] : 0u;
                    uint? textureId = null;
                    if (surfaceId != 0 && portalDb.AllFiles.ContainsKey(surfaceId))
                    {
                        var surface = portalDb.ReadFromDat<Surface>(surfaceId);
                        var isImage = surface.Type.HasFlag(ACE.Entity.Enum.SurfaceType.Base1Image)
                                   || surface.Type.HasFlag(ACE.Entity.Enum.SurfaceType.Base1ClipMap);
                        if (isImage && surface.OrigTextureId != 0)
                        {
                            // Apply weenie texture_map substitution at the
                            // SurfaceTexture (0x05) level before reading it.
                            uint sfcTexId = surface.OrigTextureId;
                            if (partTexMap != null && partTexMap.TryGetValue(sfcTexId, out var sub))
                                sfcTexId = sub;
                            if (portalDb.AllFiles.ContainsKey(sfcTexId))
                            {
                                var sfcTex = portalDb.ReadFromDat<SurfaceTexture>(sfcTexId);
                                if (sfcTex.Textures.Count > 0)
                                    textureId = sfcTex.Textures[sfcTex.Textures.Count - 1];
                            }
                        }
                    }
                    allMtls[mtlName] = (surfaceId, textureId);
                }

                sw.WriteLine($"g {mtlName}");
                sw.WriteLine($"usemtl {mtlName}");
                foreach (var poly in grp)
                {
                    if (poly.NumPts < 3) continue;
                    if (poly.VertexIds == null || poly.VertexIds.Count < poly.NumPts) continue;

                    int v0 = idToObjIndex[(ushort)poly.VertexIds[0]];
                    for (int i = 1; i + 1 < poly.NumPts; i++)
                    {
                        int va = idToObjIndex[(ushort)poly.VertexIds[i]];
                        int vb = idToObjIndex[(ushort)poly.VertexIds[i + 1]];
                        sw.WriteLine($"f {v0}/{v0}/{v0} {vb}/{vb}/{vb} {va}/{va}/{va}");
                        totalTris++;
                    }
                }
            }

            globalVertOffset += vertOrder.Count;
            partsEmitted++;
        }
        sw.Flush();

        int texturesWritten = 0;
        using (var mtl = new StreamWriter(mtlPath))
        {
            mtl.WriteLine($"# Materials for npc_{setupId:X8} (appearance overlay applied; palettes NOT applied)");
            mtl.WriteLine();
            foreach (var kvp in allMtls)
            {
                mtl.WriteLine($"newmtl {kvp.Key}");
                mtl.WriteLine("Ka 0.1 0.1 0.1");
                mtl.WriteLine("Kd 1.0 1.0 1.0");
                mtl.WriteLine("d  1.0");
                mtl.WriteLine("illum 1");
                if (kvp.Value.textureId.HasValue && portalDb.AllFiles.ContainsKey(kvp.Value.textureId.Value))
                {
                    var tex = portalDb.ReadFromDat<Texture>(kvp.Value.textureId.Value);
                    string ext = tex.Format == ACE.Entity.Enum.SurfacePixelFormat.PFID_CUSTOM_RAW_JPEG ? ".jpg" : ".png";
                    string texFileName = $"{kvp.Value.textureId.Value:X8}{ext}";
                    string texPath = Path.Combine(texDir, texFileName);
                    if (!File.Exists(texPath))
                    {
                        try { tex.ExportTexture(texDir); texturesWritten++; }
                        catch (Exception ex) { mtl.WriteLine($"# (texture export failed: {ex.Message})"); }
                    }
                    mtl.WriteLine($"# Texture 0x{kvp.Value.textureId.Value:X8} {tex.Width}x{tex.Height} {tex.Format}");
                    mtl.WriteLine($"map_Kd textures/{texFileName}");
                }
                else
                {
                    mtl.WriteLine($"# Surface 0x{kvp.Value.surfaceId:X8} (no extractable texture)");
                }
                mtl.WriteLine();
            }
        }

        Console.WriteLine($"Wrote {new FileInfo(outPath).Length} bytes to {outPath}");
        Console.WriteLine($"  npc 0x{setupId:X8}: {partsEmitted} parts emitted, {partsSkipped} skipped -> {totalTris} triangles, {allMtls.Count} mtls, {texturesWritten} new textures");
        return 0;
    }

    /// <summary>
    /// Bulk-export every unique SetupModel referenced by an academy's statics
    /// JSON. Generates one OBJ per setup under outDir, sharing the textures/
    /// directory. Pair with dump-academy-statics.
    /// </summary>
    public static int ExportAcademyStatics(ReadOnlySpan<string> args)
    {
        if (args.Length < 3) { Console.Error.WriteLine("export-academy-statics: missing <datDir> <statics.json> <outDir>"); return 1; }
        var datDir = args[0];
        var staticsJson = args[1];
        var outDir = args[2];
        Directory.CreateDirectory(outDir);

        if (!File.Exists(staticsJson))
        {
            Console.Error.WriteLine($"Statics JSON not found: {staticsJson}");
            return 1;
        }
        using var stream = File.OpenRead(staticsJson);
        var doc = JsonSerializer.Deserialize<JsonElement>(stream);
        var unique = doc.GetProperty("unique_setups").EnumerateArray()
            .Select(e => e.GetString()!).ToList();

        Console.WriteLine($"Exporting {unique.Count} unique setups to {outDir}");
        int ok = 0, failed = 0;
        foreach (var setupHex in unique)
        {
            var clean = setupHex.StartsWith("0x") ? setupHex.Substring(2) : setupHex;
            var path = Path.Combine(outDir, $"setup_{clean}.obj");
            int rc;
            try { rc = ExportSetup(new[] { datDir, clean, path }); }
            catch (Exception ex) { Console.Error.WriteLine($"  FAILED {setupHex}: {ex.Message}"); rc = 99; }
            if (rc == 0) ok++; else failed++;
        }
        Console.WriteLine($"Done. {ok} OK, {failed} failed.");
        return failed == 0 ? 0 : 1;
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
