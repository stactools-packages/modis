import logging
import warnings
from typing import Any, Dict, List, cast

import rasterio
from pystac import Item
from rasterio.errors import NotGeoreferencedWarning
from stactools.core.utils.raster_footprint import update_geometry_from_asset_footprint

from stactools.modis.constants import COLLECTIONS, PRECISION, SIN_TILE_METERS

logger = logging.getLogger(__name__)


class FootprintError(Exception):
    """Raster data footprint failure."""


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


def recursive_round(coordinates: List[Any]) -> List[Any]:
    for idx, value in enumerate(coordinates):
        if isinstance(value, (int, float)):
            coordinates[idx] = round(value, PRECISION)
        else:
            coordinates[idx] = list(value)  # handle any tuples
            coordinates[idx] = recursive_round(coordinates[idx])
    return coordinates


def get_collection_info(collection: str) -> Dict[str, Any]:
    collection_info = COLLECTIONS.get(collection, None)
    if collection_info is None:
        raise ValueError(f"Unsupported MODIS collection: {collection}")
    return collection_info


def tile_pixel_size(collection: str) -> int:
    collection_info = get_collection_info(collection)
    tile_pixel_size: int = collection_info["sin_tile_pixels"]
    return tile_pixel_size


def pixel_degrees(tile_pixel_size: int) -> float:
    return SIN_TILE_METERS / tile_pixel_size / 100000  # at equator


def raster_data_footprint_geometry(item: Item, collection: str) -> Item:
    simplify_tolerance = pixel_degrees(tile_pixel_size(collection)) / 2
    collection_info = get_collection_info(collection)
    asset_names = collection_info.get("footprint_assets", None)
    try:
        if asset_names is None:
            raise ValueError(
                f"Raster data footprint geometry not supported for collection '{collection}'."
            )
        bands = collection_info.get("footprint_asset_bands", None) or [1]
        success = update_geometry_from_asset_footprint(
            item,
            asset_names=asset_names,
            precision=PRECISION,
            densification_factor=20,
            simplify_tolerance=simplify_tolerance,
            bands=bands,
        )
        if not success:
            logger.warning(
                f"Geometry generation from raster data footprint was not successful "
                f"for Item {item.id}. Default tile geometry retained."
            )
    except Exception:
        logger.error(
            (
                f"Geometry generation from raster data footprint failed with an "
                f"exception for Item {item.id}. Default tile geometry retained."
            ),
            exc_info=True,
        )
    return item
