"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import os
from pathlib import Path
import pytest
import tempfile

from softpack_core.artifacts import Artifacts, app

import pygit2


@pytest.fixture(scope="package", autouse=True)
def testable_artifacts():
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

    try:
        user_branch = artifacts.repo.branches.remote[f"origin/{user}"]
    except Exception as e:
        pytest.fail(f"There must be a branch named after your username. [{e}]")

    artifacts.repo.set_head(user_branch.name)
    artifacts.head_name = user_branch.name

    tree = artifacts.repo.head.peel(pygit2.Tree)
    print([(e.name, e) for e in tree])

    oid = reset_test_repo(artifacts)

    tree = artifacts.repo.head.peel(pygit2.Tree)
    print([(e.name, e) for e in tree])

    dict = {
        "artifacts": artifacts,
        "user_branch": user_branch,
        # "repo": repo,
        "repo_url": repo_url,
        "temp_dir": temp_dir,
        "initial_commit_oid": oid,
        # "users_folder": users_folder,
        # "groups_folder": groups_folder,
        # "test_user": test_user,
        # "test_group": test_group,
        # "test_environment": test_env,
    }
    return dict


def reset_test_repo(artifacts: Artifacts) -> pygit2.Oid:
    tree = artifacts.repo.head.peel(pygit2.Tree)
    dir_path = app.settings.artifacts.path

    if artifacts.environments_root in tree:
        exitcode = os.system(
            f"cd {dir_path} && git rm -r {artifacts.environments_root} && git commit -m 'remove environments'")
        if exitcode != 0:
            pytest.fail("failed to remove environments")

        # exitcode = os.system(
        #     f"cd {dir_path} && git commit -m 'remove environements' && git push")
        # print(exitcode)
        # tb = artifacts.repo.TreeBuilder(tree)

        # sub_tb = artifacts.repo.TreeBuilder(tree[artifacts.environments_root])
        # for obj in tree[artifacts.environments_root]:
        #     sub_tb.remove(obj.name)

        # tb.insert(artifacts.environments_root,
        #           sub_tb.write(), pygit2.GIT_FILEMODE_TREE)
        # tb.remove(artifacts.environments_root)
        # oid = tb.write()

        # ref = artifacts.head_name
        # parents = [artifacts.repo.lookup_reference(ref).target]
        # artifacts.repo.create_commit(
        #     ref, artifacts.signature, artifacts.signature, "rm environments", oid, parents
        # )

        # remote = artifacts.repo.remotes[0]
        # remote.push([artifacts.head_name],
        #             callbacks=artifacts.credentials_callback)
        print("removed environments")
    else:
        print("repo started empty")

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

    # Commit
    index = artifacts.repo.index
    index.add_all()
    index.write()
    ref = artifacts.head_name  # "HEAD"
    parents = [artifacts.repo.lookup_reference(ref).target]
    message = "Add test environments"
    tree = index.write_tree()
    return artifacts.repo.create_commit(
        ref, artifacts.signature, artifacts.signature, message, tree, parents
    )
