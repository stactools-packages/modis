import pytest

from stactools.modis.file import File

from . import test_data


def test_file() -> None:
    href = test_data.get_path(
        "data-files/MCD12Q1.A2001001.h00v08.006.2018142182903.hdf.xml")
    file = File(href)
    assert file.href == href
    assert file.hdf_href == test_data.get_path(
        "data-files/MCD12Q1.A2001001.h00v08.006.2018142182903.hdf")
    assert file.xml_href == href
    assert file.version == "006"
    assert str(file.product) == "MCD12Q1"
    assert file.id == "MCD12Q1.A2001001.h00v08.006.2018142182903"

    href = test_data.get_path(
        "data-files/MCD12Q1.A2001001.h00v08.006.2018142182903.hdf")
    file = File(href)
    assert file.xml_href == test_data.get_path(
        "data-files/MCD12Q1.A2001001.h00v08.006.2018142182903.hdf.xml")
    assert file.hdf_href == href

    with pytest.raises(ValueError):
        File("not cool")
    with pytest.raises(ValueError):
        File("metadata.xml")
    with pytest.raises(ValueError):
        File("not-enough-dots.hdf.xml")

    url = "http://example.com/MCD12Q1.A2001001.h00v08.006.2018142182903.hdf.xml"
    file = File(url)
    assert file.xml_href == url
    assert file.hdf_href == "http://example.com/MCD12Q1.A2001001.h00v08.006.2018142182903.hdf"
