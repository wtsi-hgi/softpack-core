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
    file_was_pushed,
    get_user_path_without_environments,
    new_test_artifacts,
)

pytestmark = pytest.mark.repo


@pytest.fixture
def testable_environment_input(mocker) -> EnvironmentInput:
    ad = new_test_artifacts()
    artifacts: Artifacts = ad["artifacts"]
    user = ad["test_user"]

    mocker.patch.object(Environment, 'artifacts', new=artifacts)

    testable_environment_input = EnvironmentInput(
        name="test_env_create",
        path=str(get_user_path_without_environments(artifacts, user)),
        description="description",
        packages=[Package(name="pkg_test")],
    )

    yield testable_environment_input


def test_create(
    httpx_post, testable_environment_input: EnvironmentInput
) -> None:
    result = Environment.create(testable_environment_input)
    assert isinstance(result, CreateEnvironmentSuccess)

    path = Path(
        Environment.artifacts.environments_root,
        testable_environment_input.path,
        testable_environment_input.name,
        ".created",
    )
    assert file_was_pushed(path)

    httpx_post.assert_called_once()
    builder_called_correctly(httpx_post, testable_environment_input)

    result = Environment.create(testable_environment_input)
    assert isinstance(result, EnvironmentAlreadyExistsError)

    orig_name = testable_environment_input.name
    testable_environment_input.name = ""
    result = Environment.create(testable_environment_input)
    assert isinstance(result, InvalidInputError)

    testable_environment_input.name = orig_name
    testable_environment_input.path = "invalid/path"
    result = Environment.create(testable_environment_input)
    assert isinstance(result, InvalidInputError)


def builder_called_correctly(
    post_mock, testable_environment_input: EnvironmentInput
) -> None:
    # TODO: don't mock this; actually have a real builder service to test with?
    # Also need to not hard-code the url here.
    post_mock.assert_called_with(
        "http://0.0.0.0:7080/environments/build",
        json={
            "name": f"{testable_environment_input.path}/{testable_environment_input.name}",
            "model": {
                "description": testable_environment_input.description,
                "packages": [
                    f"{pkg.name}"
                    for pkg in testable_environment_input.packages
                ],
            },
        },
    )


def test_update(httpx_post, testable_environment_input) -> None:
    result = Environment.create(testable_environment_input)
    assert isinstance(result, CreateEnvironmentSuccess)
    httpx_post.assert_called_once()

    testable_environment_input.description = "updated description"
    result = Environment.update(
        testable_environment_input,
        testable_environment_input.path,
        testable_environment_input.name,
    )
    assert isinstance(result, UpdateEnvironmentSuccess)

    builder_called_correctly(httpx_post, testable_environment_input)

    result = Environment.update(
        testable_environment_input, "invalid/path", "invalid_name"
    )
    assert isinstance(result, InvalidInputError)

    testable_environment_input.name = ""
    result = Environment.update(
        testable_environment_input,
        testable_environment_input.path,
        testable_environment_input.name,
    )
    assert isinstance(result, InvalidInputError)

    testable_environment_input.name = "invalid_name"
    testable_environment_input.path = "invalid/path"
    result = Environment.update(
        testable_environment_input, "invalid/path", "invalid_name"
    )
    assert isinstance(result, EnvironmentNotFoundError)


def test_delete(httpx_post, testable_environment_input) -> None:
    result = Environment.delete(
        testable_environment_input.name, testable_environment_input.path
    )
    assert isinstance(result, EnvironmentNotFoundError)

    result = Environment.create(testable_environment_input)
    assert isinstance(result, CreateEnvironmentSuccess)
    httpx_post.assert_called_once()

    path = Path(
        Environment.artifacts.environments_root,
        testable_environment_input.path,
        testable_environment_input.name,
        ".created",
    )
    assert file_was_pushed(path)

    result = Environment.delete(
        testable_environment_input.name, testable_environment_input.path
    )
    assert isinstance(result, DeleteEnvironmentSuccess)

    assert not file_was_pushed(path)


@pytest.mark.asyncio
async def test_write_artifact(httpx_post, testable_environment_input, upload):
    upload.filename = "example.txt"
    upload.content_type = "text/plain"
    upload.read.return_value = b"mock data"

    result = await Environment.write_artifact(
        file=upload,
        folder_path=f"{testable_environment_input.path}/{testable_environment_input.name}",
        file_name=upload.filename,
    )
    assert isinstance(result, InvalidInputError)

    result = Environment.create(testable_environment_input)
    assert isinstance(result, CreateEnvironmentSuccess)
    httpx_post.assert_called_once()

    result = await Environment.write_artifact(
        file=upload,
        folder_path=f"{testable_environment_input.path}/{testable_environment_input.name}",
        file_name=upload.filename,
    )
    assert isinstance(result, WriteArtifactSuccess)

    path = Path(
        Environment.artifacts.environments_root,
        testable_environment_input.path,
        testable_environment_input.name,
        upload.filename,
    )
    assert file_was_pushed(path)

    result = await Environment.write_artifact(
        file=upload,
        folder_path="invalid/env/path",
        file_name=upload.filename,
    )
    assert isinstance(result, InvalidInputError)


@pytest.mark.asyncio
async def test_iter(httpx_post, testable_environment_input, upload):
    envs_filter = Environment.iter()
    count = 0
    for env in envs_filter:
        count += 1

    assert count == 0

    result = Environment.create(testable_environment_input)
    assert isinstance(result, CreateEnvironmentSuccess)
    httpx_post.assert_called_once()

    upload.filename = Artifacts.environments_file
    upload.content_type = "text/plain"
    upload.read.return_value = b"description: test env\npackages:\n- zlib\n"

    result = await Environment.write_artifact(
        file=upload,
        folder_path=f"{testable_environment_input.path}/{testable_environment_input.name}",
        file_name=upload.filename,
    )
    assert isinstance(result, WriteArtifactSuccess)

    envs_filter = Environment.iter()
    count = 0
    for env in envs_filter:
        assert env.name == testable_environment_input.name
        assert any(p.name == "zlib" for p in env.packages)
        count += 1

    assert count == 1
