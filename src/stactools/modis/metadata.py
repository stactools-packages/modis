import datetime
import math
import os.path
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import fsspec
import shapely.geometry
from lxml import etree
from shapely.geometry import Polygon
from stactools.core.io import ReadHrefModifier
from stactools.core.io.xml import XmlElement

from stactools.modis import utils
from stactools.modis.constants import TEMPORALLY_WEIGHTED_PRODUCTS

SIN_SPHERE_RADIUS = 6371007.181
SIN_TILE_METERS = 1111950
SIN_X_MIN = -20015109
SIN_Y_MAX = 10007555
SIN_CRS = 'PROJCRS["unnamed",BASEGEOGCRS["Unknown datum based upon the custom spheroid",DATUM["Not specified (based on custom spheroid)",ELLIPSOID["Custom spheroid",6371007.181,0,LENGTHUNIT["metre",1,ID["EPSG",9001]]]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433,ID["EPSG",9122]]]],CONVERSION["unnamed",METHOD["Sinusoidal"],PARAMETER["Longitude of natural origin",0,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8802]],PARAMETER["False easting",0,LENGTHUNIT["metre",1],ID["EPSG",8806]],PARAMETER["False northing",0,LENGTHUNIT["metre",1],ID["EPSG",8807]]],CS[Cartesian,2],AXIS["easting",east,ORDER[1],LENGTHUNIT["metre",1,ID["EPSG",9001]]],AXIS["northing",north,ORDER[2],LENGTHUNIT["metre",1,ID["EPSG",9001]]]]'  # noqa
SIN_TILE_PIXELS = {
    1200: ["11A1", "11A2", "14A1", "14A2", "21A2"],
    2400: [
        "09A1",
        "10A1",
        "10A2",
        "12Q1",
        "13A1",
        "15A2H",
        "15A3H",
        "16A3GF",
        "17A2H",
        "17A2HGF",
        "17A3HGF",
        "43A4",
        "64A1",
    ],  # noqa
    4800: ["09Q1", "13Q1", "44B", "44W"],
}


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
        def exterior_pixel_coords(pixels: int) -> List[List[int]]:
            col_row = []
            col_row.extend([[0, row] for row in range(pixels)])  # left
            col_row.extend([[col, pixels - 1] for col in range(pixels)])  # bottom
            col_row.extend(
                [[pixels - 1, row] for row in range(pixels).__reversed__()]
            )  # right
            col_row.extend([[col, 0] for col in range(pixels).__reversed__()])  # top
            return col_row

        def pixel_to_geodetic(
            pixel_coords: List[List[int]], htile: int, vtile: int, pixels: int
        ) -> List[List[float]]:
            pixel_width = SIN_TILE_METERS / pixels
            lon_lat = []
            for col, row in pixel_coords:
                x = (col + 0.5) * pixel_width + htile * SIN_TILE_METERS + SIN_X_MIN
                y = SIN_Y_MAX - (row + 0.5) * pixel_width - vtile * SIN_TILE_METERS
                lat = math.degrees(y / SIN_SPHERE_RADIUS)
                lon = math.degrees(
                    x / (SIN_SPHERE_RADIUS * math.cos(math.radians(lat)))
                )
                if lat >= -90 and lat <= 90 and lon >= -180 and lon <= 180:
                    lon_lat.append([lon, lat])
            return lon_lat

        tile_pixel_size = [k for k, v in SIN_TILE_PIXELS.items() if collection in v][0]
        pixel_degrees = SIN_TILE_METERS / tile_pixel_size / 100000  # at equator
        pixel_coords = exterior_pixel_coords(tile_pixel_size)
        geo_coords = pixel_to_geodetic(pixel_coords, htile, vtile, tile_pixel_size)
        polygon = Polygon(geo_coords).simplify(tolerance=pixel_degrees / 2)
        geometry = shapely.geometry.mapping(polygon)

        geometry["coordinates"] = utils.recursive_round(list(geometry["coordinates"]))
        bbox = utils.recursive_round(list(polygon.bounds))

        return (geometry, bbox)
