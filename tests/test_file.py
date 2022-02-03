import pytest

from stactools.modis.file import File

from . import test_data


def test_file() -> None:
    path = test_data.get_path(
        "data-files/MCD12Q1.A2001001.h00v08.006.2018142182903.hdf.xml")
    file = File(path)
    assert file.path == path
    assert file.hdf_path == test_data.get_path(
        "data-files/MCD12Q1.A2001001.h00v08.006.2018142182903.hdf")
    assert file.xml_path == path
    assert file.version == "006"
    assert file.product == "MCD12Q1"
    assert file.id == "MCD12Q1.A2001001.h00v08.006.2018142182903"

    path = test_data.get_path(
        "data-files/MCD12Q1.A2001001.h00v08.006.2018142182903.hdf")
    file = File(path)
    assert file.xml_path == test_data.get_path(
        "data-files/MCD12Q1.A2001001.h00v08.006.2018142182903.hdf.xml")
    assert file.hdf_path == path

    with pytest.raises(ValueError):
        File("not cool")
    with pytest.raises(ValueError):
        File("metadata.xml")
    with pytest.raises(ValueError):
        File("not-enough-dots.hdf.xml")

    url = "http://example.com/MCD12Q1.A2001001.h00v08.006.2018142182903.hdf.xml"
    file = File(url)
    assert file.xml_path == url
    assert file.hdf_path == "http://example.com/MCD12Q1.A2001001.h00v08.006.2018142182903.hdf"
