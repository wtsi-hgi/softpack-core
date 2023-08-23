"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import os
from pathlib import Path
import pygit2
import pytest
import shutil
import tempfile

from softpack_core.artifacts import Artifacts, app
from tests.integration.conftest import new_test_artifacts


def test_clone() -> None:
    ad = new_test_artifacts()
    artifacts: Artifacts = ad["artifacts"]
    path = artifacts.repo.path
    assert path.startswith(ad["temp_dir"].name)

    shutil.rmtree(ad["temp_dir"].name)
    assert os.path.isdir(path) is False

    artifacts = Artifacts()
    assert os.path.isdir(path) is True


def test_commit_and_push() -> None:
    ad = new_test_artifacts()
    artifacts: Artifacts = ad["artifacts"]
    old_commit_oid = ad["initial_commit_oid"]

    tree = artifacts.repo.head.peel(pygit2.Tree)

    new_file_name = "new_file.txt"
    path = Path(ad["temp_dir"].name, artifacts.environments_root,
                artifacts.users_folder_name, ad["test_user"],
                ad["test_environment"], new_file_name)

    open(path, "w").close()

    index = artifacts.repo.index
    index.add_all()
    index.write()
    new_tree = index.write_tree()

    new_commit_oid = artifacts.commit(new_tree, "commit new file")
    repo_head = artifacts.repo.head.peel(pygit2.Commit).oid

    assert old_commit_oid != new_commit_oid
    assert new_commit_oid == repo_head

    artifacts.push()

    path = Path(artifacts.users_folder_name, ad["test_user"],
                ad["test_environment"], new_file_name)

    assert file_was_pushed(path)


def file_was_pushed(*paths_without_environment: str) -> bool:
    temp_dir = tempfile.TemporaryDirectory()
    app.settings.artifacts.path = Path(temp_dir.name)
    artifacts = Artifacts()

    for path_without_environment in paths_without_environment:
        path = Path(temp_dir.name, artifacts.environments_root,
                    path_without_environment)
        if not os.path.isfile(path):
            return False

    return True


def test_create_file() -> None:
    ad = new_test_artifacts()
    artifacts: Artifacts = ad["artifacts"]
    user = ad["test_user"]

    new_test_env = "test_create_file_env"
    assert new_test_env not in [
        obj.name for obj in artifacts.iter_user(user)
    ]

    folder_path = Path(
        get_user_path_without_environments(
            artifacts, user), new_test_env
    )
    basename = "create_file.txt"

    oid = artifacts.create_file(
        str(folder_path), basename, "lorem ipsum", True, False
    )

    user_envs_tree = get_user_envs_tree(artifacts, user, oid)
    assert new_test_env in [obj.name for obj in user_envs_tree]
    assert basename in [obj.name for obj in user_envs_tree[new_test_env]]

    artifacts.commit(oid, "create file")

    with pytest.raises(RuntimeError) as exc_info:
        artifacts.create_file(
            str(folder_path), basename, "lorem ipsum", False, True
        )
    assert exc_info.value.args[0] == 'No changes made to the environment'

    basename2 = "create_file2.txt"
    with pytest.raises(RuntimeError) as exc_info:
        artifacts.create_file(
            str(folder_path), basename2, "lorem ipsum", True, False
        )
    assert exc_info.value.args[0] == 'Too many changes to the repo'

    oid = artifacts.create_file(
        str(folder_path), basename2, "lorem ipsum", False, False
    )

    artifacts.commit(oid, "create file2")

    user_envs_tree = get_user_envs_tree(artifacts, user, oid)
    assert basename2 in [
        obj.name for obj in user_envs_tree[new_test_env]
    ]

    with pytest.raises(FileExistsError) as exc_info:
        artifacts.create_file(
            str(folder_path), basename, "lorem ipsum", False, False
        )
    assert exc_info.value.args[0] == 'File already exists'

    oid = artifacts.create_file(
        str(folder_path), basename, "override", False, True
    )

    artifacts.commit(oid, "update created file")

    user_envs_tree = get_user_envs_tree(artifacts, user, oid)
    assert basename in [obj.name for obj in user_envs_tree[new_test_env]]
    assert user_envs_tree[new_test_env][basename].data.decode() == "override"

    artifacts.push()

    assert file_was_pushed(Path(folder_path, basename),
                           Path(folder_path, basename2))


def get_user_path_without_environments(artifacts: Artifacts, user: str) -> Path:
    return Path(*(artifacts.user_folder(user).parts[1:]))


def get_user_envs_tree(artifacts: Artifacts, user: str, oid: pygit2.Oid) -> pygit2.Tree:
    new_tree = artifacts.repo.get(oid)
    return new_tree[artifacts.user_folder(user)]
