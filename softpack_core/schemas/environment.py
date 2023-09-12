"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Union

import httpx
import strawberry
from starlette.datastructures import UploadFile
from strawberry.file_uploads import Upload

from softpack_core.artifacts import Artifacts, Package, State
from softpack_core.module import GenerateEnvReadme, ToSoftpackYML
from softpack_core.schemas.base import BaseSchema


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


@strawberry.type
class UpdateEnvironmentSuccess(Success):
    """Environment successfully updated."""


@strawberry.type
class DeleteEnvironmentSuccess(Success):
    """Environment successfully deleted."""


@strawberry.type
class WriteArtifactSuccess(Success):
    """Artifact successfully created."""

    commit_oid: str


# Error types
@strawberry.type
class InvalidInputError(Error):
    """Invalid input data."""


@strawberry.type
class EnvironmentNotFoundError(Error):
    """Environment not found."""

    path: str
    name: str


@strawberry.type
class EnvironmentAlreadyExistsError(Error):
    """Environment name already exists."""

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


@strawberry.input
class PackageInput(Package):
    """A Strawberry input model representing a package."""

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

    def validate(cls) -> Union[None, InvalidInputError]:
        """Validate that all values have been supplied.

        Returns:
            None if good, or InvalidInputError if not all values supplied.
        """
        if any(len(value) == 0 for value in vars(cls).values()):
            return InvalidInputError(message="all fields must be filled in")

        return None

    @classmethod
    def from_path(cls, environment_path: str) -> 'EnvironmentInput':
        """from_path creates a new EnvironmentInput based on an env path.

        Args:
            environment_path (str): path of the environment.

        Returns:
            EnvironmentInput: a package-less, description-less
                              EnvironmentInput.
        """
        environment_dirs = environment_path.split("/")
        environment_name = environment_dirs.pop()

        return EnvironmentInput(
            name=environment_name,
            path="/".join(environment_dirs),
            description="",
            packages=list(),
        )


