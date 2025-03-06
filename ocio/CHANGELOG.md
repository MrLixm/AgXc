# Changelog

OCIO config changes documention for each version published 
(ocio config version is determined by the top commented line).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

None

## [1.0.0]

Major release with lot of breaking changes.

### Added

- Introduce config variants and an OCIO v2 variant of the config: same config as v1 but taking benefit of specific OCIO v2 feature. Benefits are:
    - remove allocation vars (OCIO GPU engine)
    - use proper clamp in AgX Log
- `BT.2020` colorspace, with linear transfer-function
- AgXc `Softer` IRT with a tonescale producing softer highlights

### Changed

- ! (look) new rendering space is `BT.2020`
- ! (look) new rendering transform algorithm
- ! (look) changed `Punchy` look algorithm to adapt new look
- ! new colorspace naming convention:
    - we try to follow the convention `{gamut name}-{transfer function}(-{whitepoint})` so `Linear sRGB` become `sRGB-linear`
    - introduce the concept of "Image colorspace". An output-refered colorspace that include image and display rendering with an optional look.
- ! other various transforms name changes for consistency
- better `family` sorting of View-like colorspaces

### Chore

- split the build script into multiple modules to make code maintenance/browsing easier
- introduce the variant concept in build script
- automatise the generation of  `<View>` and their colorspaces (Image Colorspaces)

## [0.2.5]

### Changed

- The config is now built with a python script instead of manually edited on place.

## [0.2.4]

### Added

- `name` key to the config

## [0.2.3]

### Fixed

- incorrect matrices transform for some colorspaces ([issue #16](https://github.com/MrLixm/AgXc/issues/16))
  - Display P3
  - ACEScg
  - ACES2065-1
  - CIE - XYZ - D65

## [0.2.2]

### Fixed

- clamp of negatives in AgX Log ([PR #13](https://github.com/MrLixm/AgXc/pull/13))

---

_Additional previous releases might not be included._