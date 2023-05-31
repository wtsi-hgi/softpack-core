"""Copyright (c) 2023 Genome Research Ltd.

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
class Package(Spack.PackageBase):
    """A Strawberry model representing a package."""

    version: Optional[str] = None

@strawberry.input
class PackageInput(Package):
    """A Strawberry input model representing a pacakge."""

    def to_package(self):
        """Create a Package object from a PackageInput object.
        
        Return: a Package object
        """
        return Package(**self.__dict__)

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
        for env in Environment.iter():
            if name == env.name:
                return EnvironmentAlreadyExistsError(**env.__dict__)
        return Environment(
            id=uuid.uuid4().hex,
            name=name,
            path="users/username",
            description="description",
            packages=[Package(id="unknown", name="unknown-package")],
        )  # type: ignore [call-arg]

    @classmethod
    def update(cls, name: str, path: Optional[str]=None, description: Optional[str]=None, packages: Optional[list[PackageInput]]=None):
        for env in Environment.iter():
            if env.name == name:
                if path != None:
                    env.path = path
                if description != None:
                    env.description = description
                if packages != None:
                    env.packages = map(lambda pkg: pkg.to_package(), packages)
                return env
            return EnvironmentNotFoundError(name=name)
    
    @classmethod
    def delete(cls, name: str):
        for env in Environment.iter():
            if env.name == name:
                return f"Deleted {name}"
        return "An environment with that name was not found"
    
#Error types
@strawberry.type
class EnvironmentNotFoundError:
    """Environment not found"""
    name: str

@strawberry.type
class EnvironmentAlreadyExistsError(Environment):
    """Environment name already exists"""

UpdateEnvironmentResponse = strawberry.union("UpdateEnvironmentResponse", [Environment, EnvironmentNotFoundError])
CreateEnvironmentResponse = strawberry.union("CreateEnvironmentResponse", [Environment, EnvironmentAlreadyExistsError])

class EnvironmentSchema(BaseSchema):
    """Environment schema."""

    @dataclass
    class Query:
        """GraphQL query schema."""

        environments: list[Environment] = Environment.iter  # type: ignore

    @dataclass
    class Mutation:
        """GraphQL mutation schema."""

        createEnvironment: CreateEnvironmentResponse = Environment.create  # type: ignore
        updateEnvironment: UpdateEnvironmentResponse = Environment.update  # type: ignore
        deleteEnvironment: str = Environment.delete # type: ignore
