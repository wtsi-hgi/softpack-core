from .schemas.strawberry.user import User


class Users:
    
    def get(self):
        users = [
            User(
                name="Jip Bager",
                email="jip.bager@email.com",
            ),
            User(
                name="Eike Wetzel",
                email="eike.wetzel@email.com",
            ),
            User(
                name="Yalwa Norris",
                email="yalwa.norris@email.com",
            ),
        ]