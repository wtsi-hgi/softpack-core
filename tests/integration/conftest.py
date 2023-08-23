"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import os
from pathlib import Path
import pygit2
import pytest
import tempfile
import shutil

from softpack_core.artifacts import Artifacts, app

artifacts_dict = dict[str, str | pygit2.Oid | Path
                      | Artifacts | tempfile.TemporaryDirectory[str]]


@pytest.fixture(scope="package", autouse=True)
def testable_artifacts() -> artifacts_dict:
    repo_url = os.getenv("SOFTPACK_TEST_ARTIFACTS_REPO_URL")
    repo_user = os.getenv("SOFTPACK_TEST_ARTIFACTS_REPO_USER")
    repo_token = os.getenv("SOFTPACK_TEST_ARTIFACTS_REPO_TOKEN")
    if repo_url is None or repo_user is None or repo_token is None:
        pytest.skip(("SOFTPACK_TEST_ARTIFACTS_REPO_URL, _USER and _TOKEN "
                     "env vars are all required for these tests"))

    user = repo_user.split('@', 1)[0]
    app.settings.artifacts.repo.url = repo_url
    app.settings.artifacts.repo.username = repo_user
    app.settings.artifacts.repo.author = user
    app.settings.artifacts.repo.email = repo_user
    app.settings.artifacts.repo.writer = repo_token
    temp_dir = tempfile.TemporaryDirectory()
    app.settings.artifacts.path = Path(temp_dir.name)
    app.settings.artifacts.repo.branch = user

    artifacts = Artifacts()
    dict = reset_test_repo(artifacts)
    dict["temp_dir"] = temp_dir
    dict["artifacts"] = artifacts

    return dict


def reset_test_repo(artifacts: Artifacts) -> artifacts_dict:
    delete_environments_folder_from_test_repo(artifacts)

    return create_initial_test_repo_state(artifacts)


def delete_environments_folder_from_test_repo(artifacts: Artifacts):
    tree = artifacts.repo.head.peel(pygit2.Tree)

    if artifacts.environments_root in tree:
        shutil.rmtree(Path(app.settings.artifacts.path,
                      artifacts.environments_root))
        commit_local_file_changes(artifacts, "delete environments")


def commit_local_file_changes(artifacts: Artifacts, msg: str) -> pygit2.Oid:
    index = artifacts.repo.index
    index.add_all()
    index.write()
    ref = artifacts.head_name
    parents = [artifacts.repo.lookup_reference(ref).target]
    oid = index.write_tree()
    return artifacts.repo.create_commit(
        ref, artifacts.signature, artifacts.signature, msg, oid, parents
    )


def create_initial_test_repo_state(artifacts: Artifacts) -> artifacts_dict:
    dir_path = app.settings.artifacts.path
    users_folder = "users"
    groups_folder = "groups"
    test_user = "test_user"
    test_group = "test_group"
    test_env = "test_environment"
    user_env_path = Path(
        dir_path, "environments", users_folder, test_user, test_env
    )
    group_env_path = Path(
        dir_path, "environments", groups_folder, test_group, test_env
    )
    os.makedirs(user_env_path)
    os.makedirs(group_env_path)
    open(f"{user_env_path}/initial_file.txt", "w").close()
    open(f"{group_env_path}/initial_file.txt", "w").close()

    oid = commit_local_file_changes(artifacts, "Add test environments")

    dict: artifacts_dict = {
        "initial_commit_oid": oid,
        "users_folder": users_folder,
        "groups_folder": groups_folder,
        "test_user": test_user,
        "test_group": test_group,
        "test_environment": test_env,
        "user_env_path": user_env_path,
        "group_env_path": group_env_path,
    }
    return dict
