from .schemas.strawberry.user import User


class Users:
    
    def get(self):
        users = [
            User(
                name="Haris Rivas",
                email="haris.rivas@example.com",
                id=0,
            ),
            User(
                name="Annabelle Lloyd",
                email="annabelle.lloyd@example.com",
                id=1,
            ),
            User(
                name="Khalil Sawyer",
                email="khalil.sawyer@example.com",
                id=2,
            ),
            User(
                name="Frederick Contreras",
                email="frederick.contreras@example.com",
                id=3,
            ),
            User(
                name="Sian Duke",
                email="sian.duke@example.com",
                id=4,
            ),
        ]
        return users