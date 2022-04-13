import logging
import os
import warnings
from typing import List, Optional, Tuple

import stactools.core.utils.convert
from pystac import Asset, Item, MediaType
from pystac.extensions.eo import Band, EOExtension
from pystac.extensions.raster import RasterBand, RasterExtension

import stactools.modis.utils
from stactools.modis.constants import CLASSIFICATION_EXTENSION_HREF
from stactools.modis.file import File

logger = logging.getLogger(__name__)


def add_cogs(
    item: Item, directory: str, create: bool = False
) -> Tuple[List[str], List[str]]:
    """Add the COGs in the directory to the provided item.

    Args:
        item (pystac.Item): MODIS Item
        directory (str): The directory holding the COGs.
        create (bool, optional): Set to true to create the cogs in the provided
            directory. Defaults to false.

    Returns:
        List[str]: The COG hrefs
    """
    warnings.warn(
        "stactools.modis.cog.add_cogs will be removed in v0.4.0, "
        "use stactools.modis.cogify and stactools.modis.Builder instead",
        DeprecationWarning,
    )
    file = File.from_item(item)
    if create:
        (paths, subdataset_names) = cogify(file.hdf_href, directory)
    else:
        paths = []
        for file_name in os.listdir(directory):
            basename, ext = os.path.splitext(file_name)
            if basename.startswith(os.path.splitext(item.id)) and ext == ".tif":
                paths.append(os.path.join(directory, file_name))
        if not paths:
            raise ValueError(
                "COG directory does not contain any cogs, "
                f"and create=False: {directory}"
            )
        subdataset_names = None
    subdataset_names = add_cog_assets(item, paths, subdataset_names)
    return (paths, subdataset_names)


def add_cog_assets(
    item: Item, hrefs: List[str], subdataset_names: Optional[List[str]] = None
) -> List[str]:
    """Adds COG assets to an item.

    The assets must already exist at hrefs. If `subdataset_names` is not
    provided, it will be deduced from the file names.

    Args:
        item (pystac.Item): The item which will get COG assets.
        hrefs (List[str]): A list of COG hrefs.
        subdataset_names (Optional[List[str]]): A list of subdataset names that
            map 1-to-1 with the hrefs. Produced by `cogify`.

    Returns:
        List[str]: The list of subdataset names, in case they were intuited from
            the hrefs.
    """
    warnings.warn(
        "stactools.modis.cog.add_cogs_assets will be removed in v0.4.0, "
        "use stactools.modis.cogify and stactools.modis.Builder instead",
        DeprecationWarning,
    )
    if not subdataset_names:
        subdataset_names = [
            "_".join(os.path.basename(href).split(".")[-2].split("_")[1:])
            for href in hrefs
        ]
    file = File.from_item(item)
    fragments = file.fragments()
    bands = fragments.bands()
    for path, subdataset_name in zip(hrefs, subdataset_names):
        if subdataset_name not in bands:
            raise ValueError(
                f"Invalid MODIS COG file name (subdataset={subdataset_name} "
                f"name at end of file name): {os.path.basename(path)}"
            )
        band = bands[subdataset_name]
        asset = Asset(
            href=path,
            title=band["title"],
            description=band.get("description"),
            media_type=MediaType.COG,
            roles=["data"],
        )
        item.add_asset(subdataset_name, asset)

        asset = item.assets[subdataset_name]

        raster_bands = band.get("raster:bands")
        if raster_bands:
            raster = RasterExtension.ext(asset, add_if_missing=True)
            raster.bands = [
                RasterBand.create(**raster_band) for raster_band in raster_bands
            ]
        eo_bands = band.get("eo:bands")
        if eo_bands:
            eo = EOExtension.ext(asset, add_if_missing=True)
            eo.bands = [Band.create(**eo_band) for eo_band in eo_bands]
        classification_classes = band.get("classification:classes")
        if classification_classes:
            if CLASSIFICATION_EXTENSION_HREF not in item.stac_extensions:
                item.stac_extensions.append(CLASSIFICATION_EXTENSION_HREF)
            asset.extra_fields["classification:classes"] = classification_classes

        roles = band.get("roles")
        if roles:
            asset.roles.extend(roles)

    return subdataset_names


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
        sanitized_subdataset_name = subdataset_name.replace(" ", "_")
        subdataset_names.append(sanitized_subdataset_name)
        file_name = f"{base_file_name}_{sanitized_subdataset_name}.tif"
        outfile = os.path.join(outdir, file_name)
        stactools.core.utils.convert.cogify(subdataset, outfile)
        paths.append(outfile)
    return (paths, subdataset_names)
