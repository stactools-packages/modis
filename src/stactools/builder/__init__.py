import datetime
import hashlib
import os.path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, cast

import fsspec
import multihash
import rasterio
import shapely.geometry
import stactools.core.projection
import stactools.core.utils.antimeridian
import stactools.core.utils.convert
from pystac import Asset, Item, MediaType
from pystac.extensions.eo import AssetEOExtension, EOExtension
from pystac.extensions.file import FileExtension
from pystac.extensions.projection import AssetProjectionExtension, ProjectionExtension
from pystac.extensions.raster import RasterBand, RasterExtension
from rasterio.crs import CRSError
from stactools.core.io import ReadHrefModifier
from stactools.core.utils.antimeridian import Strategy

EPSG = 4326
CLASSIFICATION_EXTENSION_HREF = (
    "https://stac-extensions.github.io/classification/v1.0.0/schema.json"
)
DEFAULT_ANTIMERIDIAN_STRATEGY = Strategy.SPLIT
Object = Dict[str, Any]


@dataclass
class AssetInfo:
    """Information about an asset.

    This is a "light" version of an actual PySTAC asset.
    """

    geometry: Optional[Object]
    """An optional WGS84 geometry for this asset."""

    projection: Optional[Object]
    """Optional projection information that will be used for the projection extension."""

    raster: Optional[Object]
    """Optional raster information that will be used for the raster extension."""

    eo: Optional[Object]
    """Optional information for the eo extension."""

    classification: Optional[Object]
    """Optional information for the classification extension."""

    calculate_file_info: bool
    """Should file info be calculated for this asset (requires reading the whole file)."""

    extra_fields: Object
    """Any extra fields to include on the asset."""


@dataclass
class ItemInfo:
    """Information about an item.

    This is a "light" version of an actual PySTAC Item.
    """

    id: str
    """The item's id."""

    geometry: Optional[Object]
    """The item's geometry."""

    datetime: Optional[datetime.datetime]
    """The item's datetime."""

    properties: Object
    """The item's properties."""

    projection: Optional[Object]
    """The item's projection information, that will be used for the projection extension."""

    eo: Optional[Object]
    """Optional EO information for the item."""

    asset_infos: Dict[str, AssetInfo]
    """Information about the item's assets."""


@dataclass
class FileInfo:
    """Information about a file, for use with the file extension."""

    checksum: str
    """The file's multihash encoded digest."""

    size: int
    """The size of the file in bytes."""

    @classmethod
    def read(cls, href: str) -> "FileInfo":
        """Reads a file's information.

        Args:
            href (str): The file's href, to be read by fsspec.

        Returns:
            FileInfo: The file's information, including checksum and size.

        """
        m = hashlib.sha256()
        with fsspec.open(href, mode="rb") as file:
            data = file.read()
            size = len(data)
            m.update(data)
        hash = multihash.encode(m.digest(), code="sha2-256", length=m.digest_size)
        checksum = cast(str, multihash.to_hex_string(hash))
        return FileInfo(checksum=checksum, size=size)


