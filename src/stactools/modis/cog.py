import logging
import os
from typing import List, Optional, Tuple

import rasterio
import stactools.core.utils.convert
from pystac import Asset, Item, MediaType
from rasterio.errors import NotGeoreferencedWarning

import stactools.modis.fragment
from stactools.modis.constants import HDF_ASSET
from stactools.modis.file import File

logger = logging.getLogger(__name__)


def add_cogs(item: Item, outdir: Optional[str] = None) -> List[str]:
    """Create COGs from the HDF asset contained in the passed in STAC item.

    The COGs will be added as assets to the item.

    Args:
        item (pystac.Item): MODIS Item
        cog_directory (str, optional): An option HREF to hold the COGs. If not
            provided, the COGs will be created alongside the item.

    Returns:
        List[str]: A list of hrefs to the created COGs.
    """
    hdf_asset = item.assets.get(HDF_ASSET, None)
    if hdf_asset is None:
        raise ValueError(f"No HDF asset found on item: {item.id}")
    hdf_href = hdf_asset.href
    file = File(hdf_href)
    if outdir is None:
        item_href = item.get_self_href()
        if item_href is None:
            raise ValueError(
                f"No outdir provided and no self href on item: {item.id}")
        else:
            outdir = os.path.dirname(item_href)
    paths, subdataset_names = cogify(hdf_href, outdir)
    band_list = stactools.modis.fragment.load_bands(file.product, file.version)
    bands = dict((band["name"], band) for band in band_list)
    for path, subdataset_name in zip(paths, subdataset_names):
        item.add_asset(
            subdataset_name,
            Asset(
                href=path,
                title=bands[subdataset_name]["name"],
                description=bands[subdataset_name]["description"],
                media_type=MediaType.COG,
                roles=["data"],
            ))
    return paths


def cogify(infile: str, outdir: str) -> Tuple[List[str], List[str]]:
    """Creates cogs for the provided HDF file.

    Args:
        infile (str): The input HDF file
        outdir (str): The output directory

    Returns:
        Tuple[List[str], List[str]]: A two tuple (paths, names):
            - The first element is a list of the output tif paths
            - The second element is a list of subdataset names
    """
    with rasterio.open(infile) as dataset:
        subdatasets = dataset.subdatasets
    base_file_name = os.path.splitext(os.path.basename(infile))[0]
    paths = []
    subdataset_names = []
    for subdataset in subdatasets:
        parts = subdataset.split(":")
        subdataset_name = parts[-1]
        subdataset_names.append(subdataset_name)
        file_name = f"{base_file_name}_{subdataset_name}.tif"
        outfile = os.path.join(outdir, file_name)
        stactools.core.utils.convert.cogify(subdataset, outfile)
        paths.append(outfile)
    return (paths, subdataset_names)
