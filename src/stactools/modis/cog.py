import logging
import os
from typing import Optional, List

import pystac
import rasterio
from pystac import Item
import stactools.core.utils.convert

from stactools.modis.constants import (ITEM_COG_IMAGE_NAME,
                                       ITEM_TIF_IMAGE_NAME)

logger = logging.getLogger(__name__)


def _create_cog(item: Item, cog_directory: str) -> str:
    hdf_asset = item.assets.get(ITEM_TIF_IMAGE_NAME)
    assert hdf_asset
    stactools.core.utils.convert.cogify(hdf_asset.href, cog_directory)

    return cog_directory


def create_cogs(item: Item, cog_directory: Optional[str] = None) -> None:
    """Create COGs from the HDF asset contained in the passed in STAC item.

    Args:
        item (pystac.Item): modis Item that contains an asset
            with key equal to stactools.modis.constants.ITEM_METADATA_NAME,
            which will be converted to COGs.
        cog_directory (str): A URI of a directory to store COGs. This will be used
            in conjunction with the file names based on the COG asset to store
            the COG data. If not supplied, the directory of the Item's self HREF
            will be used.

    Returns:
        pystac.Item: The same item, mutated to include assets for the
            new COGs.
    """
    file_name = f"{item.id}-cog.tif"
    if cog_directory:
        cog_href = os.path.join(cog_directory, file_name)
    else:
        item_href = item.get_self_href()
        if not item_href:
            raise ValueError(
                "COG directory not provided, and item has no self href")
        cog_href = os.path.join(item_href, file_name)

    _create_cog(item, cog_href)

    asset = pystac.Asset(href=cog_href,
                         media_type=pystac.MediaType.COG,
                         roles=['data'],
                         title='Raster Dataset')

    item.assets[ITEM_COG_IMAGE_NAME] = asset


def cogify(infile: str, outdir: str) -> List[str]:
    """Creates cogs for the provided HDF file.

    This will create one COG per subdataset in the HDF file.
    """
    with rasterio.open(infile) as dataset:
        subdatasets = dataset.subdatasets
    base_file_name = os.path.splitext(os.path.basename(infile))[0]
    paths = []
    for subdataset in subdatasets:
        parts = subdataset.split(":")
        product = parts[-1]
        file_name = f"{base_file_name}_{product}.tif"
        outfile = os.path.join(outdir, file_name)
        stactools.core.utils.convert.cogify(subdataset, outfile)
        paths.append(outfile)
    return paths
