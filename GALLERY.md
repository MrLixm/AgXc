# gallery

Test images to visualize and compare results of AgXc rendering.

Original images can be found in [assets](.dev/assets) directory. Original author
and additional information can be found in the side-car json file.

All sources images are processed using an automatized process stored in 
[doc-imagegen.py](.dev/implementations/doc/scripts/doc-imagegen.py). The process
is using the [ocio](ocio) implementation to render the images.


## [CAlc-D8T-dragon](doc/images/CAlc-D8T-dragon)

This comparison is interesting because it's an "extreme condition" case where
meshes colors are pure ACEScg primaries.

![CAlc-D8T-dragon.exposures.overview.jpg](doc/images/CAlc-D8T-dragon/CAlc-D8T-dragon.exposures.overview.jpg)


## [Cblr-GFD-spring](doc/images/Cblr-GFD-spring)

This comparison is interesting because the original assets were authored within
limit of sRGB and with Filmic which biased the render to look better under those.

![Cblr-GFD-spring.exposures.overview.jpg](doc/images/Cblr-GFD-spring/Cblr-GFD-spring.exposures.overview.jpg)


## [PAmsk-R65-christmas](doc/images/PAmsk-R65-christmas)

This comparison is interesting because we have camera data that was
able to record very intense energy ratios.

![PAmsk-R65-christmas.exposures.overview.jpg](doc/images/PAmsk-R65-christmas/PAmsk-R65-christmas.exposures.overview.jpg)


## [PWdc-85R-braidmaker](doc/images/PWdc-85R-braidmaker)

This comparison is interesting because we have quite a flat look, easier
to handle for image formations. It also brings diversity by showcasing effects
on non-caucasian skin.

![PWdc-85R-braidmaker.exposures.overview.jpg](doc/images/PWdc-85R-braidmaker/PWdc-85R-braidmaker.exposures.overview.jpg)


## [CAtm-FGH-specbox](doc/images/CAtm-FGH-specbox)

This example is interesting because of the wide range of colors and values
it showcase. A kind of matrix of all possible options.

![CAtm-FGH-specbox.full.AgXc.jpg](doc/images/CAtm-FGH-specbox/CAtm-FGH-specbox.full.AgXc.jpg)


## [CGts-W0L-sweep](doc/images/CGts-W0L-sweep)

This example is interesting because it try to provide a neutral context to
see exactly how the image rendering behave in all conditions.

![CGts-W0L-sweep.full.AgXc.jpg](doc/images/CGts-W0L-sweep/CGts-W0L-sweep.full.AgXc.jpg)
