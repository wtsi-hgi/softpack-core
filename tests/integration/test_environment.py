"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from pathlib import Path

import pytest
from starlette.datastructures import UploadFile

from softpack_core.artifacts import Artifacts
from softpack_core.schemas.environment import (
    CreateEnvironmentSuccess,
    DeleteEnvironmentSuccess,
    Environment,
    EnvironmentAlreadyExistsError,
    EnvironmentInput,
    EnvironmentNotFoundError,
    InvalidInputError,
    Package,
    UpdateEnvironmentSuccess,
    WriteArtifactSuccess,
)
from tests.integration.conftest import (
    file_was_pushed,
    get_user_path_without_environments,
    new_test_artifacts,
)


@pytest.fixture
def testable_environment(mocker):
    ad = new_test_artifacts()
    artifacts: Artifacts = ad["artifacts"]
    user = ad["test_user"]

    mocker.patch.object(Environment, 'artifacts', new=artifacts)

    environment = Environment(
        id="",
        name="test_env_create",
        path=str(get_user_path_without_environments(artifacts, user)),
        description="description",
        packages=[Package(id="", name="pkg_test")],
        state=None,
    )

    env_input = EnvironmentInput(
        name=environment.name,
        path=environment.path,
        description=environment.description,
        packages=environment.packages,
    )

    yield environment, env_input


def test_create(mocker, testable_environment) -> None:
    environment, env_input = testable_environment
    post_mock = mocker.patch('httpx.post')

    result = environment.create(env_input)
    assert isinstance(result, CreateEnvironmentSuccess)

    path = Path(env_input.path, env_input.name, ".created")
    assert file_was_pushed(path)

    post_mock.assert_called_once()
    builder_called_correctly(post_mock, env_input)

    result = environment.create(env_input)
    assert isinstance(result, EnvironmentAlreadyExistsError)

    env_input.name = ""
    result = environment.create(env_input)
    assert isinstance(result, InvalidInputError)

    env_input.name = environment.name
    env_input.path = "invalid/path"
    result = environment.create(env_input)
    assert isinstance(result, InvalidInputError)


def builder_called_correctly(post_mock, env_input: EnvironmentInput) -> None:
    # TODO: don't mock this; actually have a real builder service to test with?
    # Also need to not hard-code the url here.
    post_mock.assert_called_with(
        "http://0.0.0.0:7080/environments/build",
        json={
            "name": f"{env_input.path}/{env_input.name}",
            "model": {
                "description": env_input.description,
                "packages": [f"{pkg.name}" for pkg in env_input.packages],
            },
        },
    )


def test_update(mocker, testable_environment) -> None:
    environment, env_input = testable_environment
    post_mock = mocker.patch('httpx.post')

    result = environment.create(env_input)
    assert isinstance(result, CreateEnvironmentSuccess)
    post_mock.assert_called_once()

    env_input.description = "updated description"
    result = environment.update(env_input, env_input.path, env_input.name)
    assert isinstance(result, UpdateEnvironmentSuccess)

    builder_called_correctly(post_mock, env_input)

    result = environment.update(env_input, "invalid/path", "invalid_name")
    assert isinstance(result, InvalidInputError)

    env_input.name = ""
    result = environment.update(env_input, env_input.path, env_input.name)
    assert isinstance(result, InvalidInputError)

    env_input.name = "invalid_name"
    env_input.path = "invalid/path"
    result = environment.update(env_input, "invalid/path", "invalid_name")
    assert isinstance(result, EnvironmentNotFoundError)


def test_delete(mocker, testable_environment) -> None:
    environment, env_input = testable_environment

    result = environment.delete(env_input.name, env_input.path)
    assert isinstance(result, EnvironmentNotFoundError)

    post_mock = mocker.patch('httpx.post')
    result = environment.create(env_input)
    assert isinstance(result, CreateEnvironmentSuccess)
    post_mock.assert_called_once()

    path = Path(env_input.path, env_input.name, ".created")
    assert file_was_pushed(path)

    result = environment.delete(env_input.name, env_input.path)
    assert isinstance(result, DeleteEnvironmentSuccess)

    assert not file_was_pushed(path)


@pytest.mark.asyncio
async def test_write_artifact(mocker, testable_environment):
    environment, env_input = testable_environment

    upload = mocker.Mock(spec=UploadFile)
    upload.filename = "example.txt"
    upload.content_type = "text/plain"
    upload.read.return_value = b"mock data"

    result = await environment.write_artifact(
        file=upload,
        folder_path=f"{env_input.path}/{env_input.name}",
        file_name=upload.filename,
    )
    assert isinstance(result, InvalidInputError)

    post_mock = mocker.patch('httpx.post')
    result = environment.create(env_input)
    assert isinstance(result, CreateEnvironmentSuccess)
    post_mock.assert_called_once()

    result = await environment.write_artifact(
        file=upload,
        folder_path=f"{env_input.path}/{env_input.name}",
        file_name=upload.filename,
    )
    assert isinstance(result, WriteArtifactSuccess)

    path = Path(env_input.path, env_input.name, upload.filename)
    assert file_was_pushed(path)

    result = await environment.write_artifact(
        file=upload,
        folder_path="invalid/env/path",
        file_name=upload.filename,
    )
    assert isinstance(result, InvalidInputError)


@pytest.mark.asyncio
async def test_iter(mocker, testable_environment):
    environment, env_input = testable_environment

    envs_filter = environment.iter()
    count = 0
    for env in envs_filter:
        count += 1

    assert count == 0

    post_mock = mocker.patch('httpx.post')
    result = environment.create(env_input)
    assert isinstance(result, CreateEnvironmentSuccess)
    post_mock.assert_called_once()

    upload = mocker.Mock(spec=UploadFile)
    upload.filename = Artifacts.environments_file
    upload.content_type = "text/plain"
    upload.read.return_value = b"description: test env\npackages:\n- zlib\n"

    result = await environment.write_artifact(
        file=upload,
        folder_path=f"{env_input.path}/{env_input.name}",
        file_name=upload.filename,
    )
    assert isinstance(result, WriteArtifactSuccess)

    envs_filter = environment.iter()
    count = 0
    for env in envs_filter:
        assert env.name == env_input.name
        assert any(p.name == "zlib" for p in env.packages)
        count += 1

    assert count == 1
