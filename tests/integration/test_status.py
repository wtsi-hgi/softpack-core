"""Copyright (c) 2024 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import datetime

import pytest

from softpack_core.schemas.status import Status

pytestmark = pytest.mark.repo


def test_get_all(mocker) -> None:
    get_mock = mocker.patch("httpx.get")
    get_mock.return_value.json.return_value = [
        {
            "Name": "users/foo/bar",
            "Requested": "2024-01-02T03:04:05.000000000Z",
            "BuildStart": "2025-01-02T03:04:05.000000000Z",
            "BuildDone": None,
        }
    ]
    statuses = Status.get_all()
    assert statuses == [
        Status(
            name="users/foo/bar",
            requested=datetime.datetime(
                2024, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc
            ),
            build_start=datetime.datetime(
                2025, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc
            ),
            build_done=None,
        )
    ]
