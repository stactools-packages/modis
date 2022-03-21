"""Redo how the bands are laid out.

1. Make bands.json a dict with the name as the key.
2. Move description to name
3. Move raster bands inside bands
4. Delete raster bands.

Also redo some of the collection titles.
"""

import json
import os
from pathlib import Path

fragments_directory = Path(
    __file__).parents[1] / "src" / "stactools" / "modis" / "fragments"

SPECIAL_DOI_TITLES = {
    "MOD10A1":
    "MODIS/Terra Snow Cover Daily L3 Global 500m SIN Grid, Version 61",
    "MYD10A1":
    "MODIS/Aqua Snow Cover Daily L3 Global 500m SIN Grid, Version 61",
    "MOD10A2":
    "MODIS/Terra Snow Cover 8-Day L3 Global 500m SIN Grid, Version 61",
    "MYD10A2":
    "MODIS/Aqua Snow Cover 8-Day L3 Global 500m SIN Grid, Version 61",
}

for directory, directories, file_names in os.walk(fragments_directory):
    if "bands.json" not in file_names:
        continue
    bands_path = Path(directory) / "bands.json"
    raster_bands_path = Path(directory) / "raster-bands.json"
    print(f"Processing {bands_path}")
    with open(bands_path) as file:
        bands = json.load(file)
    if isinstance(bands, dict):
        print(f"Skipping {bands_path}, already processed")
        continue
    raster_bands = None
    if "raster-bands.json" in file_names:
        with open(raster_bands_path) as file:
            raster_bands = json.load(file)
    new_bands = dict()
    for band in bands:
        name = band.pop("name")
        new_bands[name] = {"name": band["description"]}
        if raster_bands:
            raster_band = raster_bands[name]
            new_raster_band = dict()
            for key, value in raster_band.items():
                if value is not None:
                    new_raster_band[key] = value
            new_bands[name]["raster:bands"] = new_raster_band
    with open(bands_path, "w") as file:
        json.dump(new_bands, file, indent=4)
    if "raster-bands.json" in file_names:
        os.remove(raster_bands_path)

for directory, directories, file_names in os.walk(fragments_directory):
    if "collection.json" not in file_names:
        continue
    collection_path = Path(directory) / "collection.json"
    print(f"Processing {collection_path}")
    with open(collection_path) as file:
        collection = json.load(file)
    for link in collection["links"]:
        if link["href"].endswith(".pdf"):
            product = os.path.basename(link["href"]).split("_")[0]
            link["title"] = f"{product} User Guide"
        if link["href"].startswith(
                "https://ladsweb.modaps.eosdis.nasa.gov/filespec"):
            product = os.path.basename(link["href"])
            link["title"] = f"{product} file specification"
        if link["href"].startswith("https://doi.org/10.5067/MODIS"):
            product = os.path.basename(link["href"]).split(".")[0]
            if product in SPECIAL_DOI_TITLES:
                link["title"] = SPECIAL_DOI_TITLES[product]
            else:
                link["title"] = f"LP DAAC - {product}"
    with open(collection_path, "w") as file:
        json.dump(collection, file, indent=4)
