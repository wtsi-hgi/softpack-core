from pydantic import BaseModel

from .package import BasePackage


class BasePackageCollection(BaseModel):
    """A model representing a single package collection."""

    name: str
    packages: list[BasePackage]
    id: int
