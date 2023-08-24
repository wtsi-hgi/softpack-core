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

from tests.integration.conftest import (new_test_artifacts,
                                        get_user_path_without_environments)
from .test_artifacts import file_was_pushed

from softpack_core.artifacts import Artifacts


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

    yield artifacts, environment, env_input


def test_create(mocker, testable_environment) -> None:
    _, environment, env_input = testable_environment
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
    _, environment, env_input = testable_environment
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
