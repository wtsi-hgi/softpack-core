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

from softpack_core.artifacts import Artifacts, app

artifacts_dict = dict[
    str, str | pygit2.Oid | Path | Artifacts | tempfile.TemporaryDirectory[str]
]


def new_test_artifacts() -> artifacts_dict:
    temp_dir = tempfile.TemporaryDirectory()
    app.settings.artifacts.path = Path(temp_dir.name)

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
        shutil.rmtree(
            Path(app.settings.artifacts.path, artifacts.environments_root)
        )
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
    os.makedirs(user_env_path)
    os.makedirs(group_env_path)
    file_basename = "file.txt"
    open(Path(user_env_path, file_basename), "w").close()
    open(Path(group_env_path, file_basename), "w").close()

    oid = commit_local_file_changes(artifacts, "Add test environments")

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


def file_was_pushed(*paths_without_environment: str | Path) -> bool:
    temp_dir = tempfile.TemporaryDirectory()
    app.settings.artifacts.path = Path(temp_dir.name)
    artifacts = Artifacts()

    for path_without_environment in paths_without_environment:
        path = Path(
            temp_dir.name,
            artifacts.environments_root,
            path_without_environment,
        )
        if not os.path.isfile(path):
            return False

    return True
