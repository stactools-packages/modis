import datetime
import os
from typing import Dict, List, Optional, cast

import pystac.utils
from pystac import Asset, Item, MediaType
from pystac.extensions.eo import Band
from pystac.extensions.raster import RasterBand
from stactools.core.io import ReadHrefModifier
from stactools.core.utils.antimeridian import Strategy

import stactools.modis
from stactools.builder import AssetInfo, ItemInfo, Object, RasterioBuilder
from stactools.modis.fragments import Fragments
from stactools.modis.metadata import Metadata

HDF_ASSET_KEY = "hdf"
HDF_ASSET_TITLE = "Source data containing all bands"
XML_ASSET_KEY = "metadata"
XML_ASSET_TITLE = "Federal Geographic Data Committee (FGDC) Metadata"


class ModisBuilder(RasterioBuilder):

    metadata: Optional[Metadata]
    """The data read from an XML metadata file."""

    def __init__(
        self,
        read_href_modifier: Optional[ReadHrefModifier] = None,
        antimeridian_strategy: Strategy = Strategy.SPLIT,
    ):
        """Creates a new modis builder."""
        super().__init__(
            read_href_modifier=read_href_modifier,
            antimeridian_strategy=antimeridian_strategy,
        )
        self.metadata = None

    def add_hdf_or_xml_href(
        self, href: str, cog_directory: Optional[str] = None, create_cogs: bool = False
    ) -> None:
        """Adds two assets, the XML metadata file and HDF data file.

        Either href can be provided.

        Args:
            href (str): The XML or HDF href.
            cog_directory (optional, str): The optional directory that does (or will) hold the COGs.
            create_cogs (optional, str): Should COGs be created from the HDF file?
        """
        basename, ext = os.path.splitext(href)
        if ext == ".xml":
            hdf_href = basename
            if os.path.splitext(hdf_href)[1] != ".hdf":
                raise ValueError(f"HREF does not end in .hdf.xml as expected: {href}")
            xml_href = href
        elif ext == ".hdf":
            hdf_href = href
            xml_href = f"{href}.xml"
        else:
            raise ValueError(f"Invalid HDF or XML href: {href}")
        self.add_xml_asset(xml_href)
        self.add_hdf_asset(
            hdf_href, cog_directory=cog_directory, create_cogs=create_cogs
        )

    def add_hdf_asset(
        self, href: str, cog_directory: Optional[str] = None, create_cogs: bool = False
    ) -> None:
        """Adds an HDF asset by href.

        The asset key is defined by HDF_ASSET_KEY.

        Args:
            href (str): The HDF href.
            cog_directory (optional, str): The optional directory that does (or will) hold the COGs.
            create_cogs (optional, str): Should COGs be created from the HDF file?
        """
        assert os.path.splitext(href)[1] == ".hdf"
        asset = Asset(
            href=href,
            media_type=MediaType.HDF,
            roles=["data"],
            title=HDF_ASSET_TITLE,
        )
        self.add_asset(HDF_ASSET_KEY, asset)

        if create_cogs:
            if not os.path.exists(asset.href):
                raise ValueError(
                    f"Cannot create COGs without a local HDF asset: {asset.href}"
                )
            if not cog_directory:
                cog_directory = os.getcwd()
            paths, names = stactools.modis.cogify(asset.href, cog_directory)
        elif cog_directory:
            id = self.id({})
            paths = []
            for file_name in os.listdir(cog_directory):
                basename, ext = os.path.splitext(file_name)
                if basename.startswith(id) and ext == ".tif":
                    paths.append(os.path.join(cog_directory, file_name))
            if not paths:
                return
            names = [
                "_".join(os.path.basename(path).split(".")[-2].split("_")[1:])
                for path in paths
            ]
        else:
            return

        bands = self.bands()
        for path, name in zip(paths, names):
            band = bands[name]
            roles = ["data"]
            extra_roles = band.get("roles")
            if extra_roles:
                roles.extend(extra_roles)

            self.add_rasterio_asset(
                name,
                Asset(
                    href=path,
                    title=band.get("title"),
                    description=band.get("description"),
                    media_type=MediaType.COG,
                    roles=roles,
                ),
            )

    def add_xml_asset(self, href: str) -> None:
        """Adds an XML asset by href.

        The asset key is defined by XML_ASSET_KEY.

        Args:
            href (str): The XML href.
        """
        assert os.path.splitext(href)[1] == ".xml"
        asset = Asset(
            href=href,
            media_type=MediaType.XML,
            roles=["metadata"],
            title=XML_ASSET_TITLE,
        )
        self.add_asset(XML_ASSET_KEY, asset)
        self.metadata = Metadata.from_xml_href(href, self.read_href_modifier)

    def create_item(self, id: Optional[str] = None) -> Item:
        if not self.metadata:
            raise ValueError(
                "Cannot create item without metadata -- "
                "add an XML file or a COG to read the metadata."
            )
        return super().create_item(id)

    def item_info(self, id: Optional[str] = None) -> ItemInfo:
        """Creates a MODIS item."""
        assert self.metadata
        item_info = super().item_info(id)
        if self.metadata.qa_percent_not_produced_cloud:
            item_info.eo = {"cloud_cover": self.metadata.qa_percent_not_produced_cloud}
        return item_info

    def asset_info(self, key: str) -> Optional[AssetInfo]:
        assert self.metadata
        asset_info = super().asset_info(key)
        if asset_info is None:
            return None

        if self.metadata and self.metadata.qa_percent_cloud_cover:
            asset_info.eo = {"cloud_cover": self.metadata.qa_percent_cloud_cover[key]}

        band = self.bands().get(key)
        if band is None:
            return None

        raster_bands = band.get("raster:bands")
        if raster_bands:
            asset_info.raster = {
                "bands": [RasterBand.create(**band) for band in raster_bands]
            }

        eo_bands = band.get("eo:bands")
        if eo_bands:
            asset_info.eo = {"bands": [Band.create(**band) for band in eo_bands]}

        classification_classes = band.get("classification:classes")
        if classification_classes:
            asset_info.classification = {
                "classification:classes": classification_classes
            }

        return asset_info

    def id(self, asset_infos: Dict[str, AssetInfo]) -> str:
        """Returns the id as determined from the metadata asset."""
        assert self.metadata
        return self.metadata.id

    def datetime(
        self, asset_infos: Dict[str, AssetInfo]
    ) -> Optional[datetime.datetime]:
        """Returns the datetime as determined from the metadata file."""
        assert self.metadata
        return self.metadata.datetime

    def properties(self, asset_infos: Dict[str, AssetInfo]) -> Object:
        """Returns extra properties for the item, as set from fragments."""
        assert self.metadata
        fragments = self.fragments()
        properties = fragments.item()
        properties["start_datetime"] = pystac.utils.datetime_to_str(
            self.metadata.start_datetime
        )
        properties["end_datetime"] = pystac.utils.datetime_to_str(
            self.metadata.end_datetime
        )
        properties["instruments"] = self.metadata.instruments
        # Per the discussion in
        # https://github.com/radiantearth/stac-spec/issues/216, it seems like
        # the recommendation for multi-platform datasets is to just include both
        # and use a string separator.
        properties["platform"] = ",".join(self.metadata.platforms)
        properties["created"] = pystac.utils.datetime_to_str(self.metadata.created)
        properties["updated"] = pystac.utils.datetime_to_str(self.metadata.updated)
        properties["modis:horizontal-tile"] = self.metadata.horizontal_tile
        properties["modis:vertical-tile"] = self.metadata.vertical_tile
        properties["modis:tile-id"] = self.metadata.tile_id
        return cast(Object, properties)

    def geometry(self, geometries: List[Object]) -> Optional[Object]:
        assert self.metadata
        return self.metadata.geometry

    def bbox(self, geometry: Object) -> List[float]:
        assert self.metadata
        return self.metadata.bbox

    def fragments(self) -> Fragments:
        return Fragments(self.collection(), self.version())

    def bands(self) -> Object:
        return cast(Object, self.fragments().bands())

    def collection(self) -> str:
        assert self.metadata
        return self.metadata.collection

    def version(self) -> str:
        assert self.metadata
        return self.metadata.version
