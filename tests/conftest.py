"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import pytest


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
