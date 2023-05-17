"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import strawberry


@strawberry.type
class User:
    """A Strawberry model representing a single package."""

    name: str
    id: strawberry.ID


@strawberry.input
class UserInput(User):
    """GraphQL input type for User."""

    def create_instance(self) -> User:
        """Create a User instance from a UserInput instance.

        Returns:
            a User object
        """
        return User(**self.__dict__)
