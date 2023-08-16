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
    InvalidInputError,
    EnvironmentAlreadyExistsError,
)

from .test_pygit import copy_of_repo, get_user_path_without_environments


def test_create(mocker):
    artifacts = Artifacts()
    environment = Environment(
        id="", name="", path="", description="", packages=[], state=None
    )
    with copy_of_repo(artifacts) as temp_dir:
        environment.artifacts = artifacts
        push_mock = mocker.patch('pygit2.Remote.push')
        post_mock = mocker.patch('httpx.post')
        env_name = "environment_test"
        env_input = EnvironmentInput(
            name=env_name,
            path=str(get_user_path_without_environments(artifacts)),
            description="description",
            packages=[PackageInput(name="pkg_test")],
        )
        result = environment.create(env_input)

        assert isinstance(result, CreateEnvironmentSuccess)
        push_mock.assert_called_once()
        post_mock.assert_called_once()

        post_mock.assert_called_with("http://0.0.0.0:7080/environments/build", json={
                "name": f"{env_input.path}/{env_input.name}",
                "model": {
                    "description": env_input.description,
                    "packages": [f"{pkg.name}" for pkg in env_input.packages],
                },
            })
        
        result = environment.create(env_input)
        assert isinstance(result, EnvironmentAlreadyExistsError)
        
        env_input.name = ""
        result = environment.create(env_input)
        assert isinstance(result, InvalidInputError)

        env_input.name = env_name
        env_input.path = "invalid/path"
        result = environment.create(env_input)
        assert isinstance(result, InvalidInputError)

