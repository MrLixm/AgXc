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

# Integrations

- [OpenColorIO](ocio) : v1 compatible
- [ReShade](reshade) : for in-game use.
- [OBS](obs) : to apply on live camera feed
- [Python](python) : with numpy as only dependency

### ReShade

![ReShade: Stray screenshot with AgX](reshade/img/stray-3-AgX.jpg)

### OBS

![OBS interface screenshot with webcam feed](obs/doc/img/obs-main.png)
