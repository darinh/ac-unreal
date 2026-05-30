# Intermediate asset exchange format (v1)

This document defines the **on-disk format** that the decompile-side
pipeline produces and the UE-side `AcUnreal` module consumes. Keeping
the format pinned here means the decompile agent and this repo can move
independently — the format is the contract, not the tooling.

> **Scope note:** v1 covers the *landblock heightfield + texture layer*
> path (the most geometrically large input). Mesh and particle paths
> have their own future sections (see "Pending formats" below).
> Texture binaries do **not** need a custom format: ship them as PNG /
> EXR / TGA and let UE's existing importers handle them.

---

## File extension and magic

| | |
|---|---|
| Extension | `.aclb` (AC Land Block) |
| Magic     | `0x424C4341` little-endian — ASCII `"ACLB"` byte order is `'A','C','L','B'` |
| Endianness | Little-endian throughout (matches the original AC client's x86 PC platform) |
| Version   | `1` (current). Bumped on **any** schema change, even additive. |

A reader that sees a different magic, an unsupported version, or a file
whose size doesn't match `ComputeExpectedFileSize(header)` MUST fail
loudly. Silent fallback to defaults would mask format drift between the
two agents.

---

## Binary layout (v1)

The file is a fixed 32-byte header followed by two raw-numeric payload
blocks. No padding inside the payload blocks; no string table; no
optional sections.

```
+-----------------------------+ offset 0
| FAcIntermediateLandblockHeader  (32 bytes)
+-----------------------------+ offset 32
| Heights[SamplesPerSide^2]   (float32 each, row-major: idx = Y * Side + X)
+-----------------------------+ offset 32 + 4 * Side * Side
| TextureIndices              (uint8 each)
|   layout = SamplesPerSide^2 * TextureLayerCount
|   row-major within a layer; layers are contiguous (layer 0 then layer 1 ...)
+-----------------------------+ EOF
```

### Header (32 bytes, packed, little-endian)

| Offset | Size | Type     | Field                | Notes |
|------:|------:|----------|----------------------|-------|
|  0    |   4   | uint32   | `Magic`              | `0x424C4341` |
|  4    |   4   | uint32   | `Version`            | `1` for this spec |
|  8    |   4   | uint32   | `LandblockId`        | AC-encoded: byte 3 = LB.X (0x00–0xFE), byte 2 = LB.Y (0x00–0xFE), **low 16 bits MUST be `0x0000`** in v1. See "LandblockId semantics" below. |
| 12    |   4   | uint32   | `SamplesPerSide`     | Height samples per landblock side. AC native is 9. Allowed range: `[2 .. 65]` (sanity bounds; v1 readers MUST reject outside this). |
| 16    |   4   | uint32   | `TextureLayerCount`  | Number of texture-index layers. `0..4` typical. `0` means: no texture data present, payload ends after Heights. |
| 20    |   4   | uint32   | `Flags`              | Reserved. v1 writers MUST set 0; v1 readers MUST reject non-zero. |
| 24    |   8   | uint32×2 | `Reserved[2]`        | Padding. v1 writers MUST set 0; v1 readers MUST reject non-zero. |

**Total: 32 bytes.** Header struct in C++17 is naturally packed at
8-byte alignment with no internal padding; verify with `static_assert(sizeof == 32)`.

### LandblockId semantics (clarification)

The original AC client encodes landblock IDs as a 32-bit value with the
following community-documented layout:

```
| byte 3 (LB.X) | byte 2 (LB.Y) | byte 1 (cell hi) | byte 0 (cell lo) |
```

For the **outdoor landblock surface** — which is what this format
represents — the low 16 bits are not a meaningful cell address; the
heightfield + texture-layer payload below covers the *entire* 9×9
outdoor surface of the landblock as a single unit. Different parts of
the AC client and the ACEmulator project use either `0x0000` or
`0xFFFF` in the low 16 bits when referring to "the landblock itself".
This format pins the choice: **v1 writers MUST emit `0x0000` in the
low 16 bits**, and **v1 readers MUST reject any other value** with the
`InvalidLandblockId` status.

If a decompile-side exporter is starting from a raw AC LandblockId
that has `0xFFFF` (or any other non-zero low 16) in the source data,
it MUST mask the low 16 bits before writing the `.aclb` header.

A future v2 may carry indoor / dungeon-cell data, in which case the
low 16 bits will become meaningful again; the version bump is the
signal to update reader semantics.

### Payload

1. **Heights** — `SamplesPerSide * SamplesPerSide` IEEE-754 single-precision floats.
   - Units: **metres** (in the AC world frame; convert to UE cm at the boundary via `ac_coord::AcUnitToUeCentimeters` × samples-as-metres → cm).
   - Ordering: row-major, Y outer / X inner. `Heights[y * SamplesPerSide + x]`.
   - Sample (0,0) is the **min-X, min-Y corner** of the landblock in AC coordinates (matches `ac_coord::AcOriginOfLandblock` output).
   - NaN / non-finite values are invalid; readers MUST treat as a parse failure.

2. **TextureIndices** — `SamplesPerSide * SamplesPerSide * TextureLayerCount` bytes.
   - Each byte is a texture-table index, dense (layer 0 occupies bytes
     `[0 .. Side²)`, layer 1 occupies `[Side² .. 2·Side²)`, etc.).
   - The texture *table* mapping `byte → asset path` is OUT OF SCOPE for
     v1 — that's a separate sibling file (`.actx` / table format TBD)
     to be defined when texture asset import lands.
   - If `TextureLayerCount == 0`, this block is empty (zero bytes).

### Expected file size

```
expected_bytes = 32
              + 4 * SamplesPerSide * SamplesPerSide
              + 1 * SamplesPerSide * SamplesPerSide * TextureLayerCount
```

Readers MUST verify the loaded buffer matches `expected_bytes` exactly.
Trailing bytes are a parse failure (could indicate a truncated payload
treated as the start of an unknown section or, worse, a different
format mistakenly fed in).

### Worked example

A 9×9 landblock with 1 texture layer:
- header = 32 bytes
- heights = 4 × 81 = 324 bytes
- texture indices = 1 × 81 × 1 = 81 bytes
- **total = 437 bytes**

---

## Reference reader / writer

The canonical reader is in
[`Source/AcUnreal/Public/AssetIngest/AcIntermediateLandblock.h`](../../Source/AcUnreal/Public/AssetIngest/AcIntermediateLandblock.h)
(and `Private/.../AcIntermediateLandblock.cpp`). It is pure C++17 with
no UE or STL-container dependencies in the interface — same dual-build
pattern as the coord-transform core, so the same code is exercised by
the standalone test rig in [`tests/`](tests/) and by the UE module via
UBT.

A reference writer is `pipeline/asset-ingest/gen_sample.ps1`; it
generates the synthetic `samples/synthetic_landblock_0xAA0B0000.aclb`
fixture that the tests round-trip against.

---

## Pending formats (placeholder slots)

These are **not** defined by v1. They are listed so contributors know
the namespace and don't accidentally collide.

| Asset class        | Extension | Format direction | Owner phase |
|--------------------|-----------|------------------|-------------|
| Static / skeletal mesh | `.gltf` + `.bin` | glTF 2.0 (UE Interchange will own import) | Phase 1.5 once Interchange path is exercised |
| Texture / heightmap | `.png` / `.exr` / `.tga` | Standard image formats, no custom container | When sample assets arrive |
| Texture table (byte → asset) | `.actx` (TBD) | TBD; needed when texture indices in `.aclb` start mattering | Phase 1.5 |
| Skeleton / animation | embedded in glTF | Per glTF 2.0 spec | Phase 1.5 |
| Particle definition (timing only) | `.acparticle.json` (TBD) | JSON listing gameplay-relevant timing events; visuals re-authored in Niagara | Phase 4 |
| Sound | `.wav` / `.ogg` | Standard audio, UE imports natively | When samples arrive |

A future format version (`2`, `3`, ...) may extend the landblock layout
(e.g. add an "environment cell" subsection for dungeon spillover). Any
such extension MUST bump the version number; v1 readers MUST refuse the
new version rather than try to interpret it.

---

## Versioning policy

- The format version is a single `uint32` in the header.
- **Additive changes** (new payload section appended to existing) still
  require a version bump. v1 readers will refuse a newer version
  loudly rather than try to interpret it.
- The on-disk schema is the source of truth. The C++ struct
  `FAcIntermediateLandblockHeader` mirrors it; if they diverge, the C++
  struct is wrong.
- Removing or renaming a field is a breaking change. Don't do it.
- Writers always emit the current version. Multi-version writers
  (producing older formats for backward compatibility) are not
  supported in v1 because no older version exists yet; the policy
  will be revisited when v2 lands and there is something to be
  backward-compatible with.
