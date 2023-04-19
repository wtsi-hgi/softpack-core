from pydantic import BaseModel


class BaseUser(BaseModel):
    """A model representing a single user."""

    name: str
    email: str
