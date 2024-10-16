"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import os
import shutil
import threading
import time
from pathlib import Path

import pygit2
import pytest

from softpack_core.artifacts import Artifacts, app
from tests.integration.utils import (
    commit_and_push_test_repo_changes,
    delete_environments_folder_from_test_repo,
    file_in_remote,
    file_in_repo,
    get_user_path_without_environments,
    new_test_artifacts,
)

pytestmark = pytest.mark.repo


def test_clone() -> None:
    ad = new_test_artifacts()
    artifacts: Artifacts = ad["artifacts"]
    path = artifacts.repo.path
    tdir = str(Path(ad["temp_dir"].name).resolve())
    assert path.startswith(tdir)

    shutil.rmtree(ad["temp_dir"].name)
    assert os.path.isdir(path) is False

    artifacts = Artifacts()
    artifacts.clone_repo()
    assert os.path.isdir(path) is True

    orig_repo_path = app.settings.artifacts.path
    ad_for_changing = new_test_artifacts()
    artifacts_for_changing: Artifacts = ad_for_changing["artifacts"]

    oid, file_path = add_test_file_to_repo(artifacts_for_changing)
    commit_and_push_test_repo_changes(artifacts_for_changing, oid, "add file")

    app.settings.artifacts.path = orig_repo_path
    artifacts = Artifacts()
    artifacts.clone_repo()

    assert file_in_repo(artifacts, file_path)

    delete_environments_folder_from_test_repo(artifacts)

    try:
        artifacts.iter()
    except BaseException as e:
        print(e)
        assert False


def test_commit_and_push() -> None:
    ad = new_test_artifacts()
    artifacts: Artifacts = ad["artifacts"]
    old_commit_oid = ad["initial_commit_oid"]

    new_tree, file_path = add_test_file_to_repo(artifacts)

    new_commit_oid = artifacts.commit_and_push(new_tree, "commit new file")
    repo_head = artifacts.repo.head.peel(pygit2.Commit).oid

    assert old_commit_oid != new_commit_oid
    assert new_commit_oid == repo_head

    assert file_in_remote(file_path)

    time.sleep(1)

    newer_commit_oid = artifacts.commit_and_push(new_tree, "new timestamp")

    assert (
        artifacts.repo.get(new_commit_oid).commit_time
        != artifacts.repo.get(newer_commit_oid).commit_time
    )


