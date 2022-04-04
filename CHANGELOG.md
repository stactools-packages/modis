# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Changed

- Insert "data" role at the front of the roles list ([#75](https://github.com/stactools-packages/modis/pull/75))
- Keywords ([#77](https://github.com/stactools-packages/modis/pull/77))

### Removed

- `file:values` ([#76](https://github.com/stactools-packages/modis/pull/76))

## [0.2.0] - 2022-03-30

### Added

- Return paths and subdatasest names from `stactools.modis.cogs.add_cogs` ([#44](https://github.com/stactools-packages/modis/pull/44))
- Keywords and summaries to collections ([#48](https://github.com/stactools-packages/modis/pull/48))
- More Item and Collection metadata ([#51](https://github.com/stactools-packages/modis/pull/51))
- Keywords for Collections ([#54](https://github.com/stactools-packages/modis/pull/54))
- Antimeridian corrections ([#62](https://github.com/stactools-packages/modis/pull/62), [#67](https://github.com/stactools-packages/modis/pull/67))
- Cloud cover ([#66](https://github.com/stactools-packages/modis/pull/66))
- `sci:publications` ([#66](https://github.com/stactools-packages/modis/pull/66))
- `eo:bands` to reflectance products ([#69](https://github.com/stactools-packages/modis/pull/69), [#71](https://github.com/stactools-packages/modis/pull/71))
- License links ([#72](https://github.com/stactools-packages/modis/pull/72))
- Classification extension ([#73](https://github.com/stactools-packages/modis/pull/73))

### Changed

- Use `null` instead of "unitless` ([#55](https://github.com/stactools-packages/modis/pull/55))
- Don't use unicode for units, PySTAC doesn't like it ([#57](https://github.com/stactools-packages/modis/pull/57))
- Use fewer collections (e.g. all 17A2HGF products are in the same collection) ([#61](https://github.com/stactools-packages/modis/pull/61))
- Example collections and items ([#65](https://github.com/stactools-packages/modis/pull/65))

### Fixed

- Formatting in V006 fragments ([#45](https://github.com/stactools-packages/modis/pull/45))
- Extents for V061 collections ([#52](https://github.com/stactools-packages/modis/pull/52))
- Spaces are disallowed in COG filenames ([#53](https://github.com/stactools-packages/modis/pull/53))
- Use keywords when creating Collections ([#56](https://github.com/stactools-packages/modis/pull/56))
- Use `raster`'s `spatial_resolution` instead of `gsd` ([#60](https://github.com/stactools-packages/modis/pull/60))
- Metadata ([#65](https://github.com/stactools-packages/modis/pull/65))
- Raster bands ([#68](https://github.com/stactools-packages/modis/pull/68))

## [0.1.0] - 2022-02-17

Initial release.

[Unreleased]: <http://github.com/stactools-packages/modis/compare/v0.2.0..main>
[0.2.0]: <http://github.com/stactools-packages/modis/compare/v0.1.0..v0.2.0>
[0.1.0]: <https://github.com/stactools-packages/modis/releases/tag/v0.1.0>
