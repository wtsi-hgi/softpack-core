"""Copyright (c) 2024 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""


import pytest
from fastapi.testclient import TestClient

from softpack_core.app import app
from softpack_core.artifacts import artifacts
from softpack_core.schemas.environment import (
    CreateEnvironmentSuccess,
    Environment,
    EnvironmentInput,
)
from softpack_core.service import ServiceAPI
from tests.integration.utils import builder_called_correctly

pytestmark = pytest.mark.repo


def test_resend_pending_builds(
    httpx_post, testable_env_input: EnvironmentInput
):
    Environment.delete("test_environment", "users/test_user")
    Environment.delete("test_environment", "groups/test_group")
    ServiceAPI.register()
    client = TestClient(app.router)

    orig_name = testable_env_input.name
    testable_env_input.name += "-1"
    r = Environment.create_new_env(
        testable_env_input, artifacts.built_by_softpack_file
    )
    assert isinstance(r, CreateEnvironmentSuccess)
    testable_env_input.name = orig_name

    httpx_post.assert_not_called()

    resp = client.post(
        url="/resend-pending-builds",
    )
    assert resp.status_code == 200
    assert resp.json().get("message") == "Successfully triggered resends"
    assert resp.json().get("successes") == 1
    assert resp.json().get("failures") == 0

    httpx_post.assert_called_once()
    builder_called_correctly(httpx_post, testable_env_input)

    httpx_post.side_effect = Exception('could not contact builder')
    resp = client.post(
        url="/resend-pending-builds",
    )
    assert resp.status_code == 500
    assert resp.json().get("message") == "Failed to trigger all resends"
    assert resp.json().get("successes") == 0
    assert resp.json().get("failures") == 1
