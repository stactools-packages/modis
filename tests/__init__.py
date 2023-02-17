from typing import Any, Dict

from stactools.testing.test_data import TestData

MICROSOFT_EXTERNAL_DATA_FILE_NAMES = [
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
    "MYD11A2.A2022025.h17v00.061.2022035054130.hdf",
    "MYD13A1.A2022009.h25v02.061.2022028071925.hdf",
    "MYD14A1.A2022025.h01v07.061.2022035001141.hdf",
    "MCD15A2H.A2022025.h01v11.061.2022035062702.hdf",
    "MYD16A3GF.A2021001.h11v02.061.2022024220526.hdf",
]

ASTRAEA_EXTERNAL_FILE_NAMES = {
    "43A4": {
        "prefix": "s3://astraea-opendata/MCD43A4.006/28/08/2022073/",
        "file_names": [
            "MCD43A4.A2022073.h28v08.006.2022082044758_B01.TIF",
            "MCD43A4.A2022073.h28v08.006.2022082044758_B01qa.TIF",
            "MCD43A4.A2022073.h28v08.006.2022082044758_B02.TIF",
            "MCD43A4.A2022073.h28v08.006.2022082044758_B02qa.TIF",
            "MCD43A4.A2022073.h28v08.006.2022082044758_B03.TIF",
            "MCD43A4.A2022073.h28v08.006.2022082044758_B03qa.TIF",
            "MCD43A4.A2022073.h28v08.006.2022082044758_B04.TIF",
            "MCD43A4.A2022073.h28v08.006.2022082044758_B04qa.TIF",
            "MCD43A4.A2022073.h28v08.006.2022082044758_B05.TIF",
            "MCD43A4.A2022073.h28v08.006.2022082044758_B05qa.TIF",
            "MCD43A4.A2022073.h28v08.006.2022082044758_B06.TIF",
            "MCD43A4.A2022073.h28v08.006.2022082044758_B06qa.TIF",
            "MCD43A4.A2022073.h28v08.006.2022082044758_B07.TIF",
            "MCD43A4.A2022073.h28v08.006.2022082044758_B07qa.TIF",
        ],
    },
    "11A1": {
        "prefix": "s3://astraea-opendata/MOD11A1.006/09/05/2022103/",
        "file_names": [
            "MOD11A1.A2022103.h09v05.006.2022104093154_CDC_B11.TIF",
            "MOD11A1.A2022103.h09v05.006.2022104093154_CNC_B12.TIF",
            "MOD11A1.A2022103.h09v05.006.2022104093154_DVA_B04.TIF",
            "MOD11A1.A2022103.h09v05.006.2022104093154_DVT_B03.TIF",
            "MOD11A1.A2022103.h09v05.006.2022104093154_E31_B09.TIF",
            "MOD11A1.A2022103.h09v05.006.2022104093154_E32_B10.TIF",
            "MOD11A1.A2022103.h09v05.006.2022104093154_LSTD_B01.TIF",
            "MOD11A1.A2022103.h09v05.006.2022104093154_LSTN_B05.TIF",
            "MOD11A1.A2022103.h09v05.006.2022104093154_NVA_B08.TIF",
            "MOD11A1.A2022103.h09v05.006.2022104093154_NVT_B07.TIF",
            "MOD11A1.A2022103.h09v05.006.2022104093154_QCD_B02.TIF",
            "MOD11A1.A2022103.h09v05.006.2022104093154_QCN_B06.TIF",
        ],
    },
    "13A1": {
        "prefix": "s3://astraea-opendata/MOD13A1.006/09/05/2022081/",
        "file_names": [
            "MOD13A1.A2022081.h09v05.006.2022101145817_BR_B06.TIF",
            "MOD13A1.A2022081.h09v05.006.2022101145817_CDOY_B11.TIF",
            "MOD13A1.A2022081.h09v05.006.2022101145817_EVI_B02.TIF",
            "MOD13A1.A2022081.h09v05.006.2022101145817_MIRR_B07.TIF",
            "MOD13A1.A2022081.h09v05.006.2022101145817_NDVI_B01.TIF",
            "MOD13A1.A2022081.h09v05.006.2022101145817_NIRR_B05.TIF",
            "MOD13A1.A2022081.h09v05.006.2022101145817_PR_B12.TIF",
            "MOD13A1.A2022081.h09v05.006.2022101145817_RAA_B10.TIF",
            "MOD13A1.A2022081.h09v05.006.2022101145817_RR_B04.TIF",
            "MOD13A1.A2022081.h09v05.006.2022101145817_SZA_B09.TIF",
            "MOD13A1.A2022081.h09v05.006.2022101145817_VIQ_B03.TIF",
            "MOD13A1.A2022081.h09v05.006.2022101145817_VZA_B08.TIF",
        ],
    },
}


def create_external_data_dict() -> Dict[str, Dict[str, Any]]:
    external_data: Dict[str, Dict[str, Any]] = dict()
    for file_name in MICROSOFT_EXTERNAL_DATA_FILE_NAMES:
        external_data[file_name] = {
            "url": "https://ai4epublictestdata.blob.core.windows.net/stactools/modis"
            f"/{file_name}"
        }
        external_data[f"{file_name}.xml"] = {
            "url": "https://ai4epublictestdata.blob.core.windows.net/stactools/modis"
            f"/{file_name}.xml"
        }

    for values in ASTRAEA_EXTERNAL_FILE_NAMES.values():
        prefix = values["prefix"]
        for file_name in values["file_names"]:
            external_data[file_name] = {
                "url": f"{prefix}{file_name}",
                "s3": {"requester_pays": True},
            }

    return external_data


external_data = create_external_data_dict()

test_data = TestData(__file__, external_data=external_data)
