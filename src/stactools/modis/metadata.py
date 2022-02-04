import datetime
import os.path
from typing import Callable, Optional

import fsspec
import shapely.geometry
from lxml import etree
from shapely.geometry import Polygon

from stactools.core.io.xml import XmlElement


class MissingElement(Exception):
    """An expected element is missing from the XML file"""


class Metadata:
    """Structure to hold values fetched from a metadata XML file."""

    def __init__(self, href: str):
        """Reads fields from a metadata href."""

        def missing_element(attribute: str) -> Callable[[str], Exception]:

            def get_exception(xpath: str) -> Exception:
                return MissingElement(
                    f"Could not find attribute `{attribute}` at xpath '{xpath}' at href {href}"
                )

            return get_exception

        with fsspec.open(href) as file:
            root = XmlElement(etree.parse(file, base_url=href).getroot())

        self.id = os.path.splitext(
            root.find_text_or_throw(
                "GranuleURMetaData/ECSDataGranule/LocalGranuleID",
                missing_element("id")))[0]
        self.product = root.find_text_or_throw(
            "GranuleURMetaData/CollectionMetaData/ShortName",
            missing_element("product"))
        version = root.find_text_or_throw(
            "GranuleURMetaData/CollectionMetaData/VersionID",
            missing_element("version"))
        if version == "6":
            self.version = "006"
        elif version == "61":
            self.version = "061"
        else:
            raise ValueError(f"Unsupported MODIS version: {version}")

        points = [(
            float(
                point.find_text_or_throw("PointLongitude",
                                         missing_element("longitude"))),
            float(
                point.find_text_or_throw("PointLatitude",
                                         missing_element("latitude")))
        ) for point in root.findall(
            "GranuleURMetaData/SpatialDomainContainer/HorizontalSpatialDomainContainer/"
            "GPolygon/Boundary/Point")]
        polygon = Polygon(points)
        self.geometry = shapely.geometry.mapping(polygon)
        self.bbox = polygon.bounds

        start_date = root.find_text_or_throw(
            "GranuleURMetaData/RangeDateTime/RangeBeginningDate",
            missing_element("start_date"))
        start_time = root.find_text_or_throw(
            "GranuleURMetaData/RangeDateTime/RangeBeginningTime",
            missing_element("start_time"))
        self.start_datetime = datetime.datetime.fromisoformat(
            f"{start_date}T{start_time}")
        end_date = root.find_text_or_throw(
            "GranuleURMetaData/RangeDateTime/RangeBeginningDate",
            missing_element("end_date"))
        end_time = root.find_text_or_throw(
            "GranuleURMetaData/RangeDateTime/RangeEndingTime",
            missing_element("end_time"))
        self.end_datetime = datetime.datetime.fromisoformat(
            f"{end_date}T{end_time}")

        self.created = datetime.datetime.fromisoformat(
            root.find_text_or_throw(
                "GranuleURMetaData/ECSDataGranule/ProductionDateTime",
                missing_element("created")))
        self.updated = datetime.datetime.fromisoformat(
            root.find_text_or_throw("GranuleURMetaData/LastUpdate",
                                    missing_element("updated")))

        platforms = root.findall("GranuleURMetaData/Platform")
        if len(platforms) == 1:
            self.platform = platforms[0].find_text_or_throw(
                "PlatformShortName",
                missing_element("platform_short_name")).lower()
        else:
            # TODO what should we do about products that list both Terra and Aqua
            # for their platforms?
            self.platform = platforms[0].find_text_or_throw(
                "PlatformShortName",
                missing_element("platform_short_name")).lower()
        self.instruments = list(
            set(
                platform.find_text_or_throw("Instrument/InstrumentShortName",
                                            "instrument_short_name").lower()
                for platform in platforms))

    @property
    def datetime(self) -> Optional[datetime.datetime]:
        """Returns a single nominal datetime for this metadata file.

        Depending on the product, this might be the midpoint between the
        start and end datetimes, or it might be None.

        Returns:
            Optional[datetime.datetime]: The nominal datetime for this product.
        """
        # FIXME this is incorrect, need to account for the prouduct type
        return self.start_datetime + (self.end_datetime -
                                      self.start_datetime) / 2