class Builder:
    """Builds a STAC item from assets."""

    antimeridian_strategy: Strategy
    """The strategy used to fix geometries that cross the the antimeridian."""

    _assets: Dict[str, Asset]

    def __init__(
        self,
        *,
        antimeridian_strategy: Strategy = DEFAULT_ANTIMERIDIAN_STRATEGY,
    ) -> None:
        """Creates a new builder with no assets.

        Args:
            antimeridian_strategy (optional, Strategy): The strategy to use to
                fix polygons that cross the antimeridian.
        """
        self.antimeridian_strategy = antimeridian_strategy
        self._assets = {}

    def get_asset(self, key: str) -> Optional[Asset]:
        """Gets an asset by key.

        Args:
            key (str): The asset key.

        Returns:
            Optional[Asset]: The asset at the provided key, or None.
        """
        return self._assets.get(key)

    def add_asset(
        self,
        key: str,
        asset: Asset,
    ) -> Optional[Asset]:
        """Adds an asset to this builder.

        Returns the old asset if this key already existed.

        Args:
            key (str): The asset key.
            asset (Asset): The asset.

        Returns:
            Optional[Asset]: The asset that was replaced.
        """
        old_asset = self._assets.pop(key, None)
        self._assets[key] = asset
        return old_asset

    def add_assets(self, assets: Dict[str, Asset]) -> Dict[str, Asset]:
        """Adds assets to this builder.

        Returns any old assets that were removed from the builder.

        Args:
            assets (Dict[str, Asset]): The assets to add.

        Returns:
            Dict[str, Asset]: Any assets that were replaced.
        """
        old_assets = dict()
        for key, asset in assets.items():
            old_asset = self.add_asset(key, asset)
            if old_asset:
                old_assets[key] = old_asset
        return old_assets

    def remove_asset(self, key: str) -> Optional[Asset]:
        """Removes and returns an asset.

        Args:
            key (str): The asset key.

        Returns:
            Optional[Asset]: The removed asset, or None if none was removed.
        """
        return self._assets.pop(key, None)

    def create_item(self, id: Optional[str] = None) -> Item:
        """Creates a pystac Item using this builder's assets.

        Args:
            id (optional, str): The id of the created item. If not provided, the
                builder will use its `id()` method.

        Returns:
            Item: The Item created by this builder.
        """
        item_info = self.item_info(id)
        if item_info.geometry:
            bbox = self.bbox(item_info.geometry)
        else:
            bbox = None
        item = Item(
            id=item_info.id,
            geometry=item_info.geometry,
            bbox=bbox,
            datetime=item_info.datetime,
            properties=item_info.properties,
        )
        stactools.core.utils.antimeridian.fix_item(item, self.antimeridian_strategy)
        if item_info.projection:
            projection = ProjectionExtension.ext(item, add_if_missing=True)
            projection.apply(**item_info.projection)
        if item_info.eo:
            eo = EOExtension.ext(item, add_if_missing=True)
            eo.apply(**item_info.eo)

        keys = sorted(list(self._assets.keys()))
        for key in keys:
            asset = self._assets[key]
            item.add_asset(key, asset)
            asset_info = item_info.asset_infos.get(key)
            if not asset_info:
                continue
            if asset_info.projection:
                asset_projection = AssetProjectionExtension.ext(
                    asset, add_if_missing=True
                )
                asset_projection.apply(**asset_info.projection)
            if asset_info.raster:
                raster = RasterExtension.ext(asset, add_if_missing=True)
                raster.apply(**asset_info.raster)
            if asset_info.eo:
                asset_eo = AssetEOExtension.ext(asset, add_if_missing=True)
                asset_eo.apply(**asset_info.eo)
            if asset_info.classification:
                if CLASSIFICATION_EXTENSION_HREF not in item.stac_extensions:
                    item.stac_extensions.append(CLASSIFICATION_EXTENSION_HREF)
                asset.extra_fields.update(**asset_info.classification)
            if asset_info.calculate_file_info:
                file = FileExtension.ext(asset, add_if_missing=True)
                file_info = FileInfo.read(asset.href)
                file.checksum = file_info.checksum
                file.size = file_info.size
            asset.extra_fields.update(asset_info.extra_fields)

        return item

    def item_info(self, id: Optional[str]) -> ItemInfo:
        """Returns the ItemInfo object for this builder.

        ItemInfo contains optional fields that will be included in the final
        item, and AssetInfo objects that will be added to this builder's assets.
        This method includes logic to consolidate identical projection
        information from AssetInfo objects up to the ItemInfo.

        Args:
            id (optional, str): The id of the created item. If not provided,
                will use the `id()` method of this builder.

        Returns:
            ItemInfo: The item's information, e.g. its geometry and asset information.
        """
        asset_infos = dict()
        projections = []
        geometries = []
        for key in self._assets:
            asset_info = self.asset_info(key)
            if asset_info is None:
                continue
            if asset_info.projection:
                projections.append(asset_info.projection)
            if asset_info.geometry:
                geometries.append(asset_info.geometry)
            asset_infos[key] = asset_info

        if projections and all(
            projection == projections[0] for projection in projections
        ):
            projection = projections[0]
            for key in asset_infos:
                asset_infos[key].projection = None
        else:
            projection = None

        geometry = self.geometry(geometries)

        return ItemInfo(
            id=id or self.id(asset_infos),
            datetime=self.datetime(asset_infos),
            geometry=geometry,
            properties=self.properties(asset_infos),
            projection=projection,
            asset_infos=asset_infos,
            eo=None,
        )

    def id(self, asset_infos: Dict[str, AssetInfo]) -> str:
        """Returns the id for this item, possibly derived from asset information.

        Args:
            asset_infos (Dict[str, AssetInfo]): AssetInfos, possibly produced by reading assets.

        Raises:
            NotImplementedError: By default, raises a not implemented error.

        Returns:
            str: The item id.
        """
        raise NotImplementedError

    def datetime(
        self, asset_infos: Dict[str, AssetInfo]
    ) -> Optional[datetime.datetime]:
        """Returns the datetime for this item, possibly derived from asset information.

        Args:
            asset_infos (Dict[str, AssetInfo]): AssetInfos, possibly produced by reading assets.

        Raises:
            NotImplementedError: By default, raises a not implemented error.

        Returns:
            Optional[datetime.datetime]: Returns this item's datetime.
        """
        raise NotImplementedError

    def properties(self, asset_infos: Dict[str, AssetInfo]) -> Object:
        """Returns this item's extra properties.

        Args:
            asset_infos (Dict[str, AssetInfo]): Asset information, possibly read from the assets.

        Returns:
            Object: The item's properties, by default an empty dictionary.
        """
        return {}

    def asset_info(self, key: str) -> Optional[AssetInfo]:
        """Returns the asset information for the provided key.

        By default, returns None, as some assets may not have any extra
        information. Subclasses should override the method to return rich
        information about assets.

        Args:
            key (str): The asset key

        Returns:
            Optional[AssetInfo]: Either None, or information about the asset.
        """
        return None

    def geometry(self, geometries: List[Object]) -> Optional[Object]:
        """Returns a single geometry from a list of geometries that will be used
        as the item's geometry.

        By default, will return:
        - None, if the input list is empty,
        - The single geometry if all geometries are identical,
        - Or raise a ValueError if all geometries are not identical.

        Subclasses should override this method if they can provide geometries
        from other sources, or if they have logic to handle multiple geometries
        (e.g. enveloping).

        Args:
            geometries (List[Dict[str, Any]]): The input geometries.

        Raises:
            ValueError: Raised if the length of the input list is more than one.

        Returns:
            Optional[Dict[str, Any]]: The item's geometry, or None.
        """
        if not geometries:
            return None
        elif all(geometry == geometries[0] for geometry in geometries):
            return geometries[0]
        else:
            raise ValueError("Cannot determine a unique geometry for this item")

    def bbox(self, geometry: Object) -> List[float]:
        """Returns the bounding box for the item's geometry.

        By default, just returns the geometry's bounds, but subclasses could
        have different behavior.

        Args:
            geometry (Dict[str, Any]): The item's geometry

        Returns:
            List[float]: The bounding box.
        """
        return list(shapely.geometry.shape(geometry).bounds)


