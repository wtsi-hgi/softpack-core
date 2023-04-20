from typing import List
from datetime import datetime
from .schemas.strawberry.environment import Environment
from .schemas.strawberry.package import Package
from .schemas.strawberry.user import User

class Environments:

    def get(self) -> List[Environment]:
        user_names = ["Haris Rivas", "Annabelle Lloyd", "Khalil Sawyer", "Frederick Contreras", "Sian Duke"]
        env_names= ["whistling-acorn", "jumping-humpback", "spotted-peacock", "hasty-daffodil", "dusty-leaf"]
        envs = [
            Environment(
                name=env_names[i],
                description="Lorem ipsum",
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
                        name=user_names[i],
                        
                        email=".".join(user_names[i].lower().split(" ")) + "@example.com",
                        id=i,
                    )
                ],
                creation_date=datetime.now(),
                status= ["completed", "pending", "failed"][i % 3],
                id=i
            )
            for i in range(5)
        ]
        return envs
