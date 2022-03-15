from typing import List

from stactools.modis.fragments import Fragments


class Product:
    """A MODIS product, e.g. MOD21A2."""

    product: str
    platforms: List[str]
    collection: str

    def __init__(self, product: str):
        """Creates a new product from the product string."""
        if product.startswith("MCD"):
            self.platforms = ["terra", "aqua"]
        elif product.startswith("MOD"):
            self.platforms = ["terra"]
        elif product.startswith("MYD"):
            self.platforms = ["aqua"]
        else:
            raise ValueError(
                f"Invalid product (should start with MCD, MOD, or MYD): {product}"
            )
        self.collection = product[3:]
        self.product = product

    def fragments(self, version: str) -> Fragments:
        """Returns the fragments for this product for the provided version."""
        return Fragments(self.collection, version)

    def collection_id(self, version: str) -> str:
        """Returns the collection id for this product and version combination."""
        return f"modis-{self.collection}-{version}"

    def __str__(self) -> str:
        return self.product
