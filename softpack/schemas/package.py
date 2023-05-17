"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from typing import Optional

import strawberry


@strawberry.type
class Package:
    """A Strawberry model representing a single package."""

    name: str
    version: Optional[str] = None


@strawberry.input
class PackageInput(Package):
    """GraphQL input type for Package."""

    def create_instance(self) -> Package:
        """Create a Package instance from a PackageInput instance.

        Returns:
            a Package object
        """
        return Package(**self.__dict__)
