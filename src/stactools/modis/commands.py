import logging
import os
from collections import defaultdict

import click
from click import Command, Group
from pystac import Catalog, CatalogType

from stactools.modis import cog, stac
from stactools.modis.file import File

logger = logging.getLogger(__name__)


def create_modis_command(cli: Group) -> Command:
    """Creates a command group for commands working with MODIS."""

    @cli.group("modis", short_help=("Commands for working with MODIS."))
    def modis() -> None:
        pass

    @modis.command("create-catalog",
                   short_help="Creates a STAC Catalog with contents "
                   "defined by urls in the INFILE")
    @click.argument("INFILE")
    @click.argument("OUTDIR")
    @click.option("-i",
                  "--id",
                  help="The ID of the output catalog",
                  default="modis")
    @click.option("-t",
                  "--title",
                  help="The title of the output catalog",
                  default="MODIS")
    @click.option(
        "-d",
        "--description",
        help="The description of the output catalog",
        default="MODIS STAC Catalog containg a subset of MODIS assets")
    def create_collection_command(
        infile: str,
        outdir: str,
        id: str,
        title: str,
        description: str,
    ) -> None:
        """Creates a STAC Catalog with collections and items defined by the URLs in INFILE.

        If there are COGs alongside, they will be added.

        \b
        Args:
            infile (str): The input file. Should contain one href per line. The
                hrefs can be to the .hdf files or .hdf.xml files
            outdir (str): The output directory that will contain the catalog.
            id (str): The ID of the output catalog.
            title (str): The title of the output catalog.
            description (str): The description of the output catalog.
        """
        with open(infile) as file:
            hrefs = [line.strip() for line in file.readlines()]
        items = defaultdict(list)
        versions = set()
        for href in hrefs:
            modis_file = File(href)
            prefix = os.path.splitext(os.path.basename(modis_file.hdf_href))[0]
            directory = os.path.dirname(modis_file.hdf_href)
            has_tiffs = any(
                os.path.splitext(file_name)[1] == ".tif"
                and file_name.startswith(prefix)
                for file_name in os.listdir(directory))
            if has_tiffs:
                cog_directory = directory
            else:
                cog_directory = None
            item = stac.create_item(href, cog_directory=cog_directory)
            items[(modis_file.product, modis_file.version)].append(item)
            versions.add(modis_file.version)
        catalog = Catalog(id=id,
                          description=description,
                          title=title,
                          catalog_type=CatalogType.SELF_CONTAINED)
        catalog.set_self_href(os.path.join(outdir, "catalog.json"))
        catalogs = dict()
        for version in versions:
            version_catalog = Catalog(
                id=f"{id}-{version}",
                description=f"{description}, version {version}",
                title=f"{title}, version {version}",
                catalog_type=CatalogType.SELF_CONTAINED)
            catalog.add_child(version_catalog)
            catalogs[version] = version_catalog
        for (product, version), collection_items in items.items():
            version_catalog = catalogs[version]
            collection = stac.create_collection(product, version)
            version_catalog.add_child(collection)
            collection.add_items(collection_items)
        catalog.validate_all()
        catalog.make_all_asset_hrefs_relative()
        catalog.save()

    @modis.command("create-item",
                   short_help="Create a STAC Item from a MODIS metadata file")
    @click.argument("INFILE")
    @click.argument("OUTDIR")
    @click.option("-c",
                  "--cogify",
                  is_flag=True,
                  help="Convert the hdf into COGs.",
                  default=False)
    def create_item_command(infile: str, outdir: str, cogify: bool) -> None:
        """Creates a STAC Item based on metadata from an .hdf.xml MODIS file.

        \b
        Args:
            infile (str): The source metadata xml file.
            outdir (str): Directory that will contain the STAC Item.
            cogify (bool, optional): Convert the .hdf file into multiple
                Cloud-Optimized GeoTIFFs, one per layer. The .hdf file is
                expected to reside alongside the metadata xml file.
        """
        item = stac.create_item(infile)
        item_path = os.path.join(outdir, "{}.json".format(item.id))
        item.set_self_href(item_path)
        if cogify:
            cog.add_cogs(item, outdir, create=True)
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
