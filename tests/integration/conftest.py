"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import os

import pytest

from softpack_core.artifacts import Artifacts, Package, app
from softpack_core.schemas.environment import EnvironmentInput
from tests.integration.utils import (
    get_user_path_without_environments,
    new_test_artifacts,
)


@pytest.fixture(scope="package", autouse=True)
def testable_artifacts_setup():
    user = app.settings.artifacts.repo.username.split('@', 1)[0]

    if user is None:
        user = os.getlogin()

    if user is None or user == "main":
        pytest.skip(
            ("Your artifacts repo username must be defined in your config.")
        )

    if app.settings.artifacts.repo.writer is None:
        pytest.skip(
            ("Your artifacts repo writer must be defined in your config.")
        )

    app.settings.artifacts.repo.branch = user


@pytest.fixture()
def httpx_post(mocker):
    post_mock = mocker.patch('httpx.post')
    return post_mock


@pytest.fixture
def testable_env_input(mocker) -> EnvironmentInput:  # type: ignore
    ad = new_test_artifacts()
    artifacts: Artifacts = ad["artifacts"]
    user = ad["test_user"]

    # mocker.patch.object(Environment, 'artifacts', new=artifacts)

    testable_env_input = EnvironmentInput(
        name="test_env_create",
        path=str(get_user_path_without_environments(artifacts, user)),
        description="description",
        packages=[Package(name="pkg_test")],
    )

    yield testable_env_input
