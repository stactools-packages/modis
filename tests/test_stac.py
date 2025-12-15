import json
import os.path
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from pystac import CatalogType, MediaType

import stactools.modis.stac
from stactools.modis.file import File

from . import ASTRAEA_EXTERNAL_FILE_NAMES, test_data

directory = test_data.get_path("data-files")
args = []
ids = []
for file_name in os.listdir(directory):
    if os.path.splitext(file_name)[1] != ".xml":
        continue
    file = File(os.path.join(directory, file_name))
    collection_path = os.path.join(
        directory, "expected", str(file.product), file.version, "collection.json"
    )
    item_path = os.path.join(
        directory,
        "expected",
        str(file.product),
        file.version,
        file.id,
        f"{file.id}.json",
    )
    args.append((file.href, collection_path, item_path))
    ids.append(str(file.product))

cog_product = "MOD10A2"
cog_version = "061"

COG_FILE_NAMES = [
    "MCD43A4.A2022073.h28v08.006.2022082044758_B01_cropped.TIF",
    "MOD11A1.A2022103.h09v05.006.2022104093154_CDC_B11_cropped.TIF",
    "MOD13A1.A2022081.h09v05.006.2022101145817_BR_B06_cropped.TIF",
]

PROJECTION_EDGE_FILES = [
    "MYD11A2.A2022025.h17v00.061.2022035054130.hdf",
    "MYD13A1.A2022009.h25v02.061.2022028071925.hdf",
    "MYD14A1.A2022025.h01v07.061.2022035001141.hdf",
    "MCD15A2H.A2022025.h01v11.061.2022035062702.hdf",
    "MYD16A3GF.A2021001.h11v02.061.2022024220526.hdf",
]


@pytest.mark.parametrize("metadata_path,collection_path,item_path", args, ids=ids)
def test_metadata_files(
    metadata_path: str, collection_path: str, item_path: str
) -> None:
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
        str(modis_file.product), modis_file.version
    )
    with TemporaryDirectory() as temporary_directory:
        temporary_metadata_path = os.path.join(
            temporary_directory, os.path.basename(metadata_path)
        )
        temporary_file = File(temporary_metadata_path)
        expected_directory = os.path.join(
            temporary_directory, "expected", str(modis_file.product), modis_file.version
        )
        collection.set_self_href(os.path.join(expected_directory, "collection.json"))
        shutil.copyfile(modis_file.xml_href, temporary_file.xml_href)
        if os.path.exists(modis_file.hdf_href):
            shutil.copyfile(modis_file.hdf_href, temporary_file.hdf_href)

        if (
            str(temporary_file.product) == cog_product
            and temporary_file.version == cog_version
        ):
            cog_directory = temporary_directory
            create_cogs = True
        else:
            cog_directory = None
            create_cogs = False
        item = stactools.modis.stac.create_item(
            temporary_metadata_path,
            cog_directory=cog_directory,
            create_cogs=create_cogs,
        )
        collection.add_item(item)
        collection.make_all_asset_hrefs_relative()
        collection.save(catalog_type=CatalogType.SELF_CONTAINED)

        with open(collection.self_href) as file:
            collection_dict = json.load(file)
        test_case.assertDictEqual(collection_dict, expected_collection_dict)

        with open(os.path.join(expected_directory, item.id, f"{item.id}.json")) as file:
            item_dict = json.load(file)
        test_case.assertDictEqual(item_dict, expected_item_dict)


def test_collection_id() -> None:
    assert (
        stactools.modis.stac.collection_id("product", "version")
        == "modis-product-version"
    )


def test_read_href_modifier() -> None:
    href = test_data.get_path(
        "data-files/MOD10A2.A2022033.h09v05.061.2022042050729.hdf.xml"
    )

    did_it = False

    def read_href_modifier(href: str) -> str:
        nonlocal did_it
        did_it = True
        return href

    _ = stactools.modis.stac.create_item(href, read_href_modifier=read_href_modifier)
    assert did_it


def test_cog_directory() -> None:
    href = test_data.get_path(
        "data-files/MOD10A2.A2022033.h09v05.061.2022042050729.hdf.xml"
    )
    item = stactools.modis.stac.create_item(href, cog_directory=os.path.dirname(href))

    cog_assets = [
        asset for asset in item.assets.values() if asset.media_type == MediaType.COG
    ]
    assert len(cog_assets) == 2


