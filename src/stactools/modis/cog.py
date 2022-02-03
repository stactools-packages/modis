import logging
import os
from typing import List, Optional

import rasterio
import stactools.core.utils.convert
from pystac import Item

logger = logging.getLogger(__name__)


def create_cogs(item: Item, cog_directory: Optional[str] = None) -> None:
    """Create COGs from the HDF asset contained in the passed in STAC item.

    Args:
        item (pystac.Item): MODIS Item that contains an asset
            with key equal to stactools.modis.constants.ITEM_METADATA_NAME,
            which will be converted to COGs.
        cog_directory (str, optional): A URI of a directory to store COGs. This will be used
            in conjunction with the file names based on the COG asset to store
            the COG data. If not supplied, the directory of the Item"s self HREF
            will be used.

    Returns:
        pystac.Item: The same item, mutated to include assets for the
            new COGs.
    """
    raise NotImplementedError


def cogify(infile: str, outdir: str) -> List[str]:
    """Creates cogs for the provided HDF file.

    Args:
        infile (str): The input HDF file
        outdir (str): The output directory

    Returns:
        List[str]: The paths to the created COGs.
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
