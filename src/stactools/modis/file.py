import os.path


class File:
    """A MODIS file."""

    href: str
    hdf_href: str
    xml_href: str
    product: str
    version: str
    id: str

    def __init__(self, href: str):
        """Creates a new MODIS file from an href.

        Args:
            href (str): The .hdf or .hdf.xml href to MODIS data
        """
        base, extension = os.path.splitext(href)
        if extension not in [".hdf", ".xml"]:
            raise ValueError(f"Invalid MODIS href: {href}")
        elif extension == ".xml":
            if os.path.splitext(base)[1] != ".hdf":
                raise ValueError(
                    f"Invalid MODIS metadata href (no .hdf.xml): {href}")
            else:
                self.xml_href = href
                self.hdf_href = base
        else:
            self.xml_href = f"{href}.xml"
            self.hdf_href = href
        self.href = href
        file_name = os.path.basename(self.hdf_href)
        parts = file_name.split(".")
        if len(parts) < 4:
            raise ValueError(
                f"Invalid MODIS file name (not enough '.'-separated parts): {file_name}"
            )
        self.product = parts[0]
        self.version = parts[3]
        self.id = os.path.splitext(file_name)[0]
