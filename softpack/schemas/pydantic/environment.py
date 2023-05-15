"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from datetime import datetime

from pydantic import BaseModel

from .package import BasePackage
from .user import BaseUser


class BaseEnvironment(BaseModel):
    """A model representing a single environment."""

    name: str
    description: str
    packages: list[BasePackage]
    owner: BaseUser
    creation_date: datetime
    status: str
    id: int
