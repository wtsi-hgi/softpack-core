"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import pygit2
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

# from .test_pygit import copy_of_repo, get_user_path_without_environments


# @pytest.fixture
# def temp_git_repo(mocker):
#     artifacts = Artifacts()
#     environment = Environment(
#         id="",
#         name="environment_test",
#         path=str(get_user_path_without_environments(artifacts)),
#         description="description",
#         packages=[Package(id="", name="pkg_test")],
#         state=None,
#     )
#     with copy_of_repo(artifacts) as temp_dir:
#         # repo needs to be modified via environment obj for change to persist
#         environment.artifacts.repo = pygit2.Repository(temp_dir)
#         mocker.patch('pygit2.Remote.push')
#         mocker.patch('httpx.post')
#         env_input = EnvironmentInput(
#             name=environment.name,
#             path=environment.path,
#             description=environment.description,
#             packages=environment.packages,
#         )

#         environment.create(env_input)

#         yield environment, artifacts, env_input


# def test_create(mocker, temp_git_repo) -> None:
#     # Setup
#     environment, artifacts, env_input = temp_git_repo
#     push_mock = mocker.patch('pygit2.Remote.push')
#     post_mock = mocker.patch('httpx.post')

#     # Tests
#     env_input.name = "test_create_new"
#     result = environment.create(env_input)
#     assert isinstance(result, CreateEnvironmentSuccess)
#     push_mock.assert_called_once()
#     post_mock.assert_called_once()

#     post_mock.assert_called_with(
#         "http://0.0.0.0:7080/environments/build",
#         json={
#             "name": f"{env_input.path}/{env_input.name}",
#             "model": {
#                 "description": env_input.description,
#                 "packages": [f"{pkg.name}" for pkg in env_input.packages],
#             },
#         },
#     )

#     result = environment.create(env_input)
#     assert isinstance(result, EnvironmentAlreadyExistsError)

#     env_input.name = ""
#     result = environment.create(env_input)
#     assert isinstance(result, InvalidInputError)

#     env_input.name = environment.name
#     env_input.path = "invalid/path"
#     result = environment.create(env_input)
#     assert isinstance(result, InvalidInputError)


# def test_update(mocker, temp_git_repo) -> None:
#     # Setup
#     environment, artifacts, env_input = temp_git_repo
#     post_mock = mocker.patch('httpx.post')

#     # Tests
#     env_input.path = str(get_user_path_without_environments(artifacts))
#     env_input.description = "updated description"
#     result = environment.update(env_input, env_input.path, env_input.name)
#     assert isinstance(result, UpdateEnvironmentSuccess)
#     post_mock.assert_called_once()

#     result = environment.update(env_input, "invalid/path", "invalid_name")
#     assert isinstance(result, InvalidInputError)

#     env_input.name = ""
#     result = environment.update(env_input, "invalid/path", "invalid_name")
#     assert isinstance(result, InvalidInputError)

#     env_input.name = "invalid_name"
#     env_input.path = "invalid/path"
#     result = environment.update(env_input, "invalid/path", "invalid_name")
#     assert isinstance(result, EnvironmentNotFoundError)


# def test_delete(mocker, temp_git_repo) -> None:
#     # Setup
#     environment, artifacts, env_input = temp_git_repo
#     mocker.patch('pygit2.Remote.push')
#     mocker.patch('httpx.post')

#     # Test
#     result = environment.delete(env_input.name, env_input.path)
#     assert isinstance(result, DeleteEnvironmentSuccess)

#     env_input.name = "invalid_name"
#     env_input.path = "invalid/path"
#     result = environment.delete(env_input.name, env_input.path)
#     assert isinstance(result, EnvironmentNotFoundError)


# @pytest.mark.asyncio
# async def test_write_artifact(mocker, temp_git_repo):
#     # Setup
#     environment, artifacts, env_input = temp_git_repo
#     push_mock = mocker.patch('pygit2.Remote.push')
#     mocker.patch('httpx.post')

#     # Mock the file upload
#     upload = mocker.Mock(spec=UploadFile)
#     upload.filename = "example.txt"
#     upload.content_type = "text/plain"
#     upload.read.return_value = b"mock data"

#     # Test
#     result = await environment.write_artifact(
#         file=upload,
#         folder_path=f"{env_input.path}/{env_input.name}",
#         file_name=upload.filename,
#     )
#     assert isinstance(result, WriteArtifactSuccess)
#     push_mock.assert_called_once()

#     result = await environment.write_artifact(
#         file=upload,
#         folder_path="invalid/env/path",
#         file_name=upload.filename,
#     )
#     assert isinstance(result, InvalidInputError)
