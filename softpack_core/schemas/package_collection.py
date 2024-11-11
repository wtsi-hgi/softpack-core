"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""


from dataclasses import dataclass

from softpack_core.app import app
from softpack_core.spack import Package


@dataclass
class PackageMultiVersion(Package):
    """A data class representing a package in a collection."""


@dataclass
class PackageCollection:
    """A data class representing a package collection."""

    name: str
    packages: list[PackageMultiVersion]

    @classmethod
    def iter(cls) -> list["PackageMultiVersion"]:
        """Get an iterator over PackageCollection objects.

        Returns:
            Iterable[PackageCollection]: An iterator of PackageCollection
            objects.
        """
        if app.spack.packagesUpdated:
            cls.packages = list(map(cls.from_package, app.spack.packages()))
            app.spack.packagesUpdated = False

        return cls.packages

    @classmethod
    def from_package(cls, package: Package) -> PackageMultiVersion:
        """Create a PackageMultiVersion object.

        Args:
            package: A Spack.Package

        Returns:
            PackageMultiVersion: A Spack package with multiple versions.

        """
        return PackageMultiVersion(
            name=package.name, versions=package.versions
        )  # type: ignore [call-arg]
