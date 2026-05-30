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
                    Walk the Portal DAT and dump every landblock-related file
                    ID. Useful for discovering which landblocks exist.

              acdat landblock-info     <datDir> <hexId>
                    Print summary of one landblock (height samples, texture
                    layers, environment cells). <hexId> e.g. A9B4 = the
                    LandblockX/Y high 16 bits.

              acdat export-landblock   <datDir> <hexId> <outFile.aclb>
                    Convert one landblock to our v1 .aclb intermediate format
                    (see pipeline/asset-ingest/FORMAT.md).

            <datDir> is the directory containing client_portal.dat,
            client_cell_1.dat, client_highres.dat, client_local_English.dat.
            For this repo, the conventional path is:
              C:\Users\darin\repos\ac-client\binary\original\
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

        // Also look for the LandblockInfo (objects + env cells) at (high16 << 16) | 0xFFFE in PortalDat.
        var infoFileId = (lbHigh16 << 16) | 0xFFFEu;
        var portalDb = DatManager.PortalDat;
        if (portalDb != null && portalDb.AllFiles.ContainsKey(infoFileId))
        {
            var info = portalDb.ReadFromDat<LandblockInfo>(infoFileId);
            Console.WriteLine($"  LandblockInfo:  present (file 0x{infoFileId:X8} in PortalDat)");
            Console.WriteLine($"    NumCells:     {info.NumCells}");
            Console.WriteLine($"    Buildings:    {info.Buildings?.Count ?? 0}");
            Console.WriteLine($"    Objects:      {info.Objects?.Count ?? 0}");
        }
        else
        {
            Console.WriteLine($"  LandblockInfo:  NONE (no 0x{infoFileId:X8} in PortalDat)");
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
