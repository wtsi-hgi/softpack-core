"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import strawberry

from ..pydantic.package import BasePackage


@strawberry.experimental.pydantic.type(model=BasePackage)
class Package:
    """A Strawberry model representing a single package."""

    name: strawberry.auto
    version: strawberry.auto
