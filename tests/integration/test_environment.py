"""Copyright (c) 2023, 2024 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import datetime
import io
from pathlib import Path
from typing import Optional

import pygit2
import pytest
import yaml
from fastapi import UploadFile

from softpack_core.artifacts import Artifacts
from softpack_core.schemas.environment import (
    AddTagSuccess,
    BuilderError,
    CreateEnvironmentSuccess,
    DeleteEnvironmentSuccess,
    Environment,
    EnvironmentAlreadyExistsError,
    EnvironmentInput,
    EnvironmentNotFoundError,
    InvalidInputError,
    Package,
    State,
    UpdateEnvironmentSuccess,
    WriteArtifactSuccess,
)
from tests.integration.utils import builder_called_correctly, file_in_remote

pytestmark = pytest.mark.repo


def test_create(httpx_post, testable_env_input: EnvironmentInput) -> None:
    orig_input_name = testable_env_input.name
    result = Environment.create(testable_env_input)
    testable_env_input.name = orig_input_name
    assert isinstance(result, CreateEnvironmentSuccess)
    httpx_post.assert_called_once()
    builder_called_correctly(httpx_post, testable_env_input)

    result = Environment.create(
        EnvironmentInput(
            name="test_env_create2",
            path="groups/not_already_in_repo",
            description="description2",
            packages=[
                Package(name="pkg_test2"),
                Package(name="pkg_test3", version="3.1"),
            ],
            tags=["foo", "foo", "bar"],
        )
    )
    assert isinstance(result, CreateEnvironmentSuccess)
    httpx_post.assert_called()

    dir = Path(
        Environment.artifacts.environments_root,
        testable_env_input.path,
        testable_env_input.name + "-1",
    )
    builtPath = dir / Environment.artifacts.built_by_softpack_file
    ymlPath = dir / Environment.artifacts.environments_file
    assert file_in_remote(builtPath)
    ymlFile = file_in_remote(ymlPath)
    expected_yaml = {
        "description": "description",
        "packages": ["pkg_test"],
    }
    assert yaml.safe_load(ymlFile.data.decode()) == expected_yaml
    meta_yml = file_in_remote(dir / Environment.artifacts.meta_file)
    expected_meta_yml = {"tags": []}
    actual_meta_yml = yaml.safe_load(meta_yml.data.decode())
    assert actual_meta_yml == expected_meta_yml

    dir = Path(
        Environment.artifacts.environments_root,
        "groups/not_already_in_repo",
        "test_env_create2-1",
    )
    builtPath = dir / Environment.artifacts.built_by_softpack_file
    ymlPath = dir / Environment.artifacts.environments_file
    assert file_in_remote(builtPath)
    ymlFile = file_in_remote(ymlPath)
    expected_yaml = {
        "description": "description2",
        "packages": ["pkg_test2", "pkg_test3@3.1"],
    }
    assert yaml.safe_load(ymlFile.data.decode()) == expected_yaml

    meta_yml = file_in_remote(dir / Environment.artifacts.meta_file)
    expected_meta_yml = {"tags": ["bar", "foo"]}
    actual_meta_yml = yaml.safe_load(meta_yml.data.decode())
    assert actual_meta_yml == expected_meta_yml

    result = Environment.create(testable_env_input)
    testable_env_input.name = orig_input_name
    assert isinstance(result, CreateEnvironmentSuccess)

    path = Path(
        Environment.artifacts.environments_root,
        testable_env_input.path,
        testable_env_input.name + "-2",
        Environment.artifacts.built_by_softpack_file,
    )
    assert file_in_remote(path)


def test_create_name_empty_disallowed(httpx_post, testable_env_input):
    testable_env_input.name = ""
    result = Environment.create(testable_env_input)
    assert isinstance(result, InvalidInputError)


def test_create_name_spaces_disallowed(httpx_post, testable_env_input):
    testable_env_input.name = "names cannot have spaces"
    result = Environment.create(testable_env_input)
    assert isinstance(result, InvalidInputError)


def test_create_name_slashes_disallowed(httpx_post, testable_env_input):
    testable_env_input.name = "names/cannot/have/slashes"
    result = Environment.create(testable_env_input)
    assert isinstance(result, InvalidInputError)


def test_create_name_dashes_and_number_first_allowed(
    httpx_post, testable_env_input
):
    testable_env_input.name = "7-zip_piz-7"
    result = Environment.create(testable_env_input)
    assert isinstance(result, CreateEnvironmentSuccess)


@pytest.mark.parametrize(
    "path",
    [
        "invalid/path",
        "users/",
        "users/username/foo",
        "users/abc123/very/nested",
        "users/../nasty",
        "users/user name",
    ],
)
def test_create_path_invalid_disallowed(httpx_post, testable_env_input, path):
    testable_env_input.path = path
    result = Environment.create(testable_env_input)
    assert isinstance(result, InvalidInputError)


def test_create_does_not_clean_up_after_builder_failure(
    httpx_post, testable_env_input
):
    httpx_post.side_effect = Exception('could not contact builder')
    result = Environment.create(testable_env_input)
    assert isinstance(result, BuilderError)

    dir = Path(
        Environment.artifacts.environments_root,
        testable_env_input.path,
        testable_env_input.name,
    )
    builtPath = dir / Environment.artifacts.built_by_softpack_file
    ymlPath = dir / Environment.artifacts.environments_file
    assert file_in_remote(builtPath)
    assert file_in_remote(ymlPath)


def test_delete(httpx_post, testable_env_input) -> None:
    result = Environment.delete(
        testable_env_input.name, testable_env_input.path
    )
    assert isinstance(result, EnvironmentNotFoundError)

    result = Environment.create(testable_env_input)
    assert isinstance(result, CreateEnvironmentSuccess)
    httpx_post.assert_called_once()

    path = Path(
        Environment.artifacts.environments_root,
        testable_env_input.path,
        testable_env_input.name,
        Artifacts.built_by_softpack_file,
    )
    assert file_in_remote(path)

    result = Environment.delete(
        testable_env_input.name, testable_env_input.path
    )
    assert isinstance(result, DeleteEnvironmentSuccess)

    assert not file_in_remote(path)


@pytest.mark.asyncio
async def test_write_artifact(httpx_post, testable_env_input):
    upload = UploadFile(filename="example.txt", file=io.BytesIO(b"mock data"))

    result = await Environment.write_artifact(
        file=upload,
        folder_path=f"{testable_env_input.path}/{testable_env_input.name}-1",
        file_name=upload.filename,
    )
    assert isinstance(result, InvalidInputError)

    orig_name = testable_env_input.name
    result = Environment.create(testable_env_input)
    testable_env_input.name = orig_name
    assert isinstance(result, CreateEnvironmentSuccess)
    httpx_post.assert_called_once()

    result = await Environment.write_artifact(
        file=upload,
        folder_path=f"{testable_env_input.path}/{testable_env_input.name}-1",
        file_name=upload.filename,
    )
    assert isinstance(result, WriteArtifactSuccess)

    path = Path(
        Environment.artifacts.environments_root,
        testable_env_input.path,
        testable_env_input.name + "-1",
        upload.filename,
    )
    assert file_in_remote(path)

    result = await Environment.write_artifact(
        file=upload,
        folder_path="invalid/env/path",
        file_name=upload.filename,
    )
    assert isinstance(result, InvalidInputError)


def test_iter(testable_env_input, mocker):
    get_mock = mocker.patch("httpx.get")
    get_mock.return_value.json.return_value = [
        {
            "Name": "users/test_user/test_environment",
            "Requested": "2025-01-02T03:04:00.000000000Z",
            "BuildStart": "2025-01-02T03:04:05.000000000Z",
            "BuildDone": None,
        },
        {
            "Name": "groups/test_group/test_environment",
            "Requested": "2025-01-02T03:04:00.000000000Z",
            "BuildStart": "2025-01-02T03:04:05.000000000Z",
            "BuildDone": "2025-01-02T03:04:15.000000000Z",
        },
        # only used for average calculations, does not map to an environment in
        # the test data
        {
            "Name": "users/foo/bar",
            "Requested": "2025-01-02T03:04:00.000000000Z",
            "BuildStart": "2025-01-02T03:04:05.000000000Z",
            "BuildDone": "2025-01-02T03:04:25.000000000Z",
        },
    ]

    envs = list(Environment.iter())
    assert len(envs) == 2
    assert envs[0].requested == datetime.datetime(
        2025, 1, 2, 3, 4, 0, tzinfo=datetime.timezone.utc
    )
    assert envs[0].build_start == datetime.datetime(
        2025, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc
    )
    assert envs[0].build_done is None
    assert envs[1].requested == datetime.datetime(
        2025, 1, 2, 3, 4, 0, tzinfo=datetime.timezone.utc
    )
    assert envs[1].build_start == datetime.datetime(
        2025, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc
    )
    assert envs[1].build_done == datetime.datetime(
        2025, 1, 2, 3, 4, 15, tzinfo=datetime.timezone.utc
    )
    assert envs[0].avg_wait_secs == envs[1].avg_wait_secs == 20


def test_iter_no_statuses(testable_env_input, mocker):
    get_mock = mocker.patch("httpx.get")
    get_mock.return_value.json.return_value = []

    envs = list(Environment.iter())
    assert len(envs) == 2
    assert envs[0].requested is None
    assert envs[0].build_start is None
    assert envs[0].build_done is None
    assert envs[0].avg_wait_secs is None
    assert envs[0].state == State.queued
    assert envs[1].state == State.queued


@pytest.mark.asyncio
async def test_states(httpx_post, testable_env_input, mocker):
    orig_name = testable_env_input.name
    result = Environment.create(testable_env_input)
    testable_env_input.name = orig_name
    assert isinstance(result, CreateEnvironmentSuccess)
    httpx_post.assert_called_once()

    upload = UploadFile(
        filename=Artifacts.environments_file,
        file=io.BytesIO(
            b"description: test env\n" b"packages:\n  - zlib@v1.1\n"
        ),
    )

    result = await Environment.write_artifact(
        file=upload,
        folder_path=f"{testable_env_input.path}/{testable_env_input.name}-1",
        file_name=upload.filename,
    )
    assert isinstance(result, WriteArtifactSuccess)

    get_mock = mocker.patch("httpx.get")
    get_mock.return_value.json.return_value = [
        {
            "Name": "users/test_user/test_env_create-1",
            "Requested": "2025-01-02T03:04:00.000000000Z",
            "BuildStart": None,
            "BuildDone": None,
        },
    ]
    env = get_env_from_iter(testable_env_input.name + "-1")
    assert env is not None
    assert any(p.name == "zlib" for p in env.packages)
    assert any(p.version == "v1.1" for p in env.packages)
    assert env.type == Artifacts.built_by_softpack
    assert env.state == State.queued

    upload = UploadFile(
        filename=Artifacts.builder_out, file=io.BytesIO(b"some output")
    )

    result = await Environment.write_artifact(
        file=upload,
        folder_path=f"{testable_env_input.path}/{testable_env_input.name}-1",
        file_name=upload.filename,
    )
    assert isinstance(result, WriteArtifactSuccess)

    env = get_env_from_iter(testable_env_input.name + "-1")
    assert env is not None
    assert env.state == State.failed

    upload = UploadFile(
        filename=Artifacts.module_file, file=io.BytesIO(b"#%Module")
    )

    result = await Environment.write_artifact(
        file=upload,
        folder_path=f"{testable_env_input.path}/{testable_env_input.name}-1",
        file_name=upload.filename,
    )
    assert isinstance(result, WriteArtifactSuccess)

    env = get_env_from_iter(testable_env_input.name + "-1")
    assert env is not None
    assert env.type == Artifacts.built_by_softpack
    assert env.state == State.ready


def get_env_from_iter(name: str) -> Optional[Environment]:
    envs = Environment.iter()
    return next((env for env in envs if env.name == name), None)


@pytest.mark.asyncio
async def test_create_from_module(httpx_post, testable_env_input):
    test_files_dir = Path(__file__).parent.parent / "files" / "modules"
    test_file_path = test_files_dir / "shpc.mod"

    with open(test_file_path, "rb") as fh:
        data = fh.read()

    upload = UploadFile(filename="shpc.mod", file=io.BytesIO(data))

    env_name = "some-environment"
    name = "groups/hgi/" + env_name
    module_path = "HGI/common/some_environment"

    result = await Environment.create_from_module(
        file=upload,
        module_path=module_path,
        environment_path=name,
    )

    assert isinstance(result, CreateEnvironmentSuccess)

    upload = UploadFile(filename="shpc.mod", file=io.BytesIO(data))

    result = await Environment.create_from_module(
        file=upload,
        module_path=module_path,
        environment_path=name,
    )

    assert isinstance(result, EnvironmentAlreadyExistsError)

    parent_path = Path(
        Environment.artifacts.group_folder(),
        "hgi",
        env_name,
    )

    readme_path = Path(parent_path, Environment.artifacts.readme_file)
    assert file_in_remote(
        Path(parent_path, Environment.artifacts.environments_file),
        Path(parent_path, Environment.artifacts.module_file),
        readme_path,
        Path(parent_path, Environment.artifacts.generated_from_module_file),
    )

    with open(test_files_dir / "shpc.readme", "rb") as fh:
        expected_readme_data = fh.read()

    tree = Environment.artifacts.repo.head.peel(pygit2.Tree)
    obj = tree[str(readme_path)]
    assert obj is not None
    assert obj.data == expected_readme_data

    envs = list(Environment.iter())
    assert len(envs) == 3

    env = get_env_from_iter(env_name)
    assert env is not None

    package_name = "quay.io/biocontainers/ldsc"
    package_version = "1.0.1--pyhdfd78af_2"

    assert len(env.packages) == 1
    assert env.packages[0].name == package_name
    assert env.packages[0].version == package_version
    assert "module load " + module_path in env.readme
    assert env.type == Artifacts.generated_from_module
    assert env.state == State.ready

    test_modifiy_file_path = test_files_dir / "all_fields.mod"

    with open(test_modifiy_file_path, "rb") as fh:
        data = fh.read()

    upload = UploadFile(filename="all_fields.mod", file=io.BytesIO(data))

    module_path = "HGI/common/all_fields"

    result = await Environment.update_from_module(
        file=upload,
        module_path=module_path,
        environment_path=name,
    )

    assert isinstance(result, UpdateEnvironmentSuccess)
    env = get_env_from_iter(env_name)
    assert env is not None

    package_name = "name_of_container"
    package_version = "1.0.1"

    assert len(env.packages) == 5
    assert env.packages[0].name == package_name
    assert env.packages[0].version == package_version
    assert "module load " + module_path in env.readme
    assert env.type == Artifacts.generated_from_module
    assert env.state == State.ready

    upload = UploadFile(filename="all_fields.mod", file=io.BytesIO(data))

    result = await Environment.update_from_module(
        file=upload,
        module_path=module_path,
        environment_path="users/non/existant",
    )
    assert isinstance(result, EnvironmentNotFoundError)


def test_environmentinput_from_path():
    for path in (
        "users/any1/envName",
        "users/any1/envName-1",
        "users/any1/envName-1.1",
        "users/any1/env_name",
        "groups/some1/env_name-0.1.2.3",
    ):
        assert EnvironmentInput.from_path(path).validate() is None

    for path in [
        "users/any1/.envName",
        "users/any1/envName!",
        "users/any1/..envName-1",
        "users/any1/../envName-1.1",
    ]:
        assert EnvironmentInput.from_path(path).validate() is not None


def test_tagging(httpx_post, testable_env_input: EnvironmentInput) -> None:
    example_env = Environment.iter()[0]
    assert example_env.tags == []

    name, path = example_env.name, example_env.path
    result = Environment.add_tag(name, path, tag="test")
    assert isinstance(result, AddTagSuccess)
    assert result.message == "Tag successfully added"

    result = Environment.add_tag("foo", "users/xyz", tag="test")
    assert isinstance(result, EnvironmentNotFoundError)

    result = Environment.add_tag(name, path, tag="../")
    assert isinstance(result, InvalidInputError)

    result = Environment.add_tag(name, path, tag="")
    assert isinstance(result, InvalidInputError)

    result = Environment.add_tag(name, path, tag="         ")
    assert isinstance(result, InvalidInputError)

    result = Environment.add_tag(name, path, tag="foo  bar")
    assert isinstance(result, InvalidInputError)

    example_env = Environment.iter()[0]
    assert len(example_env.tags) == 1
    assert example_env.tags[0] == "test"

    result = Environment.add_tag(name, path, tag="second test")
    assert isinstance(result, AddTagSuccess)

    example_env = Environment.iter()[0]
    assert list(sorted(example_env.tags)) == list(
        sorted(["test", "second test"])
    )

    result = Environment.add_tag(name, path, tag="test")
    assert isinstance(result, AddTagSuccess)
    assert result.message == "Tag already present"

    example_env = Environment.iter()[0]
    assert list(sorted(example_env.tags)) == list(
        sorted(["test", "second test"])
    )
