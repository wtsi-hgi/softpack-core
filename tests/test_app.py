"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import httpx

from softpack_core.app import Application


def test_root(client) -> None:
    response = client.get("/")
    assert response.status_code == httpx.codes.OK


def test_openapi_docs(client) -> None:
    response = client.get("/docs")
    assert response.status_code == httpx.codes.OK


def test_openapi_redoc(client) -> None:
    response = client.get("/redoc")
    assert response.status_code == httpx.codes.OK


def test_register_api(capsys) -> None:
    class TestAPI:
        pass

    app = Application()
    app.register_api(TestAPI)
    captured = capsys.readouterr()
    assert (
        f"type object '{TestAPI.__name__}' has no attribute" in captured.out
    )  # noqa: E501, W503
