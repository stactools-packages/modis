from pystac import MediaType

HDF_ASSET_KEY = "hdf"
HDF_ASSET_PROPERTIES = {
    "type": MediaType.HDF,
    "roles": ["data"],
    "title": "hdf data"
}
METADATA_ASSET_KEY = "metadata"
METADATA_ASSET_PROPERTIES = {
    "type": MediaType.XML,
    "roles": ["metadata"],
    "title": "FGDC Metdata"
}
