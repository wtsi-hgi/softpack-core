from typing import Optional

from pydantic import BaseModel


class BasePackage(BaseModel):
    """A model representing a single package."""

    name: str
    version: Optional[str]
