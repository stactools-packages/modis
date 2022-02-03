import json
from typing import Any

import pkg_resources
from pystac import Extent, Link, Provider


def load(product: str, version: str, file_name: str) -> Any:
    """Loads a fragment and return the resulting decoded JSON.

    Args:
        product (str): The ID of a MODIS product, e.g. "MCD12Q1"
        version (str): The MODIS version, e.g. "006" or "061"
        file_name (str): The fragment file name to read, e.g. "collection.json"

    Returns:
        Any: The contents of the fragment file, parsed as JSON.
    """
    with pkg_resources.resource_stream(
            "stactools.modis",
            f"fragments/{product}/{version}/{file_name}") as stream:
        return json.load(stream)


def load_collection(product: str, version: str) -> Any:
    """Loads the collection.json for the given catalog id.

    Does some conversion of the underlying fields into STAC objects.

    Args:
        product (str): The ID of a MODIS product, e.g. "MCD12Q1"
        version (str): The MODIS version, e.g. "006" or "061"

    Returns:
        Any: The contents of the fragment file, parsed as JSON and with some converted fields.
    """
    data = load(product, version, "collection.json")
    data["extent"] = Extent.from_dict(data["extent"])
    data["providers"] = [
        Provider.from_dict(provider) for provider in data["providers"]
    ]
    data["links"] = [Link.from_dict(link) for link in data["links"]]
    return data


def load_bands(product: str, version: str) -> Any:
    """Loads the bands.json for the given catalog id.

    Args:
        product (str): The ID of a MODIS product, e.g. "MCD12Q1"
        version (str): The MODIS version, e.g. "006" or "061"

    Returns:
        Any: The contents of the fragment file, parsed as JSON.
    """
    return load(product, version, "bands.json")


def load_item_properties(product: str, version: str) -> Any:
    """Loads the item-properties.json for the given catalog id.

    Args:
        product (str): The ID of a MODIS product, e.g. "MCD12Q1"
        version (str): The MODIS version, e.g. "006" or "061"

    Returns:
        Any: The contents of the fragment file, parsed as JSON.
    """
    return load(product, version, "item-properties.json")
