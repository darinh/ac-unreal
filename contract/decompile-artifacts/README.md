# Decompile artifacts landing zone

This directory receives outputs from the **separate decompile agent**. Files
deposited here are inputs to this project; they are not source.

**What belongs here:**
- Filled-in `physics-feel-spec-request.md` (or a sibling document
  `physics-feel-spec-response.md`) that resolves every UNKNOWN field in
  the request.
- Annotated pseudocode / disassembly excerpts from the client that justify
  numeric values in the spec (provenance trail).
- Recorded reference traces from the original client (position, velocity,
  state) for parity-harness comparison.
- Format documentation for any new asset/data formats the decompile agent
  uncovers.

**What does NOT belong here:**
- Raw copyrighted game binaries or unmodified extracted DAT contents.
- Anything that would constitute redistribution of copyrighted material.

**Git policy:** Contents of this directory are excluded from version
control by default (see root `.gitignore`); only this README and a
`.gitkeep` are tracked. If you need a specific artifact tracked, add an
explicit allow-list entry in `.gitignore`.
