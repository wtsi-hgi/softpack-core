"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from .schemas.package import Package


class Packages:
    """Packages."""

    def get(self) -> list[Package]:
        """Get all packages.

        Returns:
            a list of package objects
        """
        pkgs = [
            Package(
                name="Python",
                version="3.10",
            ),
            Package(
                name="R",
                version="3.4.0",
            ),
        ]
        return pkgs
