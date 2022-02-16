# stactools-modis

- Name: modis
- Package: 'stactools.modis'
- PyPI: https://pypi.org/project/stactools-modis/
- Owner: @gadomski 
- Dataset homepage: https://modis.gsfc.nasa.gov/
- STAC extensions used:
  - [proj](https://github.com/stac-extensions/projection)
  - [eo](https://github.com/stac-extensions/eo)
  - [item-assets](https://github.com/stac-extensions/item-assets)
  - [scientific](https://github.com/stac-extensions/scientific)
  - [raster](https://github.com/stac-extensions/raster)
- Extra Fields: TODO

This repository will assist you in the generation of STAC files for MODIS datasets. 

## Examples

There is an example `Catalog` at `examples/catalog.json`.
Inside that catalog are several MODIS v6.0 and v6.1 STAC `Collection`s and `Item`s.
For an example of an item with COG assets, see [MOD10A2.A2022033.h09v05.061.2022042050729.json](examples/modis-061/modis-MOD10A2-061/MOD10A2.A2022033.h09v05.061.2022042050729/MOD10A2.A2022033.h09v05.061.2022042050729.json).

### Command-line Usage

To create a STAC `Item`:

```shell
$ stac modis create-item tests/data-files/MCD12Q1.A2001001.h00v08.006.2018142182903.hdf.xml build
```

To create a STAC `Catalog` from a list of MODIS asset hrefs:

```shell
$ stac modis create-catalog examples/file-list.txt examples
```

Note that this `create-catalog` example is exactly how the `examples/` directory is generated.
