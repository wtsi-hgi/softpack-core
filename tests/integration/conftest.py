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


@pytest.fixture(scope="package", autouse=True)
def testable_artifacts_setup():
    repo_url = os.getenv("SOFTPACK_TEST_ARTIFACTS_REPO_URL")
    repo_user = os.getenv("SOFTPACK_TEST_ARTIFACTS_REPO_USER")
    repo_token = os.getenv("SOFTPACK_TEST_ARTIFACTS_REPO_TOKEN")
    if repo_url is None or repo_user is None or repo_token is None:
        pytest.skip(
            (
                "SOFTPACK_TEST_ARTIFACTS_REPO_URL, _USER and _TOKEN "
                "env vars are all required for these tests"
            )
        )

    user = repo_user.split('@', 1)[0]
    app.settings.artifacts.repo.url = repo_url
    app.settings.artifacts.repo.username = repo_user
    app.settings.artifacts.repo.author = user
    app.settings.artifacts.repo.email = repo_user
    app.settings.artifacts.repo.writer = repo_token
    app.settings.artifacts.repo.branch = user


@pytest.fixture(autouse=True)
def patch_post(mocker):
    post_mock = mocker.patch('httpx.post')
    return post_mock
