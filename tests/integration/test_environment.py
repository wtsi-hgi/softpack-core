"""Copyright (c) 2023, 2024 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import io
import json
import time
from pathlib import Path
from typing import Optional

import pygit2
import pytest
import yaml
from fastapi import UploadFile
from fastapi.testclient import TestClient

from softpack_core.app import app
from softpack_core.artifacts import Artifacts, artifacts
from softpack_core.config.models import EmailConfig
from softpack_core.schemas.environment import (
    AddTagSuccess,
    BuilderError,
    CreateEnvironmentSuccess,
    DeleteEnvironmentSuccess,
    Environment,
    EnvironmentAlreadyExistsError,
    EnvironmentInput,
    EnvironmentNotFoundError,
    HiddenSuccess,
    InvalidInputError,
    Package,
    PackageInput,
    State,
    UpdateEnvironmentSuccess,
    WriteArtifactSuccess,
)
from tests.integration.utils import builder_called_correctly, file_in_remote

pytestmark = pytest.mark.repo


@pytest.mark.asyncio
async def test_create(
    httpx_post, testable_env_input: EnvironmentInput
) -> None:
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
        artifacts.environments_root,
        testable_env_input.path,
        testable_env_input.name + "-1",
    )
    builtPath = dir / artifacts.built_by_softpack_file
    ymlPath = dir / artifacts.environments_file
    assert file_in_remote(builtPath)
    ymlFile = file_in_remote(ymlPath)
    expected_yaml = {
        "description": "description",
        "packages": ["pkg_test"],
    }
    assert yaml.safe_load(ymlFile.data.decode()) == expected_yaml
    meta_yml = file_in_remote(dir / artifacts.meta_file)
    expected_meta_yml = {"tags": []}
    actual_meta_yml = yaml.safe_load(meta_yml.data.decode())
    del actual_meta_yml["created"]
    assert actual_meta_yml == expected_meta_yml

    dir = Path(
        artifacts.environments_root,
        "groups/not_already_in_repo",
        "test_env_create2-1",
    )
    builtPath = dir / artifacts.built_by_softpack_file
    ymlPath = dir / artifacts.environments_file
    assert file_in_remote(builtPath)
    ymlFile = file_in_remote(ymlPath)
    expected_yaml = {
        "description": "description2",
        "packages": ["pkg_test2", "pkg_test3@3.1"],
    }
    assert yaml.safe_load(ymlFile.data.decode()) == expected_yaml

    meta_yml = file_in_remote(dir / artifacts.meta_file)
    expected_meta_yml = {"tags": ["bar", "foo"]}
    actual_meta_yml = yaml.safe_load(meta_yml.data.decode())
    del actual_meta_yml["created"]
    assert actual_meta_yml == expected_meta_yml

    result = Environment.create(testable_env_input)
    testable_env_input.name = orig_input_name
    assert isinstance(result, CreateEnvironmentSuccess)

    path = Path(
        artifacts.environments_root,
        testable_env_input.path,
        testable_env_input.name + "-2",
        artifacts.built_by_softpack_file,
    )
    assert file_in_remote(path)

    env = Environment.get_env(
        testable_env_input.path, testable_env_input.name + "-2"
    )
    assert env.state == State.queued

    upload = UploadFile(
        filename=Artifacts.builder_out,
        file=io.BytesIO(b""),
    )

    result = await Environment.write_artifact(
        file=upload,
        folder_path=f"{testable_env_input.path}/{testable_env_input.name}-2",
        file_name=upload.filename,
    )
    assert isinstance(result, WriteArtifactSuccess)

    env = Environment.get_env(
        testable_env_input.path, testable_env_input.name + "-2"
    )
    assert env.state == State.failed

    assert isinstance(
        Environment.check_env_exists(
            Path(testable_env_input.path, testable_env_input.name + "-3")
        ),
        EnvironmentNotFoundError,
    )

    result = Environment.create(testable_env_input)
    assert isinstance(result, CreateEnvironmentSuccess)
    assert testable_env_input.name == "test_env_create-2"
    testable_env_input.name = orig_input_name

    assert isinstance(
        Environment.check_env_exists(
            Path(testable_env_input.path, testable_env_input.name + "-3")
        ),
        EnvironmentNotFoundError,
    )

    env = Environment.get_env(
        testable_env_input.path, testable_env_input.name + "-2"
    )
    assert env.state == State.queued

    upload = UploadFile(
        filename=Artifacts.builder_out,
        file=io.BytesIO(b""),
    )

    result = await Environment.write_artifact(
        file=upload,
        folder_path=f"{testable_env_input.path}/{testable_env_input.name}-2",
        file_name=upload.filename,
    )
    assert isinstance(result, WriteArtifactSuccess)

    env = Environment.get_env(
        testable_env_input.path, testable_env_input.name + "-2"
    )
    assert env.state == State.failed

    result = Environment.create(testable_env_input)
    assert isinstance(result, CreateEnvironmentSuccess)
    assert testable_env_input.name == "test_env_create-2"
    testable_env_input.name = orig_input_name

    result = Environment.create(testable_env_input)
    assert isinstance(result, CreateEnvironmentSuccess)
    assert testable_env_input.name == "test_env_create-3"
    testable_env_input.name = orig_input_name

    result = await Environment.write_artifact(
        file=upload,
        folder_path=f"{testable_env_input.path}/{testable_env_input.name}-3",
        file_name=upload.filename,
    )
    assert isinstance(result, WriteArtifactSuccess)

    env = Environment.get_env(
        testable_env_input.path, testable_env_input.name + "-3"
    )
    assert env.state == State.failed

    metadata = env.read_metadata(
        testable_env_input.path, testable_env_input.name + "-3"
    )

    metadata.force_hidden = True

    result = await env.store_metadata(
        f"{testable_env_input.path}/{testable_env_input.name}-3", metadata
    )

    assert isinstance(result, WriteArtifactSuccess)
    assert (
        Environment.get_env(
            testable_env_input.path, testable_env_input.name + "-3"
        )
        is None
    )

    result = Environment.create(testable_env_input)
    assert isinstance(result, CreateEnvironmentSuccess)
    assert testable_env_input.name == "test_env_create-4"


def test_create_no_tags(httpx_post, testable_env_input):
    testable_env_input.tags = None
    result = Environment.create(testable_env_input)
    assert isinstance(result, CreateEnvironmentSuccess)


def test_create_illegal_tags(httpx_post, testable_env_input):
    for tag in ["   ", " ", " leading whitespace", "trailing whitespace "]:
        testable_env_input.tags = [tag]
        result = Environment.create(testable_env_input)
        assert isinstance(result, InvalidInputError)


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
        artifacts.environments_root,
        testable_env_input.path,
        testable_env_input.name,
    )
    builtPath = dir / artifacts.built_by_softpack_file
    ymlPath = dir / artifacts.environments_file
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
        artifacts.environments_root,
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
        artifacts.environments_root,
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


@pytest.mark.asyncio
async def test_email_on_build_complete(
    httpx_post, send_email, testable_env_input
):
    app.settings.environments = EmailConfig(
        fromAddr="hgi@domain.com",
        toAddr="{}@domain.com",
        smtp="server@domain.com",
    )

    testable_env_input.username = "me"

    result = Environment.create(testable_env_input)
    assert isinstance(result, CreateEnvironmentSuccess)

    client = TestClient(app.router)
    resp = client.post(
        url="/upload?"
        + testable_env_input.path
        + "/"
        + testable_env_input.name,
        files=[
            ("file", (Artifacts.module_file, "")),
        ],
    )
    assert resp.status_code == 200
    assert resp.json().get("message") == "Successfully written artifact(s)"

    assert send_email.call_count == 1

    assert send_email.call_args[0][0] == app.settings.environments
    assert "built sucessfully" in send_email.call_args[0][1]
    assert "The error was" not in send_email.call_args[0][1]
    assert send_email.call_args[0][2] == "Your environment is ready!"
    assert send_email.call_args[0][3] == "me"

    client = TestClient(app.router)
    resp = client.post(
        url="/upload?"
        + testable_env_input.path
        + "/"
        + testable_env_input.name,
        files=[
            ("file", (Artifacts.module_file, "1")),
        ],
    )

    assert send_email.call_count == 1

    result = Environment.create(testable_env_input)
    assert isinstance(result, CreateEnvironmentSuccess)

    client = TestClient(app.router)
    resp = client.post(
        url="/upload?"
        + testable_env_input.path
        + "/"
        + testable_env_input.name,
        files=[
            ("file", (Artifacts.builder_out, "")),
        ],
    )
    assert resp.status_code == 200
    assert resp.json().get("message") == "Successfully written artifact(s)"

    assert send_email.call_count == 2

    assert send_email.call_args[0][0] == app.settings.environments
    assert "failed to build" in send_email.call_args[0][1]
    assert (
        "The error was a build error. Contact your softpack administrator."
        in send_email.call_args[0][1]
    )
    assert send_email.call_args[0][2] == "Your environment failed to build"
    assert send_email.call_args[0][3] == "me"

    testable_env_input.username = ""

    result = Environment.create(testable_env_input)
    assert isinstance(result, CreateEnvironmentSuccess)

    client = TestClient(app.router)
    resp = client.post(
        url="/upload?"
        + testable_env_input.path
        + "/"
        + testable_env_input.name,
        files=[
            ("file", (Artifacts.builder_out, "")),
        ],
    )
    assert resp.status_code == 200
    assert resp.json().get("message") == "Successfully written artifact(s)"

    assert send_email.call_count == 2

    testable_env_input.username = "me"
    result = Environment.create(testable_env_input)
    assert isinstance(result, CreateEnvironmentSuccess)

    client = TestClient(app.router)
    resp = client.post(
        url="/upload?"
        + testable_env_input.path
        + "/"
        + testable_env_input.name,
        files=[
            (
                "file",
                (
                    Artifacts.builder_out,
                    "concretization failed for the following reasons:",
                ),
            ),
        ],
    )
    assert resp.status_code == 200
    assert resp.json().get("message") == "Successfully written artifact(s)"

    assert send_email.call_count == 3

    assert send_email.call_args[0][0] == app.settings.environments
    assert "failed to build" in send_email.call_args[0][1]
    assert "version conflict" in send_email.call_args[0][1]
    assert send_email.call_args[0][2] == "Your environment failed to build"
    assert send_email.call_args[0][3] == "me"


def test_failure_reason_from_build_log(
    httpx_post, send_email, testable_env_input
):
    result = Environment.create(testable_env_input)
    assert isinstance(result, CreateEnvironmentSuccess)

    client = TestClient(app.router)
    client.post(
        url="/upload?"
        + testable_env_input.path
        + "/"
        + testable_env_input.name,
        files=[
            ("file", (Artifacts.builder_out, "")),
        ],
    )

    env = Environment.get_env(testable_env_input.path, testable_env_input.name)

    assert env.failure_reason == "build"

    client.post(
        url="/upload?"
        + testable_env_input.path
        + "/"
        + testable_env_input.name,
        files=[
            (
                "file",
                (
                    Artifacts.builder_out,
                    "concretization failed for the following reasons:",
                ),
            ),
        ],
    )

    env = Environment.get_env(testable_env_input.path, testable_env_input.name)

    assert env.failure_reason == "concretization"


def test_iter(testable_env_input):
    envs = list(Environment.iter())
    assert len(envs) == 2
    assert envs[0].state == State.queued
    assert envs[1].state == State.queued


@pytest.mark.asyncio
async def test_states(httpx_post, testable_env_input, mocker):
    orig_name = testable_env_input.name
    startTime = time.time() - 1
    result = Environment.create(testable_env_input)
    endTime = time.time() + 1
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
    assert env.created >= startTime and env.created <= endTime

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
        artifacts.group_folder(),
        "hgi",
        env_name,
    )

    readme_path = Path(parent_path, artifacts.readme_file)
    assert file_in_remote(
        Path(parent_path, artifacts.environments_file),
        Path(parent_path, artifacts.module_file),
        readme_path,
        Path(parent_path, artifacts.generated_from_module_file),
    )

    with open(test_files_dir / "shpc.readme", "rb") as fh:
        expected_readme_data = fh.read()

    tree = artifacts.repo.head.peel(pygit2.Tree)
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


@pytest.mark.asyncio
async def test_tagging(
    httpx_post, testable_env_input: EnvironmentInput
) -> None:
    example_env = Environment.iter()[0]
    assert example_env.tags == []

    name, path = example_env.name, example_env.path
    result = await Environment.add_tag(name, path, tag="test")
    assert isinstance(result, AddTagSuccess)
    assert result.message == "Tag successfully added"

    result = await Environment.add_tag("foo", "users/xyz", tag="test")
    assert isinstance(result, EnvironmentNotFoundError)

    result = await Environment.add_tag(name, path, tag="../")
    assert isinstance(result, InvalidInputError)

    result = await Environment.add_tag(name, path, tag="")
    assert isinstance(result, InvalidInputError)

    result = await Environment.add_tag(name, path, tag="         ")
    assert isinstance(result, InvalidInputError)

    result = await Environment.add_tag(name, path, tag="foo  bar")
    assert isinstance(result, InvalidInputError)

    example_env = Environment.iter()[0]
    assert len(example_env.tags) == 1
    assert example_env.tags[0] == "test"

    result = await Environment.add_tag(name, path, tag="second test")
    assert isinstance(result, AddTagSuccess)

    example_env = Environment.iter()[0]
    assert example_env.tags == ["second test", "test"]

    result = await Environment.add_tag(name, path, tag="test")
    assert isinstance(result, AddTagSuccess)
    assert result.message == "Tag already present"

    example_env = Environment.iter()[0]
    assert example_env.tags == ["second test", "test"]


@pytest.mark.asyncio
async def test_hidden(
    httpx_post, testable_env_input: EnvironmentInput
) -> None:
    example_env = Environment.iter()[0]
    assert not example_env.hidden
    name, path = example_env.name, example_env.path

    result = await Environment.set_hidden(name, path, True)
    assert isinstance(result, HiddenSuccess)
    assert result.message == "Hidden metadata set"
    example_env = Environment.iter()[0]
    assert example_env.hidden

    result = await Environment.set_hidden(name, path, True)
    assert isinstance(result, HiddenSuccess)
    assert result.message == "Hidden metadata already set"
    example_env = Environment.iter()[0]
    assert example_env.hidden

    result = await Environment.set_hidden(name, path, False)
    assert isinstance(result, HiddenSuccess)
    assert result.message == "Hidden metadata set"
    example_env = Environment.iter()[0]
    assert not example_env.hidden

    result = await Environment.set_hidden(name, path, False)
    assert isinstance(result, HiddenSuccess)
    assert result.message == "Hidden metadata already set"
    example_env = Environment.iter()[0]
    assert not example_env.hidden

    result = await Environment.set_hidden(name, path, True)
    assert isinstance(result, HiddenSuccess)
    assert result.message == "Hidden metadata set"
    example_env = Environment.iter()[0]
    assert example_env.hidden


@pytest.mark.asyncio
async def test_force_hidden(
    httpx_post, testable_env_input: EnvironmentInput
) -> None:
    first_env = Environment.iter()[0]
    metadata = Environment.read_metadata(first_env.path, first_env.name)
    metadata.force_hidden = True
    await Environment.store_metadata(
        Path(first_env.path, first_env.name), metadata
    )

    new_first = Environment.iter()[0]

    assert first_env.path != new_first.path or first_env.name != new_first.name


def test_environment_with_requested_recipe(
    httpx_post, testable_env_input: EnvironmentInput
) -> None:
    testable_env_input.packages[0].name = (
        "*" + testable_env_input.packages[0].name
    )
    result = Environment.create(testable_env_input)
    assert isinstance(result, CreateEnvironmentSuccess)
    httpx_post.assert_not_called()


def test_interpreters(
    httpx_post, testable_env_input: EnvironmentInput
) -> None:
    env = EnvironmentInput.from_path("users/me/my_env-1")
    env.packages = [
        PackageInput.from_name("pkg@1"),
        PackageInput.from_name("pkg@2"),
    ]

    assert isinstance(Environment.create(env), CreateEnvironmentSuccess)

    artifacts.commit_and_push(
        artifacts.create_file(
            Path(Artifacts.environments_root, env.path, env.name),
            Artifacts.spack_file,
            json.dumps(
                {
                    "concrete_specs": {
                        "long_hash": {
                            "name": "python",
                            "version": "1.2.3",
                        }
                    }
                }
            ),
            False,
            True,
        ),
        "add spack.lock for environment",
    )

    env = Environment.from_artifact(artifacts.get(env.path, env.name))

    assert env.interpreters.python == "1.2.3"
    assert env.interpreters.r is None

    artifacts.commit_and_push(
        artifacts.create_file(
            Path(Artifacts.environments_root, env.path, env.name),
            Artifacts.spack_file,
            json.dumps(
                {
                    "concrete_specs": {
                        "long_hash": {
                            "name": "r",
                            "version": "4.5.6",
                        }
                    }
                }
            ),
            False,
            True,
        ),
        "add spack.lock for environment",
    )

    env = Environment.from_artifact(artifacts.get(env.path, env.name))

    assert env.interpreters.python is None
    assert env.interpreters.r == "4.5.6"

    artifacts.commit_and_push(
        artifacts.create_file(
            Path(Artifacts.environments_root, env.path, env.name),
            Artifacts.spack_file,
            json.dumps(
                {
                    "concrete_specs": {
                        "short_hash": {
                            "name": "python",
                            "version": "3.11.4",
                        },
                        "long_hash": {
                            "name": "r",
                            "version": "4.4.1",
                        },
                    }
                }
            ),
            False,
            True,
        ),
        "add spack.lock for environment",
    )

    env = Environment.from_artifact(artifacts.get(env.path, env.name))

    assert env.interpreters.python == "3.11.4"
    assert env.interpreters.r == "4.4.1"

    env = EnvironmentInput.from_path("users/me/my_env-2")
    env.packages = [
        PackageInput.from_name("r@1"),
    ]

    assert isinstance(Environment.create(env), CreateEnvironmentSuccess)

    artifacts.commit_and_push(
        artifacts.create_file(
            Path(Artifacts.environments_root, env.path, env.name),
            Artifacts.spack_file,
            json.dumps(
                {
                    "concrete_specs": {
                        "short_hash": {
                            "name": "python",
                            "version": "3.11.4",
                        },
                        "long_hash": {
                            "name": "r",
                            "version": "4.4.1",
                        },
                    }
                }
            ),
            False,
            True,
        ),
        "add spack.lock for environment",
    )

    env = Environment.from_artifact(artifacts.get(env.path, env.name))

    assert env.interpreters.python == "3.11.4"
    assert env.interpreters.r is None

    env = EnvironmentInput.from_path("users/me/my_env-3")
    env.packages = [
        PackageInput.from_name("python@2"),
    ]

    assert isinstance(Environment.create(env), CreateEnvironmentSuccess)

    artifacts.commit_and_push(
        artifacts.create_file(
            Path(Artifacts.environments_root, env.path, env.name),
            Artifacts.spack_file,
            json.dumps(
                {
                    "concrete_specs": {
                        "short_hash": {
                            "name": "python",
                            "version": "3.11.4",
                        },
                        "long_hash": {
                            "name": "r",
                            "version": "4.4.1",
                        },
                    }
                }
            ),
            False,
            True,
        ),
        "add spack.lock for environment",
    )

    env = Environment.from_artifact(artifacts.get(env.path, env.name))

    assert env.interpreters.python is None
    assert env.interpreters.r == "4.4.1"
