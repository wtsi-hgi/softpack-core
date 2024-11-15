"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import bisect
import datetime
import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from time import time
from traceback import format_exception_only
from typing import List, Optional, Tuple, Union, cast

import httpx
import yaml
from box import Box
from fastapi import UploadFile

from softpack_core.app import app
from softpack_core.artifacts import (
    Artifacts,
    Interpreters,
    Package,
    State,
    Type,
    artifacts,
)
from softpack_core.module import GenerateEnvReadme, ToSoftpackYML


@dataclass
class CreateEnvironmentSuccess:
    """Environment successfully scheduled."""

    message: str


@dataclass
class UpdateEnvironmentSuccess:
    """Environment successfully updated."""

    message: str


@dataclass
class AddTagSuccess:
    """Successfully added tag to environment."""

    message: str


@dataclass
class HiddenSuccess:
    """Successfully set hidden status on environment."""

    message: str


@dataclass
class DeleteEnvironmentSuccess:
    """Environment successfully deleted."""

    message: str


@dataclass
class WriteArtifactSuccess:
    """Artifact successfully created."""

    message: str


# Error types
@dataclass
class InvalidInputError:
    """Invalid input data."""

    error: str


@dataclass
class WriteArtifactFailure:
    """Artifact failed to be created."""

    error: str


@dataclass
class EnvironmentNotFoundError:
    """Environment not found."""

    path: str
    name: str
    error: str = "No environment with this path and name found."


@dataclass
class EnvironmentAlreadyExistsError:
    """Environment name already exists."""

    path: str
    name: str
    error: str


@dataclass
class BuilderError:
    """Unable to connect to builder."""

    error: str


# Unions
CreateResponse = Union[
    CreateEnvironmentSuccess,
    InvalidInputError,
    EnvironmentAlreadyExistsError,
    BuilderError,
    EnvironmentNotFoundError,
]

UpdateResponse = Union[
    UpdateEnvironmentSuccess,
    InvalidInputError,
    EnvironmentNotFoundError,
]

AddTagResponse = Union[
    AddTagSuccess,
    InvalidInputError,
    EnvironmentNotFoundError,
    WriteArtifactFailure,
]

HiddenResponse = Union[
    HiddenSuccess,
    InvalidInputError,
    EnvironmentNotFoundError,
]

DeleteResponse = Union[
    DeleteEnvironmentSuccess,
    EnvironmentNotFoundError,
]

WriteArtifactResponse = Union[
    WriteArtifactSuccess,
    InvalidInputError,
]


def validate_tag(tag: str) -> Union[None, InvalidInputError]:
    """If the given tag is invalid, return an error describing why, else None.

    Tags must be composed solely of alphanumerics, dots, underscores,
    dashes, and spaces, and not contain runs of multiple spaces or
    leading/trailing whitespace.
    """
    if tag != tag.strip():
        return InvalidInputError(
            error="Tags must not contain leading or trailing whitespace"
        )

    if re.fullmatch(r"[a-zA-Z0-9 ._-]+", tag) is None:
        return InvalidInputError(
            error="Tags must contain only alphanumerics, dots, "
            "underscores, dashes, and spaces"
        )

    if re.search(r"\s\s", tag) is not None:
        return InvalidInputError(
            error="Tags must not contain runs of multiple spaces"
        )

    return None


class PackageInput(Package):
    """A data class model representing a package."""

    def to_package(self) -> Package:
        """Create a Package object from a PackageInput object.

        Return: a Package object
        """
        return Package(**vars(self))


