# Content/Presentation/Materials/

Master materials + material instances live here. The PBR pattern:

1. **Master materials** — `M_*.uasset` files defining the shader
   network with input parameters (Base Color, Roughness, Metallic,
   Normal, AO, Emissive, ...). One master per shading style:
   - `M_PBR_Standard` — default opaque PBR.
   - `M_PBR_Translucent` — water, glass, leaves.
   - `M_PBR_Foliage` — subsurface scattering + wind.
   - `M_PBR_Skin` — character skin (subsurface profile).
   - `M_PBR_Eye` — eye/cornea (refraction).
   - (add as needed)
2. **Material instances** — `MI_*.uasset` files inheriting from a
   master, overriding texture parameters per asset. This is where the
   per-asset visual variation lives. Far cheaper than authoring
   shaders per asset.
3. **Material parameter collections** — `MPC_*.uasset` for
   project-wide values (time of day, global exposure bias, world
   wind direction).

## Why master materials + instances (not unique shaders per asset)

UE5 batches draws by material shader. Hundreds of unique shaders means
hundreds of shader switches per frame. Hundreds of material instances
sharing one master shader batch efficiently. Painful to fix later,
trivial to do correctly now.

## Conventions

- Texture inputs assume linear sRGB color space for base color, normal,
  emissive; raw (no gamma) for roughness, metallic, AO, height.
- All instances of `M_PBR_Standard` should be sRGB-aware (UE handles
  this automatically when the texture is imported with the right
  compression setting).
- Roughness map values: 0.0 = mirror, 1.0 = matte. The legacy AC art
  was all hand-painted with no roughness channel — re-authored
  versions should physically-plausibly grade these.

This directory is **currently empty**. Master materials will be
created when the first re-authored asset lands.
