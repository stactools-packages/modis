import os.path

import pystac.utils
from pystac import Item

from stactools.modis.constants import HDF_ASSET_KEY
from stactools.modis.fragments import Fragments


class File:
    """A MODIS file."""

    href: str
    hdf_href: str
    xml_href: str
    product: str
    version: str
    id: str

    @classmethod
    def from_item(cls, item: Item) -> "File":
        """Creates a File from an item.

        Raises a value error if there is no HDF asset on the item.

        Args:
            item (pystac.Item): The item

        Returns:
            file (File): A file pointing to the item's assets

        """
        hdf_asset = item.assets.get(HDF_ASSET_KEY, None)
        if hdf_asset is None:
            raise ValueError(f"No HDF asset found on item: {item.id}")
        hdf_href = hdf_asset.href
        return File(hdf_href)

    def __init__(self, href: str):
        """Creates a new MODIS file from an href.

        Args:
            href (str): The .hdf or .hdf.xml href to MODIS data
        """
        href = pystac.utils.make_absolute_href(href)
        base, extension = os.path.splitext(href)
        if extension not in [".hdf", ".xml"]:
            raise ValueError(f"Invalid MODIS href: {href}")
        elif extension == ".xml":
            if os.path.splitext(base)[1] != ".hdf":
                raise ValueError(
                    f"Invalid MODIS metadata href (no .hdf.xml): {href}")
            else:
                self.xml_href = href
                self.hdf_href = base
        else:
            self.xml_href = f"{href}.xml"
            self.hdf_href = href
        self.href = href
        file_name = os.path.basename(self.hdf_href)
        parts = file_name.split(".")
        if len(parts) < 4:
            raise ValueError(
                f"Invalid MODIS file name (not enough '.'-separated parts): {file_name}"
            )
        self.product = parts[0]
        self.version = parts[3]
        self.id = os.path.splitext(file_name)[0]
        self.fragments = Fragments(self.product, self.version)