def add_test_file_to_repo(artifacts: Artifacts) -> tuple[pygit2.Oid, Path]:
    new_file_name = "new_file.txt"
    oid = artifacts.repo.create_blob(b"")
    root = artifacts.repo.head.peel(pygit2.Tree)
    tree = root[artifacts.environments_root]
    tb = artifacts.repo.TreeBuilder(tree)
    tb.insert(new_file_name, oid, pygit2.GIT_FILEMODE_BLOB)
    oid = tb.write()
    tb = artifacts.repo.TreeBuilder(root)
    tb.insert(artifacts.environments_root, oid, pygit2.GIT_FILEMODE_TREE)
    return tb.write(), Path(artifacts.environments_root, new_file_name)


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
        Path(artifacts.environments_root, folder_path),
        basename,
        "lorem ipsum",
        True,
        False,
    )

    user_envs_tree = get_user_envs_tree(artifacts, user, oid)
    assert new_test_env in [obj.name for obj in user_envs_tree]
    assert basename in [obj.name for obj in user_envs_tree[new_test_env]]

    artifacts.commit_and_push(oid, "create file")

    with pytest.raises(RuntimeError) as exc_info:
        artifacts.create_file(
            Path(artifacts.environments_root, folder_path),
            basename,
            "lorem ipsum",
            False,
            True,
        )
    assert exc_info.value.args[0] == 'No changes made to the environment'

    basename2 = "create_file2.txt"
    with pytest.raises(RuntimeError) as exc_info:
        artifacts.create_file(
            Path(artifacts.environments_root, folder_path),
            basename2,
            "lorem ipsum",
            True,
            True,
        )
    assert exc_info.value.args[0] == 'Too many changes to the repo'

    oid = artifacts.create_file(
        Path(artifacts.environments_root, folder_path),
        basename2,
        "lorem ipsum",
        False,
        False,
    )

    artifacts.commit_and_push(oid, "create file2")

    user_envs_tree = get_user_envs_tree(artifacts, user, oid)
    assert basename2 in [obj.name for obj in user_envs_tree[new_test_env]]

    with pytest.raises(FileExistsError) as exc_info:
        artifacts.create_file(
            Path(artifacts.environments_root, folder_path),
            basename,
            "lorem ipsum",
            False,
            False,
        )
    assert exc_info.value.args[0] == 'File already exists'

    oid = artifacts.create_file(
        Path(artifacts.environments_root, folder_path),
        basename,
        "override",
        False,
        True,
    )

    artifacts.commit_and_push(oid, "update created file")

    user_envs_tree = get_user_envs_tree(artifacts, user, oid)
    assert basename in [obj.name for obj in user_envs_tree[new_test_env]]
    assert user_envs_tree[new_test_env][basename].data.decode() == "override"

    assert file_in_remote(
        Path(artifacts.environments_root, folder_path, basename),
        Path(artifacts.environments_root, folder_path, basename2),
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

    envs = artifacts.iter()
    pkgs = list(envs)[0].spec().packages
    assert len(pkgs) == 3
    assert pkgs[0].name == "pck1"
    assert pkgs[0].version == "1"
    assert pkgs[1].name == "pck2"
    assert pkgs[1].version == "v2.0.1"
    assert pkgs[2].name == "pck3"
    assert pkgs[2].version is None


# pygit2 protects us against producing diverging histories anyway:
#   _pygit2.GitError: failed to create commit: current tip is not the first
#   parent
# but the test is nice reassurance.
def test_simultaneous_commit():
    parallelism = 100
    ad = new_test_artifacts()
    artifacts: Artifacts = ad["artifacts"]
    initial_commit_oid = ad["initial_commit_oid"]

    new_tree, _ = add_test_file_to_repo(artifacts)

    e = threading.Event()

    def fn(i: int):
        e.wait()
        artifacts.commit_and_push(new_tree, f"I am thread {i}")

    threads = [
        threading.Thread(target=fn, args=[i]) for i in range(parallelism)
    ]
    for thread in threads:
        thread.start()
    e.set()
    for thread in threads:
        thread.join()

    commit = artifacts.repo.head.peel(pygit2.Commit)
    for _ in range(parallelism):
        commit = commit.parents[0]
    assert commit.oid == initial_commit_oid


def test_recipes():
    ad = new_test_artifacts()
    artifacts: Artifacts = ad["artifacts"]

    assert artifacts.get_recipe_request("recipeA", "1.23") is None
    assert artifacts.get_recipe_request("recipeB", "0.1a") is None

    recipeA = Artifacts.RecipeObject(
        "recipeA", "1.23", "A new recipe", "http://example.com", "user1"
    )
    recipeB = Artifacts.RecipeObject(
        "recipeB",
        "0.1a",
        "Another recipe",
        "http://example.com/another",
        "user2",
    )

    artifacts.create_recipe_request(recipeA)

    retrieved_recipe = artifacts.get_recipe_request("recipeA", "1.23")

    assert retrieved_recipe is not None
    assert retrieved_recipe.name == recipeA.name
    assert retrieved_recipe.version == recipeA.version
    assert retrieved_recipe.description == recipeA.description
    assert retrieved_recipe.url == recipeA.url
    assert retrieved_recipe.username == recipeA.username

    exists = False

    try:
        artifacts.create_recipe_request(recipeA)
    except Exception:
        exists = True

    assert exists

    artifacts.create_recipe_request(recipeB)

    requests = list(artifacts.iter_recipe_requests())

    assert len(requests) == 2

    removed = artifacts.remove_recipe_request("recipeA", "1.23")

    assert removed is not None
    assert artifacts.get_recipe_request("recipeA", "1.23") is None

    retrieved_recipe = artifacts.get_recipe_request("recipeB", "0.1a")

    assert retrieved_recipe is not None
    assert retrieved_recipe.name == recipeB.name
    assert retrieved_recipe.version == recipeB.version
    assert retrieved_recipe.description == recipeB.description
    assert retrieved_recipe.url == recipeB.url
    assert retrieved_recipe.username == recipeB.username

    requests = list(artifacts.iter_recipe_requests())

    assert len(requests) == 1
