"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""


import pytest
from starlette.datastructures import UploadFile

from softpack_core.artifacts import app


@pytest.fixture(scope="package", autouse=True)
def testable_artifacts_setup():
    user = app.settings.artifacts.repo.username.split('@', 1)[0]
    if user is None or user == "main":
        pytest.skip(
            ("Your artifacts repo username must be defined in your config.")
        )

    if app.settings.artifacts.repo.writer is None:
        pytest.skip(
            ("Your artifacts repo writer must be defined in your config.")
        )

    app.settings.artifacts.repo.branch = user


@pytest.fixture(autouse=True)
def post(mocker):
    post_mock = mocker.patch('httpx.post')
    return post_mock


@pytest.fixture()
def upload(mocker):
    return mocker.Mock(spec=UploadFile)
