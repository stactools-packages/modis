import os.path
import urllib.parse
from typing import Optional

import pystac
import rasterio
import shapely.geometry
import stactools.core.utils
from pystac import Collection, Item, MediaType
from pystac.extensions.eo import Band, EOExtension
from pystac.extensions.item_assets import AssetDefinition, ItemAssetsExtension
from pystac.extensions.projection import ProjectionExtension
from stactools.core.io import ReadHrefModifier

import stactools.modis.fragment
from stactools.modis.constants import HDF_ASSET, METADATA_ASSET
from stactools.modis.file import File
from stactools.modis.metadata import Metadata


def create_collection(product: str, version: str) -> Collection:
    """Creates a STAC Collection for MODIS data.

    Args:
        product (str): The ID of a MODIS product, e.g. "MCD12Q1"
        version (str): The MODIS version, e.g. "006" or "061"

    Returns:
        Collection: The created collection.
    """
    fragment = stactools.modis.fragment.load_collection(product, version)
    collection = pystac.Collection(
        id=collection_id(product, version),
        description=fragment["description"],
        extent=fragment["extent"],
        title=fragment["title"],
        providers=fragment["providers"],
    )
    collection.add_links(fragment["links"])

    item_assets = ItemAssetsExtension.ext(collection, add_if_missing=True)
    item_assets.item_assets = {
        "image":
        AssetDefinition({
            "eo:bands":
            stactools.modis.fragment.load_bands(product, version),
            "roles": ["data"],
            "title":
            "RGBIR COG tile",
            "type":
            MediaType.COG,
        })
    }

    return collection


def create_item(href: str,
                read_href_modifier: Optional[ReadHrefModifier] = None) -> Item:
    """Creates a STAC Item from MODIS data.

    Args:
        href (str): The href to an HDF file or its metadata.
        read_href_modifier (Callable[[str], str]): An optional function to
            modify the href (e.g. to add a token to a url)

    Returns:
        pystac.Item: A STAC Item representing this MODIS image.
    """
    file = File(href)
    metadata = Metadata(file.xml_href, read_href_modifier)
    item = pystac.Item(
        id=metadata.id,
        geometry=metadata.geometry,
        bbox=metadata.bbox,
        datetime=metadata.datetime,
        properties=stactools.modis.fragment.load_item_properties(
            metadata.product, metadata.version))

    item.common_metadata.instruments = metadata.instruments
    item.common_metadata.platform = metadata.platform
    item.common_metadata.created = metadata.created
    item.common_metadata.updated = metadata.updated
    item.add_asset(
        HDF_ASSET,
        pystac.Asset(href=file.hdf_href,
                     media_type=MediaType.HDF,
                     roles=["data"],
                     title="hdf data"))
    item.add_asset(
        METADATA_ASSET,
        pystac.Asset(href=file.xml_href,
                     media_type=MediaType.XML,
                     roles=["metadata"],
                     title="FGDC Metdata"))

    eo = EOExtension.ext(item.assets[HDF_ASSET], add_if_missing=True)
    eo.bands = [
        Band(band) for band in stactools.modis.fragment.load_bands(
            metadata.product, metadata.version)
    ]

    url = urllib.parse.urlparse(file.hdf_href)
    if not url.scheme and os.path.isfile(file.hdf_href):
        with rasterio.open(file.hdf_href) as dataset:
            subdatasets = dataset.subdatasets
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
