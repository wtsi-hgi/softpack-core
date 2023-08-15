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


def test_commit(new_repo):
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


def test_push(mocker):
    artifacts = Artifacts()

    push_mock = mocker.patch('pygit2.Remote.push')

    artifacts.push(artifacts.repo)
    push_mock.assert_called_once()


def get_user_envs_tree(artifacts, oid) -> pygit2.Tree:
    new_tree = artifacts.repo.get(oid)
    return new_tree[artifacts.user_folder(os.environ["USER"])]


def copy_of_repo(artifacts):
    temp_dir = tempfile.TemporaryDirectory()
    shutil.copytree(artifacts.repo.path, temp_dir.name, dirs_exist_ok=True)
    artifacts.repo = pygit2.Repository(temp_dir.name)
    return temp_dir


def get_user_path_without_environments(artifacts) -> Path:
    return Path(*(artifacts.user_folder(os.environ["USER"]).parts[1:]))


def test_create_file():
    artifacts = Artifacts()
    with copy_of_repo(artifacts):
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


def test_delete_environment():
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
            new_test_env, get_user_path_without_environments(artifacts), oid
        )

        artifacts.commit(artifacts.repo, oid, "commit file")

        user_envs_tree = get_user_envs_tree(artifacts, oid)
        assert new_test_env not in [obj.name for obj in user_envs_tree]


# consider if build_tree is needed by replacing with something simpler
