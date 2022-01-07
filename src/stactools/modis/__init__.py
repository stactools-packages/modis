# flake8: noqa

from stactools.modis.stac import create_item
from stactools.modis.cog import create_cogs

import stactools.core
from stactools.cli.registry import Registry

stactools.core.use_fsspec()


def register_plugin(registry: Registry) -> None:
    # Register subcommands

    from stactools.modis import commands

    registry.register_subcommand(commands.create_modis_command)


__version__ = '0.1.3'
"""Library version"""

__all__ = ['create_item', 'create_cogs']
