import logging
import os

import click
from click import Group, Command

from stactools.modis import stac, cog

logger = logging.getLogger(__name__)


def create_modis_command(cli: Group) -> Command:
    """Creates a command group for commands working with
    MODIS.
    """

    @cli.group('modis', short_help=("Commands for working with "
                                    "MODIS."))
    def modis() -> None:
        pass

    @modis.command('create-item',
                   short_help='Create a STAC Item from a MODIS metadata file')
    @click.argument('metadata_href')
    @click.argument('dst')
    @click.option('-c',
                  '--cogify',
                  is_flag=True,
                  help='Convert the hdf into COG.')
    def create_item_command(metadata_href: str, dst: str,
                            cogify: bool) -> None:
        """Creates a STAC Item based on metadata from an hdf.xml
        MODIS file.

        METADATA_REF is the modis metadata file. The
        hdf file will be located in the same directory as that of METADATA_REF.
        DST is directory that a STAC Item JSON file will be created
        in. This will have a filename that matches the ID, which will
        is the name of the METADATA_REF, without it's file extension.
        """

        item = stac.create_item(metadata_href)

        item_path = os.path.join(dst, '{}.json'.format(item.id))

        item.set_self_href(item_path)

        if cogify:
            cog.create_cogs(item)

        item.save_object()

    @modis.command("cogify")
    @click.argument("infile")
    @click.argument("outdir")
    def cogify_command(infile: str, outdir: str) -> None:
        """Converts a MODIS HDF file into one or more cloud optimized GeoTIFFs (COGs)."""
        cog.cogify(infile, outdir)

    return modis
