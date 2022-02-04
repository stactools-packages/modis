import datetime
import os.path
from typing import Callable, Optional

import fsspec
import shapely.geometry
from lxml import etree
from shapely.geometry import Polygon
from stactools.core.io import ReadHrefModifier
from stactools.core.io.xml import XmlElement


class MissingElement(Exception):
    """An expected element is missing from the XML file"""


class Metadata:
    """Structure to hold values fetched from a metadata XML file."""

    def __init__(self,
                 href: str,
                 read_href_modifier: Optional[ReadHrefModifier] = None):
        """Reads fields from a metadata href.

        Args:
            href (str): The href of the xml metadata file
            read_href_modifier (Optional[Callable[[str], str]]): Optional
                function to modify the read href
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

        metadata = root.find_or_throw("GranuleURMetaData",
                                      missing_element("URMetadata"))
        self.id = os.path.splitext(
            metadata.find_text_or_throw("ECSDataGranule/LocalGranuleID",
                                        missing_element("id")))[0]
        self.product = metadata.find_text_or_throw(
            "CollectionMetaData/ShortName", missing_element("product"))
        version = metadata.find_text_or_throw("CollectionMetaData/VersionID",
                                              missing_element("version"))
        if version == "6":
            self.version = "006"
        elif version == "61":
            self.version = "061"
        else:
            raise ValueError(f"Unsupported MODIS version: {version}")

        points = [
            (float(
                point.find_text_or_throw("PointLongitude",
                                         missing_element("longitude"))),
             float(
                 point.find_text_or_throw("PointLatitude",
                                          missing_element("latitude"))))
            for point in metadata.findall(
                "SpatialDomainContainer/HorizontalSpatialDomainContainer/"
                "GPolygon/Boundary/Point")
        ]
        polygon = Polygon(points)
        self.geometry = shapely.geometry.mapping(polygon)
        self.bbox = polygon.bounds

        start_date = metadata.find_text_or_throw(
            "RangeDateTime/RangeBeginningDate", missing_element("start_date"))
        start_time = metadata.find_text_or_throw(
            "RangeDateTime/RangeBeginningTime", missing_element("start_time"))
        self.start_datetime = datetime.datetime.fromisoformat(
            f"{start_date}T{start_time}")
        end_date = metadata.find_text_or_throw("RangeDateTime/RangeEndingDate",
                                               missing_element("end_date"))
        end_time = metadata.find_text_or_throw("RangeDateTime/RangeEndingTime",
                                               missing_element("end_time"))
        self.end_datetime = datetime.datetime.fromisoformat(
            f"{end_date}T{end_time}")

        self.created = datetime.datetime.fromisoformat(
            metadata.find_text_or_throw("ECSDataGranule/ProductionDateTime",
                                        missing_element("created")))
        self.updated = datetime.datetime.fromisoformat(
            metadata.find_text_or_throw("LastUpdate",
                                        missing_element("updated")))

        platforms = metadata.findall("Platform")
        # Per the discussion in
        # https://github.com/radiantearth/stac-spec/issues/216, it seems like
        # the recommendation for multi-platform datasets is to just include both
        # and use a string seperator.
        self.platform = ",".join([
            platform.find_text_or_throw(
                "PlatformShortName",
                missing_element("platform_short_name")).lower()
            for platform in platforms
        ])
        self.instruments = list(
            set(
                platform.find_text_or_throw(
                    "Instrument/InstrumentShortName",
                    missing_element("instrument_short_name")).lower()
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
