"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import os
import uuid
from dataclasses import dataclass
from typing import Iterable, Optional

import strawberry

from softpack_core.artifacts import Artifacts
from softpack_core.schemas.base import BaseSchema
from softpack_core.spack import Spack


@strawberry.type
class Package(Spack.Package):
    """A Strawberry model representing a package."""

    version: Optional[str] = None


@strawberry.type
class Environment:
    """A Strawberry model representing a single environment."""

    id: str
    name: str
    path: str
    description: str
    packages: list[Package]
    artifacts = Artifacts()

    @classmethod
    def iter(cls, all: bool = False) -> Iterable["Environment"]:
        """Get an iterator over Environment objects.

        Returns:
            Iterable[Environment]: An iterator of Environment objects.
        """
        user = None
        if not user:
            # TODO: set username from the environment for now
            # eventually this needs to be the name of the authenticated user
            user = os.environ["USER"]
        environments = cls.artifacts.iter(user=user)
        return map(cls.from_artifact, environments)

    @classmethod
    def from_artifact(cls, obj: Artifacts.Object) -> "Environment":
        """Create an Environment object from an artifact.

        Args:
            obj: An artifact object.

        Returns:
            Environment: An Environment object.
        """
        spec = obj.spec()
        return Environment(
            id=obj.oid,
            name=obj.name,
            path=obj.path.parent,
            description=spec.description,
            packages=map(
                lambda package: Package(id=package, name=package),
                spec.packages,
            ),  # type: ignore [call-arg]
        )

    @classmethod
    def create(cls, name: str) -> "Environment":
        """Create an Environment object.

        Args:
            name: Name for an environment.

        Returns:
            Environment: A newly created Environment.
        """
        return Environment(
            id=uuid.uuid4().hex,
            name=name,
            packges=[Package(id="unknown", name="unknown-package")],
        )  # type: ignore [call-arg]


class EnvironmentSchema(BaseSchema):
    """Environment schema."""

    @dataclass
    class Query:
        """GraphQL query schema."""

        environments: list[Environment] = Environment.iter  # type: ignore

    @dataclass
    class Mutation:
        """GraphQL mutation schema."""

        createEnvironment: Environment = Environment.create  # type: ignore
