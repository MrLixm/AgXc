"Fork" of Troy Sobotka's AgX https://github.com/sobotka/AgX with implementation
in various languages/software.

![agx comparison with aces and filmic](comparison.jpg)

> extreme example rendered with pure ACEScg primaries

AgX is a [display rendering transform](https://github.com/jedypod/open-display-transform/wiki/doc-introduction)
(DRT) with the goal of improving image formation.

It tries to provide a ""neutral look"" via a robust but simple image formation process.

The result can be comparable to the analog film process with noticeable soft highlight rollof,
smooth color transitions and pleasing exposure handling.

If you find that there was too much scary-looking words until now, just
consider AgX as a "LUT".

# Background

The AgX formula used is based on the original Troy's implementation which is not the same as what is currently being implemented in Blender-4+.
- assume sRGB working space
- clip everything outside
- apply "inset" (gamut reshaping)
- apply tonescale (1D curve)

It is possible the various implementations are not at the same level of progress.
For example the LUT implementation is already using a BT.2020 workspace approach
(like the Blender version).

# Content

The simplicity of AgX allowed to port it to various languages and softwares :

- [OpenColorIO](ocio) : v1 compatible
- [ReShade](reshade) : for in-game use.
- [OBS](obs) : to apply on live camera feed
- [Python](python) : numpy-only script and a more advanced library for manipulation
- [nuke](nuke): partial implementation for [Foundry's Nuke](https://www.foundry.com/products/nuke-family/nuke)
- [luts](luts): LUTs file for preview in various systems

![ReShade: Stray screenshot with AgX](reshade/img/stray-3-AgX.jpg)

> screenshot from game Stray with AgX applied via ReShade

![OBS interface screenshot with webcam feed](obs/doc/img/obs-main.png)

> Screenshot of the OBS interface while streaming 8Bit VLog from a Panasonic camera.