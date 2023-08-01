"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import httpx
import strawberry
from strawberry.file_uploads import Upload

from softpack_core.artifacts import Artifacts
from softpack_core.schemas.base import BaseSchema
from softpack_core.spack import Spack


@strawberry.type
class Package(Spack.PackageBase):
    """A Strawberry model representing a package."""

    version: Optional[str] = None


@strawberry.input
class PackageInput(Package):
    """A Strawberry input model representing a package."""

    id: Optional[str] = None

    def to_package(self):
        """Create a Package object from a PackageInput object.

        Return: a Package object
        """
        return Package(**self.__dict__)


@strawberry.input
class EnvironmentInput:
    """A Strawberry input model representing an environment."""

    name: str
    path: str
    description: str
    packages: list[PackageInput]


@strawberry.type
class Environment:
    """A Strawberry model representing a single environment."""

    id: str
    name: str
    path: str
    description: str
    packages: list[Package]
    state: Optional[str]
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
            state=None,
        )

    @classmethod
    def create(cls, env: EnvironmentInput):
        """Create an Environment object.

        Args:
            env: Details of the new environment

        Returns:
            Environment: A newly created Environment.
        """
        # Check if an env with same name already exists at given path
        if cls.artifacts.get(Path(env.path), env.name):
            return EnvironmentAlreadyExistsError(path=env.path, name=env.name)

        response = httpx.post(
            "http://0.0.0.0:7080/environments/build",
            json={
                "name": env.name,
                "model": {
                    "description": env.description,
                    "packages": [f"{pkg.name}" for pkg in env.packages],
                },
            },
        ).json()
        print(f"Create: {response}")
        new_env = Environment(
            id=uuid.uuid4().hex,
            name=response['name'],
            path=env.path,
            description=env.description,
            packages=list(map(lambda pkg: pkg.to_package(), env.packages)),
            state=response['state']['type'],
        )  # type: ignore [call-arg]

        cls.artifacts.create_environment(
            cls.artifacts.repo,
            new_env,
            "create new environment",
        )
        return new_env

    @classmethod
    def update(
        cls,
        env: EnvironmentInput,
        current_path: str,
        current_name: str,
    ):
        """Update an Environment object.

        Args:
            env: Details of the updated environment
            path: The path of the current environment
            name: The name of the current environment

        Returns:
            Environment: An updated Environment.
        """
        # Check if an environment exists at the specified path and name
        current_env = cls.artifacts.get(Path(current_path), current_name)
        print(current_env)
        if current_env:
            response = httpx.post(
                "http://0.0.0.0:7080/environments/build",
                json={
                    "name": env.name,
                    "model": {
                        "description": env.description,
                        "packages": [pkg.name for pkg in env.packages or []],
                    },
                },
            ).json()
            print(f"Update: {response}")

            new_env = Environment(
                id=uuid.uuid4().hex,
                name=env.name,
                path=env.path,
                description=env.description,
                packages=[pkg.to_package() for pkg in env.packages],
                state=response['state']['type'],
            )

            cls.artifacts.update_environment(
                new_env, current_name, current_path
            )
            return new_env

        return EnvironmentNotFoundError(name=env.name)

    @classmethod
    def delete(cls, name: str):
        """Delete an Environment object.

        Returns:
            A string confirming the deletion of the Environment
        """
        for env in Environment.iter():
            if env.name == name:
                return f"Deleted {name}"
        return "An environment with that name was not found"

    @classmethod
    async def upload_file(cls, file: Upload):
        return (await file.read()).decode("utf-8")  # type: ignore


# Error types
@strawberry.type
class EnvironmentNotFoundError:
    """Environment not found."""

    name: str


@strawberry.type
class EnvironmentAlreadyExistsError:
    """Environment name already exists."""

    path: str
    name: str


UpdateEnvironmentResponse = strawberry.union(
    "UpdateEnvironmentResponse", [Environment, EnvironmentNotFoundError]
)
CreateEnvironmentResponse = strawberry.union(
    "CreateEnvironmentResponse", [Environment, EnvironmentAlreadyExistsError]
)


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
        deleteEnvironment: str = Environment.delete  # type: ignore
        upload_file: str = Environment.upload_file  # type: ignore
