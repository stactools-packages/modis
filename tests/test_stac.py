import json
import os.path
import shutil
import unittest
from tempfile import TemporaryDirectory

import pytest
from pystac import CatalogType

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
    collection_path = os.path.join(directory, "expected", file.product,
                                   file.version, "collection.json")
    item_path = os.path.join(directory, "expected", file.product, file.version,
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
    collection = stactools.modis.stac.create_collection(
        modis_file.product, modis_file.version)
    with TemporaryDirectory() as temporary_directory:
        temporary_metadata_path = os.path.join(temporary_directory,
                                               os.path.basename(metadata_path))
        expected_directory = os.path.join(temporary_directory, "expected",
                                          modis_file.product,
                                          modis_file.version)
        collection.set_self_href(
            os.path.join(expected_directory, "collection.json"))
        shutil.copyfile(metadata_path, temporary_metadata_path)
        item = stactools.modis.stac.create_item(temporary_metadata_path)
        collection.add_item(item)
        collection.make_all_asset_hrefs_relative()
        collection.save(catalog_type=CatalogType.SELF_CONTAINED)

        with open(collection.self_href) as file:
            collection_dict = json.load(file)
        test_case.assertDictEqual(collection_dict, expected_collection_dict)

        with open(os.path.join(expected_directory, item.id,
                               f"{item.id}.json")) as file:
            item_dict = json.load(file)
        test_case.assertDictEqual(item_dict, expected_item_dict)


def test_collection_id() -> None:
    assert stactools.modis.stac.collection_id(
        "product", "version") == "modis-product-version"
