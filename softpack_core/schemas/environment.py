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
        # Check if any field has been left empty
        if any(len(value) == 0 for value in vars(env).values()):
            return InvalidInputError(message="all fields must be filled in")
        # Check if a valid path has been provided
        user = os.environ["USER"]
        if env.path not in ["groups/hgi", f"users/{user}"]:
            return InvalidInputError(message="Invalid path")
        # Check if an env with same name already exists at given path
        if cls.artifacts.get(Path(env.path), env.name):
            return EnvironmentAlreadyExistsError(message="An environment of this name already exists in this location", path=env.path, name=env.name)

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
            name=env.name,
            path=env.path,
            description=env.description,
            packages=list(map(lambda pkg: pkg.to_package(), env.packages)),
            state=response['state']['type'],
        )  # type: ignore [call-arg]

        try:
            cls.artifacts.create_environment(
                cls.artifacts.repo,
                new_env,
                "create new environment",
            )
        except RuntimeError as e:
            return InvalidInputError(message=str(e))
        
        return CreateEnvironmentSuccess(message="Successfully scheduled environment creation", environment=new_env)

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
        # Check if any field has been left empty
        if any(len(value) == 0 for value in vars(env).values()) or current_name == "" or current_path == "":
            return InvalidInputError(message="all fields must be filled in")
        # Check if an environment exists at the specified path and name
        if cls.artifacts.get(Path(current_path), current_name):
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

            try:
                cls.artifacts.update_environment(
                    new_env, current_name, current_path
                )
            except RuntimeError as e:
                return InvalidInputError(message=str(e))

            return UpdateEnvironmentSuccess(message="Successfully updated environment", environment=new_env)

        return EnvironmentNotFoundError(message="Unable to find an environment of this name in this location", path=current_path, name=current_name)

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


# Interfaces
@strawberry.interface
class Success:
    """Interface for successful results."""

    message: str

@strawberry.interface
class Error:
    """Interface for errors."""

    message: str


# Success types
@strawberry.type
class CreateEnvironmentSuccess(Success):
    """Environment successfully scheduled."""

    message: str
    environment: Environment

@strawberry.type
class UpdateEnvironmentSuccess(Success):
    """Environment successfully updated."""

    message: str
    environment: Environment


# Error types
@strawberry.type
class InvalidInputError(Error):
    """Invalid input data"""

    message: str

@strawberry.type
class EnvironmentNotFoundError(Error):
    """Environment not found."""

    message: str
    path: str
    name: str

@strawberry.type
class EnvironmentAlreadyExistsError(Error):
    """Environment name already exists."""

    message:str
    path: str
    name: str


CreateResponse = strawberry.union(
    "CreateResponse", [CreateEnvironmentSuccess,
                       InvalidInputError,
                       EnvironmentAlreadyExistsError,
                        ]
)

UpdateResponse = strawberry.union(
    "UpdateResponse", [UpdateEnvironmentSuccess,
                       InvalidInputError,
                       EnvironmentNotFoundError,
                        ]
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

        createEnvironment: CreateResponse = Environment.create  # type: ignore
        updateEnvironment: UpdateResponse = Environment.update  # type: ignore
        deleteEnvironment: str = Environment.delete  # type: ignore
        upload_file: str = Environment.upload_file  # type: ignore
