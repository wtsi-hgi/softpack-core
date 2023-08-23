"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import os
from pathlib import Path
import pygit2
import pytest
import shutil
import tempfile

from softpack_core.artifacts import Artifacts, app
from tests.integration.conftest import new_test_artifacts


def test_clone() -> None:
    ad = new_test_artifacts()
    artifacts: Artifacts = ad["artifacts"]
    path = artifacts.repo.path
    assert path.startswith(ad["temp_dir"].name)

    shutil.rmtree(ad["temp_dir"].name)
    assert os.path.isdir(path) is False

    artifacts = Artifacts()
    assert os.path.isdir(path) is True


def test_commit_and_push() -> None:
    ad = new_test_artifacts()
    artifacts: Artifacts = ad["artifacts"]
    old_commit_oid = ad["initial_commit_oid"]

    tree = artifacts.repo.head.peel(pygit2.Tree)

    new_file_name = "new_file.txt"
    path = Path(ad["temp_dir"].name, artifacts.environments_root,
                artifacts.users_folder_name, ad["test_user"],
                ad["test_environment"], new_file_name)

    open(path, "w").close()

    index = artifacts.repo.index
    index.add_all()
    index.write()
    new_tree = index.write_tree()

    new_commit_oid = artifacts.commit(new_tree, "commit new file")
    repo_head = artifacts.repo.head.peel(pygit2.Commit).oid

    assert old_commit_oid != new_commit_oid
    assert new_commit_oid == repo_head

    artifacts.push()

    temp_dir = tempfile.TemporaryDirectory()
    app.settings.artifacts.path = Path(temp_dir.name)
    artifacts = Artifacts()

    path = Path(temp_dir.name, artifacts.environments_root,
                artifacts.users_folder_name, ad["test_user"],
                ad["test_environment"], new_file_name)

    assert os.path.isfile(path)
