import logging
import math
from itertools import groupby
from typing import Any, Dict, List, Tuple

import numpy as np
from pystac import Item
from shapely.geometry.polygon import Polygon
from stactools.core.utils.raster_footprint import RasterFootprint, densify_by_distance
from stactools.core.utils.round import recursive_round

from stactools.modis.constants import (
    COLLECTION_FOOTPRINT_METADATA,
    PRECISION,
    SINUSOIDAL_SPHERE_RADIUS,
    SINUSOIDAL_TILE_METERS,
)

logger = logging.getLogger(__name__)


class SinusoidalFootprint(RasterFootprint):
    def densify_polygon(self, polygon: Polygon) -> Polygon:
        # We densify at pixel distance to ensure that the final footprint
        # polygon never strays further than the specified `simplify_tolerance`
        # from the edge of the raster data.
        return Polygon(densify_by_distance(polygon.exterior.coords, self.transform[0]))

    def reproject_polygon(self, polygon: Polygon) -> Polygon:
        lonlat_list = sinusoidal_grid_to_lonlat(polygon.exterior.coords)
        # Conversion from grid to lon/lat for tiles that contain pixels beyond
        # the projection edge produces coords beyond the antimeridian. Clipping
        # to the natural extents of the projection cleans this up.
        lonlat_array = np.asarray(lonlat_list)
        np.clip(lonlat_array[:, 0], -180, 180, lonlat_array[:, 0])
        np.clip(lonlat_array[:, 1], -90, 90, lonlat_array[:, 1])
        polygon = Polygon(
            recursive_round(lonlat_array.tolist(), precision=self.precision)
        )
        polygon = Polygon([k for k, _ in groupby(polygon.exterior.coords)])
        return polygon


def sinusoidal_grid_to_lonlat(
    grid_coords: List[Tuple[float, float]]
) -> List[Tuple[float, float]]:
    """Transform MODIS and VIIRS sinusoidal projection grid coordinates to
    spherical longitude and latitude.

    Args:
        grid_coords (List[Tuple[float, float]]): List of sinusoidal projection
            grid coordinate tuples in (x, y) order.

    Returns:
        List[Tuple[float, float]]: List of spherical longitude and latitude
            coordinate tuples in (longitude, latitude) order.
    """
    lonlat = []
    for x, y in grid_coords:
        latitude = math.degrees(y / SINUSOIDAL_SPHERE_RADIUS)
        longitude = math.degrees(
            x / (SINUSOIDAL_SPHERE_RADIUS * math.cos(y / SINUSOIDAL_SPHERE_RADIUS))
        )
        lonlat.append((longitude, latitude))
    return lonlat


def get_collection_footprint_metadata(collection: str) -> Dict[str, Any]:
    footprint_metadata = COLLECTION_FOOTPRINT_METADATA.get(collection, None)
    if footprint_metadata is None:
        raise ValueError(f"Unsupported MODIS collection: {collection}")
    return footprint_metadata


def tile_pixel_size(collection: str) -> int:
    """Returns the dimension of a MODIS tile in pixels for a given `collection`.

    The tiles are square and thus defined by a single dimension.

    Args:
        collection (str): MODIS collection (aka product) string.

    Returns:
        int: Number of pixels along the tile edge.
    """
    footprint_metadata = get_collection_footprint_metadata(collection)
    tile_pixel_size: int = footprint_metadata["sin_tile_pixels"]
    return tile_pixel_size


def pixel_degree_size(collection: str) -> float:
    """Returns the ground pixel size in degrees (at the equator) for a single
    pixel of a MODIS raster for a given `collection`.

    Args:
        collection (str): MODIS collection (aka product) string.

    Returns:
        float: Ground pixel size in degrees.
    """
    return SINUSOIDAL_TILE_METERS / tile_pixel_size(collection) / 100000  # at equator


def update_geometry(item: Item, collection: str) -> None:
    """Updates an Item geometry in-place with the footprint of raster data.

    Args:
        item (Item): PySTAC Item to be updated.
        collection (str): MODIS collection (aka product) string.
    """
    footprint_metadata = get_collection_footprint_metadata(collection)
    asset_names = footprint_metadata.get("footprint_assets", None)
    if asset_names is None:
        raise ValueError(
            f"Raster data footprint geometry not supported for collection '{collection}'."
        )
    bands = footprint_metadata.get("footprint_asset_bands", None) or [1]
    success = SinusoidalFootprint.update_geometry_from_asset_footprint(
        item,
        asset_names=asset_names,
        precision=PRECISION,
        simplify_tolerance=pixel_degree_size(collection) / 2,
        bands=bands,
    )
    if not success:
        logger.warning(
            f"Geometry generation from raster data footprint was not successful "
            f"for Item {item.id}. Default tile geometry retained."
        )
