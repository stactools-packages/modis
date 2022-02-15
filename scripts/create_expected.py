#!/usr/bin/env python3

import os

from pystac import CatalogType

import stactools.modis.stac
from stactools.modis.file import File

data_files_directory = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                    "tests", "data-files")
expected_directory = os.path.join(data_files_directory, "expected")

cog_product = "MCD12Q1"
cog_version = "006"

for file_name in os.listdir(data_files_directory):
    if os.path.splitext(file_name)[1] == ".xml":
        file = File(os.path.join(data_files_directory, file_name))
        collection = stactools.modis.stac.create_collection(
            file.product, file.version)
        collection_path = os.path.join(expected_directory, file.product,
                                       file.version, "collection.json")
        collection.set_self_href(collection_path)

        if file.product == cog_product and file.version == cog_version:
            cog_directory = data_files_directory
        else:
            cog_directory = None
        item = stactools.modis.stac.create_item(file.href,
                                                cog_directory=cog_directory)
        item.validate()

        collection.add_item(item)
        collection.make_all_asset_hrefs_relative()
        collection.save(catalog_type=CatalogType.SELF_CONTAINED)
