import os
from tempfile import TemporaryDirectory
from typing import List, Callable

from click import Group, Command
import pystac
from stactools.testing.cli_test import CliTestCase

from stactools.modis.commands import create_modis_command
from tests import test_data


class CreateItemTest(CliTestCase):

    def create_subcommand_functions(self) -> List[Callable[[Group], Command]]:
        return [create_modis_command]

    def test_create_item(self) -> None:
        metadata_href = test_data.get_path(
            'data-files/MCD12Q1.A2001001.h00v08.006.2018142182903.hdf.xml')

        with TemporaryDirectory() as tmp_dir:
            cmd = f"modis create-item {metadata_href} {tmp_dir}"
            self.run_command(cmd)

            jsons = [p for p in os.listdir(tmp_dir) if p.endswith('.json')]

            self.assertEqual(len(jsons), 1)

            item_path = os.path.join(tmp_dir, jsons[0])

            item = pystac.read_file(item_path)

        item.validate()
