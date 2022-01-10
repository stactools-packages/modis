import os.path
from tempfile import TemporaryDirectory
from unittest import TestCase

from stactools.modis import cog

from tests import test_data


class CogTest(TestCase):

    def test_cogify(self) -> None:
        infile = test_data.get_path(
            "data-files/MCD12Q1.A2001001.h00v08.006.2018142182903.hdf")
        with TemporaryDirectory() as temporary_directory:
            cog.cogify(infile, temporary_directory)
            file_names = os.listdir(temporary_directory)
        self.assertEqual(len(file_names), 13)
        subdataset_names = [
            "LC_Type1", "LC_Type2", "LC_Type3", "LC_Type4", "LC_Type5",
            "LC_Prop1_Assessment", "LC_Prop2_Assessment",
            "LC_Prop3_Assessment", "LC_Prop1", "LC_Prop2", "LC_Prop3", "QC",
            "LW"
        ]
        expected_cog_names = [
            f"MCD12Q1.A2001001.h00v08.006.2018142182903_{subdataset_name}.tif"
            for subdataset_name in subdataset_names
        ]
        self.assertEqual(set(file_names), set(expected_cog_names))
