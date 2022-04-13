#!/usr/bin/env python
# type: ignore

import os
import sys

from azure.storage.blob import BlobServiceClient

EXTERNAL_DATA_FILE_NAMES = [
    "MCD15A2H.A2022025.h01v11.061.2022035062702.hdf",
    "MCD15A3H.A2022033.h12v10.061.2022039062215.hdf",
    "MCD43A4.A2022032.h14v10.061.2022041051831.hdf",
    "MCD64A1.A2021335.h10v06.061.2022035055453.hdf",
    "MOD09A1.A2022033.h19v10.061.2022042043514.hdf",
    "MOD09Q1.A2022033.h10v10.061.2022042044048.hdf",
    "MOD10A1.A2022040.h11v05.061.2022042042026.hdf",
    "MOD10A2.A2022033.h09v05.061.2022042050729.hdf",
    "MOD11A1.A2022041.h19v02.061.2022042095544.hdf",
    "MOD11A2.A2022033.h19v10.061.2022042044121.hdf",
    "MOD13A1.A2022017.h12v11.061.2022034232214.hdf",
    "MOD13Q1.A2022017.h12v11.061.2022034232400.hdf",
    "MOD14A1.A2022033.h11v05.061.2022041234759.hdf",
    "MOD14A2.A2022033.h21v05.061.2022041234800.hdf",
    "MOD15A2H.A2022033.h13v10.061.2022042045937.hdf",
    "MOD16A3GF.A2021001.h11v02.061.2022024075208.hdf",
    "MOD17A2H.A2022025.h08v05.061.2022035065002.hdf",
    "MOD17A2HGF.A2021361.h10v06.061.2022020134637.hdf",
    "MOD17A3HGF.A2021001.h14v02.061.2022020135800.hdf",
    "MOD21A2.A2022033.h12v08.061.2022042050733.hdf",
    "MYD09A1.A2022025.h09v08.061.2022035070021.hdf",
    "MYD09Q1.A2022025.h02v08.061.2022035050917.hdf",
    "MYD10A1.A2022043.h21v04.061.2022045035657.hdf",
    "MYD10A2.A2022025.h10v05.061.2022035071201.hdf",
    "MYD11A1.A2022039.h21v07.061.2022040192419.hdf",
    "MYD11A2.A2022025.h17v00.061.2022035054130.hdf",
    "MYD13A1.A2022009.h25v02.061.2022028071925.hdf",
    "MYD13Q1.A2022009.h09v06.061.2022028072010.hdf",
    "MYD14A1.A2022025.h01v07.061.2022035001141.hdf",
    "MYD14A2.A2022025.h03v09.061.2022035001140.hdf",
    "MYD15A2H.A2022025.h22v08.061.2022035072026.hdf",
    "MYD16A3GF.A2021001.h11v02.061.2022024220526.hdf",
    "MYD17A2H.A2022025.h22v08.061.2022035120601.hdf",
    "MYD17A2HGF.A2021361.h13v09.061.2022021010829.hdf",
    "MYD17A3HGF.A2021001.h13v09.061.2022021012736.hdf",
    "MYD21A2.A2022025.h10v06.061.2022035072054.hdf",
]

sas = sys.argv[1]
outdir = sys.argv[2]
os.makedirs(outdir, exist_ok=True)
account_client = BlobServiceClient(
    "https://modiseuwest.blob.core.windows.net", credential=sas
)
container_client = account_client.get_container_client("modis-061")


def download(path: str) -> None:
    outpath = os.path.join(outdir, os.path.basename(path))
    if os.path.exists(outpath):
        print(f"Skipping {path}, already downloaded")
        return
    print(f"Downloading {path}")
    blob = container_client.get_blob_client(path)
    with open(outpath, "wb") as outfile:
        stream = blob.download_blob()
        outfile.write(stream.readall())


for file_name in EXTERNAL_DATA_FILE_NAMES:
    parts = file_name.split(".")
    product = parts[0]
    date = parts[1][1:]
    horizontal = parts[2][1:3]
    vertical = parts[2][4:6]
    hdf_path = f"{product}/{horizontal}/{vertical}/{date}/{file_name}"
    xml_path = f"{hdf_path}.xml"
    download(xml_path)
    download(hdf_path)
