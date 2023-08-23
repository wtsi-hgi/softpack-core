"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import os
import shutil
import tempfile
from pathlib import Path

import pygit2
import pytest
from pygit2 import Signature

from softpack_core.artifacts import Artifacts


# This is a fixture that sets up a new repo in a temporary directory to act
# as dummy data/repo for tests, instead of creating a copy of the real repo
# and accessing user folders with os.environ["USERS"].
@pytest.fixture
def new_test_repo():
    # Create new temp folder and repo
    temp_dir = tempfile.TemporaryDirectory()
    dir_path = temp_dir.name
    repo = pygit2.init_repository(dir_path)

    # Create directory structure
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

    # Make initial commit
    index = repo.index
    index.add_all()
    index.write()
    ref = "HEAD"
    author = Signature('Alice Author', 'alice@authors.tld')
    committer = Signature('Cecil Committer', 'cecil@committers.tld')
    message = "Initial commit"
    tree = index.write_tree()
    parents = []
    initial_commit_oid = repo.create_commit(
        ref, author, committer, message, tree, parents
    )

    repo_dict = {
        "repo": repo,
        "temp_dir": temp_dir,
        "initial_commit_oid": initial_commit_oid,
        "users_folder": users_folder,
        "groups_folder": groups_folder,
        "test_user": test_user,
        "test_group": test_group,
        "test_environment": test_env,
    }
    return repo_dict


@pytest.fixture
def new_repo():
    temp_dir = tempfile.TemporaryDirectory()
    path = temp_dir.name
    repo = pygit2.init_repository(path)

    open(f"{path}/initial_file.txt", "w").close()
    index = repo.index
    index.add_all()
    index.write()
    ref = "HEAD"
    author = Signature('Alice Author', 'alice@authors.tld')
    committer = Signature('Cecil Committer', 'cecil@committers.tld')
    message = "Initial commit"
    tree = index.write_tree()
    parents = []
    old_commit_oid = repo.create_commit(
        ref, author, committer, message, tree, parents
    )

    return (repo, temp_dir, old_commit_oid)


def test_clone() -> None:
    artifacts = Artifacts()
    path = artifacts.repo.path

    shutil.rmtree(path)
    assert os.path.isdir(path) is False

    artifacts = Artifacts()
    assert os.path.isdir(path) is True


def test_commit(new_repo) -> None:
    repo = new_repo[0]
    old_commit_oid = new_repo[2]
    with new_repo[1]:
        file_oid = repo.create_blob("test")
        tree = repo.head.peel(pygit2.Tree)
        tree_builder = repo.TreeBuilder(tree)
        tree_builder.insert("new_file.txt", file_oid, pygit2.GIT_FILEMODE_BLOB)
        new_tree = tree_builder.write()

        artifacts = Artifacts()
        new_commit_oid = artifacts.commit(repo, new_tree, "commit new file")
        repo_head = repo.head.peel(pygit2.Commit).oid

        assert old_commit_oid != new_commit_oid
        assert new_commit_oid == repo_head


def test_push(mocker) -> None:
    artifacts = Artifacts()

    push_mock = mocker.patch('pygit2.Remote.push')

    artifacts.push()
    push_mock.assert_called_once()


def get_user_envs_tree(artifacts, oid) -> pygit2.Tree:
    new_tree = artifacts.repo.get(oid)
    return new_tree[artifacts.user_folder(os.environ["USER"])]


def copy_of_repo(artifacts) -> tempfile.TemporaryDirectory:
    temp_dir = tempfile.TemporaryDirectory()
    shutil.copytree(artifacts.repo.path, temp_dir.name, dirs_exist_ok=True)
    return temp_dir


def get_user_path_without_environments(artifacts) -> Path:
    return Path(*(artifacts.user_folder(os.environ["USER"]).parts[1:]))


