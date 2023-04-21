import strawberry
from ..pydantic.package_collection import BasePackageCollection
from typing import List
from .package import Package


@strawberry.experimental.pydantic.type(model=BasePackageCollection)
class PackageCollection:
    """A Strawberry model representing a single package collection."""

    name: strawberry.auto
    packages: List[Package]
    id: strawberry.ID