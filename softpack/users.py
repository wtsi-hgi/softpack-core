from .schemas.strawberry.user import User


class Users:
    def get(self):
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
