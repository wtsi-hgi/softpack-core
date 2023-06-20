"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""


import time
from multiprocessing import Process
from threading import Thread

import httpx
import pytest
import requests
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from softpack_core.app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app.router)


class CLI:
    def __init__(self):
        self.runner = CliRunner()

    def invoke(self, *args, **kwargs):
        return self.runner.invoke(app.commands, *args, **kwargs)


@pytest.fixture
def cli() -> CLI:
    return CLI()


def service_run():
    cli = CLI()
    cli.invoke(["service", "run"])


@pytest.fixture
def service_factory():
    def create_service(module):
        service = module(target=service_run, daemon=True)
        service.start()
        while True:
            try:
                response = requests.get(app.url())
                if response.status_code == httpx.codes.OK:
                    break
            except requests.ConnectionError:
                time.sleep(0.1)
                continue
        return service

    return create_service


@pytest.fixture
def service(service_factory):
    return service_factory(Process)


@pytest.fixture
def service_thread(service_factory):
    return service_factory(Thread)
