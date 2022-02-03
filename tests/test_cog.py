import os.path
from tempfile import TemporaryDirectory
from unittest import TestCase

from pystac import MediaType

import stactools.modis.cog
import stactools.modis.stac
from tests import test_data

SUBDATASET_NAMES = [
    "LC_Type1", "LC_Type2", "LC_Type3", "LC_Type4", "LC_Type5",
    "LC_Prop1_Assessment", "LC_Prop2_Assessment", "LC_Prop3_Assessment",
    "LC_Prop1", "LC_Prop2", "LC_Prop3", "QC", "LW"
]


class CogTest(TestCase):

    def test_cog(self) -> None:
        infile = test_data.get_path(
            "data-files/MCD12Q1.A2001001.h00v08.006.2018142182903.hdf")
        item = stactools.modis.stac.create_item(infile)
        with TemporaryDirectory() as temporary_directory:
            stactools.modis.cog.add_cogs(item, temporary_directory)
        for subdataset_name in SUBDATASET_NAMES:
            asset = item.assets[subdataset_name]
            assert os.path.basename(
                asset.href
            ) == f"MCD12Q1.A2001001.h00v08.006.2018142182903_{subdataset_name}.tif"
            assert asset.media_type == MediaType.COG

    def test_cogify(self) -> None:
        infile = test_data.get_path(
            "data-files/MCD12Q1.A2001001.h00v08.006.2018142182903.hdf")
        with TemporaryDirectory() as temporary_directory:
            paths, _ = stactools.modis.cog.cogify(infile, temporary_directory)
        self.assertEqual(len(paths), 13)
        file_names = [os.path.basename(path) for path in paths]
        expected_cog_names = [
            f"MCD12Q1.A2001001.h00v08.006.2018142182903_{subdataset_name}.tif"
            for subdataset_name in SUBDATASET_NAMES
        ]
        self.assertEqual(set(file_names), set(expected_cog_names))