@dataclass
class EnvironmentInput:
    """A data class model representing an environment."""

    name: str
    path: str
    description: str
    packages: list[PackageInput]
    username: Optional[str] = ""
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
            and key != "username"
            and key != "__pydantic_initialised__"
        ):
            return InvalidInputError(error="all fields must be filled in")

        if not re.fullmatch("^[a-zA-Z0-9_-][a-zA-Z0-9_.-]*$", self.name):
            return InvalidInputError(
                error="name must only contain alphanumerics, "
                "dash, and underscore"
            )

        valid_dirs = [
            Artifacts.users_folder_name,
            Artifacts.groups_folder_name,
        ]
        if not any(self.path.startswith(dir + "/") for dir in valid_dirs):
            return InvalidInputError(error="Invalid path")

        if not re.fullmatch(r"^[^/]+/[a-zA-Z0-9_-]+$", self.path):
            return InvalidInputError(
                error="user/group subdirectory must only contain "
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

    def has_requested_recipes(self) -> bool:
        """Do any of the requested packages have an unmade recipe."""
        return any(pkg.name.startswith("*") for pkg in self.packages)


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
                error="Connection to builder failed: "
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


@dataclass
class DelEnvironmentInput:
    """A class representing an input to delete environment."""

    path: str
    name: str


@dataclass
class AddTagInput:
    """A class representing an input to add a tag."""

    path: str
    name: str
    tag: str


@dataclass
class SetHiddenInput:
    """A class representing an input to set hidden."""

    path: str
    name: str
    hidden: bool


@dataclass
class Environment:
    """A data class representing a single environment."""

    name: str
    path: str
    description: str
    readme: str
    type: Type
    packages: list[Package]
    state: Optional[State]
    tags: list[str]
    username: Optional[str]
    failure_reason: Optional[str]
    hidden: bool
    created: int
    interpreters: Interpreters = field(default_factory=Interpreters)

    environments: list["Environment"] = field(default_factory=list)

    @classmethod
    def init(cls, branch: str | None) -> None:
        """Initialises Environment."""
        artifacts.clone_repo(branch)
        cls.load_initial_environments()

    @classmethod
    def load_initial_environments(cls) -> None:
        """Loads the environments from the repo."""
        environment_folders = artifacts.iter()
        cls.environments = list(
            filter(None, map(cls.from_artifact, environment_folders))
        )

        cls.environments.sort(key=lambda x: x.full_path())

    def full_path(cls) -> Path:
        """Return a Path containing the file path and name."""
        return Path(cls.path, cls.name)

    @classmethod
    def iter(cls) -> list["Environment"]:
        """Return a list of all Enviroments."""
        return cls.environments

    def has_requested_recipes(self) -> bool:
        """Do any of the requested packages have an unmade recipe."""
        return any(pkg.name.startswith("*") for pkg in self.packages)

    @classmethod
    def get_env(cls, path: Path, name: str) -> Optional["Environment"]:
        """Return an Environment object given a path.

        Args:
            path: A path.

        Returns:
            Environment: An Environment object.
        """
        artifact_env = artifacts.get(path, name)
        if not artifact_env:
            return None

        return cls.from_artifact(artifact_env)

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
            if spec.force_hidden:
                return None

            return Environment(
                name=obj.name,
                path=str(obj.path.parent),
                description=spec.description,
                packages=spec.packages,
                state=spec.state,
                readme=spec.get("readme", ""),
                type=spec.get("type", ""),
                tags=spec.tags,
                username=spec.username,
                failure_reason=spec.failure_reason,
                hidden=spec.hidden,
                created=spec.created,
                interpreters=spec.get("interpreters", Interpreters()),
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
        version = 1

        if not env.name:
            return InvalidInputError(
                error="environment name must not be blank"
            )

        while not isinstance(
            cls.check_env_exists(
                Path(env.path, env.name + "-" + str(version))
            ),
            EnvironmentNotFoundError,
        ):
            version += 1

        if version != 1:
            prevEnv = cls.get_env(
                Path(env.path), env.name + "-" + str(version - 1)
            )
            if (
                prevEnv is not None
                and cast(Environment, prevEnv).state == State.failed
            ):
                version -= 1

                tree_oid = artifacts.delete_environment(
                    env.name + "-" + str(version), env.path
                )
                artifacts.commit_and_push(
                    tree_oid, "remove failed environment"
                )

        env.name += "-" + str(version)
        response = cls.create_new_env(env, Artifacts.built_by_softpack_file)
        if not isinstance(response, CreateEnvironmentSuccess):
            return response

        Environment.update_cache(Path(env.path, env.name))

        builder_response = cls.submit_env_to_builder(env)
        if builder_response is not None:
            return builder_response

        return CreateEnvironmentSuccess(
            message="Successfully scheduled environment creation"
        )

    @classmethod
    def insert_new_env(cls, env: "Environment") -> None:
        """Inserts an enviroment into the correct, sorted position."""
        bisect.insort(
            Environment.environments, env, key=lambda x: x.full_path()
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
                error=f"could not parse version from name: {env.name!r}"
            )

        if env.has_requested_recipes():
            return None

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
                error="Connection to builder failed: "
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
                error="This name is already used in this location",
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

            meta = dict(
                tags=sorted(set(env.tags or [])),
                created=round(time()),
            )

            if env.username != "" and env.username is not None:
                meta["username"] = env.username

            metaData = yaml.dump(meta)

            tree_oid = artifacts.create_files(
                Path(artifacts.environments_root, new_folder_path),
                [
                    (env_type, ""),  # e.g. .built_by_softpack
                    (
                        artifacts.environments_file,
                        definitionData,
                    ),  # softpack.yml
                    (artifacts.meta_file, metaData),
                ],
                True,
                True,
            )
            artifacts.commit_and_push(tree_oid, "create environment folder")
        except RuntimeError as e:
            return InvalidInputError(
                error="".join(format_exception_only(type(e), e))
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
    async def add_tag(
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
        response: Optional[EnvironmentNotFoundError] = cls.check_env_exists(
            environment_path
        )
        if response is not None:
            return response

        if (tagResponse := validate_tag(tag)) is not None:
            return tagResponse

        tree = artifacts.get(Path(path), name)
        if tree is None:
            return EnvironmentNotFoundError(path=path, name=name)
        box = tree.spec()
        tags = set(box.tags)
        if tag in tags:
            return AddTagSuccess(message="Tag already present")
        tags.add(tag)

        metadata = cls.read_metadata(path, name)
        metadata.tags = sorted(tags)

        metadataResponse = await cls.store_metadata(environment_path, metadata)

        if isinstance(metadataResponse, WriteArtifactSuccess):
            return AddTagSuccess(message="Tag successfully added")

        return WriteArtifactFailure(error="Failed to add tag")

    @classmethod
    def read_metadata(cls, path: str, name: str) -> Box:
        """Read an environments metadata.

        This method returns the metadata for an environment with the given
        path and name.
        """
        arts = artifacts.get(Path(path), name)

        if arts is not None:
            return arts.metadata()

        return Box()

    @classmethod
    async def store_metadata(
        cls, environment_path: Path, metadata: Box
    ) -> WriteArtifactResponse:  # type: ignore
        """Store an environments metadata.

        This method writes the given metadata to the repo for the
        environment path given.
        """
        return await Environment.write_artifacts(
            str(environment_path),
            [(artifacts.meta_file, metadata.to_yaml())],
            "update metadata",
        )

    @classmethod
    async def set_hidden(
        cls, name: str, path: str, hidden: bool
    ) -> HiddenResponse:  # type: ignore
        """This method sets the hidden status for the given environment."""
        environment_path = Path(path, name)
        response: Optional[EnvironmentNotFoundError] = cls.check_env_exists(
            environment_path
        )
        if response is not None:
            return response

        metadata = cls.read_metadata(path, name)

        if metadata.get("hidden") == hidden:
            return HiddenSuccess(message="Hidden metadata already set")

        metadata.hidden = hidden

        metadataResponse = await cls.store_metadata(environment_path, metadata)

        if isinstance(metadataResponse, WriteArtifactSuccess):
            return HiddenSuccess(message="Hidden metadata set")

        return metadataResponse

    async def update_metadata(cls, key: str, value: str | None) -> None:
        """Takes a key and sets the value unless value is None."""
        metadata = cls.read_metadata(cls.path, cls.name)

        if value is None:
            del metadata[key]
        else:
            metadata[key] = value

        await cls.store_metadata(Path(cls.path, cls.name), metadata)

    async def remove_username(cls) -> None:
        """Remove the username metadata from the meta.yaml file."""
        await cls.update_metadata("username", None)

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

            Environment.update_cache(Path(path, name))

            return DeleteEnvironmentSuccess(
                message="Successfully deleted the environment"
            )

        return EnvironmentNotFoundError(
            error="No environment with this name found in this location.",
            path=path,
            name=name,
        )

    @classmethod
    async def create_from_module(
        cls, file: bytes, module_path: str, environment_path: str
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
                error="Write of module file failed: " + result.error
            )

        return CreateEnvironmentSuccess(
            message="Successfully created environment in artifacts repo"
        )

    @classmethod
    async def convert_module_file_to_artifacts(
        cls, contents: bytes, env_name: str, env_path: str, module_path: str
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
        module_file: UploadFile,
        softpack_file: UploadFile,
        readme_file: UploadFile,
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
        module_file.filename = artifacts.module_file
        readme_file.filename = artifacts.readme_file
        softpack_file.filename = artifacts.environments_file

        return await cls.write_artifacts(
            folder_path=environment_path,
            files=[module_file, readme_file, softpack_file],
        )

    @classmethod
    async def write_artifact(
        cls, file: UploadFile, folder_path: str, file_name: str
    ) -> WriteArtifactResponse:  # type: ignore
        """Add a file to the Artifacts repo.

        Args:
            file: the file to be added to the repo.
            folder_path: the path to the folder that the file will be added to.
            file_name: the name of the file to be added.
        """
        file.filename = file_name

        return await cls.write_artifacts(folder_path, [file])

    @classmethod
    async def write_artifacts(
        cls,
        folder_path: str,
        files: list[Union[UploadFile, Tuple[str, str]]],
        commitMsg: str = "write artifact",
    ) -> WriteArtifactResponse:  # type: ignore
        """Add one or more files to the Artifacts repo.

        Args:
            folder_path: the path to the folder that the file will be added to.
            files: the files to add to the repo.
            commitMsg: the msg for the commit.
        """
        try:
            new_files: List[Tuple[str, Union[str, UploadFile]]] = []
            for file in files:
                if isinstance(file, tuple):
                    new_files.append(
                        cast(Tuple[str, Union[str, UploadFile]], file)
                    )
                else:
                    new_files.append(
                        (file.filename or "", cast(UploadFile, file))
                    )

            tree_oid = artifacts.create_files(
                Path(artifacts.environments_root, folder_path),
                new_files,
                overwrite=True,
            )
            artifacts.commit_and_push(tree_oid, commitMsg)

            Environment.update_cache(folder_path)

            return WriteArtifactSuccess(
                message="Successfully written artifact(s)",
            )
        except Exception as e:
            return InvalidInputError(
                error="".join(format_exception_only(type(e), e))
            )

    @classmethod
    def update_cache(cls, folder_path: str | Path) -> None:
        """Regenerate the cached environment specified by the path."""
        index = cls.env_index_from_path(str(folder_path))
        path = Path(folder_path)
        env = Environment.get_env(path.parent, path.name)

        if index is None:
            if env:
                Environment.insert_new_env(env)
        elif env:
            Environment.environments[index] = env
        else:
            del Environment.environments[index]

    @classmethod
    def env_index_from_path(cls, folder_path: str) -> Optional[int]:
        """Return the index of a folder_path from the list of environments."""
        return next(
            (
                i
                for i, env in enumerate(Environment.environments)
                if str(env.full_path()) == folder_path
            ),
            None,
        )

    @classmethod
    async def update_from_module(
        cls, file: bytes, module_path: str, environment_path: str
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

        convertResult = await cls.convert_module_file_to_artifacts(
            file, env.name, environment_path, module_path
        )

        if not isinstance(convertResult, WriteArtifactSuccess):
            return InvalidInputError(
                error="Write of module file failed: " + convertResult.error
            )

        return UpdateEnvironmentSuccess(
            message="Successfully updated environment in artifacts repo"
        )
