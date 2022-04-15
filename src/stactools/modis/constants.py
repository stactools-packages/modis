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
