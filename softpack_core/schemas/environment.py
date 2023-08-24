"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import httpx
import strawberry
from strawberry.file_uploads import Upload

from softpack_core.artifacts import Artifacts
from softpack_core.schemas.base import BaseSchema
from softpack_core.spack import Spack


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


@strawberry.type
class UpdateEnvironmentSuccess(Success):
    """Environment successfully updated."""

    message: str


@strawberry.type
class DeleteEnvironmentSuccess(Success):
    """Environment successfully deleted."""

    message: str


@strawberry.type
class WriteArtifactSuccess(Success):
    """Artifact successfully created."""

    message: str
    commit_oid: str


# Error types
@strawberry.type
class InvalidInputError(Error):
    """Invalid input data."""

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

    message: str
    path: str
    name: str


# Unions
CreateResponse = strawberry.union(
    "CreateResponse",
    [
        CreateEnvironmentSuccess,
        InvalidInputError,
        EnvironmentAlreadyExistsError,
    ],
)

UpdateResponse = strawberry.union(
    "UpdateResponse",
    [
        UpdateEnvironmentSuccess,
        InvalidInputError,
        EnvironmentNotFoundError,
        EnvironmentAlreadyExistsError,
    ],
)

DeleteResponse = strawberry.union(
    "DeleteResponse",
    [
        DeleteEnvironmentSuccess,
        EnvironmentNotFoundError,
    ],
)

WriteArtifactResponse = strawberry.union(
    "WriteArtifactResponse",
    [
        WriteArtifactSuccess,
        InvalidInputError,
    ],
)


@strawberry.type
class Package(Spack.PackageBase):
    """A Strawberry model representing a package."""

    version: Optional[str] = None


@strawberry.input
class PackageInput(Package):
    """A Strawberry input model representing a package."""

    id: Optional[str] = None

    def to_package(self) -> Package:
        """Create a Package object from a PackageInput object.

        Return: a Package object
        """
        return Package(**vars(self))


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
    def iter(cls) -> Iterable["Environment"]:
        """Get an iterator over all Environment objects.

        Returns:
            Iterable[Environment]: An iterator of Environment objects.
        """
        environment_folders = cls.artifacts.iter()
        environment_objects = map(cls.from_artifact, environment_folders)
        return filter(lambda x: x is not None, environment_objects)

    @classmethod
    def from_artifact(cls, obj: Artifacts.Object) -> Optional["Environment"]:
        """Create an Environment object from an artifact.

        Args:
            obj: An artifact object.

        Returns:
            Environment: An Environment object.
        """
        try:
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
        except KeyError:
            return None

    @classmethod
    def create(cls, env: EnvironmentInput) -> CreateResponse:
        """Create an Environment.

        Args:
            env: Details of the new environment

        Returns:
            A message confirming the success or failure of the operation.
        """
        # Check if any field has been left empty
        if any(len(value) == 0 for value in vars(env).values()):
            return InvalidInputError(message="all fields must be filled in")

        # Check if a valid path has been provided. TODO: improve this to check
        # that they can only create stuff in their own users folder, or in
        # group folders of unix groups they belong to.
        valid_dirs = [
            cls.artifacts.users_folder_name,
            cls.artifacts.groups_folder_name,
        ]
        if not any(env.path.startswith(dir) for dir in valid_dirs):
            return InvalidInputError(message="Invalid path")

        # Check if an env with same name already exists at given path
        if cls.artifacts.get(Path(env.path), env.name):
            return EnvironmentAlreadyExistsError(
                message="This name is already used in this location",
                path=env.path,
                name=env.name,
            )

        # Create folder with place-holder file
        new_folder_path = Path(env.path, env.name)
        file_name = ".created"
        try:
            tree_oid = cls.artifacts.create_file(
                new_folder_path, file_name, "", True
            )
            cls.artifacts.commit(tree_oid, "create environment folder")
            cls.artifacts.push()
        except RuntimeError as e:
            return InvalidInputError(message=str(e))

        # Send build request
        httpx.post(
            "http://0.0.0.0:7080/environments/build",
            json={
                "name": f"{env.path}/{env.name}",
                "model": {
                    "description": env.description,
                    "packages": [f"{pkg.name}" for pkg in env.packages],
                },
            },
        )

        return CreateEnvironmentSuccess(
            message="Successfully scheduled environment creation"
        )

    @classmethod
    def update(
        cls,
        env: EnvironmentInput,
        current_path: str,
        current_name: str,
    ) -> UpdateResponse:
        """Update an Environment.

        Args:
            env: Details of the updated environment
            path: The path of the current environment
            name: The name of the current environment

        Returns:
            A message confirming the success or failure of the operation.
        """
        # Check if any field has been left empty
        if (
            any(len(value) == 0 for value in vars(env).values())
            or current_name == ""
            or current_path == ""
        ):
            return InvalidInputError(message="all fields must be filled in")

        # Check name and path have not been changed.
        if env.path != current_path or env.name != current_name:
            return InvalidInputError(
                message=("change of name or path not " "currently supported")
            )

        # Check if an environment exists at the specified path and name
        if cls.artifacts.get(Path(current_path), current_name):
            httpx.post(
                "http://0.0.0.0:7080/environments/build",
                json={
                    "name": f"{env.path}/{env.name}",
                    "model": {
                        "description": env.description,
                        "packages": [pkg.name for pkg in env.packages or []],
                    },
                },
            )

            return UpdateEnvironmentSuccess(
                message="Successfully updated environment"
            )

        return EnvironmentNotFoundError(
            message="No environment with this name found in this location.",
            path=current_path,
            name=current_name,
        )

    @classmethod
    def delete(cls, name: str, path: str) -> DeleteResponse:
        """Delete an Environment.

        Args:
            name: the name of of environment
            path: the path of the environment

        Returns:
            A message confirming the success or failure of the operation.
        """
        if cls.artifacts.get(Path(path), name):
            tree_oid = cls.artifacts.delete_environment(name, path)
            cls.artifacts.commit(tree_oid, "delete environment")
            cls.artifacts.push()
            return DeleteEnvironmentSuccess(
                message="Successfully deleted the environment"
            )

        return EnvironmentNotFoundError(
            message="No environment with this name found in this location.",
            path=path,
            name=name,
        )

    @classmethod
    async def write_artifact(
        cls, file: Upload, folder_path: str, file_name: str
    ) -> WriteArtifactResponse:
        """Add a file to the Artifacts repo.

        Args:
            file: the file to add to the repo
            folder_path: the path to the folder that the file will be added to
            file_name: the name of the file
        """
        try:
            contents = (await file.read()).decode()
            tree_oid = cls.artifacts.create_file(
                Path(folder_path), file_name, contents, overwrite=True
            )
            commit_oid = cls.artifacts.commit(tree_oid, "write artifact")
            cls.artifacts.push()
            return WriteArtifactSuccess(
                message="Successfully written artifact",
                commit_oid=str(commit_oid),
            )

        except Exception as e:
            return InvalidInputError(message=str(e))


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
        deleteEnvironment: DeleteResponse = Environment.delete  # type: ignore
        writeArtifact: WriteArtifactResponse = (
            Environment.write_artifact
        )  # type: ignore
