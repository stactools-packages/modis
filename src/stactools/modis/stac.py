import pystac
from pystac import Collection, Item, MediaType
from pystac.extensions.eo import Band, EOExtension
from pystac.extensions.item_assets import AssetDefinition, ItemAssetsExtension

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


def create_item(infile: str) -> Item:
    """Creates a STAC Item from MODIS data.

    Args:
        infile (str): The href to an HDF file or its metadata.

    Returns:
        pystac.Item: A STAC Item representing this MODIS image.
    """
    file = File(infile)
    metadata = Metadata(file.xml_path)
    item = pystac.Item(
        id=metadata.id,
        geometry=metadata.geometry,
        bbox=metadata.bbox,
        datetime=metadata.datetime,
        properties=stactools.modis.fragment.load_item_properties(
            metadata.product, metadata.version))

    item.common_metadata.instruments = metadata.instruments
    item.common_metadata.platform = metadata.platform

    # Hdf
    item.add_asset(
        HDF_ASSET,
        pystac.Asset(href=file.hdf_path,
                     media_type=MediaType.HDF,
                     roles=["data"],
                     title="hdf data"))

    # Metadata
    item.add_asset(
        METADATA_ASSET,
        pystac.Asset(href=file.xml_path,
                     media_type=MediaType.XML,
                     roles=["metadata"],
                     title="FGDC Metdata"))

    # Bands
    eo = EOExtension.ext(item.assets[HDF_ASSET], add_if_missing=True)
    eo.bands = [
        Band(band) for band in stactools.modis.fragment.load_bands(
            metadata.product, metadata.version)
    ]

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
