"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import tempfile
from pathlib import Path
from typing import Union

import pygit2
import pytest

from softpack_core.artifacts import Artifacts, app

artifacts_dict = dict[
    str, Union[str, pygit2.Oid, Path, Artifacts, tempfile.TemporaryDirectory[str]]
]


def new_test_artifacts() -> artifacts_dict:
    temp_dir = tempfile.TemporaryDirectory()
    app.settings.artifacts.path = Path(temp_dir.name)

    artifacts = Artifacts()

    branch_name = app.settings.artifacts.repo.branch
    branch = artifacts.repo.branches.get(branch_name)

    if branch is None or branch_name == "main":
        pytest.skip(
            (
                "Your artifacts repo must have a branch named after your "
                "username."
            )
        )

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
        treeBuilder = artifacts.repo.TreeBuilder(tree)
        treeBuilder.remove(artifacts.environments_root)
        oid = treeBuilder.write()
        commit_and_push_test_repo_changes(
            artifacts, oid, "delete environments"
        )


def commit_and_push_test_repo_changes(
    artifacts: Artifacts, oid: pygit2.Oid, msg: str
) -> pygit2.Oid:
    ref = artifacts.repo.head.name
    oid = artifacts.repo.create_commit(
        ref,
        artifacts.signature,
        artifacts.signature,
        msg,
        oid,
        [artifacts.repo.lookup_reference(ref).target],
    )
    remote = artifacts.repo.remotes[0]
    remote.push(
        [artifacts.repo.head.name], callbacks=artifacts.credentials_callback
    )
    return oid


def create_initial_test_repo_state(artifacts: Artifacts) -> artifacts_dict:
    dir_path = app.settings.artifacts.path
    test_user = "test_user"
    test_group = "test_group"
    test_env = "test_environment"
    user_env_path = Path(
        dir_path,
        "environments",
        artifacts.users_folder_name,
        test_user,
        test_env,
    )
    group_env_path = Path(
        dir_path,
        "environments",
        artifacts.groups_folder_name,
        test_group,
        test_env,
    )
    file_basename = "file.txt"

    oid = artifacts.repo.create_blob(b"")

    userTestEnv = artifacts.repo.TreeBuilder()
    userTestEnv.insert(file_basename, oid, pygit2.GIT_FILEMODE_BLOB)

    testUser = artifacts.repo.TreeBuilder()
    testUser.insert(test_env, userTestEnv.write(), pygit2.GIT_FILEMODE_TREE)

    usersFolder = artifacts.repo.TreeBuilder()
    usersFolder.insert(test_user, testUser.write(), pygit2.GIT_FILEMODE_TREE)

    oid = artifacts.repo.create_blob(b"")

    userGroupEnv = artifacts.repo.TreeBuilder()
    userGroupEnv.insert(file_basename, oid, pygit2.GIT_FILEMODE_BLOB)

    testGroup = artifacts.repo.TreeBuilder()
    testGroup.insert(test_env, userGroupEnv.write(), pygit2.GIT_FILEMODE_TREE)

    groupsFolder = artifacts.repo.TreeBuilder()
    groupsFolder.insert(
        test_group, testGroup.write(), pygit2.GIT_FILEMODE_TREE
    )

    environments = artifacts.repo.TreeBuilder()
    environments.insert(
        artifacts.users_folder_name,
        usersFolder.write(),
        pygit2.GIT_FILEMODE_TREE,
    )
    environments.insert(
        artifacts.groups_folder_name,
        groupsFolder.write(),
        pygit2.GIT_FILEMODE_TREE,
    )

    tree = artifacts.repo.head.peel(pygit2.Tree)
    treeBuilder = artifacts.repo.TreeBuilder(tree)
    treeBuilder.insert(
        artifacts.environments_root,
        environments.write(),
        pygit2.GIT_FILEMODE_TREE,
    )

    oid = commit_and_push_test_repo_changes(
        artifacts, treeBuilder.write(), "Add test environments"
    )

    dict: artifacts_dict = {
        "initial_commit_oid": oid,
        "test_user": test_user,
        "test_group": test_group,
        "test_environment": test_env,
        "user_env_path": user_env_path,
        "group_env_path": group_env_path,
        "basename": file_basename,
    }
    return dict


def get_user_path_without_environments(
    artifacts: Artifacts, user: str
) -> Path:
    return Path(*(artifacts.user_folder(user).parts[1:]))


def file_was_pushed(*paths_with_environment: Union[str, Path]) -> bool:
    temp_dir = tempfile.TemporaryDirectory()
    app.settings.artifacts.path = Path(temp_dir.name)
    artifacts = Artifacts()

    for path_with_environment in paths_with_environment:
        path = Path(path_with_environment)

        if not file_in_repo(artifacts, path):
            return False

    return True


def file_in_repo(artifacts: Artifacts, path: Path) -> bool:
    current = artifacts.repo.head.peel(pygit2.Tree)
    for part in path.parts:
        if part not in current:
            return False
        current = current[part]

    return True
