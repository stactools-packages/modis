import os.path
from tempfile import TemporaryDirectory
from unittest import TestCase

import pytest
from pystac import MediaType

import stactools.modis.cog
import stactools.modis.stac
from tests import test_data

SUBDATASET_NAMES = ["Eight_Day_Snow_Cover", "Maximum_Snow_Extent"]
FAILING_COG_FILE_NAMES = [
    "MOD14A1.A2022049.h09v05.061.2022057235503.hdf",
    "MOD13Q1.A2022033.h09v05.061.2022051005101.hdf",
    "MOD14A1.A2022049.h09v05.061.2022057235503.hdf",
    "MYD10A1.A2022059.h09v05.061.2022061043435.hdf",
    "MYD13A1.A2022041.h09v05.061.2022059190534.hdf",
    "MYD13Q1.A2022041.h09v05.061.2022059190716.hdf",
    "MYD14A1.A2022049.h09v05.061.2022057234556.hdf",
]


class CogTest(TestCase):

    def test_add_cogs(self) -> None:
        infile = test_data.get_path(
            "data-files/MOD10A2.A2022033.h09v05.061.2022042050729.hdf")
        item = stactools.modis.stac.create_item(infile)
        paths, subdataset_names = stactools.modis.cog.add_cogs(
            item, os.path.dirname(infile))
        assert set(subdataset_names) == set(SUBDATASET_NAMES)
        assert len(paths) == len(SUBDATASET_NAMES)
        for subdataset_name in SUBDATASET_NAMES:
            asset = item.assets[subdataset_name]
            assert os.path.basename(
                asset.href
            ) == f"MOD10A2.A2022033.h09v05.061.2022042050729_{subdataset_name}.tif"
            assert asset.media_type == MediaType.COG

    def test_add_no_cogs(self) -> None:
        infile = test_data.get_path(
            "data-files/MOD10A2.A2022033.h09v05.061.2022042050729.hdf")
        item = stactools.modis.stac.create_item(infile)
        with pytest.raises(ValueError):
            stactools.modis.cog.add_cogs(item, os.path.dirname(__file__))

    def test_cogify(self) -> None:
        infile = test_data.get_path(
            "data-files/MOD10A2.A2022033.h09v05.061.2022042050729.hdf")
        with TemporaryDirectory() as temporary_directory:
            paths, _ = stactools.modis.cog.cogify(infile, temporary_directory)
            assert all(os.path.exists(path) for path in paths)
        self.assertEqual(len(paths), 2)
        file_names = [os.path.basename(path) for path in paths]
        expected_cog_names = [
            f"MOD10A2.A2022033.h09v05.061.2022042050729_{subdataset_name}.tif"
            for subdataset_name in SUBDATASET_NAMES
        ]
        self.assertEqual(set(file_names), set(expected_cog_names))


@pytest.mark.parametrize("file_name", FAILING_COG_FILE_NAMES)
@pytest.mark.skip(reason="these are very long and were used for a one-time fix"
                  )
def test_failing_cogs(file_name: str) -> None:
    """These tests are from an initial attempt at cogifying all 36 modis V061
    products in late February 2022.
    """
    infile = test_data.get_external_data(file_name)
    _ = test_data.get_external_data(f"{file_name}.xml")
    item = stactools.modis.stac.create_item(infile)
    with TemporaryDirectory() as temporary_directory:
        _, _ = stactools.modis.cog.cogify(infile, temporary_directory)
        stactools.modis.cog.add_cogs(item, temporary_directory, create=False)
