from typing import List
from pydantic import BaseModel
from .package import BasePackage
from .user import BaseUser


class BaseEnvironment(BaseModel):
    """A model representing a single environment."""

    name: str
    packages: List[BasePackage]
    owners: List[BaseUser]
