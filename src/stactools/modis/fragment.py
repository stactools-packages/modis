import json
from typing import Any

import pkg_resources
from pystac import Extent, Link, Provider


def load(catalog_id: str, file_name: str) -> Any:
    """Load a fragment and return the resulting decoded JSON."""
    parts = catalog_id.split("/")
    with pkg_resources.resource_stream(
            "stactools.modis",
            f"fragments/{parts[1]}/{parts[2]}/{file_name}") as stream:
        return json.load(stream)


def load_collection(catalog_id: str) -> Any:
    """Loads the collection.json for the given catalog id.

    Does some conversion of the underlying fields into STAC objects.
    """
    data = load(catalog_id, "collection.json")
    data["extent"] = Extent.from_dict(data["extent"])
    data["providers"] = [
        Provider.from_dict(provider) for provider in data["providers"]
    ]
    data["links"] = [Link.from_dict(link) for link in data["links"]]
    return data


def load_bands(catalog_id: str) -> Any:
    """Loads the bands.json for the given catalog id."""
    return load(catalog_id, "bands.json")


def load_item_properties(catalog_id: str) -> Any:
    """Loads the item-properties.json for the given catalog id."""
    return load(catalog_id, "item-properties.json")
