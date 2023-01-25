import warnings
from typing import Any, List, cast

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


def version_string(version: str) -> str:
    if version == "6":
        return "006"
    elif version == "61":
        return "061"
    else:
        raise ValueError(f"Unsupported MODIS version: {version}")


def recursive_round(coordinates: List[Any], precision: int = 6) -> List[Any]:
    for idx, value in enumerate(coordinates):
        if isinstance(value, (int, float)):
            coordinates[idx] = round(value, precision)
        else:
            coordinates[idx] = list(value)  # handle any tuples
            coordinates[idx] = recursive_round(coordinates[idx], precision)
    return coordinates