class RasterioBuilder(Builder):
    """Builds an item using rasterio to read information from assets."""

    rasterio_keys: Set[str]
    read_href_modifier: Optional[ReadHrefModifier]

    def __init__(
        self,
        *,
        read_href_modifier: Optional[ReadHrefModifier] = None,
        antimeridian_strategy: Strategy = DEFAULT_ANTIMERIDIAN_STRATEGY,
    ) -> None:
        """Creates a new rasterio builder with no assets.

        Args:
            read_href_modifier (optional, ReadHrefModifier): An optional
                callable that will modify any asset hrefs before reading with
                rasterio.
            antimeridian_strategy (optional, Strategy): The strategy that will
                be used to fix geometries that cross the antimeridian.
            include_projection_extension (optional, bool): Should the item
                and/or assets include the projection extension?
        """
        super().__init__(
            antimeridian_strategy=antimeridian_strategy,
        )
        self.rasterio_keys = set()
        self.read_href_modifier = read_href_modifier

    def add_rasterio_asset(
        self,
        key: str,
        asset: Asset,
    ) -> Optional[Asset]:
        """Adds an asset that will be read by rasterio to get band and
        projection information.


        See `add_asset` for the description of parameters.
        """
        self.rasterio_keys.add(key)
        return self.add_asset(
            key,
            asset,
        )

    def asset_info(self, key: str) -> Optional[AssetInfo]:
        """Returns an asset info for assets specified in `self.rasterio_keys`.

        Uses `read_asset_info_with_rasterio` to do the reading.
        """
        if key in self.rasterio_keys:
            asset = self.get_asset(key)
            assert asset
            return self.read_asset_info_with_rasterio(asset)
        else:
            return None

    def read_asset_info_with_rasterio(self, asset: Asset) -> AssetInfo:
        """Reads a given asset with rasterio, return the asset's information.

        The asset information will include projection and raster information.

        Args:
            asset (Asset): The pystac asset to be read.

        Returns:
            AssetInfo: The asset information.
        """
        projection = dict()
        raster = dict()
        href = asset.href
        if self.read_href_modifier:
            href = self.read_href_modifier(asset.href)
        with rasterio.open(href) as dataset:
            crs = dataset.crs
            projection["bbox"] = dataset.bounds
            projection["transform"] = list(dataset.transform)[0:6]
            projection["shape"] = dataset.shape
            bands = list()
            for dtype, nodata, scale, offset, units in zip(
                dataset.dtypes,
                dataset.nodatavals,
                dataset.scales,
                dataset.offsets,
                dataset.units,
            ):
                bands.append(
                    RasterBand.create(
                        data_type=dtype,
                        nodata=nodata,
                        scale=scale,
                        offset=offset,
                        unit=units,
                    )
                )
            raster["bands"] = bands
        projection["geometry"] = shapely.geometry.mapping(
            shapely.geometry.box(*projection["bbox"])
        )
        try:
            projection["epsg"] = crs.to_epsg()
        except CRSError:
            projection["epsg"] = None
        if projection["epsg"] is None:
            projection["wkt2"] = crs.to_wkt("WKT2")
        if projection["epsg"] == EPSG:
            geometry = projection["geometry"]
        else:
            geometry = stactools.core.projection.reproject_geom(
                crs, f"EPSG:{EPSG}", projection["geometry"], precision=6
            )
        del projection["bbox"]
        return AssetInfo(
            geometry=geometry,
            projection=projection,
            raster=raster,
            eo=None,
            classification=None,
            calculate_file_info=False,
            extra_fields={},
        )