@strawberry.type
class Environment:
    """A Strawberry model representing a single environment."""

    id: str
    name: str
    path: str
    description: str
    readme: str
    type: str
    packages: list[Package]
    state: Optional[State]
    artifacts = Artifacts()

    @classmethod
    def iter(cls) -> Iterable["Environment"]:
        """Get an iterator over all Environment objects.

        Returns:
            Iterable[Environment]: An iterator of Environment objects.
        """
        environment_folders = cls.artifacts.iter()
        environment_objects = map(cls.from_artifact, environment_folders)
        return filter(None, environment_objects)

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
                path=str(obj.path.parent),
                description=spec.description,
                packages=spec.packages,
                state=spec.state,
                readme=spec.get("readme", ""),
                type=spec.get("type", ""),
            )
        except KeyError:
            return None

    @classmethod
    def create(cls, env: EnvironmentInput) -> CreateResponse:  # type: ignore
        """Create an Environment.

        Args:
            env: Details of the new environment

        Returns:
            A message confirming the success or failure of the operation.
        """
        result = env.validate()
        if result is not None:
            return result

        response = cls.create_new_env(env, Artifacts.built_by_softpack_file)
        if not isinstance(response, CreateEnvironmentSuccess):
            return response

        # TODO: remove hard-coding of URL.
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
    def create_new_env(
        cls, env: EnvironmentInput, env_type: str
    ) -> CreateResponse:  # type: ignore
        """Create a new environment in the repository.

        Adds an empty .created file in the desired location. Fails if this
        already exists.

        Args:
            env (EnvironmentInput): Details of the new environment. env_type
            (str): One of Artifacts.built_by_softpack_file or
            Artifacts.generated_from_module_file that denotes how the
            environment was made.

        Returns:
            CreateResponse: a CreateEnvironmentSuccess on success, or one of
            (InvalidInputError, EnvironmentAlreadyExistsError) on error.
        """
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
        try:
            tree_oid = cls.artifacts.create_file(
                new_folder_path, env_type, "", True
            )
            cls.artifacts.commit_and_push(
                tree_oid, "create environment folder"
            )
        except RuntimeError as e:
            return InvalidInputError(message=str(e))

        return CreateEnvironmentSuccess(
            message="Successfully created environment in artifacts repo"
        )

    @classmethod
    def update(
        cls,
        env: EnvironmentInput,
        current_path: str,
        current_name: str,
    ) -> UpdateResponse:  # type: ignore
        """Update an Environment.

        Args:
            env: Details of the updated environment
            path: The path of the current environment
            name: The name of the current environment

        Returns:
            A message confirming the success or failure of the operation.
        """
        result = env.validate()
        if result is not None:
            return result

        if current_name == "" or current_path == "":
            return InvalidInputError(message="current values must be supplied")

        if env.path != current_path or env.name != current_name:
            return InvalidInputError(
                message=("change of name or path not currently supported")
            )

        result2 = cls.check_env_exists(Path(current_path, current_name))
        if result2 is not None:
            return result2

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

        # TODO: validate the post worked

        return UpdateEnvironmentSuccess(
            message="Successfully updated environment"
        )

    @classmethod
    def check_env_exists(
        cls, path: Path
    ) -> Union[None, EnvironmentNotFoundError]:
        """check_env_exists checks if an env with the given path exists.

        Args:
            path (Path): path of the environment

        Returns:
            Union[None, EnvironmentNotFoundError]: an error if env not found.
        """
        if cls.artifacts.get(path.parent, path.name):
            return None

        return EnvironmentNotFoundError(
            message="No environment with this path and name found.",
            path=str(path.parent),
            name=path.name,
        )

    @classmethod
    def delete(cls, name: str, path: str) -> DeleteResponse:  # type: ignore
        """Delete an Environment.

        Args:
            name: the name of of environment
            path: the path of the environment

        Returns:
            A message confirming the success or failure of the operation.
        """
        if cls.artifacts.get(Path(path), name):
            tree_oid = cls.artifacts.delete_environment(name, path)
            cls.artifacts.commit_and_push(tree_oid, "delete environment")
            return DeleteEnvironmentSuccess(
                message="Successfully deleted the environment"
            )

        return EnvironmentNotFoundError(
            message="No environment with this name found in this location.",
            path=path,
            name=name,
        )

    @classmethod
    async def create_from_module(
        cls, file: Upload, module_path: str, environment_path: str
    ) -> CreateResponse:  # type: ignore
        """Create an Environment based on an existing module.

        The environment will not be built; a "fake" softpack.yml and the
        supplied module file will be written as artifacts in a newly created
        environment instead, so that they can be discovered.

        Args:
            file: the module file to add to the repo, and to parse to fake a
                  corresponding softpack.yml. It should have a format similar
                  to that produced by shpc, with `module whatis` outputting
                  a "Name: " line, a "Version: " line, and optionally a
                  "Packages: " line to say what packages are available.
                  `module help` output will be translated into the description
                  in the softpack.yml.
            module_path: the local path that users can `module load` - this is
                         used to auto-generate usage help text for this
                         environment.
            environment_path: the subdirectories of environments folder that
                              artifacts will be stored in, eg.
                              users/username/software_name

        Returns:
            A message confirming the success or failure of the operation.
        """
        env = EnvironmentInput.from_path(environment_path)

        response = cls.create_new_env(
            env, Artifacts.generated_from_module_file
        )
        if not isinstance(response, CreateEnvironmentSuccess):
            return response

        result = await cls.convert_module_file_to_artifacts(
            file, env.name, environment_path, module_path
        )

        if not isinstance(result, WriteArtifactSuccess):
            cls.delete(name=env.name, path=environment_path)
            return InvalidInputError(
                message="Write of module file failed: " + result.message
            )

        return CreateEnvironmentSuccess(
            message="Successfully created environment in artifacts repo"
        )

    @classmethod
    async def convert_module_file_to_artifacts(
        cls, file: Upload, env_name: str, env_path: str, module_path: str
    ) -> WriteArtifactResponse:  # type: ignore
        """convert_module_file_to_artifacts parses a module and writes to repo.

        Args:
            file (Upload): shpc-style module file contents.
            env_name (str): name of the environment.
            env_path (str): path of the environment.
            module_path (str): the `module load` path users will use.

        Returns:
            WriteArtifactResponse: success or failure indicator.
        """
        contents = await file.read()
        yml = ToSoftpackYML(env_name, contents)
        readme = GenerateEnvReadme(module_path)

        module_file = UploadFile(file=io.BytesIO(contents))
        softpack_file = UploadFile(file=io.BytesIO(yml))
        readme_file = UploadFile(file=io.BytesIO(readme))

        return await cls.write_module_artifacts(
            module_file=module_file,
            softpack_file=softpack_file,
            readme_file=readme_file,
            environment_path=env_path,
        )

    @classmethod
    async def write_module_artifacts(
        cls,
        module_file: Upload,
        softpack_file: Upload,
        readme_file: Upload,
        environment_path: str,
    ) -> WriteArtifactResponse:  # type: ignore
        """Writes the given module and softpack files to the artifacts repo.

        Args:
            module_file (Upload): An shpc-style module file.
            softpack_file (Upload): A "fake" softpack.yml file describing what
            the module file offers.
            readme_file (Upload): An README.md file containing usage
            instructions.
            environment_path (str): Path to the environment, eg.
            users/user/env.

        Returns:
            WriteArtifactResponse: contains message and commit hash of
            softpack.yml upload.
        """
        result = await cls.write_artifact(
            file=module_file,
            folder_path=environment_path,
            file_name=cls.artifacts.module_file,
        )

        if not isinstance(result, WriteArtifactSuccess):
            return result

        result = await cls.write_artifact(
            file=readme_file,
            folder_path=environment_path,
            file_name=cls.artifacts.readme_file,
        )

        if not isinstance(result, WriteArtifactSuccess):
            return result

        return await cls.write_artifact(
            file=softpack_file,
            folder_path=environment_path,
            file_name=cls.artifacts.environments_file,
        )

    @classmethod
    async def write_artifact(
        cls, file: Upload, folder_path: str, file_name: str
    ) -> WriteArtifactResponse:  # type: ignore
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
            commit_oid = cls.artifacts.commit_and_push(
                tree_oid, "write artifact"
            )
            return WriteArtifactSuccess(
                message="Successfully written artifact",
                commit_oid=str(commit_oid),
            )

        except Exception as e:
            return InvalidInputError(message=str(e))

    @classmethod
    async def update_from_module(
        cls, file: Upload, module_path: str, environment_path: str
    ) -> UpdateResponse:  # type: ignore
        """Update an Environment based on an existing module.

        Same as create_from_module, but only works for an existing environment.

        Args:
            file: the module file to add to the repo, and to parse to fake a
                  corresponding softpack.yml. It should have a format similar
                  to that produced by shpc, with `module whatis` outputting
                  a "Name: " line, a "Version: " line, and optionally a
                  "Packages: " line to say what packages are available.
                  `module help` output will be translated into the description
                  in the softpack.yml.
            module_path: the local path that users can `module load` - this is
                         used to auto-generate usage help text for this
                         environment.
            environment_path: the subdirectories of environments folder that
                              artifacts will be stored in, eg.
                              users/username/software_name

        Returns:
            A message confirming the success or failure of the operation.
        """
        env = EnvironmentInput.from_path(environment_path)

        result = cls.check_env_exists(Path(environment_path))
        if result is not None:
            return result

        result = await cls.convert_module_file_to_artifacts(
            file, env.name, environment_path, module_path
        )

        if not isinstance(result, WriteArtifactSuccess):
            return InvalidInputError(
                message="Write of module file failed: " + result.message
            )

        return UpdateEnvironmentSuccess(
            message="Successfully updated environment in artifacts repo"
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
        deleteEnvironment: DeleteResponse = Environment.delete  # type: ignore
        writeArtifact: WriteArtifactResponse = (  # type: ignore
            Environment.write_artifact
        )
        createFromModule: CreateResponse = (  # type: ignore
            Environment.create_from_module
        )
        updateFromModule: UpdateResponse = (  # type: ignore
            Environment.update_from_module
        )
