"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import datetime
import io
import re
import statistics
from dataclasses import dataclass
from pathlib import Path
from traceback import format_exception_only
from typing import List, Optional, Tuple, Union, cast

import httpx
import starlette.datastructures
import strawberry
import yaml
from fastapi import UploadFile
from strawberry.file_uploads import Upload

from softpack_core.app import app
from softpack_core.artifacts import Artifacts, Package, State, Type, artifacts
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
class AddTagSuccess(Success):
    """Successfully added tag to environment."""


@strawberry.type
class DeleteEnvironmentSuccess(Success):
    """Environment successfully deleted."""


@strawberry.type
class WriteArtifactSuccess(Success):
    """Artifact successfully created."""


# Error types
@strawberry.type
class InvalidInputError(Error):
    """Invalid input data."""


@strawberry.type
class EnvironmentNotFoundError(Error):
    """Environment not found."""

    path: str
    name: str
    message: str = "No environment with this path and name found."


@strawberry.type
class EnvironmentAlreadyExistsError(Error):
    """Environment name already exists."""

    path: str
    name: str


@strawberry.type
class BuilderError(Error):
    """Unable to connect to builder."""


# Unions
CreateResponse = strawberry.union(
    "CreateResponse",
    [
        CreateEnvironmentSuccess,
        InvalidInputError,
        EnvironmentAlreadyExistsError,
        BuilderError,
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

AddTagResponse = strawberry.union(
    "AddTagResponse",
    [
        AddTagSuccess,
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


def validate_tag(tag: str) -> Union[None, InvalidInputError]:
    """If the given tag is invalid, return an error describing why, else None.

    Tags must be composed solely of alphanumerics, dots, underscores,
    dashes, and spaces, and not contain runs of multiple spaces or
    leading/trailing whitespace.
    """
    if tag != tag.strip():
        return InvalidInputError(
            message="Tags must not contain leading or trailing whitespace"
        )

    if re.fullmatch(r"[a-zA-Z0-9 ._-]+", tag) is None:
        return InvalidInputError(
            message="Tags must contain only alphanumerics, dots, "
            "underscores, dashes, and spaces"
        )

    if re.search(r"\s\s", tag) is not None:
        return InvalidInputError(
            message="Tags must not contain runs of multiple spaces"
        )

    return None


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
    tags: Optional[list[str]] = None

    def validate(self) -> Union[None, InvalidInputError]:
        """Validate all values.

        Checks all values have been supplied.
        Checks that name consists only of alphanumerics, dash, and underscore.

        Returns:
            None if good, or InvalidInputError if not all values supplied.
        """
        if any(
            len(value) == 0
            for key, value in vars(self).items()
            if key != "tags"
        ):
            return InvalidInputError(message="all fields must be filled in")

        if not re.fullmatch("^[a-zA-Z0-9_-][a-zA-Z0-9_.-]*$", self.name):
            return InvalidInputError(
                message="name must only contain alphanumerics, "
                "dash, and underscore"
            )

        valid_dirs = [
            Artifacts.users_folder_name,
            Artifacts.groups_folder_name,
        ]
        if not any(self.path.startswith(dir + "/") for dir in valid_dirs):
            return InvalidInputError(message="Invalid path")

        if not re.fullmatch(r"^[^/]+/[a-zA-Z0-9_-]+$", self.path):
            return InvalidInputError(
                message="user/group subdirectory must only contain "
                "alphanumerics, dash, and underscore"
            )

        for tag in self.tags or []:
            if (response := validate_tag(tag)) is not None:
                return response

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
            description="placeholder description",
            packages=[PackageInput("placeholder")],
        )


@dataclass
class BuildStatus:
    """A class representing the status of a build."""

    name: str
    requested: datetime.datetime
    build_start: Optional[datetime.datetime]
    build_done: Optional[datetime.datetime]

    @classmethod
    def get_all(cls) -> Union[List["BuildStatus"], BuilderError]:
        """Get all known environment build statuses."""
        try:
            host = app.settings.builder.host
            port = app.settings.builder.port
            r = httpx.get(
                f"http://{host}:{port}/environments/status",
            )
            r.raise_for_status()
            json = r.json()
        except Exception as e:
            return BuilderError(
                message="Connection to builder failed: "
                + "".join(format_exception_only(type(e), e))
            )

        return [
            BuildStatus(
                name=s["Name"],
                requested=datetime.datetime.fromisoformat(s["Requested"]),
                build_start=datetime.datetime.fromisoformat(s["BuildStart"])
                if s["BuildStart"]
                else None,
                build_done=datetime.datetime.fromisoformat(s["BuildDone"])
                if s["BuildDone"]
                else None,
            )
            for s in json
        ]


@strawberry.type
class Environment:
    """A Strawberry model representing a single environment."""

    id: str
    name: str
    path: str
    description: str
    readme: str
    type: Type
    packages: list[Package]
    state: Optional[State]
    tags: list[str]

    requested: Optional[datetime.datetime] = None
    build_start: Optional[datetime.datetime] = None
    build_done: Optional[datetime.datetime] = None
    avg_wait_secs: Optional[float] = None

    @classmethod
    def iter(cls) -> list["Environment"]:
        """Get an iterator over all Environment objects.

        Returns:
            Iterable[Environment]: An iterator of Environment objects.
        """
        statuses = BuildStatus.get_all()
        if isinstance(statuses, BuilderError):
            statuses = []

        status_map = {s.name: s for s in statuses}

        waits: list[float] = []
        for s in statuses:
            if s.build_done is None:
                continue
            waits.append((s.build_done - s.requested).total_seconds())

        try:
            avg_wait_secs = statistics.mean(waits)
        except statistics.StatisticsError:
            avg_wait_secs = None

        environment_folders = artifacts.iter()
        environment_objects = list(
            filter(None, map(cls.from_artifact, environment_folders))
        )

        for env in environment_objects:
            env.avg_wait_secs = avg_wait_secs
            status = status_map.get(str(Path(env.path, env.name)))
            if not status:
                continue
            env.requested = status.requested
            env.build_start = status.build_start
            env.build_done = status.build_done

        return environment_objects

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
                tags=spec.tags,
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
        versionless_name = env.name
        version = 1

        if not versionless_name:
            return InvalidInputError(
                message="environment name must not be blank"
            )

        while True:
            env.name = versionless_name + "-" + str(version)
            response = cls.create_new_env(
                env, Artifacts.built_by_softpack_file
            )
            if isinstance(response, CreateEnvironmentSuccess):
                break

            if not isinstance(response, EnvironmentAlreadyExistsError):
                return response

            version += 1

        response = cls.submit_env_to_builder(env)
        if response is not None:
            return response

        return CreateEnvironmentSuccess(
            message="Successfully scheduled environment creation"
        )

    @classmethod
    def submit_env_to_builder(
        cls, env: EnvironmentInput
    ) -> Union[None, BuilderError, InvalidInputError]:
        """Submit an environment to the builder."""
        try:
            m = re.fullmatch(r"^(.*)-(\d+)$", env.name)
            if not m:
                raise Exception
            versionless_name, version = m.groups()
        except Exception:
            return InvalidInputError(
                message=f"could not parse version from name: {env.name!r}"
            )

        try:
            host = app.settings.builder.host
            port = app.settings.builder.port
            r = httpx.post(
                f"http://{host}:{port}/environments/build",
                json={
                    "name": f"{env.path}/{versionless_name}",
                    "version": str(version),
                    "model": {
                        "description": env.description,
                        "packages": [
                            {
                                "name": pkg.name,
                                "version": pkg.version,
                            }
                            for pkg in env.packages
                        ],
                    },
                },
            )
            r.raise_for_status()
        except Exception as e:
            return BuilderError(
                message="Connection to builder failed: "
                + "".join(format_exception_only(type(e), e))
            )
        return None

    @classmethod
    def create_new_env(
        cls, env: EnvironmentInput, env_type: str
    ) -> CreateResponse:  # type: ignore
        """Create a new environment in the repository.

        Adds an empty .created file in the desired location. Fails if this
        already exists.

        Args:
            env (EnvironmentInput): Details of the new environment.
            env_type (str): One of Artifacts.built_by_softpack_file or
            Artifacts.generated_from_module_file that denotes how the
            environment was made.

        Returns:
            CreateResponse: a CreateEnvironmentSuccess on success, or one of
            (InvalidInputError, EnvironmentAlreadyExistsError) on error.
        """
        # TODO: improve this to check
        # that users can only create stuff in their own users folder, or in
        # group folders of unix groups they belong to.
        input_err = env.validate()
        if input_err is not None:
            return input_err

        # Check if an env with same name already exists at given path
        if artifacts.get(Path(env.path), env.name):
            return EnvironmentAlreadyExistsError(
                message="This name is already used in this location",
                path=env.path,
                name=env.name,
            )

        # Create folder with initial files
        new_folder_path = Path(env.path, env.name)
        try:
            softpack_definition = dict(
                description=env.description,
                packages=[
                    pkg.name + ("@" + pkg.version if pkg.version else "")
                    for pkg in env.packages
                ],
            )
            definitionData = yaml.dump(softpack_definition)

            meta = dict(tags=sorted(set(env.tags or [])))
            metaData = yaml.dump(meta)

            tree_oid = artifacts.create_files(
                new_folder_path,
                [
                    (env_type, ""),  # e.g. .built_by_softpack
                    (
                        artifacts.environments_file,
                        definitionData,
                    ),  # softpack.yml
                    (artifacts.meta_file, metaData),
                ],
                True,
            )
            artifacts.commit_and_push(tree_oid, "create environment folder")
        except RuntimeError as e:
            return InvalidInputError(
                message="".join(format_exception_only(type(e), e))
            )

        return CreateEnvironmentSuccess(
            message="Successfully created environment in artifacts repo"
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
        if artifacts.get(path.parent, path.name):
            return None

        return EnvironmentNotFoundError(
            path=str(path.parent),
            name=path.name,
        )

    @classmethod
    def add_tag(
        cls, name: str, path: str, tag: str
    ) -> AddTagResponse:  # type: ignore
        """Add a tag to an Environment.

        Tags must be valid as defined by validate_tag().

        Adding a tag that already exists is not an error.

        Args:
            name: the name of of environment
            path: the path of the environment
            tag: the tag to add

        Returns:
            A message confirming the success or failure of the operation.
        """
        environment_path = Path(path, name)
        response: Optional[Error] = cls.check_env_exists(environment_path)
        if response is not None:
            return response

        if (response := validate_tag(tag)) is not None:
            return response

        tree = artifacts.get(Path(path), name)
        if tree is None:
            return EnvironmentNotFoundError(path=path, name=name)
        box = tree.spec()
        tags = set(box.tags)
        if tag in tags:
            return AddTagSuccess(message="Tag already present")
        tags.add(tag)

        metadata = yaml.dump({"tags": sorted(tags)})
        tree_oid = artifacts.create_file(
            environment_path, artifacts.meta_file, metadata, overwrite=True
        )
        artifacts.commit_and_push(tree_oid, "create environment folder")
        return AddTagSuccess(message="Tag successfully added")

    @classmethod
    def delete(cls, name: str, path: str) -> DeleteResponse:  # type: ignore
        """Delete an Environment.

        Args:
            name: the name of of environment
            path: the path of the environment

        Returns:
            A message confirming the success or failure of the operation.
        """
        if artifacts.get(Path(path), name):
            tree_oid = artifacts.delete_environment(name, path)
            artifacts.commit_and_push(tree_oid, "delete environment")
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

        module_file = UploadFile(
            filename=artifacts.module_file, file=io.BytesIO(contents)
        )
        softpack_file = UploadFile(
            filename=artifacts.environments_file, file=io.BytesIO(yml)
        )
        readme_file = UploadFile(
            filename=artifacts.readme_file, file=io.BytesIO(readme)
        )

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
        module_file.name = artifacts.module_file
        readme_file.name = artifacts.readme_file
        softpack_file.name = artifacts.environments_file

        return await cls.write_artifacts(
            folder_path=environment_path,
            files=[module_file, readme_file, softpack_file],
        )

    @classmethod
    async def write_artifact(
        cls, file: Upload, folder_path: str, file_name: str
    ) -> WriteArtifactResponse:  # type: ignore
        """Add a file to the Artifacts repo.

        Args:
            file: the file to be added to the repo.
            folder_path: the path to the folder that the file will be added to.
            file_name: the name of the file to be added.
        """
        file.name = file_name

        return await cls.write_artifacts(folder_path, [file])

    @classmethod
    async def write_artifacts(
        cls, folder_path: str, files: list[Union[Upload, UploadFile]]
    ) -> WriteArtifactResponse:  # type: ignore
        """Add one or more files to the Artifacts repo.

        Args:
            folder_path: the path to the folder that the file will be added to.
            files: the files to add to the repo.
        """
        try:
            new_files: List[Tuple[str, Union[str, UploadFile]]] = []
            for file in files:
                if isinstance(file, starlette.datastructures.UploadFile):
                    new_files.append(
                        (file.filename or "", cast(UploadFile, file))
                    )
                else:
                    new_files.append(
                        (file.name, cast(str, (await file.read()).decode()))
                    )

            tree_oid = artifacts.create_files(
                Path(folder_path), new_files, overwrite=True
            )
            artifacts.commit_and_push(tree_oid, "write artifact")
            return WriteArtifactSuccess(
                message="Successfully written artifact(s)",
            )

        except Exception as e:
            return InvalidInputError(
                message="".join(format_exception_only(type(e), e))
            )

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
        deleteEnvironment: DeleteResponse = Environment.delete  # type: ignore
        addTag: AddTagResponse = Environment.add_tag  # type: ignore
        # writeArtifact: WriteArtifactResponse = (  # type: ignore
        #     Environment.write_artifact
        # )
        # writeArtifacts: WriteArtifactResponse = (  # type: ignore
        #     Environment.write_artifacts
        # )
        createFromModule: CreateResponse = (  # type: ignore
            Environment.create_from_module
        )
        updateFromModule: UpdateResponse = (  # type: ignore
            Environment.update_from_module
        )
