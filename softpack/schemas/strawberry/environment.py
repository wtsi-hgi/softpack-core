"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import strawberry

from ..pydantic.environment import BaseEnvironment
from .package import Package
from .user import User


@strawberry.experimental.pydantic.type(model=BaseEnvironment)
class Environment:
    """A Strawberry model representing a single environment."""

    name: strawberry.auto
    description: strawberry.auto
    packages: list[Package]
    owner: User
    creation_date: strawberry.auto
    status: strawberry.auto
    id: strawberry.ID
