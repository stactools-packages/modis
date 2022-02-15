import os
from tempfile import TemporaryDirectory
from typing import Callable, List

import pystac
from click import Command, Group
from stactools.testing.cli_test import CliTestCase

from stactools.modis.commands import create_modis_command
from tests import test_data


class CreateItemTest(CliTestCase):

    def create_subcommand_functions(self) -> List[Callable[[Group], Command]]:
        return [create_modis_command]

    def test_create_item(self) -> None:
        infile = test_data.get_path(
            "data-files/MOD10A2.A2022033.h09v05.061.2022042050729.hdf.xml")

        with TemporaryDirectory() as temporary_directory:
            cmd = f"modis create-item --cogify {infile} {temporary_directory}"
            self.run_command(cmd)
            item_path = os.path.join(
                temporary_directory,
                "MOD10A2.A2022033.h09v05.061.2022042050729.json")
            item = pystac.read_file(item_path)
        item.validate()

    def test_cogify(self) -> None:
        infile = test_data.get_path(
            "data-files/MOD10A2.A2022033.h09v05.061.2022042050729.hdf")
        with TemporaryDirectory() as temporary_directory:
            command = f"modis cogify {infile} {temporary_directory}"
            self.run_command(command)
            file_names = os.listdir(temporary_directory)
            assert len(file_names) == 2
            assert all(
                os.path.splitext(file_name)[1] == ".tif"
                for file_name in file_names)
