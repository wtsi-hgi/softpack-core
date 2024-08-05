"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""


import pytest
from fastapi.testclient import TestClient

from softpack_core.app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app.router)
