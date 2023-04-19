import strawberry
from ..pydantic.package import BasePackage


@strawberry.experimental.pydantic.type(model=BasePackage)
class Package:
    """A Strawberry model representing a single package."""

    name: strawberry.auto
    version: strawberry.auto