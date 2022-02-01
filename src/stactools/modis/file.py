import os.path


class File:
    """A MODIS file."""

    path: str
    hdf_path: str
    xml_path: str
    product: str
    version: str
    catalog_id: str
    id: str

    def __init__(self, path: str):
        """Creates a new MODIS file from a path."""
        base, extension = os.path.splitext(path)
        if extension not in [".hdf", ".xml"]:
            raise ValueError(f"Invalid MODIS path: {path}")
        elif extension == ".xml":
            if os.path.splitext(base)[1] != ".hdf":
                raise ValueError(
                    f"Invalid MODIS metadata path (no .hdf.xml): {path}")
            else:
                self.xml_path = path
                self.hdf_path = base
        else:
            self.xml_path = f"{path}.xml"
            self.hdf_path = path
        self.path = path
        file_name = os.path.basename(self.hdf_path)
        parts = file_name.split(".")
        if len(parts) < 4:
            raise ValueError(
                f"Invalid MODIS file name (not enough '.'-separated parts): {file_name}"
            )
        self.product = parts[0]
        self.version = parts[3]
        self.catalog_id = f"MODIS/{self.version}/{self.product}"
        self.id = os.path.splitext(file_name)[0]
