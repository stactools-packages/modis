# stactools-modis

- Name: modis
- Package: `stactools.modis`
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

Use this repository to create STAC Items, Collections, and Catalogs for [MODIS](https://modis.gsfc.nasa.gov/) data. 

## Installation

```shell
$ pip install stactools-modis
```

If you need s3 support:

```shell
$ pip install 'stactools-modis[s3]'
```

## Examples

There is an example `Catalog` at `examples/catalog.json`.
Inside that catalog are several MODIS v6.0 and v6.1 STAC `Collections` and `Items`.

## Command-line Usage

To create a STAC `Item` from a single MODIS xml metadata file:

```shell
$ stac modis create-item tests/data-files/MCD12Q1.A2001001.h00v08.006.2018142182903.hdf.xml build
```

You can also create items from multiple COG files, e.g. from the Astraea open data program (note you must have installed w/ `s3` support, e.g. `pip install 'stactools-modis[s3]'`):

```shell
$ AWS_REQUEST_PAYER="requester" stac modis create-item \
    s3://astraea-opendata/MCD43A4.006/28/08/2022073/MCD43A4.A2022073.h28v08.006.2022082044758_B01.TIF \
    s3://astraea-opendata/MCD43A4.006/28/08/2022073/MCD43A4.A2022073.h28v08.006.2022082044758_B02.TIF \
    s3://astraea-opendata/MCD43A4.006/28/08/2022073/MCD43A4.A2022073.h28v08.006.2022082044758_B03.TIF \
    s3://astraea-opendata/MCD43A4.006/28/08/2022073/MCD43A4.A2022073.h28v08.006.2022082044758_B04.TIF \
    s3://astraea-opendata/MCD43A4.006/28/08/2022073/MCD43A4.A2022073.h28v08.006.2022082044758_B05.TIF \
    s3://astraea-opendata/MCD43A4.006/28/08/2022073/MCD43A4.A2022073.h28v08.006.2022082044758_B06.TIF \
    s3://astraea-opendata/MCD43A4.006/28/08/2022073/MCD43A4.A2022073.h28v08.006.2022082044758_B07.TIF \
    build
```

To create a STAC `Catalog` from a list of MODIS asset hrefs, with one collection per MODIS product:

```shell
$ stac modis create-catalog examples/file-list-061.txt examples/modis-061
```

## Contributing

We use [pre-commit](https://pre-commit.com/) to check any changes.
To set up your development environment:

```shell
$ pip install -e .
$ pip install -r requirements-dev.txt
$ pre-commit install
```

To check all files:

```shell
$ pre-commit run --all-files
```

### Running tests

Because of the large number of MODIS products supported by this library and their asset file size, the default test suite does _not_ download all HDF files.
In addition, some of the Astraea assets require s3's requester-pays to be set, so they are skipped by default.

To run the quick test suite:

```shell
$ pytest
```

To run the slow tests, use the `--runslow` option for `pytest`:

```shell
$ pytest --runslow
```

This will download HDF files for all 061 products to `tests/data-files/external`.

To run the Astraea tests, use the `--s3-requester-pays` option:

```shell
$ pytest --s3-requester-pays
```

To run all tests:

```shell
$ pytest --s3-requester-pays --runslow
```

If you are making any changes to the item or collection structure, the tests will fail until you update the expected values.
To update, run this command:

```shell
$ python -m tests.create_expected
```

This will create, validate, and save new test data items into `tests/data-files/expected` which are used for unit testing.
Note that any non-trivial changes to the item or collection structure or attributes will mean that your changes will trigger a MAJOR release version of this library.

### Updating the example files

It's required to run all tests (see above for information about `--runslow` and `--s3-requester-pays`) before you can update the `examples/` directory.
If you don't have s3 set up to request payer, that's ok -- just open a PR anyways and the maintainers can update the examples.
If you can run all the tests, you can update the examples with:

```
$ stac modis create-catalog --create-cogs examples/file-list.txt examples
```

Note that this will take a while (~5-10 minutes).
If you need to update the examples later, you can omit the `--create-cogs` as the COGs will already be created.
