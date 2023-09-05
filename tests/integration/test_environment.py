"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from pathlib import Path

import pytest

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
from tests.integration.utils import (
    file_in_remote,
    get_user_path_without_environments,
    new_test_artifacts,
)

pytestmark = pytest.mark.repo


@pytest.fixture
def testable_env_input(mocker) -> EnvironmentInput:
    ad = new_test_artifacts()
    artifacts: Artifacts = ad["artifacts"]
    user = ad["test_user"]

    mocker.patch.object(Environment, 'artifacts', new=artifacts)

    testable_env_input = EnvironmentInput(
        name="test_env_create",
        path=str(get_user_path_without_environments(artifacts, user)),
        description="description",
        packages=[Package(name="pkg_test")],
    )

    yield testable_env_input


def test_create(httpx_post, testable_env_input: EnvironmentInput) -> None:
    result = Environment.create(testable_env_input)
    assert isinstance(result, CreateEnvironmentSuccess)

    path = Path(
        Environment.artifacts.environments_root,
        testable_env_input.path,
        testable_env_input.name,
        ".created",
    )
    assert file_in_remote(path)

    httpx_post.assert_called_once()
    builder_called_correctly(httpx_post, testable_env_input)

    result = Environment.create(testable_env_input)
    assert isinstance(result, EnvironmentAlreadyExistsError)

    orig_name = testable_env_input.name
    testable_env_input.name = ""
    result = Environment.create(testable_env_input)
    assert isinstance(result, InvalidInputError)

    testable_env_input.name = orig_name
    testable_env_input.path = "invalid/path"
    result = Environment.create(testable_env_input)
    assert isinstance(result, InvalidInputError)


def builder_called_correctly(
    post_mock, testable_env_input: EnvironmentInput
) -> None:
    # TODO: don't mock this; actually have a real builder service to test with?
    # Also need to not hard-code the url here.
    post_mock.assert_called_with(
        "http://0.0.0.0:7080/environments/build",
        json={
            "name": f"{testable_env_input.path}/{testable_env_input.name}",
            "model": {
                "description": testable_env_input.description,
                "packages": [
                    f"{pkg.name}" for pkg in testable_env_input.packages
                ],
            },
        },
    )


def test_update(httpx_post, testable_env_input) -> None:
    result = Environment.create(testable_env_input)
    assert isinstance(result, CreateEnvironmentSuccess)
    httpx_post.assert_called_once()

    testable_env_input.description = "updated description"
    result = Environment.update(
        testable_env_input,
        testable_env_input.path,
        testable_env_input.name,
    )
    assert isinstance(result, UpdateEnvironmentSuccess)

    builder_called_correctly(httpx_post, testable_env_input)

    result = Environment.update(
        testable_env_input, "invalid/path", "invalid_name"
    )
    assert isinstance(result, InvalidInputError)

    testable_env_input.name = ""
    result = Environment.update(
        testable_env_input,
        testable_env_input.path,
        testable_env_input.name,
    )
    assert isinstance(result, InvalidInputError)

    testable_env_input.name = "invalid_name"
    testable_env_input.path = "invalid/path"
    result = Environment.update(
        testable_env_input, "invalid/path", "invalid_name"
    )
    assert isinstance(result, EnvironmentNotFoundError)


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
        ".created",
    )
    assert file_in_remote(path)

    result = Environment.delete(
        testable_env_input.name, testable_env_input.path
    )
    assert isinstance(result, DeleteEnvironmentSuccess)

    assert not file_in_remote(path)


@pytest.mark.asyncio
async def test_write_artifact(httpx_post, testable_env_input, upload):
    upload.filename = "example.txt"
    upload.content_type = "text/plain"
    upload.read.return_value = b"mock data"

    result = await Environment.write_artifact(
        file=upload,
        folder_path=f"{testable_env_input.path}/{testable_env_input.name}",
        file_name=upload.filename,
    )
    assert isinstance(result, InvalidInputError)

    result = Environment.create(testable_env_input)
    assert isinstance(result, CreateEnvironmentSuccess)
    httpx_post.assert_called_once()

    result = await Environment.write_artifact(
        file=upload,
        folder_path=f"{testable_env_input.path}/{testable_env_input.name}",
        file_name=upload.filename,
    )
    assert isinstance(result, WriteArtifactSuccess)

    path = Path(
        Environment.artifacts.environments_root,
        testable_env_input.path,
        testable_env_input.name,
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
async def test_iter(httpx_post, testable_env_input, upload):
    envs_filter = Environment.iter()
    count = 0
    for env in envs_filter:
        count += 1

    assert count == 0

    result = Environment.create(testable_env_input)
    assert isinstance(result, CreateEnvironmentSuccess)
    httpx_post.assert_called_once()

    upload.filename = Artifacts.environments_file
    upload.content_type = "text/plain"
    upload.read.return_value = b"description: test env\npackages:\n- zlib\n"

    result = await Environment.write_artifact(
        file=upload,
        folder_path=f"{testable_env_input.path}/{testable_env_input.name}",
        file_name=upload.filename,
    )
    assert isinstance(result, WriteArtifactSuccess)

    envs_filter = Environment.iter()
    count = 0
    for env in envs_filter:
        assert env.name == testable_env_input.name
        assert any(p.name == "zlib" for p in env.packages)
        count += 1

    assert count == 1
