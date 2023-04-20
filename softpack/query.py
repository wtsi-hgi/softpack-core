import strawberry
from typing import List
from .schemas.strawberry.environment import Environment
from .schemas.strawberry.package import Package
from .schemas.strawberry.user import User
from .environments import Environments
from .packages import Packages
from .users import Users


def env_count() -> int:
    envs = Environments()
    return len(envs.get())

def all_environments() -> List[Environment]:
    envs = Environments()
    return envs.get()

def all_packages() -> List[Package]:
    pkgs = Packages()
    return pkgs.get()

def all_users() -> List[User]:
    users = Users()
    return users.get()

@strawberry.type
class Query:
    env_count = strawberry.field(resolver=env_count)
    all_environments = strawberry.field(resolver=all_environments)
    all_packages = strawberry.field(resolver=all_packages)
    all_users = strawberry.field(resolver=all_users)