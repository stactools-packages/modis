import json
from typing import Any, List

import pkg_resources
from pystac import Extent, Link, Provider

PREFIXES = ["MCD", "MOD", "MYD"]


class Fragments:
    """Class for accessing fragment data for products and versions."""

    def __init__(self, product: str, version: str):
        """Creates a new group of fragments for the provided product and version."""
        self._product = product
        self._version = version
        self._optional_file_names = ["raster-bands.json"]

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

    def raster_bands(self) -> Any:
        """Loads the raster-bands.json for the given catalog id.

        Returns:
            Any: The contents of the fragment file, parsed as JSON.
        """
        return self._load("raster-bands.json")

    def item_properties(self) -> Any:
        """Loads the item-properties.json for the given catalog id.

        Returns:
            Any: The contents of the fragment file, parsed as JSON.
        """
        return self._load("item-properties.json")

    def prefix(self) -> str:
        """The product prefix (aka MCD, MYD, or MOD)."""
        return self._product[0:3]

    def with_prefix(self, prefix: str) -> "Fragments":
        """Returns this fragments but with a different prefix."""
        product = self._product.replace(self.prefix(), prefix)
        return Fragments(product, self._version)

    def _load(self, file_name: str) -> Any:
        fallbacks = PREFIXES.copy()
        fallbacks.remove(self.prefix())
        try:
            return self._load_with_fallbacks(file_name, fallbacks)
        except FragmentMissing:
            raise FragmentMissing(
                f"Fragment missing for product={self._product}, "
                f"version={self._version}: {file_name}")

    def _load_with_fallbacks(self, file_name: str,
                             fallbacks: List[str]) -> Any:
        package = "stactools.modis.fragments"
        path = f"{self._product}/{self._version}/{file_name}"
        if pkg_resources.resource_exists(package, path):
            with pkg_resources.resource_stream(package, path) as stream:
                return json.load(stream)
        elif fallbacks:
            prefix = fallbacks.pop(0)
            fragments = self.with_prefix(prefix)
            return fragments._load_with_fallbacks(file_name, fallbacks)
        elif file_name in self._optional_file_names:
            return None
        else:
            raise FragmentMissing()


class FragmentMissing(Exception):
    pass
