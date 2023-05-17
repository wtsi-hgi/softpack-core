"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import strawberry

from .package import Package


@strawberry.type
class PackageCollection:
    """A Strawberry model representing a single package collection."""

    name: str
    packages: list[Package]
    id: strawberry.ID
