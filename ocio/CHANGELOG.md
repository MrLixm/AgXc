# Changelog

OCIO config changes documention for each version published 
(ocio config version is determined by the top commented line).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

None

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