"""Copyright (c) 2024 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import datetime
from dataclasses import dataclass
from traceback import format_exception_only
from typing import List, Optional, Union

import httpx
import strawberry

from softpack_core.app import app


# Interfaces
@strawberry.interface
class Success:
    """Interface for successful results."""

    message: str


@strawberry.interface
class Error:
    """Interface for errors."""

    message: str


@strawberry.type
class BuilderError(Error):
    """Unable to connect to builder."""


StatusResponse = Union[List["Status"], BuilderError]
# StatusResponse = strawberry.union(
#     "StatusResponse",
#     [
#         List["Status"],
#         BuilderError,
#     ],
# )


@strawberry.type
class Status:
    """A Strawberry model representing the status of all known builds."""

    name: str
    requested: datetime.datetime
    build_start: Optional[datetime.datetime]
    build_done: Optional[datetime.datetime]

    @classmethod
    def get_all(cls) -> StatusResponse:
        """Get all Status objects.

        Returns:
            List[Status]: A list of Status objects.
        """
        try:
            host = app.settings.builder.host
            port = app.settings.builder.port
            r = httpx.get(
                f"http://{host}:{port}/environments/status",
            )
            r.raise_for_status()
            json = r.json()
        except Exception as e:
            return BuilderError(
                message="Connection to builder failed: "
                + "".join(format_exception_only(type(e), e))
            )

        return [
            Status(
                name=s["Name"],
                requested=datetime.datetime.fromisoformat(s["Requested"]),
                build_start=datetime.datetime.fromisoformat(s["BuildStart"])
                if s["BuildStart"]
                else None,
                build_done=datetime.datetime.fromisoformat(s["BuildDone"])
                if s["BuildDone"]
                else None,
            )
            for s in json
        ]


class StatusSchema:
    """Status schema."""

    @dataclass
    class Query:
        """GraphQL query schema."""

        statuses: list[Status] = Status.get_all  # type: ignore
