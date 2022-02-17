import logging
import os.path
import urllib.parse
from typing import Any, Dict, Optional, cast

import pystac
import rasterio
import shapely.geometry
import stactools.core.utils
from pystac import Asset, Collection, Item
from pystac.extensions.eo import Band, EOExtension
from pystac.extensions.item_assets import AssetDefinition, ItemAssetsExtension
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.raster import RasterBand, RasterExtension
from pystac.extensions.scientific import ScientificExtension
from stactools.core.io import ReadHrefModifier

import stactools.modis.cog
import stactools.modis.utils
from stactools.modis.constants import (HDF_ASSET_KEY, HDF_ASSET_PROPERTIES,
                                       METADATA_ASSET_KEY,
                                       METADATA_ASSET_PROPERTIES)
from stactools.modis.file import File
from stactools.modis.fragments import Fragments
from stactools.modis.metadata import Metadata
from stactools.modis.warnings import MissingProj, MissingRasterBand

logger = logging.getLogger(__name__)


def create_collection(product: str, version: str) -> Collection:
    """Creates a STAC Collection for MODIS data.

    Args:
        product (str): The ID of a MODIS product, e.g. "MCD12Q1"
        version (str): The MODIS version, e.g. "006" or "061"

    Returns:
        Collection: The created collection.
    """
    fragments = Fragments(product, version)
    fragment = fragments.collection()
    collection = pystac.Collection(
        id=collection_id(product, version),
        description=fragment["description"],
        extent=fragment["extent"],
        title=fragment["title"],
        providers=fragment["providers"],
    )
    collection.add_links(fragment["links"])

    item_assets = ItemAssetsExtension.ext(collection, add_if_missing=True)
    hdf_asset_properties = HDF_ASSET_PROPERTIES.copy()
    hdf_asset_properties["eo:bands"] = fragments.bands()
    item_assets.item_assets = {
        HDF_ASSET_KEY: AssetDefinition(hdf_asset_properties),
        METADATA_ASSET_KEY: AssetDefinition(METADATA_ASSET_PROPERTIES),
    }

    doi = _doi(fragment)
    if doi:
        scientific = ScientificExtension.ext(collection, add_if_missing=True)
        scientific.doi = doi

    return collection


def create_item(href: str,
                cog_directory: Optional[str] = None,
                create_cogs: Optional[bool] = None,
                read_href_modifier: Optional[ReadHrefModifier] = None) -> Item:
    """Creates a STAC Item from MODIS data.

    Args:
        href (str): The href to an HDF file or its metadata.
        cog_directory (str): The directory that will/does hold the COGs. Use
            `cogify` to actually create COGs there.
        create_cogs (str): Should we create cogs from the source data? If so, put
            them in `cog_directory`, or if that is `None`, put them alongside the
            hdf file.
        read_href_modifier (Callable[[str], str]): An optional function to
            modify the href (e.g. to add a token to a url)

    Returns:
        pystac.Item: A STAC Item representing this MODIS image.
    """
    file = File(href)
    metadata = Metadata(file.xml_href, read_href_modifier)
    fragments = Fragments(metadata.product, metadata.version)
    item = pystac.Item(id=metadata.id,
                       geometry=metadata.geometry,
                       bbox=metadata.bbox,
                       datetime=metadata.datetime,
                       properties=fragments.item_properties())

    item.common_metadata.instruments = metadata.instruments
    item.common_metadata.platform = metadata.platform
    item.common_metadata.start_datetime = metadata.start_datetime
    item.common_metadata.end_datetime = metadata.end_datetime
    item.common_metadata.created = metadata.created
    item.common_metadata.updated = metadata.updated
    properties = HDF_ASSET_PROPERTIES.copy()
    properties["href"] = file.hdf_href
    item.add_asset(HDF_ASSET_KEY, Asset.from_dict(properties))

    properties = METADATA_ASSET_PROPERTIES.copy()
    properties["href"] = file.xml_href
    item.add_asset(METADATA_ASSET_KEY, Asset.from_dict(properties))

    hdf_asset = item.assets[HDF_ASSET_KEY]

    eo = EOExtension.ext(hdf_asset, add_if_missing=True)
    eo.bands = [Band.create(**band) for band in fragments.bands()]

    raster_bands = fragments.raster_bands()
    if raster_bands:
        raster = RasterExtension.ext(hdf_asset, add_if_missing=True)
        bands = []
        for band in eo.bands:
            raster_band = raster_bands.get(band.name, None)
            if raster_band:
                bands.append(RasterBand.create(**raster_band))
            else:
                logger.warning(MissingRasterBand(item, band.name))
        raster.bands = bands

    url = urllib.parse.urlparse(file.hdf_href)
    is_local_hdf = not url.scheme and os.path.isfile(file.hdf_href)

    if is_local_hdf:
        subdatasets = stactools.modis.utils.subdatasets(file.hdf_href)
        if not subdatasets:
            raise ValueError(
                f"No subdatasets found in HDF file: {file.hdf_href}")
        with rasterio.open(subdatasets[0]) as dataset:
            crs = dataset.crs
            proj_bbox = dataset.bounds
            proj_transform = list(dataset.transform)[0:6]
            proj_shape = dataset.shape
        proj_geometry = shapely.geometry.mapping(
            shapely.geometry.box(*proj_bbox))
        projection = ProjectionExtension.ext(item, add_if_missing=True)
        projection.epsg = None
        projection.wkt2 = crs.to_wkt("WKT2")
        projection.geometry = proj_geometry
        projection.transform = proj_transform
        projection.shape = proj_shape
    else:
        logger.warning(MissingProj(item, file))

    if create_cogs:
        if not is_local_hdf:
            raise ValueError(
                f"Cannot cogify remote or non-existant HDF files: {file.hdf_href}"
            )
        elif not cog_directory:
            cog_directory = os.path.dirname(file.hdf_href)

    if cog_directory:
        stactools.modis.cog.add_cogs(item, cog_directory, create_cogs)

    return item


def collection_id(product: str, version: str) -> str:
    """Creates a collection id from a product and a version:

    Args:
        product (str): The MODIS product
        version (str): The MODIS version

    Returns:
        str: The collection id, e.g. "modis-MCD12Q1-006"
    """
    return f"modis-{product}-{version}"


def _doi(fragment: Dict[str, Any]) -> Optional[str]:
    providers = fragment.get("providers") or []
    for provider in providers:
        url = provider.url
        if not url:
            continue
        parsed_url = urllib.parse.urlparse(url)
        if parsed_url.hostname == "doi.org":
            return cast(str, parsed_url.path[1:])
    return None
