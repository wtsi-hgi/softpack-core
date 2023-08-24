"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

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

from softpack_core.artifacts import Artifacts, app


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
    # push_mock.assert_called_once()

    # TODO: don't mock this; actually have a real builder service to test with?
    post_mock.assert_called_once_with(
        "http://0.0.0.0:7080/environments/build",
        json={
            "name": f"{env_input.path}/{env_input.name}",
            "model": {
                "description": env_input.description,
                "packages": [f"{pkg.name}" for pkg in env_input.packages],
            },
        },
    )

    result = environment.create(env_input)
    assert isinstance(result, EnvironmentAlreadyExistsError)

    env_input.name = ""
    result = environment.create(env_input)
    assert isinstance(result, InvalidInputError)

    env_input.name = environment.name
    env_input.path = "invalid/path"
    result = environment.create(env_input)
    assert isinstance(result, InvalidInputError)
