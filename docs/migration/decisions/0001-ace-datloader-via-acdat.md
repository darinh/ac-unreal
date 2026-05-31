# 0001 - Use ACE.DatLoader (via the `acdat` CLI) for DAT extraction
Status: Accepted   Date: 2026-05-30

## Context
Reading AC's DAT files is a large, solved problem. ACEmulator's `ACE.DatLoader`
(~5k lines of community-maintained C#) parses every file type. Re-implementing
it would be weeks of work with high regression risk.

## Decision
Extract via a thin C# CLI (`pipeline/dat-extract/acdat`) that references
`ACE.DatLoader` and emits engine-neutral intermediates (OBJ/PNG/JSON). The
UE side consumes only the intermediates, with no .NET dependency at runtime.

## Consequences
- We inherit ACE's data semantics as ground truth (good: correctness; risk: we
  must track ACE's licensing - see [LEGAL.md](../../../LEGAL.md) and ADR-0003).
- A C# build step (.NET 8) is required in the pipeline.
- Revisit only if ACE.DatLoader proves insufficient for a file type we need.

## Alternatives
- Re-implement the reader in C++/Python: rejected (cost, regression risk).
- Parse inside a UE plugin: rejected (duplicates ACE, ties extraction to the editor).
