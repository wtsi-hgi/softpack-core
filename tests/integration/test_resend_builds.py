"""Copyright (c) 2024 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""


import pytest
from fastapi.testclient import TestClient

from softpack_core.app import app
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
    ServiceAPI.register()
    client = TestClient(app.router)

    orig_name = testable_env_input.name
    testable_env_input.name += "-1"
    r = Environment.create_new_env(
        testable_env_input, Environment.artifacts.built_by_softpack_file
    )
    assert isinstance(r, CreateEnvironmentSuccess)
    testable_env_input.name = orig_name

    httpx_post.assert_not_called()

    resp = client.post(
        url="/resend-pending-builds",
    )
    assert resp.status_code == 200
    assert resp.json().get("message") == "Successfully triggered resend"

    httpx_post.assert_called_once()
    builder_called_correctly(httpx_post, testable_env_input)
