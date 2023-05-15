"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from pydantic import BaseModel

from .package import BasePackage


class BasePackageCollection(BaseModel):
    """A model representing a single package collection."""

    name: str
    packages: list[BasePackage]
    id: int