class SingleFileRasterioBuilder(RasterioBuilder):
    """Creates an item from a single file."""

    DEFAULT_KEY = "data"
    """The default key that will point to the single file."""

    _key: str

    def __init__(
        self,
        key: str,
        asset: Asset,
    ):
        """Creates a new builder with the given asset and asset key."""
        super().__init__()
        self._key = key
        self.add_rasterio_asset(
            key,
            asset,
        )

    @classmethod
    def from_href(
        cls, href: str, key: str = DEFAULT_KEY
    ) -> "SingleFileRasterioBuilder":
        """Creates a builder from a single href."""
        return cls(key, Asset(href, roles=["data"]))

    @property
    def asset(self) -> Asset:
        """Returns the asset for the single file.

        Returns:
            Asset: The single file asset.
        """
        return self._assets[self._key]

    def id(self, asset_infos: Dict[str, AssetInfo]) -> str:
        """Sets the id to the basename (w/o extension) of the single file.

        Args:
            assets (Assets): The assets for this builder (unused).

        Returns:
            str: The id for the item.
        """
        return os.path.splitext(os.path.basename(self.asset.href))[0]


class SingleCOGBuilder(SingleFileRasterioBuilder):
    """Creates an item from a single COG file."""

    @classmethod
    def from_href(
        cls,
        href: str,
        key: str = SingleFileRasterioBuilder.DEFAULT_KEY,
    ) -> "SingleCOGBuilder":
        return cls(
            key,
            Asset(href, roles=["data"], media_type=MediaType.COG),
        )
