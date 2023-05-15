"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from pydantic import BaseModel


class BaseUser(BaseModel):
    """A model representing a single user."""

    name: str
    id: int
