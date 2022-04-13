#!/usr/bin/env python3
# type: ignore

"""Creates fragment files from constants.py.

Should only need to be used for the initial migration from constants.py to
fragments, but kept around for posterity.
"""

import json
import os
from typing import List, cast

from pystac import Extent, Link, Provider

from stactools.modis.constants import (
    ADDITIONAL_MODIS_PROPERTIES,
    MODIS_BAND_DATA,
    MODIS_CATALOG_ELEMENTS,
)

root = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "src", "stactools", "modis", "fragments"
)


def make_fragments_directory(root: str, catalog_id: str) -> str:
    parts = catalog_id.split("/")
    path = os.path.join(root, parts[1], parts[2])
    os.makedirs(path, exist_ok=True)
    return path


for catalog_id, data in MODIS_CATALOG_ELEMENTS.items():
    directory = make_fragments_directory(root, catalog_id)
    path = os.path.join(directory, "collection.json")
    data["links"] = [link.to_dict() for link in cast(List[Link], data["links"])]
    data["providers"] = [cast(Provider, data["provider"]).to_dict()]
    del data["provider"]
    data["extent"] = cast(Extent, data["extent"]).to_dict()
    with open(path, "w") as file:
        json.dump(data, file, indent=4)

for catalog_id, bands in MODIS_BAND_DATA.items():
    directory = make_fragments_directory(root, catalog_id)
    path = os.path.join(directory, "bands.json")
    bands_as_dicts = [band.to_dict() for band in bands]
    with open(path, "w") as file:
        json.dump(bands_as_dicts, file, indent=4)

for catalog_id, properties in ADDITIONAL_MODIS_PROPERTIES.items():
    directory = make_fragments_directory(root, catalog_id)
    path = os.path.join(directory, "item-properties.json")
    with open(path, "w") as file:
        json.dump(properties, file, indent=4)
