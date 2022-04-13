#!/usr/bin/env python3
"""Adds the classification extension.

Also consolidates file-info into bands, and removes classification and file-info.
"""

import json
import os
from pathlib import Path

fragments_directory = (
    Path(__file__).parents[1] / "src" / "stactools" / "modis" / "fragments"
)

for directory, directories, file_names in os.walk(fragments_directory):
    if "bands.json" not in file_names or "file-info.json" not in file_names:
        continue
    bands_path = Path(directory) / "bands.json"
    print(f"Processing {bands_path}")
    if "classification.json" in file_names:
        os.remove(Path(directory) / "classification.json")
    with open(bands_path) as file:
        bands = json.load(file)

    file_info_path = Path(directory) / "file-info.json"
    with open(file_info_path) as file:
        file_info = json.load(file)

    os.remove(file_info_path)

    if not file_info:
        continue

    for name, values in file_info.items():
        bands[name]["file:values"] = values
        classification_classes = []
        for value in values:
            classification_classes.append(
                {"value": value["values"][0], "description": value["summary"]}
            )
        bands[name]["classification:classes"] = classification_classes

    with open(bands_path, "w") as file:
        json.dump(bands, file, indent=4)

for directory, directories, file_names in os.walk(fragments_directory):
    if "item-properties.json" in file_names:
        os.rename(
            Path(directory) / "item-properties.json", Path(directory) / "item.json"
        )

for directory, directories, file_names in os.walk(fragments_directory):
    if "bands.json" not in file_names:
        continue
    bands_path = Path(directory) / "bands.json"
    print(f"Processing {bands_path}")
    with open(bands_path) as file:
        bands = json.load(file)
    for name, band in bands.items():
        if "name" in band:
            bands[name]["title"] = bands[name].pop("name")
    with open(bands_path, "w") as file:
        json.dump(bands, file, indent=4)
