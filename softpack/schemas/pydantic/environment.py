from typing import List
from pydantic import BaseModel
from datetime import datetime
from .package import BasePackage
from .user import BaseUser


class BaseEnvironment(BaseModel):
    """A model representing a single environment."""

    name: str
    description: str
    packages: List[BasePackage]
    owners: List[BaseUser]
    creation_date: datetime
    status: str
    id: int
