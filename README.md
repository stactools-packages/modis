# stactools-modis

- Name: modis
- Package: 'stactools.modis'
- PyPI: https://pypi.org/project/stactools-modis/
- Owner: @gadomski 
- Dataset homepage: https://modis.gsfc.nasa.gov/
- STAC extensions used:
  - [classification](https://github.com/stac-extensions/classification/)
  - [eo](https://github.com/stac-extensions/eo)
  - [item-assets](https://github.com/stac-extensions/item-assets)
  - [proj](https://github.com/stac-extensions/projection)
  - [raster](https://github.com/stac-extensions/raster)
  - [scientific](https://github.com/stac-extensions/scientific)
- Extra Fields:
  - `modis:horizontal-tile`
  - `modis:vertical-tile`
  - `modis:tile-id`

This repository will assist you in the generation of STAC files for MODIS datasets. 

## Examples

There is an example `Catalog` at `examples/catalog.json`.
Inside that catalog are several MODIS v6.0 and v6.1 STAC `Collection`s and `Item`s.

### Command-line Usage

To create a STAC `Item`:

```shell
$ stac modis create-item tests/data-files/MCD12Q1.A2001001.h00v08.006.2018142182903.hdf.xml build
```

To create a STAC `Catalog` from a list of MODIS asset hrefs:

```shell
$ stac modis create-catalog examples/file-list-061.txt examples/modis-061
```

## Contributing

If you are making any changes to the item or collection structure, the tests will fail until you update the expected values.
To update, run this script:

```shell
$ scripts/create_expected.py
```

This will create, validate, and save new test data items into `tests/data-files/expected` which are used for unit testing.

Once you've got a pull request ready, please update the examples as well (you'll need to download the external test data files first, see [below](#running-tests)):

```
$ stac modis create-catalog --cogify examples/file-list-061.txt examples/modis-061
```

Note that this will take a while (~5-10 minutes).
If you need to update the examples later, you can omit the `--cogify` as the COGs will already be created.

### Running tests

Because of the large number of MODIS products supported by this library and their asset file size, the default test suite does _not_ download all HDF files.
To run all tests, use the `--runslow` option for `pytest`:

```shell
pytest --runslow
```

This will download HDF files for all 061 products to `tests/data-files/external`.
Note that these files are required to create the `examples/` directory.
