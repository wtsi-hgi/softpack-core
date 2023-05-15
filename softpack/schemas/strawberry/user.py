"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import strawberry

from ..pydantic.user import BaseUser


@strawberry.experimental.pydantic.type(model=BaseUser)
class User:
    """A Strawberry model representing a single package."""

    name: strawberry.auto
    id: strawberry.ID
