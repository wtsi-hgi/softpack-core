"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import pygit2
import pytest

from softpack_core.artifacts import Artifacts


def test_commit(testable_artifacts) -> None:
    artifacts = testable_artifacts["artifacts"]
    tree = artifacts.repo.head.peel(pygit2.Tree)
    print([(e.name, e) for e in tree])
    print([(e.name, e) for e in tree[artifacts.environments_root]])
    print([(e.name, e) for e in tree[artifacts.environments_root]["users"]])
    print(testable_artifacts["user_env_path"])

    assert True
