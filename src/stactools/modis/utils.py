import warnings
from typing import List, cast

import rasterio
from rasterio.errors import NotGeoreferencedWarning


def subdatasets(href: str) -> List[str]:
    """Returns a list of subdatasets from this HDF file href.

    Includes a warning-cathcher so you don't get a "no CRS" warning while doing it.

    Args:
        href (str): The HREF to a MODIS HDF file.

    Returns:
        List[str]: A list of subdatasets (GDAL-openable paths)
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=NotGeoreferencedWarning)
        with rasterio.open(href) as dataset:
            return cast(List[str], dataset.subdatasets)
