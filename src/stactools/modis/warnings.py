from pystac import Item

from stactools.modis.file import File


class MissingProj(UserWarning):
    """Raised when there is missing proj information on an item."""

    def __init__(self, item: Item, file: File):
        """Creates a new missing proj warning from an item and a file."""
        super().__init__(f"No PROJ information on {item.id}, "
                         f"{file.hdf_href} is a remote file or not present")


class MissingRasterBand(UserWarning):
    """Raised when there is missing raster band information."""

    def __init__(self, item: Item, subdataset_name: str):
        """Creates a new missing raster band inforamtion."""
        super().__init__(
            f"Missing raster band for {item.id}: {subdataset_name}")
