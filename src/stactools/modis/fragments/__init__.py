import json
from typing import Any

import pkg_resources
from pystac import Extent, Link, Provider


class Fragments:
    """Class for accessing fragment data for products and versions."""

    def __init__(self, product: str, version: str):
        """Creates a new group of fragments for the provided product and version."""
        self._product = product
        self._version = version

    def collection(self) -> Any:
        """Loads the collection.json for the given catalog id.

        Does some conversion of the underlying fields into STAC objects.

        Returns:
            Any: The contents of the fragment file, parsed as JSON and with some converted fields.
        """
        data = self._load("collection.json")
        data["extent"] = Extent.from_dict(data["extent"])
        data["providers"] = [
            Provider.from_dict(provider) for provider in data["providers"]
        ]
        data["links"] = [Link.from_dict(link) for link in data["links"]]
        return data

    def bands(self) -> Any:
        """Loads the bands.json for the given catalog id.

        Returns:
            Any: The contents of the fragment file, parsed as JSON.
        """
        return self._load("bands.json")

    def item_properties(self) -> Any:
        """Loads the item-properties.json for the given catalog id.

        Returns:
            Any: The contents of the fragment file, parsed as JSON.
        """
        return self._load("item-properties.json")

    def _load(self, file_name: str) -> Any:
        with pkg_resources.resource_stream(
                "stactools.modis",
                f"fragments/{self._product}/{self._version}/{file_name}"
        ) as stream:
            return json.load(stream)
