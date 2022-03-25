"""Raster bands needs to be an array."""

import json
import os
from pathlib import Path

fragments_directory = Path(
    __file__).parents[1] / "src" / "stactools" / "modis" / "fragments"

for directory, directories, file_names in os.walk(fragments_directory):
    if "bands.json" not in file_names:
        continue
    bands_path = Path(directory) / "bands.json"
    print(f"Processing {bands_path}")
    with open(bands_path) as file:
        bands = json.load(file)
    for key in bands:
        if "raster:bands" not in bands[key]:
            continue
        if isinstance(bands[key]["raster:bands"], dict):
            bands[key]["raster:bands"] = [bands[key]["raster:bands"]]
    with open(bands_path, "w") as file:
        json.dump(bands, file, indent=4)
