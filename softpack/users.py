"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from .schemas.strawberry.user import User


class Users:
    """Users."""

    def get(self):
        """Get all users.

        Returns:
            a list of user objects
        """
        users = [
            User(
                name="Haris Rivas",
                id=0,
            ),
            User(
                name="Annabelle Lloyd",
                id=1,
            ),
            User(
                name="Khalil Sawyer",
                id=2,
            ),
            User(
                name="Frederick Contreras",
                id=3,
            ),
            User(
                name="Sian Duke",
                id=4,
            ),
        ]
        return users
