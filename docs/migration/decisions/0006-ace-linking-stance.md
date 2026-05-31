# 0006 - ACE.DatLoader linking stance (AGPL obligations)
Status: Accepted   Date: 2026-05-30

## Context
[LEGAL.md](../../../LEGAL.md) hard rule #3 requires an ADR recording the
linking-vs-clean-room stance per third-party component. `acdat` consumes
ACEmulator code by **compile-time project reference**:
`AcDatExtract.csproj` has `<ProjectReference Include="..\..\..\ACE\Source\ACE.DatLoader\ACE.DatLoader.csproj" />`,
producing a binary that statically incorporates `ACE.DatLoader`. ACEmulator is
distributed under an AGPL-family license, which attaches source-availability
obligations to *distribution* of a combined work.

## Decision
- **Link directly (compile-time) for now.** Re-implementing the DAT reader is out
  of scope (ADR-0001) and the value is in correctness, not novelty.
- **`acdat` is a build-time tool, not shipped to end users.** It runs locally to
  produce intermediates from a user-supplied client (ADR-0003). The UE runtime
  does **not** link ACE.
- **Distribution gate:** we do **not** distribute any binary that links
  ACE.DatLoader. If that ever changes, AGPL obligations apply (publish the
  corresponding source of the combined tool under compatible terms, preserve
  notices) and this ADR must be revisited *before* release with legal review.
- Pin the exact ACE source (`docs/migration/versions.md`: SHA `9bc20cbd`) so the
  linked version is identifiable.

## Consequences
- We stay clean for private/build-time use; the obligation is parked behind a
  hard "no distribution of the linked tool" rule.
- If we later need a shippable extractor, options are: ship `acdat` under
  AGPL-compatible terms (publish its source), or clean-room re-implement the
  needed parsers. That is a future ADR.

## Alternatives
- Clean-room re-implement now: rejected (cost/risk; ADR-0001).
- Treat ACE as docs-only and hand-port the parsers: deferred until distribution forces it.