def test_create_file() -> None:
    artifacts = Artifacts()
    with copy_of_repo(artifacts) as temp_dir:
        artifacts.repo = pygit2.Repository(temp_dir)
        new_test_env = "test_create_file_env"
        assert new_test_env not in [
            obj.name for obj in artifacts.iter_user(os.environ["USER"])
        ]

        fname = "file.txt"

        folder_path = Path(
            get_user_path_without_environments(artifacts), new_test_env
        )
        oid = artifacts.create_file(
            str(folder_path), fname, "lorem ipsum", True, False
        )

        user_envs_tree = get_user_envs_tree(artifacts, oid)
        assert new_test_env in [obj.name for obj in user_envs_tree]
        assert fname in [obj.name for obj in user_envs_tree[new_test_env]]

        artifacts.commit(artifacts.repo, oid, "commit file")

        with pytest.raises(RuntimeError) as exc_info:
            oid = artifacts.create_file(
                str(folder_path), fname, "lorem ipsum", False, True
            )
        assert exc_info.value.args[0] == 'No changes made to the environment'

        with pytest.raises(RuntimeError) as exc_info:
            artifacts.create_file(
                str(folder_path), "second_file.txt", "lorem ipsum", True, False
            )
        assert exc_info.value.args[0] == 'Too many changes to the repo'

        oid = artifacts.create_file(
            str(folder_path), "second_file.txt", "lorem ipsum", False, False
        )

        user_envs_tree = get_user_envs_tree(artifacts, oid)
        assert "second_file.txt" in [
            obj.name for obj in user_envs_tree[new_test_env]
        ]

        with pytest.raises(FileExistsError) as exc_info:
            artifacts.create_file(
                str(folder_path), fname, "lorem ipsum", False, False
            )
        assert exc_info.value.args[0] == 'File already exists'

        oid = artifacts.create_file(
            str(folder_path), fname, "override", False, True
        )

        user_envs_tree = get_user_envs_tree(artifacts, oid)
        assert fname in [obj.name for obj in user_envs_tree[new_test_env]]
        assert user_envs_tree[new_test_env][fname].data.decode() == "override"


def test_delete_environment() -> None:
    artifacts = Artifacts()
    with copy_of_repo(artifacts):
        new_test_env = "test_create_file_env"
        folder_path = Path(
            get_user_path_without_environments(artifacts), new_test_env
        )
        oid = artifacts.create_file(
            str(folder_path), "file.txt", "lorem ipsum", True, False
        )
        artifacts.commit(artifacts.repo, oid, "commit file")

        user_envs_tree = get_user_envs_tree(artifacts, oid)
        assert new_test_env in [obj.name for obj in user_envs_tree]

        oid = artifacts.delete_environment(
            new_test_env, get_user_path_without_environments(artifacts)
        )

        artifacts.commit(artifacts.repo, oid, "commit file")

        user_envs_tree = get_user_envs_tree(artifacts, oid)
        assert new_test_env not in [obj.name for obj in user_envs_tree]

        with pytest.raises(ValueError) as exc_info:
            artifacts.delete_environment(
                os.environ["USER"], artifacts.users_folder_name
            )
        assert exc_info.value.args[0] == 'Not a valid environment path'

        with pytest.raises(KeyError) as exc_info:
            artifacts.delete_environment(new_test_env, "foo/bar")
        assert exc_info


def count_user_and_group_envs(artifacts, envs) -> (int, int):
    num_user_envs = 0
    num_group_envs = 0

    for env in envs:
        if str(env.path).startswith(artifacts.users_folder_name):
            num_user_envs += 1
        elif str(env.path).startswith(artifacts.groups_folder_name):
            num_group_envs += 1

    return num_user_envs, num_group_envs


def test_iter() -> None:
    artifacts = Artifacts()
    user = os.environ["USER"]
    envs = artifacts.iter(user)

    user_found = False
    only_this_user = True
    num_user_envs = 0
    num_group_envs = 0

    for env in envs:
        if str(env.path).startswith(artifacts.users_folder_name):
            num_user_envs += 1
            if str(env.path).startswith(
                f"{artifacts.users_folder_name}/{user}"
            ):
                user_found = True
            else:
                only_this_user = False
        elif str(env.path).startswith(artifacts.groups_folder_name):
            num_group_envs += 1

    assert user_found is True
    assert only_this_user is True
    assert num_group_envs > 0

    envs = artifacts.iter()
    no_user_num_user_envs, no_user_num_group_envs = count_user_and_group_envs(
        artifacts, envs
    )
    assert no_user_num_user_envs >= num_user_envs
    assert no_user_num_group_envs >= num_group_envs

    envs = artifacts.iter("!@£$%")
    (
        bad_user_num_user_envs,
        bad_user_num_group_envs,
    ) = count_user_and_group_envs(artifacts, envs)
    assert bad_user_num_user_envs == 0
    assert bad_user_num_group_envs == 0
