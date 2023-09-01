"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""


import pytest
from starlette.datastructures import UploadFile

from softpack_core.artifacts import app


def pytest_addoption(parser):
    parser.addoption(
        "--repo",
        action="store_true",
        default=False,
        help=("run integration tests that alter your real git repo"),
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "repo: mark test as altering a real git repo"
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--repo"):
        return
    skip_repo = pytest.mark.skip(
        reason=(
            "specify --repo to run integration "
            "tests that will alter your "
            "configured git repo"
        )
    )
    for item in items:
        if "repo" in item.keywords:
            item.add_marker(skip_repo)


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
