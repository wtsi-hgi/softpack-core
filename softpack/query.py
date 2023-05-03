import strawberry
from typing import List
from .schemas.strawberry.package_collection import PackageCollection
from .schemas.strawberry.environment import Environment
from .schemas.strawberry.user import User
from .package_collections import PackageCollections
from .environments import Environments
from .users import Users


def all_environments() -> List[Environment]:
    envs = Environments()
    return envs.get()

def all_package_collections() -> List[PackageCollection]:
    collections = PackageCollections()
    return collections.get()

def all_users() -> List[User]:
    users = Users()
    return users.get()

def find_environment(name: str) -> Environment:
    envs = Environments().get()
    matching_envs = [env for env in envs if env.name == name]
    if len(matching_envs) > 0:
        return matching_envs[0]
    else:
        return None
    
def find_package_collection(name: str) -> PackageCollection:
    collections = PackageCollections().get()
    matching_collections = [collection for collection in collections if collection.name == name]
    if len(matching_collections) > 0:
        return matching_collections[0]
    else:
        return None
    
def find_users(name: str) -> User:
    users = Users().get()
    matching_users = [user for user in users if user.name == name]
    if len(matching_users) > 0:
        return matching_users[0]
    else:
        return None


@strawberry.type
class Query:
    all_environments = strawberry.field(resolver=all_environments)
    all_packages = strawberry.field(resolver=all_package_collections)
    all_users = strawberry.field(resolver=all_users)
    find_environment = strawberry.field(resolver=find_environment)
    find_package_collection = strawberry.field(resolver=find_package_collection)
    find_users = strawberry.field(resolver=find_users)
