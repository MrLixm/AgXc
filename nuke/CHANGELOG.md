# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

# AgXcDRT

## [1.1.1] - 2024-02-01

### Fixed

internal:

* faulty outset that was not at the right position in the processing chain.
  it should have been after the first tonescale, still on linear encoding.

## [1.1.0] - 2024-02-01

### Added

public:

* `purity amount` knob controling how much outset is applied

internal:

* Added new PrimariesInset node to act as Outset

### Changed

* `inset` moved knob to a new top "Purity" section

## [1.0.6] - 2024-01-01

Initial release

# AgXcTonescale

## [0.7.1]