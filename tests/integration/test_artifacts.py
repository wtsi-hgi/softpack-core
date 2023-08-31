"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import os
import shutil
from pathlib import Path

import pygit2
import pytest

from softpack_core.artifacts import Artifacts
from tests.integration.utils import (
    file_was_pushed,
    get_user_path_without_environments,
    new_test_artifacts,
    delete_environments_folder_from_test_repo,
)


pytestmark = pytest.mark.repo


def test_clone() -> None:
    ad = new_test_artifacts()
    artifacts: Artifacts = ad["artifacts"]
    path = artifacts.repo.path
    assert path.startswith(ad["temp_dir"].name)

    shutil.rmtree(ad["temp_dir"].name)
    assert os.path.isdir(path) is False

    artifacts = Artifacts()
    assert os.path.isdir(path) is True

    # add test where we make a change to the repo in a different clone dir,
    # then call Artifacts() in an existing clone dir, and we should see the
    # change: ie. implement pull on init.
    # And then possibly something to test pull on every iter?


def test_commit_and_push() -> None:
    ad = new_test_artifacts()
    artifacts: Artifacts = ad["artifacts"]
    old_commit_oid = ad["initial_commit_oid"]

    new_file_name = "new_file.txt"
    oid = artifacts.repo.create_blob(b"")

    root = artifacts.repo.head.peel(pygit2.Tree)
    tree = root[artifacts.environments_root]
    tb = artifacts.repo.TreeBuilder(tree)
    tb.insert(new_file_name, oid, pygit2.GIT_FILEMODE_BLOB)
    oid = tb.write()
    tb = artifacts.repo.TreeBuilder(root)
    tb.insert(artifacts.environments_root, oid, pygit2.GIT_FILEMODE_TREE)
    new_tree = tb.write()

    new_commit_oid = artifacts.commit_and_push(new_tree, "commit new file")
    repo_head = artifacts.repo.head.peel(pygit2.Commit).oid

    assert old_commit_oid != new_commit_oid
    assert new_commit_oid == repo_head

    assert file_was_pushed(Path(artifacts.environments_root, new_file_name))


def test_create_file() -> None:
    ad = new_test_artifacts()
    artifacts: Artifacts = ad["artifacts"]
    user = ad["test_user"]

    new_test_env = "test_create_file_env"

    user_envs_tree = get_user_envs_tree(
        artifacts, user, artifacts.repo.head.peel(pygit2.Tree).oid
    )
    assert new_test_env not in [obj.name for obj in user_envs_tree]

    folder_path = Path(
        get_user_path_without_environments(artifacts, user), new_test_env
    )
    basename = "create_file.txt"

    oid = artifacts.create_file(
        folder_path, basename, "lorem ipsum", True, False
    )

    user_envs_tree = get_user_envs_tree(artifacts, user, oid)
    assert new_test_env in [obj.name for obj in user_envs_tree]
    assert basename in [obj.name for obj in user_envs_tree[new_test_env]]

    artifacts.commit_and_push(oid, "create file")

    with pytest.raises(RuntimeError) as exc_info:
        artifacts.create_file(
            folder_path, basename, "lorem ipsum", False, True
        )
    assert exc_info.value.args[0] == 'No changes made to the environment'

    basename2 = "create_file2.txt"
    with pytest.raises(RuntimeError) as exc_info:
        artifacts.create_file(
            folder_path, basename2, "lorem ipsum", True, False
        )
    assert exc_info.value.args[0] == 'Too many changes to the repo'

    oid = artifacts.create_file(
        folder_path, basename2, "lorem ipsum", False, False
    )

    artifacts.commit_and_push(oid, "create file2")

    user_envs_tree = get_user_envs_tree(artifacts, user, oid)
    assert basename2 in [obj.name for obj in user_envs_tree[new_test_env]]

    with pytest.raises(FileExistsError) as exc_info:
        artifacts.create_file(
            folder_path, basename, "lorem ipsum", False, False
        )
    assert exc_info.value.args[0] == 'File already exists'

    oid = artifacts.create_file(folder_path, basename, "override", False, True)

    artifacts.commit_and_push(oid, "update created file")

    user_envs_tree = get_user_envs_tree(artifacts, user, oid)
    assert basename in [obj.name for obj in user_envs_tree[new_test_env]]
    assert user_envs_tree[new_test_env][basename].data.decode() == "override"

    assert file_was_pushed(
        Path(artifacts.environments_root, folder_path, basename),
        Path(artifacts.environments_root, folder_path, basename2)
    )


def get_user_envs_tree(
    artifacts: Artifacts, user: str, oid: pygit2.Oid
) -> pygit2.Tree:
    new_tree = artifacts.repo.get(oid)
    return new_tree[artifacts.user_folder(user)]


def test_delete_environment() -> None:
    ad = new_test_artifacts()
    artifacts: Artifacts = ad["artifacts"]
    user = ad["test_user"]
    env_for_deleting = ad["test_environment"]

    user_envs_tree = get_user_envs_tree(
        artifacts, user, artifacts.repo.head.peel(pygit2.Tree).oid
    )
    assert env_for_deleting in [obj.name for obj in user_envs_tree]

    oid = artifacts.delete_environment(
        env_for_deleting, get_user_path_without_environments(artifacts, user)
    )

    artifacts.commit_and_push(oid, "delete new env")

    user_envs_tree = get_user_envs_tree(artifacts, user, oid)
    assert env_for_deleting not in [obj.name for obj in user_envs_tree]

    with pytest.raises(ValueError) as exc_info:
        artifacts.delete_environment(user, artifacts.users_folder_name)
    assert exc_info.value.args[0] == 'Not a valid environment path'

    with pytest.raises(KeyError) as exc_info:
        artifacts.delete_environment(env_for_deleting, "foo/bar")
    assert exc_info


def test_iter() -> None:
    ad = new_test_artifacts()
    artifacts: Artifacts = ad["artifacts"]
    user = ad["test_user"]

    user_found = False
    num_user_envs = 0
    num_group_envs = 0

    envs = artifacts.iter()

    for env in envs:
        if str(env.path).startswith(artifacts.users_folder_name):
            num_user_envs += 1
            if str(env.path).startswith(
                f"{artifacts.users_folder_name}/{user}"
            ):
                user_found = True
        elif str(env.path).startswith(artifacts.groups_folder_name):
            num_group_envs += 1

    assert user_found is True
    assert num_user_envs == 1
    assert num_group_envs == 1
