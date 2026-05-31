# pipeline/asset-ingest

The **receiving side** of the asset pipeline. The decompile agent (or
any community DAT exporter — ACEmulator's ACViewer is the most mature)
emits intermediate files in the formats defined in
[FORMAT.md](FORMAT.md); the UE-side `AcUnreal` module consumes them.

## What lives here

```
asset-ingest/
├── README.md                this file
├── FORMAT.md                binary format spec for the intermediate exchange
├── samples/                 synthetic test fixtures (committed)
│   └── synthetic_landblock_0xAA0B0000.aclb
├── gen_sample.ps1           regenerates samples/ deterministically
├── tests/                   standalone parser tests (cl.exe; no UE)
│   └── LandblockImporterTests.cpp
└── build.ps1                vcvars64 + cl.exe build & run for tests/
```

The reader implementation does NOT live here. It lives in the UE module
at `Source/AcUnreal/{Public,Private}/AssetIngest/`, with pure-C++17
source files that this directory's `build.ps1` also compiles into a
standalone test executable — same dual-build pattern as the
coord-transform module.

## Why a binary format (and not glTF/JSON)?

Landblocks are dense numeric grids: a 9×9 height array + per-cell
texture-layer indices. JSON would balloon a 437-byte payload to several
KB. glTF would impose a graph format that doesn't fit a regular grid.
A fixed-header + raw-array binary file is the smallest thing that
correctly captures the data, and it parses in tens of lines of C.

Meshes are a different story — they're graphs of vertices, indices,
skeletons, weights, materials — and the right tool there IS glTF. The
intermediate format reflects this: each asset class gets the
representation that matches its shape.

## Why synthetic samples?

The brief says "hand-exported sample assets". In this repo's autonomous
setup nobody hand-exports anything yet — so `gen_sample.ps1`
**procedurally** generates a synthetic landblock conforming to the v1
format. The sample is:

- Deterministic (same script, same bytes — comparable across runs).
- Synthetic (no AC binary content — no copyright issues).
- Format-conformant (the parser tests validate the round-trip).

When the decompile agent starts dropping real exports into
`contract/decompile-artifacts/`, those replace the synthetic samples in
the parser tests; the format itself doesn't change.

## How to run the tests

```powershell
# Regenerate the sample (only needed if FORMAT.md changes)
.\gen_sample.ps1

# Build and run the standalone parser tests
.\build.ps1
```

Exits 0 on all-pass, non-zero on any failure. Output lands in `build/`
(gitignored).
