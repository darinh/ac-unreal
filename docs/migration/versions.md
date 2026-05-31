# Version pins & provenance

Pin the toolchain and inputs so results are reproducible. Update when any of
these change; record the change in the README §6 changelog.

| Component | Pinned value | Notes |
|-----------|-------------|-------|
| Unreal Engine | **5.7** | installed at `C:\Program Files\Epic Games\UE_5.7`. Exact hotfix/patch: **TBD** (record `Build.version`). |
| .NET SDK (build) | **8.0** target (`net8.0-windows`) | `acdat` targets net8.0-windows; local `dotnet` CLI was 10.0.300 (SDK ok, project pins net8.0). |
| Python | **3.11.9** | used by the UE headless import scripts (UE's bundled interpreter at runtime). |
| ACEmulator (`ACE.DatLoader`) | SHA **`9bc20cbd`** | clone at `~/repos/ACE`; referenced by `AcDatExtract.csproj` via relative path. License: AGPL-family - see [LEGAL.md](../../LEGAL.md) / ADR-0003. |
| ACViewer | **TBD** | reference documentation only; record SHA if/when used. |
| AC DAT iteration | portal **2072** / cell **982** | the retail install we validated against; *provenance, not a spec* (read from each DAT header). |
| GPU / driver | **TBD** | record for render-determinism debugging (dev box: RTX 4090 per root README). |
| ac-unreal branch | `anvil/phase5-content-extraction` | working branch at time of writing. |

**TBD items are real gaps** (review item D2): fill UE exact patch, ACViewer
SHA, and GPU driver before treating any render as a reproducible baseline.
