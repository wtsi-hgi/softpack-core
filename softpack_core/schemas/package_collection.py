"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from dataclasses import dataclass
from typing import Iterable

import strawberry

from softpack_core.app import app
from softpack_core.spack import Package


@strawberry.type
class PackageMultiVersion(Package):
    """A Strawberry model representing a package in a collection."""


@strawberry.type
class PackageCollection:
    """A Strawberry model representing a package collection."""

    name: str
    packages: list[PackageMultiVersion]

    @classmethod
    def iter(cls) -> Iterable["PackageMultiVersion"]:
        """Get an iterator over PackageCollection objects.

        Returns:
            Iterable[PackageCollection]: An iterator of PackageCollection
            objects.
        """
        return map(cls.from_package, app.spack.packages())

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


class PackageCollectionSchema:
    """Package collection schema."""

    @dataclass
    class Query:
        """GraphQL query schema."""

        packageCollections: list[
            PackageMultiVersion
        ] = PackageCollection.iter  # type: ignore
