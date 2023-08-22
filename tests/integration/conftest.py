"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import os
from pathlib import Path
import pytest
import tempfile

from softpack_core.artifacts import Artifacts, app


@pytest.fixture(scope="package", autouse=True)
def safe_testing_artifacts():
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

    artifacts = Artifacts()

    try:
        user_branch = artifacts.repo.branches.remote[f"origin/{user}"]
    except Exception as e:
        pytest.fail(f"There must be a branch named after your username. [{e}]")

    commit_ref = artifacts.repo.lookup_reference(user_branch.name)
    artifacts.repo.set_head(commit_ref.target)

    dict = {
        "artifacts": artifacts,
        # "repo": repo,
        "repo_url": repo_url,
        "temp_dir": temp_dir,
        # "initial_commit_oid": initial_commit_oid,
        # "users_folder": users_folder,
        # "groups_folder": groups_folder,
        # "test_user": test_user,
        # "test_group": test_group,
        # "test_environment": test_env,
    }
    return dict
