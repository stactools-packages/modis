import datetime
import os.path
import warnings
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import fsspec
import numpy as np
import rasterio
from lxml import etree
from rasterio import Affine
from rasterio.crs import CRS
from rasterio.errors import NotGeoreferencedWarning
from shapely.geometry import shape
from stactools.core.io import ReadHrefModifier
from stactools.core.io.xml import XmlElement

from stactools.modis import utils
from stactools.modis.constants import (
    PRECISION,
    SINUSOIDAL_TILE_METERS,
    SINUSOIDAL_X_MIN,
    SINUSOIDAL_Y_MAX,
    TEMPORALLY_WEIGHTED_PRODUCTS,
)
from stactools.modis.sinusoidal import (
    SinusoidalFootprint,
    pixel_degree_size,
    tile_pixel_size,
)


class MissingElement(Exception):
    """An expected element is missing from the XML file"""


@dataclass(frozen=True)
class Metadata:
    """Structure to hold values fetched from a metadata XML file or other metadata source."""

    id: str
    product: str
    version: str
    geometry: Optional[Dict[str, Any]]
    bbox: Optional[List[float]]
    start_datetime: datetime.datetime
    end_datetime: datetime.datetime
    created: Optional[datetime.datetime]
    updated: Optional[datetime.datetime]
    qa_percent_not_produced_cloud: int
    qa_percent_cloud_cover: Dict[str, int]
    horizontal_tile: int
    vertical_tile: int
    tile_id: str
    platforms: List[str]
    instruments: List[str]
    collection: str

    @classmethod
    def from_xml_href(
        cls, href: str, read_href_modifier: Optional[ReadHrefModifier] = None
    ) -> "Metadata":
        """Reads metadat from an XML href.

        Args:
            href (str): The href of the xml metadata file
            read_href_modifier (Optional[Callable[[str], str]]): Optional
                function to modify the read href

        Returns:
            Metadata: Information that will map to Item attributes.
        """

        def missing_element(attribute: str) -> Callable[[str], Exception]:
            def get_exception(xpath: str) -> Exception:
                return MissingElement(
                    f"Could not find attribute `{attribute}` at xpath '{xpath}' at href {href}"
                )

            return get_exception

        if read_href_modifier:
            read_href = read_href_modifier(href)
        else:
            read_href = href
        with fsspec.open(read_href) as file:
            root = XmlElement(etree.parse(file, base_url=href).getroot())

        metadata = root.find_or_throw(
            "GranuleURMetaData", missing_element("URMetadata")
        )
        id = ".".join(
            os.path.splitext(
                metadata.find_text_or_throw(
                    "ECSDataGranule/LocalGranuleID", missing_element("id")
                )
            )[0].split(".")[0:-1]
        )
        product = metadata.find_text_or_throw(
            "CollectionMetaData/ShortName", missing_element("product")
        )
        version = utils.version_string(
            metadata.find_text_or_throw(
                "CollectionMetaData/VersionID", missing_element("version")
            )
        )

        start_date = metadata.find_text_or_throw(
            "RangeDateTime/RangeBeginningDate", missing_element("start_date")
        )
        start_time = metadata.find_text_or_throw(
            "RangeDateTime/RangeBeginningTime", missing_element("start_time")
        )
        start_datetime = datetime.datetime.fromisoformat(f"{start_date}T{start_time}")
        end_date = metadata.find_text_or_throw(
            "RangeDateTime/RangeEndingDate", missing_element("end_date")
        )
        end_time = metadata.find_text_or_throw(
            "RangeDateTime/RangeEndingTime", missing_element("end_time")
        )
        end_datetime = datetime.datetime.fromisoformat(f"{end_date}T{end_time}")

        created = datetime.datetime.fromisoformat(
            metadata.find_text_or_throw(
                "ECSDataGranule/ProductionDateTime", missing_element("created")
            )
        )
        updated = datetime.datetime.fromisoformat(
            metadata.find_text_or_throw("LastUpdate", missing_element("updated"))
        )

        psas = metadata.findall("PSAs/PSA")
        qa_percent_not_produced_cloud = None
        for psa in psas:
            name = psa.find_text_or_throw("PSAName", missing_element("PSAName"))
            value = psa.find_text_or_throw("PSAValue", missing_element("PSAValue"))
            if name == "HORIZONTALTILENUMBER":
                horizontal_tile = int(value)
            elif name == "VERTICALTILENUMBER":
                vertical_tile = int(value)
            elif name == "TileID":
                tile_id = value
            elif name == "QAPERCENTNOTPRODUCEDCLOUD":
                qa_percent_not_produced_cloud = int(value)

        qa_percent_cloud_cover: Dict[str, int] = {}
        measured_parameters = metadata.findall(
            "MeasuredParameter/MeasuredParameterContainer"
        )
        for measured_parameter in measured_parameters:
            name = measured_parameter.find_text_or_throw(
                "ParameterName", missing_element("ParameterName")
            ).replace(" ", "_")
            band_qa_percent_cloud_cover = measured_parameter.find_text(
                "QAStats/QAPercentCloudCover"
            )
            if band_qa_percent_cloud_cover:
                qa_percent_cloud_cover[name] = int(band_qa_percent_cloud_cover)

        if qa_percent_cloud_cover and qa_percent_not_produced_cloud is None:
            assert len(set(qa_percent_cloud_cover.values())) == 1, (
                f"Mutiple, different 'qa_percent_cloud_cover' values exist "
                f"in href={href}. This is not supported at this time."
            )
            qa_percent_not_produced_cloud = next(iter(qa_percent_cloud_cover.values()))

        platform_elements = metadata.findall("Platform")
        platforms = [
            platform.find_text_or_throw(
                "PlatformShortName", missing_element("platform_short_name")
            ).lower()
            for platform in platform_elements
        ]
        instruments = list(
            set(
                platform.find_text_or_throw(
                    "Instrument/InstrumentShortName",
                    missing_element("instrument_short_name"),
                ).lower()
                for platform in platform_elements
            )
        )

        collection = cls._collection(product)
        geometry, bbox = cls._geometry_and_bbox(
            collection, horizontal_tile, vertical_tile
        )

        return Metadata(
            id=id,
            product=product,
            version=version,
            geometry=geometry,
            bbox=bbox,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            created=created,
            updated=updated,
            qa_percent_not_produced_cloud=qa_percent_not_produced_cloud,
            qa_percent_cloud_cover=qa_percent_cloud_cover,
            horizontal_tile=horizontal_tile,
            vertical_tile=vertical_tile,
            tile_id=tile_id,
            platforms=platforms,
            instruments=instruments,
            collection=collection,
        )

    @classmethod
    def from_cog_tags(cls, cog_tags: Dict[str, str]) -> "Metadata":
        start_datetime = datetime.datetime.fromisoformat(
            f"{cog_tags['RANGEBEGINNINGDATE']} {cog_tags['RANGEBEGINNINGTIME']}"
        )
        end_datetime = datetime.datetime.fromisoformat(
            f"{cog_tags['RANGEENDINGDATE']} {cog_tags['RANGEENDINGTIME']}"
        )
        platforms = set()
        for key in (
            key
            for key in cog_tags.keys()
            if key.startswith("ASSOCIATEDPLATFORMSHORTNAME")
        ):
            platforms.add(cog_tags[key].lower())
        instruments = set()
        for key in (
            key
            for key in cog_tags.keys()
            if key.startswith("ASSOCIATEDINSTRUMENTSHORTNAME")
        ):
            instruments.add(cog_tags[key].lower())
        product = cog_tags["SHORTNAME"]
        horizontal_tile = int(cog_tags["HORIZONTALTILENUMBER"])
        vertical_tile = int(cog_tags["VERTICALTILENUMBER"])
        collection = cls._collection(product)
        geometry, bbox = cls._geometry_and_bbox(
            collection, horizontal_tile, vertical_tile
        )
        return Metadata(
            id=os.path.splitext(cog_tags["LOCALGRANULEID"])[0],
            product=product,
            version=utils.version_string(cog_tags["VERSIONID"]),
            geometry=geometry,
            bbox=bbox,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            created=None,
            updated=None,
            qa_percent_not_produced_cloud=int(cog_tags["QAPERCENTNOTPRODUCEDCLOUD"]),
            qa_percent_cloud_cover=None,
            horizontal_tile=horizontal_tile,
            vertical_tile=vertical_tile,
            tile_id=cog_tags["TileID"],
            platforms=sorted(list(platforms)),
            instruments=sorted(list(instruments)),
            collection=collection,
        )

    @classmethod
    def from_hdf_href(
        cls, href: str, read_href_modifier: Optional[ReadHrefModifier] = None
    ) -> "Metadata":
        """Reads metadata from an HDF file when XML is not available.

        Args:
            href (str): The href of the HDF file
            read_href_modifier (Optional[Callable[[str], str]]): Optional
                function to modify the read href

        Returns:
            Metadata: Information that will map to Item attributes.
        """
        if read_href_modifier:
            read_href = read_href_modifier(href)
        else:
            read_href = href

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=NotGeoreferencedWarning)
            with rasterio.open(read_href) as dataset:
                hdf_tags = dataset.tags()

        return cls.from_cog_tags(hdf_tags)

    @property
    def datetime(self) -> Optional[datetime.datetime]:
        """Returns a single nominal datetime for this metadata file.

        Depending on the product, this might be the midpoint between the
        start and end datetimes, or it might be None.

        Returns:
            Optional[datetime.datetime]: The nominal datetime for this product.
        """
        if self.product in TEMPORALLY_WEIGHTED_PRODUCTS:
            return self.start_datetime + (self.end_datetime - self.start_datetime) / 2
        else:
            return None

    @classmethod
    def _collection(cls, product: str) -> str:
        return product[3:]

    @classmethod
    def _geometry_and_bbox(
        cls, collection: str, htile: int, vtile: int
    ) -> Tuple[Dict[str, Any], List[float]]:
        tile_size_pixels = tile_pixel_size(collection)
        data_array = np.full((tile_size_pixels, tile_size_pixels), 1, dtype=np.uint8)

        pixel_size_meters = SINUSOIDAL_TILE_METERS / tile_size_pixels
        x_offset = htile * SINUSOIDAL_TILE_METERS + SINUSOIDAL_X_MIN
        y_offset = SINUSOIDAL_Y_MAX - vtile * SINUSOIDAL_TILE_METERS
        transform = Affine(
            pixel_size_meters, 0, x_offset, 0, -pixel_size_meters, y_offset
        )

        footprint_geometry = SinusoidalFootprint(
            data_array=data_array,
            crs=CRS.from_epsg(4326),  # unused
            transform=transform,
            precision=PRECISION,
            simplify_tolerance=pixel_degree_size(collection),
        ).footprint()
        footprint_bbox = shape(footprint_geometry).bounds

        return (footprint_geometry, footprint_bbox)
