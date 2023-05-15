"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import strawberry

from ..pydantic.package_collection import BasePackageCollection
from .package import Package


@strawberry.experimental.pydantic.type(model=BasePackageCollection)
class PackageCollection:
    """A Strawberry model representing a single package collection."""

    name: strawberry.auto
    packages: list[Package]
    id: strawberry.ID
