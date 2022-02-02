import stactools.core
from stactools.cli.registry import Registry

from stactools.modis.cog import create_cogs
from stactools.modis.stac import create_item

stactools.core.use_fsspec()


def register_plugin(registry: Registry) -> None:
    from stactools.modis import commands
    registry.register_subcommand(commands.create_modis_command)


__version__ = "0.1.3"
"""Library version"""

__all__ = ["create_item", "create_cogs"]
