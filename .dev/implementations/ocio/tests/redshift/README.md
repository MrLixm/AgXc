# test-ocio-redshift

The test consits of rendering an image with the redshift command line tool 
and verifying there is no error in the log (the rendered image doesn't matter).

An error would looks like:

```
Loading OCIO config using N:\apps\ocio\configs\AgXc\config.ocio
        Full path: N:\apps\ocio\configs\AgXc\config.ocio
        Ok
Creating OCIO processors between rendering and view/srgb spaces
        Rendering space: 2.2-EOTF-Encoding
        Display: sRGB-2.2
        View: AgXc.base Punchy
        Failed to find a suitable sRGB color space in config!
                Proxies with textures in 'sRGB' color space may not render correctly.
                Physical sun/sky, black-body and hair shaders may not render correctly.
        Failed to create rendering to sRGB processor
Loading OCIO color space transforms for texture sampling
        Unable to find a suitable sRGB-linear color space. Common texture linear color space will be: "BT.2020-linear"
```