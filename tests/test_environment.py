"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from softpack_core.artifacts import Artifacts
from softpack_core.schemas.environment import (
    CreateEnvironmentSuccess,
    Environment,
    EnvironmentInput,
    PackageInput,
)

from .test_pygit import copy_of_repo, get_user_path_without_environments


def test_create(mocker):
    artifacts = Artifacts()
    environment = Environment(
        id="", name="", path="", description="", packages=[], state=None
    )
    with copy_of_repo(artifacts) as temp_dir:
        print(temp_dir)
        environment.artifacts = artifacts
        push_mock = mocker.patch('pygit2.Remote.push')
        post_mock = mocker.patch('httpx.post')
        env_input = EnvironmentInput(
            name="environment_test",
            path=str(get_user_path_without_environments(artifacts)),
            description="description",
            packages=[PackageInput(name="pkg_test")],
        )
        result = environment.create(env_input)
        print(result)

        assert isinstance(result, CreateEnvironmentSuccess)
        push_mock.assert_called_once()
        post_mock.assert_called_once()
