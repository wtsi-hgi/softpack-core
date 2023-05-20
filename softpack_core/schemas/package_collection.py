"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from dataclasses import dataclass
from typing import Iterable
from uuid import UUID

import strawberry

from softpack_core.app import app
from softpack_core.spack import Spack


@strawberry.type
class PackageMultiVersion(Spack.Package):
    """A Strawberry model representing a package in a collection."""

    versions: list[str]


@strawberry.type
class PackageCollection:
    """A Strawberry model representing a package collection."""

    id: UUID
    name: str
    packages: list[PackageMultiVersion]

    @classmethod
    def iter(cls) -> Iterable["PackageCollection"]:
        return map(cls.from_collection, app.spack.collections)

    @classmethod
    def from_collection(
        cls, collection: Spack.Collection
    ) -> "PackageCollection":
        return PackageCollection(
            id=collection.id,
            name=collection.name,
            packages=map(cls.from_package, collection.packages[:3]),
        )  # type: ignore [call-arg]

    @classmethod
    def from_package(cls, package: Spack.Package) -> PackageMultiVersion:
        return PackageMultiVersion(
            id=package.id, name=package.name, versions=["latest"]
        )  # type: ignore [call-arg]


class PackageCollectionSchema:
    @dataclass
    class Query:
        packaageCollections: list[
            PackageCollection
        ] = PackageCollection.iter  # type: ignore
