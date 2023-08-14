"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import pytest
import pytest_mock
import pygit2
from pygit2 import Signature
import tempfile
from softpack_core.artifacts import Artifacts

@pytest.fixture
def new_repo():
    temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    path = temp_dir.name
    print(path)
    repo = pygit2.init_repository(path)

    open(f"{path}/initial_file.txt", "w").close()
    index = repo.index
    index.add_all()
    index.write()
    ref = "HEAD"
    author = Signature('Alice Author', 'alice@authors.tld')
    committer = Signature('Cecil Committer', 'cecil@committers.tld')
    message = "Initial commit"
    tree = index.write_tree()
    parents = []
    old_commit_oid = repo.create_commit(ref, author, committer, message, tree, parents)

    return (repo, temp_dir, old_commit_oid)


def test_commit(new_repo):
    repo = new_repo[0]
    temp_dir = new_repo[1]
    old_commit_oid = new_repo[2]
    file_oid = repo.create_blob("test")
    tree = repo.head.peel(pygit2.Tree)
    tree_builder = repo.TreeBuilder(tree)
    tree_builder.insert("new_file.txt", file_oid, pygit2.GIT_FILEMODE_BLOB)
    new_tree = tree_builder.write()
    
    artifacts = Artifacts()
    new_commit_oid = artifacts.commit(repo, new_tree, "commit new file")
    repo_head = repo.head.peel(pygit2.Commit).oid
    temp_dir.cleanup()

    assert old_commit_oid != new_commit_oid
    assert new_commit_oid == repo_head

def test_push(mocker):
    artifacts = Artifacts()

    push_mock = mocker.patch('pygit2.Remote.push')

    artifacts.push(artifacts.repo)
    push_mock.assert_called_once()
