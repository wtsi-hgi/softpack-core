from typing import List
from .schemas.strawberry.environment import Environment
from .schemas.strawberry.package import Package
from .schemas.strawberry.user import User

class Environments:

    def get(self) -> List[Environment]:
        envs = [
            Environment(
                name="Env1",
                packages=[
                    Package(
                        name="Python",
                        version="3.10",
                    ),
                    Package(
                        name="R",
                        version="4.3.0",
                    ),
                ],
                owners=[
                    User(
                        name="Steve",
                        email="Steve@email.com"
                    )
                ]
            )
        ]
        return envs