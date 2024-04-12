# OCIO

The goal was making [the proof-of-concept OCIO config](https://github.com/sobotka/AgX) 
more "production-ready" because, well that's a damn solid concept.

![AgXc comparison with ACES and filmic using a cg render](../doc/images/dragon.full.combined.jpg)

>  [!TIP]
>  Compatible with OCIO v2 and OCIO v1.

## Changes with original

- Slight update in the colorspaces names / families 
    - `Generic Data` -> `Passtrough` ( for scalar data)
    - `Linear BT.709` -> `Linear sRGB` (less accurate, but clearer for artists)
    - Appearance view renamed.
- punchy look less punchy (tweak it to your taste anyway)
- Edited display's views :
    - New view `Disabled`, data directly to the display.
    - Removed Golden appearance.
    - Making `Agx Punchy` the default view
- New `ACEScg`, `ACES2065-1` colorspace.
- New `CIE - XYZ -D65`
- **OCIO v1 supports**
    - converted OCIO v2 transforms to v1
    - added allocation vars (not 100% accuracy guarantee)

## Support

This was tested on :
- RV (no exact version, tested q1 2022)
- Katana (4.0)
- Nuke (13)
- C4D (2023) + Redshift (3.5.07)

I do not guarantee it is perfectly working on OCIO v1 GPU engine.

## Future

This config was initially a proof of concept (of an already proof of concept yes) and I planned to write it in Python with OCIO binding but never had the time.

You can open issues if you feel like something can be improved.
