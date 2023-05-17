"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from datetime import datetime

import strawberry

from .package import Package
from .user import User


@strawberry.type
class Environment:
    """A Strawberry model representing a single environment."""

    name: str
    description: str
    packages: list[Package]
    owner: User
    creation_date: datetime
    status: str
    id: strawberry.ID
