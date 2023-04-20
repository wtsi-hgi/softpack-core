import strawberry
from ..pydantic.user import BaseUser

@strawberry.experimental.pydantic.type(model=BaseUser)
class User:
    """A Strawberry model representing a single package."""

    name: strawberry.auto
    email: strawberry.auto
    id: strawberry.ID
