"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import os
from pathlib import Path
import pygit2
import pytest
import shutil

from softpack_core.artifacts import Artifacts, app
from tests.integration.conftest import new_test_artifacts


def test_clone() -> None:
    ad = new_test_artifacts()
    artifacts = ad["artifacts"]
    path = artifacts.repo.path
    assert path.startswith(ad["temp_dir"].name)

    shutil.rmtree(ad["temp_dir"].name)
    assert os.path.isdir(path) is False

    artifacts = Artifacts()
    assert os.path.isdir(path) is True


def test_commit() -> None:
    ad = new_test_artifacts()
    artifacts = ad["artifacts"]
    repo = artifacts.repo
    old_commit_oid = ad["initial_commit_oid"]

    file_oid = repo.create_blob("test")
    tree = repo.head.peel(pygit2.Tree)
    tree_builder = repo.TreeBuilder(tree)
    tree_builder.insert("new_file.txt", file_oid, pygit2.GIT_FILEMODE_BLOB)
    new_tree = tree_builder.write()

    new_commit_oid = artifacts.commit(repo, new_tree, "commit new file")
    repo_head = repo.head.peel(pygit2.Commit).oid

    assert old_commit_oid != new_commit_oid
    assert new_commit_oid == repo_head
