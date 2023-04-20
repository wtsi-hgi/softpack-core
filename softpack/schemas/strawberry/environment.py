from typing import List
import strawberry
from ..pydantic.environment import BaseEnvironment
from .package import Package
from .user import User


@strawberry.experimental.pydantic.type(model=BaseEnvironment)
class Environment:
    """ A Strawberry model representing a single environment"""

    name: strawberry.auto
    description: strawberry.auto
    packages: List[Package]
    owners: List[User]
    creation_date: strawberry.auto
    status: strawberry.auto
    id: strawberry.ID