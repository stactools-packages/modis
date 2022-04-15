import logging
import os
from collections import defaultdict
from typing import List

import click
from click import Command, Group
from pystac import Catalog, CatalogType, Item, Summaries

from stactools.modis import cog, stac
from stactools.modis.builder import ModisBuilder

logger = logging.getLogger(__name__)


def create_modis_command(cli: Group) -> Command:
    """Creates a command group for commands working with MODIS."""

    @cli.group("modis", short_help=("Commands for working with MODIS."))
    def modis() -> None:
        pass

    @modis.command(
        "create-catalog",
        short_help="Creates a STAC Catalog with contents "
        "defined by urls in the INFILE",
    )
    @click.argument("INFILE")
    @click.argument("OUTDIR")
    @click.option("-i", "--id", help="The ID of the output catalog", default="modis")
    @click.option(
        "-t", "--title", help="The title of the output catalog", default="MODIS"
    )
    @click.option(
        "-d",
        "--description",
        help="The description of the output catalog",
        default="MODIS STAC Catalog containing a subset of MODIS assets",
    )
    @click.option(
        "--create-cogs/--no-create-cogs",
        help="Create COGs for each file",
        default=False,
    )
    def create_collection_command(
        infile: str,
        outdir: str,
        id: str,
        title: str,
        description: str,
        create_cogs: bool,
    ) -> None:
        """Creates a STAC Catalog with collections and items defined by the URLs in INFILE.

        \b
        Args:
            infile (str): The input file. Should contain one href per line. The
                hrefs can be to the .hdf files, .hdf.xml files, or to tiffs. Any
                tiffs listed on the same line, separated by commas, will be
                added to the same item.
            outdir (str): The output directory that will contain the catalog.
            id (str): The ID of the output catalog.
            title (str): The title of the output catalog.
            description (str): The description of the output catalog.
            create_cogs (str): Create cogs for all source HDF files?
        """
        with open(infile) as f:
            hrefs = [os.path.abspath(line.strip()) for line in f.readlines()]
        item_dict: defaultdict[str, defaultdict[str, List[Item]]] = defaultdict(
            lambda: defaultdict(list)
        )
        collection_id_set = set()
        for href in hrefs:
            builder = ModisBuilder(skip_creating_cogs_if_missing_hdf=True)
            sub_hrefs = href.split(",")
            for href in sub_hrefs:
                indir = os.path.dirname(href)
                if os.path.splitext(href)[1].lower() == ".tif":
                    builder.add_cog_href(href)
                else:
                    builder.add_hdf_or_xml_href(
                        href,
                        cog_directory=indir,
                        create_cogs=create_cogs,
                    )
            item = builder.create_item()
            metadata = builder.metadata
            item.set_self_href(os.path.join(indir, f"{metadata.id}.json"))
            item_dict[metadata.version][metadata.collection].append(item)
            collection_id_set.add(metadata.collection)
        collection_ids = list(collection_id_set)
        collection_ids.sort()
        catalog = Catalog(
            id=id,
            description=description,
            title=title,
            catalog_type=CatalogType.SELF_CONTAINED,
        )
        for version, collections in item_dict.items():
            version_catalog = Catalog(
                id=f"{id}-{version}",
                description=f"{description}, version {version}",
                title=f"{title}, version {version}",
                catalog_type=CatalogType.SELF_CONTAINED,
            )
            for collection_id in collection_ids:
                if collection_id not in collections:
                    continue
                items = collections[collection_id]
                collection = stac.create_collection(items[0].id.split(".")[0], version)
                platform_set = set()
                for item in items:
                    item.set_self_href(None)
                    collection.add_item(item)
                    for platform in item.common_metadata.platform.split(","):
                        platform_set.add(platform)
                platforms = list(platform_set)
                platforms.sort()
                collection.summaries.update(Summaries({"platform": platforms}))
                version_catalog.add_child(collection)
            catalog.add_child(version_catalog)
        catalog.normalize_hrefs(outdir)
        catalog.validate_all()
        catalog.make_all_asset_hrefs_relative()
        catalog.save()

    @modis.command(
        "create-item", short_help="Create a STAC Item from a MODIS metadata file"
    )
    @click.argument("INFILES", nargs=-1)
    @click.argument("OUTDIR")
    @click.option(
        "-c",
        "--create-cogs",
        is_flag=True,
        help="Convert any hdfs into COGs.",
        default=False,
    )
    @click.option(
        "--validate/--no-validate",
        help="Validate the item before saving",
        default=True,
    )
    def create_item_command(
        infiles: str, outdir: str, create_cogs: bool, validate: bool
    ) -> None:
        """Creates a STAC Item.

        \b
        Args:
            infiles (str): The source file(s). This can be one hdf file, one xml file,
                or multiple tif files.
            outdir (str): Directory that will contain the STAC Item.
            create_cogs (bool, optional): Create COGs in the output directory
                from any .hdf files, one per subdataset.
        """
        builder = ModisBuilder()
        for infile in infiles:
            builder.add_href(infile, cog_directory=outdir, create_cogs=create_cogs)
        item = builder.create_item()
        item_path = os.path.join(outdir, "{}.json".format(item.id))
        item.set_self_href(item_path)
        if validate:
            item.validate()
        item.save_object()

    @modis.command("cogify")
    @click.argument("INFILE")
    @click.argument("OUTDIR")
    def cogify_command(infile: str, outdir: str) -> None:
        """Converts a MODIS HDF file into one or more cloud optimized GeoTIFFs (COGs).

        \b
        Args:
            infile (str): The source .hdf file.
            outdir (str): The directory that will contain the COGs.
        """
        cog.cogify(infile, outdir)

    return modis
