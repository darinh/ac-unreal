# Legal & IP Posture

**Read this before contributing or distributing anything from this repository.**

## What this project is

A personal, non-commercial, archival/educational effort to study how the
Asheron's Call retail client's data and systems work, and to re-implement
comparable behavior in Unreal Engine 5. It is a learning and preservation
project, not a product.

## Who owns Asheron's Call

Asheron's Call, its DAT file contents (art, models, textures, sounds,
animations, UI, world data, text), and all related trademarks are the
intellectual property of their rights holders (originally Turbine, Inc.;
rights subsequently held by Warner Bros. / others). **This project claims
no ownership of any of it** and is not affiliated with or endorsed by any
rights holder.

## Hard rules for this repository

1. **No Turbine/WB game assets are committed to this repo.** No extracted
   models, textures, sounds, animations, world geometry, or UI assets from
   the DAT files — not as binaries, not as derived OBJ/PNG/JSON, not in
   Git LFS. The pipeline is designed so each user extracts from *their own*
   legally-obtained client install at build time.
   - `pipeline/**/out/` is git-ignored and is the **only** place extracted
     assets may live (locally, uncommitted).
   - Committed `samples/` fixtures must be limited to tiny, non-substitutable
     technical artifacts needed to test the *pipeline* (e.g. a few-vertex
     cell layout), never bulk content. When in doubt, leave it out.
   - Reference screenshots used for visual comparison are **not committed**;
     they live outside the repo (e.g. `~/repos/ac-screenshots/`).

2. **Each user supplies their own DAT files.** The methodology references a
   retail install at `C:\Turbine\Asheron's Call\`. You must legally own the
   client whose DATs you read. This repo distributes no DATs.

3. **Third-party code obligations.** This project reads and is informed by
   community open-source projects:
   - **ACEmulator (`ACE.*`)** — referenced/linked for DAT parsing and as the
     reference server. Check its license (AGPL-family) **before** copying or
     statically linking its code, or shaping our code closely on its
     internals. Linking vs. clean-room re-implementation has different
     obligations; an ADR must record the chosen stance per component.
   - **ACViewer** and similar tools — likewise GPL-derived; treated as
     reference documentation, not a code source, unless an ADR says otherwise
     and the license is honored.
   - Record every such dependency, its license, and our usage stance in
     `docs/migration/decisions/` (ADRs) and a top-level dependency manifest.

4. **No copyrighted material reproduced in docs.** Documentation describes
   file *formats*, ID ranges, and methodology (facts/interfaces), not
   copyrighted asset content.

## Distribution

Do not publish builds or assets that embed any AC client content. A
shippable artifact may contain only: our own code, our own/CC-or-permissive
assets, and tooling that operates on a user-supplied client. If publication
is ever contemplated, get explicit legal review first.

## If contacted by a rights holder

Treat any rights-holder request (takedown, cease-and-desist) as
authoritative: stop distribution, remove the flagged material, and record
the event. Nothing here asserts a right to use AC IP.

> This file is a project posture, not legal advice. If you intend to do
> anything beyond private, personal study, consult a qualified attorney.
