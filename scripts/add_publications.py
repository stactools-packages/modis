"""Add publications to collections."""

import json
import requests
import os
import urllib.parse
from pathlib import Path

fragments_directory = Path(
    __file__).parents[1] / "src" / "stactools" / "modis" / "fragments"

for directory, directories, file_names in os.walk(fragments_directory):
    if "collection.json" not in file_names:
        continue
    collection_path = Path(directory) / "collection.json"
    print(f"Processing {collection_path}")
    with open(collection_path) as file:
        collection = json.load(file)
    publications = []
    for link in collection["links"]:
        if link["rel"] == "cite-as":
            url = urllib.parse.urlparse(link["href"])
            response = requests.get(
                link["href"],
                headers={"Accept": "text/x-bibliography; style=apa"})
            publications.append({
                "doi": url.path[1:],
                "citation": response.text,
            })
    if publications:
        collection["sci:publications"] = publications
    with open(collection_path, "w") as file:
        json.dump(collection, file, indent=4)
