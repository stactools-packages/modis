import json
import os.path
from tempfile import TemporaryDirectory
import unittest

from pystac import CatalogType
import pytest

import stactools.modis.stac
from stactools.modis.file import File

from . import test_data

directory = test_data.get_path("data-files")
args = []
ids = []
for file_name in os.listdir(directory):
    if os.path.splitext(file_name)[1] != ".xml":
        continue
    file = File(os.path.join(directory, file_name))
    collection_path = os.path.join(directory, "expected", file.version,
                                   file.product, "collection.json")
    item_path = os.path.join(directory, "expected", file.version, file.product,
                             file.id, f"{file.id}.json")
    args.append((file.path, collection_path, item_path))
    ids.append(file.product)


@pytest.mark.parametrize("metadata_path,collection_path,item_path",
                         args,
                         ids=ids)
def test_metadata_files(metadata_path: str, collection_path: str,
                        item_path: str) -> None:
    """Compares creates STAC Collections and Items to expected values (located
    in tests/data-files/expected.

    If you change the logic in the STAC object creation, or you add new
    products, run `scripts/create_expected.py` to regenerate the expected STAC
    objects.
    """
    test_case = unittest.TestCase()
    test_case.maxDiff = None
    with open(collection_path) as file:
        expected_collection_dict = json.load(file)
    with open(item_path) as file:
        expected_item_dict = json.load(file)

    modis_file = File(metadata_path)
    collection = stactools.modis.stac.create_collection(modis_file.catalog_id)
    item = stactools.modis.stac.create_item(metadata_path)
    with TemporaryDirectory() as temporary_directory:
        collection.set_self_href(
            os.path.join(temporary_directory, "collection.json"))
        collection.add_item(item)
        collection.save(catalog_type=CatalogType.SELF_CONTAINED)

        with open(os.path.join(temporary_directory,
                               "collection.json")) as file:
            collection_dict = json.load(file)
        test_case.assertDictEqual(collection_dict, expected_collection_dict)

        with open(os.path.join(temporary_directory, item.id,
                               f"{item.id}.json")) as file:
            item_dict = json.load(file)
        test_case.assertDictEqual(item_dict, expected_item_dict)
