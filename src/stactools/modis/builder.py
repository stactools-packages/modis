import datetime
import os
import warnings
from typing import Any, Dict, List, Optional, cast

import pystac.utils
import rasterio
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

    cog_tags: Dict[str, Dict[str, str]]
    """TIFF tag information as read from COGs."""

    skip_creating_cogs_if_missing_hdf: bool
    """If the HDF is not locally available but COG creation is requested, should
    we skip creating COGs?
    """

    def __init__(
        self,
        read_href_modifier: Optional[ReadHrefModifier] = None,
        antimeridian_strategy: Strategy = Strategy.SPLIT,
        skip_creating_cogs_if_missing_hdf: bool = False,
    ):
        """Creates a new modis builder.

        Args:
            See `RasterioBuilder` for information about `read_href_modifier` and
            and `antimeridian_strategy`.
            skip_creating_cogs_if_missing_hdf (bool): If the HDF is not locally
                available but COG creation is requested, should we skip creating
                COGs?
        """
        super().__init__(
            read_href_modifier=read_href_modifier,
            antimeridian_strategy=antimeridian_strategy,
        )
        self.metadata = None
        self.cog_tags = {}
        self.skip_creating_cogs_if_missing_hdf = skip_creating_cogs_if_missing_hdf

    def add_href(
        self, href: str, cog_directory: Optional[str] = None, create_cogs: bool = False
    ) -> None:
        """Adds a new asset to this builder by href.

        Can be .xml, .hdf, or .tif.

        Args:
            href (str): The href of the asset to add.
            cog_directory (Optional[str], optional): If .hdf or .xml file, look
                in this directory to find related COGs, or if `create_cogs` is true,
                create cogs here.
            create_cogs (bool, optional): Create COGs from the HDF file, if the
                href is an xml or hdf file. Defaults to false.

        Raises:
            ValueError: If `create_cogs` is true but the hdf file isn't locally
            available.
        """
        ext = os.path.splitext(href)[1].lower()
        if ext == ".tif":
            self.add_cog_href(href)
        elif ext == ".xml" or ext == ".hdf":
            self.add_hdf_or_xml_href(
                href, cog_directory=cog_directory, create_cogs=create_cogs
            )
        else:
            raise ValueError(f"Invalid MODIS href: {href}")

    def add_hdf_or_xml_href(
        self, href: str, cog_directory: Optional[str] = None, create_cogs: bool = False
    ) -> None:
        """Adds two assets, the XML metadata file and HDF data file.

        Either href can be provided.

        Args:
            href (str): The XML or HDF href.
            cog_directory (optional, str): The optional directory that does (or will) hold the COGs.
            create_cogs (optional, str): Should COGs be created from the HDF file?

        Raises:
            ValueError: If `create_cogs` is true but the hdf file isn't locally
            available.
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

        Raises:
            ValueError: If `create_cogs` is true but the hdf file isn't locally
            available.
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
                if self.skip_creating_cogs_if_missing_hdf:
                    warnings.warn(
                        f"Skipping creating COG for {asset.href}, local HDF file does not exist",
                    )
                    return
                else:
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

        for path, name in zip(paths, names):
            self.add_cog_asset_from_href(name, path)

    def add_cog_href(self, href: str) -> None:
        """Adds a COG asset by href.

        The asset key will be the band name of the COG.

        Args:
            href (str): The href of the COG.

        Raises:
            ValueError: If the href doesn't end in .tif.
        """
        ext = os.path.splitext(href)[1]
        if ext.lower() != ".tif":
            raise ValueError(f"Invalid COG file name: {os.path.basename(href)}")
        cog_tags = self.read_cog_tags(href)
        self.add_cog_asset_from_href(self.band_name(cog_tags), href)

    def add_cog_asset_from_href(self, name: str, href: str) -> None:
        """Adds a COG asset with the given asset key and href.

        Args:
            name (str): The band name, which is used as the asset key.
            href (str): The href to the COG asset.
        """
        self.read_cog_tags(href, name=name)
        bands = self.bands()
        band = bands[name]
        roles = ["data"]
        extra_roles = band.get("roles")
        if extra_roles:
            roles.extend(extra_roles)
        self.add_rasterio_asset(
            name,
            Asset(
                href=href,
                title=band.get("title"),
                description=band.get("description"),
                media_type=MediaType.COG,
                roles=roles,
            ),
        )

    def add_xml_asset(self, href: str) -> None:
        """Adds an XML asset by href, and reads it in as the metadata for this
        builder.

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
        """Creates a new pystac Item.

        Args:
            id (Optional[str], optional): The id override. Defaults to None. By
                default the ID will be determined from the metadata.

        Raises:
            ValueError: If there is no metadata available. Metadata is read from
                either xml or COG assets.

        Returns:
            Item: The PySTAC item.
        """
        if not self.metadata:
            raise ValueError(
                "Cannot create item without metadata -- "
                "add an XML file or a COG to read the metadata."
            )
        return super().create_item(id)

    def item_info(self, id: Optional[str] = None) -> ItemInfo:
        """Returns information about the item.

        Args:
            id (Optional[str], optional): The ID override. Defaults to None.

        Returns:
            ItemInfo: Information about the item, including cloud cover data.
        """
        assert self.metadata
        item_info = super().item_info(id)
        if self.metadata.qa_percent_not_produced_cloud:
            item_info.eo = {"cloud_cover": self.metadata.qa_percent_not_produced_cloud}
        return item_info

    def asset_info(self, key: str) -> Optional[AssetInfo]:
        """Returns asset information about the asset at the given key.

        Args:
            key (str): The asset key.

        Returns:
            Optional[AssetInfo]: The asset information, or none if there's no
                information to provide.
        """
        assert self.metadata
        asset_info = super().asset_info(key)
        if asset_info is None:
            return None

        if self.metadata.qa_percent_cloud_cover:
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
        """Returns the id as determined from the metadata."""
        assert self.metadata
        return self.metadata.id

    def datetime(
        self, asset_infos: Dict[str, AssetInfo]
    ) -> Optional[datetime.datetime]:
        """Returns the datetime as determined from the metadata."""
        assert self.metadata
        return self.metadata.datetime

    def properties(self, asset_infos: Dict[str, AssetInfo]) -> Object:
        """Returns extra properties for the item."""
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
        if self.metadata.created:
            properties["created"] = pystac.utils.datetime_to_str(self.metadata.created)
        if self.metadata.updated:
            properties["updated"] = pystac.utils.datetime_to_str(self.metadata.updated)
        properties["modis:horizontal-tile"] = self.metadata.horizontal_tile
        properties["modis:vertical-tile"] = self.metadata.vertical_tile
        properties["modis:tile-id"] = self.metadata.tile_id
        return cast(Object, properties)

    def geometry(self, geometries: List[Object]) -> Optional[Object]:
        """Returns the geometry.

        If there is geometry on the metadata, uses that. If not, uses the
        geometry as determined from the assets by reading them with rasterio.

        Args:
            geometries (List[Object]): The geometries as read from the assets.

        Returns:
            Optional[Object]: The item geometry.
        """
        assert self.metadata
        if self.metadata.geometry:
            return self.metadata.geometry
        else:
            return super().geometry(geometries)

    def bbox(self, geometry: Object) -> List[float]:
        """Returns the bounding box.

        If its available on the metadata, uses that. Otherwise, returns the
        default implementation which is derived from the geometry.
        """
        assert self.metadata
        if self.metadata.bbox:
            return self.metadata.bbox
        else:
            return super().bbox(geometry)

    def fragments(self) -> Fragments:
        """Returns the fragments for this builder.

        Requires metadata to be read (to determine product version and name).

        Returns:
            Fragments: Item and collection fragment generator.
        """
        return Fragments(self.collection(), self.version())

    def bands(self) -> Object:
        """Returns the band fragments for this builder.

        Requires metadata.

        Returns:
            Object: A dictionary of band information.
        """
        return cast(Object, self.fragments().bands())

    def collection(self) -> str:
        """Returns this builder's collection string.

        Requires metadata to be read.

        Returns:
            str: The builder's collection (e.g. "14A2")
        """
        assert self.metadata
        return self.metadata.collection

    def version(self) -> str:
        """Returns this builder's version string.

        Requires metadata to be read.

        Returns:
            str: The builder's version (e.g. "061")
        """
        assert self.metadata
        return self.metadata.version

    def read_cog_tags(self, href: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Reads COG tags from an href.

        If "name" is provided, will attempt to look up already-read tags from
        the tags cache. If "name" is not provided, will be determined from the
        COG tags.

        Sets self.metadata as a side effect.

        Args:
            href (str): The COG href.
            name (Optional[str], optional): The band name for the COG. Defaults
                to None.

        Returns:
            Dict[str, Any]: The COG tags.
        """
        if name and name in self.cog_tags:
            return self.cog_tags[name]
        with rasterio.open(href) as dataset:
            cog_tags = dataset.tags()
        if self.metadata is None:
            self.metadata = Metadata.from_cog_tags(cog_tags)
        if name is None:
            name = self.band_name(cog_tags)
        self.cog_tags[name] = cog_tags
        return cast(Object, cog_tags)

    def band_name(self, cog_tags: Dict[str, str]) -> str:
        """Determines the band name from COG tags.

        Uses the `long_name` COG tag, and then looks up the key by trying to
        find a `band["title"]` in this builder's band fragment. Requires
        metadata to be read.

        Args:
            cog_tags (Dict[str, str]): The tags for this band.

        Returns:
            str: The band name.
        """
        bands = self.bands()
        name = cog_tags["long_name"]
        band = next(
            (
                key
                for key, value in bands.items()
                if value["title"].lower() == name.lower()
            ),
            None,
        )
        if band:
            return band
        else:
            return name.replace(" ", "_")
