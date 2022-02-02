import logging
import os

import click
from click import Group, Command

from stactools.modis import stac, cog

logger = logging.getLogger(__name__)


def create_modis_command(cli: Group) -> Command:
    """Creates a command group for commands working with MODIS."""

    @cli.group("modis", short_help=("Commands for working with MODIS."))
    def modis() -> None:
        pass

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

        Args:
            infile (str): The source metadata xml file.
            outdir (str): Directory that will contain the STAC Item.
            cogify (bool, optional): Convert the .hdf file into multiple
                Cloud-Optimized GeoTIFFs, one per layer. The .hdf file is
                expected to reside alongside the metadata xml file.
        """
        item = stac.create_item(infile)
        item_path = os.path.join(outdir, '{}.json'.format(item.id))
        item.set_self_href(item_path)
        if cogify:
            cog.create_cogs(item)
        item.validate()
        item.save_object()

    @modis.command("cogify")
    @click.argument("INFILE")
    @click.argument("OUTDIR")
    def cogify_command(infile: str, outdir: str) -> None:
        """Converts a MODIS HDF file into one or more cloud optimized GeoTIFFs (COGs).

        Args:
            infile (str): The source .hdf file. 
            outdir (str): The directory that will contain the COGs.
        """
        cog.cogify(infile, outdir)

    return modis
