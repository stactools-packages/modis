from typing import Any, Dict

from pystac import MediaType

CLASSIFICATION_EXTENSION_HREF = (
    "https://stac-extensions.github.io/classification/v1.0.0/schema.json"
)
HDF_ASSET_KEY = "hdf"
HDF_ASSET_PROPERTIES = {
    "type": MediaType.HDF,
    "roles": ["data"],
    "title": "Source data containing all bands",
}
METADATA_ASSET_KEY = "metadata"
METADATA_ASSET_PROPERTIES = {
    "type": MediaType.XML,
    "roles": ["metadata"],
    "title": "Federal Geographic Data Committee (FGDC) Metadata",
}
TEMPORALLY_WEIGHTED_PRODUCTS = ["MCD43A4"]

# Sinusoidal projection parameters found in Appendix B of
# https://modis-fire.umd.edu/files/MODIS_C6_BA_User_Guide_1.2.pdf
SIN_SPHERE_RADIUS = 6371007.181
SIN_TILE_METERS = 1111950
SIN_X_MIN = -20015109
SIN_Y_MAX = 10007555
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
    ],
    4800: ["09Q1", "13Q1", "44B", "44W"],
}

PRECISION = 6

# fmt: off
COLLECTIONS: Dict[str, Dict[str, Any]] = {  # only collecton 061 products
    "11A1": {
        "sin_tile_pixels": 1200,
        "footprint_assets": ["LST_Day_1km", "LST_Night_1km", "Emis_31", "Emis_32"],
    },
    "11A2": {
        "sin_tile_pixels": 1200,
        "footprint_assets": ["LST_Day_1km", "LST_Night_1km", "Emis_31", "Emis_32"],
    },
    "14A1": {
        "sin_tile_pixels": 1200,
        "footprint_assets": ["FireMask"],
        "footprint_asset_bands": [],
    },
    "14A2": {
        "sin_tile_pixels": 1200,
        "footprint_assets": ["FireMask"],
        "footprint_asset_bands": [],
    },
    "21A2": {
        "sin_tile_pixels": 1200,
        "footprint_assets": ["LST_Day_1km", "LST_Night_1km", "Emis_31", "Emis_32"],
    },
    "09A1": {
        "sin_tile_pixels": 2400,
        "footprint_assets": [f"sur_refl_b0{b}" for b in range(1, 8)],
    },
    "10A1": {
        "sin_tile_pixels": 2400,
        "footprint_assets": ["NDSI_Snow_Cover", "Snow_Albedo_Daily_Tile"],
    },
    "10A2": {
        "sin_tile_pixels": 2400,
        "footprint_assets": ["Maximum_Snow_Extent"]
    },
    "12Q1": {
        "sin_tile_pixels": 2400
    },
    "13A1": {
        "sin_tile_pixels": 2400,
        "footprint_assets": ["500m_16_days_NDVI"]
    },
    "15A2H": {
        "sin_tile_pixels": 2400,
        "footprint_assets": ["Fpar_500m"]
    },
    "15A3H": {
        "sin_tile_pixels": 2400,
        "footprint_assets": ["Fpar_500m"]
    },
    "16A3GF": {
        "sin_tile_pixels": 2400,
        "footprint_assets": ["ET_500m"]
    },
    "17A2H": {
        "sin_tile_pixels": 2400,
        "footprint_assets": ["Gpp_500m"]
    },
    "17A2HGF": {
        "sin_tile_pixels": 2400,
        "footprint_assets": ["Gpp_500m"]
    },
    "17A3HGF": {
        "sin_tile_pixels": 2400,
        "footprint_assets": ["Gpp_500m"]
    },
    "43A4": {
        "sin_tile_pixels": 2400,
        "footprint_assets": [f"Nadir_Reflectance_Band{b}" for b in range(1, 8)],
    },
    "44W": {
        "sin_tile_pixels": 2400
    },
    "64A1": {
        "sin_tile_pixels": 2400,
        "footprint_assets": ["Burn_Date"]
    },
    "09Q1": {
        "sin_tile_pixels": 4800,
        "footprint_assets": ["sur_refl_b01", "sur_refl_b02"],
    },
    "13Q1": {
        "sin_tile_pixels": 4800,
        "footprint_assets": ["250m_16_days_NDVI"]
    },
    "44B": {
        "sin_tile_pixels": 4800
    }
}
# fmt:on
