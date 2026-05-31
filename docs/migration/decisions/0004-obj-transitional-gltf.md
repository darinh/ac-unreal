# 0004 - OBJ is a transitional intermediate; glTF for skinned/multi-UV
Status: Proposed   Date: 2026-05-30

## Context
The pipeline currently exports indoor cell geometry as Wavefront OBJ. OBJ
carries position/normal/UV0 only - no vertex color, no skinning, no multiple
UV channels, no rich material params. This is *adequate today* because AC
indoor cells have no vertex color and AC animation is part-based rigid
transforms (no skinning). But outdoor terrain needs 6 UV channels per vertex
(`LandVertex`: base + 3 overlay + 2 road), and richer material data will be
wanted later.

## Decision (proposed)
Keep OBJ for the current indoor milestone, but treat it explicitly as
*transitional*. Adopt glTF (or a custom binary) for: outdoor terrain
(multi-UV), and any asset needing multiple UV sets or richer materials. Do not
build new long-lived tooling that assumes OBJ is permanent.

## Consequences
- Two exchange formats during the transition; importers must handle both.
- A clean cutover point (first outdoor or first multi-UV asset) forces the glTF work.

## Alternatives
- glTF everywhere now: deferred (extra work before it's needed; OBJ is fine for indoor).
- Stay on OBJ permanently: rejected (cannot express terrain/animation needs).