@pytest.mark.parametrize("file_name", COG_FILE_NAMES)
def test_cog(file_name: str) -> None:
    href = test_data.get_path(f"data-files/{file_name}")
    item_file_name = os.path.splitext(file_name)[0] + ".json"
    expected_path = test_data.get_path(f"data-files/expected/{item_file_name}")
    item = stactools.modis.stac.create_item_from_cogs([href])
    item.set_self_href(expected_path)
    item.make_asset_hrefs_relative()
    item.validate()
    with TemporaryDirectory() as temporary_directory:
        path = os.path.join(temporary_directory, item_file_name)
        item.save_object(
            include_self_link=False,
            dest_href=path,
        )
        with open(path) as file:
            actual_item = json.load(file)
    with open(expected_path) as file:
        expected_item = json.load(file)
    test_case = unittest.TestCase()
    test_case.maxDiff = None
    test_case.assertDictEqual(actual_item, expected_item)


@pytest.mark.parametrize("key", ASTRAEA_EXTERNAL_FILE_NAMES.keys())
@pytest.mark.s3_requester_pays
def test_astraea(key: str) -> None:
    value = ASTRAEA_EXTERNAL_FILE_NAMES[key]
    file_names = value["file_names"]
    paths = []
    for file_name in file_names:
        paths.append(test_data.get_external_data(file_name))
    item = stactools.modis.stac.create_item_from_cogs(paths)
    item.validate()


def test_raster_footprint_geometry() -> None:
    path = test_data.get_path("MYD10A2.A2022025.h10v05.061.2022035071201.hdf")
    if not Path(path).exists():
        pytest.skip(
            f"Skipping {path} because it does not exist and we can't fetch "
            "it from Microsoft anymore"
        )
    hdf_href = test_data.get_external_data(
        "MYD10A2.A2022025.h10v05.061.2022035071201.hdf"
    )
    _ = test_data.get_external_data("MYD10A2.A2022025.h10v05.061.2022035071201.hdf.xml")
    with TemporaryDirectory() as temporary_directory:
        item = stactools.modis.stac.create_item(
            href=hdf_href,
            cog_directory=temporary_directory,
            create_cogs=True,
            raster_footprint=True,
        )
        assert len(item.geometry["coordinates"][0]) == 35
        item.validate()


def test_create_item_from_hdf_without_xml(tmp_path: Path) -> None:
    hdf_file = "MOD10A2.A2022033.h09v05.061.2022042050729.hdf"
    source_hdf_path = test_data.get_path(f"data-files/{hdf_file}")

    temp_hdf_path = tmp_path / hdf_file
    shutil.copyfile(source_hdf_path, temp_hdf_path)

    temp_xml_path = tmp_path / f"{hdf_file}.xml"
    assert not temp_xml_path.exists()

    item = stactools.modis.stac.create_item(str(temp_hdf_path))

    assert item is not None
    assert item.id.startswith("MOD10A2.A2022033.h09v05")
    assert "hdf" in item.assets
    assert "metadata" not in item.assets
    item.validate()


@pytest.mark.parametrize("file_name", PROJECTION_EDGE_FILES)
def test_raster_footprint_at_projection_edge(file_name: str) -> None:
    path = test_data.get_path(file_name)
    if not Path(path).exists():
        pytest.skip(
            f"Skipping {file_name} because it does not exist and we can't "
            "fetch it from Microsoft anymore"
        )
    hdf_href = test_data.get_external_data(file_name)
    _ = test_data.get_external_data(f"{file_name}.xml")
    with TemporaryDirectory() as temporary_directory:
        # Tile Footprint
        item = stactools.modis.stac.create_item(
            href=hdf_href,
            cog_directory=temporary_directory,
            create_cogs=True,
            raster_footprint=False,
        )
        assert item.geometry["type"] == "Polygon"  # not MultiPolygon
        item.validate()

        # Data Footprint
        item = stactools.modis.stac.create_item(
            href=hdf_href,
            cog_directory=temporary_directory,
            create_cogs=True,
            raster_footprint=True,
        )
        assert item.geometry["type"] == "Polygon"  # not MultiPolygon
        item.validate()
