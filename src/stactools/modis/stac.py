import logging
import os.path
import urllib.parse
from typing import Optional

import pystac
import pystac.utils
import rasterio
import shapely.geometry
import stactools.core.utils
import stactools.core.utils.antimeridian
from pystac import Asset, Collection, Item, MediaType, Summaries
from pystac.extensions.eo import EOExtension
from pystac.extensions.item_assets import AssetDefinition, ItemAssetsExtension
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.raster import RasterExtension
from pystac.extensions.scientific import ScientificExtension
from stactools.core.io import ReadHrefModifier
from stactools.core.utils.antimeridian import Strategy

import stactools.modis.cog
import stactools.modis.utils
from stactools.modis.constants import (CLASSIFICATION_EXTENSION_HREF,
                                       HDF_ASSET_KEY, HDF_ASSET_PROPERTIES,
                                       METADATA_ASSET_KEY,
                                       METADATA_ASSET_PROPERTIES)
from stactools.modis.file import File
from stactools.modis.metadata import Metadata
from stactools.modis.product import Product
from stactools.modis.warnings import MissingProj

logger = logging.getLogger(__name__)


def create_collection(product_name: str, version: str) -> Collection:
    """Creates a STAC Collection for MODIS data.

    Args:
        product (str): The ID of a MODIS product, e.g. "MCD12Q1"
        version (str): The MODIS version, e.g. "006" or "061"

    Returns:
        Collection: The created collection.
    """
    product = Product(product_name)
    summaries = {
        "instruments": ["modis"],
        "platform": product.platforms,
    }
    fragments = product.fragments(version)
    item = fragments.item()
    gsd = item.get("gsd")
    if gsd:
        summaries["gsd"] = [gsd]

    fragment = fragments.collection()
    collection = pystac.Collection(id=product.collection_id(version),
                                   description=fragment["description"],
                                   extent=fragment["extent"],
                                   title=fragment["title"],
                                   providers=fragment["providers"],
                                   keywords=fragment.get("keywords", list()),
                                   summaries=Summaries(summaries))
    collection.add_links(fragment["links"])

    item_assets_dict = {
        HDF_ASSET_KEY: AssetDefinition(HDF_ASSET_PROPERTIES),
        METADATA_ASSET_KEY: AssetDefinition(METADATA_ASSET_PROPERTIES),
    }
    for name, band in fragments.bands().items():
        if "roles" in band:
            band["roles"].append("data")
        else:
            band["roles"] = ["data"]
        band["type"] = MediaType.COG
        item_assets_dict[name] = AssetDefinition(band)
        if "eo:bands" in band:
            collection.stac_extensions.append(EOExtension.get_schema_uri())
        if "raster:bands" in band:
            collection.stac_extensions.append(RasterExtension.get_schema_uri())
        if "classification:classes" in band:
            collection.stac_extensions.append(CLASSIFICATION_EXTENSION_HREF)
    collection.stac_extensions = list(set(collection.stac_extensions))
    collection.stac_extensions.sort()
    item_assets = ItemAssetsExtension.ext(collection, add_if_missing=True)
    item_assets.item_assets = item_assets_dict

    if "sci:publications" in fragment:
        ScientificExtension.add_to(collection)
        # We don't use the scientific extension to set the publications because
        # we don't want duplicate cite-as links.
        collection.extra_fields["sci:publications"] = fragment[
            "sci:publications"]

    return collection


def create_item(href: str,
                cog_directory: Optional[str] = None,
                create_cogs: bool = False,
                read_href_modifier: Optional[ReadHrefModifier] = None,
                antimeridian_strategy: Strategy = Strategy.SPLIT) -> Item:
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
        antimeridian_strategy (AntimeridianStrategy): Either split on -180 or
            normalize geometries so all longitudes are either positive or negative.

    Returns:
        pystac.Item: A STAC Item representing this MODIS image.
    """
    file = File(href)
    metadata = Metadata(file.xml_href, read_href_modifier)
    fragments = file.product.fragments(metadata.version)
    properties = fragments.item()
    properties["start_datetime"] = pystac.utils.datetime_to_str(
        metadata.start_datetime)
    properties["end_datetime"] = pystac.utils.datetime_to_str(
        metadata.end_datetime)
    properties["modis:horizontal-tile"] = metadata.horizontal_tile
    properties["modis:vertical-tile"] = metadata.vertical_tile
    properties["modis:tile-id"] = metadata.tile_id
    item = pystac.Item(id=metadata.id,
                       geometry=metadata.geometry,
                       bbox=metadata.bbox,
                       datetime=metadata.datetime,
                       properties=properties)
    stactools.core.utils.antimeridian.fix_item(item, antimeridian_strategy)

    item.common_metadata.instruments = metadata.instruments
    item.common_metadata.platform = metadata.platform
    item.common_metadata.created = metadata.created
    item.common_metadata.updated = metadata.updated

    if metadata.qa_percent_not_produced_cloud:
        eo = EOExtension.ext(item, add_if_missing=True)
        eo.cloud_cover = metadata.qa_percent_not_produced_cloud

    properties = HDF_ASSET_PROPERTIES.copy()
    properties["href"] = file.hdf_href
    item.add_asset(HDF_ASSET_KEY, Asset.from_dict(properties))

    properties = METADATA_ASSET_PROPERTIES.copy()
    properties["href"] = file.xml_href
    item.add_asset(METADATA_ASSET_KEY, Asset.from_dict(properties))

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
        if metadata.qa_percent_cloud_cover:
            EOExtension.add_to(item)
        for name, cloud_cover in metadata.qa_percent_cloud_cover.items():
            asset = item.assets[name]
            asset.extra_fields["eo:cloud_cover"] = cloud_cover

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
