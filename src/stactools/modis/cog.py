import logging
import os
from typing import List, Optional, Tuple

import stactools.core.utils.convert
from pystac import Asset, Item, MediaType

import stactools.modis.utils
from stactools.modis.constants import HDF_ASSET_KEY
from stactools.modis.file import File

logger = logging.getLogger(__name__)


def add_cogs(item: Item,
             directory: str,
             create: Optional[bool] = False) -> None:
    """Add the COGs in the directory to the provided item.

    Args:
        item (pystac.Item): MODIS Item
        directory (str): The directory holding the COGs.
        create (bool, optional): Set to true to create the cogs in the provided
            directory. Defaults to false.
    """
    hdf_asset = item.assets.get(HDF_ASSET_KEY, None)
    if hdf_asset is None:
        raise ValueError(f"No HDF asset found on item: {item.id}")
    hdf_href = hdf_asset.href
    file = File(hdf_href)
    if create:
        (paths, subdataset_names) = cogify(file.hdf_href, directory)
    else:
        paths = [
            os.path.join(directory, file_name)
            for file_name in os.listdir(directory)
            if os.path.splitext(file_name)[1] == ".tif"
        ]
        if not paths:
            raise ValueError("COG directory does not contain any cogs, "
                             f"and create=False: {directory}")
        subdataset_names = [
            "_".join(os.path.basename(path).split(".")[-2].split("_")[1:])
            for path in paths
        ]
    band_list = file.fragments.bands()
    bands = dict((band["name"], band) for band in band_list)
    for path, subdataset_name in zip(paths, subdataset_names):
        if subdataset_name not in bands:
            raise ValueError(
                f"Invalid MODIS COG file name (subdataset={subdataset_name} "
                f"name at end of file name): {os.path.basename(path)}")
        asset = Asset(
            href=path,
            title=bands[subdataset_name]["name"],
            description=bands[subdataset_name]["description"],
            media_type=MediaType.COG,
            roles=["data"],
        )
        item.add_asset(subdataset_name, asset)


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
    subdatasets = stactools.modis.utils.subdatasets(infile)
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
