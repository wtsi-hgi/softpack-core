"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from typing import Optional

from pydantic import BaseModel


class BasePackage(BaseModel):
    """A model representing a single package."""

    name: str
    version: Optional[str]
