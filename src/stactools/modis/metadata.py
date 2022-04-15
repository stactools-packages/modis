import datetime
import os.path
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import fsspec
import shapely.geometry
from lxml import etree
from shapely.geometry import Polygon
from stactools.core.io import ReadHrefModifier
from stactools.core.io.xml import XmlElement

from stactools.modis import utils
from stactools.modis.constants import TEMPORALLY_WEIGHTED_PRODUCTS


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
        id = os.path.splitext(
            metadata.find_text_or_throw(
                "ECSDataGranule/LocalGranuleID", missing_element("id")
            )
        )[0]
        product = metadata.find_text_or_throw(
            "CollectionMetaData/ShortName", missing_element("product")
        )
        version = utils.version_string(
            metadata.find_text_or_throw(
                "CollectionMetaData/VersionID", missing_element("version")
            )
        )

        points = [
            (
                float(
                    point.find_text_or_throw(
                        "PointLongitude", missing_element("longitude")
                    )
                ),
                float(
                    point.find_text_or_throw(
                        "PointLatitude", missing_element("latitude")
                    )
                ),
            )
            for point in metadata.findall(
                "SpatialDomainContainer/HorizontalSpatialDomainContainer/"
                "GPolygon/Boundary/Point"
            )
        ]
        polygon = Polygon(points)
        geometry = shapely.geometry.mapping(polygon)
        bbox = polygon.bounds

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
                "QAPercentCloudCover"
            )
            if qa_percent_cloud_cover:
                qa_percent_cloud_cover[name] = int(band_qa_percent_cloud_cover)

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
        )

    @classmethod
    def from_cog_tags(self, cog_tags: Dict[str, str]) -> "Metadata":
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
        return Metadata(
            id=os.path.splitext(cog_tags["LOCALGRANULEID"])[0],
            product=cog_tags["SHORTNAME"],
            version=utils.version_string(cog_tags["VERSIONID"]),
            geometry=None,
            bbox=None,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            created=None,
            updated=None,
            qa_percent_not_produced_cloud=int(cog_tags["QAPERCENTNOTPRODUCEDCLOUD"]),
            qa_percent_cloud_cover=None,
            horizontal_tile=int(cog_tags["HORIZONTALTILENUMBER"]),
            vertical_tile=int(cog_tags["VERTICALTILENUMBER"]),
            tile_id=cog_tags["TileID"],
            platforms=sorted(list(platforms)),
            instruments=sorted(list(instruments)),
        )

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

    @property
    def collection(self) -> str:
        return self.product[3:]
