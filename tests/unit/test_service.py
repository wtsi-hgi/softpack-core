"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import httpx
from box import Box

from softpack_core import __version__
from softpack_core.app import app
import multiprocessing
from softpack_core.service import ServiceAPI
from time import sleep


def test_service_run() -> None:
    ready = multiprocessing.Event()
    run = multiprocessing.Process(target=ServiceAPI.run, kwargs={"serviceReady": ready})
    run.start()
    ready.wait(timeout=120)
    response = httpx.get(app.url())
    run.terminate()
    status = Box(response.json())
    assert status.softpack.core.version == __version__
