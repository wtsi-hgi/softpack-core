"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import pytest_mock
from softpack_core.artifacts import Artifacts

def test_commit(mocker):
    # mocker.patch(
    #     'softpack_core.artifacts.Artifacts.commit',
    #     return_value="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
    # )

    expected = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
    artifacts = Artifacts()
    tree_oid = "5f6e7d8c9b0a1f2e3d4c5b6a7e8d9c0b1a2f3e4"
    actual = artifacts.commit(artifacts.repo, tree_oid, "pytest commit")
    print(actual)
    assert expected == actual