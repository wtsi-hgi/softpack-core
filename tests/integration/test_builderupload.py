"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from softpack_core.app import app
from softpack_core.schemas.environment import Environment
from softpack_core.service import ServiceAPI
from tests.integration.utils import file_in_repo

pytestmark = pytest.mark.repo


def test_builder_upload(testable_env_input):
    ServiceAPI.register()
    client = TestClient(app.router)

    env_parent = "groups/hgi"
    env_name = "unknown-env"
    env_path = env_parent + "/" + env_name

    softpackYaml = "softpack.yaml"
    softpackYamlContents = b"softpack yaml file"

    spackLock = "spack.lock"
    spackLockContents = b"spack lock file"

    assert Environment.check_env_exists(Path(env_path)) is not None
    resp = client.post(
        url="/upload?" + env_path,
        files=[
            ("file", (softpackYaml, softpackYamlContents)),
            ("file", (spackLock, spackLockContents)),
        ],
    )
    assert resp.status_code == 200
    assert resp.json().get("message") == "Successfully written artifact(s)"
    assert Environment.check_env_exists(Path(env_path)) is None
    assert file_in_repo(
        Environment.artifacts,
        Path(Environment.artifacts.environments_root, env_path, softpackYaml),
    )
    assert file_in_repo(
        Environment.artifacts,
        Path(Environment.artifacts.environments_root, env_path, spackLock),
    )

    tree = Environment.artifacts.get(env_parent, env_name)
    assert tree is not None

    assert tree.get(softpackYaml).data == softpackYamlContents
    assert tree.get(spackLock).data == spackLockContents
