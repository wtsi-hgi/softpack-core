"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from pathlib import Path

import pygit2
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
    httpx_post.assert_called_once()
    builder_called_correctly(httpx_post, testable_env_input)

    result = Environment.create(
        EnvironmentInput(
            name="test_env_create2",
            path="groups/not_already_in_repo",
            description="description2",
            packages=[Package(name="pkg_test2")],
        )
    )
    assert isinstance(result, CreateEnvironmentSuccess)
    httpx_post.assert_called()

    path = Path(
        Environment.artifacts.environments_root,
        testable_env_input.path,
        testable_env_input.name,
        Environment.artifacts.built_by_softpack_file,
    )
    assert file_in_remote(path)

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
        Artifacts.built_by_softpack_file,
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
    upload.read.return_value = b"description: test env\npackages:\n  - zlib\n"

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
        assert env.type == Artifacts.built_by_softpack
        count += 1

    assert count == 1


@pytest.mark.asyncio
async def test_create_from_module(httpx_post, testable_env_input, upload):
    test_files_dir = Path(__file__).parent.parent / "files" / "modules"
    test_file_path = test_files_dir / "shpc.mod"

    with open(test_file_path, "rb") as fh:
        upload.filename = "shpc.mod"
        upload.content_type = "text/plain"
        upload.read.return_value = fh.read()

    env_name = "some-environment"
    name = "groups/hgi/" + env_name
    module_path = "HGI/common/some_environment"

    result = await Environment.create_from_module(
        file=upload,
        module_path=module_path,
        environment_path=name,
    )

    assert isinstance(result, CreateEnvironmentSuccess)

    parent_path = Path(
        Environment.artifacts.group_folder(),
        "hgi",
        env_name,
    )

    readme_path = Path(parent_path, Environment.artifacts.readme_file)
    assert file_in_remote(
        Path(parent_path, Environment.artifacts.environments_file),
        Path(parent_path, Environment.artifacts.module_file),
        readme_path,
        Path(parent_path, Environment.artifacts.generated_from_module_file),
    )

    with open(test_files_dir / "shpc.readme", "rb") as fh:
        expected_readme_data = fh.read()

    tree = Environment.artifacts.repo.head.peel(pygit2.Tree)
    obj = tree[str(readme_path)]
    assert obj is not None
    assert obj.data == expected_readme_data

    envs = list(Environment.iter())

    assert len(envs) == 1

    env = envs[0]

    package_name = "quay.io/biocontainers/ldsc@1.0.1--pyhdfd78af_2"

    assert env.name == env_name
    assert len(env.packages) == 1 and env.packages[0].name == package_name
    assert "module load " + module_path in env.readme
    assert env.type == Artifacts.generated_from_module
